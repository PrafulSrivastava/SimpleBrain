from __future__ import annotations
import base64
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
