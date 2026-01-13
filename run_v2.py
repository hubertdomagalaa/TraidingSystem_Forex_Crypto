"""
Trading System v2.0 - Główny skrypt uruchomieniowy.

Nowa architektura:
- DecisionEngine (hierarchiczny decision tree)
- SentimentContext (gate/filter, nie voter)
- HorizonDetector (DAILY/WEEKLY/MONTHLY)
- Adaptive Risk Management

v2.0 - Refaktoryzacja z linear voting na decision tree
"""
import sys
from pathlib import Path
from datetime import datetime
import logging
import json

# Setup path
sys.path.insert(0, str(Path(__file__).parent))

# Importy v2.0
from core.decision_engine import DecisionEngine, DecisionResult
from core.horizon_detector import HorizonDetector, TradingHorizon
from models.sentiment_context import SentimentAggregator, SentimentSource, SentimentContext
from strategies.entry_confirmation import EntryConfirmationV2
from risk_management.stop_loss import StopLossCalculator
from risk_management.time_exit import TimeExitManager
from output.llm_advisor_exporter import LLMAdvisorExporter

# Istniejące moduły
from config.trading_sessions import SessionAnalyzer
from models.technical.multi_timeframe import MultiTimeframeAnalyzer

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingSystemV2:
    """
    Trading System v2.0 - Decision Tree Architecture.
    
    Główne zmiany:
    1. Sentiment = gate/filter, nie voter
    2. Hierarchiczny decision tree zamiast linear voting
    3. REQUIRED vs OPTIONAL warunki
    4. Adaptive SL (ATR + structure)
    5. Time-based forced exits
    """
    
    def __init__(self, market: str = "forex"):
        """
        Args:
            market: "forex" lub "crypto"
        """
        self.market = market
        
        # Core v2.0 components
        self.decision_engine = DecisionEngine()
        self.horizon_detector = HorizonDetector()
        self.sentiment_aggregator = SentimentAggregator()
        self.entry_confirmation = EntryConfirmationV2()
        self.sl_calculator = StopLossCalculator()
        self.time_exit_manager = TimeExitManager()
        
        # Existing components
        self.session_analyzer = SessionAnalyzer()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        
        # Output
        self.exporter = LLMAdvisorExporter()
        
        logger.info("Trading System v2.0 initialized")
        logger.info("Architecture: Decision Tree (NOT linear voting)")
    
    def analyze(
        self,
        pair: str,
        current_price: float,
        indicators: dict,
        news_sentiment: list = None,
        vix_value: float = 20,
    ) -> dict:
        """
        Główna analiza tradingowa.
        
        Args:
            pair: Para walutowa (np. "EUR/PLN")
            current_price: Aktualna cena
            indicators: Dict ze wskaźnikami (rsi, adx, vwap, pivots, atr)
            news_sentiment: Lista wyników sentymentu
            vix_value: Wartość VIX
        
        Returns:
            Dict z wynikiem analizy
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 ANALYZING {pair} - Trading System v2.0")
        logger.info(f"{'='*60}")
        
        result = {
            'pair': pair,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0',
        }
        
        # ========================================
        # 1. SESSION CHECK
        # ========================================
        session = self.session_analyzer.get_current_session(self.market)
        result['session'] = session
        logger.info(f"⏰ Session: {session.get('recommendation', 'Unknown')}")
        
        if not session.get('can_trade', False):
            result['action'] = 'WAIT'
            result['reason'] = 'Session not tradeable'
            return result
        
        # ========================================
        # 2. VIX CHECK
        # ========================================
        vix_info = {
            'value': vix_value,
            'regime': 'high' if vix_value > 25 else 'normal' if vix_value > 18 else 'low',
            'can_trade': vix_value <= 30,
        }
        result['vix'] = vix_info
        logger.info(f"📈 VIX: {vix_value} ({vix_info['regime']})")
        
        if not vix_info['can_trade']:
            result['action'] = 'STOP'
            result['reason'] = f'VIX too high ({vix_value})'
            return result
        
        # ========================================
        # 3. SENTIMENT CONTEXT (gate, not voter)
        # ========================================
        self.sentiment_aggregator.clear_all()
        
        if news_sentiment:
            for news in news_sentiment:
                source = news.get('source', 'forex_news')
                try:
                    source_enum = SentimentSource[source.upper()]
                except:
                    source_enum = SentimentSource.FOREX_NEWS
                
                self.sentiment_aggregator.add_signal(
                    source=source_enum,
                    value=news.get('signal', 0),
                    confidence=news.get('confidence', 0.5),
                )
        
        sentiment_context = self.sentiment_aggregator.get_context()
        result['sentiment'] = sentiment_context.to_dict()
        logger.info(f"💭 Sentiment: {sentiment_context.bias_direction} "
                   f"(conf={sentiment_context.confidence:.2f}, "
                   f"regime={sentiment_context.regime.value})")
        
        # ========================================
        # 4. MTF ANALYSIS
        # ========================================
        # Simplified MTF for demo (w produkcji użyj prawdziwych danych)
        mtf_analysis = {
            'trends': {
                '1h': {'direction': 'up' if indicators.get('rsi', 50) > 50 else 'down', 'strength': 0.6},
                '4h': {'direction': 'up', 'strength': 0.4},
                '1d': {'direction': 'sideways', 'strength': 0.2},
            },
            'alignment': 'good_bullish' if indicators.get('rsi', 50) > 50 else 'good_bearish',
            'conflict': False,
        }
        result['mtf'] = mtf_analysis
        logger.info(f"📊 MTF Alignment: {mtf_analysis['alignment']}")
        
        # ========================================
        # 5. DECISION ENGINE (core v2.0)
        # ========================================
        decision = self.decision_engine.decide(
            session=session,
            vix=vix_info,
            sentiment=sentiment_context,
            mtf_analysis=mtf_analysis,
            indicators=indicators,
            current_price=current_price,
        )
        
        result['decision'] = decision.to_dict()
        logger.info(f"🎯 Decision: {decision.action.value} "
                   f"(confidence={decision.confidence:.2f})")
        
        if decision.is_trade():
            logger.info(f"📍 Entry: {decision.entry_price}")
            logger.info(f"🛑 SL: {decision.stop_loss}")
            logger.info(f"🎯 TP: {decision.take_profit}")
            logger.info(f"📊 Position modifier: {decision.position_modifier:.2f}")
        
        # ========================================
        # 6. GENERATE LLM OUTPUT
        # ========================================
        self.exporter.market = pair
        llm_output = self.exporter.export(
            decision_result=decision,
            session_info=session,
            vix_info=vix_info,
            sentiment_context=sentiment_context,
            mtf_analysis=mtf_analysis,
            indicators=indicators,
        )
        
        result['llm_output'] = llm_output.to_dict()
        result['llm_prompt'] = llm_output.to_llm_prompt()
        
        return result


def main():
    """Demo Trading System v2.0."""
    
    print("\n" + "=" * 70)
    print("  🚀 TRADING DECISION SYSTEM v2.0")
    print("  Architecture: Decision Tree (NOT linear voting)")
    print("=" * 70 + "\n")
    
    # Initialize system
    system = TradingSystemV2(market="forex")
    
    # Sample data
    indicators = {
        'rsi': 58,
        'adx': {'value': 26, 'plus_di': 22, 'minus_di': 17},
        'vwap': 4.325,
        'atr': 0.018,
        'pivots': {'PP': 4.340, 'R1': 4.365, 'S1': 4.315, 'R2': 4.390, 'S2': 4.290},
        'macd_hist': 0.0015,
    }
    
    news_sentiment = [
        {'source': 'forex_news', 'signal': 0.4, 'confidence': 0.75},
        {'source': 'macro_cb', 'signal': 0.2, 'confidence': 0.6},
    ]
    
    # Analyze
    result = system.analyze(
        pair="EUR/PLN",
        current_price=4.350,
        indicators=indicators,
        news_sentiment=news_sentiment,
        vix_value=19.5,
    )
    
    # Print result
    print("\n" + "=" * 70)
    print("📋 ANALYSIS RESULT")
    print("=" * 70)
    
    decision = result.get('decision', {})
    print(f"\n🎯 Action: {decision.get('action', 'N/A')}")
    print(f"📊 Confidence: {decision.get('confidence', 0):.2%}")
    print(f"⏰ Horizon: {decision.get('horizon', 'N/A')}")
    
    if decision.get('is_trade', False):
        trade = decision.get('trade', {})
        print(f"\n💰 TRADE DETAILS:")
        print(f"   Entry: {trade.get('entry', 'N/A')}")
        print(f"   Stop Loss: {trade.get('stop_loss', 'N/A')}")
        print(f"   Take Profit: {trade.get('take_profit', 'N/A')}")
        print(f"   Position Modifier: {trade.get('position_modifier', 1):.0%}")
    
    reasoning = decision.get('reasoning', {})
    if reasoning.get('confirmations'):
        print(f"\n✅ Confirmations: {reasoning['confirmations']}")
    if reasoning.get('warnings'):
        print(f"⚠️ Warnings: {reasoning['warnings']}")
    
    print("\n" + "=" * 70)
    print("📤 JSON OUTPUT FOR LLM (first 500 chars)")
    print("=" * 70)
    print(json.dumps(result.get('llm_output', {}), indent=2, ensure_ascii=False)[:500] + "...")
    
    return result


if __name__ == "__main__":
    main()
