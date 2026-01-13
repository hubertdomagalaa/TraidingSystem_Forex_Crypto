'use client';

import { useEffect, useState } from 'react';
import {
  Header,
  SignalCard,
  VixGauge,
  FearGreedMeter,
  EntryChecklist,
  MtfTable,
  RiskPanel,
  DecisionPath,
} from '@/components';
import { useDashboard } from '@/lib/useDashboard';

export default function Dashboard() {
  const {
    analysis,
    marketContext,
    riskMetrics,
    isLoading,
    error,
    lastUpdated,
    analysisTime,
    loadAll,
    exportJson,
  } = useDashboard();

  const [selectedAsset, setSelectedAsset] = useState('EUR/PLN');
  const [selectedMarket, setSelectedMarket] = useState<'forex' | 'crypto'>('forex');
  const [copySuccess, setCopySuccess] = useState(false);

  // Load data on mount and when asset changes
  useEffect(() => {
    loadAll(selectedMarket, selectedAsset);
  }, [selectedAsset, selectedMarket, loadAll]);

  const handleRefresh = () => {
    loadAll(selectedMarket, selectedAsset);
  };

  const handleCopyJson = async () => {
    try {
      const json = await exportJson();
      await navigator.clipboard.writeText(json);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (e) {
      console.error('Copy failed:', e);
    }
  };

  const handleAssetChange = (asset: string, market: 'forex' | 'crypto') => {
    setSelectedAsset(asset);
    setSelectedMarket(market);
  };

  // Build signal object for SignalCard
  const signal = analysis?.signal || {
    asset: selectedAsset,
    direction: 'HOLD' as const,
    confidence: 0,
    entry: 0,
    stopLoss: 0,
    takeProfit: 0,
    horizon: 'DAY' as const,
    riskReward: 0,
    positionSize: 0,
    timestamp: new Date().toISOString(),
  };

  const context = marketContext || {
    vix: 0,
    vixRegime: 'normal',
    fearGreed: 50,
    fearGreedLabel: 'Neutral',
    session: 'CLOSED',
    sessionQuality: 0,
    tradingStatus: 'CAUTION' as const,
  };

  const risk = riskMetrics || {
    dailyDrawdown: 0,
    maxDrawdown: 3,
    openPositions: 0,
    maxPositions: 3,
    capitalAtRisk: 0,
    riskPercentage: 0,
  };

  return (
    <div className="min-h-screen p-4 md:p-6 lg:p-8">
      {/* Header */}
      <Header 
        session={context.session} 
        status={context.tradingStatus} 
      />

      {/* Error Banner */}
      {error && (
        <div className="mb-6 p-4 rounded-lg bg-[rgba(255,0,85,0.15)] border border-[var(--accent-red)] text-[var(--accent-red)]">
          <span className="font-bold">⚠️ Error:</span> {error}
          <button 
            onClick={handleRefresh}
            className="ml-4 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Asset Selector */}
      <div className="mb-6 flex flex-wrap gap-2">
        {[
          { asset: 'EUR/PLN', market: 'forex' as const },
          { asset: 'EUR/USD', market: 'forex' as const },
          { asset: 'BTC/USDT', market: 'crypto' as const },
          { asset: 'ETH/USDT', market: 'crypto' as const },
        ].map(({ asset, market }) => (
          <button
            key={asset}
            onClick={() => handleAssetChange(asset, market)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              selectedAsset === asset
                ? 'bg-[var(--accent-blue)] text-white'
                : 'bg-[var(--bg-card)] text-[var(--text-secondary)] hover:bg-[var(--bg-card-hover)]'
            }`}
          >
            {asset}
          </button>
        ))}
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column - Main Signal */}
        <div className="lg:col-span-2 space-y-6">
          {/* Hero Signal Card */}
          <div className={`relative ${isLoading ? 'opacity-50' : ''}`}>
            {isLoading && (
              <div className="absolute inset-0 flex items-center justify-center z-10">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[var(--accent-green)]"></div>
              </div>
            )}
            <SignalCard signal={signal} />
          </div>
          
          {/* Bottom Row - MTF and Chart */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <MtfTable analysis={analysis?.mtfAnalysis || []} />
            
            {/* Chart Placeholder */}
            <div className="glass-card-static p-4">
              <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">Price Chart</h3>
              <div className="h-40 flex items-center justify-center border border-dashed border-[var(--border-glass)] rounded-lg">
                <div className="text-center text-[var(--text-muted)]">
                  <span className="text-3xl mb-2 block">📈</span>
                  <span className="text-sm">Chart integration pending</span>
                </div>
              </div>
              
              {signal.entry > 0 && (
                <div className="mt-4 flex justify-between text-xs font-mono">
                  <span className="text-[var(--accent-red)]">SL: {signal.stopLoss.toFixed(4)}</span>
                  <span className="text-white">Entry: {signal.entry.toFixed(4)}</span>
                  <span className="text-[var(--accent-green)]">TP: {signal.takeProfit.toFixed(4)}</span>
                </div>
              )}
            </div>
          </div>
          
          {/* Decision Path */}
          <DecisionPath steps={analysis?.decisionPath || []} />
        </div>

        {/* Right Column - Context & Risk */}
        <div className="space-y-6">
          {/* Market Context Gauges */}
          <div className="grid grid-cols-2 lg:grid-cols-1 gap-4">
            <VixGauge value={context.vix} />
            <FearGreedMeter 
              value={context.fearGreed} 
              label={context.fearGreedLabel} 
            />
          </div>
          
          {/* Entry Checklist */}
          <EntryChecklist conditions={analysis?.entryConditions || []} />
          
          {/* Risk Panel */}
          <RiskPanel metrics={risk} />
          
          {/* Quick Actions */}
          <div className="glass-card-static p-4">
            <h3 className="text-sm font-medium text-[var(--text-secondary)] mb-4">Quick Actions</h3>
            <div className="space-y-2">
              <button 
                onClick={handleRefresh}
                disabled={isLoading}
                className="w-full p-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors text-white text-sm flex items-center gap-2 disabled:opacity-50"
              >
                <span className={isLoading ? 'animate-spin' : ''}>🔄</span> 
                {isLoading ? 'Analyzing...' : 'Refresh Analysis'}
              </button>
              <button 
                onClick={handleCopyJson}
                className="w-full p-3 rounded-lg bg-[var(--bg-secondary)] hover:bg-[var(--bg-card-hover)] transition-colors text-white text-sm flex items-center gap-2"
              >
                <span>{copySuccess ? '✅' : '📋'}</span> 
                {copySuccess ? 'Copied!' : 'Copy JSON for LLM'}
              </button>
              <button className="w-full p-3 rounded-lg bg-gradient-to-r from-[var(--accent-green)] to-[var(--accent-blue)] text-[var(--bg-void)] font-bold text-sm flex items-center justify-center gap-2 hover:opacity-90 transition-opacity">
                <span>📊</span> Full Report
              </button>
            </div>
          </div>
          
          {/* Status Footer */}
          {lastUpdated && (
            <div className="text-center text-xs text-[var(--text-muted)]">
              <p>Last updated: {lastUpdated.toLocaleTimeString()}</p>
              {analysisTime && <p>Analysis time: {analysisTime.toFixed(2)}s</p>}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-8 text-center text-xs text-[var(--text-muted)]">
        <p>Trading Decision System v2.0 • Not financial advice • Use at your own risk</p>
      </footer>
    </div>
  );
}
