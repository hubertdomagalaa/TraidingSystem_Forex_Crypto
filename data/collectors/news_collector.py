"""
Automatyczny kolektor newsów finansowych z RSS feeds.
Nie wymaga API key - używa publicznych RSS.
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Importuj feedparser
try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser nie jest zainstalowany. pip install feedparser")


@dataclass
class NewsItem:
    """Pojedynczy news."""
    title: str
    summary: str
    source: str
    url: str
    published: datetime
    category: str  # 'forex', 'crypto', 'macro', 'polish'


class NewsCollector:
    """
    Pobiera newsy z publicznych RSS feeds.
    
    Źródła:
    - Forex: ForexLive, FXStreet, DailyFX
    - Crypto: CoinTelegraph, CoinDesk, Decrypt
    - Macro: Reuters, MarketWatch
    - Polish: Bankier.pl, Money.pl
    """
    
    # RSS Feeds - publiczne, bez API
    FOREX_FEEDS = [
        ("ForexLive", "https://www.forexlive.com/feed/"),
        ("FXStreet", "https://www.fxstreet.com/rss/news"),
        ("Investing", "https://www.investing.com/rss/news.rss"),
    ]
    
    CRYPTO_FEEDS = [
        ("CoinTelegraph", "https://cointelegraph.com/rss"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Decrypt", "https://decrypt.co/feed"),
        ("CryptoSlate", "https://cryptoslate.com/feed/"),
    ]
    
    MACRO_FEEDS = [
        ("MarketWatch", "https://www.marketwatch.com/rss/topstories"),
        ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ]
    
    POLISH_FEEDS = [
        ("Bankier", "https://www.bankier.pl/rss/wiadomosci.xml"),
        ("Money.pl", "https://www.money.pl/rss/rss.xml"),
        ("StockWatch", "https://stooq.pl/rss/"),
    ]
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.cache: Dict[str, List[NewsItem]] = {}
        self.last_fetch: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=15)
        
        if not FEEDPARSER_AVAILABLE:
            logger.error("feedparser niedostępny - NewsCollector nie będzie działać")
    
    def fetch_feed(self, url: str, source: str, category: str) -> List[NewsItem]:
        """Pobiera newsy z pojedynczego RSS feed."""
        if not FEEDPARSER_AVAILABLE:
            return []
        
        try:
            feed = feedparser.parse(url)
            news_items = []
            
            for entry in feed.entries[:10]:  # Max 10 z każdego źródła
                # Parsuj datę
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                # Wyciągnij summary
                summary = ""
                if hasattr(entry, 'summary'):
                    summary = self._clean_html(entry.summary)[:500]
                elif hasattr(entry, 'description'):
                    summary = self._clean_html(entry.description)[:500]
                
                news_items.append(NewsItem(
                    title=entry.get('title', ''),
                    summary=summary,
                    source=source,
                    url=entry.get('link', ''),
                    published=published,
                    category=category,
                ))
            
            logger.debug(f"Pobrano {len(news_items)} newsów z {source}")
            return news_items
        
        except Exception as e:
            logger.warning(f"Błąd pobierania {source}: {e}")
            return []
    
    def _clean_html(self, text: str) -> str:
        """Usuwa tagi HTML."""
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()
        return clean
    
    def get_forex_news(self, max_age_hours: int = 24) -> List[NewsItem]:
        """Pobiera najnowsze newsy Forex."""
        cache_key = 'forex'
        
        # Sprawdź cache
        if self._is_cache_valid(cache_key):
            return self._filter_by_age(self.cache[cache_key], max_age_hours)
        
        # Pobierz ze wszystkich źródeł
        all_news = []
        for source, url in self.FOREX_FEEDS:
            all_news.extend(self.fetch_feed(url, source, 'forex'))
        
        # Sortuj po dacie (najnowsze pierwsze)
        all_news.sort(key=lambda x: x.published, reverse=True)
        
        # Cache
        self.cache[cache_key] = all_news
        self.last_fetch[cache_key] = datetime.now()
        
        logger.info(f"Pobrano {len(all_news)} newsów Forex")
        return self._filter_by_age(all_news, max_age_hours)
    
    def get_crypto_news(self, max_age_hours: int = 24) -> List[NewsItem]:
        """Pobiera najnowsze newsy Crypto."""
        cache_key = 'crypto'
        
        if self._is_cache_valid(cache_key):
            return self._filter_by_age(self.cache[cache_key], max_age_hours)
        
        all_news = []
        for source, url in self.CRYPTO_FEEDS:
            all_news.extend(self.fetch_feed(url, source, 'crypto'))
        
        all_news.sort(key=lambda x: x.published, reverse=True)
        
        self.cache[cache_key] = all_news
        self.last_fetch[cache_key] = datetime.now()
        
        logger.info(f"Pobrano {len(all_news)} newsów Crypto")
        return self._filter_by_age(all_news, max_age_hours)
    
    def get_polish_news(self, max_age_hours: int = 24) -> List[NewsItem]:
        """Pobiera polskie newsy ekonomiczne."""
        cache_key = 'polish'
        
        if self._is_cache_valid(cache_key):
            return self._filter_by_age(self.cache[cache_key], max_age_hours)
        
        all_news = []
        for source, url in self.POLISH_FEEDS:
            all_news.extend(self.fetch_feed(url, source, 'polish'))
        
        all_news.sort(key=lambda x: x.published, reverse=True)
        
        self.cache[cache_key] = all_news
        self.last_fetch[cache_key] = datetime.now()
        
        logger.info(f"Pobrano {len(all_news)} newsów polskich")
        return self._filter_by_age(all_news, max_age_hours)
    
    def get_all_news(self, max_age_hours: int = 12) -> Dict[str, List[NewsItem]]:
        """Pobiera wszystkie newsy."""
        return {
            'forex': self.get_forex_news(max_age_hours),
            'crypto': self.get_crypto_news(max_age_hours),
            'polish': self.get_polish_news(max_age_hours),
        }
    
    def get_news_texts_for_analysis(self, category: str = 'forex', limit: int = 10) -> List[str]:
        """
        Zwraca listę tekstów (title + summary) do analizy sentiment.
        Format gotowy do wrzucenia do FinBERT/CryptoBERT.
        """
        if category == 'forex':
            news = self.get_forex_news()
        elif category == 'crypto':
            news = self.get_crypto_news()
        elif category == 'polish':
            news = self.get_polish_news()
        else:
            news = []
        
        texts = []
        for item in news[:limit]:
            text = f"{item.title}. {item.summary}"
            texts.append(text)
        
        return texts
    
    def _is_cache_valid(self, key: str) -> bool:
        """Sprawdza czy cache jest aktualny."""
        if key not in self.last_fetch:
            return False
        return datetime.now() - self.last_fetch[key] < self.cache_duration
    
    def _filter_by_age(self, news: List[NewsItem], max_hours: int) -> List[NewsItem]:
        """Filtruje newsy starsze niż max_hours."""
        cutoff = datetime.now() - timedelta(hours=max_hours)
        return [n for n in news if n.published > cutoff]
    
    def get_summary(self) -> Dict:
        """Zwraca podsumowanie dostępnych newsów."""
        all_news = self.get_all_news(max_age_hours=24)
        
        return {
            'forex_count': len(all_news['forex']),
            'crypto_count': len(all_news['crypto']),
            'polish_count': len(all_news['polish']),
            'total': sum(len(v) for v in all_news.values()),
            'last_fetch': datetime.now().isoformat(),
        }


# Przykład użycia
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if not FEEDPARSER_AVAILABLE:
        print("❌ feedparser nie jest zainstalowany!")
        print("   Uruchom: pip install feedparser")
    else:
        collector = NewsCollector()
        
        print("📰 Fetching Forex news...")
        forex_news = collector.get_forex_news(max_age_hours=24)
        print(f"   Found {len(forex_news)} items")
        for news in forex_news[:3]:
            print(f"   [{news.source}] {news.title[:60]}...")
        
        print("\n🪙 Fetching Crypto news...")
        crypto_news = collector.get_crypto_news(max_age_hours=24)
        print(f"   Found {len(crypto_news)} items")
        
        print("\n🇵🇱 Fetching Polish news...")
        polish_news = collector.get_polish_news(max_age_hours=24)
        print(f"   Found {len(polish_news)} items")
        
        # Teksty do analizy
        print("\n📝 Texts for FinBERT analysis:")
        texts = collector.get_news_texts_for_analysis('forex', limit=3)
        for t in texts:
            print(f"   - {t[:80]}...")
