"""
Wagi modeli w ensemble.
Wagi są optymalizowane na podstawie backtestingu.
"""

# Wagi modeli sentiment
SENTIMENT_MODEL_WEIGHTS = {
    "finbert": 0.25,           # Core dla Forex (EN)
    "polish_bert": 0.10,       # Pomocniczy dla PL news
    "cryptobert": 0.20,        # Core dla Crypto
}

# Wagi strategii
STRATEGY_WEIGHTS = {
    "mean_reversion": 0.20,    # Najlepsza dla EUR/PLN
    "momentum_sentiment": 0.15, # Główna dla Crypto
    "carry_trade": 0.10,       # NBP vs ECB
    "technical": 0.10,         # RSI, MACD, Bollinger
}

# Mnożniki wag bazowane na reżimie rynku
REGIME_WEIGHT_MULTIPLIERS = {
    "high_volatility": {
        # VIX > 25 - trend models mają priorytet
        "momentum_sentiment": 1.5,
        "carry_trade": 1.5,
        "mean_reversion": 0.3,
        "technical": 1.0,
        "finbert": 1.2,
        "polish_bert": 1.0,
        "cryptobert": 1.2,
    },
    "low_volatility": {
        # VIX < 15 - mean reversion ma priorytet
        "momentum_sentiment": 0.8,
        "carry_trade": 1.0,
        "mean_reversion": 1.5,
        "technical": 1.2,
        "finbert": 1.0,
        "polish_bert": 1.0,
        "cryptobert": 1.0,
    },
    "news_window": {
        # Ważne newsy w ciągu 1h - sentiment override
        "momentum_sentiment": 1.0,
        "carry_trade": 0.5,
        "mean_reversion": 0.5,
        "technical": 0.5,
        "finbert": 2.0,
        "polish_bert": 2.0,
        "cryptobert": 2.0,
    },
    "normal": {
        # Normalne warunki - domyślne wagi
        "momentum_sentiment": 1.0,
        "carry_trade": 1.0,
        "mean_reversion": 1.0,
        "technical": 1.0,
        "finbert": 1.0,
        "polish_bert": 1.0,
        "cryptobert": 1.0,
    },
}

def get_weight(model_or_strategy: str, regime: str = "normal") -> float:
    """
    Zwraca finalną wagę modelu/strategii uwzględniając reżim rynku.
    
    Args:
        model_or_strategy: Nazwa modelu lub strategii
        regime: Reżim rynku (high_volatility, low_volatility, news_window, normal)
    
    Returns:
        Finalna waga
    """
    # Znajdź bazową wagę
    if model_or_strategy in SENTIMENT_MODEL_WEIGHTS:
        base_weight = SENTIMENT_MODEL_WEIGHTS[model_or_strategy]
    elif model_or_strategy in STRATEGY_WEIGHTS:
        base_weight = STRATEGY_WEIGHTS[model_or_strategy]
    else:
        base_weight = 0.1  # Domyślna waga
    
    # Pobierz mnożnik reżimu
    regime_multipliers = REGIME_WEIGHT_MULTIPLIERS.get(regime, REGIME_WEIGHT_MULTIPLIERS["normal"])
    multiplier = regime_multipliers.get(model_or_strategy, 1.0)
    
    return base_weight * multiplier
