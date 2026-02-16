'use client';

import { useEffect, useState } from 'react';
import { EntryCondition } from '@/types/trading';

interface EntryChecklistProps {
  conditions: EntryCondition[];
}

export function EntryChecklist({ conditions }: EntryChecklistProps) {
  const [animatedConditions, setAnimatedConditions] = useState<boolean[]>([]);

  const metCount = conditions.filter(c => c.met).length;
  const requiredMet = conditions.filter(c => c.required && c.met).length;
  const requiredTotal = conditions.filter(c => c.required).length;
  const allRequiredMet = requiredMet === requiredTotal;
  const percentage = conditions.length > 0 ? (metCount / conditions.length) * 100 : 0;

  // Animate checkmarks appearing
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAnimatedConditions([]);
    const timers: ReturnType<typeof setTimeout>[] = [];

    conditions.forEach((_, index) => {
      const timer = setTimeout(() => {
        setAnimatedConditions(prev => {
          const updated = [...prev];
          updated[index] = true;
          return updated;
        });
      }, index * 100);
      timers.push(timer);
    });

    return () => {
      timers.forEach(clearTimeout);
    };
  }, [conditions]);

  return (
    <div className="glass-card-static p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">Entry Checklist</h3>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-bold tabular-nums ${allRequiredMet ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'}`}>
            {metCount}/{conditions.length}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-1.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden mb-4">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${percentage}%`,
            backgroundColor: allRequiredMet ? 'var(--accent-green)' : 'var(--accent-yellow)',
            boxShadow: `0 0 10px ${allRequiredMet ? 'var(--accent-green-glow)' : 'rgba(255, 193, 7, 0.3)'}`
          }}
        />
      </div>

      <div className="space-y-2">
        {conditions.map((condition, index) => (
          <div
            key={index}
            className={`flex items-center gap-3 p-2.5 rounded-lg transition-all duration-300 ${
              condition.met
                ? 'bg-[rgba(0,255,157,0.08)] border border-[rgba(0,255,157,0.2)]'
                : 'bg-[rgba(255,193,7,0.05)] border border-transparent'
            } ${animatedConditions[index] ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'}`}
            style={{ transitionDelay: `${index * 50}ms` }}
          >
            {/* Status Icon */}
            <div className={`w-5 h-5 rounded-full flex items-center justify-center transition-all duration-300 ${
              condition.met
                ? 'bg-[var(--accent-green)] scale-100'
                : 'bg-transparent border-2 border-[var(--accent-yellow)] scale-90'
            }`}>
              {condition.met && (
                <svg className="w-3 h-3 text-[var(--bg-void)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              )}
            </div>

            {/* Condition Name */}
            <div className="flex-1 min-w-0">
              <span className={`text-sm transition-colors ${condition.met ? 'text-white' : 'text-[var(--text-muted)]'}`}>
                {condition.name}
              </span>
              {condition.required && (
                <span className="text-xs text-[var(--accent-red)] ml-1" title="Required">*</span>
              )}
            </div>

            {/* Value */}
            {condition.value && (
              <span className={`text-xs font-mono px-2 py-0.5 rounded ${
                condition.met
                  ? 'bg-[rgba(0,255,157,0.15)] text-[var(--accent-green)]'
                  : 'bg-[var(--bg-secondary)] text-[var(--text-muted)]'
              }`}>
                {condition.value}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Status Footer */}
      <div className="mt-4 pt-3 border-t border-[var(--border-glass)]">
        <div className={`text-center text-sm font-medium flex items-center justify-center gap-2 ${
          allRequiredMet ? 'text-[var(--accent-green)]' : 'text-[var(--accent-yellow)]'
        }`}>
          {allRequiredMet ? (
            <>
              <span className="w-2 h-2 rounded-full bg-[var(--accent-green)] animate-pulse" />
              Entry Allowed
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-[var(--accent-yellow)] animate-pulse" />
              Waiting for conditions
            </>
          )}
        </div>
      </div>
    </div>
  );
}
