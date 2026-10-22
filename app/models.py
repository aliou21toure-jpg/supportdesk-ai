import uuid
from datetime import datetime

from sqlalchemy import Computed, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    customer_email: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(20), default="open")
    assignee: Mapped[str | None] = mapped_column(String(100))

    # Filled in by the AI triage background job
    category: Mapped[str | None] = mapped_column(String(30))
    priority: Mapped[str | None] = mapped_column(String(10))
    sentiment: Mapped[str | None] = mapped_column(String(10))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_suggested_reply: Mapped[str | None] = mapped_column(Text)
    ai_status: Mapped[str] = mapped_column(String(12), default="pending")
    ai_error: Mapped[str | None] = mapped_column(Text)
    ai_attempts: Mapped[int] = mapped_column(Integer, default=0)
    ai_provider: Mapped[str | None] = mapped_column(String(50))
    triaged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    replies: Mapped[list["Reply"]] = relationship(
        back_populates="ticket", order_by="Reply.created_at", cascade="all, delete-orphan"
    )


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    author: Mapped[str] = mapped_column(String(100))
    body: Mapped[str] = mapped_column(Text)
    ai_assisted: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped[Ticket] = relationship(back_populates="replies")


class Article(Base):
    """Knowledge-base article. `search` is a generated full-text index column."""

    __tablename__ = "articles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    search: Mapped[str] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', title || ' ' || body)", persisted=True), deferred=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
