import { DashboardData } from '@/types/trading';

export const mockDashboardData: DashboardData = {
  signal: {
    asset: 'EUR/PLN',
    direction: 'LONG',
    confidence: 78,
    entry: 4.2650,
    stopLoss: 4.2580,
    takeProfit: 4.2790,
    horizon: 'DAY',
    riskReward: 2.0,
    positionSize: 0.1,
    timestamp: new Date().toISOString(),
  },
  marketContext: {
    vix: 18.5,
    vixRegime: 'normal',
    fearGreed: 38,
    fearGreedLabel: 'Fear',
    session: 'LONDON',
    sessionQuality: 4,
    tradingStatus: 'OK',
  },
  entryConditions: [
    { name: 'Trend Aligned', met: true, value: 'MTF Bullish', required: true },
    { name: 'Near Support', met: true, value: '4.2620', required: true },
    { name: 'RSI Not Overbought', met: true, value: 'RSI: 45', required: true },
    { name: 'VWAP Position', met: true, value: 'Above VWAP', required: false },
    { name: 'Sentiment Gate', met: true, value: 'Neutral', required: true },
    { name: 'Bollinger Confirmation', met: false, value: 'No signal', required: false },
  ],
  mtfAnalysis: [
    { timeframe: '1H', trend: 'bullish', signal: 0.42, aligned: true },
    { timeframe: '4H', trend: 'bullish', signal: 0.28, aligned: true },
    { timeframe: '1D', trend: 'neutral', signal: 0.05, aligned: false },
  ],
  riskMetrics: {
    dailyDrawdown: 0.8,
    maxDrawdown: 3.0,
    openPositions: 1,
    maxPositions: 3,
    capitalAtRisk: 250,
    riskPercentage: 2.5,
  },
  decisionPath: [
    { step: 'Session Check', passed: true, detail: 'London active' },
    { step: 'VIX Gate', passed: true, detail: '18.5 < 30' },
    { step: 'Sentiment Gate', passed: true, detail: 'Neutral (passed)' },
    { step: 'MTF Direction', passed: true, detail: 'Bullish bias' },
    { step: 'Entry Conditions', passed: true, detail: '5/6 met' },
    { step: 'Risk Check', passed: true, detail: 'Within limits' },
  ],
};
