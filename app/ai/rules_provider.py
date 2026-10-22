"""Deterministic keyword-based triage.

Used when no API key is configured (local dev, CI, demos) and as a baseline
to compare the LLM against. It never calls the network.
"""

from app.ai.base import Category, KnowledgeSnippet, Priority, Sentiment, TriageResult

_CATEGORY_KEYWORDS: list[tuple[Category, tuple[str, ...]]] = [
    ("security", ("hacked", "phishing", "breach", "unauthorized", "suspicious", "2fa", "compromised")),
    ("billing", ("invoice", "charge", "charged", "refund", "payment", "billing", "subscription", "price")),
    ("account", ("password", "login", "log in", "sign in", "account", "email change", "locked")),
    ("technical", ("error", "bug", "crash", "broken", "not working", "500", "slow", "timeout", "api")),
    ("feature_request", ("feature", "would be great", "suggestion", "could you add", "wish")),
]
_URGENT = ("urgent", "asap", "immediately", "down for everyone", "production down", "outage", "hacked")
_HIGH = ("cannot", "can't", "unable", "blocked", "charged twice", "refund")
_NEGATIVE = ("angry", "terrible", "worst", "frustrated", "unacceptable", "disappointed", "ridiculous")
_POSITIVE = ("thanks", "thank you", "love", "great", "awesome", "appreciate")


class RulesProvider:
    name = "rules"

    def triage(self, subject: str, body: str, knowledge: list[KnowledgeSnippet]) -> TriageResult:
        text = f"{subject}\n{body}".lower()

        category: Category = next(
            (cat for cat, words in _CATEGORY_KEYWORDS if any(w in text for w in words)), "other"
        )
        priority: Priority = (
            "urgent"
            if any(w in text for w in _URGENT)
            else "high"
            if category == "security" or any(w in text for w in _HIGH)
            else "low"
            if category == "feature_request"
            else "medium"
        )
        sentiment: Sentiment = (
            "negative"
            if any(w in text for w in _NEGATIVE)
            else "positive"
            if any(w in text for w in _POSITIVE)
            else "neutral"
        )

        reply = (
            "Hi,\n\nThanks for contacting us — we've received your request and an agent is looking into it."
        )
        if knowledge:
            reply += f'\n\nIn the meantime, this article may help: "{knowledge[0].title}".'
        reply += "\n\nBest regards,\nSupport team"

        return TriageResult(
            category=category,
            priority=priority,
            sentiment=sentiment,
            summary=f"{category.replace('_', ' ').capitalize()} request: {subject[:150]}",
            suggested_reply=reply,
        )
