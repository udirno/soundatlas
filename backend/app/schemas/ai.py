from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class AIAskRequest(BaseModel):
    question: str


class AIAskResponse(BaseModel):
    answer: str
    sources: list[str] = []
    query: str
    cached: bool = False
    tokens: Optional[int] = None


class AISuggestion(BaseModel):
    question: str
