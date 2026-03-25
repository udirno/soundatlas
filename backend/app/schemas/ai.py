from __future__ import annotations

from pydantic import BaseModel


class AIAskRequest(BaseModel):
    question: str


class AIAskResponse(BaseModel):
    answer: str
    sources: list[str] = []
    query: str


class AISuggestion(BaseModel):
    question: str
