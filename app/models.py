"""SQLAlchemy models for UniAssist."""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


class ChatLog(Base):
    """Stores every chat interaction for analytics."""

    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), index=True, nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, default="")  # JSON list of source labels
    is_fallback = Column(Integer, default=0)  # 1 if the bot fell back
    language = Column(String(16), default="en")
    latency_ms = Column(Float, default=0.0)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Feedback(Base):
    """Thumbs-up / thumbs-down feedback on answers."""

    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False)
    chat_log_id = Column(Integer, nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    sources = Column(Text, default="")
    rating = Column(String(8), nullable=False)  # "up" or "down"
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class Ticket(Base):
    """Escalation / support tickets."""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(String(16), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    student_id = Column(String(32), nullable=False)
    email = Column(String(128), nullable=False)
    query = Column(Text, nullable=False)
    status = Column(String(16), default="open")  # open / resolved
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at = Column(DateTime, nullable=True)
