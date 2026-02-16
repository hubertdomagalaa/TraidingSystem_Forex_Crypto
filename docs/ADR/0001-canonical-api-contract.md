# ADR 0001: Canonical API Contract Between Analysis and UI

## Status
Accepted

## Date
2026-02-16

## Context
The project had mismatched payload keys between:
1. `run_short_term.py` output
2. `api/services.py` mapping
3. `dashboard-web` expectations

This caused missing UI sections and fallback-only rendering.

## Decision
Adopt one canonical payload for analysis endpoint:
1. `signal`
2. `entryConditions`
3. `mtfAnalysis`
4. `decisionPath`
5. `analysisTime`
6. `timestamp`

`api/services.py` is responsible for normalization from internal analysis structures to this contract.

## Consequences
Positive:
1. Stable frontend rendering with predictable keys.
2. Reduced contract drift risk between backend and UI.
3. Easier API contract testing.

Negative:
1. Additional mapping logic in service layer.
2. Legacy payload variants still need backward-compatible handling.

## Follow-up
1. Generate TypeScript types from OpenAPI in a future iteration.
2. Add stricter schema contract tests for all endpoints.
