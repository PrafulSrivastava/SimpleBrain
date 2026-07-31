from __future__ import annotations
import base64
import re
import shutil
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field
from simplebrain.config import BrainConfig
from simplebrain.ingest.service import IngestService
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.store.index import IndexStore
from simplebrain.brain.grower import SelfGrower
from simplebrain.brain.healer import SelfHealer
from simplebrain.models import Resolution


class TextNoteRequest(BaseModel):
    text: str
    user: str
    device: str = "unknown"


class VoiceNoteRequest(BaseModel):
    audio_b64: str
    filename: str
    user: str
    device: str = "unknown"


class DocumentNoteRequest(BaseModel):
    file_b64: str
    filename: str
    user: str
    device: str = "unknown"


class ResolveConflictRequest(BaseModel):
    resolution: str
    resolved_by: str


class RejectProposalRequest(BaseModel):
    target_folder: str


class ApplyStructureRequest(BaseModel):
    summary: str = "Personal knowledge base."
    healer_schedule: str = "daily"
    folders: list[dict]


class ProposeStructureRequest(BaseModel):
    description: str = Field(min_length=1)


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


def create_app(config: BrainConfig) -> FastAPI:
    app = FastAPI(title="SimpleBrain", version="0.1.0")
    ingest = IngestService(config)
    knowledge = KnowledgeStore(config)
    index = IndexStore(config)
    grower = SelfGrower(config)
    healer = SelfHealer(config)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/status")
    def status():
        queue_files = list(config.queue_dir.glob("*.json"))
        return {
            "queue_depth": len(queue_files),
            "pending_conflicts": len(healer.list_pending()),
            "pending_proposals": len(grower.list_pending()),
        }

    @app.post("/notes/text")
    def add_text_note(req: TextNoteRequest):
        job_id = ingest.add_text_note(req.text, req.user, req.device)
        return {"job_id": job_id}

    @app.post("/notes/voice")
    def add_voice_note(req: VoiceNoteRequest):
        audio = base64.b64decode(req.audio_b64)
        job_id = ingest.add_voice_note(audio, req.filename, req.user, req.device)
        return {"job_id": job_id}

    @app.post("/notes/document")
    def add_document(req: DocumentNoteRequest):
        try:
            doc = base64.b64decode(req.file_b64)
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid base64 in file_b64")
        job_id = ingest.add_document(doc, req.filename, req.user, req.device)
        return {"job_id": job_id}

    @app.get("/topics")
    def list_topics():
        topics = index.load_topics()
        return {"topics": {k: len(v) for k, v in topics.items()}}

    @app.get("/tags")
    def list_tags():
        tags = index.load_tags()
        return {"tags": {k: len(v) for k, v in tags.items()}}

    @app.get("/search")
    def search(query: str, tags: str = ""):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        ids = index.search(query, tag_list or None)
        chunks = []
        for cid in ids[:10]:
            try:
                c = knowledge.read(cid)
                chunks.append({
                    "id": c.id,
                    "content": c.content[:300],
                    "tags": c.tags,
                    "file_path": c.file_path,
                })
            except FileNotFoundError:
                continue
        return {"results": chunks}

    @app.get("/chunks/{chunk_id}")
    def get_chunk(chunk_id: str):
        c = knowledge.read(chunk_id)
        return {
            "id": c.id,
            "content": c.content,
            "tags": c.tags,
            "links": c.links,
            "user": c.user,
            "device": c.device,
        }

    @app.get("/proposals")
    def list_proposals():
        return {"proposals": [p.model_dump() for p in grower.list_pending()]}

    @app.post("/proposals/{proposal_id}/confirm")
    def confirm_proposal(proposal_id: str):
        p = grower.confirm_proposal(proposal_id)
        return {"confirmed": p is not None}

    @app.post("/proposals/{proposal_id}/reject")
    def reject_proposal(proposal_id: str, req: RejectProposalRequest):
        p = grower.reject_proposal(proposal_id)
        return {"rejected": p is not None}

    @app.get("/conflicts")
    def list_conflicts():
        return {"conflicts": [c.model_dump() for c in healer.list_pending()]}

    @app.post("/conflicts/{conflict_id}/resolve")
    def resolve_conflict(conflict_id: str, req: ResolveConflictRequest):
        healer.resolve(conflict_id, Resolution(req.resolution), req.resolved_by)
        return {"resolved": True}

    @app.post("/conflicts/{conflict_id}/revert")
    def revert_resolution(conflict_id: str):
        healer.revert(conflict_id)
        return {"reverted": True}

    @app.post("/heal")
    def run_healer():
        conflicts = healer.scan()
        return {"conflicts_found": len(conflicts)}

    # --- Structure management ---

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

    @app.post("/structure/propose")
    def propose_structure(req: ProposeStructureRequest):
        from simplebrain.setup.wizard import SetupWizard
        wizard = SetupWizard(config)
        proposal = wizard.propose(req.description)
        return proposal

    @app.post("/structure/apply")
    def apply_structure(req: ApplyStructureRequest):
        from simplebrain.setup.wizard import SetupWizard
        wizard = SetupWizard(config)
        proposal = {"summary": req.summary, "healer_schedule": req.healer_schedule, "folders": req.folders}
        folder_names = wizard.apply(proposal)
        return {"applied": True, "folder_count": len(folder_names)}

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

    # Serve mobile UI
    ui_dir = Path(__file__).parent.parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir)), name="ui")

    @app.get("/")
    def root():
        ui_index = ui_dir / "index.html"
        if ui_index.exists():
            return FileResponse(str(ui_index))
        return {"message": "SimpleBrain API", "docs": "/docs"}

    return app
