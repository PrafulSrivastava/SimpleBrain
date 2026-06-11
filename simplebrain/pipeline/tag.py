from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk

_TAG_PROMPT = """Extract tags from the following note chunk.
Tags should be short, lowercase, prefixed with #, and represent key topics/concepts.
Return a JSON array of tag strings.

Chunk:
{content}

Return only the JSON array, no explanation."""


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
        try:
            tags = json.loads(raw)
            if isinstance(tags, list):
                chunk.tags = [t for t in tags if isinstance(t, str)]
            else:
                chunk.tags = []
        except json.JSONDecodeError:
            chunk.tags = []
        return chunk
