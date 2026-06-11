# SimpleBrain Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-organising, self-growing, self-healing second brain that accepts voice and text notes, processes them asynchronously through an LLM pipeline, and exposes everything via an MCP server and a lightweight FastAPI web UI.

**Architecture:** An async ingest service instantly queues raw input while a background worker runs a 5-stage pipeline (Transcribe → Chunk → Tag → File → Index). All knowledge is stored as Markdown files with YAML frontmatter in a human-readable folder structure. An MCP server and FastAPI REST layer expose the full feature set.

**Tech Stack:** Python 3.11+, faster-whisper, LiteLLM (multi-provider LLM abstraction), MCP Python SDK, FastAPI, watchdog, pytest

---

## File Structure

```
simplebrain/
├── simplebrain/
│   ├── __init__.py
│   ├── config.py                  # Brain config loader (_meta/setup.json)
│   ├── models.py                  # Pydantic models: Job, Chunk, Conflict, Proposal
│   │
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── service.py             # IngestService: save raw, enqueue job
│   │   └── queue.py               # FileQueue: write/read/delete jobs in _queue/
│   │
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── worker.py              # BackgroundWorker: watchdog-powered job runner
│   │   ├── transcribe.py          # Stage 1: faster-whisper STT
│   │   ├── chunk.py               # Stage 2: LLM semantic chunking
│   │   ├── tag.py                 # Stage 3: LLM auto-tagging
│   │   ├── file.py                # Stage 4: LLM folder filing + proposal creation
│   │   └── index.py               # Stage 5: update _index/tags.json + topics.json
│   │
│   ├── store/
│   │   ├── __init__.py
│   │   ├── raw.py                 # RawStore: save/read audio and transcripts
│   │   ├── knowledge.py           # KnowledgeStore: read/write chunk .md files
│   │   └── index.py               # IndexStore: read/write _index/tags.json + topics.json
│   │
│   ├── brain/
│   │   ├── __init__.py
│   │   ├── grower.py              # SelfGrower: manage folder proposals
│   │   └── healer.py              # SelfHealer: detect + flag conflicts
│   │
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py              # MCP server: all tool definitions
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py              # FastAPI routes (1:1 with MCP tools)
│   │   └── ui.py                  # Serve mobile web UI static files
│   │
│   └── setup/
│       ├── __init__.py
│       └── wizard.py              # SetupWizard: interview + generate folder structure
│
├── ui/
│   └── index.html                 # Minimal mobile web UI (voice + text input)
│
├── tests/
│   ├── conftest.py                # Shared fixtures (tmp brain dir, mock LLM)
│   ├── test_queue.py
│   ├── test_ingest.py
│   ├── test_transcribe.py
│   ├── test_chunk.py
│   ├── test_tag.py
│   ├── test_file.py
│   ├── test_index.py
│   ├── test_worker.py
│   ├── test_grower.py
│   ├── test_healer.py
│   ├── test_mcp.py
│   ├── test_api.py
│   └── test_setup.py
│
├── pyproject.toml
├── README.md
└── .env.example
```

---

## Task 1: Project Scaffold & Core Models

**Files:**
- Create: `pyproject.toml`
- Create: `simplebrain/__init__.py`
- Create: `simplebrain/models.py`
- Create: `tests/conftest.py`
- Create: `.env.example`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "simplebrain"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "faster-whisper>=1.0.3",
    "litellm>=1.40.0",
    "mcp>=1.0.0",
    "fastapi>=0.111.0",
    "uvicorn>=0.30.0",
    "watchdog>=4.0.0",
    "pydantic>=2.7.0",
    "python-frontmatter>=1.1.0",
    "python-multipart>=0.0.9",
    "python-dotenv>=1.0.0",
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
```

- [ ] **Step 2: Create simplebrain/__init__.py**

```python
"""SimpleBrain — self-organising second brain."""
```

- [ ] **Step 3: Create simplebrain/models.py**

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


class JobStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    CHUNKING = "chunking"
    TAGGING = "tagging"
    FILING = "filing"
    INDEXING = "indexing"
    COMPLETE = "complete"
    FAILED = "failed"


class JobType(str, Enum):
    VOICE = "voice"
    TEXT = "text"


class Job(BaseModel):
    id: str = Field(default_factory=_new_id)
    type: JobType
    user: str
    device: str = "unknown"
    created: datetime = Field(default_factory=datetime.utcnow)
    status: JobStatus = JobStatus.PENDING
    raw_path: Optional[str] = None       # path to audio or transcript in _raw/
    transcript_path: Optional[str] = None
    error: Optional[str] = None


class Chunk(BaseModel):
    id: str = Field(default_factory=_new_id)
    created: datetime = Field(default_factory=datetime.utcnow)
    source_raw: str
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    parent: Optional[str] = None
    user: str
    device: str = "unknown"
    content: str
    file_path: Optional[str] = None      # relative path under knowledge/


class ConflictType(str, Enum):
    FACTUAL = "factual_conflict"
    STRUCTURAL = "structural_issue"
    PIVOT = "pivot"


class ConflictStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REVERTED = "reverted"


class Resolution(str, Enum):
    KEEP_NEWER = "keep_newer"
    KEEP_OLDER = "keep_older"
    KEEP_BOTH = "keep_both"
    MERGE = "merge"
    ARCHIVE = "archive"


class Conflict(BaseModel):
    id: str = Field(default_factory=_new_id)
    detected: datetime = Field(default_factory=datetime.utcnow)
    type: ConflictType
    chunks_involved: list[str]
    summary: str
    status: ConflictStatus = ConflictStatus.PENDING
    resolution: Optional[Resolution] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    snapshot: dict = Field(default_factory=dict)  # chunk content before resolution


class FolderProposalStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class FolderProposal(BaseModel):
    id: str = Field(default_factory=_new_id)
    proposed_folder: str
    reasoning: str
    held_chunk_ids: list[str] = Field(default_factory=list)
    status: FolderProposalStatus = FolderProposalStatus.PENDING
    created: datetime = Field(default_factory=datetime.utcnow)
```

- [ ] **Step 4: Create tests/conftest.py**

```python
import pytest
import tempfile
from pathlib import Path
from simplebrain.config import BrainConfig


@pytest.fixture
def brain_dir(tmp_path: Path) -> Path:
    """A temporary directory pre-structured as a SimpleBrain root."""
    for folder in ["_raw/audio", "_raw/transcripts", "_queue/failed",
                   "_index", "_conflicts/pending", "_meta",
                   "knowledge/_unfiled"]:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def config(brain_dir: Path) -> BrainConfig:
    return BrainConfig(brain_root=brain_dir, user="testuser", device="test")
```

- [ ] **Step 5: Create .env.example**

```
BRAIN_ROOT=~/simplebrain
OPENAI_API_KEY=sk-...
# ANTHROPIC_API_KEY=sk-ant-...
# OLLAMA_BASE_URL=http://localhost:11434
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
HEALER_SCHEDULE=daily
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -e ".[dev]" 2>/dev/null || pip install -e .
```

Expected: installs without errors.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "feat: project scaffold and core models"
```

---

## Task 2: BrainConfig

**Files:**
- Create: `simplebrain/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_config.py
from pathlib import Path
from simplebrain.config import BrainConfig


def test_config_creates_directories(brain_dir):
    config = BrainConfig(brain_root=brain_dir, user="alice", device="mac")
    assert (brain_dir / "_raw" / "audio").exists()
    assert (brain_dir / "_queue").exists()
    assert (brain_dir / "knowledge").exists()


def test_config_paths(brain_dir):
    config = BrainConfig(brain_root=brain_dir, user="alice", device="mac")
    assert config.queue_dir == brain_dir / "_queue"
    assert config.raw_audio_dir == brain_dir / "_raw" / "audio"
    assert config.raw_transcripts_dir == brain_dir / "_raw" / "transcripts"
    assert config.knowledge_dir == brain_dir / "knowledge"
    assert config.index_dir == brain_dir / "_index"
    assert config.conflicts_dir == brain_dir / "_conflicts"
    assert config.meta_dir == brain_dir / "_meta"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL with "cannot import name 'BrainConfig'"

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/config.py
from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
import os


class BrainConfig(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    brain_root: Path
    user: str
    device: str = "unknown"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    def model_post_init(self, __context):
        for folder in [
            self.raw_audio_dir, self.raw_transcripts_dir,
            self.queue_dir, self.queue_dir / "failed",
            self.index_dir,
            self.conflicts_dir / "pending",
            self.meta_dir,
            self.knowledge_dir / "_unfiled",
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def raw_audio_dir(self) -> Path:
        return self.brain_root / "_raw" / "audio"

    @property
    def raw_transcripts_dir(self) -> Path:
        return self.brain_root / "_raw" / "transcripts"

    @property
    def queue_dir(self) -> Path:
        return self.brain_root / "_queue"

    @property
    def knowledge_dir(self) -> Path:
        return self.brain_root / "knowledge"

    @property
    def index_dir(self) -> Path:
        return self.brain_root / "_index"

    @property
    def conflicts_dir(self) -> Path:
        return self.brain_root / "_conflicts"

    @property
    def meta_dir(self) -> Path:
        return self.brain_root / "_meta"

    @classmethod
    def from_env(cls) -> "BrainConfig":
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            brain_root=Path(os.getenv("BRAIN_ROOT", "~/simplebrain")).expanduser(),
            user=os.getenv("BRAIN_USER", "default"),
            device=os.getenv("BRAIN_DEVICE", "unknown"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/config.py tests/test_config.py
git commit -m "feat: BrainConfig with directory bootstrapping"
```

---

## Task 3: File Queue

**Files:**
- Create: `simplebrain/ingest/queue.py`
- Create: `simplebrain/ingest/__init__.py`
- Test: `tests/test_queue.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_queue.py
import json
from simplebrain.ingest.queue import FileQueue
from simplebrain.models import Job, JobType, JobStatus


def test_enqueue_creates_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="_raw/transcripts/x.txt")
    q.enqueue(job)
    files = list(config.queue_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["id"] == job.id


def test_dequeue_returns_oldest_job(config):
    q = FileQueue(config)
    job1 = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    job2 = Job(type=JobType.TEXT, user="alice", raw_path="b.txt")
    q.enqueue(job1)
    q.enqueue(job2)
    result = q.dequeue()
    assert result is not None
    assert result.id == job1.id


def test_dequeue_empty_returns_none(config):
    q = FileQueue(config)
    assert q.dequeue() is None


def test_mark_failed_moves_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    q.enqueue(job)
    q.mark_failed(job, error="boom")
    assert len(list(config.queue_dir.glob("*.json"))) == 0
    failed = list((config.queue_dir / "failed").glob("*.json"))
    assert len(failed) == 1


def test_complete_removes_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    q.enqueue(job)
    q.complete(job)
    assert len(list(config.queue_dir.glob("*.json"))) == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_queue.py -v
```

Expected: FAIL with "cannot import name 'FileQueue'"

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/ingest/__init__.py
```

```python
# simplebrain/ingest/queue.py
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobStatus


class FileQueue:
    def __init__(self, config: BrainConfig):
        self.config = config

    def _job_path(self, job: Job) -> Path:
        return self.config.queue_dir / f"{job.created.timestamp():.6f}-{job.id}.json"

    def enqueue(self, job: Job) -> None:
        path = self._job_path(job)
        path.write_text(job.model_dump_json(indent=2))

    def dequeue(self) -> Optional[Job]:
        files = sorted(self.config.queue_dir.glob("*.json"))
        if not files:
            return None
        data = json.loads(files[0].read_text())
        return Job(**data)

    def _find_job_file(self, job: Job) -> Optional[Path]:
        matches = list(self.config.queue_dir.glob(f"*-{job.id}.json"))
        return matches[0] if matches else None

    def mark_failed(self, job: Job, error: str) -> None:
        path = self._find_job_file(job)
        if path:
            job.status = JobStatus.FAILED
            job.error = error
            dest = self.config.queue_dir / "failed" / path.name
            path.rename(dest)
            dest.write_text(job.model_dump_json(indent=2))

    def complete(self, job: Job) -> None:
        path = self._find_job_file(job)
        if path:
            path.unlink()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_queue.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/ingest/ tests/test_queue.py
git commit -m "feat: file-based job queue"
```

---

## Task 4: Raw Store & Ingest Service

**Files:**
- Create: `simplebrain/store/raw.py`
- Create: `simplebrain/store/__init__.py`
- Create: `simplebrain/ingest/service.py`
- Test: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ingest.py
from pathlib import Path
from simplebrain.ingest.service import IngestService
from simplebrain.models import JobType, JobStatus


def test_add_text_note_returns_job_id(config):
    svc = IngestService(config)
    job_id = svc.add_text_note("Hello world", user="alice", device="mac")
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_add_text_note_saves_to_raw(config):
    svc = IngestService(config)
    svc.add_text_note("Hello world", user="alice", device="mac")
    files = list(config.raw_transcripts_dir.glob("*.txt"))
    assert len(files) == 1
    assert files[0].read_text() == "Hello world"


def test_add_text_note_enqueues_job(config):
    svc = IngestService(config)
    svc.add_text_note("Hello world", user="alice", device="mac")
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    job = q.dequeue()
    assert job is not None
    assert job.type == JobType.TEXT
    assert job.user == "alice"


def test_add_voice_note_saves_audio(config):
    svc = IngestService(config)
    fake_audio = b"RIFF....fake audio data"
    job_id = svc.add_voice_note(fake_audio, filename="test.wav",
                                 user="alice", device="iphone")
    audio_files = list(config.raw_audio_dir.glob("*.wav"))
    assert len(audio_files) == 1


def test_add_voice_note_enqueues_job(config):
    svc = IngestService(config)
    fake_audio = b"RIFF....fake audio data"
    svc.add_voice_note(fake_audio, filename="test.wav",
                       user="alice", device="iphone")
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    job = q.dequeue()
    assert job is not None
    assert job.type == JobType.VOICE
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_ingest.py -v
```

Expected: FAIL with "cannot import name 'IngestService'"

- [ ] **Step 3: Write store/raw.py**

```python
# simplebrain/store/__init__.py
```

```python
# simplebrain/store/raw.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
from simplebrain.config import BrainConfig


class RawStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    def save_text(self, text: str, job_id: str) -> str:
        """Save raw text. Returns relative path from brain_root."""
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        path = self.config.raw_transcripts_dir / f"{ts}-{job_id}.txt"
        path.write_text(text, encoding="utf-8")
        return str(path.relative_to(self.config.brain_root))

    def save_audio(self, audio_bytes: bytes, filename: str, job_id: str) -> str:
        """Save raw audio. Returns relative path from brain_root."""
        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        suffix = Path(filename).suffix or ".wav"
        path = self.config.raw_audio_dir / f"{ts}-{job_id}{suffix}"
        path.write_bytes(audio_bytes)
        return str(path.relative_to(self.config.brain_root))

    def read_text(self, relative_path: str) -> str:
        return (self.config.brain_root / relative_path).read_text(encoding="utf-8")
```

- [ ] **Step 4: Write ingest/service.py**

```python
# simplebrain/ingest/service.py
from __future__ import annotations
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType
from simplebrain.store.raw import RawStore
from simplebrain.ingest.queue import FileQueue


class IngestService:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.raw = RawStore(config)
        self.queue = FileQueue(config)

    def add_text_note(self, text: str, user: str, device: str = "unknown") -> str:
        """Save text, enqueue job. Returns job_id immediately."""
        job = Job(type=JobType.TEXT, user=user, device=device)
        raw_path = self.raw.save_text(text, job.id)
        job.raw_path = raw_path
        self.queue.enqueue(job)
        return job.id

    def add_voice_note(self, audio_bytes: bytes, filename: str,
                       user: str, device: str = "unknown") -> str:
        """Save audio, enqueue job. Returns job_id immediately."""
        job = Job(type=JobType.VOICE, user=user, device=device)
        raw_path = self.raw.save_audio(audio_bytes, filename, job.id)
        job.raw_path = raw_path
        self.queue.enqueue(job)
        return job.id
```

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_ingest.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/store/ simplebrain/ingest/service.py tests/test_ingest.py
git commit -m "feat: raw store and ingest service"
```

---

## Task 5: Pipeline — Transcribe

**Files:**
- Create: `simplebrain/pipeline/__init__.py`
- Create: `simplebrain/pipeline/transcribe.py`
- Test: `tests/test_transcribe.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_transcribe.py
from unittest.mock import patch, MagicMock
from simplebrain.pipeline.transcribe import TranscribeStage
from simplebrain.models import Job, JobType


def test_transcribe_skipped_for_text(config):
    stage = TranscribeStage(config)
    job = Job(type=JobType.TEXT, user="alice",
              raw_path="_raw/transcripts/test.txt")
    result = stage.run(job)
    assert result.transcript_path == job.raw_path


def test_transcribe_voice_calls_whisper(config, tmp_path):
    # Write a fake audio file
    audio_path = config.raw_audio_dir / "test.wav"
    audio_path.write_bytes(b"fake")
    job = Job(type=JobType.VOICE, user="alice",
              raw_path=str(audio_path.relative_to(config.brain_root)))

    mock_segment = MagicMock()
    mock_segment.text = " Hello world"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], None)

    with patch("simplebrain.pipeline.transcribe.WhisperModel",
               return_value=mock_model):
        stage = TranscribeStage(config)
        result = stage.run(job)

    assert result.transcript_path is not None
    transcript_file = config.brain_root / result.transcript_path
    assert transcript_file.exists()
    assert "Hello world" in transcript_file.read_text()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_transcribe.py -v
```

Expected: FAIL with "cannot import name 'TranscribeStage'"

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/pipeline/__init__.py
```

```python
# simplebrain/pipeline/transcribe.py
from __future__ import annotations
from datetime import datetime
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType

_whisper_model = None  # module-level cache


def _get_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel("base", device="auto", compute_type="auto")
    return _whisper_model


class TranscribeStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> Job:
        if job.type == JobType.TEXT:
            # Text notes are already transcripts
            job.transcript_path = job.raw_path
            return job

        from faster_whisper import WhisperModel
        model = _get_model()
        audio_path = self.config.brain_root / job.raw_path
        segments, _ = model.transcribe(str(audio_path))
        text = " ".join(s.text for s in segments).strip()

        ts = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        out_path = self.config.raw_transcripts_dir / f"{ts}-{job.id}.txt"
        out_path.write_text(text, encoding="utf-8")
        job.transcript_path = str(out_path.relative_to(self.config.brain_root))
        return job
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_transcribe.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/pipeline/ tests/test_transcribe.py
git commit -m "feat: pipeline transcribe stage"
```

---

## Task 6: Pipeline — Chunk & Tag

**Files:**
- Create: `simplebrain/pipeline/chunk.py`
- Create: `simplebrain/pipeline/tag.py`
- Test: `tests/test_chunk.py`
- Test: `tests/test_tag.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_chunk.py
from unittest.mock import patch
from simplebrain.pipeline.chunk import ChunkStage
from simplebrain.models import Job, JobType, Chunk


def _mock_llm(content):
    """Returns a mock litellm completion with given content."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_chunk_single_small_note(config):
    # Write a small transcript
    transcript = config.raw_transcripts_dir / "test.txt"
    transcript.write_text("Today I learned about MCP servers.")
    job = Job(type=JobType.TEXT, user="alice", device="mac",
              raw_path="", transcript_path=str(transcript.relative_to(config.brain_root)))

    mock_response = _mock_llm('["Today I learned about MCP servers."]')
    with patch("simplebrain.pipeline.chunk.litellm.completion",
               return_value=mock_response):
        stage = ChunkStage(config)
        chunks = stage.run(job)

    assert len(chunks) == 1
    assert chunks[0].content == "Today I learned about MCP servers."
    assert chunks[0].user == "alice"
    assert chunks[0].device == "mac"


def test_chunk_large_note_creates_parent_links(config):
    transcript = config.raw_transcripts_dir / "large.txt"
    transcript.write_text("Note about MCP. Note about chunking.")
    job = Job(type=JobType.TEXT, user="alice", device="mac",
              raw_path="", transcript_path=str(transcript.relative_to(config.brain_root)))

    mock_response = _mock_llm('["Note about MCP.", "Note about chunking."]')
    with patch("simplebrain.pipeline.chunk.litellm.completion",
               return_value=mock_response):
        stage = ChunkStage(config)
        chunks = stage.run(job)

    assert len(chunks) == 2
    assert all(c.parent == chunks[0].parent for c in chunks)
```

```python
# tests/test_tag.py
from unittest.mock import patch
from simplebrain.pipeline.tag import TagStage
from simplebrain.models import Chunk


def _mock_llm(content):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_tag_extracts_tags(config):
    chunk = Chunk(content="MCP is a protocol for AI tools.",
                  source_raw="test.txt", user="alice")
    mock_response = _mock_llm('["#mcp", "#ai", "#protocol"]')
    with patch("simplebrain.pipeline.tag.litellm.completion",
               return_value=mock_response):
        stage = TagStage(config)
        result = stage.run(chunk)
    assert "#mcp" in result.tags
    assert "#ai" in result.tags


def test_tag_handles_malformed_llm_response(config):
    chunk = Chunk(content="Some content.", source_raw="test.txt", user="alice")
    mock_response = _mock_llm("not valid json")
    with patch("simplebrain.pipeline.tag.litellm.completion",
               return_value=mock_response):
        stage = TagStage(config)
        result = stage.run(chunk)
    assert result.tags == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_chunk.py tests/test_tag.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write chunk.py**

```python
# simplebrain/pipeline/chunk.py
from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.models import Job, Chunk

_CHUNK_PROMPT = """You are a knowledge chunker. Split the following note into semantic chunks.
Each chunk should represent one focused idea or topic.
Return a JSON array of strings. Each string is one chunk.
If the note is short and focused, return a single-element array.

Note:
{text}

Return only the JSON array, no explanation."""


class ChunkStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> list[Chunk]:
        text = (self.config.brain_root / job.transcript_path).read_text(encoding="utf-8")
        prompt = _CHUNK_PROMPT.format(text=text)

        response = litellm.completion(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            contents = json.loads(raw)
            if not isinstance(contents, list):
                contents = [text]
        except json.JSONDecodeError:
            contents = [text]

        # If multiple chunks, assign a shared parent id
        parent_id = None
        if len(contents) > 1:
            import uuid
            parent_id = str(uuid.uuid4())[:8]

        chunks = []
        for content in contents:
            chunk = Chunk(
                content=content.strip(),
                source_raw=job.transcript_path or "",
                user=job.user,
                device=job.device,
                parent=parent_id,
            )
            chunks.append(chunk)

        return chunks
```

- [ ] **Step 4: Write tag.py**

```python
# simplebrain/pipeline/tag.py
from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk

_TAG_PROMPT = """Extract tags from the following note chunk.
Tags should be short, lowercase, prefixed with #, and represent key topics/concepts.
Return a JSON array of tag strings.

Chunk:
{content}

Return only the JSON array, no explanation."""


class TagStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, chunk: Chunk) -> Chunk:
        prompt = _TAG_PROMPT.format(content=chunk.content)
        response = litellm.completion(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()
        try:
            tags = json.loads(raw)
            if isinstance(tags, list):
                chunk.tags = [t for t in tags if isinstance(t, str)]
            else:
                chunk.tags = []
        except json.JSONDecodeError:
            chunk.tags = []
        return chunk
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_chunk.py tests/test_tag.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/pipeline/chunk.py simplebrain/pipeline/tag.py \
        tests/test_chunk.py tests/test_tag.py
git commit -m "feat: pipeline chunk and tag stages"
```

---

## Task 7: Knowledge Store & Index Store

**Files:**
- Create: `simplebrain/store/knowledge.py`
- Create: `simplebrain/store/index.py`
- Test: `tests/test_index.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_index.py
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.store.index import IndexStore
from simplebrain.models import Chunk


def test_knowledge_store_write_read(config):
    ks = KnowledgeStore(config)
    chunk = Chunk(content="MCP is great.", source_raw="test.txt",
                  tags=["#mcp"], user="alice", device="mac")
    path = ks.write(chunk, folder="projects")
    assert path.exists()
    loaded = ks.read(chunk.id)
    assert loaded.content == "MCP is great."
    assert loaded.tags == ["#mcp"]


def test_knowledge_store_unfiled(config):
    ks = KnowledgeStore(config)
    chunk = Chunk(content="Orphan note.", source_raw="test.txt",
                  user="alice")
    path = ks.write_unfiled(chunk)
    assert "_unfiled" in str(path)


def test_index_store_update_and_lookup(config):
    ks = KnowledgeStore(config)
    idx = IndexStore(config)
    chunk = Chunk(content="Test.", source_raw="t.txt",
                  tags=["#mcp", "#ai"], user="alice")
    path = ks.write(chunk, folder="projects")
    idx.update(chunk, path)

    tags = idx.load_tags()
    assert "#mcp" in tags
    assert chunk.id in tags["#mcp"]


def test_index_store_cross_links(config):
    ks = KnowledgeStore(config)
    idx = IndexStore(config)

    c1 = Chunk(content="A.", source_raw="t.txt", tags=["#mcp"], user="alice")
    c2 = Chunk(content="B.", source_raw="t.txt", tags=["#mcp"], user="alice")
    p1 = ks.write(c1, folder="projects")
    p2 = ks.write(c2, folder="projects")
    idx.update(c1, p1)
    idx.update(c2, p2)
    idx.update_cross_links([c1, c2], ks)

    updated_c1 = ks.read(c1.id)
    assert c2.id in updated_c1.links
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_index.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write knowledge.py**

```python
# simplebrain/store/knowledge.py
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import frontmatter
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk


class KnowledgeStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    def write(self, chunk: Chunk, folder: str) -> Path:
        target_dir = self.config.knowledge_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{chunk.id}.md"
        self._write_chunk_file(chunk, path)
        chunk.file_path = str(path.relative_to(self.config.brain_root))
        return path

    def write_unfiled(self, chunk: Chunk) -> Path:
        return self.write(chunk, "_unfiled")

    def _write_chunk_file(self, chunk: Chunk, path: Path) -> None:
        post = frontmatter.Post(
            content=chunk.content,
            id=chunk.id,
            created=chunk.created.isoformat(),
            source_raw=chunk.source_raw,
            tags=chunk.tags,
            links=chunk.links,
            parent=chunk.parent,
            user=chunk.user,
            device=chunk.device,
        )
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def read(self, chunk_id: str) -> Chunk:
        matches = list(self.config.knowledge_dir.rglob(f"{chunk_id}.md"))
        if not matches:
            raise FileNotFoundError(f"Chunk {chunk_id} not found")
        post = frontmatter.load(str(matches[0]))
        return Chunk(
            id=post["id"],
            created=datetime.fromisoformat(post["created"]),
            source_raw=post["source_raw"],
            tags=post.get("tags", []),
            links=post.get("links", []),
            parent=post.get("parent"),
            user=post["user"],
            device=post.get("device", "unknown"),
            content=post.content,
            file_path=str(matches[0].relative_to(self.config.brain_root)),
        )

    def update_links(self, chunk_id: str, links: list[str]) -> None:
        matches = list(self.config.knowledge_dir.rglob(f"{chunk_id}.md"))
        if not matches:
            return
        post = frontmatter.load(str(matches[0]))
        post["links"] = links
        matches[0].write_text(frontmatter.dumps(post), encoding="utf-8")
```

- [ ] **Step 4: Write index.py**

```python
# simplebrain/store/index.py
from __future__ import annotations
import json
from pathlib import Path
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk


class IndexStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _tags_path(self) -> Path:
        return self.config.index_dir / "tags.json"

    @property
    def _topics_path(self) -> Path:
        return self.config.index_dir / "topics.json"

    def load_tags(self) -> dict[str, list[str]]:
        if not self._tags_path.exists():
            return {}
        return json.loads(self._tags_path.read_text())

    def load_topics(self) -> dict[str, list[str]]:
        if not self._topics_path.exists():
            return {}
        return json.loads(self._topics_path.read_text())

    def update(self, chunk: Chunk, file_path: Path) -> None:
        tags = self.load_tags()
        for tag in chunk.tags:
            tags.setdefault(tag, [])
            if chunk.id not in tags[tag]:
                tags[tag].append(chunk.id)
        self._tags_path.write_text(json.dumps(tags, indent=2))

        topics = self.load_topics()
        folder = file_path.parent.name
        topics.setdefault(folder, [])
        if chunk.id not in topics[folder]:
            topics[folder].append(chunk.id)
        self._topics_path.write_text(json.dumps(topics, indent=2))

    def update_cross_links(self, chunks: list[Chunk], knowledge_store) -> None:
        """Update links in chunk files for chunks that share tags."""
        tag_to_chunks: dict[str, list[str]] = {}
        for chunk in chunks:
            for tag in chunk.tags:
                tag_to_chunks.setdefault(tag, []).append(chunk.id)

        for chunk in chunks:
            linked = set()
            for tag in chunk.tags:
                for cid in tag_to_chunks.get(tag, []):
                    if cid != chunk.id:
                        linked.add(cid)
            if linked:
                knowledge_store.update_links(chunk.id, list(linked))

    def search(self, query: str, tags: list[str] | None = None) -> list[str]:
        """Return chunk IDs matching tags or query keywords."""
        tag_index = self.load_tags()
        matched: set[str] = set()

        search_tags = tags or []
        if not search_tags:
            query_lower = query.lower()
            search_tags = [t for t in tag_index if query_lower in t.lower()]

        for tag in search_tags:
            matched.update(tag_index.get(tag, []))

        return list(matched)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_index.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/store/ tests/test_index.py
git commit -m "feat: knowledge store and index store"
```

---

## Task 8: Pipeline — File Stage

**Files:**
- Create: `simplebrain/pipeline/file.py`
- Create: `simplebrain/brain/__init__.py`
- Create: `simplebrain/brain/grower.py`
- Test: `tests/test_file.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_file.py
import json
from unittest.mock import patch, MagicMock
from simplebrain.pipeline.file import FileStage
from simplebrain.models import Chunk, FolderProposalStatus


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_file_to_existing_folder(config):
    # Create existing folder structure
    (config.knowledge_dir / "projects").mkdir()
    structure = {"folders": ["projects", "research"]}
    (config.meta_dir / "structure.json").write_text(json.dumps(structure))

    chunk = Chunk(content="Working on MCP server.", source_raw="t.txt",
                  tags=["#mcp"], user="alice")
    mock_resp = _mock_llm('{"folder": "projects", "is_new": false}')

    with patch("simplebrain.pipeline.file.litellm.completion",
               return_value=mock_resp):
        stage = FileStage(config)
        filed_chunk, proposal = stage.run(chunk)

    assert filed_chunk.file_path is not None
    assert "projects" in filed_chunk.file_path
    assert proposal is None


def test_file_creates_proposal_for_new_folder(config):
    structure = {"folders": ["projects"]}
    (config.meta_dir / "structure.json").write_text(json.dumps(structure))

    chunk = Chunk(content="Cooking recipe for pasta.", source_raw="t.txt",
                  tags=["#cooking"], user="alice")
    mock_resp = _mock_llm('{"folder": "cooking", "is_new": true, "reasoning": "No food folder exists"}')

    with patch("simplebrain.pipeline.file.litellm.completion",
               return_value=mock_resp):
        stage = FileStage(config)
        filed_chunk, proposal = stage.run(chunk)

    assert proposal is not None
    assert proposal.proposed_folder == "cooking"
    assert proposal.status == FolderProposalStatus.PENDING
    assert filed_chunk.file_path is not None
    assert "_unfiled" in filed_chunk.file_path
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_file.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write brain/grower.py**

```python
# simplebrain/brain/__init__.py
```

```python
# simplebrain/brain/grower.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.models import FolderProposal, FolderProposalStatus


class SelfGrower:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _structure_path(self) -> Path:
        return self.config.meta_dir / "structure.json"

    def load_structure(self) -> dict:
        if not self._structure_path.exists():
            return {"folders": [], "pending_proposals": []}
        return json.loads(self._structure_path.read_text())

    def save_structure(self, structure: dict) -> None:
        self._structure_path.write_text(json.dumps(structure, indent=2))

    def get_folders(self) -> list[str]:
        return self.load_structure().get("folders", [])

    def create_proposal(self, folder: str, reasoning: str,
                        chunk_id: str) -> FolderProposal:
        proposal = FolderProposal(
            proposed_folder=folder,
            reasoning=reasoning,
            held_chunk_ids=[chunk_id],
        )
        structure = self.load_structure()
        structure.setdefault("pending_proposals", [])
        structure["pending_proposals"].append(json.loads(proposal.model_dump_json()))
        self.save_structure(structure)
        return proposal

    def confirm_proposal(self, proposal_id: str) -> Optional[FolderProposal]:
        structure = self.load_structure()
        for p in structure.get("pending_proposals", []):
            if p["id"] == proposal_id:
                p["status"] = FolderProposalStatus.CONFIRMED
                structure["folders"].append(p["proposed_folder"])
                self.save_structure(structure)
                return FolderProposal(**p)
        return None

    def reject_proposal(self, proposal_id: str) -> Optional[FolderProposal]:
        structure = self.load_structure()
        for p in structure.get("pending_proposals", []):
            if p["id"] == proposal_id:
                p["status"] = FolderProposalStatus.REJECTED
                self.save_structure(structure)
                return FolderProposal(**p)
        return None

    def list_pending(self) -> list[FolderProposal]:
        structure = self.load_structure()
        return [
            FolderProposal(**p)
            for p in structure.get("pending_proposals", [])
            if p["status"] == FolderProposalStatus.PENDING
        ]
```

- [ ] **Step 4: Write pipeline/file.py**

```python
# simplebrain/pipeline/file.py
from __future__ import annotations
import json
import litellm
from typing import Optional, Tuple
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk, FolderProposal
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.brain.grower import SelfGrower

_FILE_PROMPT = """You are a knowledge organiser. Given a chunk of text and its tags,
decide which folder it belongs in from the available folders.
If no folder fits well, propose a new folder name.

Available folders: {folders}
Tags: {tags}
Content: {content}

Return JSON: {{"folder": "folder_name", "is_new": true/false, "reasoning": "why"}}
Only return JSON, no explanation."""


class FileStage:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.knowledge = KnowledgeStore(config)
        self.grower = SelfGrower(config)

    def run(self, chunk: Chunk) -> Tuple[Chunk, Optional[FolderProposal]]:
        folders = self.grower.get_folders()
        prompt = _FILE_PROMPT.format(
            folders=folders or ["(none yet)"],
            tags=chunk.tags,
            content=chunk.content[:500],
        )
        response = litellm.completion(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: file to _unfiled
            self.knowledge.write_unfiled(chunk)
            return chunk, None

        folder = data.get("folder", "_unfiled")
        is_new = data.get("is_new", False)
        reasoning = data.get("reasoning", "")

        if is_new:
            proposal = self.grower.create_proposal(folder, reasoning, chunk.id)
            self.knowledge.write_unfiled(chunk)
            return chunk, proposal
        else:
            self.knowledge.write(chunk, folder)
            return chunk, None
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_file.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/pipeline/file.py simplebrain/brain/ tests/test_file.py
git commit -m "feat: pipeline file stage and self-grower"
```

---

## Task 9: Background Worker

**Files:**
- Create: `simplebrain/pipeline/worker.py`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_worker.py
import json
from unittest.mock import patch, MagicMock
from simplebrain.pipeline.worker import BackgroundWorker
from simplebrain.ingest.service import IngestService
from simplebrain.models import JobStatus, JobType


def _mock_llm_chunk(text):
    mock = MagicMock()
    mock.choices[0].message.content = json.dumps([text])
    return mock


def _mock_llm_tag():
    mock = MagicMock()
    mock.choices[0].message.content = '["#test"]'
    return mock


def _mock_llm_file():
    mock = MagicMock()
    mock.choices[0].message.content = '{"folder": "general", "is_new": false}'
    return mock


def test_worker_processes_text_job(config):
    (config.knowledge_dir / "general").mkdir()
    (config.meta_dir / "structure.json").write_text(
        json.dumps({"folders": ["general"]})
    )

    svc = IngestService(config)
    job_id = svc.add_text_note("Hello MCP world.", user="alice", device="mac")

    def mock_completion(model, messages, **kwargs):
        content = messages[0]["content"]
        if "chunker" in content:
            return _mock_llm_chunk("Hello MCP world.")
        elif "Extract tags" in content:
            return _mock_llm_tag()
        else:
            return _mock_llm_file()

    with patch("simplebrain.pipeline.chunk.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.tag.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.file.litellm.completion", side_effect=mock_completion):
        worker = BackgroundWorker(config)
        worker.process_one()

    # Queue should be empty
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    assert q.dequeue() is None

    # A chunk file should exist
    chunks = list(config.knowledge_dir.rglob("*.md"))
    non_unfiled = [c for c in chunks if "_unfiled" not in str(c)]
    assert len(non_unfiled) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py -v
```

Expected: FAIL with "cannot import name 'BackgroundWorker'"

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/pipeline/worker.py
from __future__ import annotations
import logging
from simplebrain.config import BrainConfig
from simplebrain.ingest.queue import FileQueue
from simplebrain.models import JobType, JobStatus
from simplebrain.pipeline.transcribe import TranscribeStage
from simplebrain.pipeline.chunk import ChunkStage
from simplebrain.pipeline.tag import TagStage
from simplebrain.pipeline.file import FileStage
from simplebrain.store.index import IndexStore
from simplebrain.store.knowledge import KnowledgeStore

logger = logging.getLogger(__name__)


class BackgroundWorker:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.queue = FileQueue(config)
        self.transcribe = TranscribeStage(config)
        self.chunk = ChunkStage(config)
        self.tag = TagStage(config)
        self.file = FileStage(config)
        self.index = IndexStore(config)
        self.knowledge = KnowledgeStore(config)

    def process_one(self) -> bool:
        """Process one job. Returns True if a job was processed."""
        job = self.queue.dequeue()
        if job is None:
            return False
        try:
            # Stage 1: Transcribe
            job = self.transcribe.run(job)

            # Stage 2: Chunk
            chunks = self.chunk.run(job)

            # Stage 3: Tag
            chunks = [self.tag.run(c) for c in chunks]

            # Stage 4: File
            filed = []
            for chunk in chunks:
                filed_chunk, proposal = self.file.run(chunk)
                filed.append(filed_chunk)
                if proposal:
                    logger.info(f"New folder proposal: {proposal.proposed_folder}")

            # Stage 5: Index
            for chunk in filed:
                if chunk.file_path:
                    path = self.config.brain_root / chunk.file_path
                    self.index.update(chunk, path)
            self.index.update_cross_links(filed, self.knowledge)

            self.queue.complete(job)
            logger.info(f"Job {job.id} complete — {len(filed)} chunks filed.")
            return True

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            self.queue.mark_failed(job, error=str(e))
            return False

    def run_forever(self, poll_interval: float = 2.0) -> None:
        """Poll queue continuously. Run as a thread or process."""
        import time
        logger.info("Worker started, polling queue...")
        while True:
            if not self.process_one():
                time.sleep(poll_interval)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_worker.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/pipeline/worker.py tests/test_worker.py
git commit -m "feat: background pipeline worker"
```

---

## Task 10: Self-Healer

**Files:**
- Create: `simplebrain/brain/healer.py`
- Test: `tests/test_healer.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_healer.py
import json
from unittest.mock import patch, MagicMock
from simplebrain.brain.healer import SelfHealer
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.models import Chunk, ConflictType, ConflictStatus, Resolution


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_healer_detects_factual_conflict(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="MCP uses HTTP transport.", source_raw="t.txt",
               tags=["#mcp"], user="alice")
    c2 = Chunk(content="MCP does not use HTTP transport.", source_raw="t.txt",
               tags=["#mcp"], user="alice")
    ks.write(c1, "projects")
    ks.write(c2, "projects")

    conflict_response = json.dumps([{
        "type": "factual_conflict",
        "chunks_involved": [c1.id, c2.id],
        "summary": "Contradiction about MCP transport"
    }])
    mock_resp = _mock_llm(conflict_response)

    with patch("simplebrain.brain.healer.litellm.completion",
               return_value=mock_resp):
        healer = SelfHealer(config)
        conflicts = healer.scan()

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.FACTUAL


def test_healer_resolve_and_log(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="Version A.", source_raw="t.txt",
               tags=["#test"], user="alice")
    c2 = Chunk(content="Version B.", source_raw="t.txt",
               tags=["#test"], user="alice")
    ks.write(c1, "projects")
    ks.write(c2, "projects")

    healer = SelfHealer(config)
    from simplebrain.models import Conflict, ConflictType
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=[c1.id, c2.id],
        summary="Test conflict",
        snapshot={"chunks": {c1.id: c1.content, c2.id: c2.content}}
    )
    healer._save_pending(conflict)
    healer.resolve(conflict.id, Resolution.KEEP_NEWER, resolved_by="alice")

    log = healer.load_resolution_log()
    assert any(e["id"] == conflict.id for e in log)


def test_healer_revert(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="Original content.", source_raw="t.txt",
               tags=["#test"], user="alice")
    ks.write(c1, "projects")

    healer = SelfHealer(config)
    from simplebrain.models import Conflict, ConflictType
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=[c1.id],
        summary="Test",
        snapshot={"chunks": {c1.id: "Original content."}}
    )
    healer._save_pending(conflict)
    healer.resolve(conflict.id, Resolution.KEEP_NEWER, resolved_by="alice")
    healer.revert(conflict.id, knowledge_store=ks)

    log = healer.load_resolution_log()
    entry = next(e for e in log if e["id"] == conflict.id)
    assert entry["status"] == ConflictStatus.REVERTED
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_healer.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/brain/healer.py
from __future__ import annotations
import json
import litellm
from datetime import datetime
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.models import (Conflict, ConflictType, ConflictStatus,
                                 Resolution)
from simplebrain.store.knowledge import KnowledgeStore

_HEAL_PROMPT = """You are a knowledge consistency checker. Review the following chunks
from the same knowledge base folder and identify:
1. Factual conflicts (contradicting statements)
2. Structural issues (duplicates, orphans)
3. Pivots (topic drift)

Chunks:
{chunks}

Return a JSON array of conflicts found. Each conflict:
{{"type": "factual_conflict|structural_issue|pivot",
  "chunks_involved": ["id1", "id2"],
  "summary": "brief description"}}

Return empty array [] if no conflicts found. Return only JSON."""


class SelfHealer:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _log_path(self) -> Path:
        return self.config.conflicts_dir / "resolution-log.json"

    @property
    def _pending_dir(self) -> Path:
        return self.config.conflicts_dir / "pending"

    def load_resolution_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        return json.loads(self._log_path.read_text())

    def _save_log(self, log: list[dict]) -> None:
        self._log_path.write_text(json.dumps(log, indent=2))

    def _save_pending(self, conflict: Conflict) -> None:
        path = self._pending_dir / f"{conflict.id}.json"
        path.write_text(conflict.model_dump_json(indent=2))

    def scan(self) -> list[Conflict]:
        """Scan all knowledge folders for conflicts. Returns new conflicts."""
        ks = KnowledgeStore(self.config)
        all_conflicts: list[Conflict] = []

        for folder in self.config.knowledge_dir.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            chunk_files = list(folder.glob("*.md"))
            if len(chunk_files) < 2:
                continue

            chunks_text = []
            for cf in chunk_files[:20]:  # limit context size
                try:
                    import frontmatter
                    post = frontmatter.load(str(cf))
                    chunks_text.append(f"ID:{post['id']} — {post.content[:200]}")
                except Exception:
                    continue

            prompt = _HEAL_PROMPT.format(chunks="\n".join(chunks_text))
            response = litellm.completion(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            try:
                items = json.loads(raw)
                for item in items:
                    conflict = Conflict(
                        type=ConflictType(item["type"]),
                        chunks_involved=item["chunks_involved"],
                        summary=item["summary"],
                    )
                    self._save_pending(conflict)
                    all_conflicts.append(conflict)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return all_conflicts

    def resolve(self, conflict_id: str, resolution: Resolution,
                resolved_by: str) -> None:
        pending_path = self._pending_dir / f"{conflict_id}.json"
        if not pending_path.exists():
            raise FileNotFoundError(f"Conflict {conflict_id} not found")

        conflict = Conflict(**json.loads(pending_path.read_text()))
        conflict.resolution = resolution
        conflict.resolved_by = resolved_by
        conflict.resolved_at = datetime.utcnow()
        conflict.status = ConflictStatus.RESOLVED

        log = self.load_resolution_log()
        log.append(json.loads(conflict.model_dump_json()))
        self._save_log(log)
        pending_path.unlink()

    def revert(self, conflict_id: str,
               knowledge_store: Optional[KnowledgeStore] = None) -> None:
        log = self.load_resolution_log()
        entry = next((e for e in log if e["id"] == conflict_id), None)
        if not entry:
            raise FileNotFoundError(f"Resolution {conflict_id} not in log")

        ks = knowledge_store or KnowledgeStore(self.config)
        snapshot = entry.get("snapshot", {}).get("chunks", {})
        for chunk_id, original_content in snapshot.items():
            try:
                chunk = ks.read(chunk_id)
                chunk.content = original_content
                if chunk.file_path:
                    path = self.config.brain_root / chunk.file_path
                    import frontmatter
                    post = frontmatter.load(str(path))
                    post.content = original_content
                    path.write_text(frontmatter.dumps(post), encoding="utf-8")
            except FileNotFoundError:
                continue

        entry["status"] = ConflictStatus.REVERTED
        self._save_log(log)

    def list_pending(self) -> list[Conflict]:
        return [
            Conflict(**json.loads(p.read_text()))
            for p in self._pending_dir.glob("*.json")
        ]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_healer.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/brain/healer.py tests/test_healer.py
git commit -m "feat: self-healer with conflict detection, resolution, and revert"
```

---

## Task 11: MCP Server

**Files:**
- Create: `simplebrain/mcp/__init__.py`
- Create: `simplebrain/mcp/server.py`
- Test: `tests/test_mcp.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_mcp.py
import json
import pytest
from simplebrain.mcp.server import create_mcp_server
from simplebrain.config import BrainConfig


def test_mcp_server_has_expected_tools(config):
    server = create_mcp_server(config)
    tool_names = [t.name for t in server.list_tools()]
    expected = [
        "add_text_note", "add_voice_note", "job_status",
        "search", "get_chunk", "list_topics", "list_tags",
        "list_pending_folder_proposals", "confirm_folder_proposal",
        "reject_folder_proposal", "list_conflicts", "resolve_conflict",
        "revert_resolution", "run_healer", "get_brain_status",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_mcp_add_text_note_returns_job_id(config):
    server = create_mcp_server(config)
    result = server.call_tool("add_text_note", {
        "text": "Hello brain", "user": "alice", "device": "mac"
    })
    data = json.loads(result[0].text)
    assert "job_id" in data
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_mcp.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/mcp/__init__.py
```

```python
# simplebrain/mcp/server.py
from __future__ import annotations
import json
from simplebrain.config import BrainConfig
from simplebrain.ingest.service import IngestService
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.store.index import IndexStore
from simplebrain.brain.grower import SelfGrower
from simplebrain.brain.healer import SelfHealer
from simplebrain.models import Resolution
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.types as types


def create_mcp_server(config: BrainConfig) -> Server:
    server = Server("simplebrain")
    ingest = IngestService(config)
    knowledge = KnowledgeStore(config)
    index = IndexStore(config)
    grower = SelfGrower(config)
    healer = SelfHealer(config)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name="add_text_note",
                 description="Add a text note to the brain",
                 inputSchema={"type": "object",
                              "properties": {"text": {"type": "string"},
                                             "user": {"type": "string"},
                                             "device": {"type": "string"}},
                              "required": ["text", "user"]}),
            Tool(name="add_voice_note",
                 description="Add a voice note (base64 audio) to the brain",
                 inputSchema={"type": "object",
                              "properties": {"audio_b64": {"type": "string"},
                                             "filename": {"type": "string"},
                                             "user": {"type": "string"},
                                             "device": {"type": "string"}},
                              "required": ["audio_b64", "filename", "user"]}),
            Tool(name="job_status",
                 description="Check the status of an ingestion job",
                 inputSchema={"type": "object",
                              "properties": {"job_id": {"type": "string"}},
                              "required": ["job_id"]}),
            Tool(name="search",
                 description="Search the knowledge base",
                 inputSchema={"type": "object",
                              "properties": {"query": {"type": "string"},
                                             "tags": {"type": "array",
                                                      "items": {"type": "string"}}},
                              "required": ["query"]}),
            Tool(name="get_chunk",
                 description="Get a specific chunk by ID",
                 inputSchema={"type": "object",
                              "properties": {"chunk_id": {"type": "string"}},
                              "required": ["chunk_id"]}),
            Tool(name="list_topics",
                 description="List all topics with chunk counts",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="list_tags",
                 description="List all tags with usage counts",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="list_pending_folder_proposals",
                 description="List pending folder proposals",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="confirm_folder_proposal",
                 description="Confirm a folder proposal",
                 inputSchema={"type": "object",
                              "properties": {"proposal_id": {"type": "string"}},
                              "required": ["proposal_id"]}),
            Tool(name="reject_folder_proposal",
                 description="Reject a folder proposal",
                 inputSchema={"type": "object",
                              "properties": {"proposal_id": {"type": "string"},
                                             "target_folder": {"type": "string"}},
                              "required": ["proposal_id", "target_folder"]}),
            Tool(name="list_conflicts",
                 description="List pending conflicts",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="resolve_conflict",
                 description="Resolve a conflict",
                 inputSchema={"type": "object",
                              "properties": {"conflict_id": {"type": "string"},
                                             "resolution": {"type": "string"},
                                             "resolved_by": {"type": "string"}},
                              "required": ["conflict_id", "resolution", "resolved_by"]}),
            Tool(name="revert_resolution",
                 description="Revert a previously resolved conflict",
                 inputSchema={"type": "object",
                              "properties": {"conflict_id": {"type": "string"}},
                              "required": ["conflict_id"]}),
            Tool(name="run_healer",
                 description="Manually trigger a healing scan",
                 inputSchema={"type": "object", "properties": {}}),
            Tool(name="get_brain_status",
                 description="Get brain status summary",
                 inputSchema={"type": "object", "properties": {}}),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        def ok(data: dict) -> list[TextContent]:
            return [TextContent(type="text", text=json.dumps(data))]

        if name == "add_text_note":
            job_id = ingest.add_text_note(
                arguments["text"], arguments["user"],
                arguments.get("device", "unknown"))
            return ok({"job_id": job_id})

        elif name == "add_voice_note":
            import base64
            audio = base64.b64decode(arguments["audio_b64"])
            job_id = ingest.add_voice_note(
                audio, arguments["filename"], arguments["user"],
                arguments.get("device", "unknown"))
            return ok({"job_id": job_id})

        elif name == "job_status":
            from simplebrain.ingest.queue import FileQueue
            q = FileQueue(config)
            pending = [j for j in [q.dequeue()] if j and j.id == arguments["job_id"]]
            status = pending[0].status if pending else "complete_or_not_found"
            return ok({"job_id": arguments["job_id"], "status": str(status)})

        elif name == "search":
            ids = index.search(arguments["query"],
                               arguments.get("tags", []))
            chunks = []
            for cid in ids[:10]:
                try:
                    c = knowledge.read(cid)
                    chunks.append({"id": c.id, "content": c.content[:200],
                                   "tags": c.tags, "file_path": c.file_path})
                except FileNotFoundError:
                    continue
            return ok({"results": chunks})

        elif name == "get_chunk":
            c = knowledge.read(arguments["chunk_id"])
            return ok({"id": c.id, "content": c.content, "tags": c.tags,
                       "links": c.links, "user": c.user, "device": c.device,
                       "created": c.created.isoformat()})

        elif name == "list_topics":
            topics = index.load_topics()
            return ok({"topics": {k: len(v) for k, v in topics.items()}})

        elif name == "list_tags":
            tags = index.load_tags()
            return ok({"tags": {k: len(v) for k, v in tags.items()}})

        elif name == "list_pending_folder_proposals":
            proposals = grower.list_pending()
            return ok({"proposals": [json.loads(p.model_dump_json())
                                     for p in proposals]})

        elif name == "confirm_folder_proposal":
            p = grower.confirm_proposal(arguments["proposal_id"])
            return ok({"confirmed": p is not None,
                       "folder": p.proposed_folder if p else None})

        elif name == "reject_folder_proposal":
            p = grower.reject_proposal(arguments["proposal_id"])
            return ok({"rejected": p is not None})

        elif name == "list_conflicts":
            conflicts = healer.list_pending()
            return ok({"conflicts": [json.loads(c.model_dump_json())
                                     for c in conflicts]})

        elif name == "resolve_conflict":
            healer.resolve(
                arguments["conflict_id"],
                Resolution(arguments["resolution"]),
                arguments["resolved_by"])
            return ok({"resolved": True})

        elif name == "revert_resolution":
            healer.revert(arguments["conflict_id"])
            return ok({"reverted": True})

        elif name == "run_healer":
            conflicts = healer.scan()
            return ok({"conflicts_found": len(conflicts)})

        elif name == "get_brain_status":
            from simplebrain.ingest.queue import FileQueue
            q = FileQueue(config)
            queue_files = list(config.queue_dir.glob("*.json"))
            return ok({
                "queue_depth": len(queue_files),
                "pending_conflicts": len(healer.list_pending()),
                "pending_proposals": len(grower.list_pending()),
            })

        return ok({"error": f"Unknown tool: {name}"})

    return server
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_mcp.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/mcp/ tests/test_mcp.py
git commit -m "feat: MCP server with all tools"
```

---

## Task 12: FastAPI Web UI & REST API

**Files:**
- Create: `simplebrain/api/__init__.py`
- Create: `simplebrain/api/routes.py`
- Create: `simplebrain/api/ui.py`
- Create: `ui/index.html`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_api.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_api.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write routes.py**

```python
# simplebrain/api/__init__.py
```

```python
# simplebrain/api/routes.py
from __future__ import annotations
import base64
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
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


class ResolveConflictRequest(BaseModel):
    resolution: str
    resolved_by: str


class RejectProposalRequest(BaseModel):
    target_folder: str


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
        from simplebrain.ingest.queue import FileQueue
        q = FileQueue(config)
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
                chunks.append({"id": c.id, "content": c.content[:300],
                               "tags": c.tags, "file_path": c.file_path})
            except FileNotFoundError:
                continue
        return {"results": chunks}

    @app.get("/chunks/{chunk_id}")
    def get_chunk(chunk_id: str):
        c = knowledge.read(chunk_id)
        return {"id": c.id, "content": c.content, "tags": c.tags,
                "links": c.links, "user": c.user, "device": c.device}

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
```

- [ ] **Step 4: Write the mobile UI**

```html
<!-- ui/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>SimpleBrain</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, sans-serif; background: #0f0f0f; color: #f0f0f0; padding: 1rem; }
    h1 { font-size: 1.4rem; margin-bottom: 1rem; color: #a78bfa; }
    .card { background: #1a1a1a; border-radius: 12px; padding: 1rem; margin-bottom: 1rem; }
    textarea { width: 100%; background: #2a2a2a; color: #f0f0f0; border: 1px solid #333;
               border-radius: 8px; padding: 0.75rem; font-size: 1rem; min-height: 100px; resize: vertical; }
    button { width: 100%; padding: 0.75rem; border-radius: 8px; border: none;
             font-size: 1rem; font-weight: 600; cursor: pointer; margin-top: 0.5rem; }
    .btn-primary { background: #7c3aed; color: white; }
    .btn-record { background: #dc2626; color: white; }
    .btn-record.recording { background: #991b1b; animation: pulse 1s infinite; }
    .btn-stop { background: #374151; color: white; }
    @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.6; } }
    .status { font-size: 0.85rem; color: #9ca3af; margin-top: 0.5rem; text-align: center; }
    .tag { display: inline-block; background: #2e1065; color: #a78bfa;
           border-radius: 4px; padding: 2px 8px; font-size: 0.75rem; margin: 2px; }
    input[type=text] { width: 100%; background: #2a2a2a; color: #f0f0f0;
                       border: 1px solid #333; border-radius: 8px; padding: 0.6rem;
                       font-size: 1rem; margin-bottom: 0.5rem; }
  </style>
</head>
<body>
  <h1>🧠 SimpleBrain</h1>

  <div class="card">
    <h2 style="font-size:1rem;margin-bottom:.75rem;">🎙 Voice Note</h2>
    <button class="btn-record" id="recordBtn" onclick="toggleRecording()">Start Recording</button>
    <p class="status" id="recordStatus">Tap to record</p>
  </div>

  <div class="card">
    <h2 style="font-size:1rem;margin-bottom:.75rem;">✏️ Text Note</h2>
    <textarea id="noteText" placeholder="Type your note here..."></textarea>
    <button class="btn-primary" onclick="submitText()">Add Note</button>
    <p class="status" id="textStatus"></p>
  </div>

  <div class="card">
    <h2 style="font-size:1rem;margin-bottom:.75rem;">🔍 Search</h2>
    <input type="text" id="searchQuery" placeholder="Search topics or tags..." />
    <button class="btn-primary" onclick="doSearch()">Search</button>
    <div id="searchResults"></div>
  </div>

  <div class="card" id="statusCard">
    <h2 style="font-size:1rem;margin-bottom:.75rem;">📊 Brain Status</h2>
    <p class="status" id="brainStatus">Loading...</p>
  </div>

  <script>
    const USER = "mobile_user";
    let mediaRecorder, audioChunks = [], isRecording = false;

    async function toggleRecording() {
      if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];
        mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
        mediaRecorder.onstop = sendAudio;
        mediaRecorder.start();
        isRecording = true;
        document.getElementById("recordBtn").textContent = "⏹ Stop Recording";
        document.getElementById("recordBtn").classList.add("recording");
        document.getElementById("recordStatus").textContent = "Recording...";
      } else {
        mediaRecorder.stop();
        isRecording = false;
        document.getElementById("recordBtn").textContent = "Start Recording";
        document.getElementById("recordBtn").classList.remove("recording");
        document.getElementById("recordStatus").textContent = "Processing...";
      }
    }

    async function sendAudio() {
      const blob = new Blob(audioChunks, { type: "audio/webm" });
      const reader = new FileReader();
      reader.onloadend = async () => {
        const b64 = reader.result.split(",")[1];
        const resp = await fetch("/notes/voice", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ audio_b64: b64, filename: "note.webm",
                                  user: USER, device: "iphone" })
        });
        const data = await resp.json();
        document.getElementById("recordStatus").textContent =
          resp.ok ? `✅ Queued (${data.job_id})` : "❌ Error";
      };
      reader.readAsDataURL(blob);
    }

    async function submitText() {
      const text = document.getElementById("noteText").value.trim();
      if (!text) return;
      const resp = await fetch("/notes/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, user: USER, device: "iphone" })
      });
      const data = await resp.json();
      document.getElementById("textStatus").textContent =
        resp.ok ? `✅ Queued (${data.job_id})` : "❌ Error";
      if (resp.ok) document.getElementById("noteText").value = "";
    }

    async function doSearch() {
      const q = document.getElementById("searchQuery").value.trim();
      if (!q) return;
      const resp = await fetch(`/search?query=${encodeURIComponent(q)}`);
      const data = await resp.json();
      const el = document.getElementById("searchResults");
      if (!data.results.length) { el.innerHTML = "<p class='status'>No results</p>"; return; }
      el.innerHTML = data.results.map(r => `
        <div style="border-top:1px solid #333;margin-top:.5rem;padding-top:.5rem;">
          <p style="font-size:.85rem;">${r.content}</p>
          <div>${(r.tags||[]).map(t=>`<span class="tag">${t}</span>`).join("")}</div>
        </div>`).join("");
    }

    async function loadStatus() {
      const resp = await fetch("/status");
      const d = await resp.json();
      document.getElementById("brainStatus").textContent =
        `Queue: ${d.queue_depth} | Conflicts: ${d.pending_conflicts} | Proposals: ${d.pending_proposals}`;
    }

    loadStatus();
    setInterval(loadStatus, 10000);
  </script>
</body>
</html>
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_api.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add simplebrain/api/ ui/ tests/test_api.py
git commit -m "feat: FastAPI REST API and mobile web UI"
```

---

## Task 13: Setup Wizard

**Files:**
- Create: `simplebrain/setup/wizard.py`
- Create: `simplebrain/setup/__init__.py`
- Test: `tests/test_setup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_setup.py
import json
from unittest.mock import patch, MagicMock
from simplebrain.setup.wizard import SetupWizard
from simplebrain.config import BrainConfig


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_setup_saves_config(config):
    answers = {
        "purpose": "My software projects and research notes",
        "users": ["alice"],
        "topics": ["projects", "research", "personal"],
        "healer_schedule": "daily",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    }
    mock_resp = _mock_llm(json.dumps(["projects", "research", "personal", "archive"]))

    with patch("simplebrain.setup.wizard.litellm.completion",
               return_value=mock_resp):
        wizard = SetupWizard(config)
        wizard.run(answers)

    setup_file = config.meta_dir / "setup.json"
    assert setup_file.exists()
    data = json.loads(setup_file.read_text())
    assert data["users"] == ["alice"]


def test_setup_creates_folders(config):
    answers = {
        "purpose": "Personal notes",
        "users": ["alice"],
        "topics": ["journal", "work"],
        "healer_schedule": "weekly",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    }
    mock_resp = _mock_llm(json.dumps(["journal", "work", "archive"]))

    with patch("simplebrain.setup.wizard.litellm.completion",
               return_value=mock_resp):
        wizard = SetupWizard(config)
        folders = wizard.run(answers)

    for folder in folders:
        assert (config.knowledge_dir / folder).exists()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_setup.py -v
```

Expected: FAIL with import errors

- [ ] **Step 3: Write minimal implementation**

```python
# simplebrain/setup/__init__.py
```

```python
# simplebrain/setup/wizard.py
from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.brain.grower import SelfGrower

_STRUCTURE_PROMPT = """You are setting up a knowledge base. Based on the user's description,
generate a list of top-level folder names for organising their notes.
Keep it to 4-8 folders. Use lowercase, hyphen-separated names.
Always include an "archive" folder.

Purpose: {purpose}
Suggested topics: {topics}

Return a JSON array of folder name strings only."""


class SetupWizard:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, answers: dict) -> list[str]:
        """Run setup with provided answers. Returns list of created folders."""
        prompt = _STRUCTURE_PROMPT.format(
            purpose=answers["purpose"],
            topics=", ".join(answers.get("topics", [])),
        )
        response = litellm.completion(
            model=answers.get("llm_model", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            folders = json.loads(raw)
            if not isinstance(folders, list):
                folders = answers.get("topics", []) + ["archive"]
        except json.JSONDecodeError:
            folders = answers.get("topics", []) + ["archive"]

        # Create folders
        for folder in folders:
            (self.config.knowledge_dir / folder).mkdir(parents=True, exist_ok=True)

        # Save structure
        grower = SelfGrower(self.config)
        structure = grower.load_structure()
        structure["folders"] = folders
        grower.save_structure(structure)

        # Save setup config
        setup_data = {**answers, "folders": folders}
        (self.config.meta_dir / "setup.json").write_text(
            json.dumps(setup_data, indent=2))

        return folders
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_setup.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add simplebrain/setup/ tests/test_setup.py
git commit -m "feat: setup wizard"
```

---

## Task 14: Entry Point & README

**Files:**
- Create: `simplebrain/__main__.py`
- Create: `README.md`

- [ ] **Step 1: Write the entry point**

```python
# simplebrain/__main__.py
from __future__ import annotations
import argparse
import threading
import uvicorn
from simplebrain.config import BrainConfig


def main():
    parser = argparse.ArgumentParser(description="SimpleBrain — self-organising second brain")
    parser.add_argument("--setup", action="store_true", help="Run setup wizard")
    parser.add_argument("--host", default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--mcp", action="store_true", help="Run MCP server (stdio)")
    args = parser.parse_args()

    config = BrainConfig.from_env()

    if args.setup:
        _run_setup(config)
        return

    if args.mcp:
        _run_mcp(config)
        return

    _run_all(config, args.host, args.port)


def _run_setup(config: BrainConfig):
    from simplebrain.setup.wizard import SetupWizard
    print("🧠 SimpleBrain Setup\n")
    purpose = input("What is this knowledge base about?\n> ")
    users = input("Who will use it? (comma-separated usernames)\n> ").split(",")
    topics = input("What are the main topics? (comma-separated)\n> ").split(",")
    schedule = input("Healer schedule? (daily/weekly/manual)\n> ") or "daily"
    provider = input("LLM provider? (openai/anthropic/ollama)\n> ") or "openai"
    model = input("LLM model? (e.g. gpt-4o-mini)\n> ") or "gpt-4o-mini"

    answers = {
        "purpose": purpose.strip(),
        "users": [u.strip() for u in users],
        "topics": [t.strip() for t in topics],
        "healer_schedule": schedule.strip(),
        "llm_provider": provider.strip(),
        "llm_model": model.strip(),
    }
    wizard = SetupWizard(config)
    folders = wizard.run(answers)
    print(f"\n✅ Setup complete! Created folders: {', '.join(folders)}")
    print(f"Run: python -m simplebrain")


def _run_mcp(config: BrainConfig):
    import asyncio
    from mcp.server.stdio import stdio_server
    from simplebrain.mcp.server import create_mcp_server
    server = create_mcp_server(config)
    asyncio.run(stdio_server(server))


def _run_all(config: BrainConfig, host: str, port: int):
    from simplebrain.pipeline.worker import BackgroundWorker
    from simplebrain.api.routes import create_app
    import socket

    # Start background worker in a thread
    worker = BackgroundWorker(config)
    worker_thread = threading.Thread(target=worker.run_forever, daemon=True)
    worker_thread.start()

    # Get local IP for iPhone access
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = host

    print(f"🧠 SimpleBrain running")
    print(f"   API:    http://{ip}:{port}")
    print(f"   UI:     http://{ip}:{port}/ui/index.html")
    print(f"   Docs:   http://{ip}:{port}/docs")

    app = create_app(config)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write README.md**

```markdown
# 🧠 SimpleBrain

A self-organising, self-growing, and self-healing second brain.
Drop voice or text notes — the brain transcribes, chunks, tags, and files them automatically.
Exposed as an MCP server for AI tool and CLI consumption.

## Quickstart

```bash
pip install -e .
cp .env.example .env  # add your API keys

# First-time setup
python -m simplebrain --setup

# Run the brain (API + worker)
python -m simplebrain

# Run as MCP server (for Claude Desktop / CLI)
python -m simplebrain --mcp
```

## iPhone Access

Open `http://<your-mac-ip>:8000` in Safari on your iPhone.
Bookmark it as a home screen shortcut for instant access.

## MCP Tools

| Tool | Description |
|---|---|
| `add_text_note` | Add a text note |
| `add_voice_note` | Add a voice note (base64 audio) |
| `search` | Search by query or tags |
| `list_topics` | List all topics |
| `list_tags` | List all tags |
| `list_conflicts` | List pending conflicts |
| `resolve_conflict` | Resolve a conflict |
| `run_healer` | Trigger a healing scan |
| `get_brain_status` | Get system status |

## Environment Variables

See `.env.example` for all configuration options.
```

- [ ] **Step 3: Run the full test suite**

```bash
pytest tests/ -v --tb=short
```

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add simplebrain/__main__.py README.md
git commit -m "feat: entry point and README — SimpleBrain v0.1.0 complete"
```

---

## Full Test Run

- [ ] **Run all tests**

```bash
pytest tests/ -v
```

Expected: All tests pass with no errors.
