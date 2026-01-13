"""
Konfiguracja kryptowalut.
"""

# Główne kryptowaluty do śledzenia
CRYPTO_ASSETS = {
    "BTC/USDT": {
        "symbol": "BTC/USDT",
        "base": "BTC",
        "quote": "USDT",
        "description": "Bitcoin / Tether",
        "priority": 1,
        "strategies": ["momentum_sentiment", "btc_dominance"],
        "coingecko_id": "bitcoin",
    },
    "ETH/USDT": {
        "symbol": "ETH/USDT",
        "base": "ETH",
        "quote": "USDT",
        "description": "Ethereum / Tether",
        "priority": 2,
        "strategies": ["momentum_sentiment", "btc_dominance"],
        "coingecko_id": "ethereum",
    },
    "SOL/USDT": {
        "symbol": "SOL/USDT",
        "base": "SOL",
        "quote": "USDT",
        "description": "Solana / Tether",
        "priority": 3,
        "strategies": ["momentum_sentiment"],
        "coingecko_id": "solana",
    },
    "BNB/USDT": {
        "symbol": "BNB/USDT",
        "base": "BNB",
        "quote": "USDT",
        "description": "Binance Coin / Tether",
        "priority": 4,
        "strategies": ["momentum_sentiment"],
        "coingecko_id": "binancecoin",
    },
}

# Giełda do pobierania danych (ccxt)
CRYPTO_EXCHANGE = "binance"

# Timeframes do analizy
CRYPTO_TIMEFRAMES = {
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}

# Domyślny timeframe
DEFAULT_CRYPTO_TIMEFRAME = "4h"

# Ilość danych historycznych do pobrania (dni)
CRYPTO_HISTORY_DAYS = 180

# Social media keywords do śledzenia
CRYPTO_KEYWORDS = {
    "BTC": ["bitcoin", "btc", "#bitcoin", "$btc"],
    "ETH": ["ethereum", "eth", "#ethereum", "$eth"],
    "SOL": ["solana", "sol", "#solana", "$sol"],
    "BNB": ["bnb", "binance coin", "#bnb"],
}

# Fear & Greed Index API
FEAR_GREED_API_URL = "https://api.alternative.me/fng/"
