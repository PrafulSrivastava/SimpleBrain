# Folder Structure UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a browser-based UI at `/ui/setup.html` that lets users configure the SimpleBrain knowledge-base folder structure via an AI wizard and a lightweight folder manager.

**Architecture:** New REST endpoints in the existing FastAPI app expose structure CRUD operations backed by the existing `SetupWizard` and `SelfGrower` classes. A new static HTML page (`ui/setup.html`) uses the same vanilla CSS design system as `ui/index.html` and communicates entirely via `fetch()`.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, vanilla HTML/CSS/JS (no framework, no build step)

## Global Constraints

- No external frontend dependencies (no React, Tailwind, npm)
- Follow existing test patterns: `pytest` + `TestClient` + `conftest.py` fixtures
- Folder names: lowercase, hyphen-separated, 1-3 words, no special chars. Regex: `^[a-z][a-z0-9-]{0,30}[a-z0-9]$`
- "archive" folder cannot be deleted
- Deleting a folder moves its knowledge files to `knowledge/_unfiled/`, does NOT delete them
- All new endpoints live inside `create_app()` in `simplebrain/api/routes.py`

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `simplebrain/api/routes.py` | Modify | Add 5 new endpoints for structure CRUD |
| `tests/test_api_structure.py` | Create | Tests for all structure endpoints |
| `ui/setup.html` | Create | Wizard + folder manager frontend |
| `ui/index.html` | Modify | Add gear icon linking to setup.html |

---

### Task 1: Backend — GET /structure and POST /structure/apply

**Files:**
- Modify: `simplebrain/api/routes.py` (add endpoints after existing routes, before UI mount)
- Create: `tests/test_api_structure.py`

**Interfaces:**
- Consumes: `SelfGrower.get_folder_details()` → `list[dict]`, `SelfGrower.load_structure()` → `dict`, `SetupWizard.apply(proposal)` → `list[str]`
- Produces: `GET /structure` → `{summary: str, healer_schedule: str, folders: list[dict]}`, `POST /structure/apply` → `{applied: true, folder_count: int}`

- [ ] **Step 1: Write failing tests for GET /structure**

```python
# tests/test_api_structure.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_structure.py -v`
Expected: FAIL — endpoints not yet defined (404)

- [ ] **Step 3: Implement GET /structure and POST /structure/apply**

Add to `simplebrain/api/routes.py` inside `create_app()`, after the `heal` endpoint and before the UI mount:

```python
# --- Structure management ---

class ApplyStructureRequest(BaseModel):
    summary: str = "Personal knowledge base."
    healer_schedule: str = "daily"
    folders: list[dict]

@app.get("/structure")
def get_structure():
    folders = grower.get_folder_details()
    setup_path = config.meta_dir / "setup.json"
    summary = ""
    healer_schedule = "daily"
    if setup_path.exists():
        import json
        setup_data = json.loads(setup_path.read_text())
        summary = setup_data.get("summary", "")
        healer_schedule = setup_data.get("healer_schedule", "daily")
    return {"summary": summary, "healer_schedule": healer_schedule, "folders": folders}

@app.post("/structure/apply")
def apply_structure(req: ApplyStructureRequest):
    from simplebrain.setup.wizard import SetupWizard
    wizard = SetupWizard(config)
    proposal = {"summary": req.summary, "healer_schedule": req.healer_schedule, "folders": req.folders}
    folder_names = wizard.apply(proposal)
    return {"applied": True, "folder_count": len(folder_names)}
```

Add the `ApplyStructureRequest` class near the other request models at the top of the file.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_structure.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/api/routes.py tests/test_api_structure.py
git commit -m "feat: add GET /structure and POST /structure/apply endpoints"
```

---

### Task 2: Backend — POST /structure/propose

**Files:**
- Modify: `simplebrain/api/routes.py`
- Modify: `tests/test_api_structure.py`

**Interfaces:**
- Consumes: `SetupWizard.propose(description: str)` → `dict`
- Produces: `POST /structure/propose` → `{summary: str, healer_schedule: str, folders: list[dict]}`

- [ ] **Step 1: Write failing test**

```python
# Add to tests/test_api_structure.py

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_structure.py::test_propose_structure tests/test_api_structure.py::test_propose_structure_empty_description -v`
Expected: FAIL (404 — endpoint doesn't exist yet)

- [ ] **Step 3: Implement POST /structure/propose**

Add to `simplebrain/api/routes.py` inside `create_app()`:

```python
class ProposeStructureRequest(BaseModel):
    description: str = Field(min_length=1)

@app.post("/structure/propose")
def propose_structure(req: ProposeStructureRequest):
    from simplebrain.setup.wizard import SetupWizard
    wizard = SetupWizard(config)
    proposal = wizard.propose(req.description)
    return proposal
```

Add `ProposeStructureRequest` near the other request models. Import `Field` from pydantic (already imported at the top via `BaseModel`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_structure.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/api/routes.py tests/test_api_structure.py
git commit -m "feat: add POST /structure/propose endpoint"
```

---

### Task 3: Backend — POST, PATCH, DELETE /structure/folders

**Files:**
- Modify: `simplebrain/api/routes.py`
- Modify: `tests/test_api_structure.py`

**Interfaces:**
- Consumes: `SelfGrower.load_structure()` → `dict`, `SelfGrower.save_structure(dict)` → `None`
- Produces: `POST /structure/folders` → `{created: true, folder: dict}`, `PATCH /structure/folders/{name}` → `{updated: true, folder: dict}`, `DELETE /structure/folders/{name}` → `{deleted: true}`

- [ ] **Step 1: Write failing tests**

```python
# Add to tests/test_api_structure.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_structure.py -v -k "add_folder or patch_folder or delete_folder"`
Expected: All FAIL (404/405 — endpoints don't exist)

- [ ] **Step 3: Implement folder CRUD endpoints**

Add to `simplebrain/api/routes.py` inside `create_app()`:

```python
import re
import shutil

_FOLDER_NAME_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}[a-z0-9]$")

class AddFolderRequest(BaseModel):
    name: str
    display: str = ""
    description: str = ""
    examples: list[str] = Field(default_factory=list)

class PatchFolderRequest(BaseModel):
    new_name: str | None = None
    display: str | None = None
    description: str | None = None
    examples: list[str] | None = None

@app.post("/structure/folders")
def add_folder(req: AddFolderRequest):
    if not _FOLDER_NAME_RE.match(req.name):
        raise HTTPException(status_code=422, detail="Invalid folder name. Use lowercase, hyphens, 2-32 chars.")
    structure = grower.load_structure()
    existing_names = [f["name"] if isinstance(f, dict) else f for f in structure.get("folders", [])]
    if req.name in existing_names:
        raise HTTPException(status_code=409, detail=f"Folder '{req.name}' already exists.")
    folder_meta = {
        "name": req.name,
        "display": req.display or req.name,
        "description": req.description,
        "examples": req.examples,
    }
    structure.setdefault("folders", []).append(folder_meta)
    grower.save_structure(structure)
    # Create directory + README
    folder_path = config.knowledge_dir / req.name
    folder_path.mkdir(parents=True, exist_ok=True)
    readme = f"# {folder_meta['display']}\n\n{folder_meta['description']}\n"
    (folder_path / "README.md").write_text(readme, encoding="utf-8")
    return {"created": True, "folder": folder_meta}

@app.patch("/structure/folders/{name}")
def patch_folder(name: str, req: PatchFolderRequest):
    structure = grower.load_structure()
    folders = structure.get("folders", [])
    target = None
    target_idx = None
    for i, f in enumerate(folders):
        fname = f["name"] if isinstance(f, dict) else f
        if fname == name:
            target = f if isinstance(f, dict) else {"name": f, "display": f, "description": "", "examples": []}
            target_idx = i
            break
    if target is None:
        raise HTTPException(status_code=404, detail=f"Folder '{name}' not found.")
    if req.new_name is not None:
        if not _FOLDER_NAME_RE.match(req.new_name):
            raise HTTPException(status_code=422, detail="Invalid folder name.")
        existing_names = [f["name"] if isinstance(f, dict) else f for f in folders]
        if req.new_name in existing_names and req.new_name != name:
            raise HTTPException(status_code=409, detail=f"Folder '{req.new_name}' already exists.")
        # Rename directory on disk
        old_path = config.knowledge_dir / name
        new_path = config.knowledge_dir / req.new_name
        if old_path.exists():
            old_path.rename(new_path)
        target["name"] = req.new_name
    if req.display is not None:
        target["display"] = req.display
    if req.description is not None:
        target["description"] = req.description
    if req.examples is not None:
        target["examples"] = req.examples
    folders[target_idx] = target
    structure["folders"] = folders
    grower.save_structure(structure)
    return {"updated": True, "folder": target}

@app.delete("/structure/folders/{name}")
def delete_folder(name: str):
    if name == "archive":
        raise HTTPException(status_code=403, detail="Cannot delete the archive folder.")
    structure = grower.load_structure()
    folders = structure.get("folders", [])
    found = False
    new_folders = []
    for f in folders:
        fname = f["name"] if isinstance(f, dict) else f
        if fname == name:
            found = True
        else:
            new_folders.append(f)
    if not found:
        raise HTTPException(status_code=404, detail=f"Folder '{name}' not found.")
    structure["folders"] = new_folders
    grower.save_structure(structure)
    # Move files to _unfiled, then remove the directory
    folder_path = config.knowledge_dir / name
    unfiled = config.knowledge_dir / "_unfiled"
    unfiled.mkdir(parents=True, exist_ok=True)
    if folder_path.exists():
        for item in folder_path.iterdir():
            if item.name == "README.md":
                item.unlink()
                continue
            dest = unfiled / item.name
            shutil.move(str(item), str(dest))
        folder_path.rmdir()
    return {"deleted": True}
```

Add `import re` and `import shutil` at the top of `routes.py`. Add `from pydantic import BaseModel, Field` (Field is already imported via models, but add it to the pydantic import at the top of routes.py).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_structure.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/api/routes.py tests/test_api_structure.py
git commit -m "feat: add folder CRUD endpoints (POST, PATCH, DELETE)"
```

---

### Task 4: Frontend — setup.html wizard view

**Files:**
- Create: `ui/setup.html`

**Interfaces:**
- Consumes: `GET /structure`, `POST /structure/propose`, `POST /structure/apply`
- Produces: Complete wizard UI (describe → generate → edit → apply)

- [ ] **Step 1: Create ui/setup.html with wizard view**

Create `ui/setup.html` with the full wizard flow. The file follows `index.html`'s design system (same CSS variables, dark/light mode, card layout):

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
  <meta name="theme-color" content="#0b0d12" />
  <title>SimpleBrain — Setup</title>
  <script>
    document.documentElement.dataset.mode   = localStorage.getItem("sb_mode")   || "dark";
    document.documentElement.dataset.scheme = localStorage.getItem("sb_scheme") || "indigo";
  </script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }

    :root {
      --bg: #0b0d12; --surface: #12151d; --surface-2: #1a1e29;
      --border: #232837; --border-focus: #4f5b78;
      --text: #e8eaf0; --muted: #8b93a7; --faint: #5c6478;
      --green: #3ecf8e; --red: #f0506e; --red-soft: rgba(240,80,110,0.12);
      --radius: 16px; --accent-contrast: #0b0d12;
      --accent-soft: color-mix(in srgb, var(--accent) 14%, transparent);
      --glow: color-mix(in srgb, var(--accent) 8%, transparent);
    }
    :root, :root[data-scheme="indigo"]  { --accent: #6d8dff; --accent-2: #9b6dff; }
    :root[data-scheme="emerald"]        { --accent: #3ecf8e; --accent-2: #2dd4bf; }
    :root[data-scheme="rose"]           { --accent: #fb7185; --accent-2: #e879f9; }

    :root[data-mode="light"] {
      --bg: #f3f4f9; --surface: #ffffff; --surface-2: #f1f2f7;
      --border: #e3e6ef; --border-focus: #b7c0d8;
      --text: #191d28; --muted: #596276; --faint: #98a0b3;
      --red-soft: rgba(240,80,110,0.10); --accent-contrast: #ffffff;
    }
    :root[data-mode="light"][data-scheme="indigo"]  { --accent: #4c6ef5; --accent-2: #7048e8; }
    :root[data-mode="light"][data-scheme="emerald"] { --accent: #0ca678; --accent-2: #15aabf; }
    :root[data-mode="light"][data-scheme="rose"]    { --accent: #e64980; --accent-2: #be4bdb; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: radial-gradient(1200px 500px at 50% -10%, var(--glow), transparent 60%), var(--bg);
      color: var(--text); min-height: 100vh;
      padding: calc(env(safe-area-inset-top, 0px) + 12px) 16px calc(env(safe-area-inset-bottom, 0px) + 32px);
      max-width: 560px; margin: 0 auto;
      -webkit-font-smoothing: antialiased;
    }

    header { display: flex; align-items: center; justify-content: space-between; padding: 10px 2px 22px; }
    .brand { display: flex; align-items: center; gap: 10px; }
    .brand .logo { width: 34px; height: 34px; border-radius: 10px; background: linear-gradient(135deg, var(--accent), var(--accent-2)); display: grid; place-items: center; color: #fff; }
    .brand h1 { font-size: 1.05rem; font-weight: 650; }
    .brand p { font-size: 0.7rem; color: var(--faint); margin-top: 1px; }
    .back-link { font-size: 0.82rem; color: var(--accent); text-decoration: none; font-weight: 600; }
    .back-link:hover { text-decoration: underline; }

    .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 18px; margin-bottom: 14px; }
    .card-title { display: flex; align-items: center; gap: 8px; font-size: 0.78rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 14px; }
    .card-title svg { color: var(--accent); }

    textarea, input[type="text"] {
      width: 100%; background: var(--surface-2); color: var(--text); border: 1px solid var(--border);
      border-radius: 12px; padding: 12px 14px; font-size: 1rem; font-family: inherit; outline: none;
    }
    textarea { min-height: 100px; resize: vertical; line-height: 1.5; }
    textarea:focus, input[type="text"]:focus { border-color: var(--border-focus); }
    ::placeholder { color: var(--faint); }

    .btn {
      display: flex; align-items: center; justify-content: center; gap: 8px;
      width: 100%; padding: 12px; margin-top: 10px; border: none; border-radius: 12px;
      font-size: 0.92rem; font-weight: 600; font-family: inherit; cursor: pointer;
      transition: filter 0.15s, transform 0.1s;
    }
    .btn:active { transform: scale(0.985); filter: brightness(1.15); }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; filter: none; }
    .btn-primary { background: var(--accent); color: var(--accent-contrast); }
    .btn-ghost { background: var(--surface-2); color: var(--text); border: 1px dashed var(--border-focus); }
    .btn-danger { background: var(--red-soft); color: var(--red); }
    .btn-row { display: flex; gap: 8px; }
    .btn-row .btn { flex: 1; }

    .hint { font-size: 0.78rem; color: var(--muted); margin-top: 10px; text-align: center; min-height: 1.1em; }
    .hint.ok { color: var(--green); }
    .hint.err { color: var(--red); }

    .folder-card {
      background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px;
      padding: 14px; margin-bottom: 10px; position: relative;
    }
    .folder-card label { font-size: 0.72rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; display: block; margin-bottom: 4px; margin-top: 10px; }
    .folder-card label:first-child { margin-top: 0; }
    .folder-card input { padding: 8px 10px; font-size: 0.88rem; }
    .folder-card .delete-btn {
      position: absolute; top: 10px; right: 10px; width: 28px; height: 28px;
      border-radius: 8px; border: none; background: var(--red-soft); color: var(--red);
      cursor: pointer; display: grid; place-items: center; font-size: 1rem;
    }
    .folder-card .delete-btn:hover { background: var(--red); color: #fff; }

    .spinner { display: inline-block; width: 16px; height: 16px; border: 2px solid var(--accent-contrast); border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; }
    @keyframes spin { to { transform: rotate(360deg); } }

    .view { display: none; }
    .view.active { display: block; animation: fadeIn 0.18s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; } }

    .folder-list-item {
      display: flex; align-items: center; gap: 10px;
      background: var(--surface-2); border: 1px solid var(--border); border-radius: 12px;
      padding: 12px 14px; margin-bottom: 8px;
    }
    .folder-list-item .name { font-weight: 600; font-size: 0.9rem; min-width: 0; }
    .folder-list-item .desc { font-size: 0.8rem; color: var(--muted); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .folder-list-item .del-btn {
      flex: none; width: 28px; height: 28px; border-radius: 8px; border: none;
      background: var(--red-soft); color: var(--red); cursor: pointer; display: grid; place-items: center;
    }
    .folder-list-item .del-btn:hover { background: var(--red); color: #fff; }

    .add-row { display: flex; gap: 8px; margin-top: 10px; }
    .add-row input { flex: 1; padding: 10px 12px; font-size: 0.88rem; }
    .add-row .btn { width: auto; flex: none; padding: 10px 18px; margin-top: 0; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <div class="logo">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 2a5 5 0 0 0-5 5v1a4 4 0 0 0-2 7.5A4 4 0 0 0 8 22h1a3 3 0 0 0 3-3V5a3 3 0 0 1 3-3"/>
          <path d="M12 2a5 5 0 0 1 5 5v1a4 4 0 0 1 2 7.5A4 4 0 0 1 16 22h-1a3 3 0 0 1-3-3"/>
        </svg>
      </div>
      <div>
        <h1>Structure Setup</h1>
        <p>configure your knowledge folders</p>
      </div>
    </div>
    <a href="/ui/index.html" class="back-link">&larr; Back</a>
  </header>

  <!-- WIZARD VIEW -->
  <div class="view" id="wizard-view">
    <div class="card">
      <div class="card-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
        Describe Your Knowledge Base
      </div>
      <textarea id="descInput" placeholder="What is this brain for? What topics will you store? Who will use it?"></textarea>
      <button class="btn btn-primary" id="generateBtn" onclick="generate()">Generate Structure</button>
      <p class="hint" id="wizardHint"></p>
    </div>

    <div id="proposalSection" style="display:none">
      <div class="card">
        <div class="card-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 7h18M3 12h18M3 17h18"/></svg>
          Proposed Folders
        </div>
        <div id="folderCards"></div>
        <button class="btn btn-ghost" onclick="addBlankCard()">+ Add Folder</button>
        <div class="btn-row" style="margin-top:12px">
          <button class="btn btn-ghost" onclick="generate()">Regenerate</button>
          <button class="btn btn-primary" onclick="applyProposal()">Apply Structure</button>
        </div>
        <p class="hint" id="applyHint"></p>
      </div>
    </div>
  </div>

  <!-- MANAGER VIEW -->
  <div class="view" id="manager-view">
    <div class="card">
      <div class="card-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 7h18M3 12h18M3 17h18"/></svg>
        Knowledge Folders
      </div>
      <div id="folderList"></div>
      <div class="add-row">
        <input type="text" id="addName" placeholder="folder-name" />
        <input type="text" id="addDesc" placeholder="Description" />
        <button class="btn btn-primary" onclick="addFolder()">Add</button>
      </div>
      <p class="hint" id="managerHint"></p>
    </div>
    <button class="btn btn-ghost" onclick="showWizard()">Redesign with AI</button>
  </div>

  <script>
    /* --- State --- */
    let currentProposal = null;

    /* --- Init --- */
    async function init() {
      const data = await safeFetch("/structure");
      if (data && data.folders && data.folders.length > 0) {
        showManager(data.folders);
      } else {
        showWizard();
      }
    }

    function showWizard() {
      document.getElementById("wizard-view").classList.add("active");
      document.getElementById("manager-view").classList.remove("active");
    }

    function showManager(folders) {
      document.getElementById("manager-view").classList.add("active");
      document.getElementById("wizard-view").classList.remove("active");
      renderFolderList(folders);
    }

    /* --- Wizard --- */
    async function generate() {
      const desc = document.getElementById("descInput").value.trim();
      if (!desc) { setHint("wizardHint", "Please describe your knowledge base.", "err"); return; }
      const btn = document.getElementById("generateBtn");
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Generating…';
      setHint("wizardHint", "");
      const data = await safeFetch("/structure/propose", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({description: desc}),
      });
      btn.disabled = false;
      btn.textContent = "Generate Structure";
      if (!data) { setHint("wizardHint", "Generation failed. Check LLM config.", "err"); return; }
      currentProposal = data;
      renderProposal(data.folders);
      document.getElementById("proposalSection").style.display = "block";
    }

    function renderProposal(folders) {
      const container = document.getElementById("folderCards");
      container.innerHTML = folders.map((f, i) => `
        <div class="folder-card" data-idx="${i}">
          <button class="delete-btn" onclick="removeCard(${i})" title="Remove">&times;</button>
          <label>Name</label>
          <input type="text" value="${esc(f.name)}" onchange="updateCard(${i},'name',this.value)" />
          <label>Description</label>
          <input type="text" value="${esc(f.description)}" onchange="updateCard(${i},'description',this.value)" />
          <label>Examples (comma-separated)</label>
          <input type="text" value="${esc((f.examples||[]).join(', '))}" onchange="updateCard(${i},'examples',this.value)" />
        </div>
      `).join("");
    }

    function updateCard(idx, field, value) {
      if (field === "examples") {
        currentProposal.folders[idx].examples = value.split(",").map(s => s.trim()).filter(Boolean);
      } else {
        currentProposal.folders[idx][field] = value;
      }
    }

    function removeCard(idx) {
      currentProposal.folders.splice(idx, 1);
      renderProposal(currentProposal.folders);
    }

    function addBlankCard() {
      currentProposal.folders.push({name: "", display: "", description: "", examples: []});
      renderProposal(currentProposal.folders);
    }

    async function applyProposal() {
      // Validate names
      const nameRe = /^[a-z][a-z0-9-]{0,30}[a-z0-9]$/;
      for (const f of currentProposal.folders) {
        if (!nameRe.test(f.name)) {
          setHint("applyHint", `Invalid name: "${f.name}". Use lowercase + hyphens, 2-32 chars.`, "err");
          return;
        }
        f.display = f.display || f.name;
      }
      setHint("applyHint", "");
      const data = await safeFetch("/structure/apply", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(currentProposal),
      });
      if (!data) { setHint("applyHint", "Apply failed.", "err"); return; }
      setHint("applyHint", `Created ${data.folder_count} folders!`, "ok");
      setTimeout(async () => {
        const s = await safeFetch("/structure");
        if (s) showManager(s.folders);
      }, 1000);
    }

    /* --- Manager --- */
    function renderFolderList(folders) {
      const el = document.getElementById("folderList");
      el.innerHTML = folders.map(f => `
        <div class="folder-list-item">
          <span class="name">${esc(f.name)}</span>
          <span class="desc">${esc(f.description)}</span>
          ${f.name === "archive" ? "" : `<button class="del-btn" onclick="deleteFolder('${esc(f.name)}')" title="Delete">&times;</button>`}
        </div>
      `).join("");
    }

    async function addFolder() {
      const name = document.getElementById("addName").value.trim();
      const desc = document.getElementById("addDesc").value.trim();
      if (!name) return;
      const data = await safeFetch("/structure/folders", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({name, description: desc}),
      });
      if (!data) { setHint("managerHint", "Failed to add folder.", "err"); return; }
      if (data.detail) { setHint("managerHint", data.detail, "err"); return; }
      document.getElementById("addName").value = "";
      document.getElementById("addDesc").value = "";
      setHint("managerHint", `Added "${name}"`, "ok");
      const s = await safeFetch("/structure");
      if (s) renderFolderList(s.folders);
    }

    async function deleteFolder(name) {
      if (!confirm(`Delete folder "${name}"? Files will be moved to _unfiled.`)) return;
      const resp = await safeFetch(`/structure/folders/${name}`, {method: "DELETE"});
      if (!resp) { setHint("managerHint", "Delete failed.", "err"); return; }
      setHint("managerHint", `Deleted "${name}"`, "ok");
      const s = await safeFetch("/structure");
      if (s) renderFolderList(s.folders);
    }

    /* --- Helpers --- */
    async function safeFetch(url, opts) {
      try {
        const r = await fetch(url, opts);
        if (!r.ok) {
          const err = await r.json().catch(() => null);
          if (err && err.detail) return {detail: err.detail};
          return null;
        }
        return await r.json();
      } catch { return null; }
    }

    function setHint(id, text, cls) {
      const el = document.getElementById(id);
      el.textContent = text;
      el.className = "hint" + (cls ? " " + cls : "");
    }

    function esc(s) {
      return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
    }

    init();
  </script>
</body>
</html>
```

- [ ] **Step 2: Verify the page loads**

Run: `python -m simplebrain --port 8001 &` then open `http://localhost:8001/ui/setup.html` in a browser.
Expected: Page loads, shows wizard view (no structure exists yet).

- [ ] **Step 3: Commit**

```bash
git add ui/setup.html
git commit -m "feat: add setup.html — AI wizard + folder manager UI"
```

---

### Task 5: Link setup page from main UI

**Files:**
- Modify: `ui/index.html`

**Interfaces:**
- Consumes: None
- Produces: Gear icon in header that navigates to `/ui/setup.html`

- [ ] **Step 1: Add gear icon link to index.html header**

In `ui/index.html`, find the `.hdr-right` div and add a gear link before the scheme switcher:

Find this block (around line 382-383):
```html
    <div class="hdr-right">
      <div class="schemes" role="radiogroup" aria-label="Color scheme">
```

Replace with:
```html
    <div class="hdr-right">
      <a href="/ui/setup.html" class="mode-btn" aria-label="Setup" title="Folder Setup">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
      </a>
      <div class="schemes" role="radiogroup" aria-label="Color scheme">
```

- [ ] **Step 2: Verify the link works**

Open `http://localhost:8001/ui/index.html` — gear icon should appear in header. Clicking it navigates to setup page.

- [ ] **Step 3: Commit**

```bash
git add ui/index.html
git commit -m "feat: add gear icon linking to setup page from main UI"
```

---

### Task 6: Integration test — full wizard flow

**Files:**
- Modify: `tests/test_api_structure.py`

**Interfaces:**
- Consumes: All structure endpoints
- Produces: End-to-end test proving the wizard → manager flow works

- [ ] **Step 1: Write integration test**

```python
# Add to tests/test_api_structure.py

def test_full_wizard_flow(client, config, monkeypatch):
    """End-to-end: propose → edit → apply → verify → add folder → delete folder."""
    from simplebrain.setup import wizard as wizard_mod

    fake_proposal = {
        "summary": "Dev brain",
        "healer_schedule": "daily",
        "folders": [
            {"name": "code-notes", "display": "Code Notes", "description": "Programming stuff", "examples": ["python"]},
            {"name": "archive", "display": "Archive", "description": "Old", "examples": []},
        ],
    }
    monkeypatch.setattr(wizard_mod.SetupWizard, "propose", lambda self, d: fake_proposal)

    # Step 1: propose
    resp = client.post("/structure/propose", json={"description": "dev brain"})
    assert resp.status_code == 200
    proposal = resp.json()

    # Step 2: apply
    resp = client.post("/structure/apply", json=proposal)
    assert resp.status_code == 200
    assert resp.json()["folder_count"] == 2

    # Step 3: verify
    resp = client.get("/structure")
    assert resp.status_code == 200
    names = [f["name"] for f in resp.json()["folders"]]
    assert "code-notes" in names
    assert "archive" in names

    # Step 4: add a folder
    resp = client.post("/structure/folders", json={"name": "meetings", "description": "Meeting notes"})
    assert resp.status_code == 200

    # Step 5: verify it's there
    resp = client.get("/structure")
    names = [f["name"] for f in resp.json()["folders"]]
    assert "meetings" in names

    # Step 6: delete the new folder
    resp = client.delete("/structure/folders/meetings")
    assert resp.status_code == 200

    # Step 7: verify it's gone
    resp = client.get("/structure")
    names = [f["name"] for f in resp.json()["folders"]]
    assert "meetings" not in names
```

- [ ] **Step 2: Run all structure tests**

Run: `pytest tests/test_api_structure.py -v`
Expected: All tests PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_structure.py
git commit -m "test: add full wizard flow integration test"
```
