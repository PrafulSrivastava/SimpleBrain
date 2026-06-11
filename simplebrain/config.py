from __future__ import annotations
from pathlib import Path
from pydantic import BaseModel
import os


class BrainConfig(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    brain_root: Path
    user: str
    device: str = "unknown"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"

    def model_post_init(self, __context):
        for folder in [
            self.raw_audio_dir, self.raw_transcripts_dir,
            self.queue_dir, self.queue_dir / "failed",
            self.index_dir,
            self.conflicts_dir / "pending",
            self.meta_dir,
            self.knowledge_dir / "_unfiled",
        ]:
            folder.mkdir(parents=True, exist_ok=True)

    @property
    def raw_audio_dir(self) -> Path:
        return self.brain_root / "_raw" / "audio"

    @property
    def raw_transcripts_dir(self) -> Path:
        return self.brain_root / "_raw" / "transcripts"

    @property
    def queue_dir(self) -> Path:
        return self.brain_root / "_queue"

    @property
    def knowledge_dir(self) -> Path:
        return self.brain_root / "knowledge"

    @property
    def index_dir(self) -> Path:
        return self.brain_root / "_index"

    @property
    def conflicts_dir(self) -> Path:
        return self.brain_root / "_conflicts"

    @property
    def meta_dir(self) -> Path:
        return self.brain_root / "_meta"

    @classmethod
    def from_env(cls) -> "BrainConfig":
        from dotenv import load_dotenv
        load_dotenv()
        return cls(
            brain_root=Path(os.getenv("BRAIN_ROOT", "~/simplebrain")).expanduser(),
            user=os.getenv("BRAIN_USER", "default"),
            device=os.getenv("BRAIN_DEVICE", "unknown"),
            llm_provider=os.getenv("LLM_PROVIDER", "openai"),
            llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        )
