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
