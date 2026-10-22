from typing import Literal, Protocol

from pydantic import BaseModel, Field

Category = Literal["billing", "technical", "account", "security", "feature_request", "other"]
Priority = Literal["low", "medium", "high", "urgent"]
Sentiment = Literal["positive", "neutral", "negative"]


class TriageResult(BaseModel):
    """The only shape we accept back from any AI provider.

    Enums and length limits mean a confused or manipulated model cannot write
    arbitrary values into the database.
    """

    category: Category
    priority: Priority
    sentiment: Sentiment
    summary: str = Field(min_length=1, max_length=500, description="One or two sentences for the agent")
    suggested_reply: str = Field(min_length=1, max_length=3000, description="Draft reply to the customer")


class KnowledgeSnippet(BaseModel):
    title: str
    body: str


class TriageProvider(Protocol):
    name: str

    def triage(self, subject: str, body: str, knowledge: list[KnowledgeSnippet]) -> TriageResult: ...
