from __future__ import annotations
import os
from datetime import datetime, timezone
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType

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
        device  = os.getenv("WHISPER_DEVICE",  "cpu")   # cpu | cuda | auto | mps
        compute = os.getenv("WHISPER_COMPUTE", "int8")  # int8 | float16 | float32
        _whisper_model = WhisperModel("base", device=device, compute_type=compute)
    return _whisper_model


class TranscribeStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> Job:
        if job.type == JobType.TEXT:
            # Text notes are already transcripts — skip transcription
            job.transcript_path = job.raw_path
            return job

        model = _get_model()
        audio_path = self.config.brain_root / job.raw_path
        segments, _ = model.transcribe(str(audio_path))
        text = " ".join(s.text for s in segments).strip()

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        out_path = self.config.raw_transcripts_dir / f"{ts}-{job.id}.txt"
        out_path.write_text(text, encoding="utf-8")
        job.transcript_path = str(out_path.relative_to(self.config.brain_root))
        return job
