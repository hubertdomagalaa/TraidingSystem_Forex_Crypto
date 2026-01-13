"""
Trading System API - FastAPI Application
"""
import sys
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import (
    AnalysisResponse, 
    MarketContext, 
    AllSignalsResponse,
    RiskMetrics,
    RefreshResponse,
    TradingSignal,
    EntryCondition,
    MTFAnalysis,
    DecisionStep,
)
from api.services import get_trading_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Trading Decision System API",
    description="API for trading signal generation and market analysis",
    version="2.0.0",
)

# CORS middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Trading Decision System API",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/market-context", response_model=MarketContext)
async def get_market_context():
    """Get current market context (VIX, Fear&Greed, Session)."""
    service = get_trading_service()
    data = service.get_market_context()
    return MarketContext(**data)


@app.get("/api/analysis/{market}/{asset}")
async def get_analysis(market: str, asset: str):
    """
    Get full analysis for a specific asset.
    
    - market: 'forex' or 'crypto'
    - asset: Asset pair with dash (e.g., 'EUR-PLN', 'BTC-USDT')
    """
    if market not in ["forex", "crypto"]:
        raise HTTPException(status_code=400, detail="Market must be 'forex' or 'crypto'")
    
    service = get_trading_service()
    result, analysis_time = service.analyze_asset(market, asset)
    
    return {
        "signal": result["signal"],
        "entryConditions": result["entryConditions"],
        "mtfAnalysis": result["mtfAnalysis"],
        "decisionPath": result["decisionPath"],
        "analysisTime": round(analysis_time, 2),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/api/signals", response_model=AllSignalsResponse)
async def get_all_signals():
    """Get summary of signals for all configured assets."""
    service = get_trading_service()
    data = service.get_all_signals()
    return AllSignalsResponse(
        signals=data["signals"],
        timestamp=datetime.fromisoformat(data["timestamp"]),
    )


@app.get("/api/risk", response_model=RiskMetrics)
async def get_risk_metrics():
    """Get current risk metrics."""
    service = get_trading_service()
    data = service.get_risk_metrics()
    return RiskMetrics(**data)


@app.post("/api/refresh", response_model=RefreshResponse)
async def refresh_data():
    """Force refresh all cached data."""
    # In production, this would invalidate caches
    return RefreshResponse(
        status="ok",
        message="Data refresh triggered",
        timestamp=datetime.now(),
    )


@app.get("/api/export-json")
async def export_json():
    """Export analysis results as LLM-ready JSON."""
    service = get_trading_service()
    
    # Get all data
    context = service.get_market_context()
    signals = service.get_all_signals()
    
    # Format for LLM
    export = {
        "timestamp": datetime.now().isoformat(),
        "market_context": context,
        "signals": signals["signals"],
        "instructions": "Analyze these trading signals and provide recommendations.",
    }
    
    return export


@app.get("/api/signals/history")
async def get_signals_history(asset: str = None, limit: int = 50):
    """Get historical signals from database."""
    try:
        from core.database import get_signal_repository
        repo = get_signal_repository()
        history = repo.get_history(asset=asset, limit=limit)
        return {"signals": history, "count": len(history)}
    except Exception as e:
        logger.error(f"Error fetching signal history: {e}")
        return {"signals": [], "count": 0, "error": str(e)}


@app.get("/api/signals/stats")
async def get_signals_stats(days: int = 30):
    """Get signal statistics for the last N days."""
    try:
        from core.database import get_signal_repository
        repo = get_signal_repository()
        stats = repo.get_stats(days=days)
        return stats
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
