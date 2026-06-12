from __future__ import annotations
import logging
import time
from simplebrain.config import BrainConfig
from simplebrain.ingest.queue import FileQueue
from simplebrain.logger import get_logger
from simplebrain.models import JobStatus
from simplebrain.pipeline.transcribe import TranscribeStage
from simplebrain.pipeline.chunk import ChunkStage
from simplebrain.pipeline.tag import TagStage
from simplebrain.pipeline.file import FileStage
from simplebrain.store.index import IndexStore
from simplebrain.store.knowledge import KnowledgeStore

log = get_logger(__name__)


class BackgroundWorker:
    """Polls the FileQueue and runs the 5-stage pipeline on each job."""

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
        job = self.queue.dequeue()
        if job is None:
            return False

        log.info("[job=%s] Dequeued — type=%s user=%s device=%s raw_path=%s",
                 job.id, job.type, job.user, job.device, job.raw_path)

        try:
            # Stage 1: Transcribe
            log.info("[job=%s] Stage 1/5: Transcribe", job.id)
            job = self.transcribe.run(job)
            log.info("[job=%s] Stage 1 done — transcript_path=%s", job.id, job.transcript_path)

            # Stage 2: Chunk
            log.info("[job=%s] Stage 2/5: Chunk", job.id)
            chunks = self.chunk.run(job)
            log.info("[job=%s] Stage 2 done — %d chunk(s)", job.id, len(chunks))

            # Stage 3: Tag
            log.info("[job=%s] Stage 3/5: Tag", job.id)
            chunks = [self.tag.run(c) for c in chunks]
            log.info("[job=%s] Stage 3 done", job.id)

            # Stage 4: File
            log.info("[job=%s] Stage 4/5: File", job.id)
            filed: list = []
            for chunk in chunks:
                filed_chunk, proposal = self.file.run(chunk)
                filed.append(filed_chunk)
                if proposal:
                    log.info("[job=%s] New folder proposal: %r — %s",
                             job.id, proposal.proposed_folder, proposal.reasoning)

            log.info("[job=%s] Stage 4 done — %d chunk(s) filed, paths: %s",
                     job.id, len(filed),
                     [c.file_path for c in filed])

            # Stage 5: Index
            log.info("[job=%s] Stage 5/5: Index", job.id)
            for chunk in filed:
                if chunk.file_path:
                    path = self.config.brain_root / chunk.file_path
                    self.index.update(chunk, path)
            self.index.update_cross_links(filed, self.knowledge)
            log.info("[job=%s] Stage 5 done", job.id)

            self.queue.complete(job)
            log.info("[job=%s] COMPLETE — %d chunk(s) written to knowledge/", job.id, len(filed))
            return True

        except Exception as exc:
            log.error("[job=%s] FAILED at pipeline stage: %s: %s",
                      job.id, type(exc).__name__, exc, exc_info=True)
            self.queue.mark_failed(job, error=str(exc))
            return False

    def run_forever(self, poll_interval: float = 2.0) -> None:
        log.info("BackgroundWorker started — polling every %.1fs", poll_interval)
        while True:
            if not self.process_one():
                time.sleep(poll_interval)
