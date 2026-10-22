"""initial schema

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE tickets (
          id                 UUID PRIMARY KEY,
          subject            VARCHAR(200) NOT NULL,
          body               TEXT NOT NULL,
          customer_email     VARCHAR(254) NOT NULL,
          status             VARCHAR(20) NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open', 'pending', 'resolved', 'closed')),
          assignee           VARCHAR(100),
          category           VARCHAR(30)
                             CHECK (category IN ('billing', 'technical', 'account', 'security',
                                                 'feature_request', 'other')),
          priority           VARCHAR(10) CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
          sentiment          VARCHAR(10) CHECK (sentiment IN ('positive', 'neutral', 'negative')),
          ai_summary         TEXT,
          ai_suggested_reply TEXT,
          ai_status          VARCHAR(12) NOT NULL DEFAULT 'pending'
                             CHECK (ai_status IN ('pending', 'processing', 'done', 'failed')),
          ai_error           TEXT,
          ai_attempts        INTEGER NOT NULL DEFAULT 0,
          ai_provider        VARCHAR(50),
          triaged_at         TIMESTAMPTZ,
          created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX tickets_queue_idx ON tickets (status, priority, created_at DESC);
        CREATE INDEX tickets_category_idx ON tickets (category);

        CREATE TABLE replies (
          id          UUID PRIMARY KEY,
          ticket_id   UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
          author      VARCHAR(100) NOT NULL,
          body        TEXT NOT NULL,
          ai_assisted BOOLEAN NOT NULL DEFAULT false,
          created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX replies_ticket_idx ON replies (ticket_id, created_at);

        CREATE TABLE articles (
          id         UUID PRIMARY KEY,
          title      VARCHAR(200) NOT NULL,
          body       TEXT NOT NULL,
          search     TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', title || ' ' || body)) STORED,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX articles_search_idx ON articles USING GIN (search);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE replies; DROP TABLE tickets; DROP TABLE articles;")
