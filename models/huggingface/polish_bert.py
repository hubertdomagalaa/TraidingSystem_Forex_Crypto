"""
Polish BERT - Model sentymentu dla języka polskiego.
Używany do analizy newsów NBP, PAP i polskich portali finansowych.
Ocena: 7/10 (dobry jako sygnał pomocniczy)
"""
from typing import Dict
import logging

from .base_hf_model import BaseHuggingFaceModel
from config.settings import MODEL_SETTINGS

logger = logging.getLogger(__name__)


class PolishBERTSentiment(BaseHuggingFaceModel):
    """
    mrm8488/bert-base-polish-cased-sentiment
    
    Użycie:
    - Komunikaty NBP
    - Newsy PAP
    - Polskie portale finansowe (money.pl, bankier.pl)
    
    UWAGA: Nie jest stricte finansowy, ale dobrze działa na ogólny sentiment PL.
    """
    
    def __init__(self):
        model_config = MODEL_SETTINGS.get("polish_bert", {})
        super().__init__(
            model_name=model_config.get("name", "mrm8488/bert-base-polish-cased-sentiment"),
            weight=model_config.get("weight", 0.10)
        )
    
    def load_model(self) -> bool:
        """Ładuje model Polish BERT z Hugging Face."""
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
        Analizuje tekst w języku polskim i zwraca sygnał.
        
        Args:
            text: Tekst do analizy (PL)
        
        Returns:
            Słownik z sygnałem tradingowym
        """
        if not self.is_loaded:
            if not self.load_model():
                return self._empty_result()
        
        try:
            # Ogranicz długość tekstu
            text = text[:1500]
            
            result = self.model(text)[0]
            
            label = result['label'].upper()
            score = result['score']
            
            # Mapowanie na signal
            label_map = {
                'POSITIVE': 1,
                'NEGATIVE': -1,
                'NEUTRAL': 0,
                'LABEL_0': -1,  # Niektóre modele używają numerycznych labeli
                'LABEL_1': 0,
                'LABEL_2': 1,
            }
            
            signal_direction = label_map.get(label, 0)
            signal = signal_direction * score
            
            # Normalizuj label
            if signal > 0:
                normalized_label = 'positive'
            elif signal < 0:
                normalized_label = 'negative'
            else:
                normalized_label = 'neutral'
            
            return {
                'signal': round(signal, 4),
                'confidence': round(score, 4),
                'label': normalized_label,
                'model': 'polish_bert',
                'raw_label': result['label'],
                'language': 'pl',
            }
        
        except Exception as e:
            logger.error(f"Błąd analizy Polish BERT: {e}")
            return self._empty_result()


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    polish_bert = PolishBERTSentiment()
    
    # Testy
    test_texts = [
        "NBP utrzymuje stopy procentowe bez zmian",
        "Inflacja w Polsce spada szybciej niż oczekiwano",
        "Gospodarka polska rozwija się dynamicznie",
        "Kryzys na rynku nieruchomości pogłębia się",
        "Złoty umacnia się względem euro",
        "Eksperci ostrzegają przed recesją",
    ]
    
    print("Polish BERT Sentiment Analysis Tests:")
    print("=" * 50)
    
    for text in test_texts:
        result = polish_bert.analyze(text)
        print(f"\nText: {text[:50]}...")
        print(f"Signal: {result['signal']:.4f}")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Label: {result['label']}")
