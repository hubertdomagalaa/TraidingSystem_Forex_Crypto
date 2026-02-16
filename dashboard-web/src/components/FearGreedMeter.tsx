'use client';

import { useEffect, useRef, useState } from 'react';

interface FearGreedMeterProps {
  value: number;
  label: string;
}

export function FearGreedMeter({ value, label }: FearGreedMeterProps) {
  const [displayValue, setDisplayValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const prevValue = useRef(0);

  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (displayValue / 100) * circumference * 0.75;

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsAnimating(true);
    const startValue = prevValue.current;
    const endValue = value;
    const duration = 1000;
    const startTime = performance.now();
    let frameId = 0;

    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeOutElastic =
        progress === 1
          ? 1
          : 1 - Math.pow(2, -10 * progress) * Math.cos((progress * 10 - 0.75) * ((2 * Math.PI) / 3));

      const currentValue = startValue + (endValue - startValue) * easeOutElastic;
      setDisplayValue(Math.max(0, Math.min(100, currentValue)));

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
    if (displayValue < 25) return 'var(--accent-red)';
    if (displayValue < 45) return '#ff6b35';
    if (displayValue < 55) return 'var(--accent-yellow)';
    if (displayValue < 75) return '#7cb342';
    return 'var(--accent-green)';
  };

  const getMoodLabel = () => {
    if (displayValue < 25) return 'PANIC';
    if (displayValue < 45) return 'FEAR';
    if (displayValue < 55) return 'NEUTRAL';
    if (displayValue < 75) return 'GREED';
    return 'EUPHORIA';
  };

  const isExtreme = displayValue < 20 || displayValue > 80;
  const needleRotation = -135 + (displayValue / 100) * 270;

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Fear &amp; Greed Index</h3>

      <div className="flex items-center justify-center">
        <div className={`gauge-container ${isExtreme ? 'animate-pulse-glow' : ''}`}>
          <svg viewBox="0 0 100 100" className="transform -rotate-135">
            <defs>
              <linearGradient id="fngGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="var(--accent-red)" />
                <stop offset="25%" stopColor="#ff6b35" />
                <stop offset="50%" stopColor="var(--accent-yellow)" />
                <stop offset="75%" stopColor="#7cb342" />
                <stop offset="100%" stopColor="var(--accent-green)" />
              </linearGradient>
              <filter id="fngGlow" x="-50%" y="-50%" width="200%" height="200%">
                <feGaussianBlur stdDeviation="3" result="coloredBlur" />
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
              stroke="url(#fngGradient)"
              strokeWidth="3"
              fill="none"
              opacity="0.3"
              strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
            />

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
              filter="url(#fngGlow)"
              style={{
                filter: `drop-shadow(0 0 10px ${getColor()})`,
                transition: isAnimating ? 'none' : 'stroke-dashoffset 0.3s ease',
              }}
            />
          </svg>

          <div
            className="absolute inset-0 flex items-center justify-center pointer-events-none"
            style={{
              transform: `rotate(${needleRotation}deg)`,
              transition: isAnimating ? 'none' : 'transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1)',
            }}
          >
            <div
              className="absolute w-1 h-8 rounded-full origin-bottom"
              style={{
                background: `linear-gradient(to top, ${getColor()}, transparent)`,
                bottom: '50%',
                boxShadow: `0 0 8px ${getColor()}`,
              }}
            />
          </div>

          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className={`text-[10px] tracking-wider ${isExtreme ? 'animate-bounce' : ''}`}>{getMoodLabel()}</span>
            <span className="text-2xl font-bold tabular-nums" style={{ color: getColor() }}>
              {Math.round(displayValue)}
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
          {isExtreme && <span className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: getColor() }} />}
          {label}
        </span>
      </div>
    </div>
  );
}
