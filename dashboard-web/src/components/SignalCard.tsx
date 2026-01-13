'use client';

import { TradingSignal } from '@/types/trading';

interface SignalCardProps {
  signal: TradingSignal;
}

export function SignalCard({ signal }: SignalCardProps) {
  const isLong = signal.direction === 'LONG';
  const isShort = signal.direction === 'SHORT';
  const isHold = signal.direction === 'HOLD';

  const directionColor = isLong 
    ? 'text-[var(--accent-green)]' 
    : isShort 
    ? 'text-[var(--accent-red)]' 
    : 'text-[var(--accent-yellow)]';

  const glowClass = isLong 
    ? 'glow-green' 
    : isShort 
    ? 'glow-red' 
    : '';

  const textGlowClass = isLong 
    ? 'text-glow-green' 
    : isShort 
    ? 'text-glow-red' 
    : '';

  const slDistance = ((signal.entry - signal.stopLoss) / signal.entry * 100).toFixed(2);
  const tpDistance = ((signal.takeProfit - signal.entry) / signal.entry * 100).toFixed(2);

  return (
    <div className={`glass-card p-6 ${glowClass}`}>
      {/* Asset & Direction */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-white">{signal.asset}</h2>
        <span className={`text-sm badge ${isLong ? 'badge-success' : isShort ? 'badge-danger' : 'badge-warning'}`}>
          {signal.horizon}
        </span>
      </div>

      {/* Direction Display */}
      <div className="text-center mb-8">
        <div className={`text-5xl font-black ${directionColor} ${textGlowClass} flex items-center justify-center gap-3`}>
          {isLong && <span className="text-4xl">↑</span>}
          {isShort && <span className="text-4xl">↓</span>}
          {isHold && <span className="text-4xl">⏸</span>}
          {signal.direction}
        </div>
        <div className="mt-3 text-lg text-[var(--text-secondary)]">
          Confidence: <span className={`font-bold ${directionColor}`}>{signal.confidence}%</span>
        </div>
        
        {/* Confidence Bar */}
        <div className="mt-3 h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
          <div 
            className={`h-full rounded-full transition-all duration-500 ${isLong ? 'bg-[var(--accent-green)]' : isShort ? 'bg-[var(--accent-red)]' : 'bg-[var(--accent-yellow)]'}`}
            style={{ width: `${signal.confidence}%` }}
          />
        </div>
      </div>

      {/* Price Levels */}
      <div className="space-y-4">
        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)]">
          <span className="text-[var(--text-secondary)]">Entry</span>
          <span className="text-xl font-mono font-bold text-white">{signal.entry.toFixed(4)}</span>
        </div>
        
        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)]">
          <span className="text-[var(--text-secondary)]">Stop Loss</span>
          <div className="text-right">
            <span className="text-xl font-mono font-bold text-[var(--accent-red)]">{signal.stopLoss.toFixed(4)}</span>
            <span className="text-sm text-[var(--text-muted)] ml-2">(-{slDistance}%)</span>
          </div>
        </div>
        
        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)]">
          <span className="text-[var(--text-secondary)]">Take Profit</span>
          <div className="text-right">
            <span className="text-xl font-mono font-bold text-[var(--accent-green)]">{signal.takeProfit.toFixed(4)}</span>
            <span className="text-sm text-[var(--text-muted)] ml-2">(+{tpDistance}%)</span>
          </div>
        </div>
      </div>

      {/* Risk:Reward Ratio */}
      <div className="mt-6 text-center p-4 rounded-xl bg-gradient-to-r from-[var(--bg-secondary)] to-transparent">
        <span className="text-[var(--text-secondary)]">Risk : Reward</span>
        <div className="text-2xl font-bold text-white mt-1">
          1 : {signal.riskReward.toFixed(1)}
        </div>
      </div>
    </div>
  );
}
