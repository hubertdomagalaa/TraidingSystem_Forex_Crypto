"""
Multi-Timeframe Analysis.
Analizuje trend na wyższych TF zanim handlujesz na niższym.
"""
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MultiTimeframeAnalyzer:
    """
    Multi-Timeframe Analysis (MTF).
    
    Zasada: Handluj zgodnie z trendem wyższego timeframe'u.
    
    Przykład:
    - Daily trend: UP
    - 4H trend: UP  
    - 1H sygnał: BUY → WYKONAJ (zgodny z D i 4H)
    
    - Daily trend: UP
    - 4H trend: DOWN
    - 1H sygnał: BUY → OSTROŻNIE (konflikt)
    """
    
    TIMEFRAME_HIERARCHY = ['1W', '1D', '4H', '1H']
    
    def __init__(self):
        pass
    
    def analyze_trend(self, df: pd.DataFrame) -> Dict:
        """
        Analizuje trend na podstawie EMA i ceny.
        
        Returns:
            {'direction': 'up'/'down'/'sideways', 'strength': 0-1}
        """
        if df is None or len(df) < 50:
            return {'direction': 'sideways', 'strength': 0.0}
        
        # Standaryzuj kolumny
        df = df.copy()
        df.columns = df.columns.str.lower()
        
        if 'close' not in df.columns:
            return {'direction': 'sideways', 'strength': 0.0}
        
        # EMA 20 i 50
        ema_20 = df['close'].ewm(span=20, adjust=False).mean()
        ema_50 = df['close'].ewm(span=50, adjust=False).mean()
        
        current_price = df['close'].iloc[-1]
        current_ema20 = ema_20.iloc[-1]
        current_ema50 = ema_50.iloc[-1]
        
        # Określ trend
        # Bullish: Price > EMA20 > EMA50
        # Bearish: Price < EMA20 < EMA50
        
        if current_price > current_ema20 > current_ema50:
            # Strong uptrend
            strength = min((current_price - current_ema50) / current_ema50 * 10, 1.0)
            return {'direction': 'up', 'strength': abs(strength)}
        
        elif current_price < current_ema20 < current_ema50:
            # Strong downtrend
            strength = min((current_ema50 - current_price) / current_ema50 * 10, 1.0)
            return {'direction': 'down', 'strength': abs(strength)}
        
        elif current_price > current_ema50:
            # Weak uptrend
            return {'direction': 'up', 'strength': 0.3}
        
        elif current_price < current_ema50:
            # Weak downtrend
            return {'direction': 'down', 'strength': 0.3}
        
        else:
            return {'direction': 'sideways', 'strength': 0.0}
    
    def get_mtf_signal(
        self,
        data_1h: pd.DataFrame,
        data_4h: pd.DataFrame,
        data_1d: pd.DataFrame,
        signal_1h: float  # -1 do +1
    ) -> Dict:
        """
        Generuje sygnał MTF.
        
        Args:
            data_1h, data_4h, data_1d: DataFrames z różnych timeframe'ów
            signal_1h: Oryginalny sygnał z 1H
        
        Returns:
            Zmodyfikowany sygnał z uwzględnieniem MTF
        """
        # Analizuj trendy
        trend_1h = self.analyze_trend(data_1h)
        trend_4h = self.analyze_trend(data_4h)
        trend_1d = self.analyze_trend(data_1d)
        
        # Sprawdź alignment
        bullish_count = sum(1 for t in [trend_1h, trend_4h, trend_1d] if t['direction'] == 'up')
        bearish_count = sum(1 for t in [trend_1h, trend_4h, trend_1d] if t['direction'] == 'down')
        
        if bullish_count == 3 and signal_1h > 0:
            # Perfect bullish alignment
            multiplier = 1.3
            confidence = 0.9
            alignment = 'perfect_bullish'
            advice = "🟢 Wszystkie TF zgodne - SILNY sygnał long"
        
        elif bearish_count == 3 and signal_1h < 0:
            # Perfect bearish alignment
            multiplier = 1.3
            confidence = 0.9
            alignment = 'perfect_bearish'
            advice = "🔴 Wszystkie TF zgodne - SILNY sygnał short"
        
        elif bullish_count >= 2 and signal_1h > 0:
            # Good bullish alignment
            multiplier = 1.1
            confidence = 0.7
            alignment = 'good_bullish'
            advice = "🟡 Dobry alignment bullish"
        
        elif bearish_count >= 2 and signal_1h < 0:
            # Good bearish alignment
            multiplier = 1.1
            confidence = 0.7
            alignment = 'good_bearish'
            advice = "🟡 Dobry alignment bearish"
        
        elif (bullish_count >= 2 and signal_1h < 0) or (bearish_count >= 2 and signal_1h > 0):
            # Conflict - sygnał przeciwny do trendu
            multiplier = 0.3
            confidence = 0.3
            alignment = 'conflict'
            advice = "⚠️ KONFLIKT - sygnał przeciwny do wyższych TF!"
        
        else:
            # Mixed/Sideways
            multiplier = 0.7
            confidence = 0.5
            alignment = 'mixed'
            advice = "⚪ Mixed signals - ostrożność"
        
        adjusted_signal = signal_1h * multiplier
        
        return {
            'original_signal': signal_1h,
            'adjusted_signal': round(adjusted_signal, 4),
            'multiplier': multiplier,
            'confidence': confidence,
            'alignment': alignment,
            'advice': advice,
            'trends': {
                '1H': trend_1h,
                '4H': trend_4h,
                '1D': trend_1d,
            },
            'strategy': 'multi_timeframe',
        }
    
    def get_simple_mtf_check(
        self,
        higher_tf_data: pd.DataFrame,
        signal: float
    ) -> Dict:
        """
        Prosty check MTF - tylko jeden wyższy TF.
        
        Args:
            higher_tf_data: Dane z wyższego TF (np. daily)
            signal: Oryginalny sygnał
        
        Returns:
            Dict z adjusted signal
        """
        trend = self.analyze_trend(higher_tf_data)
        
        # Zgodność
        if (trend['direction'] == 'up' and signal > 0) or \
           (trend['direction'] == 'down' and signal < 0):
            # Zgodny z trendem
            multiplier = 1.2
            aligned = True
        elif trend['direction'] == 'sideways':
            # Neutral
            multiplier = 1.0
            aligned = None
        else:
            # Przeciwny
            multiplier = 0.5
            aligned = False
        
        return {
            'signal': round(signal * multiplier, 4),
            'original': signal,
            'multiplier': multiplier,
            'higher_tf_trend': trend['direction'],
            'aligned': aligned,
            'strategy': 'mtf_simple',
        }


# Przykład użycia
if __name__ == "__main__":
    import yfinance as yf
    
    logging.basicConfig(level=logging.INFO)
    
    # Pobierz dane z różnych TF
    print("📊 Pobieranie danych EUR/PLN...")
    ticker = yf.Ticker("EURPLN=X")
    
    data_1h = ticker.history(period="5d", interval="1h")
    data_4h = ticker.history(period="30d", interval="1d")  # Symulacja 4H
    data_1d = ticker.history(period="90d", interval="1d")
    
    mtf = MultiTimeframeAnalyzer()
    
    # Przykładowy sygnał z 1H
    signal_1h = 0.6  # Bullish signal
    
    print(f"\n🎯 Original 1H signal: {signal_1h}")
    
    result = mtf.get_mtf_signal(data_1h, data_4h, data_1d, signal_1h)
    
    print(f"\n📈 Multi-Timeframe Analysis:")
    print(f"  Adjusted signal: {result['adjusted_signal']}")
    print(f"  Multiplier: {result['multiplier']}x")
    print(f"  Alignment: {result['alignment']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"  Advice: {result['advice']}")
    print(f"\n  Trends:")
    for tf, trend in result['trends'].items():
        emoji = "🟢" if trend['direction'] == 'up' else "🔴" if trend['direction'] == 'down' else "⚪"
        print(f"    {tf}: {emoji} {trend['direction']} ({trend['strength']:.2f})")
