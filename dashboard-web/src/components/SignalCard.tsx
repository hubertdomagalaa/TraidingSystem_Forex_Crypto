'use client';

import { useEffect, useRef, useState } from 'react';
import { TradingSignal } from '@/types/trading';

interface SignalCardProps {
  signal: TradingSignal;
}

function AnimatedNumber({ value, decimals = 4 }: { value: number; decimals?: number }) {
  const [displayValue, setDisplayValue] = useState(0);
  const prevValue = useRef(0);

  useEffect(() => {
    if (value === 0) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDisplayValue(0);
      return;
    }

    const startValue = prevValue.current;
    const endValue = value;
    const duration = 600;
    const startTime = performance.now();
    let frameId = 0;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const currentValue = startValue + (endValue - startValue) * easeOut;

      setDisplayValue(currentValue);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      } else {
        prevValue.current = endValue;
      }
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [value]);

  return <>{displayValue.toFixed(decimals)}</>;
}

export function SignalCard({ signal }: SignalCardProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsVisible(true);
  }, []);

  const isLong = signal.direction === 'LONG';
  const isShort = signal.direction === 'SHORT';
  const directionColor = isLong
    ? 'text-[var(--accent-green)]'
    : isShort
      ? 'text-[var(--accent-red)]'
      : 'text-[var(--accent-yellow)]';

  const glowClass = isLong ? 'glow-green' : isShort ? 'glow-red' : '';
  const textGlowClass = isLong ? 'text-glow-green' : isShort ? 'text-glow-red' : '';

  const accentColor = isLong
    ? 'var(--accent-green)'
    : isShort
      ? 'var(--accent-red)'
      : 'var(--accent-yellow)';

  const slDistance = signal.entry > 0 ? (((signal.entry - signal.stopLoss) / signal.entry) * 100).toFixed(2) : '0.00';
  const tpDistance = signal.entry > 0 ? (((signal.takeProfit - signal.entry) / signal.entry) * 100).toFixed(2) : '0.00';

  const directionMarker = isLong ? 'UP' : isShort ? 'DOWN' : 'HOLD';

  return (
    <div className={`glass-card p-6 ${glowClass} ${isVisible ? 'animate-scale-in' : 'opacity-0'}`}>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-bold text-white">{signal.asset}</h2>
        <span className={`text-sm badge ${isLong ? 'badge-success' : isShort ? 'badge-danger' : 'badge-warning'}`}>
          {signal.horizon}
        </span>
      </div>

      <div className="text-center mb-8">
        <div className={`text-5xl font-black ${directionColor} ${textGlowClass} flex items-center justify-center gap-3`}>
          <span className="text-base tracking-[0.2em] opacity-80">{directionMarker}</span>
          <span className="animate-number">{signal.direction}</span>
        </div>
        <div className="mt-3 text-lg text-[var(--text-secondary)]">
          Confidence: <span className={`font-bold tabular-nums ${directionColor}`}>{signal.confidence}%</span>
        </div>

        <div className="mt-3 h-2 bg-[var(--bg-secondary)] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${signal.confidence}%`,
              backgroundColor: accentColor,
              boxShadow: `0 0 10px ${accentColor}`,
            }}
          />
        </div>
      </div>

      <div className="space-y-3 stagger-children">
        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors">
          <span className="text-[var(--text-secondary)] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-white" />
            Entry
          </span>
          <span className="text-xl font-mono font-bold text-white tabular-nums">
            <AnimatedNumber value={signal.entry} />
          </span>
        </div>

        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors">
          <span className="text-[var(--text-secondary)] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-red)]" />
            Stop Loss
          </span>
          <div className="text-right">
            <span className="text-xl font-mono font-bold text-[var(--accent-red)] tabular-nums">
              <AnimatedNumber value={signal.stopLoss} />
            </span>
            <span className="text-sm text-[var(--text-muted)] ml-2">(-{slDistance}%)</span>
          </div>
        </div>

        <div className="flex justify-between items-center p-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors">
          <span className="text-[var(--text-secondary)] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
            Take Profit
          </span>
          <div className="text-right">
            <span className="text-xl font-mono font-bold text-[var(--accent-green)] tabular-nums">
              <AnimatedNumber value={signal.takeProfit} />
            </span>
            <span className="text-sm text-[var(--text-muted)] ml-2">(+{tpDistance}%)</span>
          </div>
        </div>
      </div>

      <div className="mt-6 text-center p-4 rounded-xl bg-gradient-to-r from-[var(--bg-secondary)] to-transparent border border-[var(--border-glass)]">
        <span className="text-[var(--text-secondary)]">Risk : Reward</span>
        <div className="text-2xl font-bold text-white mt-1 flex items-center justify-center gap-2">
          <span>1</span>
          <span className="text-[var(--text-muted)]">:</span>
          <span className={isLong ? 'text-[var(--accent-green)]' : isShort ? 'text-[var(--accent-red)]' : 'text-white'}>
            {signal.riskReward.toFixed(1)}
          </span>
        </div>
      </div>
    </div>
  );
}
