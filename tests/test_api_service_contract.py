"""
Contract mapping tests for TradingService API payload normalization.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services import TradingService


class TestApiServiceContract:
    def setup_method(self):
        self.service = TradingService()

    def test_build_entry_conditions_from_confirmation_v2(self):
        analysis = {
            "confirmation": {
                "required_met": ["session_ok", "volatility_ok"],
                "required_failed": ["price_location_ok"],
                "optional_met": ["adx_trend_present"],
                "optional_missed": ["momentum_positive"],
            }
        }

        conditions = self.service._build_entry_conditions(analysis)
        names = {c["name"]: c for c in conditions}

        assert names["Session Ok"]["met"] is True
        assert names["Session Ok"]["required"] is True
        assert names["Price Location Ok"]["met"] is False
        assert names["Price Location Ok"]["required"] is True
        assert names["Adx Trend Present"]["required"] is False

    def test_build_mtf_analysis_from_trends(self):
        analysis = {
            "trends": {
                "1h": {"direction": "up", "strength": 0.7},
                "4h": {"direction": "up", "strength": 0.4},
                "1d": {"direction": "down", "strength": 0.3},
            }
        }

        mtf = self.service._build_mtf_analysis(analysis)
        by_tf = {item["timeframe"]: item for item in mtf}

        assert by_tf["1H"]["trend"] == "bullish"
        assert by_tf["1H"]["signal"] > 0
        assert by_tf["4H"]["aligned"] is True
        assert by_tf["1D"]["trend"] == "bearish"
        assert by_tf["1D"]["signal"] < 0

    def test_build_decision_path_fallback(self):
        analysis = {
            "session": {"can_trade": True, "recommendation": "OK"},
            "vix": {"can_trade": True, "value": 18.5, "regime": "normal"},
            "action": "HOLD",
            "reason": "Need more confirmations",
        }

        path = self.service._build_decision_path(analysis)

        assert len(path) >= 3
        assert path[0]["step"] == "Session Check"
        assert path[-1]["passed"] is False
