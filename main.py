"""
Trading Decision System - Main Entry Point
System Wspomagania Decyzji Tradingowych

Ten system:
1. Pobiera dane z rynków (Forex, Crypto)
2. Analizuje je za pomocą modeli ML (FinBERT, CryptoBERT, Polish BERT)
3. Agreguje sygnały z różnych źródeł
4. Eksportuje wyniki do JSON dla analizy przez LLM (AntiGravity)

UWAGA: System NIE wykonuje automatycznie transakcji!
       Użytkownik ręcznie handluje na XTB/Bybit.
"""
import sys
import logging
from datetime import datetime
from pathlib import Path

# Dodaj katalog projektu do ścieżki
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import LOG_LEVEL, LOG_FORMAT, LOGS_DIR
from data.collectors import ForexCollector, CryptoCollector
from models.huggingface import FinBERTSentiment, CryptoBERTSentiment, PolishBERTSentiment
from aggregator import SignalAggregator, ConflictResolver
from output import JSONExporter

# Konfiguracja logowania
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=LOG_FORMAT,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOGS_DIR / f"trading_{datetime.now().strftime('%Y%m%d')}.log")
    ]
)
logger = logging.getLogger(__name__)


class TradingSystem:
    """
    Główna klasa systemu tradingowego.
    Koordynuje wszystkie komponenty.
    """
    
    def __init__(self, load_models: bool = True):
        """
        Inicjalizuje system tradingowy.
        
        Args:
            load_models: Czy załadować modele ML przy starcie
        """
        logger.info("=" * 60)
        logger.info("Inicjalizacja Trading Decision System")
        logger.info("=" * 60)
        
        # Data collectors
        logger.info("Inicjalizacja data collectors...")
        self.forex_collector = ForexCollector()
        self.crypto_collector = CryptoCollector()
        
        # ML Models
        self.finbert = None
        self.cryptobert = None
        self.polish_bert = None
        
        if load_models:
            self._load_models()
        
        # Aggregator & Resolver
        self.aggregator = SignalAggregator()
        self.conflict_resolver = ConflictResolver()
        
        # Output
        self.exporter = JSONExporter()
        
        logger.info("System zainicjalizowany pomyślnie!")
    
    def _load_models(self):
        """Ładuje modele ML."""
        logger.info("Ładowanie modeli ML...")
        
        try:
            self.finbert = FinBERTSentiment()
            self.finbert.load_model()
        except Exception as e:
            logger.warning(f"Nie udało się załadować FinBERT: {e}")
        
        try:
            self.cryptobert = CryptoBERTSentiment()
            self.cryptobert.load_model()
        except Exception as e:
            logger.warning(f"Nie udało się załadować CryptoBERT: {e}")
        
        try:
            self.polish_bert = PolishBERTSentiment()
            self.polish_bert.load_model()
        except Exception as e:
            logger.warning(f"Nie udało się załadować Polish BERT: {e}")
    
    def get_forex_data(self, pair: str = "EUR/PLN"):
        """Pobiera dane dla pary Forex."""
        logger.info(f"Pobieranie danych dla {pair}...")
        
        price = self.forex_collector.get_current_price(pair)
        history = self.forex_collector.get_historical_data(pair, days=30)
        returns = self.forex_collector.calculate_returns(pair)
        
        return {
            'pair': pair,
            'current_price': price,
            'history': history,
            'returns': returns,
        }
    
    def get_crypto_data(self, pair: str = "BTC/USDT"):
        """Pobiera dane dla pary Crypto."""
        logger.info(f"Pobieranie danych dla {pair}...")
        
        price = self.crypto_collector.get_current_price(pair)
        stats = self.crypto_collector.get_24h_stats(pair)
        history = self.crypto_collector.get_historical_data(pair, days=30)
        volatility = self.crypto_collector.calculate_volatility(pair)
        
        return {
            'pair': pair,
            'current_price': price,
            'stats_24h': stats,
            'history': history,
            'volatility': volatility,
        }
    
    def analyze_sentiment(self, texts: list, language: str = "en", market: str = "forex"):
        """
        Analizuje sentiment tekstów.
        
        Args:
            texts: Lista tekstów do analizy
            language: Język tekstów (en/pl)
            market: Rynek (forex/crypto)
        
        Returns:
            Lista sygnałów sentiment
        """
        signals = []
        
        if market == "crypto" and self.cryptobert:
            for text in texts:
                result = self.cryptobert.analyze(text)
                signals.append(result)
        
        elif language == "pl" and self.polish_bert:
            for text in texts:
                result = self.polish_bert.analyze(text)
                signals.append(result)
        
        elif self.finbert:
            for text in texts:
                result = self.finbert.analyze(text)
                signals.append(result)
        
        return signals
    
    def run_analysis(
        self,
        forex_news: list = None,
        crypto_news: list = None,
        polish_news: list = None,
        vix: float = 20,
        fear_greed: int = 50
    ):
        """
        Uruchamia pełną analizę.
        
        Args:
            forex_news: Lista newsów Forex (EN)
            crypto_news: Lista newsów Crypto
            polish_news: Lista newsów polskich
            vix: Wartość VIX
            fear_greed: Crypto Fear & Greed Index
        
        Returns:
            Wynik analizy
        """
        logger.info("=" * 60)
        logger.info("Rozpoczynanie analizy...")
        logger.info("=" * 60)
        
        forex_signals = []
        crypto_signals = []
        
        # Analiza newsów Forex (EN)
        if forex_news and self.finbert:
            logger.info(f"Analizowanie {len(forex_news)} newsów Forex...")
            for news in forex_news:
                result = self.finbert.analyze(news)
                forex_signals.append(result)
        
        # Analiza newsów polskich
        if polish_news and self.polish_bert:
            logger.info(f"Analizowanie {len(polish_news)} newsów polskich...")
            for news in polish_news:
                result = self.polish_bert.analyze(news)
                forex_signals.append(result)
        
        # Analiza newsów Crypto
        if crypto_news and self.cryptobert:
            logger.info(f"Analizowanie {len(crypto_news)} newsów Crypto...")
            for news in crypto_news:
                result = self.cryptobert.analyze(news)
                crypto_signals.append(result)
        
        # Rozwiąż konflikty i dostosuj wagi
        forex_adjusted, forex_regime, forex_can_trade = self.conflict_resolver.resolve(
            forex_signals, vix=vix
        )
        crypto_adjusted, crypto_regime, crypto_can_trade = self.conflict_resolver.resolve(
            crypto_signals, vix=vix, fear_greed=fear_greed
        )
        
        # Agreguj sygnały
        forex_result = self.aggregator.aggregate(forex_adjusted, regime=forex_regime)
        crypto_result = self.aggregator.aggregate(crypto_adjusted, regime=crypto_regime)
        
        # Wykryj konflikty
        forex_conflicts = self.aggregator.get_conflicts(forex_signals)
        crypto_conflicts = self.aggregator.get_conflicts(crypto_signals)
        
        # Przygotuj kontekst rynkowy
        market_context = {
            'vix': vix,
            'fear_greed': fear_greed,
            'fear_greed_label': self._get_fear_greed_label(fear_greed),
            'regime': forex_regime,
            'trading_allowed': forex_can_trade and crypto_can_trade,
            'conflicts': forex_conflicts + crypto_conflicts,
        }
        
        # Eksportuj do JSON
        output_json = self.exporter.export_for_llm(
            forex_result, 
            crypto_result, 
            market_context
        )
        
        logger.info("=" * 60)
        logger.info("Analiza zakończona!")
        logger.info(f"Forex: {forex_result.get('action')} (score: {forex_result.get('score', 0):.4f})")
        logger.info(f"Crypto: {crypto_result.get('action')} (score: {crypto_result.get('score', 0):.4f})")
        logger.info("=" * 60)
        
        return {
            'forex': forex_result,
            'crypto': crypto_result,
            'market_context': market_context,
            'json_output': output_json,
        }
    
    def _get_fear_greed_label(self, value: int) -> str:
        """Konwertuje wartość Fear & Greed na label."""
        if value < 25:
            return "Extreme Fear"
        elif value < 45:
            return "Fear"
        elif value < 55:
            return "Neutral"
        elif value < 75:
            return "Greed"
        else:
            return "Extreme Greed"


def main():
    """Główna funkcja uruchomieniowa."""
    print("\n" + "=" * 60)
    print("  TRADING DECISION SYSTEM")
    print("  System Wspomagania Decyzji Tradingowych")
    print("=" * 60 + "\n")
    
    # Inicjalizuj system (może potrwać przy ładowaniu modeli)
    print("Inicjalizacja systemu (ładowanie modeli ML)...")
    print("To może potrwać kilka minut przy pierwszym uruchomieniu...\n")
    
    system = TradingSystem(load_models=True)
    
    # Przykładowe newsy do analizy
    sample_forex_news = [
        "ECB signals prolonged higher interest rates to combat inflation",
        "Euro strengthens against dollar amid positive economic data",
        "Polish central bank keeps rates unchanged",
    ]
    
    sample_polish_news = [
        "NBP utrzymuje stopy procentowe bez zmian",
        "Polska gospodarka rośnie szybciej niż oczekiwano",
    ]
    
    sample_crypto_news = [
        "Bitcoin breaks through key resistance level",
        "Institutional investors increasing crypto allocations",
        "Regulatory clarity improving for crypto markets",
    ]
    
    # Uruchom analizę
    result = system.run_analysis(
        forex_news=sample_forex_news,
        polish_news=sample_polish_news,
        crypto_news=sample_crypto_news,
        vix=18.5,
        fear_greed=42
    )
    
    # Wyświetl wynik
    print("\n" + "=" * 60)
    print("WYNIK ANALIZY - SKOPIUJ I WKLEJ DO ANTIGRAVITY:")
    print("=" * 60)
    print(result['json_output'])
    
    return result


if __name__ == "__main__":
    main()
