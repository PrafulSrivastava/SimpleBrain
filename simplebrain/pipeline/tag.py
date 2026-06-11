from __future__ import annotations
import json
import re
import litellm
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk

_TAG_PROMPT = """Analyse the following note chunk and return a JSON object with two fields:
  "title" : a short, descriptive title for this chunk (5 words max, sentence case, no punctuation)
  "tags"  : an array of lowercase tag strings prefixed with #, representing key topics/concepts

Chunk:
{content}

Return only valid JSON, no explanation. Example:
{{"title": "PostgreSQL chosen as main datastore", "tags": ["#postgresql", "#database", "#decision"]}}"""


def _slugify(text: str) -> str:
    """Convert a title to a filename-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)       # strip non-alphanumeric except hyphens
    text = re.sub(r"[\s_]+", "-", text)         # spaces/underscores -> hyphens
    text = re.sub(r"-+", "-", text).strip("-")  # collapse multiple hyphens
    return text[:60]                             # cap length


class TagStage:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, chunk: Chunk) -> Chunk:
        prompt = _TAG_PROMPT.format(content=chunk.content)
        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # Strip thinking preamble (some models emit reasoning before JSON)
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start : brace_end + 1]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        # Handle both {"title": ..., "tags": [...]} and legacy ["#tag"] array responses
        if isinstance(data, list):
            title = None
            tags = data
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
                    # Slugify: replace spaces and underscores with hyphens
                    import re as _re
                    t = "#" + _re.sub(r"[\s_]+", "-", t[1:])
                    t = _re.sub(r"-+", "-", t).strip("-")
                    normalised.append(t)
            chunk.tags = normalised
        else:
            chunk.tags = []

        chunk.title = title.strip() if title else None
        return chunk
