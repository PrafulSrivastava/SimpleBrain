from __future__ import annotations
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger
from simplebrain.models import Job, JobType
from simplebrain.store.raw import RawStore
from simplebrain.ingest.queue import FileQueue

log = get_logger(__name__)


class IngestService:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.raw = RawStore(config)
        self.queue = FileQueue(config)

    def add_text_note(self, text: str, user: str, device: str = "unknown") -> str:
        job = Job(type=JobType.TEXT, user=user, device=device)
        log.info("[job=%s] Ingesting TEXT note — user=%s device=%s chars=%d",
                 job.id, user, device, len(text))

        raw_path = self.raw.save_text(text, job.id)
        job.raw_path = raw_path
        log.debug("[job=%s] Raw text saved: %s", job.id, raw_path)

        self.queue.enqueue(job)
        log.info("[job=%s] Queued for processing", job.id)
        return job.id

    def add_voice_note(self, audio_bytes: bytes, filename: str,
                       user: str, device: str = "unknown") -> str:
        job = Job(type=JobType.VOICE, user=user, device=device)
        log.info("[job=%s] Ingesting VOICE note — user=%s device=%s filename=%s bytes=%d",
                 job.id, user, device, filename, len(audio_bytes))

        raw_path = self.raw.save_audio(audio_bytes, filename, job.id)
        job.raw_path = raw_path
        log.info("[job=%s] Audio saved: %s", job.id, raw_path)

        self.queue.enqueue(job)
        log.info("[job=%s] Queued for processing", job.id)
        return job.id
