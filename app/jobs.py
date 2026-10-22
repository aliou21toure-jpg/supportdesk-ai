"""Background jobs, executed by the RQ worker process (see app/worker.py)."""

import logging
import uuid
from datetime import UTC, datetime

from app.ai.factory import build_provider
from app.config import get_settings
from app.db import get_sessionmaker
from app.knowledge import search_articles
from app.models import Ticket
from app.redaction import redact

log = logging.getLogger(__name__)


def triage_ticket(ticket_id: str) -> str:
    """Classify a ticket and draft a reply.

    Safe to run more than once (idempotent): it just recomputes the fields.
    On failure the error is recorded and re-raised so RQ can retry with backoff.
    """
    Session = get_sessionmaker()
    with Session() as db:
        ticket = db.get(Ticket, uuid.UUID(ticket_id))
        if ticket is None:
            log.warning("ticket %s no longer exists; skipping", ticket_id)
            return "missing"

        ticket.ai_status = "processing"
        ticket.ai_attempts += 1
        db.commit()

        try:
            provider = build_provider(get_settings())
            subject, body = redact(ticket.subject), redact(ticket.body)
            knowledge = search_articles(db, f"{subject} {body}")
            result = provider.triage(subject, body, knowledge)
        except Exception as exc:
            db.rollback()
            ticket.ai_status = "failed"
            ticket.ai_error = f"{type(exc).__name__}: {exc}"[:500]
            db.commit()
            log.exception("triage failed for %s", ticket_id)
            raise

        ticket.category = result.category
        ticket.priority = result.priority
        ticket.sentiment = result.sentiment
        ticket.ai_summary = result.summary
        ticket.ai_suggested_reply = result.suggested_reply
        ticket.ai_provider = provider.name
        ticket.ai_status = "done"
        ticket.ai_error = None
        ticket.triaged_at = datetime.now(UTC)
        db.commit()
        return "done"
