"""
API route contract tests using a lightweight fake service.
"""
import sys
from pathlib import Path
from datetime import datetime

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

import api.main as api_main


class _FakeService:
    def get_market_context(self):
        return {
            "vix": 18.5,
            "vixRegime": "normal",
            "fearGreed": 52,
            "fearGreedLabel": "Neutral",
            "session": "LONDON",
            "sessionQuality": 80,
            "tradingStatus": "OK",
        }

    def analyze_asset(self, market: str, asset: str):
        return (
            {
                "signal": {
                    "asset": asset.replace("-", "/"),
                    "direction": "LONG",
                    "confidence": 78.5,
                    "entry": 4.35,
                    "stopLoss": 4.32,
                    "takeProfit": 4.41,
                    "horizon": "DAY",
                    "riskReward": 2.0,
                    "positionSize": 0.0,
                    "timestamp": datetime.now().isoformat(),
                },
                "entryConditions": [
                    {"name": "Session Ok", "met": True, "required": True},
                    {"name": "Adx Trend Present", "met": True, "required": False},
                ],
                "mtfAnalysis": [
                    {"timeframe": "1H", "trend": "bullish", "signal": 0.6, "aligned": True},
                    {"timeframe": "4H", "trend": "bullish", "signal": 0.4, "aligned": True},
                    {"timeframe": "1D", "trend": "neutral", "signal": 0.0, "aligned": False},
                ],
                "decisionPath": [
                    {"step": "Session Check", "passed": True, "detail": "OK"},
                    {"step": "Signal Decision", "passed": True, "detail": "LONG"},
                ],
            },
            0.21,
        )

    def get_all_signals(self):
        return {
            "signals": [
                {"asset": "EUR/PLN", "direction": "LONG", "confidence": 78.5, "horizon": "DAY"},
                {"asset": "BTC/USDT", "direction": "HOLD", "confidence": 0.0, "horizon": "DAY"},
            ],
            "timestamp": datetime.now().isoformat(),
        }

    def get_risk_metrics(self):
        return {
            "dailyDrawdown": 0.0,
            "maxDrawdown": 3.0,
            "openPositions": 0,
            "maxPositions": 3,
            "capitalAtRisk": 0,
            "riskPercentage": 0,
        }


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(api_main, "get_trading_service", lambda: _FakeService())
    return TestClient(api_main.app)


def test_health_route(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "Trading Decision System API"


def test_market_context_route(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/api/market-context")
    assert response.status_code == 200
    payload = response.json()
    assert payload["vix"] == 18.5
    assert payload["tradingStatus"] == "OK"


def test_analysis_route_valid_market(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/api/analysis/forex/EUR-PLN")
    assert response.status_code == 200
    payload = response.json()
    assert payload["signal"]["direction"] == "LONG"
    assert len(payload["entryConditions"]) == 2
    assert len(payload["mtfAnalysis"]) == 3
    assert isinstance(payload["analysisTime"], float)


def test_analysis_route_invalid_market(monkeypatch):
    client = _client(monkeypatch)
    response = client.get("/api/analysis/stocks/AAPL")
    assert response.status_code == 400
    assert "Market must be 'forex' or 'crypto'" in response.json()["detail"]


def test_summary_routes(monkeypatch):
    client = _client(monkeypatch)

    signals = client.get("/api/signals")
    assert signals.status_code == 200
    assert len(signals.json()["signals"]) == 2

    risk = client.get("/api/risk")
    assert risk.status_code == 200
    assert risk.json()["maxDrawdown"] == 3.0

    refresh = client.post("/api/refresh")
    assert refresh.status_code == 200
    assert refresh.json()["status"] == "ok"

    export_payload = client.get("/api/export-json")
    assert export_payload.status_code == 200
    assert "market_context" in export_payload.json()
