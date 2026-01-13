"""
Conflict Resolver - rozwiązuje konflikty między modelami bazując na reżimie rynku.
"""
from typing import Dict, List
import logging

from config.settings import RISK_SETTINGS
from config.model_weights import REGIME_WEIGHT_MULTIPLIERS

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    Rozwiązuje konflikty między modelami bazując na reżimie rynku.
    
    Reguły:
    - High volatility (VIX > 25) → trend models mają priorytet
    - Low volatility (VIX < 15) → mean reversion ma priorytet
    - News window (ważne newsy w 1h) → sentiment models override
    """
    
    def __init__(self):
        self.vix_high = RISK_SETTINGS.get("high_volatility_vix", 25)
        self.vix_low = RISK_SETTINGS.get("low_volatility_vix", 15)
        self.max_vix = RISK_SETTINGS.get("max_vix_for_trading", 30)
    
    def detect_regime(
        self, 
        vix: float = 20, 
        news_within_1h: bool = False,
        fear_greed: Optional[int] = None
    ) -> str:
        """
        Wykrywa aktualny reżim rynku.
        
        Args:
            vix: Wartość VIX
            news_within_1h: Czy są ważne newsy w ciągu 1h
            fear_greed: Crypto Fear & Greed Index (0-100)
        
        Returns:
            Nazwa reżimu: high_volatility, low_volatility, news_window, normal
        """
        # News window ma najwyższy priorytet
        if news_within_1h:
            return "news_window"
        
        # Sprawdź volatility
        if vix > self.vix_high:
            return "high_volatility"
        elif vix < self.vix_low:
            return "low_volatility"
        
        return "normal"
    
    def should_trade(self, vix: float = 20) -> bool:
        """
        Sprawdza czy warunki pozwalają na trading.
        
        Returns:
            True jeśli można handlować, False jeśli za wysoki VIX
        """
        return vix <= self.max_vix
    
    def resolve(
        self, 
        signals: List[Dict], 
        vix: float = 20,
        news_within_1h: bool = False,
        fear_greed: Optional[int] = None
    ) -> tuple:
        """
        Rozwiązuje konflikty i dostosowuje wagi sygnałów.
        
        Args:
            signals: Lista sygnałów
            vix: Wartość VIX
            news_within_1h: Czy są ważne newsy
            fear_greed: Fear & Greed Index
        
        Returns:
            Tuple (adjusted_signals, regime, trading_allowed)
        """
        regime = self.detect_regime(vix, news_within_1h, fear_greed)
        trading_allowed = self.should_trade(vix)
        
        if not trading_allowed:
            logger.warning(f"Trading zablokowany! VIX = {vix} (max = {self.max_vix})")
            # Zwróć wszystkie sygnały z zerowymi wagami
            return [
                {**s, 'weight_multiplier': 0.0, 'reason': 'VIX too high'} 
                for s in signals
            ], regime, False
        
        # Pobierz mnożniki dla danego reżimu
        multipliers = REGIME_WEIGHT_MULTIPLIERS.get(regime, REGIME_WEIGHT_MULTIPLIERS["normal"])
        
        adjusted_signals = []
        for signal in signals:
            # Pobierz nazwę źródła
            source = signal.get('model') or signal.get('strategy') or 'unknown'
            
            # Pobierz mnożnik
            multiplier = multipliers.get(source, 1.0)
            
            adjusted_signal = signal.copy()
            adjusted_signal['weight_multiplier'] = multiplier
            adjusted_signal['regime'] = regime
            
            adjusted_signals.append(adjusted_signal)
        
        logger.info(f"Regime: {regime}, VIX: {vix}, Signals adjusted: {len(adjusted_signals)}")
        
        return adjusted_signals, regime, True
    
    def get_regime_description(self, regime: str) -> str:
        """Zwraca opis reżimu po polsku."""
        descriptions = {
            "high_volatility": "Wysoka zmienność (VIX > 25) - faworyzowane modele trendowe",
            "low_volatility": "Niska zmienność (VIX < 15) - faworyzowana strategia mean reversion",
            "news_window": "Okno newsowe - priorytet dla modeli sentiment",
            "normal": "Normalne warunki - standardowe wagi",
        }
        return descriptions.get(regime, "Nieznany reżim")


# Import dla type hints
from typing import Optional


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    resolver = ConflictResolver()
    
    # Przykładowe sygnały
    test_signals = [
        {'signal': 0.7, 'confidence': 0.85, 'model': 'finbert'},
        {'signal': 0.5, 'confidence': 0.75, 'model': 'polish_bert'},
        {'signal': -0.5, 'confidence': 0.80, 'strategy': 'mean_reversion'},
        {'signal': 0.3, 'confidence': 0.65, 'strategy': 'momentum_sentiment'},
    ]
    
    # Test różnych reżimów
    test_cases = [
        (15, False, "Low volatility"),
        (20, False, "Normal"),
        (28, False, "High volatility"),
        (20, True, "News window"),
        (35, False, "VIX too high"),
    ]
    
    print("Conflict Resolver Tests:")
    print("=" * 60)
    
    for vix, news, desc in test_cases:
        adjusted, regime, can_trade = resolver.resolve(test_signals, vix=vix, news_within_1h=news)
        
        print(f"\n{desc} (VIX={vix}, News={news}):")
        print(f"  Regime: {regime}")
        print(f"  Can trade: {can_trade}")
        if can_trade:
            for s in adjusted:
                source = s.get('model') or s.get('strategy')
                print(f"  - {source}: multiplier={s['weight_multiplier']:.1f}")
