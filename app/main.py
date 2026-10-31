"""FastAPI main application – routes, static serving, startup checks."""

# Ensure ChromaDB compatibility with SQLite on Linux hosts
try:
    __import__("pysqlite3")
    import sys
    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except (ImportError, KeyError):
    pass

import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.chatbot import process_message, process_message_stream
from app.config import settings
from app.database import SessionLocal, get_db, init_db
from app.escalation import create_ticket, list_tickets, resolve_ticket
from app.guardrails import mask_pii
from app.llm import check_llm_health, detect_model, get_active_model
from app.memory import memory_store
from app.models import ChatLog, Feedback, Ticket
from app.rag import get_index_count, ingest_documents
from app.sentiment import analyze_sentiment, get_sentiment_summary
from app.schemas import (
    AnalyticsResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    TicketCreate,
    TicketResponse,
)

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-7s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("uniassist.main")

# ── Rate Limiter ────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ── App Lifecycle ───────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("=" * 60)
    logger.info("  UniAssist — AI-Powered Student Support Chatbot")
    logger.info("  Sample Institute of Technology (SIT)")
    logger.info("=" * 60)

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Check LLM availability
    if settings.effective_demo_mode:
        logger.warning("Running in DEMO MODE (no LLM API key configured)")
        logger.warning("Set XAI_API_KEY in .env to enable LLM features")
    else:
        try:
            model = detect_model()
            logger.info(f"LLM configured: model={model}")
        except Exception as e:
            logger.error(f"LLM setup failed: {e}")

    # Check knowledge base index
    count = get_index_count()
    if count == 0:
        logger.info("Knowledge base index is empty. Running automatic initial ingestion...")
        try:
            count = ingest_documents()
            logger.info(f"Knowledge base initialized successfully with {count} chunks.")
        except Exception as e:
            logger.error(f"Automatic ingestion failed: {e}")
    else:
        logger.info(f"Knowledge base: {count} indexed chunks")

    logger.info(f"Server starting at http://localhost:8000")
    logger.info(f"Admin panel at http://localhost:8000/admin")
    logger.info(f"API docs at http://localhost:8000/docs")

    yield

    # Cleanup
    memory_store.cleanup_expired()
    logger.info("Server shutting down")


# ── FastAPI App ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="UniAssist",
    description="AI-Powered Chatbot for University Student Support",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── Admin Auth ──────────────────────────────────────────────────────────────

def verify_admin(request: Request) -> bool:
    """Verify admin password from query param or header."""
    # Check query parameter
    password = request.query_params.get("password", "")
    if not password:
        # Check Authorization header (Basic auth style or custom header)
        auth = request.headers.get("X-Admin-Password", "")
        password = auth

    if not password or password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return True


# ── HTML Pages ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main chat interface."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>UniAssist</h1><p>static/index.html not found</p>")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    """Serve the admin panel."""
    admin_path = static_dir / "admin.html"
    if admin_path.exists():
        return HTMLResponse(content=admin_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>Admin</h1><p>static/admin.html not found</p>")


# ── Health ──────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    llm_ok = False
    if not settings.effective_demo_mode:
        llm_ok = check_llm_health()

    return HealthResponse(
        status="ok",
        llm_reachable=llm_ok,
        index_documents=get_index_count(),
        demo_mode=settings.effective_demo_mode,
        model=get_active_model(),
    )


# ── Chat Endpoints ──────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.rate_limit_per_min}/minute")
async def chat(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
    """Non-streaming chat endpoint."""
    start = time.time()

    # Mask PII in stored logs
    masked_message = mask_pii(body.message)

    response = process_message(body.message, body.session_id)

    # Log to database
    latency_ms = (time.time() - start) * 1000
    log_entry = ChatLog(
        session_id=body.session_id,
        question=masked_message,
        answer=response.answer[:2000],
        sources=json.dumps([s.model_dump() for s in response.sources]),
        is_fallback=1 if response.is_fallback else 0,
        language=response.language,
        latency_ms=latency_ms,
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)

    response.chat_log_id = log_entry.id
    return response


@app.post("/api/chat/stream")
@limiter.limit(f"{settings.rate_limit_per_min}/minute")
async def chat_stream(request: Request, body: ChatRequest, db: Session = Depends(get_db)):
    """Streaming chat endpoint using SSE."""
    start = time.time()
    masked_message = mask_pii(body.message)

    def event_generator():
        full_answer = ""
        sources_data = []
        meta_data = {}

        for event in process_message_stream(body.message, body.session_id):
            event_type = event["event"]
            data = event["data"]

            if event_type == "token":
                full_answer += data
                yield f"event: token\ndata: {json.dumps(data)}\n\n"
            elif event_type == "sources":
                sources_data = data
                yield f"event: sources\ndata: {json.dumps(data)}\n\n"
            elif event_type == "meta":
                meta_data = data
                yield f"event: meta\ndata: {json.dumps(data)}\n\n"
            elif event_type == "done":
                # Save to database
                latency_ms = (time.time() - start) * 1000
                try:
                    db_session = SessionLocal()
                    log_entry = ChatLog(
                        session_id=body.session_id,
                        question=masked_message,
                        answer=full_answer[:2000],
                        sources=json.dumps(sources_data),
                        is_fallback=1 if meta_data.get("is_fallback") else 0,
                        language=meta_data.get("language", "en"),
                        latency_ms=latency_ms,
                    )
                    db_session.add(log_entry)
                    db_session.commit()
                    chat_log_id = log_entry.id
                    db_session.close()
                except Exception as e:
                    logger.error(f"Failed to save chat log: {e}")
                    chat_log_id = None

                yield f"event: chat_log_id\ndata: {json.dumps(chat_log_id)}\n\n"
                yield f"event: done\ndata: \n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── Feedback ────────────────────────────────────────────────────────────────

@app.post("/api/feedback", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackRequest, db: Session = Depends(get_db)):
    """Submit thumbs up/down feedback."""
    feedback = Feedback(
        session_id=body.session_id,
        chat_log_id=body.chat_log_id,
        question=mask_pii(body.question),
        answer=body.answer[:2000],
        sources=body.sources,
        rating=body.rating,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)

    return FeedbackResponse(
        id=feedback.id,
        rating=feedback.rating,
        created_at=feedback.created_at,
    )


# ── Tickets ─────────────────────────────────────────────────────────────────

@app.post("/api/tickets", response_model=TicketResponse)
async def create_ticket_endpoint(body: TicketCreate, db: Session = Depends(get_db)):
    """Create an escalation ticket."""
    ticket = create_ticket(
        db=db,
        name=body.name,
        student_id=body.student_id,
        email=mask_pii(body.email),
        query=body.query,
    )
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        name=ticket.name,
        student_id=ticket.student_id,
        email=ticket.email,
        query=ticket.query,
        status=ticket.status,
        created_at=ticket.created_at,
    )


# ── Session Management ──────────────────────────────────────────────────────

@app.post("/api/session/clear")
async def clear_session(request: Request):
    """Clear conversation memory for a session."""
    data = await request.json()
    session_id = data.get("session_id", "")
    if session_id:
        memory_store.clear_session(session_id)
    return {"status": "ok"}


# ── Admin API ───────────────────────────────────────────────────────────────

@app.post("/api/admin/login")
async def admin_login(request: Request):
    """Validate admin password."""
    data = await request.json()
    if data.get("password") == settings.admin_password:
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Invalid password")


@app.get("/api/admin/analytics")
async def admin_analytics(request: Request, db: Session = Depends(get_db)):
    """Get analytics data for the admin dashboard."""
    verify_admin(request)

    total_chats = db.query(func.count(ChatLog.id)).scalar() or 0
    total_fallbacks = db.query(func.count(ChatLog.id)).filter(ChatLog.is_fallback == 1).scalar() or 0
    answered = total_chats - total_fallbacks
    answered_ratio = (answered / total_chats * 100) if total_chats > 0 else 0

    thumbs_up = db.query(func.count(Feedback.id)).filter(Feedback.rating == "up").scalar() or 0
    thumbs_down = db.query(func.count(Feedback.id)).filter(Feedback.rating == "down").scalar() or 0
    total_feedback = thumbs_up + thumbs_down
    feedback_ratio = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0

    avg_latency = db.query(func.avg(ChatLog.latency_ms)).scalar() or 0

    open_tickets = db.query(func.count(Ticket.id)).filter(Ticket.status == "open").scalar() or 0
    resolved_tickets = db.query(func.count(Ticket.id)).filter(Ticket.status == "resolved").scalar() or 0

    # Top questions (most common)
    top_q = (
        db.query(ChatLog.question, func.count(ChatLog.id).label("count"))
        .group_by(ChatLog.question)
        .order_by(func.count(ChatLog.id).desc())
        .limit(10)
        .all()
    )
    top_questions = [{"question": q[0][:100], "count": q[1]} for q in top_q]

    return AnalyticsResponse(
        total_chats=total_chats,
        total_fallbacks=total_fallbacks,
        answered_ratio=round(answered_ratio, 1),
        thumbs_up=thumbs_up,
        thumbs_down=thumbs_down,
        feedback_ratio=round(feedback_ratio, 1),
        avg_latency_ms=round(avg_latency, 1),
        open_tickets=open_tickets,
        resolved_tickets=resolved_tickets,
        top_questions=top_questions,
    )


@app.get("/api/analytics/sentiment")
async def get_sentiment_analytics(db: Session = Depends(get_db)):
    """Compute sentiment distribution across recent user queries."""
    recent_logs = (
        db.query(ChatLog.question)
        .order_by(ChatLog.created_at.desc())
        .limit(100)
        .all()
    )
    if not recent_logs:
        return get_sentiment_summary([])
    sentiments = [analyze_sentiment(log[0]) for log in recent_logs if log[0]]
    return get_sentiment_summary(sentiments)


@app.get("/api/admin/tickets")
async def admin_tickets(request: Request, db: Session = Depends(get_db)):
    """List all tickets."""
    verify_admin(request)
    status_filter = request.query_params.get("status")
    tickets = list_tickets(db, status=status_filter)
    return [
        TicketResponse(
            ticket_id=t.ticket_id,
            name=t.name,
            student_id=t.student_id,
            email=t.email,
            query=t.query,
            status=t.status,
            created_at=t.created_at,
            resolved_at=t.resolved_at,
        )
        for t in tickets
    ]


@app.post("/api/admin/tickets/{ticket_id}/resolve")
async def admin_resolve_ticket(ticket_id: str, request: Request, db: Session = Depends(get_db)):
    """Resolve a ticket."""
    verify_admin(request)
    ticket = resolve_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "resolved", "ticket_id": ticket_id}


@app.get("/api/admin/feedback")
async def admin_feedback(request: Request, db: Session = Depends(get_db)):
    """List recent feedback."""
    verify_admin(request)
    feedbacks = db.query(Feedback).order_by(Feedback.created_at.desc()).limit(100).all()
    return [
        {
            "id": f.id,
            "session_id": f.session_id,
            "question": f.question[:200],
            "answer": f.answer[:200],
            "rating": f.rating,
            "created_at": f.created_at.isoformat(),
        }
        for f in feedbacks
    ]


@app.post("/api/admin/upload")
async def admin_upload(
    request: Request,
    file: UploadFile = File(...),
):
    """Upload a new document to the knowledge base."""
    verify_admin(request)

    # Validate file type
    allowed = {".md", ".txt", ".pdf", ".docx"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {', '.join(allowed)}",
        )

    # Save file
    kb_dir = Path(settings.knowledge_base_dir)
    kb_dir.mkdir(parents=True, exist_ok=True)
    save_path = kb_dir / file.filename

    content = await file.read()
    save_path.write_bytes(content)
    logger.info(f"Uploaded document: {file.filename}")

    return {"status": "ok", "filename": file.filename}


@app.post("/api/admin/reindex")
async def admin_reindex(request: Request):
    """Re-index the knowledge base."""
    verify_admin(request)

    count = ingest_documents()
    logger.info(f"Re-indexed: {count} chunks")

    return {"status": "ok", "chunks": count}


# ── Init file for the app package ──────────────────────────────────────────

# Make sure __init__.py exists
init_file = Path(__file__).parent / "__init__.py"
if not init_file.exists():
    init_file.write_text("")
