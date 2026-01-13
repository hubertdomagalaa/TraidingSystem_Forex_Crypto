"""
Automatyczne pobieranie VIX z Yahoo Finance.
VIX = ^VIX na Yahoo Finance.
"""
import yfinance as yf
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class VIXCollector:
    """
    Pobiera aktualną wartość VIX z Yahoo Finance.
    
    VIX interpretacja:
    - < 15: Niska zmienność (mean reversion favored)
    - 15-25: Normalna zmienność
    - 25-30: Wysoka zmienność (trend following favored)
    - > 30: Ekstremalna zmienność (STOP TRADING!)
    """
    
    def __init__(self):
        self.symbol = "^VIX"
        self.last_value: Optional[float] = None
        self.last_fetch: Optional[datetime] = None
    
    def get_current(self) -> Dict:
        """
        Pobiera aktualną wartość VIX.
        
        Returns:
            Dict z value, regime, can_trade, advice
        """
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period="1d")
            
            if data.empty:
                logger.warning("Brak danych VIX")
                return self._default_response("No data")
            
            vix = float(data['Close'].iloc[-1])
            self.last_value = vix
            self.last_fetch = datetime.now()
            
            logger.info(f"VIX pobrany: {vix:.2f}")
            return self._interpret_vix(vix)
        
        except Exception as e:
            logger.error(f"Błąd pobierania VIX: {e}")
            return self._default_response(str(e))
    
    def _interpret_vix(self, vix: float) -> Dict:
        """Interpretuje wartość VIX."""
        
        if vix < 15:
            regime = "low_volatility"
            can_trade = True
            advice = "🟢 Niska zmienność - Mean Reversion preferowany"
            signal = 0.0
            weight_adjustments = {
                'mean_reversion': 1.5,
                'momentum': 0.8,
                'trend': 0.8,
            }
        elif vix < 25:
            regime = "normal"
            can_trade = True
            advice = "⚪ Normalna zmienność - Standardowe wagi"
            signal = 0.0
            weight_adjustments = {
                'mean_reversion': 1.0,
                'momentum': 1.0,
                'trend': 1.0,
            }
        elif vix < 30:
            regime = "high_volatility"
            can_trade = True
            advice = "🟡 Wysoka zmienność - Trend following preferowany, ostrożnie!"
            signal = -0.3
            weight_adjustments = {
                'mean_reversion': 0.5,
                'momentum': 1.2,
                'trend': 1.5,
            }
        else:
            regime = "extreme"
            can_trade = False
            advice = "🔴 EKSTREMALNA zmienność - STOP TRADING!"
            signal = -1.0
            weight_adjustments = {
                'mean_reversion': 0.0,
                'momentum': 0.0,
                'trend': 0.0,
            }
        
        return {
            'value': round(vix, 2),
            'regime': regime,
            'can_trade': can_trade,
            'advice': advice,
            'signal': signal,
            'weight_adjustments': weight_adjustments,
            'fetched_at': datetime.now().isoformat(),
        }
    
    def _default_response(self, error: str) -> Dict:
        """Odpowiedź domyślna przy błędzie."""
        # Zakładamy normalne warunki przy błędzie
        return {
            'value': 20.0,
            'regime': 'normal',
            'can_trade': True,
            'advice': f'⚠️ Błąd pobierania VIX: {error}. Zakładam normalny.',
            'signal': 0.0,
            'weight_adjustments': {
                'mean_reversion': 1.0,
                'momentum': 1.0,
                'trend': 1.0,
            },
            'error': error,
        }
    
    def get_historical(self, days: int = 30):
        """Pobiera historyczne wartości VIX."""
        try:
            ticker = yf.Ticker(self.symbol)
            data = ticker.history(period=f"{days}d")
            return data
        except Exception as e:
            logger.error(f"Błąd historii VIX: {e}")
            return None
    
    def get_regime_multipliers(self) -> Dict[str, float]:
        """
        Zwraca mnożniki wag dla aktualnego reżimu.
        Używane przez SignalAggregator.
        """
        current = self.get_current()
        return current.get('weight_adjustments', {
            'mean_reversion': 1.0,
            'momentum': 1.0,
            'trend': 1.0,
        })


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    vix = VIXCollector()
    
    print("📊 Pobieranie VIX...")
    result = vix.get_current()
    
    print(f"\nVIX: {result['value']}")
    print(f"Regime: {result['regime']}")
    print(f"Can trade: {result['can_trade']}")
    print(f"Advice: {result['advice']}")
    print(f"\nWeight adjustments:")
    for strategy, mult in result['weight_adjustments'].items():
        print(f"  {strategy}: {mult}x")
