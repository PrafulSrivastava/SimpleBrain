from __future__ import annotations
import logging
import time
from simplebrain.config import BrainConfig
from simplebrain.ingest.queue import FileQueue
from simplebrain.models import JobStatus
from simplebrain.pipeline.transcribe import TranscribeStage
from simplebrain.pipeline.chunk import ChunkStage
from simplebrain.pipeline.tag import TagStage
from simplebrain.pipeline.file import FileStage
from simplebrain.store.index import IndexStore
from simplebrain.store.knowledge import KnowledgeStore

logger = logging.getLogger(__name__)


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
        """Dequeue and fully process one job.

        Returns:
            True  — a job was dequeued and processed (successfully or failed).
            False — queue was empty; nothing to do.
        """
        job = self.queue.dequeue()
        if job is None:
            return False

        try:
            # Stage 1: Transcribe (no-op for TEXT jobs)
            job = self.transcribe.run(job)

            # Stage 2: Semantic chunking
            chunks = self.chunk.run(job)

            # Stage 3: Auto-tagging
            chunks = [self.tag.run(c) for c in chunks]

            # Stage 4: File each chunk into knowledge/ (or _unfiled)
            filed: list = []
            for chunk in chunks:
                filed_chunk, proposal = self.file.run(chunk)
                filed.append(filed_chunk)
                if proposal:
                    logger.info(
                        "New folder proposal: %s — %s",
                        proposal.proposed_folder,
                        proposal.reasoning,
                    )

            # Stage 5: Update tag/topic index and cross-links
            for chunk in filed:
                if chunk.file_path:
                    path = self.config.brain_root / chunk.file_path
                    self.index.update(chunk, path)
            self.index.update_cross_links(filed, self.knowledge)

            self.queue.complete(job)
            logger.info("Job %s complete — %d chunk(s) filed.", job.id, len(filed))
            return True

        except Exception as exc:  # noqa: BLE001
            logger.error("Job %s failed: %s", job.id, exc)
            self.queue.mark_failed(job, error=str(exc))
            return False

    def run_forever(self, poll_interval: float = 2.0) -> None:
        """Poll the queue indefinitely.  Run in a thread or subprocess."""
        logger.info("BackgroundWorker started — polling every %.1fs.", poll_interval)
        while True:
            if not self.process_one():
                time.sleep(poll_interval)
