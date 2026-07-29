# Docling Integration — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a document ingestion path (PDF, DOCX, PPTX, XLSX, HTML, etc.) to SimpleBrain using Docling, so documents flow through the same Chunk → Tag → File → Index pipeline as voice and text notes.

**Architecture:** Docling converts documents to Markdown (its native output format). A new `DOCUMENT` job type runs through a `DoclingStage` that replaces `TranscribeStage` for documents — the output is a Markdown string saved as a transcript file. Everything downstream (ChunkStage, TagStage, FileStage, IndexStore) remains unchanged.

**Tech Stack:** `docling` (document parser), existing `litellm` + `pydantic` + `fastapi` stack.

## Global Constraints

- Python ≥ 3.11
- No new dependencies beyond `docling`
- All documents stored in `_raw/documents/` before processing
- Markdown output stored in `_raw/transcripts/` (same as voice transcriptions)
- Existing tests must continue to pass unchanged
- Follow existing code patterns: `get_logger(__name__)`, Pydantic models, relative path storage

---

### Task 1: Add `docling` dependency and `DOCUMENT` job type

**Files:**
- Modify: `pyproject.toml` (add `docling` to dependencies)
- Modify: `simplebrain/models.py:24-26` (add `DOCUMENT` to `JobType` enum)
- Modify: `simplebrain/config.py` (add `raw_documents_dir` property, create dir in `init_dirs`)
- Test: `tests/test_models.py` (new file — verify JobType.DOCUMENT exists)

**Interfaces:**
- Produces: `JobType.DOCUMENT` enum value, `BrainConfig.raw_documents_dir` property

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from simplebrain.models import JobType, Job


def test_document_job_type_exists():
    assert JobType.DOCUMENT == "document"


def test_create_document_job():
    job = Job(type=JobType.DOCUMENT, user="test")
    assert job.type == JobType.DOCUMENT
    assert job.raw_path is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `JobType` has no `DOCUMENT` member

- [ ] **Step 3: Add DOCUMENT to JobType enum**

In `simplebrain/models.py`, add to the `JobType` class:

```python
class JobType(str, Enum):
    VOICE = "voice"
    TEXT = "text"
    DOCUMENT = "document"
```

- [ ] **Step 4: Add `raw_documents_dir` to BrainConfig**

In `simplebrain/config.py`, add a property after `raw_transcripts_dir`:

```python
@property
def raw_documents_dir(self) -> Path:
    return self.brain_root / "_raw" / "documents"
```

Update `init_dirs` to include `self.raw_documents_dir`:

```python
def init_dirs(self) -> None:
    for folder in [
        self.raw_audio_dir, self.raw_transcripts_dir,
        self.raw_documents_dir,
        self.queue_dir, self.queue_dir / "failed",
        self.index_dir,
        self.conflicts_dir / "pending",
        self.meta_dir,
        self.knowledge_dir / "_unfiled",
    ]:
        folder.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 5: Add `docling` to pyproject.toml**

```toml
dependencies = [
    ...
    "docling>=2.0.0",
]
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_models.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml simplebrain/models.py simplebrain/config.py tests/test_models.py
git commit -m "feat: add DOCUMENT job type and raw_documents_dir config"
```

---

### Task 2: Add `save_document` to RawStore

**Files:**
- Modify: `simplebrain/store/raw.py` (add `save_document` method)
- Test: `tests/test_raw_store.py` (new file)

**Interfaces:**
- Consumes: `BrainConfig.raw_documents_dir`
- Produces: `RawStore.save_document(doc_bytes, filename, job_id) -> str` (relative path)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_raw_store.py
from pathlib import Path
from simplebrain.config import BrainConfig
from simplebrain.store.raw import RawStore


def test_save_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()
    store = RawStore(config)

    content = b"%PDF-1.4 fake pdf content"
    rel_path = store.save_document(content, "report.pdf", "abc12345")

    saved = tmp_path / rel_path
    assert saved.exists()
    assert saved.read_bytes() == content
    assert saved.suffix == ".pdf"
    assert "abc12345" in saved.name
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_raw_store.py::test_save_document -v`
Expected: FAIL — `RawStore` has no attribute `save_document`

- [ ] **Step 3: Implement `save_document`**

Add to `simplebrain/store/raw.py`:

```python
def save_document(self, doc_bytes: bytes, filename: str, job_id: str) -> str:
    """Save raw document. Returns relative path from brain_root."""
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    suffix = Path(filename).suffix or ".bin"
    path = self.config.raw_documents_dir / f"{ts}-{job_id}{suffix}"
    path.write_bytes(doc_bytes)
    return str(path.relative_to(self.config.brain_root))
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_raw_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/store/raw.py tests/test_raw_store.py
git commit -m "feat: add save_document to RawStore"
```

---

### Task 3: Create DoclingStage

**Files:**
- Create: `simplebrain/pipeline/docling_stage.py`
- Test: `tests/test_docling_stage.py`

**Interfaces:**
- Consumes: `Job` with `type=DOCUMENT`, `raw_path` pointing to a file in `_raw/documents/`
- Produces: `DoclingStage.run(job: Job) -> Job` — sets `job.transcript_path` to a `.md` file in `_raw/transcripts/`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_docling_stage.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType
from simplebrain.pipeline.docling_stage import DoclingStage


def test_docling_stage_converts_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()

    # Write a fake document
    doc_path = config.raw_documents_dir / "20260728T120000-abc12345.pdf"
    doc_path.write_bytes(b"%PDF-1.4 fake content")

    job = Job(type=JobType.DOCUMENT, user="test", id="abc12345")
    job.raw_path = str(doc_path.relative_to(tmp_path))

    # Mock docling to avoid needing real PDF parsing in tests
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Extracted Title\n\nSome content from the PDF."

    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    with patch("simplebrain.pipeline.docling_stage.DocumentConverter", return_value=mock_converter):
        stage = DoclingStage(config)
        result = stage.run(job)

    assert result.transcript_path is not None
    transcript = (tmp_path / result.transcript_path).read_text(encoding="utf-8")
    assert "Extracted Title" in transcript
    assert "Some content from the PDF" in transcript
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_docling_stage.py -v`
Expected: FAIL — module `simplebrain.pipeline.docling_stage` does not exist

- [ ] **Step 3: Implement DoclingStage**

Create `simplebrain/pipeline/docling_stage.py`:

```python
from __future__ import annotations
from datetime import datetime, timezone
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger
from simplebrain.models import Job

log = get_logger(__name__)

try:
    from docling.document_converter import DocumentConverter
except ImportError:
    DocumentConverter = None  # type: ignore


class DoclingStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> Job:
        if DocumentConverter is None:
            raise RuntimeError(
                "docling is not installed. Install it with: pip install docling"
            )

        doc_path = self.config.brain_root / job.raw_path
        log.info("[job=%s] Parsing document with Docling: %s", job.id, doc_path)

        if not doc_path.exists():
            raise FileNotFoundError(f"Document not found: {doc_path}")

        converter = DocumentConverter()
        result = converter.convert(str(doc_path))
        md = result.document.export_to_markdown()

        log.info("[job=%s] Docling conversion complete — chars=%d", job.id, len(md))

        if not md.strip():
            log.warning("[job=%s] Docling produced empty output", job.id)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = self.config.raw_transcripts_dir / f"{ts}-{job.id}.md"
        out_path.write_text(md, encoding="utf-8")
        job.transcript_path = str(out_path.relative_to(self.config.brain_root))

        log.info("[job=%s] Document markdown saved: %s", job.id, out_path)
        return job
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/test_docling_stage.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/pipeline/docling_stage.py tests/test_docling_stage.py
git commit -m "feat: add DoclingStage — converts documents to markdown"
```

---

### Task 4: Wire DoclingStage into BackgroundWorker

**Files:**
- Modify: `simplebrain/pipeline/worker.py` (import DoclingStage, route DOCUMENT jobs)
- Modify: `simplebrain/pipeline/transcribe.py` (add DOCUMENT passthrough in TranscribeStage)
- Test: `tests/test_worker_docling.py`

**Interfaces:**
- Consumes: `DoclingStage.run(job)`, `JobType.DOCUMENT`
- Produces: `BackgroundWorker` routes DOCUMENT jobs through DoclingStage → ChunkStage → TagStage → FileStage → IndexStore

- [ ] **Step 1: Write the failing test**

```python
# tests/test_worker_docling.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType
from simplebrain.ingest.queue import FileQueue
from simplebrain.pipeline.worker import BackgroundWorker


def test_worker_processes_document_job(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()

    # Setup: structure.json needed by FileStage
    meta = config.meta_dir / "structure.json"
    meta.write_text('{"folders": [{"name": "general", "description": "General"}], "pending_proposals": []}')
    setup = config.meta_dir / "setup.json"
    setup.write_text('{"summary": "test brain", "healer_schedule": "manual"}')

    # Queue a document job
    doc_path = config.raw_documents_dir / "20260728T120000-testdoc1.pdf"
    doc_path.write_bytes(b"fake pdf")
    job = Job(type=JobType.DOCUMENT, user="test", id="testdoc1")
    job.raw_path = str(doc_path.relative_to(tmp_path))
    queue = FileQueue(config)
    queue.enqueue(job)

    # Mock Docling and LLM calls
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Report\n\nImportant findings about testing."
    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    mock_llm_responses = [
        # ChunkStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='["Important findings about testing."]'))]),
        # TagStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"title": "Testing Report", "tags": ["#testing", "#report"]}'))]),
        # FileStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"folder": "general", "is_new": false, "reasoning": "fits general"}'))]),
    ]

    with patch("simplebrain.pipeline.docling_stage.DocumentConverter", return_value=mock_converter):
        with patch("litellm.completion", side_effect=mock_llm_responses):
            worker = BackgroundWorker(config)
            result = worker.process_one()

    assert result is True
    # Verify chunk was written
    knowledge_files = list(config.knowledge_dir.rglob("*.md"))
    readme_files = [f for f in knowledge_files if f.name == "README.md"]
    chunk_files = [f for f in knowledge_files if f.name != "README.md"]
    assert len(chunk_files) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_worker_docling.py -v`
Expected: FAIL — worker doesn't handle DOCUMENT jobs

- [ ] **Step 3: Update TranscribeStage to skip DOCUMENT jobs**

In `simplebrain/pipeline/transcribe.py`, add handling for DOCUMENT type at the top of `run()`:

```python
def run(self, job: Job) -> Job:
    if job.type == JobType.TEXT:
        log.debug("[job=%s] TEXT job — skipping transcription, raw_path=%s",
                  job.id, job.raw_path)
        job.transcript_path = job.raw_path
        return job

    if job.type == JobType.DOCUMENT:
        log.debug("[job=%s] DOCUMENT job — handled by DoclingStage", job.id)
        return job

    # ... rest of voice handling
```

- [ ] **Step 4: Update BackgroundWorker to route DOCUMENT jobs**

In `simplebrain/pipeline/worker.py`:

```python
from simplebrain.pipeline.docling_stage import DoclingStage
from simplebrain.models import JobStatus, JobType

class BackgroundWorker:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.queue = FileQueue(config)
        self.transcribe = TranscribeStage(config)
        self.docling = DoclingStage(config)
        self.chunk = ChunkStage(config)
        self.tag = TagStage(config)
        self.file = FileStage(config)
        self.index = IndexStore(config)
        self.knowledge = KnowledgeStore(config)

    def process_one(self) -> bool:
        job = self.queue.dequeue()
        if job is None:
            return False

        log.info("[job=%s] Dequeued — type=%s user=%s device=%s raw_path=%s",
                 job.id, job.type, job.user, job.device, job.raw_path)

        try:
            # Stage 1: Transcribe / Parse
            log.info("[job=%s] Stage 1/5: Transcribe/Parse", job.id)
            if job.type == JobType.DOCUMENT:
                job = self.docling.run(job)
            else:
                job = self.transcribe.run(job)
            log.info("[job=%s] Stage 1 done — transcript_path=%s", job.id, job.transcript_path)

            # ... Stages 2-5 unchanged
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_worker_docling.py -v`
Expected: PASS

Run: `pytest tests/ -v`
Expected: All existing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/pipeline/worker.py simplebrain/pipeline/transcribe.py tests/test_worker_docling.py
git commit -m "feat: route DOCUMENT jobs through DoclingStage in worker"
```

---

### Task 5: Add `add_document` to IngestService, REST API, and MCP

**Files:**
- Modify: `simplebrain/ingest/service.py` (add `add_document` method)
- Modify: `simplebrain/api/routes.py` (add `POST /notes/document` endpoint)
- Modify: `simplebrain/mcp/server.py` (add `add_document` tool)
- Test: `tests/test_api_document.py`

**Interfaces:**
- Consumes: `RawStore.save_document`, `FileQueue.enqueue`, `JobType.DOCUMENT`
- Produces: `IngestService.add_document(doc_bytes, filename, user, device)`, `POST /notes/document`, MCP `add_document` tool

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api_document.py
import base64
from fastapi.testclient import TestClient
from simplebrain.config import BrainConfig
from simplebrain.api.routes import create_app


def test_post_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()
    (config.meta_dir / "structure.json").write_text(
        '{"folders": [], "pending_proposals": []}'
    )

    app = create_app(config)
    client = TestClient(app)

    pdf_content = b"%PDF-1.4 test content"
    b64 = base64.b64encode(pdf_content).decode()

    resp = client.post("/notes/document", json={
        "file_b64": b64,
        "filename": "test.pdf",
        "user": "testuser",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data

    # Verify file was saved
    docs = list(config.raw_documents_dir.glob("*"))
    assert len(docs) == 1
    assert docs[0].read_bytes() == pdf_content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_document.py -v`
Expected: FAIL — no `/notes/document` endpoint

- [ ] **Step 3: Add `add_document` to IngestService**

In `simplebrain/ingest/service.py`:

```python
def add_document(self, doc_bytes: bytes, filename: str,
                 user: str, device: str = "unknown") -> str:
    job = Job(type=JobType.DOCUMENT, user=user, device=device)
    log.info("[job=%s] Ingesting DOCUMENT — user=%s device=%s filename=%s bytes=%d",
             job.id, user, device, filename, len(doc_bytes))

    raw_path = self.raw.save_document(doc_bytes, filename, job.id)
    job.raw_path = raw_path
    log.info("[job=%s] Document saved: %s", job.id, raw_path)

    self.queue.enqueue(job)
    log.info("[job=%s] Queued for processing", job.id)
    return job.id
```

- [ ] **Step 4: Add request model and endpoint to routes.py**

In `simplebrain/api/routes.py`, add the request model:

```python
class DocumentNoteRequest(BaseModel):
    file_b64: str
    filename: str
    user: str
    device: str = "unknown"
```

Add the endpoint after the `/notes/voice` route:

```python
@app.post("/notes/document")
def add_document(req: DocumentNoteRequest):
    doc = base64.b64decode(req.file_b64)
    job_id = ingest.add_document(doc, req.filename, req.user, req.device)
    return {"job_id": job_id}
```

- [ ] **Step 5: Add `add_document` tool to MCP server**

In `simplebrain/mcp/server.py`, add to `_build_tools()` list:

```python
T("add_document",
  "Add a document (base64-encoded PDF, DOCX, PPTX, etc.) to the brain",
  required=["file_b64", "filename", "user"],
  properties={
      "file_b64": {"type": "string", "description": "Base64-encoded document"},
      "filename": {"type": "string", "description": "Original filename with extension"},
      "user": {"type": "string"},
      "device": {"type": "string", "default": "unknown"},
  }),
```

Add the handler in `_call_tool_async`:

```python
elif name == "add_document":
    import base64
    doc = base64.b64decode(arguments["file_b64"])
    job_id = self._ingest.add_document(
        doc,
        arguments["filename"],
        arguments["user"],
        arguments.get("device", "unknown"),
    )
    return ok({"job_id": job_id})
```

- [ ] **Step 6: Run tests**

Run: `pytest tests/test_api_document.py -v`
Expected: PASS

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add simplebrain/ingest/service.py simplebrain/api/routes.py simplebrain/mcp/server.py tests/test_api_document.py
git commit -m "feat: add document ingest endpoint (REST + MCP)"
```

---

### Task 6: Install docling and run end-to-end integration test

**Files:**
- No new files — verify the full pipeline works with a real document

- [ ] **Step 1: Install docling**

```bash
pip install -e .
```

Verify: `python -c "from docling.document_converter import DocumentConverter; print('ok')"`

- [ ] **Step 2: Create a test PDF and run the full pipeline**

```bash
python -c "
import base64, requests

# Create a minimal test: use a simple text file as document
# (Docling handles .txt files too)
content = base64.b64encode(b'This is a test document about machine learning pipelines.').decode()

resp = requests.post('http://localhost:8000/notes/document', json={
    'file_b64': content,
    'filename': 'test.txt',
    'user': 'srivpra',
})
print(resp.json())
"
```

- [ ] **Step 3: Monitor the worker log for successful processing**

```bash
tail -f brain/brain.log | grep -E "(Stage|COMPLETE|FAILED)"
```

Expected: job completes through all 5 stages, chunk appears in `knowledge/` folder.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 5: Commit any fixes needed**

```bash
git add -A
git commit -m "chore: verify docling integration end-to-end"
```

---

## Summary

| Task | What it delivers |
|---|---|
| 1 | `JobType.DOCUMENT`, `raw_documents_dir`, `docling` dependency |
| 2 | `RawStore.save_document()` |
| 3 | `DoclingStage` — document → markdown conversion |
| 4 | Worker routing — DOCUMENT jobs flow through DoclingStage |
| 5 | API + MCP entrypoints — `POST /notes/document` + `add_document` tool |
| 6 | End-to-end verification |

Total: ~6 files modified, 2 files created, 1 new dependency. The downstream pipeline (Chunk → Tag → File → Index) is completely unchanged.
