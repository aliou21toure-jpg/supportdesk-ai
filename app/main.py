import uuid
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app import queue
from app.db import get_db
from app.knowledge import search_articles
from app.models import Article, Reply, Ticket
from app.schemas import (
    AiStatus,
    ArticleCreate,
    ArticleOut,
    ReplyCreate,
    ReplyOut,
    TicketCreate,
    TicketCreated,
    TicketDetail,
    TicketPage,
    TicketStatus,
    TicketUpdate,
)
from app.security import require_agent

app = FastAPI(
    title="SupportDesk AI",
    version="1.0.0",
    description="Customer support tickets with background AI triage (category, priority, draft reply).",
)

DB = Annotated[Session, Depends(get_db)]
agent_only = [Depends(require_agent)]


def _get_ticket(db: Session, ticket_id: uuid.UUID) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


@app.get("/health")
def health(db: DB) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    queue.get_queue().connection.ping()
    return {"status": "ok"}


# ---------- public: customers submit tickets ----------


@app.post("/tickets", status_code=status.HTTP_201_CREATED, response_model=TicketCreated)
def create_ticket(payload: TicketCreate, db: DB) -> Ticket:
    """Save the ticket and return immediately; AI triage happens in the background worker."""
    ticket = Ticket(**payload.model_dump())
    db.add(ticket)
    db.commit()
    queue.enqueue_triage(str(ticket.id))
    db.refresh(ticket)
    return ticket


# ---------- agents ----------


@app.get("/tickets", response_model=TicketPage, dependencies=agent_only)
def list_tickets(
    db: DB,
    status_: Annotated[TicketStatus | None, Query(alias="status")] = None,
    category: str | None = None,
    priority: str | None = None,
    ai_status: AiStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TicketPage:
    filters = []
    if status_:
        filters.append(Ticket.status == status_)
    if category:
        filters.append(Ticket.category == category)
    if priority:
        filters.append(Ticket.priority == priority)
    if ai_status:
        filters.append(Ticket.ai_status == ai_status)

    # Most urgent first, then oldest first within the same priority.
    priority_rank = func.array_position(
        text("ARRAY['urgent','high','medium','low']::varchar[]"), Ticket.priority
    )
    items = db.scalars(
        select(Ticket)
        .where(*filters)
        .order_by(priority_rank.asc().nulls_last(), Ticket.created_at.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    total = db.scalar(select(func.count()).select_from(Ticket).where(*filters)) or 0
    return TicketPage(items=items, total=total)  # type: ignore[arg-type]


@app.get("/tickets/{ticket_id}", response_model=TicketDetail, dependencies=agent_only)
def get_ticket(ticket_id: uuid.UUID, db: DB) -> Ticket:
    ticket = db.scalar(select(Ticket).options(selectinload(Ticket.replies)).where(Ticket.id == ticket_id))
    if ticket is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket not found")
    return ticket


@app.patch("/tickets/{ticket_id}", response_model=TicketDetail, dependencies=agent_only)
def update_ticket(ticket_id: uuid.UUID, payload: TicketUpdate, db: DB) -> Ticket:
    ticket = _get_ticket(db, ticket_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Provide at least one field")
    for field, value in changes.items():
        setattr(ticket, field, value)
    db.commit()
    db.refresh(ticket)
    return ticket


@app.post(
    "/tickets/{ticket_id}/replies",
    status_code=status.HTTP_201_CREATED,
    response_model=ReplyOut,
    dependencies=agent_only,
)
def reply_to_ticket(ticket_id: uuid.UUID, payload: ReplyCreate, db: DB) -> Reply:
    """Agents reply in their own words, or send the AI draft after reviewing it."""
    ticket = _get_ticket(db, ticket_id)
    if payload.use_ai_draft:
        if not ticket.ai_suggested_reply:
            raise HTTPException(status.HTTP_409_CONFLICT, "No AI draft available for this ticket yet")
        body, ai_assisted = ticket.ai_suggested_reply, True
    elif payload.body:
        body, ai_assisted = payload.body, False
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Provide a body or set use_ai_draft")

    reply = Reply(ticket_id=ticket.id, author=payload.author, body=body, ai_assisted=ai_assisted)
    db.add(reply)
    ticket.status = "pending"  # waiting on the customer
    db.commit()
    db.refresh(reply)
    return reply


@app.post("/tickets/{ticket_id}/retriage", status_code=status.HTTP_202_ACCEPTED, dependencies=agent_only)
def retriage(ticket_id: uuid.UUID, db: DB) -> dict[str, str]:
    ticket = _get_ticket(db, ticket_id)
    ticket.ai_status = "pending"
    db.commit()
    queue.enqueue_triage(str(ticket.id))
    return {"status": "queued"}


@app.get("/stats", dependencies=agent_only)
def stats(db: DB) -> dict[str, dict[str, int]]:
    def count_by(column) -> dict[str, int]:  # noqa: ANN001
        rows = db.execute(select(column, func.count()).group_by(column)).all()
        return {str(k): n for k, n in rows if k is not None}

    return {
        "status": count_by(Ticket.status),
        "category": count_by(Ticket.category),
        "priority": count_by(Ticket.priority),
        "ai_status": count_by(Ticket.ai_status),
    }


# ---------- knowledge base ----------


@app.post(
    "/articles", status_code=status.HTTP_201_CREATED, response_model=ArticleOut, dependencies=agent_only
)
def create_article(payload: ArticleCreate, db: DB) -> Article:
    article = Article(**payload.model_dump())
    db.add(article)
    db.commit()
    db.refresh(article)
    return article


@app.get("/articles/search", dependencies=agent_only)
def search(q: Annotated[str, Query(min_length=2, max_length=200)], db: DB) -> list[dict[str, str]]:
    return [a.model_dump() for a in search_articles(db, q, limit=5)]


@app.delete("/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=agent_only)
def delete_article(article_id: uuid.UUID, db: DB) -> Response:
    article = db.get(Article, article_id)
    if article is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article not found")
    db.delete(article)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
