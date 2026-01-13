"""
Engine wskaźników technicznych dla Forex.
Oblicza RSI, MACD, Bollinger Bands, ATR i generuje sygnały.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IndicatorEngine:
    """
    Oblicza wskaźniki techniczne i generuje sygnały.
    
    Wskaźniki:
    - RSI (14) - overbought/oversold
    - MACD (12, 26, 9) - trend direction
    - Bollinger Bands (20, 2) - volatility breakout
    - ATR (14) - dla stop loss calculation
    - SMA/EMA - trend direction
    """
    
    def __init__(self):
        # RSI settings
        self.rsi_period = 14
        self.rsi_overbought = 70
        self.rsi_oversold = 30
        
        # MACD settings
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        
        # Bollinger settings
        self.bb_period = 20
        self.bb_std = 2
        
        # ATR settings
        self.atr_period = 14
    
    def calculate_rsi(self, prices: pd.Series, period: int = None) -> pd.Series:
        """
        Oblicza RSI (Relative Strength Index).
        
        RSI < 30 = oversold (sygnał kupna)
        RSI > 70 = overbought (sygnał sprzedaży)
        """
        period = period or self.rsi_period
        
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Oblicza MACD (Moving Average Convergence Divergence).
        
        Returns:
            Tuple (macd_line, signal_line, histogram)
        """
        ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def calculate_bollinger_bands(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Oblicza Bollinger Bands.
        
        Returns:
            Tuple (upper_band, middle_band, lower_band)
        """
        middle = prices.rolling(window=self.bb_period).mean()
        std = prices.rolling(window=self.bb_period).std()
        
        upper = middle + (std * self.bb_std)
        lower = middle - (std * self.bb_std)
        
        return upper, middle, lower
    
    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """
        Oblicza ATR (Average True Range).
        Używany do position sizing i stop loss.
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=self.atr_period).mean()
        
        return atr
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """Oblicza Simple Moving Average."""
        return prices.rolling(window=period).mean()
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """Oblicza Exponential Moving Average."""
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate_zscore(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """
        Oblicza Z-score dla mean reversion.
        Z-score > 2 = cena za wysoko
        Z-score < -2 = cena za nisko
        """
        mean = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        zscore = (prices - mean) / std
        return zscore
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Oblicza wszystkie wskaźniki i dodaje do DataFrame.
        
        Args:
            df: DataFrame z kolumnami: open, high, low, close, volume
        
        Returns:
            DataFrame z dodanymi kolumnami wskaźników
        """
        # Standaryzuj nazwy kolumn
        df.columns = df.columns.str.lower()
        
        # RSI
        df['rsi'] = self.calculate_rsi(df['close'])
        
        # MACD
        df['macd'], df['macd_signal'], df['macd_hist'] = self.calculate_macd(df['close'])
        
        # Bollinger Bands
        df['bb_upper'], df['bb_middle'], df['bb_lower'] = self.calculate_bollinger_bands(df['close'])
        
        # ATR
        df['atr'] = self.calculate_atr(df['high'], df['low'], df['close'])
        
        # Z-score
        df['zscore'] = self.calculate_zscore(df['close'])
        
        # Moving Averages
        df['sma_20'] = self.calculate_sma(df['close'], 20)
        df['sma_50'] = self.calculate_sma(df['close'], 50)
        df['ema_12'] = self.calculate_ema(df['close'], 12)
        df['ema_26'] = self.calculate_ema(df['close'], 26)
        
        return df
    
    def get_rsi_signal(self, rsi: float) -> Dict:
        """Generuje sygnał na podstawie RSI."""
        if pd.isna(rsi):
            return {'signal': 0.0, 'confidence': 0.0, 'indicator': 'rsi', 'reason': 'No data'}
        
        if rsi < self.rsi_oversold:
            signal = 1.0
            confidence = min((self.rsi_oversold - rsi) / self.rsi_oversold, 1.0)
            reason = f'RSI oversold ({rsi:.1f})'
        elif rsi > self.rsi_overbought:
            signal = -1.0
            confidence = min((rsi - self.rsi_overbought) / (100 - self.rsi_overbought), 1.0)
            reason = f'RSI overbought ({rsi:.1f})'
        else:
            signal = 0.0
            confidence = 0.3
            reason = f'RSI neutral ({rsi:.1f})'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'indicator': 'rsi',
            'value': rsi,
            'reason': reason,
        }
    
    def get_macd_signal(self, macd: float, signal_line: float, histogram: float) -> Dict:
        """Generuje sygnał na podstawie MACD."""
        if pd.isna(macd) or pd.isna(signal_line):
            return {'signal': 0.0, 'confidence': 0.0, 'indicator': 'macd', 'reason': 'No data'}
        
        # Bullish: MACD > Signal i histogram rośnie
        # Bearish: MACD < Signal i histogram maleje
        
        if macd > signal_line and histogram > 0:
            signal = 1.0
            confidence = min(abs(histogram) * 10, 1.0)  # Normalizacja
            reason = 'MACD bullish crossover'
        elif macd < signal_line and histogram < 0:
            signal = -1.0
            confidence = min(abs(histogram) * 10, 1.0)
            reason = 'MACD bearish crossover'
        else:
            signal = 0.0
            confidence = 0.3
            reason = 'MACD neutral'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'indicator': 'macd',
            'macd': macd,
            'signal_line': signal_line,
            'histogram': histogram,
            'reason': reason,
        }
    
    def get_bollinger_signal(self, price: float, upper: float, lower: float, middle: float) -> Dict:
        """Generuje sygnał na podstawie Bollinger Bands."""
        if pd.isna(price) or pd.isna(upper) or pd.isna(lower):
            return {'signal': 0.0, 'confidence': 0.0, 'indicator': 'bollinger', 'reason': 'No data'}
        
        # Price at/below lower band = oversold
        # Price at/above upper band = overbought
        
        band_width = upper - lower
        if band_width == 0:
            return {'signal': 0.0, 'confidence': 0.0, 'indicator': 'bollinger', 'reason': 'Zero band width'}
        
        position = (price - lower) / band_width  # 0 = at lower, 1 = at upper
        
        if price <= lower:
            signal = 1.0  # Buy - at lower band
            confidence = min(abs(lower - price) / (band_width * 0.1), 1.0)
            reason = 'Price at lower Bollinger band'
        elif price >= upper:
            signal = -1.0  # Sell - at upper band
            confidence = min(abs(price - upper) / (band_width * 0.1), 1.0)
            reason = 'Price at upper Bollinger band'
        else:
            signal = 0.0
            confidence = 0.3
            reason = f'Price within bands ({position:.1%})'
        
        return {
            'signal': signal,
            'confidence': confidence,
            'indicator': 'bollinger',
            'position': position,
            'reason': reason,
        }
    
    def generate_combined_signal(self, df: pd.DataFrame) -> Dict:
        """
        Generuje zagregowany sygnał techniczny.
        Kombinuje RSI, MACD i Bollinger Bands.
        
        Returns:
            Sygnał w formacie kompatybilnym z SignalAggregator
        """
        if df.empty or len(df) < 26:  # Minimum dla MACD
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'technical',
                'reason': 'Insufficient data',
            }
        
        # Oblicz wskaźniki jeśli nie ma
        if 'rsi' not in df.columns:
            df = self.calculate_all(df)
        
        # Pobierz ostatnie wartości
        last = df.iloc[-1]
        
        # Pobierz sygnały z poszczególnych wskaźników
        rsi_signal = self.get_rsi_signal(last.get('rsi'))
        macd_signal = self.get_macd_signal(
            last.get('macd'), 
            last.get('macd_signal'), 
            last.get('macd_hist')
        )
        bb_signal = self.get_bollinger_signal(
            last.get('close'),
            last.get('bb_upper'),
            last.get('bb_lower'),
            last.get('bb_middle')
        )
        
        # Agreguj sygnały (równe wagi)
        signals = [rsi_signal, macd_signal, bb_signal]
        
        total_signal = sum(s['signal'] * s['confidence'] for s in signals)
        total_confidence = sum(s['confidence'] for s in signals)
        
        if total_confidence > 0:
            final_signal = total_signal / total_confidence
            final_confidence = total_confidence / len(signals)
        else:
            final_signal = 0.0
            final_confidence = 0.0
        
        return {
            'signal': round(final_signal, 4),
            'confidence': round(final_confidence, 4),
            'strategy': 'technical',
            'indicators': {
                'rsi': rsi_signal,
                'macd': macd_signal,
                'bollinger': bb_signal,
            },
            'atr': last.get('atr'),
            'zscore': last.get('zscore'),
        }


# Przykład użycia
if __name__ == "__main__":
    import yfinance as yf
    
    # Pobierz dane testowe
    ticker = yf.Ticker("EURPLN=X")
    df = ticker.history(period="3mo")
    
    # Oblicz wskaźniki
    engine = IndicatorEngine()
    df = engine.calculate_all(df)
    
    print("Ostatnie wartości wskaźników:")
    print(df[['Close', 'rsi', 'macd', 'macd_hist', 'bb_upper', 'bb_lower', 'atr', 'zscore']].tail())
    
    # Generuj sygnał
    signal = engine.generate_combined_signal(df)
    print(f"\nZagregowany sygnał techniczny:")
    print(f"  Signal: {signal['signal']:.4f}")
    print(f"  Confidence: {signal['confidence']:.4f}")
    print(f"  Strategy: {signal['strategy']}")
