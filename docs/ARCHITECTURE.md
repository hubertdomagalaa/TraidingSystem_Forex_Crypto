# Architecture Overview

## System Boundaries
TradingSystem is a recommendation engine (not auto-execution) composed of:
1. Data collection layer.
2. Analysis and decision layer.
3. API + UI delivery layer.

## Layers
### 1) Data Layer
Sources:
1. Forex (`yfinance`)
2. Crypto (`ccxt`)
3. VIX (`yfinance`)
4. News/RSS and Fear&Greed

Outputs:
1. OHLCV market data
2. Sentiment input text
3. Market regime context

### 2) Analysis Layer
Core modules:
1. Technical indicators + MTF analysis
2. Sentiment models
3. Entry confirmation + risk management
4. Aggregation/conflict resolution

Output:
1. Structured trade recommendation with explanation path.

### 3) Interface Layer
1. FastAPI endpoints in `api/main.py`
2. Service mapping in `api/services.py`
3. Next.js dashboard in `dashboard-web`

## Canonical API Contract
Primary analysis contract (returned by `/api/analysis/{market}/{asset}`):
1. `signal`
2. `entryConditions`
3. `mtfAnalysis`
4. `decisionPath`
5. `analysisTime`
6. `timestamp`

Contract types are defined in:
1. `api/schemas.py`
2. `dashboard-web/src/lib/api.ts`

## Runtime Flow
1. Dashboard requests analysis endpoint.
2. API invokes `TradingService`.
3. Service executes market-specific analysis via `ShortTermTrader`.
4. Service normalizes output to canonical contract.
5. Dashboard renders signal, risk and decision context.

## Operational Notes
1. Docker healthcheck validates API root endpoint.
2. Frontend API base URL is environment-driven (`NEXT_PUBLIC_API_URL`).
3. CI enforces backend and frontend quality gates.
