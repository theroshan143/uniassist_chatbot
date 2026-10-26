"""Escalation: ticket creation and management."""

import logging
import random
import string
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Ticket

logger = logging.getLogger("uniassist.escalation")


def generate_ticket_id() -> str:
    """Generate a unique ticket ID like 'TKT-A3F7B2'."""
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=6))
    return f"TKT-{suffix}"


def create_ticket(
    db: Session,
    name: str,
    student_id: str,
    email: str,
    query: str,
) -> Ticket:
    """Create a new escalation ticket."""
    ticket = Ticket(
        ticket_id=generate_ticket_id(),
        name=name,
        student_id=student_id,
        email=email,
        query=query,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    logger.info(f"Created ticket {ticket.ticket_id} for {name}")
    return ticket


def list_tickets(db: Session, status: str | None = None) -> list[Ticket]:
    """List all tickets, optionally filtered by status."""
    query = db.query(Ticket).order_by(Ticket.created_at.desc())
    if status:
        query = query.filter(Ticket.status == status)
    return query.all()


def resolve_ticket(db: Session, ticket_id: str) -> Ticket | None:
    """Mark a ticket as resolved."""
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if ticket:
        ticket.status = "resolved"
        ticket.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(ticket)
        logger.info(f"Resolved ticket {ticket_id}")
    return ticket
