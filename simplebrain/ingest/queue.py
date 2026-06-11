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
        # Use time.time_ns() for nanosecond-precision ordering so that jobs
        # enqueued within the same millisecond are still ordered correctly.
        ns = time.time_ns()
        return self.config.queue_dir / f"{ns:020d}-{job.id}.json"

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
