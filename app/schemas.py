import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.ai.base import Category, Priority, Sentiment

TicketStatus = Literal["open", "pending", "resolved", "closed"]
AiStatus = Literal["pending", "processing", "done", "failed"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class TicketCreate(Strict):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=10_000)
    customer_email: EmailStr


class TicketUpdate(Strict):
    status: TicketStatus | None = None
    assignee: str | None = Field(default=None, max_length=100)
    category: Category | None = None
    priority: Priority | None = None


class ReplyCreate(Strict):
    author: str = Field(min_length=1, max_length=100)
    body: str | None = Field(default=None, min_length=1, max_length=10_000)
    use_ai_draft: bool = False


class ReplyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    author: str
    body: str
    ai_assisted: bool
    created_at: datetime


class TicketCreated(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: TicketStatus
    ai_status: AiStatus


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject: str
    body: str
    customer_email: str
    status: TicketStatus
    assignee: str | None
    category: Category | None
    priority: Priority | None
    sentiment: Sentiment | None
    ai_summary: str | None
    ai_suggested_reply: str | None
    ai_status: AiStatus
    ai_error: str | None
    ai_attempts: int
    ai_provider: str | None
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketOut):
    replies: list[ReplyOut]


class TicketPage(BaseModel):
    items: list[TicketOut]
    total: int


class ArticleCreate(Strict):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=10, max_length=20_000)


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    title: str
    body: str
