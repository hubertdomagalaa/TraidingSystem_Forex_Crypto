"""
Kalendarz ekonomiczny - pobiera ważne eventy.
Używa predefiniowanych dat (w produkcji dodaj API).
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class EconomicEvent:
    """Pojedynczy event ekonomiczny."""
    date: datetime
    time: str
    currency: str
    event: str
    impact: str  # 'low', 'medium', 'high'
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class CalendarCollector:
    """
    Kalendarz ekonomiczny.
    
    Ważne eventy do śledzenia:
    - ECB Rate Decision
    - Fed Rate Decision (FOMC)
    - NFP (Non-Farm Payrolls)
    - CPI (Inflation)
    - GDP
    - NBP Rate Decision (dla PLN)
    
    UWAGA: W wersji bez API używa przybliżonych dat.
    Dla prawdziwego tradingu dodaj integrację z:
    - Trading Economics API
    - Forex Factory (scraping)
    - Investing.com Calendar
    """
    
    # Kluczowe eventy (high impact)
    HIGH_IMPACT_KEYWORDS = [
        "Interest Rate Decision",
        "Rate Decision",
        "FOMC",
        "Non-Farm Payrolls",
        "NFP",
        "CPI",
        "Inflation Rate",
        "GDP",
        "Unemployment Rate",
        "ECB",
        "Fed",
        "NBP",
        "PMI",
        "Retail Sales",
    ]
    
    # Regularne eventy (przybliżone daty)
    # Format: (dzień_miesiąca, nazwa, waluta, czas)
    RECURRING_EVENTS = [
        # US Events
        (1, "ISM Manufacturing PMI", "USD", "16:00", "high"),
        (3, "ISM Services PMI", "USD", "16:00", "high"),
        (-1, "Non-Farm Payrolls", "USD", "14:30", "high"),  # First Friday
        (12, "CPI m/m", "USD", "14:30", "high"),
        (15, "Retail Sales m/m", "USD", "14:30", "medium"),
        
        # EUR Events
        (1, "ECB Interest Rate Decision", "EUR", "13:45", "high"),  # ~co 6 tygodni
        (15, "GDP q/q", "EUR", "11:00", "high"),
        
        # PLN Events
        (3, "NBP Interest Rate Decision", "PLN", "14:00", "high"),
    ]
    
    def __init__(self):
        self.events_cache: List[EconomicEvent] = []
        self.last_fetch: Optional[datetime] = None
    
    def get_upcoming_events(
        self, 
        days_ahead: int = 7, 
        high_impact_only: bool = True,
        currencies: List[str] = None
    ) -> List[EconomicEvent]:
        """
        Pobiera nadchodzące eventy.
        
        Args:
            days_ahead: Ile dni do przodu
            high_impact_only: Tylko high impact
            currencies: Filtruj po walutach (None = wszystkie)
        
        Returns:
            Lista eventów posortowana po dacie
        """
        events = self._generate_upcoming_events(days_ahead)
        
        if high_impact_only:
            events = [e for e in events if e.impact == 'high']
        
        if currencies:
            events = [e for e in events if e.currency in currencies]
        
        return sorted(events, key=lambda x: x.date)
    
    def _generate_upcoming_events(self, days_ahead: int) -> List[EconomicEvent]:
        """
        Generuje listę nadchodzących eventów.
        W produkcji zastąp prawdziwym API!
        """
        events = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        for day_offset in range(days_ahead + 1):
            check_date = today + timedelta(days=day_offset)
            day_of_month = check_date.day
            day_of_week = check_date.weekday()  # 0=Monday, 4=Friday
            
            for (event_day, name, currency, time_str, impact) in self.RECURRING_EVENTS:
                # Specjalny przypadek: First Friday (NFP)
                if event_day == -1:
                    # Pierwszy piątek miesiąca
                    if day_of_week == 4 and day_of_month <= 7:
                        events.append(self._create_event(check_date, name, currency, time_str, impact))
                elif day_of_month == event_day:
                    events.append(self._create_event(check_date, name, currency, time_str, impact))
        
        return events
    
    def _create_event(
        self, 
        date: datetime, 
        name: str, 
        currency: str, 
        time_str: str, 
        impact: str
    ) -> EconomicEvent:
        """Tworzy obiekt EconomicEvent."""
        try:
            hour, minute = map(int, time_str.split(':'))
            event_datetime = date.replace(hour=hour, minute=minute)
        except:
            event_datetime = date
        
        return EconomicEvent(
            date=event_datetime,
            time=time_str,
            currency=currency,
            event=name,
            impact=impact,
        )
    
    def has_high_impact_today(self, currencies: List[str] = None) -> bool:
        """Sprawdza czy dziś są ważne eventy."""
        events = self.get_upcoming_events(
            days_ahead=0, 
            high_impact_only=True,
            currencies=currencies
        )
        today = datetime.now().date()
        return any(e.date.date() == today for e in events)
    
    def get_next_high_impact(self, currencies: List[str] = None) -> Optional[EconomicEvent]:
        """Zwraca najbliższy ważny event."""
        events = self.get_upcoming_events(
            days_ahead=30, 
            high_impact_only=True,
            currencies=currencies
        )
        now = datetime.now()
        future_events = [e for e in events if e.date > now]
        return future_events[0] if future_events else None
    
    def is_in_news_window(
        self, 
        hours_before: int = 1, 
        hours_after: int = 2,
        currencies: List[str] = None
    ) -> Dict:
        """
        Sprawdza czy jesteśmy w oknie wokół ważnego eventu.
        
        W oknie newsowym:
        - Wyższa waga dla modeli sentiment
        - Niższa waga dla mean reversion
        
        Returns:
            Dict z informacją o oknie i aktywnym evencie
        """
        events = self.get_upcoming_events(
            days_ahead=1, 
            high_impact_only=True,
            currencies=currencies
        )
        now = datetime.now()
        
        for event in events:
            window_start = event.date - timedelta(hours=hours_before)
            window_end = event.date + timedelta(hours=hours_after)
            
            if window_start <= now <= window_end:
                logger.info(f"W oknie newsowym: {event.event} ({event.currency})")
                return {
                    'in_window': True,
                    'event': event.event,
                    'currency': event.currency,
                    'event_time': event.date.isoformat(),
                    'window_end': window_end.isoformat(),
                    'weight_adjustments': {
                        'sentiment': 2.0,
                        'mean_reversion': 0.3,
                        'technical': 0.5,
                    }
                }
        
        return {
            'in_window': False,
            'event': None,
            'weight_adjustments': {
                'sentiment': 1.0,
                'mean_reversion': 1.0,
                'technical': 1.0,
            }
        }
    
    def get_events_for_display(self, days_ahead: int = 7) -> List[Dict]:
        """Zwraca eventy w formacie do wyświetlenia."""
        events = self.get_upcoming_events(days_ahead, high_impact_only=False)
        
        return [
            {
                'date': e.date.strftime('%Y-%m-%d'),
                'time': e.time,
                'currency': e.currency,
                'event': e.event,
                'impact': e.impact,
            }
            for e in events
        ]


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    calendar = CalendarCollector()
    
    print("📅 Upcoming High Impact Events (7 days):")
    print("-" * 60)
    events = calendar.get_upcoming_events(days_ahead=7)
    
    if events:
        for e in events:
            print(f"  {e.date.strftime('%Y-%m-%d %H:%M')} [{e.currency}] {e.event}")
    else:
        print("  Brak eventów w nadchodzących dniach")
    
    print(f"\n🔔 High impact today: {calendar.has_high_impact_today()}")
    
    window_status = calendar.is_in_news_window()
    print(f"📰 In news window: {window_status['in_window']}")
    if window_status['in_window']:
        print(f"   Event: {window_status['event']}")
    
    next_event = calendar.get_next_high_impact()
    if next_event:
        print(f"\n⏰ Next high impact: {next_event.event} ({next_event.date.strftime('%Y-%m-%d %H:%M')})")
