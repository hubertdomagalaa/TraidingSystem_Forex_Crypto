"""
Konfiguracja par walutowych Forex.
"""

# Główne pary do śledzenia
FOREX_PAIRS = {
    "EUR/PLN": {
        "symbol": "EURPLN=X",      # Yahoo Finance symbol
        "base": "EUR",
        "quote": "PLN",
        "description": "Euro / Polski Złoty",
        "priority": 1,              # Priorytet (1 = najwyższy)
        "strategies": ["mean_reversion", "carry_trade", "news_trading"],
    },
    "EUR/USD": {
        "symbol": "EURUSD=X",
        "base": "EUR",
        "quote": "USD",
        "description": "Euro / US Dollar",
        "priority": 2,
        "strategies": ["mean_reversion", "carry_trade"],
    },
    "USD/PLN": {
        "symbol": "USDPLN=X",
        "base": "USD",
        "quote": "PLN",
        "description": "US Dollar / Polski Złoty",
        "priority": 3,
        "strategies": ["mean_reversion", "carry_trade"],
    },
    "GBP/USD": {
        "symbol": "GBPUSD=X",
        "base": "GBP",
        "quote": "USD",
        "description": "British Pound / US Dollar",
        "priority": 4,
        "strategies": ["mean_reversion"],
    },
}

# Timeframes do analizy
FOREX_TIMEFRAMES = {
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1w": "1wk",
}

# Domyślny timeframe
DEFAULT_FOREX_TIMEFRAME = "1d"

# Ilość danych historycznych do pobrania (dni)
FOREX_HISTORY_DAYS = 365

# Stopy procentowe banków centralnych (aktualizuj ręcznie lub pobieraj z API)
CENTRAL_BANK_RATES = {
    "NBP": 5.75,   # Narodowy Bank Polski (aktualizuj!)
    "ECB": 4.50,   # European Central Bank (aktualizuj!)
    "FED": 5.50,   # Federal Reserve (aktualizuj!)
    "BOE": 5.25,   # Bank of England (aktualizuj!)
}
