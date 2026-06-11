from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
from simplebrain.config import BrainConfig


class RawStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    def save_text(self, text: str, job_id: str) -> str:
        """Save raw text. Returns relative path from brain_root."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        path = self.config.raw_transcripts_dir / f"{ts}-{job_id}.txt"
        path.write_text(text, encoding="utf-8")
        return str(path.relative_to(self.config.brain_root))

    def save_audio(self, audio_bytes: bytes, filename: str, job_id: str) -> str:
        """Save raw audio. Returns relative path from brain_root."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        suffix = Path(filename).suffix or ".wav"
        path = self.config.raw_audio_dir / f"{ts}-{job_id}{suffix}"
        path.write_bytes(audio_bytes)
        return str(path.relative_to(self.config.brain_root))

    def read_text(self, relative_path: str) -> str:
        return (self.config.brain_root / relative_path).read_text(encoding="utf-8")
