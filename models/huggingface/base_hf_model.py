"""
Bazowa klasa dla modeli Hugging Face.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseHuggingFaceModel(ABC):
    """
    Abstrakcyjna klasa bazowa dla wszystkich modeli sentiment z Hugging Face.
    """
    
    def __init__(self, model_name: str, weight: float = 1.0):
        """
        Args:
            model_name: Nazwa modelu na Hugging Face Hub
            weight: Waga modelu w ensemble (0-1)
        """
        self.model_name = model_name
        self.weight = weight
        self.model = None
        self.is_loaded = False
    
    @abstractmethod
    def load_model(self) -> bool:
        """
        Ładuje model z Hugging Face.
        
        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        pass
    
    @abstractmethod
    def analyze(self, text: str) -> Dict:
        """
        Analizuje tekst i zwraca sygnał.
        
        Args:
            text: Tekst do analizy
        
        Returns:
            Słownik z kluczami:
            - signal: float od -1 (bearish) do +1 (bullish)
            - confidence: float od 0 do 1
            - label: str (positive/negative/neutral)
            - model: str (nazwa modelu)
        """
        pass
    
    def analyze_batch(self, texts: List[str]) -> List[Dict]:
        """
        Analizuje wiele tekstów.
        
        Args:
            texts: Lista tekstów do analizy
        
        Returns:
            Lista wyników analizy
        """
        results = []
        for text in texts:
            try:
                result = self.analyze(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Błąd analizy tekstu: {e}")
                results.append(self._empty_result())
        return results
    
    def get_aggregated_signal(self, texts: List[str]) -> Dict:
        """
        Analizuje wiele tekstów i agreguje wyniki.
        
        Args:
            texts: Lista tekstów
        
        Returns:
            Zagregowany sygnał
        """
        if not texts:
            return self._empty_result()
        
        results = self.analyze_batch(texts)
        
        # Średnia ważona confidence
        total_confidence = sum(r['confidence'] for r in results)
        if total_confidence == 0:
            return self._empty_result()
        
        weighted_signal = sum(
            r['signal'] * r['confidence'] 
            for r in results
        ) / total_confidence
        
        avg_confidence = total_confidence / len(results)
        
        # Określ label
        if weighted_signal > 0.1:
            label = 'positive'
        elif weighted_signal < -0.1:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {
            'signal': weighted_signal,
            'confidence': avg_confidence,
            'label': label,
            'model': self.model_name,
            'texts_analyzed': len(texts),
        }
    
    def _empty_result(self) -> Dict:
        """Zwraca pusty wynik w przypadku błędu."""
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'label': 'neutral',
            'model': self.model_name,
        }
    
    def __repr__(self):
        return f"{self.__class__.__name__}(model='{self.model_name}', loaded={self.is_loaded})"
