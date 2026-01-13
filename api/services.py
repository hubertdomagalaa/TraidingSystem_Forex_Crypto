"""
Trading System API - Service Layer
Connects API routes to the trading system modules.
"""
import sys
from pathlib import Path
from datetime import datetime
import time
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class TradingService:
    """
    Service layer that connects API to trading system.
    Lazy-loads trading components to improve startup time.
    """
    
    def __init__(self):
        self._trader = None
        self._session_analyzer = None
        self._vix_collector = None
        self._fear_greed = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of trading system components."""
        if self._initialized:
            return
            
        try:
            from run_short_term import ShortTermTrader
            self._trader = ShortTermTrader()
            self._initialized = True
            logger.info("Trading system initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize full trading system: {e}")
            # Will use fallback/mock data
    
    def get_market_context(self) -> Dict[str, Any]:
        """Get current market context (VIX, Fear&Greed, Session)."""
        self._ensure_initialized()
        
        result = {
            "vix": 20.0,
            "vixRegime": "normal",
            "fearGreed": 50,
            "fearGreedLabel": "Neutral",
            "session": "CLOSED",
            "sessionQuality": 0,
            "tradingStatus": "CAUTION",
        }
        
        try:
            # Try to get VIX
            from data.collectors import VIXCollector
            vix_collector = VIXCollector()
            vix_data = vix_collector.get_current()
            if vix_data:
                result["vix"] = vix_data.get("value", 20.0)
                result["vixRegime"] = vix_data.get("regime", "normal")
        except Exception as e:
            logger.warning(f"VIX collector error: {e}")
        
        try:
            # Try to get Fear & Greed
            from social_tracking import FearGreedIndex
            fg = FearGreedIndex()
            fg_data = fg.get_current()
            if fg_data:
                result["fearGreed"] = fg_data.get("value", 50)
                result["fearGreedLabel"] = fg_data.get("classification", "Neutral")
        except Exception as e:
            logger.warning(f"Fear & Greed error: {e}")
        
        try:
            # Try to get session info
            from config.trading_sessions import SessionAnalyzer
            analyzer = SessionAnalyzer()
            session_info = analyzer.get_current_session()
            if session_info:
                result["session"] = session_info.get("name", "CLOSED")
                result["sessionQuality"] = session_info.get("quality", 0)
                result["tradingStatus"] = "OK" if session_info.get("can_trade", False) else "BLOCKED"
        except Exception as e:
            logger.warning(f"Session analyzer error: {e}")
        
        return result
    
    def analyze_asset(self, market: str, asset: str) -> Tuple[Dict[str, Any], float]:
        """
        Run full analysis for an asset.
        Returns (result_dict, analysis_time_seconds)
        """
        self._ensure_initialized()
        start_time = time.time()
        
        # Convert URL-safe asset to proper format
        asset_formatted = asset.replace("-", "/")
        
        result = {
            "signal": {
                "asset": asset_formatted,
                "direction": "HOLD",
                "confidence": 0,
                "entry": 0,
                "stopLoss": 0,
                "takeProfit": 0,
                "horizon": "DAY",
                "riskReward": 0,
                "positionSize": 0,
                "timestamp": datetime.now().isoformat(),
            },
            "entryConditions": [],
            "mtfAnalysis": [],
            "decisionPath": [],
        }
        
        if not self._trader:
            logger.warning("Trader not initialized, returning default data")
            # Provide default MTF analysis for UI
            result["mtfAnalysis"] = [
                {"timeframe": "1H", "trend": "neutral", "signal": 0, "aligned": False},
                {"timeframe": "4H", "trend": "neutral", "signal": 0, "aligned": False},
                {"timeframe": "1D", "trend": "neutral", "signal": 0, "aligned": False},
            ]
            result["decisionPath"] = [
                {"step": "System Check", "passed": False, "detail": "Trader not initialized - loading models..."}
            ]
            return result, time.time() - start_time
        
        try:
            if market.lower() == "forex":
                analysis = self._trader.analyze_forex(asset_formatted)
            else:
                symbol = asset_formatted.split("/")[0]  # BTC/USDT -> BTC
                analysis = self._trader.analyze_crypto(symbol)
            
            if analysis and analysis.get("trade"):
                trade = analysis["trade"]
                # Normalize direction to uppercase (LONG/SHORT/HOLD)
                direction_raw = trade.get("direction", "HOLD")
                direction = direction_raw.upper() if isinstance(direction_raw, str) else "HOLD"
                result["signal"] = {
                    "asset": asset_formatted,
                    "direction": direction,
                    "confidence": trade.get("confidence", 0) * 100,
                    "entry": trade.get("entry", 0),
                    "stopLoss": trade.get("stop_loss", 0),
                    "takeProfit": trade.get("take_profit", 0),
                    "horizon": trade.get("horizon", "DAY").upper(),
                    "riskReward": trade.get("risk_reward", 0),
                    "positionSize": trade.get("position_size", 0),
                    "timestamp": datetime.now().isoformat(),
                }
                
                # Entry conditions
                if "confirmations" in analysis:
                    for name, met in analysis["confirmations"].items():
                        result["entryConditions"].append({
                            "name": name.replace("_", " ").title(),
                            "met": met,
                            "required": name in ["trend", "rsi", "sentiment"],
                        })
                
                # MTF Analysis
                if "mtf" in analysis:
                    mtf = analysis["mtf"]
                    # Normalize trend values: up->bullish, down->bearish, sideways->neutral
                    trend_map = {"up": "bullish", "down": "bearish", "sideways": "neutral"}
                    for tf in ["1H", "4H", "1D"]:
                        tf_data = mtf.get(tf.lower(), {})
                        raw_trend = tf_data.get("trend", "neutral")
                        normalized_trend = trend_map.get(raw_trend, raw_trend)
                        result["mtfAnalysis"].append({
                            "timeframe": tf,
                            "trend": normalized_trend,
                            "signal": tf_data.get("signal", 0),
                            "aligned": tf_data.get("aligned", False),
                        })
                
                # Decision path
                if "decision_path" in analysis:
                    result["decisionPath"] = analysis["decision_path"]
                    
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            result["decisionPath"].append({
                "step": "Error",
                "passed": False,
                "detail": str(e),
            })
        
        elapsed = time.time() - start_time
        return result, elapsed
    
    def get_all_signals(self) -> Dict[str, Any]:
        """Get summary of signals for all configured assets."""
        self._ensure_initialized()
        
        signals = []
        
        # Default assets to check
        assets = [
            ("forex", "EUR/PLN"),
            ("forex", "EUR/USD"),
            ("crypto", "BTC/USDT"),
            ("crypto", "ETH/USDT"),
        ]
        
        for market, asset in assets:
            try:
                result, _ = self.analyze_asset(market, asset.replace("/", "-"))
                sig = result["signal"]
                signals.append({
                    "asset": sig["asset"],
                    "direction": sig["direction"],
                    "confidence": sig["confidence"],
                    "horizon": sig["horizon"],
                })
            except Exception as e:
                logger.warning(f"Could not analyze {asset}: {e}")
                signals.append({
                    "asset": asset,
                    "direction": "HOLD",
                    "confidence": 0,
                    "horizon": "DAY",
                })
        
        return {"signals": signals, "timestamp": datetime.now().isoformat()}
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        # These would come from a portfolio tracker in production
        return {
            "dailyDrawdown": 0.0,
            "maxDrawdown": 3.0,
            "openPositions": 0,
            "maxPositions": 3,
            "capitalAtRisk": 0,
            "riskPercentage": 0,
        }


# Singleton instance
_service: Optional[TradingService] = None


def get_trading_service() -> TradingService:
    """Get or create the trading service singleton."""
    global _service
    if _service is None:
        _service = TradingService()
    return _service
