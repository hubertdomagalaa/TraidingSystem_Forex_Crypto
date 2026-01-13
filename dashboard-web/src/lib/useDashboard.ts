'use client';

import { useState, useCallback } from 'react';
import { api, AnalysisResponse, MarketContext, RiskMetrics, SignalSummary } from './api';

export interface DashboardState {
  analysis: AnalysisResponse | null;
  marketContext: MarketContext | null;
  riskMetrics: RiskMetrics | null;
  allSignals: SignalSummary[];
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
  analysisTime: number | null;
}

const initialState: DashboardState = {
  analysis: null,
  marketContext: null,
  riskMetrics: null,
  allSignals: [],
  isLoading: false,
  error: null,
  lastUpdated: null,
  analysisTime: null,
};

export function useDashboard() {
  const [state, setState] = useState<DashboardState>(initialState);

  const setLoading = (isLoading: boolean) => {
    setState(prev => ({ ...prev, isLoading, error: isLoading ? null : prev.error }));
  };

  const setError = (error: string) => {
    setState(prev => ({ ...prev, error, isLoading: false }));
  };

  /**
   * Load all dashboard data
   */
  const loadAll = useCallback(async (market: 'forex' | 'crypto' = 'forex', asset: string = 'EUR/PLN') => {
    setLoading(true);
    const startTime = Date.now();

    try {
      // Fetch all data in parallel
      const [analysisResult, contextResult, riskResult, signalsResult] = await Promise.all([
        api.getAnalysis(market, asset),
        api.getMarketContext(),
        api.getRiskMetrics(),
        api.getAllSignals(),
      ]);

      const totalTime = (Date.now() - startTime) / 1000;

      setState({
        analysis: analysisResult,
        marketContext: contextResult,
        riskMetrics: riskResult,
        allSignals: signalsResult.signals,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        analysisTime: totalTime,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
    }
  }, []);

  /**
   * Load analysis for a specific asset
   */
  const loadAnalysis = useCallback(async (market: 'forex' | 'crypto', asset: string) => {
    setLoading(true);

    try {
      const result = await api.getAnalysis(market, asset);
      setState(prev => ({
        ...prev,
        analysis: result,
        isLoading: false,
        error: null,
        lastUpdated: new Date(),
        analysisTime: result.analysisTime,
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load analysis';
      setError(message);
    }
  }, []);

  /**
   * Load market context only
   */
  const loadMarketContext = useCallback(async () => {
    try {
      const result = await api.getMarketContext();
      setState(prev => ({
        ...prev,
        marketContext: result,
      }));
    } catch (err) {
      console.error('Failed to load market context:', err);
    }
  }, []);

  /**
   * Refresh all data
   */
  const refresh = useCallback(async () => {
    await api.refresh();
    await loadAll();
  }, [loadAll]);

  /**
   * Export JSON for LLM
   */
  const exportJson = useCallback(async (): Promise<string> => {
    const data = await api.exportJson();
    return JSON.stringify(data, null, 2);
  }, []);

  return {
    ...state,
    loadAll,
    loadAnalysis,
    loadMarketContext,
    refresh,
    exportJson,
  };
}
