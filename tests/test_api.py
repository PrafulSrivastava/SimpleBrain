import pytest
from fastapi.testclient import TestClient
from simplebrain.api.routes import create_app
from simplebrain.config import BrainConfig


@pytest.fixture
def client(config):
    app = create_app(config)
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_add_text_note(client):
    resp = client.post("/notes/text",
                       json={"text": "Hello brain", "user": "alice", "device": "mac"})
    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_add_voice_note(client):
    import base64
    fake_audio = base64.b64encode(b"fake audio").decode()
    resp = client.post("/notes/voice",
                       json={"audio_b64": fake_audio, "filename": "test.wav",
                             "user": "alice", "device": "iphone"})
    assert resp.status_code == 200
    assert "job_id" in resp.json()


def test_list_topics(client):
    resp = client.get("/topics")
    assert resp.status_code == 200
    assert "topics" in resp.json()


def test_list_tags(client):
    resp = client.get("/tags")
    assert resp.status_code == 200
    assert "tags" in resp.json()


def test_search(client):
    resp = client.get("/search?query=mcp")
    assert resp.status_code == 200
    assert "results" in resp.json()


def test_brain_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "queue_depth" in data
    assert "pending_conflicts" in data
    assert "pending_proposals" in data


def test_list_proposals(client):
    resp = client.get("/proposals")
    assert resp.status_code == 200
    assert "proposals" in resp.json()


def test_list_conflicts(client):
    resp = client.get("/conflicts")
    assert resp.status_code == 200
    assert "conflicts" in resp.json()


def test_root_serves_ui(client):
    resp = client.get("/")
    # Should either return the HTML file or a JSON message
    assert resp.status_code == 200


def test_heal_endpoint(client, monkeypatch):
    """POST /heal should return conflicts_found count (mock healer to avoid LLM calls)."""
    from simplebrain.brain import healer as healer_mod

    original_scan = healer_mod.SelfHealer.scan

    def mock_scan(self):
        return []

    monkeypatch.setattr(healer_mod.SelfHealer, "scan", mock_scan)
    resp = client.post("/heal")
    assert resp.status_code == 200
    assert "conflicts_found" in resp.json()
