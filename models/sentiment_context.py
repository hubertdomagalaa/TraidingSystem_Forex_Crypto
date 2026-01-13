"""
Sentiment Context - sentiment jako gate/filter, nie voter.

Sentiment nie głosuje razem z RSI. Sentiment:
- określa dozwolony kierunek
- modyfikuje position size
- może zablokować trade

v2.0 - Refaktoryzacja z linear voting na gate logic
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SentimentRegime(Enum):
    """Reżim sentymentu rynkowego."""
    CALM = "calm"           # Normalny, spokojny rynek
    EMOTIONAL = "emotional"  # Podwyższony sentyment, ale kontrolowany
    PANIC = "panic"         # Ekstremalne emocje (strach lub euforia)


class SentimentSource(Enum):
    """Źródła sentymentu z ich TTL."""
    TWITTER = "twitter"       # TTL: 6-24h
    REDDIT = "reddit"         # TTL: 6-24h
    CRYPTO_NEWS = "crypto_news"  # TTL: 1-3 dni
    FOREX_NEWS = "forex_news"    # TTL: 1-3 dni
    MACRO_CB = "macro_cb"        # TTL: 3-10 dni (Central Bank, makro)


# TTL w godzinach dla każdego źródła
SOURCE_TTL_HOURS = {
    SentimentSource.TWITTER: 12,      # 12h default
    SentimentSource.REDDIT: 18,       # 18h default
    SentimentSource.CRYPTO_NEWS: 48,  # 2 dni
    SentimentSource.FOREX_NEWS: 48,   # 2 dni
    SentimentSource.MACRO_CB: 168,    # 7 dni
}


@dataclass
class SentimentSignal:
    """Pojedynczy sygnał sentymentu z jednego źródła."""
    source: SentimentSource
    value: float          # -1.0 do +1.0
    confidence: float     # 0.0 do 1.0
    timestamp: datetime
    text: Optional[str] = None
    
    @property
    def ttl_hours(self) -> int:
        """Time-to-live w godzinach."""
        return SOURCE_TTL_HOURS.get(self.source, 24)
    
    def is_expired(self) -> bool:
        """Czy sygnał wygasł (starszy niż TTL)."""
        age = datetime.now() - self.timestamp
        return age.total_seconds() / 3600 > self.ttl_hours
    
    def age_hours(self) -> float:
        """Wiek sygnału w godzinach."""
        return (datetime.now() - self.timestamp).total_seconds() / 3600
    
    def decay_factor(self) -> float:
        """Współczynnik zaniku (1.0 = świeży, 0.0 = wygasły)."""
        age_ratio = self.age_hours() / self.ttl_hours
        return max(0.0, 1.0 - age_ratio)


@dataclass
class SentimentContext:
    """
    Zagregowany kontekst sentymentu.
    
    To NIE jest sygnał do głosowania!
    To jest KONTEKST, który:
    - określa dozwolony kierunek (bias_direction)
    - modyfikuje wielkość pozycji (position_modifier)
    - może zablokować trade (allows_direction)
    """
    bias_direction: str      # "LONG", "SHORT", "NEUTRAL"
    confidence: float        # 0.0 do 1.0 (zagregowana pewność)
    regime: SentimentRegime  # calm / emotional / panic
    signals: List[SentimentSignal]
    timestamp: datetime
    
    @classmethod
    def from_signals(cls, signals: List[SentimentSignal]) -> "SentimentContext":
        """
        Tworzy kontekst z listy sygnałów.
        Automatycznie filtruje wygasłe sygnały.
        """
        # Filtruj wygasłe
        valid_signals = [s for s in signals if not s.is_expired()]
        
        if not valid_signals:
            return cls(
                bias_direction="NEUTRAL",
                confidence=0.0,
                regime=SentimentRegime.CALM,
                signals=[],
                timestamp=datetime.now(),
            )
        
        # Oblicz ważoną średnią z decay
        total_weight = 0.0
        weighted_sum = 0.0
        
        for sig in valid_signals:
            weight = sig.confidence * sig.decay_factor()
            weighted_sum += sig.value * weight
            total_weight += weight
        
        avg_sentiment = weighted_sum / total_weight if total_weight > 0 else 0.0
        avg_confidence = total_weight / len(valid_signals)
        
        # Określ kierunek
        if avg_sentiment > 0.15:
            bias = "LONG"
        elif avg_sentiment < -0.15:
            bias = "SHORT"
        else:
            bias = "NEUTRAL"
        
        # Określ reżim
        regime = cls._detect_regime(valid_signals, avg_confidence)
        
        return cls(
            bias_direction=bias,
            confidence=avg_confidence,
            regime=regime,
            signals=valid_signals,
            timestamp=datetime.now(),
        )
    
    @staticmethod
    def _detect_regime(signals: List[SentimentSignal], avg_conf: float) -> SentimentRegime:
        """Wykrywa reżim sentymentu."""
        if not signals:
            return SentimentRegime.CALM
        
        # Sprawdź rozrzut (czy sygnały są spójne?)
        values = [s.value for s in signals]
        if len(values) < 2:
            spread = 0
        else:
            spread = max(values) - min(values)
        
        # Sprawdź ekstremalne wartości
        extreme_count = sum(1 for v in values if abs(v) > 0.7)
        extreme_ratio = extreme_count / len(values)
        
        # Panic: dużo ekstremalnych lub wysoki spread
        if extreme_ratio > 0.5 or (spread > 1.0 and avg_conf > 0.6):
            return SentimentRegime.PANIC
        
        # Emotional: umiarkowane emocje
        if avg_conf > 0.5 or extreme_ratio > 0.2:
            return SentimentRegime.EMOTIONAL
        
        return SentimentRegime.CALM
    
    def get_position_modifier(self) -> float:
        """
        Zwraca mnożnik dla wielkości pozycji.
        
        Returns:
            float: 0.0 do 1.0 (1.0 = pełna pozycja)
        """
        if self.regime == SentimentRegime.PANIC:
            # W panice - zmniejsz pozycję
            return 0.5
        
        if self.confidence < 0.3:
            # Niski confidence - mniejsza pozycja
            return 0.8
        
        if self.regime == SentimentRegime.EMOTIONAL:
            return 0.9
        
        return 1.0
    
    def allows_direction(self, direction: str) -> bool:
        """
        Czy sentiment pozwala na dany kierunek trade'u?
        
        Args:
            direction: "LONG" lub "SHORT"
        
        Returns:
            True jeśli dozwolone, False jeśli zablokowane
        """
        # Neutralny sentiment nie blokuje
        if self.bias_direction == "NEUTRAL":
            return True
        
        # Niski confidence nie blokuje
        if self.confidence < 0.4:
            return True
        
        # Conflict z wysokim confidence blokuje
        return self.bias_direction == direction.upper()
    
    def get_conflict_severity(self, direction: str) -> str:
        """
        Ocena powagi konfliktu z sentimentem.
        
        Returns:
            "none", "mild", "moderate", "severe"
        """
        if self.allows_direction(direction):
            if self.bias_direction == direction.upper():
                return "none"  # Zgodny
            return "mild"  # Neutralny lub niski confidence
        
        if self.confidence > 0.7 and self.regime == SentimentRegime.PANIC:
            return "severe"
        
        if self.confidence > 0.5:
            return "moderate"
        
        return "mild"
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika dla JSON output."""
        return {
            "bias_direction": self.bias_direction,
            "confidence": round(self.confidence, 3),
            "regime": self.regime.value,
            "position_modifier": self.get_position_modifier(),
            "signals_count": len(self.signals),
            "valid_signals": len([s for s in self.signals if not s.is_expired()]),
            "timestamp": self.timestamp.isoformat(),
        }


class SentimentAggregator:
    """
    Agregator sentymentu - zamienia sygnały ML na SentimentContext.
    
    Używa modeli FinBERT, CryptoBERT, PolishBERT ale NIE jako voterów,
    tylko do budowania kontekstu.
    """
    
    def __init__(self):
        self.signals: List[SentimentSignal] = []
    
    def add_signal(
        self,
        source: SentimentSource,
        value: float,
        confidence: float,
        text: str = None,
    ) -> None:
        """Dodaje nowy sygnał sentymentu."""
        signal = SentimentSignal(
            source=source,
            value=max(-1.0, min(1.0, value)),  # Clamp do -1, +1
            confidence=max(0.0, min(1.0, confidence)),
            timestamp=datetime.now(),
            text=text,
        )
        self.signals.append(signal)
        logger.debug(f"Added sentiment signal: {source.value} = {value:.3f}")
    
    def add_finbert_result(self, result: Dict) -> None:
        """Dodaje wynik z FinBERT."""
        self.add_signal(
            source=SentimentSource.FOREX_NEWS,
            value=result.get('signal', 0),
            confidence=result.get('confidence', 0.5),
            text=result.get('text'),
        )
    
    def add_cryptobert_result(self, result: Dict) -> None:
        """Dodaje wynik z CryptoBERT (z dampening)."""
        # CryptoBERT ma już dampening 0.8 w modelu
        self.add_signal(
            source=SentimentSource.CRYPTO_NEWS,
            value=result.get('signal', 0),
            confidence=result.get('confidence', 0.5),
            text=result.get('text'),
        )
    
    def add_twitter_sentiment(self, tweets: List[Dict]) -> None:
        """Dodaje sentyment z Twittera (wiele tweetów)."""
        for tweet in tweets:
            self.add_signal(
                source=SentimentSource.TWITTER,
                value=tweet.get('sentiment', 0),
                confidence=tweet.get('confidence', 0.5),
                text=tweet.get('text'),
            )
    
    def get_context(self) -> SentimentContext:
        """Zwraca zagregowany kontekst sentymentu."""
        return SentimentContext.from_signals(self.signals)
    
    def clear_expired(self) -> int:
        """Usuwa wygasłe sygnały. Zwraca liczbę usuniętych."""
        before = len(self.signals)
        self.signals = [s for s in self.signals if not s.is_expired()]
        removed = before - len(self.signals)
        if removed > 0:
            logger.info(f"Cleared {removed} expired sentiment signals")
        return removed
    
    def clear_all(self) -> None:
        """Czyści wszystkie sygnały."""
        self.signals = []


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    agg = SentimentAggregator()
    
    # Symuluj sygnały z różnych źródeł
    agg.add_finbert_result({
        'signal': 0.6,
        'confidence': 0.85,
        'text': 'ECB signals positive outlook',
    })
    
    agg.add_cryptobert_result({
        'signal': 0.4,
        'confidence': 0.7,
    })
    
    agg.add_signal(
        source=SentimentSource.TWITTER,
        value=-0.2,
        confidence=0.5,
    )
    
    # Pobierz kontekst
    ctx = agg.get_context()
    
    print("=" * 50)
    print("SENTIMENT CONTEXT")
    print("=" * 50)
    print(f"Bias Direction: {ctx.bias_direction}")
    print(f"Confidence: {ctx.confidence:.2f}")
    print(f"Regime: {ctx.regime.value}")
    print(f"Position Modifier: {ctx.get_position_modifier()}")
    print(f"Allows LONG: {ctx.allows_direction('LONG')}")
    print(f"Allows SHORT: {ctx.allows_direction('SHORT')}")
    print(f"Conflict with SHORT: {ctx.get_conflict_severity('SHORT')}")
