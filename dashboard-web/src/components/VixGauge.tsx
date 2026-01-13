'use client';

interface VixGaugeProps {
  value: number;
  maxValue?: number;
}

export function VixGauge({ value, maxValue = 50 }: VixGaugeProps) {
  const percentage = Math.min((value / maxValue) * 100, 100);
  const circumference = 2 * Math.PI * 45; // radius = 45
  const dashOffset = circumference - (percentage / 100) * circumference * 0.75; // 270deg arc

  const getColor = () => {
    if (value < 15) return 'var(--accent-green)';
    if (value < 25) return 'var(--accent-yellow)';
    return 'var(--accent-red)';
  };

  const getLabel = () => {
    if (value < 15) return 'Low';
    if (value < 25) return 'Normal';
    if (value < 30) return 'Elevated';
    return 'High';
  };

  return (
    <div className="glass-card-static p-4">
      <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-3">Market Context</h3>
      
      <div className="flex items-center justify-center">
        <div className="gauge-container">
          <svg viewBox="0 0 100 100" className="transform -rotate-135">
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
            <span className="text-xs text-[var(--text-muted)] uppercase">VIX</span>
            <span 
              className="text-2xl font-bold" 
              style={{ color: getColor() }}
            >
              {value.toFixed(1)}
            </span>
          </div>
        </div>
      </div>
      
      <div className="text-center mt-2">
        <span 
          className="text-sm font-medium"
          style={{ color: getColor() }}
        >
          {getLabel()} Volatility
        </span>
      </div>
    </div>
  );
}
