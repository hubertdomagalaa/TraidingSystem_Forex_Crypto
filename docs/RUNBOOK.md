# TradingSystem Runbook

## Purpose
Operational guide for diagnosing and recovering the TradingSystem services (`api` + `dashboard-web`).

## Services
1. `api` (FastAPI, port `8000`)
2. `dashboard-web` (Next.js, port `3000`)

## Quick Health Checks
```powershell
Invoke-RestMethod http://localhost:8000/
Invoke-RestMethod http://localhost:8000/api/market-context
Invoke-RestMethod http://localhost:8000/api/signals
```

```powershell
curl http://localhost:3000
```

Expected:
1. API returns `status: ok`.
2. Market context and signals return JSON without 5xx errors.
3. Dashboard responds with HTTP 200.

## Common Incidents

### 1) API returns empty/placeholder signals
Symptoms:
1. `direction: HOLD`, zeroed entry/SL/TP for all assets.

Actions:
1. Check API logs for `Trader not initialized`.
2. Verify Python deps installed: `pip install -r requirements.txt`.
3. Run a direct analysis smoke test:
```powershell
python -c "from run_short_term import ShortTermTrader; t=ShortTermTrader(); print(t.analyze_forex('EUR/PLN').get('action'))"
```

### 2) Crypto analysis returns `ERROR`
Symptoms:
1. `/api/analysis/crypto/BTC-USDT` gives fallback or error path.

Actions:
1. Verify exchange connectivity (CCXT/binance).
2. Validate pair format (`BTC/USDT`, `ETH/USDT`).
3. Retry endpoint and inspect API logs.

### 3) Dashboard cannot connect to API
Symptoms:
1. Frontend loads with error banner / fetch errors.

Actions:
1. Confirm `NEXT_PUBLIC_API_URL` is set correctly.
2. Local dev:
```powershell
$env:NEXT_PUBLIC_API_URL="http://localhost:8000"
```
3. Docker: verify compose env uses `http://api:8000`.

### 4) Docker service unhealthy
Symptoms:
1. `api` service never reaches healthy state.

Actions:
1. Check API container logs:
```powershell
docker compose logs api --tail=200
```
2. Validate healthcheck endpoint manually in container.
3. Verify db volume mount permissions.

## Recovery Playbooks

### Restart stack
```powershell
docker compose down
docker compose up --build -d
```

### Rebuild local environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest tests -q
```

### Verify frontend build integrity
```powershell
cd dashboard-web
npm ci
npm run type-check
npm run lint
npm run build
```

## Escalation Criteria
Escalate when:
1. API 5xx error rate > 5% for 10 minutes.
2. `/api/analysis/*` is unavailable > 10 minutes.
3. Data collectors fail repeatedly for all assets.
4. CI main branch is red for > 24 hours.
