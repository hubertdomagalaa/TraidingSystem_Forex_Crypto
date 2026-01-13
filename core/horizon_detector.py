"""
Horizon Detector - wykrywa optymalny horyzont czasowy dla trade'u.

Horyzonty:
- DAILY: 1-2 dni, execution/momentum/reversion
- WEEKLY: 3-7 dni, swing/regime continuation  
- MONTHLY: 2-4 tygodnie, macro swing/repricing

v2.0 - Bez long-term, świat zmienia się za szybko!
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class TradingHorizon(Enum):
    """Dostępne horyzonty czasowe."""
    DAILY = "daily"      # 1-2 dni
    WEEKLY = "weekly"    # 3-7 dni
    MONTHLY = "monthly"  # 2-4 tygodnie


@dataclass
class HorizonConfig:
    """Konfiguracja dla danego horyzontu."""
    name: TradingHorizon
    max_duration: timedelta
    sl_atr_multiplier: tuple  # (min, max)
    tp_rr_ratio: tuple        # (min, max) Risk:Reward
    
    def get_sl_multiplier(self, volatility_regime: str = "normal") -> float:
        """Zwraca mnożnik ATR dla SL."""
        min_mult, max_mult = self.sl_atr_multiplier
        
        if volatility_regime == "high":
            return max_mult
        elif volatility_regime == "low":
            return min_mult
        return (min_mult + max_mult) / 2
    
    def get_rr_ratio(self, trend_strength: float = 0.5) -> float:
        """Zwraca R:R ratio."""
        min_rr, max_rr = self.tp_rr_ratio
        
        # Silniejszy trend = większy R:R możliwy
        return min_rr + (max_rr - min_rr) * trend_strength


# Konfiguracje horyzontów
HORIZON_CONFIGS = {
    TradingHorizon.DAILY: HorizonConfig(
        name=TradingHorizon.DAILY,
        max_duration=timedelta(hours=48),
        sl_atr_multiplier=(0.8, 1.2),
        tp_rr_ratio=(1.0, 1.8),
    ),
    TradingHorizon.WEEKLY: HorizonConfig(
        name=TradingHorizon.WEEKLY,
        max_duration=timedelta(days=7),
        sl_atr_multiplier=(1.2, 1.8),
        tp_rr_ratio=(1.5, 2.5),
    ),
    TradingHorizon.MONTHLY: HorizonConfig(
        name=TradingHorizon.MONTHLY,
        max_duration=timedelta(days=30),
        sl_atr_multiplier=(2.0, 2.5),
        tp_rr_ratio=(2.0, 3.0),
    ),
}


class HorizonDetector:
    """
    Wykrywa optymalny horyzont czasowy na podstawie warunków rynkowych.
    
    Logika:
    - High volatility + news → DAILY (szybko zamknij)
    - Strong trend → WEEKLY (daj mu czas)
    - Macro event → MONTHLY (repricing trwa)
    """
    
    CATALYST_TYPES = ["news", "earnings", "macro", "technical", "unknown"]
    
    def detect(
        self,
        volatility: float,          # ATR jako % ceny
        catalyst_type: str,         # news/earnings/macro/technical
        trend_strength: float,      # 0.0 - 1.0
        adx: float = 20,           # ADX value
        sentiment_regime: str = "calm",  # calm/emotional/panic
    ) -> TradingHorizon:
        """
        Wykrywa najlepszy horyzont dla aktualnych warunków.
        
        Args:
            volatility: Zmienność jako % (ATR/price)
            catalyst_type: Typ katalizatora
            trend_strength: Siła trendu (0-1)
            adx: Wartość ADX
            sentiment_regime: Reżim sentymentu
        
        Returns:
            TradingHorizon
        """
        # PANIC = zawsze krótki horyzont
        if sentiment_regime == "panic":
            logger.info("Horizon: DAILY (panic regime)")
            return TradingHorizon.DAILY
        
        # High volatility + news = DAILY
        if volatility > 0.02 and catalyst_type in ["news", "earnings"]:
            logger.info(f"Horizon: DAILY (high vol + {catalyst_type})")
            return TradingHorizon.DAILY
        
        # Macro event = MONTHLY (repricing takes time)
        if catalyst_type == "macro":
            logger.info("Horizon: MONTHLY (macro event)")
            return TradingHorizon.MONTHLY
        
        # Strong trend (ADX > 30 lub trend_strength > 0.7) = WEEKLY
        if adx > 30 or trend_strength > 0.7:
            logger.info(f"Horizon: WEEKLY (strong trend, ADX={adx:.1f})")
            return TradingHorizon.WEEKLY
        
        # Moderate trend = WEEKLY
        if adx > 20 or trend_strength > 0.5:
            logger.info(f"Horizon: WEEKLY (moderate trend)")
            return TradingHorizon.WEEKLY
        
        # Default: DAILY dla bezpieczeństwa
        logger.info("Horizon: DAILY (default)")
        return TradingHorizon.DAILY
    
    def get_config(self, horizon: TradingHorizon) -> HorizonConfig:
        """Zwraca konfigurację dla horyzontu."""
        return HORIZON_CONFIGS[horizon]
    
    def detect_with_config(self, **kwargs) -> tuple:
        """Wykrywa horyzont i zwraca razem z konfiguracją."""
        horizon = self.detect(**kwargs)
        config = self.get_config(horizon)
        return horizon, config


@dataclass 
class HorizonContext:
    """Pełny kontekst horyzontu dla trade'u."""
    horizon: TradingHorizon
    config: HorizonConfig
    detection_reason: str
    
    # Calculated values
    max_duration_hours: int
    sl_multiplier: float
    rr_ratio: float
    
    @classmethod
    def create(
        cls,
        horizon: TradingHorizon,
        volatility_regime: str = "normal",
        trend_strength: float = 0.5,
        reason: str = "",
    ) -> "HorizonContext":
        """Tworzy kontekst z obliczonymi wartościami."""
        config = HORIZON_CONFIGS[horizon]
        
        return cls(
            horizon=horizon,
            config=config,
            detection_reason=reason,
            max_duration_hours=int(config.max_duration.total_seconds() / 3600),
            sl_multiplier=config.get_sl_multiplier(volatility_regime),
            rr_ratio=config.get_rr_ratio(trend_strength),
        )
    
    def to_dict(self) -> Dict:
        """Konwertuje do słownika."""
        return {
            "horizon": self.horizon.value,
            "max_duration_hours": self.max_duration_hours,
            "sl_multiplier": round(self.sl_multiplier, 2),
            "rr_ratio": round(self.rr_ratio, 2),
            "reason": self.detection_reason,
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    detector = HorizonDetector()
    
    # Test różnych scenariuszy
    scenarios = [
        {"volatility": 0.03, "catalyst_type": "news", "trend_strength": 0.3, "adx": 15},
        {"volatility": 0.01, "catalyst_type": "technical", "trend_strength": 0.8, "adx": 35},
        {"volatility": 0.015, "catalyst_type": "macro", "trend_strength": 0.5, "adx": 25},
        {"volatility": 0.01, "catalyst_type": "technical", "trend_strength": 0.4, "adx": 18},
    ]
    
    print("=" * 60)
    print("HORIZON DETECTION TESTS")
    print("=" * 60)
    
    for i, s in enumerate(scenarios, 1):
        horizon = detector.detect(**s)
        config = detector.get_config(horizon)
        
        print(f"\nScenario {i}: {s}")
        print(f"  → Horizon: {horizon.value}")
        print(f"  → Max Duration: {config.max_duration}")
        print(f"  → SL Multiplier: {config.get_sl_multiplier():.2f}")
        print(f"  → R:R Ratio: {config.get_rr_ratio(s['trend_strength']):.2f}")
