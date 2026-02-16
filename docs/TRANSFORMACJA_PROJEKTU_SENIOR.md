# Transformacja projektu do poziomu seniorskiego

## Cel dokumentu
Ten dokument opisuje, jak podniesc TradingSystem z poziomu "dobry projekt indywidualny" do poziomu "senior engineering project":
- stabilny runtime i spojnosc kontraktow miedzy warstwami,
- wysoka jakosc kodu i testow,
- powtarzalny proces dostarczania zmian,
- wiarygodny track-record metryk i decyzji.

## Definicja "projektu seniorskiego"
Projekt seniorski w tym kontekœcie to projekt, ktory:
1. Ma przewidywalne zachowanie na produkcji (observability + fallback + SLO).
2. Ma jawne kontrakty danych (schema-first API, wersjonowanie, kompatybilnosc).
3. Ma twarde quality gates (testy, lint, type-check, security scan, coverage threshold).
4. Ma udokumentowane decyzje techniczne (ADR) i roadmape.
5. Daje sie rozwijac przez inne osoby bez wiedzy ukrytej w glowie autora.

## Etap 0: Stabilizacja (najpierw)
### Priorytet P0 (blokery)
- Naprawic krytyczne bledy runtime (rekurencja, bledy kontraktow API, bledy harmonizacji danych).
- Ujednolicic formaty danych miedzy `run_short_term.py` -> `api/services.py` -> `dashboard-web`.
- Naprawic testy, ktore nie odzwierciedlaja realnego API (falszywe poczucie bezpieczenstwa).

### Priorytet P1 (spojnosc)
- Zdefiniowac canonical model sygnalu: jedna struktura `SignalDTO` uzywana wszedzie.
- Usunac stale "magiczne" i przeniesc je do wersjonowanej konfiguracji.
- Dodac walidacje wejsc i sanitacje danych z kolektorow.

## Docelowa architektura
### Warstwy
1. `domain/`:
- Logika tradingowa (entry, risk, scoring, horizon), bez zaleznosci od FastAPI, ccxt, yfinance.

2. `adapters/`:
- Integracje zewnetrzne (Yahoo, CCXT, RSS, FearGreed API, DB).
- Kazdy adapter ma timeout, retry policy i fallback.

3. `application/`:
- Use-case'y: `AnalyzeAsset`, `GetMarketContext`, `GetRiskMetrics`, `RunBacktest`.

4. `interfaces/`:
- API HTTP, CLI, dashboard contracts.

### Kontrakty
- Zrodlo prawdy: `api/schemas.py` + odpowiedniki TypeScript generowane automatycznie.
- Wersjonowanie endpointow: `/api/v1/...`.

## Engineering quality gates
Ka¿dy PR musi przejsc:
1. `ruff`/`flake8` + formatowanie (`black` lub `ruff format`).
2. Type checking (`mypy` dla Python, `tsc --noEmit` dla dashboard).
3. Testy jednostkowe + integracyjne.
4. Coverage threshold (np. minimum 80% backend core).
5. Security scan (`pip-audit`, `npm audit --production`, `bandit`).

## Strategia testowania
### 1. Unit tests
- `domain/*`: deterministyczne testy logiki sygnalow, risk i decision engine.

### 2. Contract tests
- API schemas kontra odpowiedzi endpointow.
- Frontend client kontra backend OpenAPI.

### 3. Integration tests
- Adaptery danych na fixture/mock API.
- SQLite repozytorium na izolowanej bazie testowej.

### 4. E2E tests
- Scenariusz: `refresh -> analyze -> render dashboard -> export JSON`.

### 5. Regression tests
- Golden files z przykladowymi sygnalami dla konkretnych danych historycznych.

## Observability i operacyjnosc
### Logi
- Strukturalne logi JSON (`request_id`, `asset`, `market`, `decision_id`).

### Metryki
- Latencja endpointow (`p50`, `p95`, `p99`).
- Error rate kolektorow.
- Skutecznosc cache.
- Rozklad decyzji LONG/SHORT/HOLD.

### Tracing
- Correlation ID od API do warstwy kolektorow i decyzji.

### SLO (przyklad)
- `GET /api/analysis/*`: p95 < 1200 ms (bez cold start modeli).
- Dostepnosc API: >= 99.5% miesiecznie.

## Zarzadzanie konfiguracja i sekretami
- `.env` tylko lokalnie.
- Produkcja: sekrety z managera (GitHub Secrets, Doppler, Vault).
- Konfiguracje runtime rozdzielone per env (`dev/stage/prod`).
- Walidacja configu przy starcie aplikacji (fail fast).

## Data governance i odpowiedzialnosc modelu
- Wersjonowanie wag modeli i parametrow strategii.
- Rejestrowanie powodow decyzji (`decision_path`) jako first-class artifact.
- Dodanie `model card` i `risk card` (ograniczenia systemu, kiedy nie uzywac).

## Backtesting na poziomie senior
1. Walk-forward validation zamiast jednego okresu.
2. Rozdzial in-sample/out-of-sample.
3. Metryki transakcyjne z kosztami (spread, slippage, fees) i stres test.
4. Raporty porownawcze strategii vs baseline.
5. Powtarzalnosc: seed, snapshot danych, wersja konfiguracji.

## CI/CD blueprint
### CI
- Workflow: lint -> type-check -> tests -> coverage -> security.
- Blokada merge przy niespelnionych gate'ach.

### CD
- Build image + scan + podpis.
- Deploy canary (jesli environment produkcyjny).
- Automatyczny rollback przy przekroczeniu error budget.

## Dokumentacja, ktora buduje senior-level trust
Dodaj i utrzymuj:
1. `docs/ARCHITECTURE.md` (diagram C4 + przeplywy).
2. `docs/ADR/` (decyzje architektoniczne).
3. `docs/RUNBOOK.md` (jak diagnozowac awarie).
4. `docs/QUALITY_GATES.md` (co musi przejsc PR).
5. `docs/BACKTEST_PROTOCOL.md` (jak porownywac wyniki uczciwie).

## Roadmapa 30/60/90
### 0-30 dni
- Stabilizacja P0/P1.
- Ujednolicenie kontraktow API + frontend.
- Naprawa i rozszerzenie testow krytycznych.
- CI z quality gates jako required checks.

### 31-60 dni
- Refactor do warstw domain/application/adapters.
- Observability (metryki + logi strukturalne).
- Pierwszy zestaw ADR i runbook.
- E2E dla glownego flow dashboard.

### 61-90 dni
- Walk-forward backtesting pipeline.
- Release process (wersjonowanie, changelog, release notes).
- Benchmark latency i reliability.
- Publiczny "engineering maturity report" w repo.

## KPI transformacji
Mierz co tydzien:
- Defect escape rate (ile bugow trafia na main/production).
- Mean time to detect / recover (MTTD, MTTR).
- Test coverage core + contract pass rate.
- Build success rate i median CI time.
- Runtime error rate per endpoint.

## Definition of Done (senior milestone)
Projekt uznajemy za "senior-level" gdy:
1. Brak krytycznych runtime bugow przez min. 4 tygodnie.
2. Wszystkie quality gates sa obligatoryjne i zielone.
3. API i frontend korzystaja z jednego, wersjonowanego kontraktu.
4. Istnieje komplet: architektura, ADR, runbook, protokol backtestu.
5. Metryki operacyjne sa monitorowane i regularnie raportowane.

## Krotka checklista wdrozeniowa
- [ ] Naprawione krytyczne bledy i niespojnosci kontraktow.
- [ ] Dodane testy dla wszystkich scenariuszy krytycznych.
- [ ] Wlaczone lint/type/security/coverage jako wymagane checki.
- [ ] Udokumentowany proces release i incident response.
- [ ] Dashboard i API dzialaja z jednym modelem danych.

