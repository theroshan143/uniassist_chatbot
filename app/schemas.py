"""Pydantic schemas for API request / response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Chat ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Incoming chat message."""
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=64)


class SourceInfo(BaseModel):
    """A retrieved source chunk reference."""
    title: str
    section: str
    file: str
    score: float = 0.0


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    answer: str
    sources: list[SourceInfo] = []
    is_fallback: bool = False
    follow_ups: list[str] = []
    language: str = "en"
    chat_log_id: int | None = None


# ── Feedback ────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    """Thumbs up/down feedback on an answer."""
    session_id: str
    question: str
    answer: str
    sources: str = ""
    rating: str = Field(..., pattern=r"^(up|down)$")
    chat_log_id: int | None = None


class FeedbackResponse(BaseModel):
    id: int
    rating: str
    created_at: datetime


# ── Tickets ─────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    """Create a new escalation ticket."""
    name: str = Field(..., min_length=1, max_length=128)
    student_id: str = Field(..., min_length=1, max_length=32)
    email: str = Field(..., min_length=3, max_length=128)
    query: str = Field(..., min_length=1, max_length=2000)


class TicketResponse(BaseModel):
    ticket_id: str
    name: str
    student_id: str
    email: str
    query: str
    status: str
    created_at: datetime
    resolved_at: datetime | None = None


# ── Admin ───────────────────────────────────────────────────────────────────

class AnalyticsResponse(BaseModel):
    """Dashboard analytics data."""
    total_chats: int = 0
    total_fallbacks: int = 0
    answered_ratio: float = 0.0
    thumbs_up: int = 0
    thumbs_down: int = 0
    feedback_ratio: float = 0.0
    avg_latency_ms: float = 0.0
    open_tickets: int = 0
    resolved_tickets: int = 0
    top_questions: list[dict] = []


# ── Health ──────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    llm_reachable: bool
    index_documents: int
    demo_mode: bool
    model: str
