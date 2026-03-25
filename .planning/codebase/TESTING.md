# Testing

> Test framework, structure, coverage, and patterns for HealthMap

## Current State

**No tests exist.** The codebase has zero unit tests, zero integration tests, and zero E2E tests. No test framework is configured for either backend or frontend.

## Framework Setup Needed

### Backend (Python/FastAPI)
- **No test dependencies** in `requirements.txt`
- Recommended: `pytest`, `pytest-asyncio`, `httpx` (for TestClient)
- FastAPI's built-in `TestClient` (uses `httpx` under the hood) for API testing
- SQLAlchemy in-memory SQLite or test PostgreSQL for DB tests

### Frontend (Next.js/React)
- **No test dependencies** in `package.json`
- No `jest.config`, `vitest.config`, or test scripts defined
- Recommended: `vitest` + `@testing-library/react` for component tests
- `playwright` or `cypress` for E2E

## Test Structure (Recommended)

```
backend/
├── tests/
│   ├── conftest.py            # Fixtures: test DB, client, seed data
│   ├── test_routes/
│   │   ├── test_disease.py    # Disease API endpoint tests
│   │   ├── test_correlations.py
│   │   ├── test_insights.py
│   │   └── test_regions.py
│   ├── test_services/
│   │   ├── test_disease_service.py
│   │   ├── test_correlation_service.py
│   │   ├── test_trend_service.py
│   │   └── test_ai_service.py
│   └── test_models/
│       └── test_models.py

frontend/
├── __tests__/
│   ├── components/
│   │   ├── MapContainer.test.tsx
│   │   ├── Sidebar.test.tsx
│   │   ├── AIInsightPanel.test.tsx
│   │   └── TrendChart.test.tsx
│   └── lib/
│       └── api-client.test.ts
```

## Critical Areas Needing Tests

### High Priority
1. **Correlation calculations** (`correlation_service.py`) — Pure-Python Pearson/Spearman implementations with custom p-value approximation. Mathematical correctness is critical.
2. **Disease metrics** (`disease_service.py`) — 7-day/14-day averages, trend detection, CFR calculations. Business-critical data.
3. **Anomaly detection** (`trend_service.py`) — Z-score threshold logic, spike/drop classification.
4. **AI service** (`ai_service.py`) — Error handling, prompt construction, conversation history management.

### Medium Priority
5. **API routes** — Request validation, error responses, query parameter handling
6. **Data ingestion scripts** — Data transformation, deduplication, error handling
7. **Frontend API client** — Request formatting, error handling, type correctness

### Lower Priority
8. **React components** — Rendering, user interactions, state management
9. **Map interactions** — Country selection, hover effects, comparison mode

## Mocking Strategy

| Dependency | Mock Approach |
|-----------|---------------|
| PostgreSQL | In-memory SQLite via SQLAlchemy or test Postgres container |
| Redis | `fakeredis` or skip (Redis not actively used in current code) |
| Anthropic API | Mock `anthropic.Anthropic` client, return canned responses |
| Mapbox GL | Jest/Vitest mock for `mapbox-gl` module |
| Axios | `msw` (Mock Service Worker) or `axios-mock-adapter` |

## Test Data

- `backend/app/main.py` contains a `/api/seed` endpoint with deterministic test data (`random.seed(42)`)
- 20 countries, 3 diseases, 365 days of COVID-19 records per country
- Climate data with seasonal patterns for correlation testing
- This seed data can be reused in test fixtures

## Coverage Gaps Summary

| Layer | Files | Lines (approx) | Test Coverage |
|-------|-------|----------------|---------------|
| Services | 4 files | ~700 lines | 0% |
| Routes | 4 files | ~200 lines | 0% |
| Models | 4 files | ~100 lines | 0% |
| Frontend components | 5 files | ~800 lines | 0% |
| Data pipeline | 5 scripts | ~500 lines | 0% |
| **Total** | **22 files** | **~2300 lines** | **0%** |
