"""
CryptoBERT - Model sentymentu dla kryptowalut.
Fine-tuned na Twitter + crypto news.
Ocena: 9/10
"""
from typing import Dict
import logging

from .base_hf_model import BaseHuggingFaceModel
from config.settings import MODEL_SETTINGS

logger = logging.getLogger(__name__)


class CryptoBERTSentiment(BaseHuggingFaceModel):
    """
    ElKulako/cryptobert - BERT fine-tuned na Twitter + crypto news.
    
    Zalety:
    - Crypto-native (rozumie slang, memy)
    - Dobrze działa na tweety i posty social media
    
    Wady:
    - Tendencja do overreaction - używamy dampening_factor!
    """
    
    def __init__(self):
        model_config = MODEL_SETTINGS.get("cryptobert", {})
        super().__init__(
            model_name=model_config.get("name", "ElKulako/cryptobert"),
            weight=model_config.get("weight", 0.20)
        )
        # Dampening factor - tłumi overreaction modelu
        self.dampening_factor = model_config.get("dampening_factor", 0.8)
    
    def load_model(self) -> bool:
        """Ładuje model CryptoBERT z Hugging Face."""
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
        Analizuje tekst o kryptowalutach i zwraca sygnał.
        
        Args:
            text: Tekst do analizy (tweet, news, post)
        
        Returns:
            Słownik z sygnałem tradingowym
        """
        if not self.is_loaded:
            if not self.load_model():
                return self._empty_result()
        
        try:
            # Ogranicz długość tekstu
            text = text[:500]
            
            result = self.model(text)[0]
            
            label = result['label'].lower()
            raw_score = result['score']
            
            # Dampening - tłumimy overreaction
            score = raw_score * self.dampening_factor
            
            # Konwertuj na signal
            # CryptoBERT może mieć różne labele (bullish/bearish/positive/negative)
            if 'bullish' in label or 'positive' in label:
                signal = score
            elif 'bearish' in label or 'negative' in label:
                signal = -score
            else:
                signal = 0.0
            
            return {
                'signal': round(signal, 4),
                'confidence': round(raw_score, 4),  # Oryginalne confidence
                'label': label,
                'model': 'cryptobert',
                'raw_label': result['label'],
                'dampened': True,
            }
        
        except Exception as e:
            logger.error(f"Błąd analizy CryptoBERT: {e}")
            return self._empty_result()
    
    def analyze_tweets(self, tweets: list) -> Dict:
        """
        Analizuje listę tweetów i zwraca zagregowany sygnał.
        
        Args:
            tweets: Lista tweetów o kryptowalutach
        
        Returns:
            Zagregowany sygnał
        """
        return self.get_aggregated_signal(tweets)


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    cryptobert = CryptoBERTSentiment()
    
    # Testy
    test_texts = [
        "Bitcoin to the moon! 🚀🚀🚀 #BTC #HODL",
        "Massive sell-off incoming, bears taking control",
        "Just bought more ETH, this dip is a gift",
        "Crypto is dead, another scam exposed",
        "Sideways movement, waiting for breakout",
        "Whales are accumulating, bullish signal",
    ]
    
    print("CryptoBERT Sentiment Analysis Tests:")
    print("=" * 50)
    
    for text in test_texts:
        result = cryptobert.analyze(text)
        print(f"\nText: {text[:50]}...")
        print(f"Signal: {result['signal']:.4f} (dampened)")
        print(f"Confidence: {result['confidence']:.4f}")
        print(f"Label: {result['label']}")
