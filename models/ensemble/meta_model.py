"""
XGBoost Meta-Model.
Uczy się które modele są najlepsze w jakich warunkach.
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging
import pickle
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost nie jest zainstalowany. pip install xgboost")


class MetaModel:
    """
    XGBoost meta-learner.
    
    Uczy się optymalne wagi dla modeli bazując na:
    - Sygnałach z każdego modelu
    - VIX, Fear & Greed, volatility
    - Historycznych wynikach
    
    Cel: Przewidzieć które modele będą najlepsze w danych warunkach.
    """
    
    # Domyślne wagi (gdy model nie jest wytrenowany)
    DEFAULT_WEIGHTS = {
        'finbert': 0.25,
        'cryptobert': 0.20,
        'polish_bert': 0.10,
        'technical': 0.10,
        'mean_reversion': 0.20,
        'momentum_sentiment': 0.15,
    }
    
    def __init__(self, model_path: str = None):
        self.model = None
        self.is_fitted = False
        
        if model_path:
            self.model_path = Path(model_path)
        else:
            self.model_path = Path(__file__).parent / "meta_model.pkl"
        
        self.feature_names = [
            'finbert_signal', 'cryptobert_signal', 'polishbert_signal',
            'technical_signal', 'mean_reversion_signal', 'momentum_signal',
            'vix', 'fear_greed', 'volatility', 'trend_strength',
        ]
        
        # Spróbuj załadować istniejący model
        self.load()
    
    def prepare_features(
        self,
        signals: Dict[str, float],
        market_context: Dict
    ) -> np.ndarray:
        """Przygotowuje features dla meta-modelu."""
        features = [
            signals.get('finbert', 0),
            signals.get('cryptobert', 0),
            signals.get('polish_bert', 0),
            signals.get('technical', 0),
            signals.get('mean_reversion', 0),
            signals.get('momentum_sentiment', 0),
            market_context.get('vix', 20),
            market_context.get('fear_greed', 50),
            market_context.get('volatility', 0.02),
            market_context.get('trend_strength', 0.5),
        ]
        return np.array(features).reshape(1, -1)
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> bool:
        """
        Trenuje meta-model.
        
        Args:
            X: Features (sygnały + kontekst), shape (n_samples, 10)
            y: Labels (1 = profitable trade, 0 = not profitable)
        
        Returns:
            True jeśli sukces
        """
        if not XGBOOST_AVAILABLE:
            logger.error("XGBoost niedostępny")
            return False
        
        try:
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                objective='binary:logistic',
                random_state=42,
                use_label_encoder=False,
                eval_metric='logloss',
            )
            self.model.fit(X, y)
            self.is_fitted = True
            
            # Zapisz model
            self.save()
            
            logger.info("Meta-model trained successfully")
            return True
        
        except Exception as e:
            logger.error(f"Błąd trenowania meta-modelu: {e}")
            return False
    
    def predict_profitability(
        self,
        signals: Dict[str, float],
        market_context: Dict
    ) -> float:
        """
        Przewiduje prawdopodobieństwo zyskownej transakcji.
        
        Returns:
            Prawdopodobieństwo 0-1
        """
        if not self.is_fitted or self.model is None:
            return 0.5  # Domyślnie 50%
        
        try:
            X = self.prepare_features(signals, market_context)
            proba = self.model.predict_proba(X)[0, 1]
            return float(proba)
        except Exception as e:
            logger.error(f"Błąd predykcji: {e}")
            return 0.5
    
    def predict_optimal_weights(
        self,
        signals: Dict[str, float],
        market_context: Dict
    ) -> Dict[str, float]:
        """
        Przewiduje optymalne wagi dla modeli.
        
        Jeśli model nie jest wytrenowany, używa domyślnych wag.
        
        Returns:
            Dict z wagami dla każdego modelu
        """
        if not self.is_fitted or self.model is None:
            return self.DEFAULT_WEIGHTS.copy()
        
        try:
            # Pobierz feature importance jako wagi
            importance = self.model.feature_importances_
            
            # Mapuj na modele (pierwsze 6 features to sygnały)
            model_importance = importance[:6]
            
            # Normalize
            total = model_importance.sum()
            if total > 0:
                normalized = model_importance / total
            else:
                return self.DEFAULT_WEIGHTS.copy()
            
            return {
                'finbert': float(normalized[0]),
                'cryptobert': float(normalized[1]),
                'polish_bert': float(normalized[2]),
                'technical': float(normalized[3]),
                'mean_reversion': float(normalized[4]),
                'momentum_sentiment': float(normalized[5]),
            }
        
        except Exception as e:
            logger.error(f"Błąd predykcji wag: {e}")
            return self.DEFAULT_WEIGHTS.copy()
    
    def get_adjusted_signal(
        self,
        signals: Dict[str, float],
        market_context: Dict
    ) -> Dict:
        """
        Zwraca zagregowany sygnał z optymalnymi wagami.
        
        Returns:
            Dict z sygnałem, confidence i wagami
        """
        weights = self.predict_optimal_weights(signals, market_context)
        profitability = self.predict_profitability(signals, market_context)
        
        # Oblicz ważony sygnał
        weighted_signal = 0
        total_weight = 0
        
        for model_name, weight in weights.items():
            if model_name in signals:
                weighted_signal += signals[model_name] * weight
                total_weight += weight
        
        if total_weight > 0:
            final_signal = weighted_signal / total_weight
        else:
            final_signal = 0
        
        return {
            'signal': round(final_signal, 4),
            'confidence': round(profitability, 4),
            'weights': weights,
            'strategy': 'meta_model',
            'model_fitted': self.is_fitted,
        }
    
    def save(self):
        """Zapisuje model do pliku."""
        if self.model is not None:
            try:
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                logger.info(f"Model saved to {self.model_path}")
            except Exception as e:
                logger.error(f"Błąd zapisywania modelu: {e}")
    
    def load(self) -> bool:
        """Ładuje model z pliku."""
        if self.model_path.exists():
            try:
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                self.is_fitted = True
                logger.info("Meta-model loaded")
                return True
            except Exception as e:
                logger.error(f"Błąd ładowania modelu: {e}")
        return False
    
    def train_from_backtest(self, backtest_results: List[Dict]) -> bool:
        """
        Trenuje model na podstawie wyników backtestingu.
        
        Args:
            backtest_results: Lista słowników z:
                - signals: Dict z sygnałami modeli
                - market_context: Dict z VIX, fear_greed, etc.
                - profitable: bool (czy trade był zyskowny)
        
        Returns:
            True jeśli sukces
        """
        if not backtest_results:
            logger.warning("Brak danych do treningu")
            return False
        
        X_list = []
        y_list = []
        
        for result in backtest_results:
            features = self.prepare_features(
                result.get('signals', {}),
                result.get('market_context', {})
            )
            X_list.append(features.flatten())
            y_list.append(1 if result.get('profitable', False) else 0)
        
        X = np.array(X_list)
        y = np.array(y_list)
        
        return self.fit(X, y)


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if not XGBOOST_AVAILABLE:
        print("❌ XGBoost nie jest zainstalowany!")
        print("   Uruchom: pip install xgboost")
        print("\n   XGBoost jest opcjonalny - system używa domyślnych wag.")
    
    meta = MetaModel()
    
    # Przykładowe sygnały
    signals = {
        'finbert': 0.6,
        'cryptobert': 0.4,
        'polish_bert': 0.3,
        'technical': 0.2,
        'mean_reversion': -0.1,
        'momentum_sentiment': 0.5,
    }
    
    market_context = {
        'vix': 18,
        'fear_greed': 45,
        'volatility': 0.02,
        'trend_strength': 0.6,
    }
    
    print("\n📊 Meta-Model Analysis:")
    print(f"  Model fitted: {meta.is_fitted}")
    
    result = meta.get_adjusted_signal(signals, market_context)
    print(f"\n  Adjusted signal: {result['signal']}")
    print(f"  Confidence: {result['confidence']}")
    print(f"\n  Optimal weights:")
    for model, weight in result['weights'].items():
        print(f"    {model}: {weight:.2%}")
