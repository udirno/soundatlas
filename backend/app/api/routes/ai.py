from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import AIAskRequest, AIAskResponse, AISuggestion
from app.services import analytics_service, ai_service

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/ask", response_model=AIAskResponse)
async def ask_question(
    request: AIAskRequest,
    db: AsyncSession = Depends(get_db),
) -> AIAskResponse:
    """Answer a natural language question about the user's music library using Claude."""
    # Build RAG context from analytics service
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
        sources=[],
    )


@router.get("/suggestions", response_model=list[AISuggestion])
async def get_suggestions() -> list[AISuggestion]:
    """Return pre-built question suggestions for the AI interface."""
    return [
        AISuggestion(question="Which countries dominate my library?"),
        AISuggestion(question="What's the most represented genre?"),
        AISuggestion(question="Which artists have the highest danceability?"),
        AISuggestion(question="How diverse is my music library geographically?"),
        AISuggestion(question="What are the common audio features across my top countries?"),
    ]
