"""
Wskaźniki specyficzne dla intraday/swing trading.
VWAP, Pivot Points, Opening Range Breakout, Session High/Low.
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, time
import logging

logger = logging.getLogger(__name__)


class IntradayIndicators:
    """
    Wskaźniki dla day/swing trading:
    - VWAP (Volume Weighted Average Price)
    - Pivot Points (Daily S1/S2/R1/R2/PP)
    - Session High/Low
    - Opening Range Breakout
    - ADX (trend strength)
    """
    
    def __init__(self):
        pass
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """
        VWAP - Volume Weighted Average Price.
        
        Interpretacja:
        - Cena > VWAP = bullish bias (kupujący silniejsi)
        - Cena < VWAP = bearish bias (sprzedający silniejsi)
        
        VWAP często działa jako dynamiczny support/resistance.
        """
        df = df.copy()
        
        # Standaryzuj kolumny
        df.columns = df.columns.str.lower()
        
        # Sprawdź czy mamy volume
        if 'volume' not in df.columns or df['volume'].sum() == 0:
            # Dla Forex bez volume - zwróć średnią cenę
            return (df['high'] + df['low'] + df['close']) / 3
        
        # Typowa cena
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        # VWAP
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        return vwap
    
    def calculate_pivot_points(
        self, 
        high: float, 
        low: float, 
        close: float,
        method: str = "classic"
    ) -> Dict[str, float]:
        """
        Pivot Points - kluczowe poziomy S/R.
        
        Używane jako:
        - Entry points (odbicie od S1/R1)
        - Take profit levels
        - Stop loss placement
        
        Args:
            high, low, close: OHLC z poprzedniego dnia/sesji
            method: 'classic', 'fibonacci', 'camarilla'
        
        Returns:
            Dict z poziomami PP, R1-R3, S1-S3
        """
        pp = (high + low + close) / 3
        
        if method == "classic":
            r1 = 2 * pp - low
            s1 = 2 * pp - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)
            r3 = high + 2 * (pp - low)
            s3 = low - 2 * (high - pp)
            
        elif method == "fibonacci":
            diff = high - low
            r1 = pp + 0.382 * diff
            r2 = pp + 0.618 * diff
            r3 = pp + 1.000 * diff
            s1 = pp - 0.382 * diff
            s2 = pp - 0.618 * diff
            s3 = pp - 1.000 * diff
            
        elif method == "camarilla":
            diff = high - low
            r1 = close + diff * 1.1 / 12
            r2 = close + diff * 1.1 / 6
            r3 = close + diff * 1.1 / 4
            r4 = close + diff * 1.1 / 2
            s1 = close - diff * 1.1 / 12
            s2 = close - diff * 1.1 / 6
            s3 = close - diff * 1.1 / 4
            s4 = close - diff * 1.1 / 2
            
            return {
                'PP': round(pp, 5),
                'R1': round(r1, 5), 'R2': round(r2, 5), 
                'R3': round(r3, 5), 'R4': round(r4, 5),
                'S1': round(s1, 5), 'S2': round(s2, 5), 
                'S3': round(s3, 5), 'S4': round(s4, 5),
            }
        else:
            # Default to classic
            r1 = 2 * pp - low
            s1 = 2 * pp - high
            r2 = pp + (high - low)
            s2 = pp - (high - low)
            r3 = high + 2 * (pp - low)
            s3 = low - 2 * (high - pp)
        
        return {
            'PP': round(pp, 5),
            'R1': round(r1, 5), 'R2': round(r2, 5), 'R3': round(r3, 5),
            'S1': round(s1, 5), 'S2': round(s2, 5), 'S3': round(s3, 5),
        }
    
    def get_pivot_signal(
        self, 
        current_price: float, 
        pivots: Dict[str, float]
    ) -> Dict:
        """
        Generuje sygnał bazując na pozycji względem pivot points.
        """
        pp = pivots['PP']
        r1, r2 = pivots['R1'], pivots['R2']
        s1, s2 = pivots['S1'], pivots['S2']
        
        # Określ pozycję
        if current_price > r2:
            position = "above_r2"
            bias = "strong_bullish"
            signal = 0.8
        elif current_price > r1:
            position = "above_r1"
            bias = "bullish"
            signal = 0.5
        elif current_price > pp:
            position = "above_pp"
            bias = "slight_bullish"
            signal = 0.2
        elif current_price > s1:
            position = "below_pp"
            bias = "slight_bearish"
            signal = -0.2
        elif current_price > s2:
            position = "below_s1"
            bias = "bearish"
            signal = -0.5
        else:
            position = "below_s2"
            bias = "strong_bearish"
            signal = -0.8
        
        # Najbliższe poziomy
        levels = sorted(pivots.items(), key=lambda x: abs(x[1] - current_price))
        nearest = levels[0]
        
        return {
            'current_price': current_price,
            'position': position,
            'bias': bias,
            'signal': signal,
            'nearest_level': nearest[0],
            'nearest_price': nearest[1],
            'distance_to_nearest_pct': (current_price - nearest[1]) / current_price * 100,
            'pivots': pivots,
        }
    
    def opening_range_breakout(
        self, 
        df: pd.DataFrame, 
        range_bars: int = 3
    ) -> Dict:
        """
        Opening Range Breakout (ORB).
        
        Strategia:
        1. Wyznacz high/low z pierwszych N świec sesji
        2. Breakout powyżej = LONG
        3. Breakout poniżej = SHORT
        4. Wewnątrz range = WAIT
        
        Args:
            df: DataFrame z danymi
            range_bars: Ile świec stanowi opening range
        
        Returns:
            Dict z sygnałem i poziomami
        """
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        if len(df) < range_bars + 1:
            return {'signal': 0, 'error': 'Not enough data'}
        
        # Opening range
        opening_range = df.head(range_bars)
        or_high = opening_range['high'].max()
        or_low = opening_range['low'].min()
        or_mid = (or_high + or_low) / 2
        
        # Current price
        current_price = df['close'].iloc[-1]
        
        # Sygnał
        if current_price > or_high:
            signal = 1.0  # Long breakout
            direction = 'long'
            target = or_high + (or_high - or_low)  # 1R target
            stop = or_mid  # Stop w środku range
        elif current_price < or_low:
            signal = -1.0  # Short breakout
            direction = 'short'
            target = or_low - (or_high - or_low)
            stop = or_mid
        else:
            signal = 0.0  # W range
            direction = 'wait'
            target = None
            stop = None
        
        return {
            'signal': signal,
            'direction': direction,
            'or_high': round(or_high, 5),
            'or_low': round(or_low, 5),
            'or_mid': round(or_mid, 5),
            'current_price': round(current_price, 5),
            'breakout': signal != 0,
            'target': round(target, 5) if target else None,
            'stop': round(stop, 5) if stop else None,
            'strategy': 'opening_range_breakout',
        }
    
    def calculate_adx(
        self, 
        df: pd.DataFrame, 
        period: int = 14
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        ADX - Average Directional Index.
        
        Mierzy siłę trendu (nie kierunek!):
        - ADX < 20: Brak trendu (range) → Mean Reversion
        - ADX 20-40: Trend developing → Momentum
        - ADX > 40: Silny trend → Trend Following
        
        Returns:
            Tuple: (ADX, +DI, -DI)
        """
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # Directional Movement
        plus_dm = high - high.shift(1)
        minus_dm = low.shift(1) - low
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        # Smoothed
        atr = tr.ewm(span=period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
        
        # DX and ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(span=period, adjust=False).mean()
        
        return adx, plus_di, minus_di
    
    def get_adx_signal(self, adx_value: float, plus_di: float, minus_di: float) -> Dict:
        """
        Interpretuje ADX dla day trading.
        """
        # Siła trendu
        if adx_value < 20:
            trend_strength = "no_trend"
            recommended_strategy = "mean_reversion"
        elif adx_value < 40:
            trend_strength = "developing_trend"
            recommended_strategy = "momentum"
        else:
            trend_strength = "strong_trend"
            recommended_strategy = "trend_following"
        
        # Kierunek
        if plus_di > minus_di:
            direction = "bullish"
            signal = min(adx_value / 50, 1.0)
        else:
            direction = "bearish"
            signal = -min(adx_value / 50, 1.0)
        
        return {
            'adx': round(adx_value, 2),
            'plus_di': round(plus_di, 2),
            'minus_di': round(minus_di, 2),
            'trend_strength': trend_strength,
            'direction': direction,
            'signal': round(signal, 4),
            'recommended_strategy': recommended_strategy,
        }
    
    def calculate_all(self, df: pd.DataFrame) -> Dict:
        """
        Oblicza wszystkie wskaźniki intraday.
        """
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        results = {}
        
        # VWAP
        try:
            results['vwap'] = self.calculate_vwap(df).iloc[-1]
        except:
            results['vwap'] = None
        
        # Pivot Points (z poprzedniego dnia)
        if len(df) >= 2:
            prev_day = df.iloc[-2] if len(df) > 1 else df.iloc[-1]
            results['pivots'] = self.calculate_pivot_points(
                prev_day['high'], 
                prev_day['low'], 
                prev_day['close']
            )
        
        # ADX
        try:
            adx, plus_di, minus_di = self.calculate_adx(df)
            results['adx'] = {
                'value': adx.iloc[-1],
                'plus_di': plus_di.iloc[-1],
                'minus_di': minus_di.iloc[-1],
            }
        except:
            results['adx'] = None
        
        # ORB
        try:
            results['orb'] = self.opening_range_breakout(df)
        except:
            results['orb'] = None
        
        return results


# Przykład użycia
if __name__ == "__main__":
    import yfinance as yf
    
    logging.basicConfig(level=logging.INFO)
    
    # Pobierz dane
    print("📊 Pobieranie danych EUR/PLN...")
    ticker = yf.Ticker("EURPLN=X")
    df = ticker.history(period="5d", interval="1h")
    
    indicators = IntradayIndicators()
    
    # Test wszystkich wskaźników
    print("\n📈 Intraday Indicators:")
    
    results = indicators.calculate_all(df)
    
    if results.get('vwap'):
        current = df['Close'].iloc[-1]
        vwap = results['vwap']
        bias = "Bullish" if current > vwap else "Bearish"
        print(f"\n  VWAP: {vwap:.4f}")
        print(f"  Current: {current:.4f} → {bias}")
    
    if results.get('pivots'):
        print(f"\n  Pivot Points:")
        for level, price in results['pivots'].items():
            print(f"    {level}: {price}")
    
    if results.get('adx'):
        adx = results['adx']
        print(f"\n  ADX: {adx['value']:.2f}")
        print(f"  +DI: {adx['plus_di']:.2f}, -DI: {adx['minus_di']:.2f}")
