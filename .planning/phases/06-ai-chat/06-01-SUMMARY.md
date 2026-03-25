---
phase: 06-ai-chat
plan: 01
subsystem: api
tags: [anthropic, claude, redis, caching, rag, ai, async]

# Dependency graph
requires:
  - phase: 03-backend-api
    provides: "analytics_service with get_dashboard_stats, get_genre_distribution, get_feature_averages"
  - phase: 01-infrastructure
    provides: "redis service in docker-compose, REDIS_URL in settings, AIQueryLog model"
provides:
  - "Async Redis singleton (get_redis, close_redis) via redis.asyncio"
  - "AIService ask() with RAG context assembly, AsyncAnthropic Claude call, Redis caching, ai_query_log insert"
  - "POST /api/ai/ask endpoint returning data-grounded answers with cached/tokens fields"
  - "GET /api/ai/suggestions returning 5 example questions"
affects: [06-02]

# Tech tracking
tech-stack:
  added: [anthropic>=0.80.0, AsyncAnthropic, redis.asyncio]
  patterns:
    - "Module-level Optional singleton with lazy init for external clients (Claude, Redis)"
    - "SHA-256 cache key with namespace prefix (ai:ask:) for Redis collision avoidance"
    - "Cache-check before API call; log only on cache miss (accurate token/time accounting)"
    - "RAG context assembled from analytics_service before every Claude call"

key-files:
  created:
    - backend/app/services/redis_client.py
    - backend/app/services/ai_service.py
  modified:
    - backend/requirements.txt
    - backend/app/schemas/ai.py
    - backend/app/api/routes/ai.py
    - docker-compose.yml

key-decisions:
  - "REDIS_URL overridden in docker-compose.yml to redis://redis:6379 — same pattern as DATABASE_URL; .env localhost:6379 is for host access only"
  - "Use redis.asyncio (NOT deprecated aioredis package) — redis==5.1.0 already in requirements.txt bundles asyncio support"
  - "Use AsyncAnthropic (NOT sync Anthropic) — backend is fully async; sync client would block event loop"
  - "Log to ai_query_log only on cache miss — cache hits made no Claude call, so no tokens or timing to record"
  - "Cache key = SHA-256(question.strip().lower()) with ai:ask: prefix — case/whitespace insensitive, namespace-safe"
  - "MODEL = claude-sonnet-4-5-20250929, MAX_TOKENS = 1024, CACHE_TTL_SECONDS = 3600"

patterns-established:
  - "Singleton pattern: module-level Optional[T] + lazy init function for AsyncAnthropic and Redis clients"
  - "RAG pattern: fetch analytics context → format as structured text → prepend to user question → send to LLM"

# Metrics
duration: 15min
completed: 2026-03-25
---

# Phase 6 Plan 01: AI Chat Backend Summary

**Claude AI chat with Redis caching and RAG context from analytics: POST /api/ai/ask answers natural language questions about the user's music library using AsyncAnthropic, with Redis 1-hour cache and ai_query_log persistence on cache miss.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-03-25T08:17:47Z
- **Completed:** 2026-03-25T08:32:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Async Redis singleton (`redis_client.py`) with lazy init, using `redis.asyncio` from the already-installed `redis==5.1.0` package
- `ai_service.ask()` with full pipeline: cache check → RAG context assembly → AsyncAnthropic call → cache write → ai_query_log insert
- Real endpoints replacing stubs: POST `/api/ai/ask` returns Claude-grounded answers, GET `/api/ai/suggestions` returns 5 example questions
- Fixed Redis container networking so backend container can reach Redis service

## Task Commits

Each task was committed atomically:

1. **Task 1: Redis client singleton and AIService** - `0be3b5c` (feat)
2. **Task 2: Extend AI schemas and replace route stubs** - `615d44e` (feat)

## Files Created/Modified

- `backend/app/services/redis_client.py` - Async Redis singleton (get_redis, close_redis)
- `backend/app/services/ai_service.py` - Claude API integration with RAG context assembly, SHA-256 caching, ai_query_log logging
- `backend/requirements.txt` - Added anthropic>=0.80.0
- `backend/app/schemas/ai.py` - Added cached: bool and tokens: Optional[int] to AIAskResponse
- `backend/app/api/routes/ai.py` - Replaced stub with real RAG-powered implementation
- `docker-compose.yml` - Added REDIS_URL=redis://redis:6379 override for backend service

## Decisions Made

- `REDIS_URL` overridden in docker-compose.yml environment section (`redis://redis:6379`) — same pattern established in 01-01 for `DATABASE_URL`; the `.env` localhost:6379 value is only valid on the host
- `AsyncAnthropic` used throughout — sync `Anthropic` would block the async event loop
- `redis.asyncio` used (NOT the deprecated `aioredis` package) — bundled in `redis==5.1.0` already in requirements
- ai_query_log writes only on cache miss — cache hits have no tokens/timing to record accurately
- `MODEL = "claude-sonnet-4-5-20250929"` per plan specification

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed Redis container hostname in docker-compose.yml**
- **Found during:** Task 2 verification (testing POST /api/ai/ask)
- **Issue:** Backend container was connecting to `localhost:6379` (from .env) but Redis runs at `redis:6379` in Docker networking; same root cause as the DATABASE_URL issue from Phase 1
- **Fix:** Added `REDIS_URL: redis://redis:6379` to backend service `environment` block in docker-compose.yml, overriding the .env value inside the container
- **Files modified:** `docker-compose.yml`
- **Verification:** `docker compose exec backend python -c "from app.config import settings; print(settings.REDIS_URL)"` shows `redis://redis:6379`; subsequent POST /api/ai/ask returns 200 with Claude response
- **Committed in:** `615d44e` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug)
**Impact on plan:** Fix was essential for functionality; same infrastructure pattern as Phase 1. No scope creep.

## Issues Encountered

None beyond the auto-fixed Redis hostname bug.

## Next Phase Readiness

- POST `/api/ai/ask` is production-ready for Phase 6 Plan 02 (frontend chat UI)
- GET `/api/ai/suggestions` provides the static list the chat UI will display on open
- Redis caching prevents duplicate Claude API calls on page reload / repeated questions
- `cached` and `tokens` fields in response can be displayed in chat UI for transparency

---
*Phase: 06-ai-chat*
*Completed: 2026-03-25*
