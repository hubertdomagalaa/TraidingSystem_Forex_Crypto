"""
Kolektor danych kryptowalut z ccxt.
"""
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import logging

from config.crypto_assets import (
    CRYPTO_ASSETS, 
    CRYPTO_EXCHANGE, 
    CRYPTO_HISTORY_DAYS,
    DEFAULT_CRYPTO_TIMEFRAME
)

logger = logging.getLogger(__name__)


class CryptoCollector:
    """
    Pobiera dane kryptowalut z giełd przez ccxt.
    UWAGA: Tylko do pobierania danych, NIE do tradingu!
    """
    
    def __init__(self, exchange_id: str = None):
        self.exchange_id = exchange_id or CRYPTO_EXCHANGE
        self.assets = CRYPTO_ASSETS
        self.history_days = CRYPTO_HISTORY_DAYS
        self.default_timeframe = DEFAULT_CRYPTO_TIMEFRAME
        
        # Inicjalizuj giełdę
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
            })
            logger.info(f"Połączono z giełdą: {self.exchange_id}")
        except Exception as e:
            logger.error(f"Błąd połączenia z giełdą: {e}")
            self.exchange = None
    
    def get_current_price(self, pair: str) -> Optional[float]:
        """
        Pobiera aktualną cenę dla pary krypto.
        
        Args:
            pair: Nazwa pary, np. "BTC/USDT"
        
        Returns:
            Aktualna cena lub None w przypadku błędu
        """
        if self.exchange is None:
            return None
        
        if pair not in self.assets:
            logger.error(f"Nieznana para krypto: {pair}")
            return None
        
        symbol = self.assets[pair]["symbol"]
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        
        except Exception as e:
            logger.error(f"Błąd pobierania ceny {pair}: {e}")
            return None
    
    def get_historical_data(
        self, 
        pair: str, 
        days: Optional[int] = None,
        timeframe: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        Pobiera dane historyczne OHLCV dla pary krypto.
        
        Args:
            pair: Nazwa pary, np. "BTC/USDT"
            days: Liczba dni wstecz
            timeframe: Interwał czasowy (1h, 4h, 1d)
        
        Returns:
            DataFrame z kolumnami: timestamp, open, high, low, close, volume
        """
        if self.exchange is None:
            return None
        
        if pair not in self.assets:
            logger.error(f"Nieznana para krypto: {pair}")
            return None
        
        symbol = self.assets[pair]["symbol"]
        days = days or self.history_days
        timeframe = timeframe or self.default_timeframe
        
        try:
            # Oblicz since timestamp
            since = self.exchange.parse8601(
                (datetime.now() - timedelta(days=days)).isoformat()
            )
            
            # Pobierz OHLCV
            ohlcv = self.exchange.fetch_ohlcv(
                symbol, 
                timeframe=timeframe, 
                since=since,
                limit=1000
            )
            
            if not ohlcv:
                logger.warning(f"Brak danych dla {pair}")
                return None
            
            # Konwertuj na DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Konwertuj timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Dodaj kolumnę z nazwą pary
            df['pair'] = pair
            
            logger.info(f"Pobrano {len(df)} rekordów dla {pair}")
            return df
        
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
        
        for pair in self.assets.keys():
            data = self.get_historical_data(pair, days=days)
            if data is not None:
                all_data[pair] = data
        
        return all_data
    
    def get_24h_stats(self, pair: str) -> Optional[Dict]:
        """
        Pobiera statystyki 24h dla pary.
        
        Returns:
            Słownik ze statystykami (high, low, volume, change)
        """
        if self.exchange is None:
            return None
        
        if pair not in self.assets:
            return None
        
        symbol = self.assets[pair]["symbol"]
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            
            return {
                'last': ticker.get('last'),
                'high_24h': ticker.get('high'),
                'low_24h': ticker.get('low'),
                'volume_24h': ticker.get('quoteVolume'),
                'change_24h': ticker.get('percentage'),
                'bid': ticker.get('bid'),
                'ask': ticker.get('ask'),
            }
        
        except Exception as e:
            logger.error(f"Błąd pobierania statystyk {pair}: {e}")
            return None
    
    def get_orderbook_imbalance(self, pair: str, depth: int = 20) -> Optional[float]:
        """
        Oblicza nierównowagę order booka (bid/ask ratio).
        
        Wartość > 1 = więcej bidów (bullish pressure)
        Wartość < 1 = więcej asków (bearish pressure)
        
        Returns:
            Bid/Ask ratio
        """
        if self.exchange is None:
            return None
        
        if pair not in self.assets:
            return None
        
        symbol = self.assets[pair]["symbol"]
        
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=depth)
            
            bid_volume = sum([bid[1] for bid in orderbook['bids'][:depth]])
            ask_volume = sum([ask[1] for ask in orderbook['asks'][:depth]])
            
            if ask_volume == 0:
                return None
            
            return bid_volume / ask_volume
        
        except Exception as e:
            logger.error(f"Błąd pobierania orderbook {pair}: {e}")
            return None
    
    def calculate_volatility(self, pair: str, period: int = 14) -> Optional[float]:
        """
        Oblicza zmienność (ATR %) dla pary.
        
        Args:
            pair: Nazwa pary
            period: Okres ATR
        
        Returns:
            Zmienność jako procent ceny
        """
        data = self.get_historical_data(pair, days=period * 2)
        
        if data is None or len(data) < period:
            return None
        
        # Oblicz True Range
        data['tr'] = pd.concat([
            data['high'] - data['low'],
            abs(data['high'] - data['close'].shift(1)),
            abs(data['low'] - data['close'].shift(1))
        ], axis=1).max(axis=1)
        
        # ATR
        atr = data['tr'].rolling(period).mean().iloc[-1]
        current_price = data['close'].iloc[-1]
        
        return (atr / current_price) * 100


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    collector = CryptoCollector()
    
    # Test pobierania aktualnej ceny
    price = collector.get_current_price("BTC/USDT")
    print(f"BTC/USDT aktualna cena: {price}")
    
    # Test 24h stats
    stats = collector.get_24h_stats("BTC/USDT")
    print(f"BTC/USDT 24h stats: {stats}")
    
    # Test pobierania danych historycznych
    data = collector.get_historical_data("BTC/USDT", days=7)
    if data is not None:
        print(f"\nOstatnie 5 rekordów BTC/USDT:")
        print(data.tail())
    
    # Test volatility
    vol = collector.calculate_volatility("BTC/USDT")
    print(f"\nBTC/USDT zmienność: {vol:.2f}%")
