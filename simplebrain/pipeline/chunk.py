from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.models import Job, Chunk

_CHUNK_PROMPT = """You are a knowledge chunker. Split the following note into semantic chunks.
Each chunk should represent one focused idea or topic.
Return a JSON array of strings. Each string is one chunk.
If the note is short and focused, return a single-element array.

Note:
{text}

Return only the JSON array, no explanation."""


class ChunkStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, job: Job) -> list[Chunk]:
        text = (self.config.brain_root / job.transcript_path).read_text(encoding="utf-8")
        prompt = _CHUNK_PROMPT.format(text=text)

        response = litellm.completion(
            model=self.config.llm_model,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            contents = json.loads(raw)
            if not isinstance(contents, list):
                contents = [text]
        except json.JSONDecodeError:
            contents = [text]

        # If multiple chunks, assign a shared parent id
        parent_id = None
        if len(contents) > 1:
            import uuid
            parent_id = str(uuid.uuid4())[:8]

        chunks = []
        for content in contents:
            chunk = Chunk(
                content=content.strip(),
                source_raw=job.transcript_path or "",
                user=job.user,
                device=job.device,
                parent=parent_id,
            )
            chunks.append(chunk)

        return chunks
