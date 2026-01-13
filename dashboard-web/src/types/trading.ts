// Trading Dashboard Types

export type SignalDirection = 'LONG' | 'SHORT' | 'HOLD';
export type TradingStatus = 'OK' | 'BLOCKED' | 'CAUTION';
export type TimeHorizon = 'SCALP' | 'DAY' | 'SWING' | 'POSITION';
export type Regime = 'normal' | 'high_volatility' | 'low_volatility' | 'news_event';

export interface TradingSignal {
  asset: string;
  direction: SignalDirection;
  confidence: number;
  entry: number;
  stopLoss: number;
  takeProfit: number;
  horizon: TimeHorizon;
  riskReward: number;
  positionSize: number;
  timestamp: string;
}

export interface MarketContext {
  vix: number;
  vixRegime: string;
  fearGreed: number;
  fearGreedLabel: string;
  session: string;
  sessionQuality: number;
  tradingStatus: TradingStatus;
}

export interface EntryCondition {
  name: string;
  met: boolean;
  value?: string;
  required: boolean;
}

export interface MTFAnalysis {
  timeframe: string;
  trend: 'bullish' | 'bearish' | 'neutral';
  signal: number;
  aligned: boolean;
}

export interface RiskMetrics {
  dailyDrawdown: number;
  maxDrawdown: number;
  openPositions: number;
  maxPositions: number;
  capitalAtRisk: number;
  riskPercentage: number;
}

export interface DecisionStep {
  step: string;
  passed: boolean;
  detail: string;
}

export interface DashboardData {
  signal: TradingSignal;
  marketContext: MarketContext;
  entryConditions: EntryCondition[];
  mtfAnalysis: MTFAnalysis[];
  riskMetrics: RiskMetrics;
  decisionPath: DecisionStep[];
}
