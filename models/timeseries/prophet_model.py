"""
Facebook Prophet dla predykcji cen.
Wymaga: pip install prophet
"""
import pandas as pd
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Importuj Prophet (może nie być zainstalowany)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet nie jest zainstalowany. pip install prophet")


class ProphetForecaster:
    """
    Facebook Prophet dla predykcji trendów.
    
    Dobre dla:
    - Wykrywanie trendów długoterminowych
    - Sezonowość (dzień tygodnia, miesiąc)
    
    NIE używaj do:
    - Krótkoterminowych predykcji cen (< 1 dzień)
    - Precyzyjnych target prices
    """
    
    def __init__(self):
        self.model = None
        self.is_fitted = False
        self.last_forecast = None
    
    def fit(self, df: pd.DataFrame) -> bool:
        """
        Trenuje model Prophet.
        
        Args:
            df: DataFrame z kolumnami: date, close (lub ds, y)
        """
        if not PROPHET_AVAILABLE:
            logger.error("Prophet nie jest dostępny")
            return False
        
        try:
            # Przygotuj dane dla Prophet
            prophet_df = df.copy()
            
            # Prophet wymaga kolumn 'ds' i 'y'
            if 'ds' not in prophet_df.columns:
                if isinstance(prophet_df.index, pd.DatetimeIndex):
                    prophet_df['ds'] = prophet_df.index
                elif 'date' in prophet_df.columns:
                    prophet_df['ds'] = pd.to_datetime(prophet_df['date'])
            
            if 'y' not in prophet_df.columns:
                if 'close' in prophet_df.columns:
                    prophet_df['y'] = prophet_df['close']
                elif 'Close' in prophet_df.columns:
                    prophet_df['y'] = prophet_df['Close']
            
            prophet_df = prophet_df[['ds', 'y']].dropna()
            prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
            
            # Trenuj model
            self.model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=True,
                yearly_seasonality=True,
                changepoint_prior_scale=0.05,  # Mniej elastyczny
            )
            self.model.fit(prophet_df)
            self.is_fitted = True
            
            logger.info(f"Prophet trained on {len(prophet_df)} observations")
            return True
        
        except Exception as e:
            logger.error(f"Błąd trenowania Prophet: {e}")
            return False
    
    def predict(self, periods: int = 10) -> Optional[pd.DataFrame]:
        """
        Predykcja na N okresów.
        
        Returns:
            DataFrame z yhat, yhat_lower, yhat_upper
        """
        if not self.is_fitted or self.model is None:
            logger.error("Model nie jest wytrenowany")
            return None
        
        try:
            future = self.model.make_future_dataframe(periods=periods)
            forecast = self.model.predict(future)
            
            self.last_forecast = forecast
            return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
        
        except Exception as e:
            logger.error(f"Błąd predykcji: {e}")
            return None
    
    def generate_signal(self, df: pd.DataFrame, periods: int = 5) -> Dict:
        """
        Generuje sygnał tradingowy bazowany na predykcji.
        
        Logika:
        - Jeśli predykcja > current_price → BUY
        - Jeśli predykcja < current_price → SELL
        """
        if not PROPHET_AVAILABLE:
            return self._empty_signal("Prophet not available")
        
        if not self.is_fitted:
            if not self.fit(df):
                return self._empty_signal("Could not fit model")
        
        forecast = self.predict(periods)
        
        if forecast is None or forecast.empty:
            return self._empty_signal("No forecast")
        
        # Pobierz current price
        df_copy = df.copy()
        df_copy.columns = df_copy.columns.str.lower()
        current_price = df_copy['close'].iloc[-1]
        
        predicted_price = forecast['yhat'].iloc[-1]
        predicted_low = forecast['yhat_lower'].iloc[-1]
        predicted_high = forecast['yhat_upper'].iloc[-1]
        
        pct_change = (predicted_price - current_price) / current_price
        
        # Generuj sygnał
        if pct_change > 0.01:  # > 1% up
            signal = min(pct_change * 10, 1.0)
            direction = 'bullish'
        elif pct_change < -0.01:  # > 1% down
            signal = max(pct_change * 10, -1.0)
            direction = 'bearish'
        else:
            signal = 0.0
            direction = 'neutral'
        
        return {
            'signal': round(signal, 4),
            'confidence': 0.5,  # Prophet ma umiarkowaną pewność
            'strategy': 'prophet',
            'current_price': round(current_price, 4),
            'predicted_price': round(predicted_price, 4),
            'predicted_range': (round(predicted_low, 4), round(predicted_high, 4)),
            'pct_change': round(pct_change * 100, 2),
            'direction': direction,
            'forecast_periods': periods,
        }
    
    def _empty_signal(self, reason: str) -> Dict:
        return {
            'signal': 0.0,
            'confidence': 0.0,
            'strategy': 'prophet',
            'error': reason,
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if not PROPHET_AVAILABLE:
        print("❌ Prophet nie jest zainstalowany!")
        print("   Uruchom: pip install prophet")
        print("\n   Prophet jest opcjonalny - system działa bez niego.")
    else:
        import yfinance as yf
        
        print("📊 Pobieranie danych EUR/PLN...")
        ticker = yf.Ticker("EURPLN=X")
        df = ticker.history(period="1y")
        
        print("🤖 Trenowanie Prophet...")
        prophet = ProphetForecaster()
        signal = prophet.generate_signal(df, periods=5)
        
        print("\n📈 Prophet Forecast:")
        print(f"  Current price: {signal.get('current_price')}")
        print(f"  Predicted: {signal.get('predicted_price')}")
        print(f"  Range: {signal.get('predicted_range')}")
        print(f"  Change: {signal.get('pct_change')}%")
        print(f"  Signal: {signal.get('signal')}")
        print(f"  Direction: {signal.get('direction')}")
