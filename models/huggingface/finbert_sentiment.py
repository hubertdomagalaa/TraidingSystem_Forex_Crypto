"""
FinBERT - Model sentymentu finansowego.
Główny model dla analizy newsów Forex.
Ocena: 9/10
"""
from typing import Dict
import logging

from .base_hf_model import BaseHuggingFaceModel
from config.settings import MODEL_SETTINGS

logger = logging.getLogger(__name__)


class FinBERTSentiment(BaseHuggingFaceModel):
    """
    ProsusAI/finbert - główny model sentymentu finansowego.
    
    Użycie: 
    - Newsy makro (ECB, Fed, inflacja)
    - Earnings reports
    - Komunikaty banków centralnych
    
    Wyjście: positive/negative/neutral + confidence
    
    UWAGA: Model tylko dla języka angielskiego!
    """
    
    def __init__(self):
        model_config = MODEL_SETTINGS.get("finbert", {})
        super().__init__(
            model_name=model_config.get("name", "ProsusAI/finbert"),
            weight=model_config.get("weight", 0.25)
        )
    
    def load_model(self) -> bool:
        """Ładuje model FinBERT z Hugging Face."""
        try:
            from transformers import pipeline
            
            logger.info(f"Ładowanie modelu {self.model_name}...")
            self.model = pipeline(
                "sentiment-analysis",
                model=self.model_name
            )
            self.is_loaded = True
            logger.info(f"Model {self.model_name} załadowany pomyślnie")
            return True
        
        except Exception as e:
            logger.error(f"Błąd ładowania modelu {self.model_name}: {e}")
            self.is_loaded = False
            return False
    
    def analyze(self, text: str) -> Dict:
        """
        Analizuje tekst finansowy i zwraca sygnał.
        
        Args:
            text: Tekst do analizy (EN)
        
        Returns:
            Słownik z sygnałem tradingowym
        """
        if not self.is_loaded:
            if not self.load_model():
                return self._empty_result()
        
        try:
            # Ogranicz długość tekstu (max 512 tokenów)
            text = text[:1500]  # Przybliżenie dla bezpieczeństwa
            
            result = self.model(text)[0]
            
            label = result['label'].lower()
            score = result['score']
            
            # Konwertuj na signal: -1 (sell) do +1 (buy)
            if label == 'positive':
                signal = score
            elif label == 'negative':
                signal = -score
            else:  # neutral
                signal = 0.0
            
            return {
                'signal': round(signal, 4),
                'confidence': round(score, 4),
                'label': label,
                'model': 'finbert',
                'raw_label': result['label'],
            }
        
        except Exception as e:
            logger.error(f"Błąd analizy FinBERT: {e}")
            return self._empty_result()


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    finbert = FinBERTSentiment()
    
    # Testy
    test_texts = [
        "ECB signals prolonged higher interest rates to combat inflation",
        "Stock market crashes as recession fears grow",
        "Quarterly earnings exceed analyst expectations",
        "Central bank announces rate cut amid economic slowdown",
        "Currency remains stable with low volatility",
    ]
    
    print("FinBERT Sentiment Analysis Tests:")
    print("=" * 50)
    
    for text in test_texts:
        result = finbert.analyze(text)
        print(f"\nText: {text[:60]}...")
        print(f"Signal: {result['signal']:.4f}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Label: {result['label']}")
