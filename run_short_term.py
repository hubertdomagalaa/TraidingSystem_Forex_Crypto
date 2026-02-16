"""
Główny orchestrator systemu dla short-term trading.
Uruchom zamiast main.py dla day/swing trading mode.
"""
import sys
from pathlib import Path
from datetime import datetime
import logging
import pandas as pd

# Setup path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.short_term_config import (
    TRADING_MODE, SHORT_TERM_INDICATORS, SHORT_TERM_RISK, get_active_config
)
from config.trading_sessions import SessionAnalyzer
from data.collectors import ForexCollector, CryptoCollector, VIXCollector, NewsCollector
from models.technical import IndicatorEngine, MultiTimeframeAnalyzer
from models.technical.intraday_indicators import IntradayIndicators
from models.huggingface.finbert_sentiment import FinBERTSentiment
from strategies.entry_confirmation import EntryConfirmation
from risk_management import PositionSizer, StopLossCalculator

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ShortTermTrader:
    """
    Day/Swing Trading Orchestrator.
    
    Pipeline:
    1. Check if good time to trade
    2. Collect data (1H, 4H, 1D)
    3. Calculate intraday indicators (VWAP, Pivots, ADX)
    4. Get sentiment from news
    5. Multi-timeframe alignment check
    6. Entry confirmation (multi-signal)
    7. Calculate SL/TP
    8. Output recommendation
    """
    
    def __init__(self):
        # Components
        self.session_analyzer = SessionAnalyzer()
        self.forex_collector = ForexCollector()
        self.crypto_collector = CryptoCollector()
        self.vix_collector = VIXCollector()
        self.news_collector = NewsCollector()
        self.finbert = FinBERTSentiment()
        self.indicator_engine = IndicatorEngine()
        self.intraday_indicators = IntradayIndicators()
        self.mtf_analyzer = MultiTimeframeAnalyzer()
        self.entry_confirmation = EntryConfirmation(min_confirmations=4)
        self.position_sizer = PositionSizer(default_risk_pct=0.02)
        self.sl_calculator = StopLossCalculator()
        
        # Config
        self.config = get_active_config()
        
        logger.info(f"🚀 ShortTermTrader initialized in {TRADING_MODE.value} mode")

    @staticmethod
    def _resample_to_4h(df: pd.DataFrame) -> pd.DataFrame:
        """Resample hourly OHLCV data to 4H candles."""
        if df is None or df.empty:
            return pd.DataFrame()

        frame = df.copy()
        frame.columns = frame.columns.str.lower()

        if not isinstance(frame.index, pd.DatetimeIndex):
            frame.index = pd.to_datetime(frame.index)

        agg = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        if "volume" in frame.columns:
            agg["volume"] = "sum"

        return frame.resample("4h").agg(agg).dropna(subset=["open", "high", "low", "close"])

    @staticmethod
    def _normalize_crypto_pair(asset: str) -> str:
        """Normalize input to CCXT pair format, e.g. BTC -> BTC/USDT."""
        if "/" in asset:
            return asset
        return f"{asset.upper()}/USDT"

    def analyze_forex(self, pair: str = "EUR/PLN") -> dict:
        """
        Pełna analiza dla pary Forex.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Analyzing {pair} for SHORT-TERM trading")
        logger.info(f"{'='*60}")
        
        result = {
            'pair': pair,
            'market': 'forex',
            'timestamp': datetime.now().isoformat(),
        }
        
        # 1. Check session
        session = self.session_analyzer.get_current_session("forex")
        result['session'] = session
        logger.info(f"⏰ Session: {session['recommendation']}")
        
        if not session['can_trade']:
            result['action'] = 'HOLD'
            result['reason'] = session['recommendation']
            return result
        
        # 2. Get VIX
        vix = self.vix_collector.get_current()
        result['vix'] = vix
        logger.info(f"📈 VIX: {vix['value']} ({vix['regime']})")
        
        if not vix['can_trade']:
            result['action'] = 'STOP'
            result['reason'] = vix['advice']
            return result
        
        # 3. Get price data (multi-timeframe)
        logger.info("📥 Fetching price data...")
        
        data_1h = self.forex_collector.get_historical_data(pair, days=5, interval="1h")
        data_1h_extended = self.forex_collector.get_historical_data(pair, days=30, interval="1h")
        data_4h = self._resample_to_4h(data_1h_extended)
        data_1d = self.forex_collector.get_historical_data(pair, days=90, interval="1d")
        
        if data_1h is None or data_1h.empty:
            result['action'] = 'ERROR'
            result['reason'] = 'Could not fetch price data'
            return result
        if data_4h is None or data_4h.empty:
            logger.warning("4H data unavailable, falling back to daily for higher timeframe proxy")
            data_4h = data_1d
        
        current_price = float(data_1h['Close'].iloc[-1])
        result['current_price'] = current_price
        
        # 4. Calculate indicators (fast params)
        logger.info("📊 Calculating indicators (short-term params)...")
        
        # Fast RSI
        rsi_period = SHORT_TERM_INDICATORS['rsi']['period']
        delta = data_1h['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Intraday indicators
        intraday = self.intraday_indicators.calculate_all(data_1h)
        
        result['indicators'] = {
            'rsi': round(current_rsi, 2),
            'vwap': round(intraday.get('vwap', current_price), 5),
            'adx': round(intraday['adx']['value'], 2) if intraday.get('adx') else None,
            'pivots': intraday.get('pivots'),
        }
        
        # 5. MTF alignment
        logger.info("🔍 Checking multi-timeframe alignment...")
        
        trend_1h = self.mtf_analyzer.analyze_trend(data_1h)
        trend_4h = self.mtf_analyzer.analyze_trend(data_4h)
        trend_1d = self.mtf_analyzer.analyze_trend(data_1d)
        
        result['trends'] = {
            '1h': trend_1h,
            '4h': trend_4h,
            '1d': trend_1d,
        }
        
        # 6. Entry confirmation
        logger.info("✅ Checking entry confirmations...")
        
        # 5.5 Get sentiment from news
        logger.info("📰 Analyzing news sentiment...")
        try:
            news_texts = self.news_collector.get_news_texts_for_analysis('forex', limit=5)
            if news_texts:
                sentiment_scores = [self.finbert.analyze(t)['signal'] for t in news_texts]
                sentiment_score = sum(sentiment_scores) / len(sentiment_scores)
            else:
                sentiment_score = 0.0
            logger.info(f"📊 Sentiment: {sentiment_score:.3f}")
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {e}")
            sentiment_score = 0.0
        
        result['sentiment'] = round(sentiment_score, 3)
        
        signals_for_confirmation = {
            'trend_1h': trend_1h['direction'],
            'trend_4h': trend_4h['direction'],
            'price': current_price,
            'vwap': intraday.get('vwap', current_price),
            'pivots': intraday.get('pivots'),
            'rsi': current_rsi,
            'sentiment': sentiment_score,
            'is_good_time': session['can_trade'],
            'vix': vix['value'],
            'adx': intraday['adx']['value'] if intraday.get('adx') else 20,
        }
        
        confirmation = self.entry_confirmation.check_entry(signals_for_confirmation)
        result['confirmation'] = confirmation
        
        logger.info(f"📝 {confirmation['action']}")
        
        # 7. If confirmed - calculate SL/TP
        if confirmation['entry']:
            direction = confirmation['direction']
            
            # Get ATR for SL/TP
            data_1h.columns = data_1h.columns.str.lower()
            tr = pd.concat([
                data_1h['high'] - data_1h['low'],
                abs(data_1h['high'] - data_1h['close'].shift()),
                abs(data_1h['low'] - data_1h['close'].shift())
            ], axis=1).max(axis=1)
            atr = tr.rolling(10).mean().iloc[-1]
            
            sl_tp = self.sl_calculator.atr_based(
                entry_price=current_price,
                atr=atr,
                direction=direction,
                sl_multiplier=SHORT_TERM_RISK['forex']['atr_sl_multiplier'],
                tp_multiplier=SHORT_TERM_RISK['forex']['atr_tp_multiplier'],
            )
            
            result['trade'] = {
                'direction': direction,
                'entry': current_price,
                'stop_loss': sl_tp['stop_loss'],
                'take_profit': sl_tp['take_profit'],
                'risk_reward': sl_tp['risk_reward'],
                'confidence': confirmation.get('confidence', 0.0),
                'horizon': 'DAY',
                'position_size': 0.0,
            }
            
            result['action'] = f"{direction.upper()}"
            result['reason'] = f"Entry confirmed with {confirmation['achieved']}/{confirmation['required']} signals"
            
        else:
            result['action'] = 'HOLD'
            result['reason'] = f"Need {confirmation['required'] - confirmation['achieved']} more confirmations"
        
        return result
    
    def analyze_crypto(self, symbol: str = "BTC/USDT") -> dict:
        """
        Pełna analiza dla crypto.
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"🪙 Analyzing {symbol} for SHORT-TERM trading")
        logger.info(f"{'='*60}")
        
        pair = self._normalize_crypto_pair(symbol)
        base_symbol = pair.split('/')[0]

        result = {
            'symbol': base_symbol,
            'pair': pair,
            'market': 'crypto',
            'timestamp': datetime.now().isoformat(),
        }
        
        # 1. Check session
        session = self.session_analyzer.get_current_session("crypto")
        result['session'] = session
        logger.info(f"⏰ Session: {session['recommendation']}")
        
        # 2. Get price
        try:
            current_price = self.crypto_collector.get_current_price(pair)
            if current_price is None:
                raise ValueError(f"Missing current price for {pair}")
            result['current_price'] = current_price
            logger.info(f"💰 {pair} price: ${current_price:,.2f}")
        except Exception as e:
            logger.error(f"Error fetching {pair}: {e}")
            result['action'] = 'ERROR'
            result['reason'] = str(e)
            return result
        
        # 3. Get historical data
        data = self.crypto_collector.get_historical_data(pair, timeframe="1h", days=5)
        
        if data is None or data.empty:
            result['action'] = 'ERROR'
            result['reason'] = 'No data'
            return result
        
        # 4. Indicators
        intraday = self.intraday_indicators.calculate_all(data)
        
        result['indicators'] = {
            'vwap': intraday.get('vwap'),
            'adx': intraday['adx']['value'] if intraday.get('adx') else None,
        }
        
        # 5. Trend
        trend = self.mtf_analyzer.analyze_trend(data)
        result['trend'] = trend
        
        # 6. Simple recommendation + ATR-based levels for directional bias
        tr = pd.concat([
            data['high'] - data['low'],
            abs(data['high'] - data['close'].shift()),
            abs(data['low'] - data['close'].shift())
        ], axis=1).max(axis=1)
        atr = float(tr.rolling(10).mean().iloc[-1]) if len(tr) >= 10 else float(tr.mean())

        if trend['direction'] == 'up' and trend['strength'] > 0.5:
            result['action'] = 'LONG'
            result['reason'] = f"Strong uptrend ({trend['strength']:.0%})"
            sl_tp = self.sl_calculator.atr_based(
                entry_price=current_price,
                atr=atr,
                direction='long',
                sl_multiplier=SHORT_TERM_RISK['crypto']['atr_sl_multiplier'],
                tp_multiplier=SHORT_TERM_RISK['crypto']['atr_tp_multiplier'],
            )
            result['trade'] = {
                'direction': 'long',
                'entry': current_price,
                'stop_loss': sl_tp['stop_loss'],
                'take_profit': sl_tp['take_profit'],
                'risk_reward': sl_tp['risk_reward'],
                'confidence': float(trend.get('strength', 0.0)),
                'horizon': 'DAY',
                'position_size': 0.0,
            }
        elif trend['direction'] == 'down' and trend['strength'] > 0.5:
            result['action'] = 'SHORT'
            result['reason'] = f"Strong downtrend ({trend['strength']:.0%})"
            sl_tp = self.sl_calculator.atr_based(
                entry_price=current_price,
                atr=atr,
                direction='short',
                sl_multiplier=SHORT_TERM_RISK['crypto']['atr_sl_multiplier'],
                tp_multiplier=SHORT_TERM_RISK['crypto']['atr_tp_multiplier'],
            )
            result['trade'] = {
                'direction': 'short',
                'entry': current_price,
                'stop_loss': sl_tp['stop_loss'],
                'take_profit': sl_tp['take_profit'],
                'risk_reward': sl_tp['risk_reward'],
                'confidence': float(trend.get('strength', 0.0)),
                'horizon': 'DAY',
                'position_size': 0.0,
            }
        else:
            result['action'] = 'HOLD'
            result['reason'] = 'No clear trend'
        
        return result
    
    def run_full_scan(self) -> dict:
        """
        Skanuje wszystkie rynki i pary.
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'mode': TRADING_MODE.value,
            'forex': {},
            'crypto': {},
        }
        
        # Forex
        for pair in ["EUR/PLN", "EUR/USD"]:
            try:
                results['forex'][pair] = self.analyze_forex(pair)
            except Exception as e:
                logger.error(f"Error analyzing {pair}: {e}")
        
        # Crypto
        for symbol in ["BTC/USDT", "ETH/USDT"]:
            try:
                results['crypto'][symbol] = self.analyze_crypto(symbol)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
        
        return results
    
    def print_summary(self, results: dict):
        """Drukuje podsumowanie."""
        print("\n" + "=" * 60)
        print("📋 SHORT-TERM TRADING SUMMARY")
        print("=" * 60)
        
        for market in ['forex', 'crypto']:
            print(f"\n{'🏦 FOREX' if market == 'forex' else '🪙 CRYPTO'}:")
            print("-" * 40)
            
            for asset, data in results.get(market, {}).items():
                action = data.get('action', 'N/A')
                
                emoji = "🟢" if "LONG" in action else "🔴" if "SHORT" in action else "⚪"
                
                print(f"  {emoji} {asset}: {action}")
                if 'trade' in data:
                    trade = data['trade']
                    print(f"      Entry: {trade['entry']:.5f}")
                    print(f"      SL: {trade['stop_loss']:.5f}")
                    print(f"      TP: {trade['take_profit']:.5f}")
                    print(f"      R:R: 1:{trade['risk_reward']:.1f}")
        
        print("\n" + "=" * 60)


# Main
if __name__ == "__main__":
    import pandas as pd
    
    trader = ShortTermTrader()
    
    # Pojedyncza analiza
    print("\n🔍 Single Pair Analysis: EUR/PLN")
    result = trader.analyze_forex("EUR/PLN")
    
    print("\n📊 Result:")
    print(f"   Action: {result.get('action')}")
    print(f"   Reason: {result.get('reason')}")
    
    if result.get('trade'):
        print("\n   💰 Trade Details:")
        print(f"   Direction: {result['trade']['direction']}")
        print(f"   Entry: {result['trade']['entry']:.5f}")
        print(f"   SL: {result['trade']['stop_loss']:.5f}")
        print(f"   TP: {result['trade']['take_profit']:.5f}")
