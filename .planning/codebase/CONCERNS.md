# Concerns

> Technical debt, security issues, performance risks, and fragile areas in HealthMap

## Security Issues

### Critical
1. **No authentication or authorization** — All API endpoints are publicly accessible. No user model, no JWT, no API key validation. Anyone can query disease data, trigger AI insights, and call the seed endpoint.
2. **Unvalidated API keys** — `ANTHROPIC_API_KEY` and `OPENWEATHER_API_KEY` default to empty strings in `backend/app/config.py:12-13`. No validation that keys are present before calling external APIs.
3. **No rate limiting** — No throttling on any endpoint, including the AI insight endpoint which calls Anthropic's API (billable). A single user could run up significant API costs.
4. **No input validation on AI prompts** — User questions pass directly to Claude in `backend/app/services/ai_service.py:59`. No sanitization or length limits.

### Moderate
5. **Overly permissive CORS** — `allow_methods=["*"]`, `allow_headers=["*"]` in `backend/app/main.py:27-31`. Should restrict to actual methods used.
6. **DEBUG mode defaults to True** — `backend/app/config.py:20` sets `DEBUG: bool = True`. Production deployments inherit this if env var not set.
7. **Seed endpoint in production** — `POST /api/seed` in `backend/app/main.py:47` is always available, not gated by environment.

## Performance Issues

### Database
1. **No composite unique constraints** on `disease_records` — Missing `UNIQUE(disease_id, region_id, date)` in `database/init.sql:26-40` allows duplicate records per disease/region/date.
2. **Full table scans in correlation service** — `backend/app/services/correlation_service.py:70-94` loads all disease and climate records into memory, then joins in Python. Should use SQL JOINs.
3. **N+1 query pattern** — `correlation_service.py:152-160` `get_all_correlations` calls `compute_disease_climate_correlation` 3 times, each making separate DB queries for the same disease/region.
4. **Missing indexes** — No index on `disease_records(disease_id, region_id, date)` composite. Existing indexes cover `(disease_id, region_id)` and `(date)` separately.

### Caching
5. **Redis available but unused** — Redis is in `requirements.txt` and `docker-compose.yml` but no caching is implemented anywhere. Expensive correlation and AI queries re-execute every time.

### Frontend
6. **No data caching** — API client in `frontend/src/lib/api-client.ts` makes fresh requests every time. No React Query, SWR, or similar.
7. **Mapbox re-initialization risk** — `frontend/src/components/map/MapContainer.tsx:125` removes all `useEffect` dependencies to prevent re-renders, but this means the map never updates its closure over `selectedRegion` for initial layer setup.

## Technical Debt

### Architecture
1. **Monolithic seed endpoint** — `backend/app/main.py:47-186` contains 140 lines of data seeding logic directly in `main.py`. Should be a management command or separate script.
2. **Statistical approximations** — `correlation_service.py:31` uses a simplified p-value formula (`p = 2.0 * (1.0 / (1.0 + abs(t_stat)))`) that is not statistically accurate. Noted as "good enough for display" but could mislead users.
3. **Hardcoded model name** — `ai_service.py:79,117` hardcodes `"claude-sonnet-4-20250514"`. Should be configurable.
4. **No error handling in data pipeline** — Ingestion scripts in `data-pipeline/scripts/` lack try/except blocks and don't log failures to `data_ingestion_log` table.

### Code Quality
5. **Inline imports** — `main.py:50,169` uses inline `import random` and `__import__('math')`. Non-standard pattern.
6. **Empty utils module** — `backend/app/utils/__init__.py` exists but is empty.
7. **Empty core module** — `backend/app/core/__init__.py` exists but is empty.

## Fragile Areas

1. **AI service dependency** — `backend/app/services/ai_service.py` is a single point of failure. If Anthropic API is down or key is invalid, the insight panel breaks. Error handling returns raw error strings to the client.
2. **Correlation calculation** — Pure-Python statistical functions in `correlation_service.py:11-46` without any test coverage. Manual Pearson/Spearman implementations are easy to get wrong.
3. **Date parsing** — `trend_service.py` accepts string dates (`start_date: str`) while `disease_service.py` accepts `date` objects. Inconsistent typing across services.
4. **Region code matching** — Frontend uses ISO 3166-1 alpha-3 codes from Mapbox (`iso_3166_1_alpha_3` in `MapContainer.tsx:91,110`), backend seeds with custom codes. Must stay in sync manually.

## Scaling Limitations

1. **20-country seed limit** — Only 20 countries seeded in `main.py:61-82`. Adding more requires code changes.
2. **No pagination** — API endpoints return all records. For large datasets this will timeout or OOM.
3. **Synchronous DB queries** — All SQLAlchemy queries are synchronous despite FastAPI being async. Uses sync `Session` throughout.
4. **Single-threaded AI calls** — AI insight generation blocks until Claude responds. No async/streaming.

## Zero Test Coverage

- **0 unit tests** across the entire codebase
- **0 integration tests** for API endpoints
- **0 E2E tests** for frontend workflows
- No test framework configured for either backend or frontend
- ~2300 lines of untested application code
- See `TESTING.md` for detailed breakdown

## Deployment Concerns

1. **Environment variable mismatch** — `render.yaml` and `docker-compose.yml` may define different env vars than `backend/app/config.py` expects.
2. **No health check depth** — `/health` endpoint returns `{"status": "healthy"}` without checking DB or Redis connectivity.
3. **`dump.rdb` committed** — `backend/dump.rdb` (Redis dump file) is in the repo. Should be in `.gitignore`.
4. **Multiple `runtime.txt` files** — Root and `backend/` both have `runtime.txt`, potentially conflicting.
