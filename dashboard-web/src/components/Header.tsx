'use client';

import { TradingStatus } from '@/types/trading';

interface HeaderProps {
  session: string;
  status: TradingStatus;
}

export function Header({ session, status }: HeaderProps) {
  const getStatusBadge = () => {
    switch (status) {
      case 'OK':
        return (
          <span className="badge badge-success animate-pulse-glow">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-green)]" />
            Trading OK
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="badge badge-danger">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-red)]" />
            Trading Blocked
          </span>
        );
      case 'CAUTION':
        return (
          <span className="badge badge-warning">
            <span className="w-2 h-2 rounded-full bg-[var(--accent-yellow)]" />
            Caution
          </span>
        );
      default:
        return null;
    }
  };

  const currentTime = new Date().toLocaleTimeString('pl-PL', {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <header className="glass-card-static px-6 py-4 mb-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold tracking-widest text-[var(--accent-blue)]">TS</span>
          <div>
            <h1 className="text-xl font-bold text-white">Trading System</h1>
            <span className="text-xs text-[var(--text-muted)]">Decision Support</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="badge badge-info">
            <span className="text-sm">Session: {session}</span>
          </div>

          <div className="text-[var(--text-secondary)]">
            <span className="text-lg font-mono">Time {currentTime}</span>
          </div>

          {getStatusBadge()}
        </div>
      </div>
    </header>
  );
}