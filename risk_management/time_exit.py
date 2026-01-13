"""
Time Exit Manager - wymusza zamknięcie pozycji po upływie max czasu.

Horyzonty:
- DAILY: max 48h
- WEEKLY: max 7 dni
- MONTHLY: max 30 dni

v2.0 - "Nie żeń się z trade'em"
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ExitUrgency(Enum):
    """Pilność zamknięcia pozycji."""
    NONE = "none"           # Nie trzeba zamykać
    WARNING = "warning"     # Zbliża się deadline
    URGENT = "urgent"       # Zamknij przy najbliższej okazji
    FORCE = "force"         # Zamknij natychmiast po cenie rynkowej


@dataclass
class TimeExitCheck:
    """Wynik sprawdzenia time-based exit."""
    should_exit: bool
    urgency: ExitUrgency
    time_remaining: timedelta
    time_elapsed: timedelta
    max_duration: timedelta
    reason: str
    
    @property
    def time_remaining_hours(self) -> float:
        """Pozostały czas w godzinach."""
        return self.time_remaining.total_seconds() / 3600
    
    @property
    def elapsed_percent(self) -> float:
        """Procent wykorzystanego czasu."""
        if self.max_duration.total_seconds() == 0:
            return 100.0
        return (self.time_elapsed.total_seconds() / self.max_duration.total_seconds()) * 100
    
    def to_dict(self) -> Dict:
        return {
            "should_exit": self.should_exit,
            "urgency": self.urgency.value,
            "time_remaining_hours": round(self.time_remaining_hours, 1),
            "elapsed_percent": round(self.elapsed_percent, 1),
            "reason": self.reason,
        }


class TimeExitManager:
    """
    Zarządza time-based exits.
    
    Filozofia: Czas to ryzyko. Im dłużej pozycja otwarta,
    tym więcej może się zmienić. Wymuszamy zamknięcie.
    """
    
    # Max czas trzymania per horyzont
    MAX_DURATION = {
        "DAILY": timedelta(hours=48),
        "WEEKLY": timedelta(days=7),
        "MONTHLY": timedelta(days=30),
    }
    
    # Warning threshold (% max czasu)
    WARNING_THRESHOLD = 0.75  # 75% czasu → warning
    URGENT_THRESHOLD = 0.90   # 90% czasu → urgent
    
    # Forex Friday close
    FRIDAY_CLOSE_HOUR = 16  # Zamknij Forex przed 16:00 w piątek
    
    def __init__(self):
        pass
    
    def check(
        self,
        entry_time: datetime,
        horizon: str,
        current_time: datetime = None,
        market: str = "forex",
    ) -> TimeExitCheck:
        """
        Sprawdza czy pozycja powinna być zamknięta z powodu czasu.
        
        Args:
            entry_time: Czas otwarcia pozycji
            horizon: "DAILY", "WEEKLY", "MONTHLY"
            current_time: Aktualny czas (domyślnie now())
            market: "forex" lub "crypto"
        
        Returns:
            TimeExitCheck
        """
        current_time = current_time or datetime.now()
        horizon = horizon.upper()
        
        max_duration = self.MAX_DURATION.get(horizon, self.MAX_DURATION["DAILY"])
        time_elapsed = current_time - entry_time
        time_remaining = max_duration - time_elapsed
        
        # Sprawdź przekroczenie max czasu
        if time_remaining <= timedelta(0):
            return TimeExitCheck(
                should_exit=True,
                urgency=ExitUrgency.FORCE,
                time_remaining=timedelta(0),
                time_elapsed=time_elapsed,
                max_duration=max_duration,
                reason=f"Max duration exceeded ({horizon}: {max_duration})",
            )
        
        # Sprawdź Forex Friday close
        if market.lower() == "forex":
            friday_exit = self._check_friday_close(current_time)
            if friday_exit:
                return friday_exit._replace(
                    time_elapsed=time_elapsed,
                    max_duration=max_duration,
                )
        
        # Sprawdź progi ostrzeżeń
        elapsed_ratio = time_elapsed / max_duration
        
        if elapsed_ratio >= self.URGENT_THRESHOLD:
            return TimeExitCheck(
                should_exit=False,  # Nie wymuszaj, ale ostrzeż
                urgency=ExitUrgency.URGENT,
                time_remaining=time_remaining,
                time_elapsed=time_elapsed,
                max_duration=max_duration,
                reason=f"Approaching deadline ({elapsed_ratio:.0%} elapsed)",
            )
        
        if elapsed_ratio >= self.WARNING_THRESHOLD:
            return TimeExitCheck(
                should_exit=False,
                urgency=ExitUrgency.WARNING,
                time_remaining=time_remaining,
                time_elapsed=time_elapsed,
                max_duration=max_duration,
                reason=f"Time warning ({elapsed_ratio:.0%} elapsed)",
            )
        
        return TimeExitCheck(
            should_exit=False,
            urgency=ExitUrgency.NONE,
            time_remaining=time_remaining,
            time_elapsed=time_elapsed,
            max_duration=max_duration,
            reason="Within time limits",
        )
    
    def _check_friday_close(self, current_time: datetime) -> Optional[TimeExitCheck]:
        """Sprawdza czy trzeba zamknąć Forex przed weekendem."""
        # Piątek = 4 (Monday=0)
        if current_time.weekday() == 4:
            if current_time.hour >= self.FRIDAY_CLOSE_HOUR:
                return TimeExitCheck(
                    should_exit=True,
                    urgency=ExitUrgency.URGENT,
                    time_remaining=timedelta(0),
                    time_elapsed=timedelta(0),  # Będzie nadpisane
                    max_duration=timedelta(0),  # Będzie nadpisane
                    reason="Friday close - close before weekend",
                )
        return None
    
    def get_deadline(self, entry_time: datetime, horizon: str) -> datetime:
        """Zwraca deadline dla pozycji."""
        horizon = horizon.upper()
        max_duration = self.MAX_DURATION.get(horizon, self.MAX_DURATION["DAILY"])
        return entry_time + max_duration
    
    def should_reduce_size_for_time(
        self,
        entry_time: datetime,
        horizon: str,
        current_time: datetime = None,
    ) -> float:
        """
        Zwraca mnożnik pozycji bazując na pozostałym czasie.
        
        Im bliżej deadline, tym mniejsza pozycja przy re-entry.
        
        Returns:
            float: 0.0 - 1.0 (mnożnik pozycji)
        """
        check = self.check(entry_time, horizon, current_time)
        
        if check.should_exit:
            return 0.0  # Nie otwieraj nowych pozycji
        
        if check.urgency == ExitUrgency.URGENT:
            return 0.3
        
        if check.urgency == ExitUrgency.WARNING:
            return 0.7
        
        return 1.0


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    manager = TimeExitManager()
    
    # Test różnych scenariuszy
    scenarios = [
        ("DAILY", timedelta(hours=20)),
        ("DAILY", timedelta(hours=40)),
        ("DAILY", timedelta(hours=50)),  # Przekroczony
        ("WEEKLY", timedelta(days=5)),
        ("WEEKLY", timedelta(days=8)),   # Przekroczony
    ]
    
    print("=" * 60)
    print("TIME EXIT MANAGER TESTS")
    print("=" * 60)
    
    for horizon, elapsed in scenarios:
        entry_time = datetime.now() - elapsed
        check = manager.check(entry_time, horizon)
        
        print(f"\n{horizon} | Elapsed: {elapsed}")
        print(f"  Should Exit: {check.should_exit}")
        print(f"  Urgency: {check.urgency.value}")
        print(f"  Remaining: {check.time_remaining_hours:.1f}h")
        print(f"  Elapsed %: {check.elapsed_percent:.0f}%")
        print(f"  Reason: {check.reason}")
