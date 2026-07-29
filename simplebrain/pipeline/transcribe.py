from __future__ import annotations
import os
from datetime import datetime, timezone
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger
from simplebrain.models import Job, JobType

log = get_logger(__name__)

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None  # type: ignore

_whisper_model = None  # module-level cache


def _get_model():
    global _whisper_model
    if WhisperModel is None:
        raise RuntimeError(
            "faster-whisper is not installed. "
            "Install it with: pip install faster-whisper"
        )
    if _whisper_model is None:
        device  = os.getenv("WHISPER_DEVICE",  "cpu")
        compute = os.getenv("WHISPER_COMPUTE", "int8")
        log.info("Loading Whisper model (device=%s compute=%s)", device, compute)
        _whisper_model = WhisperModel("base", device=device, compute_type=compute)
        log.info("Whisper model loaded")
    return _whisper_model


class TranscribeStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> Job:
        if job.type == JobType.TEXT:
            log.debug("[job=%s] TEXT job — skipping transcription, raw_path=%s",
                      job.id, job.raw_path)
            job.transcript_path = job.raw_path
            return job

        if job.type == JobType.DOCUMENT:
            log.debug("[job=%s] DOCUMENT job — handled by DoclingStage", job.id)
            return job

        audio_path = self.config.brain_root / job.raw_path
        log.info("[job=%s] Transcribing audio: %s", job.id, audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}. "
                f"raw_path in job was: {job.raw_path}"
            )

        model = _get_model()
        segments, info = model.transcribe(str(audio_path))
        text = " ".join(s.text for s in segments).strip()

        log.info("[job=%s] Transcription complete — detected_language=%s duration=%.1fs chars=%d",
                 job.id,
                 getattr(info, "language", "unknown"),
                 getattr(info, "duration", 0),
                 len(text))

        if not text:
            log.warning("[job=%s] Transcription produced empty text — audio may be silent or too short",
                        job.id)

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = self.config.raw_transcripts_dir / f"{ts}-{job.id}.txt"
        out_path.write_text(text, encoding="utf-8")
        job.transcript_path = str(out_path.relative_to(self.config.brain_root))

        log.info("[job=%s] Transcript saved: %s", job.id, out_path)
        return job
