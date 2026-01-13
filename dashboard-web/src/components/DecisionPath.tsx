'use client';

import { DecisionStep } from '@/types/trading';
import { useState } from 'react';

interface DecisionPathProps {
  steps: DecisionStep[];
}

export function DecisionPath({ steps }: DecisionPathProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const allPassed = steps.every(s => s.passed);

  return (
    <div className="glass-card-static p-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between"
      >
        <h3 className="text-sm font-medium text-[var(--text-secondary)]">Decision Path</h3>
        <span className="text-xs text-[var(--text-muted)]">
          {isExpanded ? '▼' : '▶'} {steps.length} steps
        </span>
      </button>
      
      {isExpanded && (
        <div className="mt-4 space-y-2 animate-slide-up">
          {steps.map((step, index) => (
            <div 
              key={index}
              className={`flex items-center gap-3 p-3 rounded-lg ${
                step.passed 
                  ? 'bg-[rgba(0,255,157,0.05)] border-l-2 border-[var(--accent-green)]' 
                  : 'bg-[rgba(255,0,85,0.05)] border-l-2 border-[var(--accent-red)]'
              }`}
            >
              <span className="text-lg">
                {step.passed ? '✅' : '❌'}
              </span>
              <div className="flex-1">
                <span className="text-sm text-white">{step.step}</span>
                <span className="text-xs text-[var(--text-muted)] ml-2">→ {step.detail}</span>
              </div>
            </div>
          ))}
          
          <div className={`mt-4 p-3 rounded-lg text-center font-bold ${
            allPassed 
              ? 'bg-[rgba(0,255,157,0.1)] text-[var(--accent-green)]' 
              : 'bg-[rgba(255,0,85,0.1)] text-[var(--accent-red)]'
          }`}>
            {allPassed ? '→ RESULT: Trade Signal Generated' : '→ RESULT: No Trade'}
          </div>
        </div>
      )}
    </div>
  );
}
