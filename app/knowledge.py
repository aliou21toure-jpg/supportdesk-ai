import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.base import KnowledgeSnippet

_WORD = re.compile(r"[a-z0-9]{3,}")


def search_articles(db: Session, query: str, limit: int = 3) -> list[KnowledgeSnippet]:
    """Full-text search over the knowledge base using PostgreSQL's tsvector index.

    Words are OR-ed together so a long ticket still matches articles sharing a few
    key terms. Only [a-z0-9] tokens reach to_tsquery, so user text cannot inject
    tsquery operators.
    """
    words = list(dict.fromkeys(_WORD.findall(query.lower())))[:20]
    if not words:
        return []
    rows = db.execute(
        text(
            """
            SELECT title, body
            FROM articles, to_tsquery('english', :q) AS q
            WHERE search @@ q
            ORDER BY ts_rank(search, q) DESC
            LIMIT :limit
            """
        ),
        {"q": " | ".join(words), "limit": limit},
    ).all()
    return [KnowledgeSnippet(title=r.title, body=r.body[:2000]) for r in rows]
