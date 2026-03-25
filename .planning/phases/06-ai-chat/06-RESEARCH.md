# Phase 6: AI Chat - Research

**Researched:** 2026-03-25
**Domain:** Claude API (Anthropic Python SDK), Redis async caching, RAG context assembly, FastAPI async service layer, React chat UI panel
**Confidence:** HIGH

---

## Summary

Phase 6 wires together five existing stubs into a working AI chat feature: a backend RAG context builder, a Claude API call, Redis response caching, `ai_query_log` persistence, and a frontend chat panel. All five pieces are already scaffolded — the `ai.py` route, `AIQueryLog` model, `AIAskRequest`/`AIAskResponse` schemas, `ANTHROPIC_API_KEY` in config, and the Redis client in `requirements.txt` are all in place. The primary work is filling in the logic.

The HealthMap reference project (`/Users/udirno/Desktop/HealthMap`) confirms the intended pattern: an `AIService` class that takes a question + structured context dict, builds a system prompt, calls `client.messages.create(...)`, and returns the text. However, HealthMap does NOT implement Redis caching — that must be designed fresh for SoundAtlas. HealthMap also uses the synchronous `anthropic.Anthropic` client; SoundAtlas uses an async FastAPI stack and must use `anthropic.AsyncAnthropic`.

The Anthropic SDK version available in the system (`0.80.0`) is current and supports `AsyncAnthropic`. The `anthropic` package is not yet in `backend/requirements.txt` — it must be added. The `redis` package (`redis==5.1.0`) is in requirements; its `redis.asyncio` module provides the async client.

**Primary recommendation:** Implement `AIService` as a module-level singleton using `AsyncAnthropic`, build RAG context with three queries (dashboard stats, genre distribution, audio feature averages) reusing existing `analytics_service` functions, cache by SHA-256 hash of the question string, and log every call to `ai_query_log` with `input_tokens + output_tokens` from `response.usage`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | latest (>=0.80.0) | Claude API client | Official SDK; `AsyncAnthropic` matches FastAPI async stack |
| redis (redis.asyncio) | 5.1.0 (already in requirements.txt) | Response caching | Already in Docker Compose and config |
| SQLAlchemy AsyncSession | 2.0.35 (already in use) | `ai_query_log` writes | Consistent with rest of backend |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| hashlib (stdlib) | stdlib | Deterministic cache key from question string | No extra dependency needed |
| time (stdlib) | stdlib | Measure `response_time_ms` | `time.perf_counter()` before/after Claude call |
| lucide-react | already installed (0.553.0 per STACK.md) | MessageSquare icon for chat toggle button | Already in project |
| react-markdown | NOT installed | Render markdown in AI responses | Optional — responses can be plain text if not installed |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SHA-256 hash key | Full question string as key | Hash avoids Redis key length limits; functionally equivalent |
| Batch response (current plan) | Streaming (SSE) | Streaming is more responsive for long answers but requires `EventSource` on frontend and FastAPI `StreamingResponse`; batch is simpler and sufficient for v1 |
| `redis.asyncio.Redis.from_url()` | `aioredis` separate package | `redis.asyncio` is built into `redis>=4.2`; no extra package needed |

**Installation (backend only — `anthropic` is missing):**
```bash
# Add to backend/requirements.txt:
anthropic>=0.80.0
```

**Frontend — no new packages required** unless markdown rendering is desired:
```bash
# Optional:
npm install react-markdown
```

---

## Architecture Patterns

### Recommended Project Structure

New files to create:
```
backend/app/services/ai_service.py       # AIService class: RAG context + Claude call + Redis cache + log write
backend/app/services/redis_client.py     # Module-level async Redis singleton

frontend/src/components/AIChatPanel.tsx  # Chat panel: toggle open/close, message list, suggestion chips, input
```

Files to modify:
```
backend/app/api/routes/ai.py             # Replace stubs with real service calls
backend/app/schemas/ai.py               # Extend AIAskResponse (add cached: bool, tokens: int)
backend/app/config.py                   # ANTHROPIC_API_KEY already present; verify no changes needed
frontend/src/components/HomeClient.tsx   # Add isChatOpen state + AIChatPanel mount + header toggle button
frontend/src/lib/api.ts                  # Add askAI() and fetchSuggestions() functions
```

### Pattern 1: Async AIService with Redis cache and query log

**What:** Module-level singleton `AsyncAnthropic` client. `ask()` method checks Redis first; on miss calls Claude, stores result, logs to `ai_query_log`, returns answer.

**When to use:** Every POST /api/ai/ask request.

**Example:**
```python
# backend/app/services/ai_service.py
import hashlib
import json
import time
from typing import Optional

import anthropic
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert

from app.config import settings
from app.models.ai_query_log import AIQueryLog
from app.services import redis_client

_client: Optional[anthropic.AsyncAnthropic] = None

def get_claude_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client

CACHE_TTL_SECONDS = 3600  # 1 hour
MODEL = "claude-sonnet-4-5-20250929"  # use a real model ID from SDK

def _cache_key(question: str) -> str:
    h = hashlib.sha256(question.strip().lower().encode()).hexdigest()
    return f"ai:ask:{h}"

async def ask(question: str, context: dict, db: AsyncSession) -> dict:
    """Check Redis, call Claude on miss, log result, return answer."""
    key = _cache_key(question)
    redis = await redis_client.get_redis()

    # Cache hit
    cached = await redis.get(key)
    if cached:
        data = json.loads(cached)
        data["cached"] = True
        return data

    # Build prompt
    system_prompt = _build_system_prompt()
    user_content = _build_user_message(question, context)

    # Call Claude
    client = get_claude_client()
    t0 = time.perf_counter()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    answer = response.content[0].text
    total_tokens = response.usage.input_tokens + response.usage.output_tokens

    # Cache result
    payload = {"answer": answer, "cached": False, "tokens": total_tokens}
    await redis.setex(key, CACHE_TTL_SECONDS, json.dumps(payload))

    # Log to ai_query_log
    await db.execute(
        insert(AIQueryLog).values(
            query=question,
            response=answer,
            model_name=MODEL,
            token_count=total_tokens,
            response_time_ms=elapsed_ms,
        )
    )
    await db.commit()

    return payload
```

### Pattern 2: Redis singleton module

**What:** Single async Redis connection pool shared across requests. Initialize lazily on first use.

**When to use:** Imported by `ai_service.py` and any future service needing Redis.

**Example:**
```python
# backend/app/services/redis_client.py
from typing import Optional
import redis.asyncio as aioredis
from app.config import settings

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis

async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
```

### Pattern 3: RAG context assembly from existing analytics_service

**What:** Reuse the three existing `analytics_service` functions to build the structured context dict injected into the Claude prompt.

**When to use:** Called before the `ask()` call inside the route handler.

**Example:**
```python
# backend/app/api/routes/ai.py
from app.services import analytics_service, ai_service

@router.post("/ask", response_model=AIAskResponse)
async def ask_question(request: AIAskRequest, db: AsyncSession = Depends(get_db)) -> AIAskResponse:
    # Build RAG context
    dashboard = await analytics_service.get_dashboard_stats(db)
    genres = await analytics_service.get_genre_distribution(db)
    features = await analytics_service.get_feature_averages(db)

    context = {
        "library_stats": {
            "country_count": dashboard["country_count"],
            "artist_count": dashboard["artist_count"],
            "track_count": dashboard["track_count"],
            "diversity_score": dashboard["diversity_score"],
        },
        "top_countries": dashboard["top_countries"][:10],
        "top_genres": genres["global_genres"][:15],
        "audio_feature_averages": features["global_averages"],
    }

    result = await ai_service.ask(request.question, context, db)
    return AIAskResponse(
        answer=result["answer"],
        query=request.question,
        cached=result["cached"],
        tokens=result.get("tokens"),
    )
```

### Pattern 4: Frontend chat panel toggle (matches CountryPanel pattern)

**What:** `AIChatPanel` is a fixed-position panel (right side, same layer as CountryPanel) controlled by `isChatOpen` state in `HomeClient`. A button in a header-bar area toggles it. On open, show suggestion chips fetched from GET /api/ai/suggestions.

**When to use:** The panel is conditionally mounted in `HomeClient` — same pattern as `CountryPanel`.

**Example:**
```typescript
// HomeClient.tsx additions
const [isChatOpen, setIsChatOpen] = useState(false);

// In JSX:
<button onClick={() => setIsChatOpen(prev => !prev)}>
  <MessageSquare /> Ask AI
</button>

{isChatOpen && (
  <AIChatPanel onClose={() => setIsChatOpen(false)} />
)}
```

### Anti-Patterns to Avoid

- **Instantiating `anthropic.Anthropic` (sync client) in async FastAPI:** Use `AsyncAnthropic` — sync client will block the event loop.
- **Creating a new Redis connection per request:** Use the singleton module. Creating connections in route handlers exhausts connection pool.
- **Storing raw Python `dict` in Redis:** Always `json.dumps()` before `setex` and `json.loads()` after `get`. `decode_responses=True` in the Redis client ensures bytes are decoded automatically.
- **Firing the `ai_query_log` write after returning the response (fire-and-forget):** Use `await db.commit()` inside `ask()` before returning — ensures logs are always persisted even if the caller crashes.
- **Using the synchronous `requests` or `httpx` client inside async route:** Both are fine as long as you use `await` with `httpx.AsyncClient`. The `anthropic.AsyncAnthropic` client handles its own internal `httpx.AsyncClient`.
- **Hardcoding `claude-3-opus-20240229` or other outdated model IDs:** The `anthropic` 0.80.0 SDK lists current valid model IDs as: `claude-sonnet-4-5-20250929`, `claude-haiku-4-5-20251001`, `claude-opus-4-5-20251101`, `claude-3-5-haiku-20241022` among others. Use a haiku or sonnet model for cost/speed balance in chat.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude API calls | Custom HTTP POST to api.anthropic.com | `anthropic.AsyncAnthropic` | Auth, retry logic, streaming, error types all built in |
| Cache key collisions | Manual string truncation | `hashlib.sha256(...).hexdigest()` | Deterministic, collision-resistant, consistent length |
| Redis connection management | Manual socket handling | `redis.asyncio.Redis.from_url()` | Connection pooling, reconnect, decode_responses |
| Token counting | Manual word count | `response.usage.input_tokens + response.usage.output_tokens` | SDK returns exact counts from the API |
| Markdown rendering in chat | Custom parser | `react-markdown` (if added) or plain text | Claude responses contain markdown; rendering improves readability |
| Context formatting | Complex template engine | f-string or `.format()` in service method | Context is a small structured dict; no template engine needed |

**Key insight:** The Anthropic SDK handles retries, auth headers, and API versioning automatically. The only custom logic needed is: prompt construction, cache key hashing, and log insertion.

---

## Common Pitfalls

### Pitfall 1: `anthropic` not in `backend/requirements.txt`
**What goes wrong:** Docker build succeeds but `import anthropic` fails at runtime with `ModuleNotFoundError`.
**Why it happens:** The package was used in HealthMap's venv but never added to SoundAtlas requirements.
**How to avoid:** Add `anthropic>=0.80.0` to `backend/requirements.txt` before any other work.
**Warning signs:** `ModuleNotFoundError: No module named 'anthropic'` in backend logs.

### Pitfall 2: Using synchronous `anthropic.Anthropic` in async route
**What goes wrong:** The event loop blocks while waiting for Claude API (2-10 second calls), causing all other requests to queue up.
**Why it happens:** HealthMap's `ai_service.py` uses sync `anthropic.Anthropic`. SoundAtlas backend is fully async (`async_sessionmaker`, `AsyncSession`).
**How to avoid:** Always use `anthropic.AsyncAnthropic` and `await client.messages.create(...)`.
**Warning signs:** Slow response times even without load; requests to other endpoints stall during AI calls.

### Pitfall 3: Redis decode_responses mismatch
**What goes wrong:** `redis.get(key)` returns `bytes` instead of `str`, causing `json.loads()` to fail with `TypeError`.
**Why it happens:** `Redis.from_url()` defaults to `decode_responses=False`.
**How to avoid:** Always pass `decode_responses=True` to `Redis.from_url()`.
**Warning signs:** `TypeError: the JSON object must be str, bytes or bytearray, not NoneType` or similar.

### Pitfall 4: Cache hit returns stale tokens/response_time
**What goes wrong:** Cached responses logged to `ai_query_log` show `token_count=None` and `response_time_ms=0`.
**Why it happens:** Cache hit path returns before reaching log write, so there's nothing to log for cached responses.
**How to avoid:** Only write to `ai_query_log` on cache miss (inside the `if not cached:` branch). On cache hit, skip the log write — this is correct behavior since no Claude call was made.
**Warning signs:** `ai_query_log` has rows with `token_count IS NULL` — acceptable only for cached rows; investigate if all rows show NULL.

### Pitfall 5: Frontend panel z-index conflict with CountryPanel
**What goes wrong:** `AIChatPanel` and `CountryPanel` both use `z-50` and render at the same position, overlapping when both are open.
**Why it happens:** `CountryPanel` uses `fixed top-0 right-0 w-96 z-50`. If `AIChatPanel` uses the same positioning, they collide.
**How to avoid:** Position `AIChatPanel` on the left side (since `StatsSidebar` is left but closeable) or use a bottom-right fixed button pattern. Alternative: make the header toggle mutually exclusive with `CountryPanel`. Simplest approach for v1: position chat panel differently (e.g., `bottom-4 right-4 w-96 h-[600px]`) so it doesn't overlap the right panel.
**Warning signs:** Panels render on top of each other; one disappears behind the other.

### Pitfall 6: RAG context size exploding Claude prompt tokens
**What goes wrong:** Injecting all 200+ countries and all genres into the prompt uses 10,000+ tokens, increasing cost and latency.
**Why it happens:** The analytics queries return unbounded lists.
**How to avoid:** Cap context: top 10 countries, top 15 genres, and 5 audio feature averages. The existing `analytics_service` functions already return top-N results — use them directly, no extra limiting needed.
**Warning signs:** Unexpected high token counts in `ai_query_log.token_count`.

### Pitfall 7: `db.commit()` in `ai_service.ask()` when session has pending state
**What goes wrong:** The commit inside `ask()` inadvertently commits partial state from the route handler if the session is shared.
**Why it happens:** `AsyncSession` is yielded once per request and shared between the route handler and the service function.
**How to avoid:** The service only INSERTs to `ai_query_log` (no reads that affect other pending writes in this route handler), so the commit is safe. But document this explicitly. A cleaner alternative is to use `db.flush()` and let the route handler commit — evaluate against code complexity.

---

## Code Examples

Verified patterns from official sources and codebase inspection:

### Async Claude call with token capture
```python
# Source: anthropic SDK 0.80.0 AsyncAnthropic.messages.create signature (verified locally)
response = await client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    system="You are a music library analyst...",
    messages=[{"role": "user", "content": user_message}],
)
answer: str = response.content[0].text
input_tokens: int = response.usage.input_tokens
output_tokens: int = response.usage.output_tokens
total_tokens: int = input_tokens + output_tokens
model_used: str = response.model
```

### Async Redis get/set
```python
# Source: redis.asyncio (redis==5.1.0, verified locally)
redis = aioredis.Redis.from_url("redis://localhost:6379", decode_responses=True)

# Cache write
await redis.setex("ai:ask:abc123", 3600, json.dumps({"answer": "...", "cached": False}))

# Cache read
raw = await redis.get("ai:ask:abc123")
if raw:
    data = json.loads(raw)  # returns dict since decode_responses=True
```

### AIQueryLog insert (async SQLAlchemy)
```python
# Source: existing SoundAtlas pattern in analytics_service.py (select + execute)
from sqlalchemy import insert
from app.models.ai_query_log import AIQueryLog

await db.execute(
    insert(AIQueryLog).values(
        query=question,
        response=answer,
        model_name=model_name,
        token_count=total_tokens,
        response_time_ms=elapsed_ms,
    )
)
await db.commit()
```

### Frontend API client additions
```typescript
// Source: existing api.ts pattern (fetchCountryDetail)
export interface AIAskRequest {
  question: string;
}

export interface AIAskResponse {
  answer: string;
  query: string;
  sources: string[];
  cached?: boolean;
  tokens?: number;
}

export interface AISuggestion {
  question: string;
}

export async function askAI(question: string): Promise<AIAskResponse> {
  const res = await fetch(`${getBaseUrl()}/api/ai/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error(`AI ask failed: ${res.status}`);
  return res.json() as Promise<AIAskResponse>;
}

export async function fetchAISuggestions(): Promise<AISuggestion[]> {
  const res = await fetch(`${getBaseUrl()}/api/ai/suggestions`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`Suggestions failed: ${res.status}`);
  return res.json() as Promise<AISuggestion[]>;
}
```

### AIChatPanel component structure
```typescript
// Source: HealthMap AIInsightPanel.tsx pattern adapted for SoundAtlas
'use client';

import { useState, useEffect, useRef } from 'react';
import { askAI, fetchAISuggestions, AISuggestion, AIAskResponse } from '@/lib/api';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AIChatPanelProps {
  onClose: () => void;
}

export default function AIChatPanel({ onClose }: AIChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    fetchAISuggestions().then(setSuggestions).catch(() => {});
  }, []);

  async function handleSend(question?: string) {
    const text = (question ?? input).trim();
    if (!text || isLoading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setIsLoading(true);
    try {
      const result = await askAI(text);
      setMessages(prev => [...prev, { role: 'assistant', content: result.answer }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error generating answer. Please try again.' }]);
    } finally {
      setIsLoading(false);
    }
  }

  // ... JSX render
}
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `anthropic.Anthropic` (sync) | `anthropic.AsyncAnthropic` | SDK 0.x, always available | Required for FastAPI async; HealthMap used sync client with sync SQLAlchemy |
| `claude-3-opus-20240229` model | `claude-sonnet-4-5-20250929` or `claude-3-5-haiku-20241022` | 2025 model releases | Better price/performance; haiku for simple Q&A, sonnet for nuanced answers |
| Separate `aioredis` package | `redis.asyncio` (built into `redis>=4.2`) | redis-py 4.2 (2022) | No extra package; `redis.asyncio.Redis` is the standard async client |
| `response.content[0].text` | Same — still correct | — | `content` is a list of blocks; `[0].text` is always the text for non-streaming |

**Deprecated/outdated:**
- `aioredis` as a separate package: replaced by `redis.asyncio`; do not add `aioredis` to requirements.
- `claude-2`, `claude-instant-1.2`: removed from API; will return errors if used.
- HealthMap's sync `ai_service.py` pattern: not portable to SoundAtlas async stack.

---

## Open Questions

1. **Should `AIChatPanel` be a floating overlay or a fixed sidebar?**
   - What we know: `CountryPanel` occupies `fixed top-0 right-0 h-screen w-96`. `StatsSidebar` occupies `fixed top-0 left-0 w-72`.
   - What's unclear: If CountryPanel is open alongside AIChatPanel, do they conflict? The planner must decide positioning.
   - Recommendation: Position AIChatPanel as a fixed bottom-right floating panel (`fixed bottom-4 right-4 w-96 h-[580px]`) to avoid collision with CountryPanel on the right and StatsSidebar on the left. The toggle button can live in a thin header strip above the map.

2. **Should suggestion chips reappear after each AI response or only on first open?**
   - What we know: HealthMap hides suggestions after 3 messages. SoundAtlas requirement only says "shown when chat is first opened."
   - What's unclear: Whether chips should reappear after conversation ends or panel is closed/reopened.
   - Recommendation: Show suggestions only when `messages.length === 0` (fresh open). This matches the requirement literally and avoids complexity.

3. **Is `react-markdown` available or should plain text be used?**
   - What we know: `react-markdown` is NOT in `frontend/package.json`. Claude responses contain markdown.
   - What's unclear: Whether the planner wants to add a package dependency.
   - Recommendation: Add `react-markdown` to frontend dependencies. The package is lightweight (30KB), well-maintained, and Claude's markdown responses (bold, lists, headers) render poorly as raw text. If not added, use `white-space: pre-wrap` as a fallback.

4. **Cache invalidation strategy**
   - What we know: The requirement says "same question twice returns cached response."
   - What's unclear: Whether the cache should be invalidated when the user's library changes (e.g., after re-importing data).
   - Recommendation: Use TTL-based expiry (1 hour) for v1. No event-based invalidation needed. If library data changes, stale answers expire naturally. If immediate invalidation is needed, add a `DELETE /api/ai/cache` admin endpoint later.

---

## Sources

### Primary (HIGH confidence)
- anthropic SDK 0.80.0 — inspected locally: `AsyncAnthropic`, `messages.create()` signature, `Usage.input_tokens`, `Usage.output_tokens`, valid model IDs
- redis 5.1.0 — inspected locally: `redis.asyncio.Redis.from_url()`, `.get()`, `.setex()` signatures
- SoundAtlas codebase — inspected: `ai.py` route stub, `AIQueryLog` model, `AIAskRequest`/`AIAskResponse` schemas, `analytics_service.py`, `config.py`, `database.py`, existing frontend components
- HealthMap codebase — inspected: `ai_service.py` service class, `AIInsightPanel.tsx` component, `insights.py` route

### Secondary (MEDIUM confidence)
- `frontend/package.json` — verified `react-markdown` is absent; `lucide-react` confirmed available via STACK.md

### Tertiary (LOW confidence)
- None — all findings verified from source code or local package inspection

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified from requirements.txt, local package inspection, and SDK introspection
- Architecture: HIGH — verified against existing codebase patterns (analytics_service, CountryPanel, HomeClient)
- Pitfalls: HIGH — derived from HealthMap code review and direct inspection of type signatures
- Redis caching pattern: HIGH — verified from redis.asyncio API and standard FastAPI async patterns
- Frontend panel positioning: MEDIUM — requires planner decision on layout (CountryPanel conflict)

**Research date:** 2026-03-25
**Valid until:** 2026-05-25 (stable stack; Anthropic model IDs may change faster — re-verify if > 30 days)
