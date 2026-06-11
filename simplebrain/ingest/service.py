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
