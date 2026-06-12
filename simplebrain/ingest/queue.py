from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger
from simplebrain.models import Job, JobStatus

log = get_logger(__name__)


class FileQueue:
    def __init__(self, config: BrainConfig):
        self.config = config

    def _job_path(self, job: Job) -> Path:
        ns = time.time_ns()
        return self.config.queue_dir / f"{ns:020d}-{job.id}.json"

    def enqueue(self, job: Job) -> None:
        path = self._job_path(job)
        path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        log.debug("[job=%s] Written to queue: %s", job.id, path.name)

    def dequeue(self) -> Optional[Job]:
        files = sorted(self.config.queue_dir.glob("*.json"))
        if not files:
            return None
        path = files[0]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            job = Job(**data)
            log.debug("[job=%s] Dequeued from: %s", job.id, path.name)
            return job
        except Exception as exc:
            log.error("Failed to read queue file %s: %s — moving to failed/", path.name, exc)
            dest = self.config.queue_dir / "failed" / path.name
            path.rename(dest)
            return None

    def _find_job_file(self, job: Job) -> Optional[Path]:
        matches = list(self.config.queue_dir.glob(f"*-{job.id}.json"))
        if not matches:
            log.warning("[job=%s] Could not find queue file to update status", job.id)
        return matches[0] if matches else None

    def mark_failed(self, job: Job, error: str) -> None:
        path = self._find_job_file(job)
        if path:
            job.status = JobStatus.FAILED
            job.error = error
            dest = self.config.queue_dir / "failed" / path.name
            path.rename(dest)
            dest.write_text(job.model_dump_json(indent=2), encoding="utf-8")
            log.error("[job=%s] Marked FAILED — saved to: %s", job.id, dest.name)

    def complete(self, job: Job) -> None:
        path = self._find_job_file(job)
        if path:
            path.unlink()
            log.debug("[job=%s] Removed from queue (complete)", job.id)
