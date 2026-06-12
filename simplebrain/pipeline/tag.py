from __future__ import annotations
import json
import re
import litellm
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger, llm_log_enabled
from simplebrain.models import Chunk

log = get_logger(__name__)

_TAG_PROMPT = """Analyse the following note chunk and return a JSON object with two fields:
  "title" : a short, descriptive title for this chunk (5 words max, sentence case, no punctuation)
  "tags"  : an array of lowercase tag strings prefixed with #, representing key topics/concepts

Chunk:
{content}

Return only valid JSON, no explanation. Example:
{{"title": "PostgreSQL chosen as main datastore", "tags": ["#postgresql", "#database", "#decision"]}}"""


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:60]


class TagStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, chunk: Chunk) -> Chunk:
        log.debug("[chunk=%s] TagStage — content_chars=%d", chunk.id, len(chunk.content))

        if not chunk.content.strip():
            log.warning("[chunk=%s] TagStage — chunk has no content, skipping LLM call", chunk.id)
            chunk.tags = []
            chunk.title = None
            return chunk

        prompt = _TAG_PROMPT.format(content=chunk.content[:1000])

        if llm_log_enabled():
            log.debug("[chunk=%s] LLM tag request — model=%s\n--- PROMPT ---\n%s\n--------------",
                      chunk.id, self.config.llm_model, prompt)

        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        if llm_log_enabled():
            log.debug("[chunk=%s] LLM tag response — chars=%d\n--- RESPONSE ---\n%s\n----------------",
                      chunk.id, len(raw), raw[:1000])

        # Strip thinking preamble
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start : brace_end + 1]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("[chunk=%s] LLM tag response is not valid JSON (%s) — tags will be empty. raw=%r",
                        chunk.id, exc, raw[:200])
            data = {}

        # Handle both {"title": ..., "tags": [...]} and legacy ["#tag"] array
        if isinstance(data, list):
            log.debug("[chunk=%s] LLM returned tag array instead of object — no title", chunk.id)
            title = None
            tags  = data
        else:
            title = data.get("title") or ""
            tags  = data.get("tags", [])

        if isinstance(tags, list):
            normalised = []
            for t in tags:
                if isinstance(t, str) and t.strip():
                    t = t.strip().lower()
                    if not t.startswith("#"):
                        t = "#" + t
                    import re as _re
                    t = "#" + _re.sub(r"[\s_]+", "-", t[1:])
                    t = _re.sub(r"-+", "-", t).strip("-")
                    normalised.append(t)
            chunk.tags = normalised
        else:
            log.warning("[chunk=%s] LLM returned non-list tags (%s) — tags will be empty",
                        chunk.id, type(tags).__name__)
            chunk.tags = []

        chunk.title = title.strip() if title else None

        log.info("[chunk=%s] TagStage — title=%r tags=%s",
                 chunk.id, chunk.title, chunk.tags)
        return chunk
