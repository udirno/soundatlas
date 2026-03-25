from __future__ import annotations

import hashlib
import json
import time
from typing import Optional

import anthropic
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_query_log import AIQueryLog
from app.services import redis_client

CACHE_TTL_SECONDS = 3600
MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 1024

_client: Optional[anthropic.AsyncAnthropic] = None


def get_claude_client() -> anthropic.AsyncAnthropic:
    """Return the AsyncAnthropic singleton, creating it lazily on first call."""
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _cache_key(question: str) -> str:
    """Return a Redis key for the given question using SHA-256."""
    digest = hashlib.sha256(question.strip().lower().encode()).hexdigest()
    return f"ai:ask:{digest}"


def _build_system_prompt() -> str:
    """Return a system prompt instructing Claude to act as a music library analyst."""
    return (
        "You are a music library analyst for SoundAtlas, a tool that helps users "
        "explore the geographic and stylistic diversity of their personal music library. "
        "Answer questions based on the listening data context provided. "
        "Keep answers concise (2-3 paragraphs max). "
        "Mention specific numbers from the data when relevant. "
        "If the data does not contain enough information to answer a question, say so clearly."
    )


def _build_user_message(question: str, context: dict) -> str:
    """Format context and question into a user message for Claude."""
    library_stats = context.get("library_stats", {})
    top_countries = context.get("top_countries", [])
    top_genres = context.get("top_genres", [])
    audio_features = context.get("audio_feature_averages", {})

    lines = ["=== Library Statistics ==="]
    lines.append(f"Countries represented: {library_stats.get('country_count', 'N/A')}")
    lines.append(f"Total artists: {library_stats.get('artist_count', 'N/A')}")
    lines.append(f"Total tracks: {library_stats.get('track_count', 'N/A')}")
    lines.append(f"Diversity score (0-1): {library_stats.get('diversity_score', 'N/A')}")

    lines.append("\n=== Top Countries by Artist Count ===")
    for i, c in enumerate(top_countries[:10], 1):
        lines.append(f"{i}. {c.get('name', 'Unknown')} — {c.get('artist_count', 0)} artists")

    lines.append("\n=== Top Genres ===")
    for i, g in enumerate(top_genres[:15], 1):
        lines.append(f"{i}. {g.get('genre', 'Unknown')} — {g.get('count', 0)} artists")

    if audio_features:
        lines.append("\n=== Audio Feature Averages (0-1 scale unless noted) ===")
        for feature, value in audio_features.items():
            if value is not None:
                if feature == "tempo":
                    lines.append(f"  {feature}: {round(value, 1)} BPM")
                else:
                    lines.append(f"  {feature}: {round(value, 3)}")
    else:
        lines.append("\n=== Audio Feature Averages ===")
        lines.append("(No audio feature data available)")

    lines.append(f"\n=== User Question ===")
    lines.append(question)

    return "\n".join(lines)


async def ask(question: str, context: dict, db: AsyncSession) -> dict:
    """
    Ask Claude a question grounded in the user's music library data.

    Returns a dict with keys: answer, cached, tokens.
    Cache hits skip the Claude API call. Only cache misses are logged to ai_query_log.
    """
    redis = await redis_client.get_redis()
    key = _cache_key(question)

    # Check cache first
    cached_raw = await redis.get(key)
    if cached_raw is not None:
        result = json.loads(cached_raw)
        result["cached"] = True
        return result

    # Cache miss — call Claude
    client = get_claude_client()
    system_prompt = _build_system_prompt()
    user_content = _build_user_message(question, context)

    t_start = time.perf_counter()
    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    t_end = time.perf_counter()

    answer = response.content[0].text
    total_tokens = response.usage.input_tokens + response.usage.output_tokens
    elapsed_ms = int((t_end - t_start) * 1000)

    # Cache the result
    payload = {"answer": answer, "cached": False, "tokens": total_tokens}
    await redis.setex(key, CACHE_TTL_SECONDS, json.dumps(payload))

    # Log to ai_query_log (only on cache miss — no API call was made for hits)
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
