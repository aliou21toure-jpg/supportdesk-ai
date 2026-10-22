import os
import re

# Configure the app for tests BEFORE anything imports app.config.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://supportdesk:supportdesk@localhost:5432/supportdesk_test"
)
os.environ["AGENT_API_KEY"] = "test-agent-key-0123456789"
os.environ["AI_PROVIDER"] = "rules"
os.environ["ANTHROPIC_API_KEY"] = ""

if not re.search(r"_test(\?|$)", os.environ["DATABASE_URL"]):
    raise RuntimeError("Tests must run against a *_test database")

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fakeredis import FakeRedis  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from rq import Queue  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app import queue as queue_module  # noqa: E402
from app.db import get_engine  # noqa: E402
from app.main import app  # noqa: E402

AGENT = {"X-API-Key": "test-agent-key-0123456789"}


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    command.upgrade(Config("alembic.ini"), "head")
    yield


@pytest.fixture(autouse=True)
def clean_db():
    with get_engine().begin() as conn:
        conn.execute(text("TRUNCATE replies, tickets, articles"))
    yield


@pytest.fixture(autouse=True)
def sync_queue(monkeypatch):
    """Run background jobs inline (is_async=False) on an in-memory Redis."""
    q = Queue("triage", is_async=False, connection=FakeRedis())
    monkeypatch.setattr(queue_module, "get_queue", lambda: q)
    return q


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def make_ticket(client):
    def _make(subject="Help needed", body="Something is not working as expected.", email="cus@example.com"):
        res = client.post("/tickets", json={"subject": subject, "body": body, "customer_email": email})
        assert res.status_code == 201, res.text
        return res.json()["id"]

    return _make
