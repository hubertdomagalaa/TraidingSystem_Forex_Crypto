'use client';

import { useEffect, useRef, useState } from 'react';

interface VixGaugeProps {
  value: number;
  maxValue?: number;
}

export function VixGauge({ value, maxValue = 50 }: VixGaugeProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const prevValue = useRef(0);

  const percentage = Math.min((displayValue / maxValue) * 100, 100);
  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (percentage / 100) * circumference * 0.75;

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsAnimating(true);
    const startValue = prevValue.current;
    const endValue = value;
    const duration = 800;
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
        setIsAnimating(false);
      }
    };

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [value]);

  const getColor = () => {
    if (displayValue < 15) return 'var(--accent-green)';
    if (displayValue < 25) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  const getLabel = () => {
    if (displayValue < 15) return 'Low';
    if (displayValue < 25) return 'Normal';
    if (displayValue < 30) return 'Elevated';
    return 'High';
  };

  const isHighVix = displayValue >= 30;

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Market Volatility</h3>

      <div className="flex items-center justify-center">
        <div className={`gauge-container ${isHighVix ? 'animate-pulse-glow' : ''}`}>
          <svg viewBox="0 0 100 100" className="transform -rotate-135">
            <defs>
              <linearGradient id="vixGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="var(--accent-green)" />
                <stop offset="50%" stopColor="var(--accent-yellow)" />
                <stop offset="100%" stopColor="var(--accent-red)" />
              </linearGradient>
              <filter id="vixGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="2" result="coloredBlur" />
                <feMerge>
                  <feMergeNode in="coloredBlur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            <circle
              cx="50"
              cy="50"
              r="45"
              className="gauge-track"
              strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
            />

            <circle
              cx="50"
              cy="50"
              r="45"
              className="gauge-fill"
              stroke={getColor()}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              filter="url(#vixGlow)"
              style={{
                filter: `drop-shadow(0 0 8px ${getColor()})`,
                transition: isAnimating ? 'none' : 'stroke-dashoffset 0.3s ease',
              }}
            />
          </svg>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xs text-[var(--text-muted)] uppercase tracking-wider">VIX</span>
            <span className={`text-2xl font-bold tabular-nums ${isHighVix ? 'animate-pulse' : ''}`} style={{ color: getColor() }}>
              {displayValue.toFixed(1)}
            </span>
          </div>
        </div>
      </div>

      <div className="text-center mt-3">
        <span
          className="text-sm font-semibold inline-flex items-center gap-1.5 px-3 py-1 rounded-full"
          style={{
            color: getColor(),
            backgroundColor: `${getColor()}15`,
          }}
        >
          {isHighVix && <span className="text-[10px] tracking-wider">ALERT</span>}
          {getLabel()} Volatility
        </span>
      </div>
    </div>
  );
}
