"""
Data collectors package initialization.
"""
from .forex_collector import ForexCollector
from .crypto_collector import CryptoCollector
from .news_collector import NewsCollector, NewsItem, FEEDPARSER_AVAILABLE
from .vix_collector import VIXCollector
from .calendar_collector import CalendarCollector, EconomicEvent
from .crypto_collector import CryptoCollector
