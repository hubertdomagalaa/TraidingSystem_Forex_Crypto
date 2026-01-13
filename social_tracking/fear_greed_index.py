"""
Crypto Fear & Greed Index.
Pobiera aktualny index z API i generuje sygnały tradingowe.
"""
import requests
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FearGreedIndex:
    """
    Crypto Fear & Greed Index z alternative.me
    
    Interpretacja:
    - 0-24: Extreme Fear → Rozważ akumulację (kontrariański BUY)
    - 25-44: Fear → Szukaj entry points
    - 45-55: Neutral → Brak wyraźnego sygnału
    - 56-74: Greed → Ostrożnie, rozważ take profit
    - 75-100: Extreme Greed → TAKE PROFIT! (kontrariański SELL)
    
    Strategia kontrariańska: kupuj gdy inni się boją, sprzedaj gdy są chciwi.
    """
    
    def __init__(self):
        self.api_url = "https://api.alternative.me/fng/"
        self.timeout = 10
        
        # Thresholds
        self.extreme_fear = 25
        self.fear = 45
        self.neutral_low = 45
        self.neutral_high = 55
        self.greed = 75
        self.extreme_greed = 75
    
    def get_current(self) -> Dict:
        """
        Pobiera aktualną wartość Fear & Greed Index.
        
        Returns:
            Słownik z wartością, sygnałem i interpretacją
        """
        try:
            response = requests.get(self.api_url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data or not data['data']:
                logger.error("Nieprawidłowa odpowiedź API Fear & Greed")
                return self._default_response("API Error")
            
            fng_data = data['data'][0]
            value = int(fng_data['value'])
            classification = fng_data['value_classification']
            timestamp = fng_data.get('timestamp', '')
            
            # Generuj sygnał i poradę
            signal, advice = self._interpret_value(value)
            
            return {
                'value': value,
                'signal': signal,
                'classification': classification,
                'advice': advice,
                'timestamp': timestamp,
                'fetched_at': datetime.now().isoformat(),
                'source': 'alternative.me',
            }
        
        except requests.Timeout:
            logger.error("Timeout pobierania Fear & Greed Index")
            return self._default_response("Timeout")
        
        except requests.RequestException as e:
            logger.error(f"Błąd pobierania Fear & Greed Index: {e}")
            return self._default_response(str(e))
        
        except Exception as e:
            logger.error(f"Nieoczekiwany błąd Fear & Greed: {e}")
            return self._default_response(str(e))
    
    def _interpret_value(self, value: int) -> tuple:
        """
        Interpretuje wartość i zwraca (signal, advice).
        
        Strategia kontrariańska:
        - Extreme Fear → sygnał kupna
        - Extreme Greed → sygnał sprzedaży
        """
        if value < self.extreme_fear:
            signal = 1.0  # Strong BUY signal
            advice = "🟢 EXTREME FEAR - Rozważ akumulację. Rynek jest w panice, to potencjalna okazja."
        
        elif value < self.fear:
            signal = 0.5  # Moderate BUY signal
            advice = "🟡 FEAR - Szukaj dobrych entry points. Sentyment negatywny ale nie ekstremalny."
        
        elif value < self.neutral_high:
            signal = 0.0  # Neutral
            advice = "⚪ NEUTRAL - Brak wyraźnego sygnału. Market w równowadze."
        
        elif value < self.greed:
            signal = -0.5  # Moderate SELL signal
            advice = "🟡 GREED - Ostrożnie. Rozważ częściowy take profit lub trzymaj stopy."
        
        else:
            signal = -1.0  # Strong SELL signal
            advice = "🔴 EXTREME GREED - TAKE PROFIT! Rynek zbyt optymistyczny, korekta możliwa."
        
        return signal, advice
    
    def _default_response(self, error: str) -> Dict:
        """Zwraca domyślną odpowiedź w przypadku błędu."""
        return {
            'value': 50,  # Zakładamy neutral
            'signal': 0.0,
            'classification': 'neutral',
            'advice': f'Błąd pobierania danych: {error}. Zakładam neutral.',
            'error': error,
            'fetched_at': datetime.now().isoformat(),
        }
    
    def get_historical(self, days: int = 7) -> Optional[Dict]:
        """
        Pobiera historyczne wartości Fear & Greed.
        
        Args:
            days: Liczba dni wstecz
        """
        try:
            response = requests.get(
                f"{self.api_url}?limit={days}",
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if 'data' not in data:
                return None
            
            historical = []
            for item in data['data']:
                historical.append({
                    'value': int(item['value']),
                    'classification': item['value_classification'],
                    'timestamp': item.get('timestamp', ''),
                })
            
            return {
                'data': historical,
                'count': len(historical),
                'average': sum(h['value'] for h in historical) / len(historical) if historical else 50,
            }
        
        except Exception as e:
            logger.error(f"Błąd pobierania historii Fear & Greed: {e}")
            return None
    
    def get_trend(self, days: int = 7) -> Dict:
        """
        Analizuje trend Fear & Greed (rosnący/malejący).
        """
        historical = self.get_historical(days)
        
        if not historical or not historical['data']:
            return {'trend': 'unknown', 'change': 0}
        
        values = [h['value'] for h in historical['data']]
        
        if len(values) < 2:
            return {'trend': 'unknown', 'change': 0}
        
        # Najnowsza wartość jest pierwsza w liście
        latest = values[0]
        oldest = values[-1]
        change = latest - oldest
        
        if change > 10:
            trend = 'rising'  # Sentiment poprawia się
        elif change < -10:
            trend = 'falling'  # Sentiment pogarsza się
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'change': change,
            'current': latest,
            'week_ago': oldest,
        }
    
    def generate_signal(self) -> Dict:
        """
        Generuje sygnał w formacie kompatybilnym z SignalAggregator.
        """
        current = self.get_current()
        
        return {
            'signal': current['signal'],
            'confidence': abs(current['signal']) * 0.7,  # Skaluj confidence
            'strategy': 'fear_greed',
            'value': current['value'],
            'classification': current['classification'],
            'advice': current['advice'],
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    fng = FearGreedIndex()
    
    print("Crypto Fear & Greed Index")
    print("=" * 50)
    
    # Pobierz aktualny index
    current = fng.get_current()
    print(f"\n📊 Aktualna wartość: {current['value']}")
    print(f"📈 Klasyfikacja: {current['classification']}")
    print(f"🎯 Sygnał: {current['signal']:.2f}")
    print(f"💡 {current['advice']}")
    
    # Pobierz trend
    trend = fng.get_trend(7)
    print(f"\n📉 Trend 7-dniowy: {trend['trend']}")
    print(f"   Zmiana: {trend['change']:+d}")
    
    # Generuj sygnał dla agregatora
    signal = fng.generate_signal()
    print(f"\n🔔 Sygnał dla agregatora:")
    print(f"   Signal: {signal['signal']:.4f}")
    print(f"   Confidence: {signal['confidence']:.4f}")
