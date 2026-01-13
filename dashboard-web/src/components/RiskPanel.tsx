'use client';

import { RiskMetrics } from '@/types/trading';

interface RiskPanelProps {
  metrics: RiskMetrics;
}

export function RiskPanel({ metrics }: RiskPanelProps) {
  const drawdownPercentage = (metrics.dailyDrawdown / metrics.maxDrawdown) * 100;
  const isRiskOk = metrics.dailyDrawdown < metrics.maxDrawdown * 0.8;

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">Risk Panel</h3>
      
      <div className="space-y-4">
        {/* Drawdown */}
        <div>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-[var(--text-muted)]">Drawdown</span>
            <span className={isRiskOk ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}>
              {metrics.dailyDrawdown.toFixed(1)}% / {metrics.maxDrawdown}%
            </span>
          </div>
          <div className="h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all ${
                drawdownPercentage < 50 ? 'bg-[var(--accent-green)]' :
                drawdownPercentage < 80 ? 'bg-[var(--accent-yellow)]' :
                'bg-[var(--accent-red)]'
              }`}
              style={{ width: `${Math.min(drawdownPercentage, 100)}%` }}
            />
          </div>
        </div>
        
        {/* Open Positions */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-[var(--text-muted)]">Open Positions</span>
          <span className="text-lg font-bold text-white">
            {metrics.openPositions}<span className="text-[var(--text-muted)]">/{metrics.maxPositions}</span>
          </span>
        </div>
        
        {/* Capital at Risk */}
        <div className="flex justify-between items-center">
          <span className="text-sm text-[var(--text-muted)]">Capital at Risk</span>
          <div className="text-right">
            <span className="text-lg font-bold text-white">${metrics.capitalAtRisk}</span>
            <span className="text-xs text-[var(--text-muted)] ml-1">({metrics.riskPercentage}%)</span>
          </div>
        </div>
      </div>
      
      <div className={`mt-4 pt-3 border-t border-[var(--border-glass)] text-center text-sm font-medium ${isRiskOk ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}`}>
        {isRiskOk ? '✅ Within Limits' : '⚠️ Approaching Limit'}
      </div>
    </div>
  );
}
