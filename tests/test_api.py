"""API integration tests for all FastAPI endpoints."""

from app.config import settings


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "llm_reachable" in data
    assert "index_documents" in data


def test_chat_non_streaming(client):
    payload = {
        "message": "What is the fee payment deadline?",
        "session_id": "test_session_api_1",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "sources" in data
    assert "chat_log_id" in data


def test_chat_streaming(client):
    payload = {
        "message": "When are the mid-term examinations scheduled?",
        "session_id": "test_session_stream_1",
    }
    response = client.post("/api/chat/stream", json=payload)
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    content = response.text
    assert "event: token" in content or "event: done" in content


def test_feedback_endpoint(client):
    payload = {
        "session_id": "test_session_api_1",
        "chat_log_id": 1,
        "question": "What is the fee payment deadline?",
        "answer": "Tuition fee must be paid before semester start.",
        "sources": "[]",
        "rating": "up",
    }
    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["rating"] == "up"
    assert "id" in data


def test_tickets_create_and_resolve(client):
    payload = {
        "name": "Aarav Sharma",
        "student_id": "SIT2024CSE042",
        "email": "aarav.sharma@example.com",
        "query": "My scholarship adjustment was not reflected in the latest fee receipt.",
    }
    # Create ticket
    create_res = client.post("/api/tickets", json=payload)
    assert create_res.status_code == 200
    t_data = create_res.json()
    assert t_data["status"] == "open"
    ticket_id = t_data["ticket_id"]

    # Verify admin listing
    headers = {"X-Admin-Password": settings.admin_password}
    list_res = client.get("/api/admin/tickets", headers=headers)
    assert list_res.status_code == 200
    tickets = list_res.json()
    matching = [t for t in tickets if t["ticket_id"] == ticket_id]
    assert len(matching) == 1

    # Resolve ticket
    resolve_res = client.post(f"/api/admin/tickets/{ticket_id}/resolve", headers=headers)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"


def test_admin_auth_unauthorized(client):
    # Without password
    res = client.get("/api/admin/analytics")
    assert res.status_code == 401

    # With wrong password
    res = client.get("/api/admin/analytics", headers={"X-Admin-Password": "wrong"})
    assert res.status_code == 401


def test_admin_analytics(client):
    headers = {"X-Admin-Password": settings.admin_password}
    res = client.get("/api/admin/analytics", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_chats" in data
    assert "answered_ratio" in data
    assert "avg_latency_ms" in data


def test_session_clear(client):
    res = client.post("/api/session/clear", json={"session_id": "test_session_api_1"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
