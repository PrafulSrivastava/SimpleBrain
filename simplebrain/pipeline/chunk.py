from __future__ import annotations
import json
import uuid
import litellm
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger, llm_log_enabled
from simplebrain.models import Job, Chunk

log = get_logger(__name__)

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
        transcript_file = self.config.brain_root / job.transcript_path
        log.info("[job=%s] ChunkStage — reading transcript: %s", job.id, transcript_file)

        if not transcript_file.exists():
            raise FileNotFoundError(
                f"Transcript file not found: {transcript_file}. "
                f"transcript_path in job was: {job.transcript_path}"
            )

        text = transcript_file.read_text(encoding="utf-8")

        if not text.strip():
            log.warning("[job=%s] Transcript is empty — producing single empty chunk", job.id)
            return [Chunk(
                content="",
                source_raw=job.raw_path or "",
                user=job.user,
                device=job.device,
            )]

        prompt = _CHUNK_PROMPT.format(text=text)

        if llm_log_enabled():
            log.debug("[job=%s] LLM chunk request — model=%s prompt_chars=%d\n--- PROMPT ---\n%s\n--------------",
                      job.id, self.config.llm_model, len(prompt), prompt[:1000])

        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        if llm_log_enabled():
            log.debug("[job=%s] LLM chunk response — chars=%d\n--- RESPONSE ---\n%s\n----------------",
                      job.id, len(raw), raw[:2000])

        # Strip thinking preamble then parse the FIRST complete JSON array
        bracket = raw.find("[")
        if bracket > 0:
            raw = raw[bracket:]
        try:
            contents, _ = json.JSONDecoder().raw_decode(raw)
            if not isinstance(contents, list):
                log.warning("[job=%s] LLM returned non-list JSON (%s) — treating as single chunk",
                            job.id, type(contents).__name__)
                contents = [text]
        except json.JSONDecodeError as exc:
            log.warning("[job=%s] LLM chunk response is not valid JSON (%s) — treating as single chunk. raw=%r",
                        job.id, exc, raw[:200])
            contents = [text]

        # Filter out empty strings and obvious prompt leaks
        contents = [c for c in contents if isinstance(c, str) and c.strip()]
        if not contents:
            log.warning("[job=%s] All chunks were empty after filtering — using full text", job.id)
            contents = [text]

        log.info("[job=%s] ChunkStage — produced %d chunk(s)", job.id, len(contents))

        parent_id = str(uuid.uuid4())[:8] if len(contents) > 1 else None

        return [
            Chunk(
                content=c.strip(),
                source_raw=job.raw_path or "",
                user=job.user,
                device=job.device,
                parent=parent_id,
            )
            for c in contents
        ]
