"""
Pydantic schemas for API responses.
"""
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum
from datetime import datetime


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    HOLD = "HOLD"


class TradingStatus(str, Enum):
    OK = "OK"
    BLOCKED = "BLOCKED"
    CAUTION = "CAUTION"


class TimeHorizon(str, Enum):
    SCALP = "SCALP"
    DAY = "DAY"
    SWING = "SWING"
    POSITION = "POSITION"


class TradingSignal(BaseModel):
    asset: str
    direction: SignalDirection
    confidence: float
    entry: float
    stopLoss: float
    takeProfit: float
    horizon: TimeHorizon
    riskReward: float
    positionSize: float
    timestamp: datetime


class MarketContext(BaseModel):
    vix: float
    vixRegime: str
    fearGreed: int
    fearGreedLabel: str
    session: str
    sessionQuality: int
    tradingStatus: TradingStatus


class EntryCondition(BaseModel):
    name: str
    met: bool
    value: Optional[str] = None
    required: bool


class MTFAnalysis(BaseModel):
    timeframe: str
    trend: str  # bullish, bearish, neutral
    signal: float
    aligned: bool


class DecisionStep(BaseModel):
    step: str
    passed: bool
    detail: str


class RiskMetrics(BaseModel):
    dailyDrawdown: float
    maxDrawdown: float
    openPositions: int
    maxPositions: int
    capitalAtRisk: float
    riskPercentage: float


class AnalysisResponse(BaseModel):
    signal: TradingSignal
    entryConditions: List[EntryCondition]
    mtfAnalysis: List[MTFAnalysis]
    decisionPath: List[DecisionStep]
    analysisTime: float  # seconds
    timestamp: datetime


class SignalSummary(BaseModel):
    asset: str
    direction: SignalDirection
    confidence: float
    horizon: TimeHorizon


class AllSignalsResponse(BaseModel):
    signals: List[SignalSummary]
    timestamp: datetime


class RefreshResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime
