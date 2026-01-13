/**
 * API client for Trading System backend
 */

const API_BASE = 'http://localhost:8000';

export interface ApiError {
  status: number;
  message: string;
}

export type TimeHorizon = 'SCALP' | 'DAY' | 'SWING' | 'POSITION';
export type TrendDirection = 'bullish' | 'bearish' | 'neutral';

export interface TradingSignal {
  asset: string;
  direction: 'LONG' | 'SHORT' | 'HOLD';
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
  tradingStatus: 'OK' | 'BLOCKED' | 'CAUTION';
}

export interface EntryCondition {
  name: string;
  met: boolean;
  value?: string;
  required: boolean;
}

export interface MTFAnalysis {
  timeframe: string;
  trend: TrendDirection;
  signal: number;
  aligned: boolean;
}

export interface DecisionStep {
  step: string;
  passed: boolean;
  detail: string;
}

export interface RiskMetrics {
  dailyDrawdown: number;
  maxDrawdown: number;
  openPositions: number;
  maxPositions: number;
  capitalAtRisk: number;
  riskPercentage: number;
}

export interface AnalysisResponse {
  signal: TradingSignal;
  entryConditions: EntryCondition[];
  mtfAnalysis: MTFAnalysis[];
  decisionPath: DecisionStep[];
  analysisTime: number;
  timestamp: string;
}

export interface SignalSummary {
  asset: string;
  direction: 'LONG' | 'SHORT' | 'HOLD';
  confidence: number;
  horizon: string;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: `API Error: ${response.statusText}`,
    };
    throw error;
  }
  return response.json();
}

export const api = {
  /**
   * Get current market context (VIX, Fear&Greed, Session)
   */
  async getMarketContext(): Promise<MarketContext> {
    const response = await fetch(`${API_BASE}/api/market-context`);
    return handleResponse<MarketContext>(response);
  },

  /**
   * Get full analysis for a specific asset
   */
  async getAnalysis(market: 'forex' | 'crypto', asset: string): Promise<AnalysisResponse> {
    const assetFormatted = asset.replace('/', '-');
    const response = await fetch(`${API_BASE}/api/analysis/${market}/${assetFormatted}`);
    return handleResponse<AnalysisResponse>(response);
  },

  /**
   * Get all active signals
   */
  async getAllSignals(): Promise<{ signals: SignalSummary[]; timestamp: string }> {
    const response = await fetch(`${API_BASE}/api/signals`);
    return handleResponse(response);
  },

  /**
   * Get risk metrics
   */
  async getRiskMetrics(): Promise<RiskMetrics> {
    const response = await fetch(`${API_BASE}/api/risk`);
    return handleResponse<RiskMetrics>(response);
  },

  /**
   * Force refresh all data
   */
  async refresh(): Promise<{ status: string; message: string; timestamp: string }> {
    const response = await fetch(`${API_BASE}/api/refresh`, { method: 'POST' });
    return handleResponse(response);
  },

  /**
   * Export JSON for LLM
   */
  async exportJson(): Promise<object> {
    const response = await fetch(`${API_BASE}/api/export-json`);
    return handleResponse(response);
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    try {
      const response = await fetch(`${API_BASE}/`);
      return handleResponse(response);
    } catch {
      return { status: 'error' };
    }
  },
};
