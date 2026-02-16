# Contributing to Trading Decision System

Thank you for contributing.

## Getting Started
1. Fork the repository.
2. Clone your fork:
   `git clone https://github.com/YOUR_USERNAME/TraidingSystem_Forex_Crypto.git`
3. Create a feature branch:
   `git checkout -b feature/your-feature-name`
4. Implement changes and add tests.
5. Open a Pull Request to `main`.

## Local Setup
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov ruff mypy bandit pip-audit
```

## Quality Gates
Run all required checks before opening a PR:

```bash
ruff check --select E9,F63,F7,F82,B api risk_management run_short_term.py tests
mypy
bandit -q -r api risk_management run_short_term.py
pip-audit -r requirements.txt
pytest tests -q --cov=api --cov=risk_management --cov-report=term-missing --cov-fail-under=30
```

Frontend checks:
```bash
cd dashboard-web
npm ci
npm run type-check
npm run lint
npm run build
```

## Pull Request Rules
1. Keep PR scope focused.
2. Include or update tests for behavior changes.
3. Update docs when API, runtime behavior, or architecture changes.
4. Do not merge if any quality gate fails.

## Coding Standards
1. Prefer clear, typed interfaces for data contracts.
2. Keep API payloads aligned with `api/schemas.py`.
3. Avoid breaking changes without an ADR in `docs/ADR/`.