"""
Konfiguracja globalna systemu tradingowego.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe
load_dotenv()

# Ścieżki
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "storage"
LOGS_DIR = PROJECT_ROOT / "logs"

# Utwórz katalogi jeśli nie istnieją
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# API Keys
FRED_API_KEY = os.getenv("FRED_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/trading.db")

# Ustawienia modeli
MODEL_SETTINGS = {
    "finbert": {
        "name": "ProsusAI/finbert",
        "weight": 0.25,
        "enabled": True,
    },
    "polish_bert": {
        "name": "mrm8488/bert-base-polish-cased-sentiment",
        "weight": 0.10,
        "enabled": True,
    },
    "cryptobert": {
        "name": "ElKulako/cryptobert",
        "weight": 0.20,
        "dampening_factor": 0.8,  # Tłumi overreaction
        "enabled": True,
    },
}

# Ustawienia strategii
STRATEGY_SETTINGS = {
    "mean_reversion": {
        "weight": 0.20,
        "lookback": 20,
        "entry_zscore": 2.0,
        "exit_zscore": 0.5,
        "enabled": True,
    },
    "momentum_sentiment": {
        "weight": 0.15,
        "enabled": True,
    },
    "carry_trade": {
        "weight": 0.10,
        "min_rate_diff": 0.5,  # Minimum 50bps różnicy
        "enabled": True,
    },
    "technical": {
        "weight": 0.10,
        "enabled": True,
    },
}

# Ustawienia ryzyka
RISK_SETTINGS = {
    "max_vix_for_trading": 30,      # Nie handluj gdy VIX > 30
    "high_volatility_vix": 25,       # VIX > 25 = wysoka zmienność
    "low_volatility_vix": 15,        # VIX < 15 = niska zmienność
    "signal_threshold_buy": 0.3,     # Score > 0.3 = BUY
    "signal_threshold_sell": -0.3,   # Score < -0.3 = SELL
}

# Fear & Greed Index thresholds
FEAR_GREED_THRESHOLDS = {
    "extreme_fear": 25,
    "fear": 45,
    "neutral_low": 45,
    "neutral_high": 55,
    "greed": 75,
    "extreme_greed": 75,
}

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
