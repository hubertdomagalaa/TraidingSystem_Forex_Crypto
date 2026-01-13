"""
Mean Reversion Strategy dla EUR/PLN.
Ocena: 9/10 - najlepsza strategia dla PLN.
"""
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MeanReversionStrategy:
    """
    EUR/PLN ma silną tendencję do powrotu do średniej.
    
    Logika:
    - Z-score > 2.0 → SELL (cena za wysoko, wróci w dół)
    - Z-score < -2.0 → BUY (cena za nisko, wróci w górę)
    - |Z-score| < 0.5 → EXIT (powrót do średniej)
    
    NIE handluj gdy:
    - VIX > 30 (kryzys, trend dominuje)
    - Ważne newsy w ciągu 1h
    - Z-score niedostępny (za mało danych)
    """
    
    def __init__(self, lookback: int = 20):
        """
        Args:
            lookback: Okres do obliczania średniej i std (domyślnie 20)
        """
        self.lookback = lookback
        self.entry_zscore = 2.0    # Wejście gdy |zscore| > 2
        self.exit_zscore = 0.5     # Wyjście gdy |zscore| < 0.5
        self.max_vix = 30          # Nie handluj gdy VIX > 30
    
    def calculate_zscore(self, prices: pd.Series) -> Optional[float]:
        """
        Oblicza Z-score dla ostatniej ceny.
        
        Z-score = (cena - średnia) / odchylenie_standardowe
        """
        if len(prices) < self.lookback:
            return None
        
        mean = prices.rolling(self.lookback).mean().iloc[-1]
        std = prices.rolling(self.lookback).std().iloc[-1]
        current = prices.iloc[-1]
        
        if std == 0 or pd.isna(std):
            return None
        
        return (current - mean) / std
    
    def generate_signal(
        self, 
        prices: pd.Series, 
        vix: float = 20,
        news_within_1h: bool = False
    ) -> Dict:
        """
        Generuje sygnał mean reversion.
        
        Args:
            prices: Seria cen (Close)
            vix: Wartość VIX
            news_within_1h: Czy są ważne newsy w ciągu 1h
        
        Returns:
            Sygnał w formacie kompatybilnym z SignalAggregator
        """
        # Blokuj w wysokiej zmienności
        if vix > self.max_vix:
            logger.info(f"Mean reversion zablokowany: VIX={vix} > {self.max_vix}")
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'mean_reversion',
                'reason': f'VIX too high ({vix})',
                'blocked': True,
            }
        
        # Blokuj podczas newsów
        if news_within_1h:
            logger.info("Mean reversion zablokowany: News window")
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'mean_reversion',
                'reason': 'News window - avoiding mean reversion',
                'blocked': True,
            }
        
        # Oblicz Z-score
        zscore = self.calculate_zscore(prices)
        
        if zscore is None:
            return {
                'signal': 0.0,
                'confidence': 0.0,
                'strategy': 'mean_reversion',
                'reason': 'Insufficient data for Z-score',
            }
        
        # Generuj sygnał
        if zscore > self.entry_zscore:
            # Cena za wysoko - sprzedaj (wróci w dół)
            signal = -1.0
            confidence = min(zscore / 3, 1.0)
            reason = f'Z-score={zscore:.2f} > {self.entry_zscore} → SELL (mean reversion)'
        
        elif zscore < -self.entry_zscore:
            # Cena za nisko - kup (wróci w górę)
            signal = 1.0
            confidence = min(abs(zscore) / 3, 1.0)
            reason = f'Z-score={zscore:.2f} < -{self.entry_zscore} → BUY (mean reversion)'
        
        elif abs(zscore) < self.exit_zscore:
            # Blisko średniej - neutralny
            signal = 0.0
            confidence = 0.5
            reason = f'Z-score={zscore:.2f} near zero → At mean'
        
        else:
            # Pomiędzy - słaby sygnał
            signal = -zscore / self.entry_zscore * 0.5  # Słabszy sygnał
            confidence = 0.3
            reason = f'Z-score={zscore:.2f} → Weak signal'
        
        return {
            'signal': round(signal, 4),
            'confidence': round(confidence, 4),
            'strategy': 'mean_reversion',
            'zscore': round(zscore, 4),
            'lookback': self.lookback,
            'reason': reason,
            'entry_threshold': self.entry_zscore,
            'current_price': float(prices.iloc[-1]) if not prices.empty else None,
        }
    
    def get_stop_loss(self, entry_price: float, atr: float, direction: str) -> float:
        """
        Oblicza stop loss na podstawie ATR.
        
        Args:
            entry_price: Cena wejścia
            atr: Average True Range
            direction: 'long' lub 'short'
        
        Returns:
            Poziom stop loss
        """
        sl_multiplier = 1.5  # SL = 1.5 * ATR
        
        if direction == 'long':
            return entry_price - (atr * sl_multiplier)
        else:
            return entry_price + (atr * sl_multiplier)
    
    def get_take_profit(self, entry_price: float, zscore: float, direction: str) -> float:
        """
        Oblicza take profit - cel to powrót do średniej (zscore = 0).
        
        Uproszczone: TP = entry_price ± (entry_price * |zscore| * 0.01)
        """
        # Cel: powrót do średniej (około 50% ruchu)
        move_pct = abs(zscore) * 0.005  # 0.5% na każdy punkt zscore
        
        if direction == 'long':
            return entry_price * (1 + move_pct)
        else:
            return entry_price * (1 - move_pct)


# Przykład użycia
if __name__ == "__main__":
    import yfinance as yf
    
    # Pobierz dane EUR/PLN
    ticker = yf.Ticker("EURPLN=X")
    df = ticker.history(period="3mo")
    
    strategy = MeanReversionStrategy(lookback=20)
    
    # Generuj sygnał
    signal = strategy.generate_signal(df['Close'], vix=18)
    
    print("Mean Reversion Strategy - EUR/PLN")
    print("=" * 50)
    print(f"Signal: {signal['signal']:.4f}")
    print(f"Confidence: {signal['confidence']:.4f}")
    print(f"Z-score: {signal.get('zscore', 'N/A')}")
    print(f"Reason: {signal['reason']}")
    
    # Test z wysokim VIX
    print("\n--- Test z VIX=35 ---")
    signal_high_vix = strategy.generate_signal(df['Close'], vix=35)
    print(f"Signal: {signal_high_vix['signal']} ({signal_high_vix['reason']})")
