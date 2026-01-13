"""
Agregator sygnałów - łączy sygnały ze wszystkich modeli i strategii.
"""
from typing import Dict, List, Optional
import logging
from datetime import datetime

from config.model_weights import get_weight, SENTIMENT_MODEL_WEIGHTS, STRATEGY_WEIGHTS
from config.settings import RISK_SETTINGS

logger = logging.getLogger(__name__)


class SignalAggregator:
    """
    Agreguje sygnały ze wszystkich modeli i strategii w jeden sygnał końcowy.
    
    Metoda: Weighted Voting
    Formula: final_score = Σ(signal * weight * confidence) / Σ(weight)
    """
    
    def __init__(self):
        self.buy_threshold = RISK_SETTINGS.get("signal_threshold_buy", 0.3)
        self.sell_threshold = RISK_SETTINGS.get("signal_threshold_sell", -0.3)
    
    def aggregate(
        self, 
        signals: List[Dict],
        regime: str = "normal"
    ) -> Dict:
        """
        Agreguje listę sygnałów w jeden sygnał końcowy.
        
        Args:
            signals: Lista słowników z sygnałami. Każdy powinien zawierać:
                     - signal: float od -1 do +1
                     - confidence: float od 0 do 1
                     - model lub strategy: str (nazwa źródła)
            regime: Reżim rynku (normal, high_volatility, low_volatility, news_window)
        
        Returns:
            Słownik z zagregowanym sygnałem
        """
        if not signals:
            return self._empty_result()
        
        weighted_sum = 0.0
        total_weight = 0.0
        signal_details = []
        
        for signal_data in signals:
            # Pobierz nazwę źródła
            source = signal_data.get('model') or signal_data.get('strategy') or 'unknown'
            
            # Pobierz wagę z uwzględnieniem reżimu
            weight = get_weight(source, regime)
            
            # Uwzględnij ewentualny mnożnik z conflict resolver
            weight_multiplier = signal_data.get('weight_multiplier', 1.0)
            final_weight = weight * weight_multiplier
            
            # Pobierz sygnał i confidence
            signal = signal_data.get('signal', 0)
            confidence = signal_data.get('confidence', 0.5)
            
            # Dodaj do sumy ważonej
            weighted_sum += signal * final_weight * confidence
            total_weight += final_weight
            
            # Zapisz szczegóły
            signal_details.append({
                'source': source,
                'signal': signal,
                'confidence': confidence,
                'weight': round(final_weight, 4),
                'contribution': round(signal * final_weight * confidence, 4),
            })
        
        # Oblicz końcowy wynik
        if total_weight > 0:
            final_score = weighted_sum / total_weight
        else:
            final_score = 0.0
        
        # Określ akcję
        if final_score > self.buy_threshold:
            action = 'BUY'
        elif final_score < self.sell_threshold:
            action = 'SELL'
        else:
            action = 'HOLD'
        
        # Oblicz siłę sygnału (0-100%)
        strength = min(abs(final_score) / 1.0, 1.0) * 100
        
        return {
            'action': action,
            'score': round(final_score, 4),
            'confidence': round(abs(final_score), 4),
            'strength': round(strength, 1),
            'regime': regime,
            'signals_count': len(signals),
            'timestamp': datetime.now().isoformat(),
            'details': signal_details,
        }
    
    def aggregate_by_segment(
        self,
        forex_signals: List[Dict],
        crypto_signals: List[Dict],
        regime: str = "normal"
    ) -> Dict:
        """
        Agreguje sygnały osobno dla Forex i Crypto.
        
        Returns:
            Słownik z zagregowanymi sygnałami dla każdego segmentu
        """
        forex_result = self.aggregate(forex_signals, regime) if forex_signals else self._empty_result()
        crypto_result = self.aggregate(crypto_signals, regime) if crypto_signals else self._empty_result()
        
        return {
            'forex': forex_result,
            'crypto': crypto_result,
            'timestamp': datetime.now().isoformat(),
            'regime': regime,
        }
    
    def _empty_result(self) -> Dict:
        """Zwraca pusty wynik."""
        return {
            'action': 'HOLD',
            'score': 0.0,
            'confidence': 0.0,
            'strength': 0.0,
            'regime': 'normal',
            'signals_count': 0,
            'timestamp': datetime.now().isoformat(),
            'details': [],
        }
    
    def get_conflicts(self, signals: List[Dict]) -> List[Dict]:
        """
        Identyfikuje konflikty między sygnałami.
        
        Returns:
            Lista konfliktów (gdzie sygnały mają przeciwne kierunki)
        """
        conflicts = []
        
        # Podziel na bullish i bearish
        bullish = [s for s in signals if s.get('signal', 0) > 0.2]
        bearish = [s for s in signals if s.get('signal', 0) < -0.2]
        
        if bullish and bearish:
            conflicts.append({
                'type': 'directional_conflict',
                'bullish_count': len(bullish),
                'bearish_count': len(bearish),
                'bullish_sources': [s.get('model') or s.get('strategy') for s in bullish],
                'bearish_sources': [s.get('model') or s.get('strategy') for s in bearish],
            })
        
        return conflicts


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    aggregator = SignalAggregator()
    
    # Przykładowe sygnały
    test_signals = [
        {'signal': 0.7, 'confidence': 0.85, 'model': 'finbert'},
        {'signal': 0.5, 'confidence': 0.75, 'model': 'polish_bert'},
        {'signal': -0.3, 'confidence': 0.60, 'strategy': 'mean_reversion'},
        {'signal': 0.4, 'confidence': 0.70, 'strategy': 'technical'},
    ]
    
    result = aggregator.aggregate(test_signals, regime="normal")
    
    print("Aggregation Result:")
    print("=" * 50)
    print(f"Action: {result['action']}")
    print(f"Score: {result['score']:.4f}")
    print(f"Strength: {result['strength']:.1f}%")
    print(f"\nSignal Details:")
    for detail in result['details']:
        print(f"  - {detail['source']}: signal={detail['signal']:.2f}, "
              f"weight={detail['weight']:.2f}, contribution={detail['contribution']:.4f}")
    
    # Test konfliktów
    conflicts = aggregator.get_conflicts(test_signals)
    if conflicts:
        print(f"\nConflicts detected: {conflicts}")
