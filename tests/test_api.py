from tests.conftest import AGENT


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_customer_creates_ticket_and_it_gets_triaged(client, make_ticket):
    ticket_id = make_ticket("Charged twice", "I was charged twice for my subscription this month!")
    t = client.get(f"/tickets/{ticket_id}", headers=AGENT).json()
    assert t["ai_status"] == "done"
    assert t["category"] == "billing"
    assert t["priority"] == "high"
    assert t["ai_provider"] == "rules"
    assert t["ai_attempts"] == 1
    assert t["ai_suggested_reply"]


def test_create_returns_only_minimal_fields(client):
    res = client.post(
        "/tickets", json={"subject": "Hello", "body": "Just a question here.", "customer_email": "a@b.co"}
    )
    assert set(res.json()) == {"id", "status", "ai_status"}


def test_create_validates_input(client):
    bad = [
        {"subject": "Hi", "body": "long enough body", "customer_email": "a@b.co"},  # subject too short
        {"subject": "Hello", "body": "short", "customer_email": "a@b.co"},  # body too short
        {"subject": "Hello", "body": "long enough body", "customer_email": "not-an-email"},
        {"subject": "Hello", "body": "long enough body", "customer_email": "a@b.co", "priority": "urgent"},
    ]
    for payload in bad:
        assert client.post("/tickets", json=payload).status_code == 422, payload


def test_agent_endpoints_require_api_key(client, make_ticket):
    ticket_id = make_ticket()
    assert client.get("/tickets").status_code == 401
    assert client.get("/tickets", headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.get(f"/tickets/{ticket_id}").status_code == 401
    assert client.get("/tickets", headers=AGENT).status_code == 200


def test_queue_is_sorted_by_priority_then_age(client, make_ticket):
    make_ticket("Feature idea", "It would be great to have a dark mode feature.")
    make_ticket("Site down", "Production down for everyone, this is urgent!")
    make_ticket("Question", "How do I export my data to CSV?")
    items = client.get("/tickets", headers=AGENT).json()["items"]
    assert [t["priority"] for t in items] == ["urgent", "medium", "low"]


def test_filters(client, make_ticket):
    make_ticket("Refund please", "Please refund my last payment.")
    make_ticket("App crash", "The app shows an error and crashes on start.")
    res = client.get("/tickets?category=billing", headers=AGENT).json()
    assert res["total"] == 1
    assert res["items"][0]["subject"] == "Refund please"


def test_update_ticket(client, make_ticket):
    ticket_id = make_ticket()
    res = client.patch(
        f"/tickets/{ticket_id}", headers=AGENT, json={"assignee": "sadia", "priority": "urgent"}
    )
    assert res.status_code == 200
    assert res.json()["assignee"] == "sadia"
    assert res.json()["priority"] == "urgent"
    assert client.patch(f"/tickets/{ticket_id}", headers=AGENT, json={}).status_code == 422
    assert client.patch(f"/tickets/{ticket_id}", headers=AGENT, json={"status": "deleted"}).status_code == 422


def test_reply_with_ai_draft(client, make_ticket):
    ticket_id = make_ticket()
    res = client.post(
        f"/tickets/{ticket_id}/replies", headers=AGENT, json={"author": "sadia", "use_ai_draft": True}
    )
    assert res.status_code == 201
    assert res.json()["ai_assisted"] is True
    detail = client.get(f"/tickets/{ticket_id}", headers=AGENT).json()
    assert detail["status"] == "pending"
    assert detail["replies"][0]["body"] == detail["ai_suggested_reply"]


def test_reply_needs_a_body(client, make_ticket):
    ticket_id = make_ticket()
    res = client.post(f"/tickets/{ticket_id}/replies", headers=AGENT, json={"author": "sadia"})
    assert res.status_code == 422


def test_retriage(client, make_ticket):
    ticket_id = make_ticket()
    assert client.post(f"/tickets/{ticket_id}/retriage", headers=AGENT).status_code == 202
    assert client.get(f"/tickets/{ticket_id}", headers=AGENT).json()["ai_attempts"] == 2


def test_missing_ticket_returns_404(client):
    missing = "00000000-0000-4000-8000-000000000000"
    assert client.get(f"/tickets/{missing}", headers=AGENT).status_code == 404
    assert client.get("/tickets/not-a-uuid", headers=AGENT).status_code == 422


def test_stats(client, make_ticket):
    make_ticket("Refund please", "Please refund my last payment.")
    make_ticket("Refund again", "Another refund request for my invoice.")
    stats = client.get("/stats", headers=AGENT).json()
    assert stats["category"]["billing"] == 2
    assert stats["ai_status"]["done"] == 2


def test_knowledge_base_search(client):
    client.post(
        "/articles",
        headers=AGENT,
        json={
            "title": "How refunds work",
            "body": "Refunds are processed within 5 business days to the original card.",
        },
    )
    client.post(
        "/articles",
        headers=AGENT,
        json={
            "title": "Resetting your password",
            "body": "Use the Forgot password link on the login page.",
        },
    )
    results = client.get("/articles/search?q=I forgot my password", headers=AGENT).json()
    assert results[0]["title"] == "Resetting your password"
    # tsquery operators in user input are stripped, not interpreted
    assert client.get("/articles/search?q=refund|!&(", headers=AGENT).status_code == 200
