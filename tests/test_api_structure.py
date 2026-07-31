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


def test_propose_structure(client, monkeypatch):
    """POST /structure/propose calls the wizard and returns a proposal (mock LLM)."""
    from simplebrain.setup import wizard as wizard_mod

    fake_proposal = {
        "summary": "AI-generated brain",
        "healer_schedule": "daily",
        "folders": [
            {"name": "projects", "display": "Projects", "description": "Active work", "examples": ["app"]},
            {"name": "archive", "display": "Archive", "description": "Old stuff", "examples": []},
        ],
    }

    def mock_propose(self, description):
        return fake_proposal

    monkeypatch.setattr(wizard_mod.SetupWizard, "propose", mock_propose)
    resp = client.post("/structure/propose", json={"description": "I need a brain for software projects"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"] == "AI-generated brain"
    assert len(data["folders"]) == 2
    assert data["folders"][0]["name"] == "projects"


def test_propose_structure_empty_description(client):
    resp = client.post("/structure/propose", json={"description": ""})
    assert resp.status_code == 422


import json


def _seed_structure(config):
    """Helper: write a structure with two folders to disk."""
    structure = {
        "folders": [
            {"name": "research", "display": "Research", "description": "Papers", "examples": []},
            {"name": "archive", "display": "Archive", "description": "Old stuff", "examples": []},
        ],
        "pending_proposals": [],
    }
    (config.meta_dir / "structure.json").write_text(json.dumps(structure))
    (config.knowledge_dir / "research").mkdir(parents=True, exist_ok=True)
    (config.knowledge_dir / "archive").mkdir(parents=True, exist_ok=True)


def test_add_folder(client, config):
    _seed_structure(config)
    resp = client.post("/structure/folders", json={
        "name": "daily-log",
        "display": "Daily Log",
        "description": "Day-to-day notes",
        "examples": ["standup", "retrospective"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["created"] is True
    assert data["folder"]["name"] == "daily-log"
    assert (config.knowledge_dir / "daily-log").is_dir()
    assert (config.knowledge_dir / "daily-log" / "README.md").exists()


def test_add_folder_invalid_name(client, config):
    _seed_structure(config)
    resp = client.post("/structure/folders", json={
        "name": "Invalid Name!",
        "description": "bad",
    })
    assert resp.status_code == 422


def test_add_folder_duplicate(client, config):
    _seed_structure(config)
    resp = client.post("/structure/folders", json={
        "name": "research",
        "description": "duplicate",
    })
    assert resp.status_code == 409


def test_patch_folder(client, config):
    _seed_structure(config)
    resp = client.patch("/structure/folders/research", json={
        "description": "Updated description",
    })
    assert resp.status_code == 200
    assert resp.json()["folder"]["description"] == "Updated description"


def test_patch_folder_rename(client, config):
    _seed_structure(config)
    resp = client.patch("/structure/folders/research", json={
        "new_name": "papers",
    })
    assert resp.status_code == 200
    assert resp.json()["folder"]["name"] == "papers"
    assert (config.knowledge_dir / "papers").is_dir()
    assert not (config.knowledge_dir / "research").exists()


def test_patch_folder_not_found(client, config):
    _seed_structure(config)
    resp = client.patch("/structure/folders/nonexistent", json={"description": "x"})
    assert resp.status_code == 404


def test_delete_folder(client, config):
    _seed_structure(config)
    # Put a file in research so we can verify it moves to _unfiled
    (config.knowledge_dir / "research" / "note.md").write_text("hello")
    resp = client.delete("/structure/folders/research")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True
    # File should be in _unfiled now
    assert (config.knowledge_dir / "_unfiled" / "note.md").exists()
    assert not (config.knowledge_dir / "research").exists()


def test_delete_archive_forbidden(client, config):
    _seed_structure(config)
    resp = client.delete("/structure/folders/archive")
    assert resp.status_code == 403


def test_delete_folder_not_found(client, config):
    _seed_structure(config)
    resp = client.delete("/structure/folders/nonexistent")
    assert resp.status_code == 404
