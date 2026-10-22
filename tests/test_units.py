import pytest

from app.ai.factory import build_provider
from app.ai.rules_provider import RulesProvider
from app.config import Settings
from app.redaction import redact


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("mail me at jane.doe+x@mail.co.uk", "mail me at [EMAIL]"),
        ("card 4111-1111-1111-1111 thanks", "card [CARD] thanks"),
        ("call (514) 555-0199", "call [PHONE]"),
        ("my key is sk-ant-abcdefghijklmnop123", "my key is [SECRET]"),
        ("order #12345 is late", "order #12345 is late"),  # short numbers untouched
    ],
)
def test_redact(text, expected):
    assert redact(text) == expected


@pytest.mark.parametrize(
    ("subject", "body", "category", "priority"),
    [
        ("Account hacked", "Someone made unauthorized changes", "security", "urgent"),
        ("Refund", "I was charged twice", "billing", "high"),
        ("Cannot log in", "Password reset email never arrives", "account", "high"),
        ("Bug", "Export shows an error sometimes", "technical", "medium"),
        ("Idea", "Would be great to add a calendar view", "feature_request", "low"),
        ("Hello", "Just saying hi to the team", "other", "medium"),
    ],
)
def test_rules_provider(subject, body, category, priority):
    r = RulesProvider().triage(subject, body, [])
    assert (r.category, r.priority) == (category, priority)


def test_rules_provider_detects_sentiment():
    assert RulesProvider().triage("x", "This is unacceptable and I am frustrated", []).sentiment == "negative"
    assert RulesProvider().triage("x", "Thanks, love the product", []).sentiment == "positive"


def _settings(**kw):
    return Settings(agent_api_key="k" * 16, **kw)


def test_factory_uses_rules_without_api_key():
    assert build_provider(_settings(ai_provider="auto")).name == "rules"


def test_factory_uses_claude_when_key_present():
    provider = build_provider(
        _settings(ai_provider="auto", anthropic_api_key="sk-test", ai_model="claude-haiku-5-5")
    )
    assert provider.name == "anthropic:claude-haiku-5-5"


def test_factory_refuses_anthropic_without_key():
    with pytest.raises(RuntimeError):
        build_provider(_settings(ai_provider="anthropic"))


def test_database_url_gets_psycopg_driver():
    assert _settings(database_url="postgres://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
    assert _settings(database_url="postgresql://u:p@h/db").database_url == "postgresql+psycopg://u:p@h/db"
