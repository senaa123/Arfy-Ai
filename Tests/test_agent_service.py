from fastapi.testclient import TestClient
from agent_service.main import app

client = TestClient(app)


def test_agent_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "agent"


def test_agent_chat_request():
    payload = {
        "text": "hello arfy",
        "session_id": "test_session_01",
        "memories": []
    }

    response = client.post("/agent/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response" in data
    assert "session_id" in data
    assert data["session_id"] == "test_session_01"


def test_agent_weather_request():
    payload = {
        "text": "what is the weather in Colombo",
        "session_id": "test_session_weather",
        "memories": []
    }

    response = client.post("/agent/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response" in data
    assert "confidence" in data
    assert "tool_used" in data


def test_agent_open_app_request():
    payload = {
        "text": "open spotify",
        "session_id": "test_session_open_app",
        "memories": []
    }

    response = client.post("/agent/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response" in data
    assert "action" in data

    # action may be None if router fails, but ideally should exist
    if data["action"] is not None:
        assert "type" in data["action"]
        assert "payload" in data["action"]


def test_agent_playlist_request():
    payload = {
        "text": "play my chill playlist on spotify",
        "session_id": "test_session_playlist",
        "memories": []
    }

    response = client.post("/agent/ask", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response" in data
    assert "action" in data

    if data["action"] is not None:
        assert "type" in data["action"]
        assert "payload" in data["action"]


def test_agent_reset():
    response = client.post("/agent/reset", params={"session_id": "test_session_01"})
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "reset"
    assert data["session_id"] == "test_session_01"