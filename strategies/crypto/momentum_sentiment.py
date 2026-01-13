"""
Momentum + Sentiment Strategy dla Crypto.
Ocena: 9/10 - główna strategia dla BTC/ETH.
"""
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class MomentumSentimentStrategy:
    """
    Łączy momentum cenowy z sentymentem.
    
    Logika - kupuj gdy WSZYSTKIE 3 warunki spełnione:
    1. Cena rośnie (momentum > 0)
    2. Sentiment pozytywny (> 0.3)
    3. Volume rośnie (opcjonalnie)
    
    Sprzedaj gdy wszystkie 3 są negatywne.
    W przeciwnych przypadkach - HOLD.
    """
    
    def __init__(self):
        self.momentum_period = 14
        self.sentiment_threshold = 0.3  # Min sentiment dla sygnału
        self.momentum_threshold = 2.0   # Min momentum % dla sygnału
    
    def calculate_momentum(self, prices: pd.Series, period: int = None) -> float:
        """
        Oblicza momentum (Rate of Change).
        
        ROC = ((current - past) / past) * 100
        """
        period = period or self.momentum_period
        
        if len(prices) < period:
            return 0.0
        
        current = prices.iloc[-1]
        past = prices.iloc[-period]
        
        if past == 0:
            return 0.0
        
        return ((current - past) / past) * 100
    
    def calculate_volume_change(self, volumes: pd.Series, period: int = 5) -> float:
        """
        Oblicza zmianę wolumenu (średnia ostatnich N vs poprzednich N).
        """
        if len(volumes) < period * 2:
            return 0.0
        
        recent_avg = volumes.iloc[-period:].mean()
        previous_avg = volumes.iloc[-period*2:-period].mean()
        
        if previous_avg == 0:
            return 0.0
        
        return ((recent_avg - previous_avg) / previous_avg) * 100
    
    def generate_signal(
        self,
        prices: pd.Series,
        sentiment_score: float,
        volumes: Optional[pd.Series] = None
    ) -> Dict:
        """
        Generuje sygnał momentum + sentiment.
        
        Args:
            prices: Seria cen (Close)
            sentiment_score: Zagregowany sentiment (-1 do +1) z CryptoBERT
            volumes: Seria wolumenów (opcjonalna)
        
        Returns:
            Sygnał w formacie kompatybilnym z SignalAggregator
        """
        # Oblicz momentum
        momentum = self.calculate_momentum(prices)
        
        # Oblicz zmianę wolumenu (jeśli dostępny)
        volume_change = 0.0
        if volumes is not None and not volumes.empty:
            volume_change = self.calculate_volume_change(volumes)
        
        # Sprawdź alignment
        price_bullish = momentum > self.momentum_threshold
        price_bearish = momentum < -self.momentum_threshold
        sentiment_bullish = sentiment_score > self.sentiment_threshold
        sentiment_bearish = sentiment_score < -self.sentiment_threshold
        volume_confirming = volume_change > 0
        
        # Generuj sygnał tylko gdy alignment istnieje
        if price_bullish and sentiment_bullish:
            # Strong BUY - momentum i sentiment zgodne
            signal = 1.0
            
            # Confidence bazowane na sile sygnałów
            confidence = min(
                (abs(momentum) / 10 + abs(sentiment_score)) / 2,
                1.0
            )
            
            # Bonus za potwierdzenie wolumenem
            if volume_confirming:
                confidence = min(confidence * 1.2, 1.0)
                reason = 'Bullish alignment: price↑ + sentiment↑ + volume↑'
            else:
                reason = 'Bullish alignment: price↑ + sentiment↑'
        
        elif price_bearish and sentiment_bearish:
            # Strong SELL - momentum i sentiment negatywne
            signal = -1.0
            
            confidence = min(
                (abs(momentum) / 10 + abs(sentiment_score)) / 2,
                1.0
            )
            
            if volume_confirming:
                confidence = min(confidence * 1.2, 1.0)
                reason = 'Bearish alignment: price↓ + sentiment↓ + volume↑'
            else:
                reason = 'Bearish alignment: price↓ + sentiment↓'
        
        elif price_bullish and sentiment_bearish:
            # Konflikt - momentum up ale sentiment down
            signal = 0.0
            confidence = 0.3
            reason = 'Conflict: price↑ but sentiment↓ → HOLD'
        
        elif price_bearish and sentiment_bullish:
            # Konflikt - momentum down ale sentiment up
            signal = 0.0
            confidence = 0.3
            reason = 'Conflict: price↓ but sentiment↑ → HOLD'
        
        else:
            # Brak wyraźnego sygnału
            signal = 0.0
            confidence = 0.2
            reason = 'No clear momentum or sentiment signal'
        
        return {
            'signal': round(signal, 4),
            'confidence': round(confidence, 4),
            'strategy': 'momentum_sentiment',
            'momentum': round(momentum, 2),
            'sentiment': round(sentiment_score, 4),
            'volume_change': round(volume_change, 2) if volumes is not None else None,
            'alignment': {
                'price_bullish': price_bullish,
                'price_bearish': price_bearish,
                'sentiment_bullish': sentiment_bullish,
                'sentiment_bearish': sentiment_bearish,
                'volume_confirming': volume_confirming,
            },
            'reason': reason,
        }
    
    def get_entry_conditions(self) -> Dict:
        """Zwraca warunki wejścia dla dokumentacji."""
        return {
            'buy': [
                f'Momentum > {self.momentum_threshold}%',
                f'Sentiment > {self.sentiment_threshold}',
                'Volume increasing (optional)',
            ],
            'sell': [
                f'Momentum < -{self.momentum_threshold}%',
                f'Sentiment < -{self.sentiment_threshold}',
                'Volume increasing (optional)',
            ],
        }


# Przykład użycia
if __name__ == "__main__":
    import numpy as np
    
    # Symulowane dane
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', periods=100, freq='4h')
    
    # Trend wzrostowy
    prices = pd.Series(
        40000 + np.cumsum(np.random.randn(100) * 100 + 50),
        index=dates
    )
    volumes = pd.Series(
        np.random.uniform(1000, 5000, 100),
        index=dates
    )
    
    strategy = MomentumSentimentStrategy()
    
    # Test różnych scenariuszy
    print("Momentum + Sentiment Strategy Tests")
    print("=" * 60)
    
    # Scenariusz 1: Bullish alignment
    signal1 = strategy.generate_signal(prices, sentiment_score=0.6, volumes=volumes)
    print(f"\n1. Bullish scenario (sentiment=0.6):")
    print(f"   Signal: {signal1['signal']:.4f}")
    print(f"   Confidence: {signal1['confidence']:.4f}")
    print(f"   Momentum: {signal1['momentum']:.2f}%")
    print(f"   Reason: {signal1['reason']}")
    
    # Scenariusz 2: Bearish sentiment
    signal2 = strategy.generate_signal(prices, sentiment_score=-0.5, volumes=volumes)
    print(f"\n2. Conflict scenario (sentiment=-0.5):")
    print(f"   Signal: {signal2['signal']:.4f}")
    print(f"   Reason: {signal2['reason']}")
    
    # Scenariusz 3: Neutral
    signal3 = strategy.generate_signal(prices, sentiment_score=0.1, volumes=volumes)
    print(f"\n3. Neutral scenario (sentiment=0.1):")
    print(f"   Signal: {signal3['signal']:.4f}")
    print(f"   Reason: {signal3['reason']}")
