'use client';

interface FearGreedMeterProps {
  value: number;
  label: string;
}

export function FearGreedMeter({ value, label }: FearGreedMeterProps) {
  const circumference = 2 * Math.PI * 45;
  const dashOffset = circumference - (value / 100) * circumference * 0.75;

  const getColor = () => {
    if (value < 25) return 'var(--accent-red)';
    if (value < 45) return '#ff6b35';
    if (value < 55) return 'var(--accent-yellow)';
    if (value < 75) return '#7cb342';
    return 'var(--accent-green)';
  };

  const getEmoji = () => {
    if (value < 25) return '😱';
    if (value < 45) return '😨';
    if (value < 55) return '😐';
    if (value < 75) return '😊';
    return '🤑';
  };

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Fear & Greed Index</h3>
      
      <div className="flex items-center justify-center">
        <div className="gauge-container">
          <svg viewBox="0 0 100 100" className="transform -rotate-135">
            {/* Gradient Background */}
            <defs>
              <linearGradient id="fngGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="var(--accent-red)" />
                <stop offset="50%" stopColor="var(--accent-yellow)" />
                <stop offset="100%" stopColor="var(--accent-green)" />
              </linearGradient>
            </defs>
            
            {/* Track */}
            <circle
              cx="50"
              cy="50"
              r="45"
              className="gauge-track"
              strokeDasharray={`${circumference * 0.75} ${circumference * 0.25}`}
            />
            {/* Fill */}
            <circle
              cx="50"
              cy="50"
              r="45"
              className="gauge-fill"
              stroke={getColor()}
              strokeDasharray={circumference}
              strokeDashoffset={dashOffset}
              style={{ filter: `drop-shadow(0 0 6px ${getColor()})` }}
            />
          </svg>
          
          {/* Center Value */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-xl">{getEmoji()}</span>
            <span 
              className="text-2xl font-bold" 
              style={{ color: getColor() }}
            >
              {value}
            </span>
          </div>
        </div>
      </div>
      
      <div className="text-center mt-2">
        <span 
          className="text-sm font-medium"
          style={{ color: getColor() }}
        >
          {label}
        </span>
      </div>
    </div>
  );
}
