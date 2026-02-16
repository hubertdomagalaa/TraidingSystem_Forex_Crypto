# Quality Gates

## Goal
Define mandatory checks required before merging to `main`.

## Backend Gates
1. `ruff` critical lint rules:
```bash
ruff check --select E9,F63,F7,F82,B api risk_management run_short_term.py tests
```
2. `mypy` baseline type-check:
```bash
mypy
```
3. Security static scan:
```bash
bandit -q -r api risk_management run_short_term.py
```
4. Dependency vulnerability scan:
```bash
pip-audit -r requirements.txt
```
5. Tests + coverage threshold:
```bash
pytest tests -q --cov=api --cov=risk_management --cov-report=xml --cov-report=term-missing --cov-fail-under=30
```

## Frontend Gates
1. Type check:
```bash
cd dashboard-web && npm run type-check
```
2. Lint:
```bash
cd dashboard-web && npm run lint
```
3. Production build:
```bash
cd dashboard-web && npm run build
```

## CI Enforcement
Gates are executed in:
1. `.github/workflows/ci.yml`
2. jobs:
   - `backend-quality`
   - `frontend-quality`

## Policy
1. Any failed gate blocks merge.
2. Exceptions require explicit owner approval and follow-up issue.
3. Security findings (`bandit`, `pip-audit`) are treated as blockers unless documented and accepted in ADR.
