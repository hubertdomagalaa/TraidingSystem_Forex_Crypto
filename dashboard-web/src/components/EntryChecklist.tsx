'use client';

import { EntryCondition } from '@/types/trading';

interface EntryChecklistProps {
  conditions: EntryCondition[];
}

export function EntryChecklist({ conditions }: EntryChecklistProps) {
  const metCount = conditions.filter(c => c.met).length;
  const requiredMet = conditions.filter(c => c.required && c.met).length;
  const requiredTotal = conditions.filter(c => c.required).length;
  const allRequiredMet = requiredMet === requiredTotal;

  return (
    <div className="glass-card-static p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">Entry Checklist</h3>
        <span className={`text-xs font-bold ${allRequiredMet ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}`}>
          {metCount}/{conditions.length}
        </span>
      </div>
      
      <div className="space-y-2">
        {conditions.map((condition, index) => (
          <div 
            key={index}
            className={`flex items-center gap-3 p-2 rounded-lg transition-colors ${
              condition.met 
                ? 'bg-[rgba(0,255,157,0.05)]' 
                : 'bg-[rgba(255,193,7,0.05)]'
            }`}
          >
            {/* Status Icon */}
            <span className={`text-lg ${condition.met ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}`}>
              {condition.met ? '✓' : '○'}
            </span>
            
            {/* Condition Name */}
            <div className="flex-1">
              <span className={`text-sm ${condition.met ? 'text-white' : 'text-[var(--text-muted)]'}`}>
                {condition.name}
              </span>
              {condition.required && (
                <span className="text-xs text-[var(--accent-red)] ml-1">*</span>
              )}
            </div>
            
            {/* Value */}
            {condition.value && (
              <span className="text-xs text-[var(--text-muted)] font-mono">
                {condition.value}
              </span>
            )}
          </div>
        ))}
      </div>
      
      <div className="mt-4 pt-3 border-t border-[var(--border-glass)]">
        <div className={`text-center text-sm font-medium ${allRequiredMet ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}`}>
          {allRequiredMet ? '✅ Entry Allowed' : '⚠️ Waiting for conditions'}
        </div>
      </div>
    </div>
  );
}
