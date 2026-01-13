"""
Konfiguracja dla krótkoterminowego tradingu (day/swing trading).
Forex i Crypto - 1 dzień do 1 tygodnia.
"""
from enum import Enum


class TradingMode(Enum):
    """Tryb tradingu."""
    SHORT_TERM = "short_term"  # Day/Swing (1h - 1 tydzień)
    LONG_TERM = "long_term"    # Position (tygodnie - miesiące)


# ===== AKTYWNY TRYB =====
TRADING_MODE = TradingMode.SHORT_TERM


# ===== KONFIGURACJA SHORT-TERM =====
SHORT_TERM_CONFIG = {
    # Timeframe'y
    "primary_timeframe": "1h",      # Główny TF do entry/exit
    "secondary_timeframe": "4h",    # Potwierdzenie trendu
    "context_timeframe": "1d",      # Kontekst makro
    
    # Historia
    "history_bars": 500,            # Wystarczy 500 świec
    "history_days": 30,             # 30 dni danych
    
    # Holding time
    "min_holding_hours": 1,         # Min 1h trzymania
    "max_holding_hours": 120,       # Max 5 dni (120h)
    "target_holding_hours": 24,     # Idealnie 1 dzień
    
    # Trade frequency
    "max_trades_per_day": 5,        # Max 5 trade'ów dziennie
    "max_trades_per_week": 15,      # Max 15 tygodniowo
    
    # Entry thresholds (bardziej agresywne)
    "signal_threshold": 0.25,       # Niższy próg (było 0.3)
    "confidence_threshold": 0.35,   # Niższy próg confidence
}


# ===== KONFIGURACJA LONG-TERM (backup) =====
LONG_TERM_CONFIG = {
    "primary_timeframe": "1d",
    "secondary_timeframe": "1w",
    "context_timeframe": "1M",
    "history_bars": 365,
    "history_days": 730,
    "min_holding_days": 3,
    "max_holding_days": 60,
    "max_trades_per_week": 2,
    "signal_threshold": 0.35,
    "confidence_threshold": 0.45,
}


# ===== AKTYWNA KONFIGURACJA =====
TIMEFRAME_CONFIG = SHORT_TERM_CONFIG if TRADING_MODE == TradingMode.SHORT_TERM else LONG_TERM_CONFIG


# ===== SZYBSZE WSKAŹNIKI DLA SHORT-TERM =====
SHORT_TERM_INDICATORS = {
    # RSI - szybszy
    "rsi": {
        "period": 7,           # Zamiast 14
        "overbought": 75,      # Zamiast 70
        "oversold": 25,        # Zamiast 30
    },
    
    # MACD - szybszy
    "macd": {
        "fast": 8,             # Zamiast 12
        "slow": 17,            # Zamiast 26
        "signal": 9,           # Bez zmian
    },
    
    # Bollinger - krótszy okres
    "bollinger": {
        "period": 10,          # Zamiast 20
        "std": 2.0,
    },
    
    # EMA - szybsze
    "ema": {
        "fast": 8,             # Zamiast 12
        "slow": 21,            # Zamiast 26
        "trend": 50,           # Dla trendu
    },
    
    # ATR - krótszy
    "atr": {
        "period": 10,          # Zamiast 14
    },
    
    # Średnie kroczące dla kontekstu
    "sma": {
        "short": 10,
        "medium": 20,
        "long": 50,
    },
    
    # Z-score dla mean reversion
    "zscore": {
        "lookback": 14,        # Zamiast 20
    },
}


# ===== RISK MANAGEMENT - WĘŻSZE SL/TP =====
SHORT_TERM_RISK = {
    # Tighter SL/TP dla day trading
    "forex": {
        "stop_loss_pct": 0.008,       # 0.8%
        "take_profit_pct": 0.016,     # 1.6% (R:R = 1:2)
        "use_atr_stops": True,
        "atr_sl_multiplier": 1.2,     # SL = 1.2x ATR
        "atr_tp_multiplier": 2.4,     # TP = 2.4x ATR
    },
    "crypto": {
        "stop_loss_pct": 0.015,       # 1.5% (crypto ma większą vol)
        "take_profit_pct": 0.030,     # 3.0% (R:R = 1:2)
        "use_atr_stops": True,
        "atr_sl_multiplier": 1.5,
        "atr_tp_multiplier": 3.0,
    },
    
    # Trailing stop
    "use_trailing": True,
    "trailing_activation_pct": 0.01,  # Aktywuj po 1% profit
    "trailing_distance_pct": 0.005,   # Trail 0.5% za ceną
    
    # Time-based exit
    "max_trade_hours": 72,            # Max 3 dni per trade
    "friday_close_all": True,         # Zamknij Forex przed weekendem
    
    # Daily limits
    "max_daily_loss_pct": 0.03,       # Max 3% dziennej straty
    "max_daily_trades": 5,
}


# ===== WAGI MODELI DLA SHORT-TERM =====
SHORT_TERM_WEIGHTS = {
    # Forex - bardziej techniczny
    "forex": {
        "finbert": 0.20,              # Sentyment EN
        "polish_bert": 0.10,          # Sentyment PL
        "technical": 0.35,            # Wskaźniki (zwiększone!)
        "mean_reversion": 0.15,       # Z-score (zmniejszone)
        "momentum": 0.20,             # Momentum
    },
    
    # Crypto - sentiment + momentum
    "crypto": {
        "cryptobert": 0.20,           # Sentyment crypto
        "fear_greed": 0.15,           # Fear & Greed Index
        "technical": 0.30,            # Wskaźniki
        "momentum_sentiment": 0.25,   # Momentum + Sentiment
        "mean_reversion": 0.10,       # Mniej skuteczny w crypto
    },
}


# ===== DYNAMICZNE WAGI W ZALEŻNOŚCI OD KONTEKSTU =====
CONTEXT_WEIGHT_ADJUSTMENTS = {
    "trending_market": {          # ADX > 25
        "momentum": 1.5,
        "mean_reversion": 0.3,
    },
    "ranging_market": {           # ADX < 20
        "mean_reversion": 1.5,
        "momentum": 0.7,
    },
    "high_volatility": {          # VIX > 25 lub ATR > 2x średniej
        "technical": 0.5,
        "momentum": 1.3,
    },
    "news_window": {              # 1h wokół news
        "sentiment": 2.0,
        "technical": 0.5,
        "mean_reversion": 0.2,
    },
}


def get_active_config():
    """Zwraca aktywną konfigurację."""
    return {
        "mode": TRADING_MODE.value,
        "timeframes": TIMEFRAME_CONFIG,
        "indicators": SHORT_TERM_INDICATORS,
        "risk": SHORT_TERM_RISK,
        "weights": SHORT_TERM_WEIGHTS,
        "adjustments": CONTEXT_WEIGHT_ADJUSTMENTS,
    }


# Przykład użycia
if __name__ == "__main__":
    config = get_active_config()
    print(f"Trading Mode: {config['mode']}")
    print(f"Primary Timeframe: {config['timeframes']['primary_timeframe']}")
    print(f"RSI Period: {config['indicators']['rsi']['period']}")
    print(f"Forex SL: {config['risk']['forex']['stop_loss_pct']:.1%}")
