from __future__ import annotations
from datetime import datetime, timezone
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
    DOCUMENT = "document"


class Job(BaseModel):
    id: str = Field(default_factory=_new_id)
    type: JobType
    user: str
    device: str = "unknown"
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: JobStatus = JobStatus.PENDING
    raw_path: Optional[str] = None       # path to audio or transcript in _raw/
    transcript_path: Optional[str] = None
    error: Optional[str] = None


class Chunk(BaseModel):
    id: str = Field(default_factory=_new_id)
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_raw: str
    title: Optional[str] = None          # short human-readable title, used as filename slug
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
    detected: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
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
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
