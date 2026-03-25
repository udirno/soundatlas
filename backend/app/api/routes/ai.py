from __future__ import annotations

from fastapi import APIRouter

from app.schemas.ai import AIAskRequest, AIAskResponse, AISuggestion

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/ask", response_model=AIAskResponse)
async def ask_question(request: AIAskRequest) -> AIAskResponse:
    """Stub endpoint — AI integration coming in Phase 6."""
    return AIAskResponse(
        answer="AI integration coming in Phase 6. Your question was received.",
        sources=[],
        query=request.question,
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
