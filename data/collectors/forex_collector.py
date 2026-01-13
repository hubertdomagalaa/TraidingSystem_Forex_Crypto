"""
Kolektor danych Forex z yfinance.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

from config.forex_pairs import FOREX_PAIRS, FOREX_HISTORY_DAYS, DEFAULT_FOREX_TIMEFRAME

logger = logging.getLogger(__name__)


class ForexCollector:
    """
    Pobiera dane Forex z Yahoo Finance.
    """
    
    def __init__(self):
        self.pairs = FOREX_PAIRS
        self.history_days = FOREX_HISTORY_DAYS
        self.default_timeframe = DEFAULT_FOREX_TIMEFRAME
    
    def get_current_price(self, pair: str) -> Optional[float]:
        """
        Pobiera aktualną cenę dla pary walutowej.
        
        Args:
            pair: Nazwa pary, np. "EUR/PLN"
        
        Returns:
            Aktualna cena lub None w przypadku błędu
        """
        if pair not in self.pairs:
            logger.error(f"Nieznana para walutowa: {pair}")
            return None
        
        symbol = self.pairs[pair]["symbol"]
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            
            if data.empty:
                logger.warning(f"Brak danych dla {pair}")
                return None
            
            return float(data['Close'].iloc[-1])
        
        except Exception as e:
            logger.error(f"Błąd pobierania ceny {pair}: {e}")
            return None
    
    def get_historical_data(
        self, 
        pair: str, 
        days: Optional[int] = None,
        interval: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Pobiera dane historyczne dla pary walutowej.
        
        Args:
            pair: Nazwa pary, np. "EUR/PLN"
            days: Liczba dni wstecz (domyślnie z konfiguracji)
            interval: Interwał czasowy (1h, 4h, 1d, 1wk)
        
        Returns:
            DataFrame z kolumnami: Open, High, Low, Close, Volume
        """
        if pair not in self.pairs:
            logger.error(f"Nieznana para walutowa: {pair}")
            return None
        
        symbol = self.pairs[pair]["symbol"]
        days = days or self.history_days
        interval = interval or self.default_timeframe
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            ticker = yf.Ticker(symbol)
            data = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=interval
            )
            
            if data.empty:
                logger.warning(f"Brak danych historycznych dla {pair}")
                return None
            
            # Dodaj kolumnę z nazwą pary
            data['pair'] = pair
            
            logger.info(f"Pobrano {len(data)} rekordów dla {pair}")
            return data
        
        except Exception as e:
            logger.error(f"Błąd pobierania danych historycznych {pair}: {e}")
            return None
    
    def get_all_pairs_data(self, days: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """
        Pobiera dane dla wszystkich skonfigurowanych par.
        
        Returns:
            Słownik {pair_name: DataFrame}
        """
        all_data = {}
        
        for pair in self.pairs.keys():
            data = self.get_historical_data(pair, days=days)
            if data is not None:
                all_data[pair] = data
        
        return all_data
    
    def get_latest_candles(self, pair: str, count: int = 100) -> Optional[pd.DataFrame]:
        """
        Pobiera ostatnie N świec dla pary.
        
        Args:
            pair: Nazwa pary
            count: Liczba świec do pobrania
        
        Returns:
            DataFrame z ostatnimi świecami
        """
        data = self.get_historical_data(pair, days=count * 2)  # Zapas na weekendy
        
        if data is not None and len(data) >= count:
            return data.tail(count)
        return data
    
    def calculate_returns(self, pair: str, periods: List[int] = [1, 5, 20]) -> Optional[Dict]:
        """
        Oblicza zwroty dla różnych okresów.
        
        Args:
            pair: Nazwa pary
            periods: Lista okresów (w dniach)
        
        Returns:
            Słownik ze zwrotami procentowymi
        """
        data = self.get_historical_data(pair, days=max(periods) + 10)
        
        if data is None or len(data) < max(periods):
            return None
        
        returns = {}
        current_price = data['Close'].iloc[-1]
        
        for period in periods:
            if len(data) > period:
                past_price = data['Close'].iloc[-period-1]
                pct_return = ((current_price - past_price) / past_price) * 100
                returns[f"{period}d"] = round(pct_return, 2)
        
        return returns


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    collector = ForexCollector()
    
    # Test pobierania aktualnej ceny
    price = collector.get_current_price("EUR/PLN")
    print(f"EUR/PLN aktualna cena: {price}")
    
    # Test pobierania danych historycznych
    data = collector.get_historical_data("EUR/PLN", days=30)
    if data is not None:
        print(f"\nOstatnie 5 dni EUR/PLN:")
        print(data.tail())
    
    # Test zwrotów
    returns = collector.calculate_returns("EUR/PLN")
    print(f"\nZwroty EUR/PLN: {returns}")
