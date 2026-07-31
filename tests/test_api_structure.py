import pytest
from fastapi.testclient import TestClient
from simplebrain.api.routes import create_app


@pytest.fixture
def client(config):
    app = create_app(config)
    return TestClient(app)


def test_get_structure_empty(client):
    resp = client.get("/structure")
    assert resp.status_code == 200
    data = resp.json()
    assert data["folders"] == []
    assert "summary" in data
    assert "healer_schedule" in data


def test_get_structure_with_folders(client, config):
    import json
    meta = config.meta_dir / "structure.json"
    meta.write_text(json.dumps({
        "folders": [
            {"name": "research", "display": "Research", "description": "Papers", "examples": ["paper1"]},
            {"name": "archive", "display": "Archive", "description": "Old stuff", "examples": []},
        ],
        "pending_proposals": [],
    }))
    setup_meta = config.meta_dir / "setup.json"
    setup_meta.write_text(json.dumps({
        "summary": "My brain",
        "healer_schedule": "daily",
        "folders": [],
    }))
    resp = client.get("/structure")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["folders"]) == 2
    assert data["folders"][0]["name"] == "research"
    assert data["summary"] == "My brain"


def test_apply_structure(client, config):
    proposal = {
        "summary": "Test brain",
        "healer_schedule": "weekly",
        "folders": [
            {"name": "notes", "display": "Notes", "description": "Daily notes", "examples": ["standup"]},
            {"name": "archive", "display": "Archive", "description": "Old content", "examples": []},
        ],
    }
    resp = client.post("/structure/apply", json=proposal)
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied"] is True
    assert data["folder_count"] == 2
    assert (config.knowledge_dir / "notes").is_dir()
    assert (config.knowledge_dir / "archive").is_dir()
    assert (config.knowledge_dir / "notes" / "README.md").exists()
