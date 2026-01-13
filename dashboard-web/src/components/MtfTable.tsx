'use client';

import { MTFAnalysis } from '@/types/trading';

interface MtfTableProps {
  analysis: MTFAnalysis[];
}

export function MtfTable({ analysis }: MtfTableProps) {
  const alignedCount = analysis.filter(a => a.aligned).length;
  const alignment = alignedCount === analysis.length 
    ? 'Perfect' 
    : alignedCount >= 2 
    ? 'Good' 
    : 'Weak';

  const getTrendIcon = (trend: MTFAnalysis['trend']) => {
    switch (trend) {
      case 'bullish': return '↗';
      case 'bearish': return '↘';
      default: return '→';
    }
  };

  const getTrendColor = (trend: MTFAnalysis['trend']) => {
    switch (trend) {
      case 'bullish': return 'text-[var(--accent-green)]';
      case 'bearish': return 'text-[var(--accent-red)]';
      default: return 'text-[var(--accent-yellow)]';
    }
  };

  return (
    <div className="glass-card-static p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">MTF Analysis</h3>
        <span className={`text-xs font-bold ${
          alignment === 'Perfect' ? 'text-[var(--accent-green)]' :
          alignment === 'Good' ? 'text-[var(--accent-blue)]' :
          'text-[var(--accent-yellow)]'
        }`}>
          {alignment} ({alignedCount}/{analysis.length})
        </span>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[var(--text-muted)] text-xs uppercase">
              <th className="text-left pb-2">TF</th>
              <th className="text-center pb-2">Trend</th>
              <th className="text-right pb-2">Signal</th>
              <th className="text-right pb-2">Align</th>
            </tr>
          </thead>
          <tbody>
            {analysis.map((row, index) => (
              <tr 
                key={index}
                className="border-t border-[var(--border-glass)]"
              >
                <td className="py-2 font-mono font-bold text-white">
                  {row.timeframe}
                </td>
                <td className={`py-2 text-center ${getTrendColor(row.trend)}`}>
                  <span className="text-lg">{getTrendIcon(row.trend)}</span>
                  <span className="ml-1 text-xs capitalize">{row.trend}</span>
                </td>
                <td className={`py-2 text-right font-mono ${
                  row.signal > 0 ? 'text-[var(--accent-green)]' : 
                  row.signal < 0 ? 'text-[var(--accent-red)]' : 
                  'text-[var(--text-muted)]'
                }`}>
                  {row.signal > 0 ? '+' : ''}{row.signal.toFixed(2)}
                </td>
                <td className="py-2 text-right">
                  {row.aligned ? (
                    <span className="text-[var(--accent-green)]">✓</span>
                  ) : (
                    <span className="text-[var(--accent-yellow)]">○</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
