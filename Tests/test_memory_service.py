from fastapi.testclient import TestClient
from memory_service.main import app

client = TestClient(app)


def test_memory_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "memory"


def test_save_memory():
    payload = {
        "category": "facts",
        "key": "favorite_app",
        "value": "spotify"
    }

    response = client.post("/memory/save", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "id" in data
    assert data["message"] == "Memory saved successfully."


def test_get_all_memory():
    response = client.get("/memory/all")
    assert response.status_code == 200

    data = response.json()
    assert "memories" in data
    assert isinstance(data["memories"], list)


def test_log_action():
    payload = {
        "action": "open spotify",
        "type": "open_app",
        "success": True
    }

    response = client.post("/memory/action", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Action logged."


def test_get_history():
    response = client.get("/memory/history")
    assert response.status_code == 200

    data = response.json()
    assert "history" in data
    assert isinstance(data["history"], list)


def test_retrieve_memory():
    payload = {
        "query": "spotify",
        "limit": 5
    }

    response = client.post("/memory/retrieve", json=payload)

    # If Qdrant is working, should be 200.
    # If Qdrant still has an API/version issue, this test will fail and show it clearly.
    assert response.status_code == 200

    data = response.json()
    assert "memories" in data
    assert isinstance(data["memories"], list)