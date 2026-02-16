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

    @staticmethod
    def _normalize_trend(direction: str) -> str:
        trend_map = {"up": "bullish", "down": "bearish", "sideways": "neutral"}
        return trend_map.get((direction or "").lower(), "neutral")

    @staticmethod
    def _trend_signal(direction: str, strength: float) -> float:
        strength = float(strength or 0)
        if direction == "up":
            return round(strength, 4)
        if direction == "down":
            return round(-strength, 4)
        return 0.0

    def _build_entry_conditions(self, analysis: Dict[str, Any]) -> list:
        """Build UI-friendly entry conditions from current analysis payload."""
        conditions = []
        confirmation = analysis.get("confirmation", {})

        # v2 format from EntryConfirmation wrapper
        for name in confirmation.get("required_met", []):
            conditions.append({
                "name": name.replace("_", " ").title(),
                "met": True,
                "required": True,
            })
        for name in confirmation.get("required_failed", []):
            conditions.append({
                "name": name.replace("_", " ").title(),
                "met": False,
                "required": True,
            })
        for name in confirmation.get("optional_met", []):
            conditions.append({
                "name": name.replace("_", " ").title(),
                "met": True,
                "required": False,
            })
        for name in confirmation.get("optional_missed", []):
            conditions.append({
                "name": name.replace("_", " ").title(),
                "met": False,
                "required": False,
            })

        # Backward compatibility with older "confirmations" dict
        legacy_confirmations = analysis.get("confirmations")
        if isinstance(legacy_confirmations, dict):
            for name, met in legacy_confirmations.items():
                conditions.append({
                    "name": str(name).replace("_", " ").title(),
                    "met": bool(met),
                    "required": name in ["trend", "rsi", "sentiment"],
                })

        return conditions

    def _build_mtf_analysis(self, analysis: Dict[str, Any]) -> list:
        """Build normalized MTF structure for frontend."""
        mtf_items = []

        if isinstance(analysis.get("mtf"), dict):
            raw = analysis["mtf"]
            for tf in ["1H", "4H", "1D"]:
                tf_data = raw.get(tf.lower(), {})
                trend_raw = tf_data.get("trend", "neutral")
                trend = self._normalize_trend(trend_raw)
                signal = tf_data.get("signal", 0)
                mtf_items.append({
                    "timeframe": tf,
                    "trend": trend,
                    "signal": signal,
                    "aligned": tf_data.get("aligned", False),
                })
            return mtf_items

        if isinstance(analysis.get("trends"), dict):
            raw = analysis["trends"]
            base_dir = raw.get("1h", {}).get("direction")
            for tf in ["1h", "4h", "1d"]:
                tf_data = raw.get(tf, {})
                direction = tf_data.get("direction", "sideways")
                strength = tf_data.get("strength", 0.0)
                mtf_items.append({
                    "timeframe": tf.upper(),
                    "trend": self._normalize_trend(direction),
                    "signal": self._trend_signal(direction, strength),
                    "aligned": direction == base_dir if base_dir else False,
                })
        return mtf_items

    def _build_decision_path(self, analysis: Dict[str, Any]) -> list:
        """Build a structured decision path from analysis output."""
        path = analysis.get("decision_path")
        if isinstance(path, list) and path:
            if all(isinstance(item, dict) for item in path):
                return path
            # Convert plain text path to structured objects
            return [
                {"step": f"Step {idx + 1}", "passed": "BLOCKED" not in str(item).upper(), "detail": str(item)}
                for idx, item in enumerate(path)
            ]

        generated = []
        if isinstance(analysis.get("session"), dict):
            generated.append({
                "step": "Session Check",
                "passed": bool(analysis["session"].get("can_trade", False)),
                "detail": analysis["session"].get("recommendation", ""),
            })
        if isinstance(analysis.get("vix"), dict):
            generated.append({
                "step": "Volatility Check",
                "passed": bool(analysis["vix"].get("can_trade", True)),
                "detail": f"VIX={analysis['vix'].get('value', 'n/a')} ({analysis['vix'].get('regime', 'unknown')})",
            })
        generated.append({
            "step": "Signal Decision",
            "passed": analysis.get("action") in ["LONG", "SHORT"],
            "detail": analysis.get("reason", "No reason provided"),
        })
        return generated
    
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
                active = session_info.get("active_sessions", [])
                result["session"] = active[0]["id"].upper() if active else "CLOSED"

                day_rating = session_info.get("day_rating", "neutral")
                quality_map = {"best": 100, "good": 75, "neutral": 50, "avoid": 20}
                result["sessionQuality"] = quality_map.get(day_rating, 0)

                can_trade = bool(session_info.get("can_trade", False))
                if can_trade and day_rating in ["best", "good"]:
                    result["tradingStatus"] = "OK"
                elif can_trade:
                    result["tradingStatus"] = "CAUTION"
                else:
                    result["tradingStatus"] = "BLOCKED"
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
                analysis = self._trader.analyze_crypto(asset_formatted)
            
            if analysis and analysis.get("trade"):
                trade = analysis["trade"]
                # Normalize direction to uppercase (LONG/SHORT/HOLD)
                direction_raw = trade.get("direction", "HOLD")
                direction = direction_raw.upper() if isinstance(direction_raw, str) else "HOLD"
                confidence = (
                    trade.get("confidence")
                    if trade.get("confidence") is not None
                    else analysis.get("confirmation", {}).get("confidence", 0)
                )
                result["signal"] = {
                    "asset": asset_formatted,
                    "direction": direction,
                    "confidence": round(float(confidence) * 100, 2),
                    "entry": trade.get("entry", 0),
                    "stopLoss": trade.get("stop_loss", 0),
                    "takeProfit": trade.get("take_profit", 0),
                    "horizon": trade.get("horizon", "DAY").upper(),
                    "riskReward": trade.get("risk_reward", 0),
                    "positionSize": trade.get("position_size", 0),
                    "timestamp": datetime.now().isoformat(),
                }

            # Build these sections regardless of whether a trade exists
            result["entryConditions"] = self._build_entry_conditions(analysis)
            result["mtfAnalysis"] = self._build_mtf_analysis(analysis)
            result["decisionPath"] = self._build_decision_path(analysis)

            # If no trade but explicit direction action exists, expose it to UI
            action = str(analysis.get("action", "")).upper()
            if not analysis.get("trade") and action in ["LONG", "SHORT", "HOLD", "STOP", "WAIT"]:
                result["signal"]["direction"] = "HOLD" if action in ["WAIT", "STOP"] else action
                result["signal"]["confidence"] = round(
                    float(analysis.get("confirmation", {}).get("confidence", 0)) * 100, 2
                )
                result["signal"]["entry"] = analysis.get("current_price", 0) or 0
                    
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
