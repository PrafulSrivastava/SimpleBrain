from __future__ import annotations
import json
from pathlib import Path
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk


class IndexStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _tags_path(self) -> Path:
        return self.config.index_dir / "tags.json"

    @property
    def _topics_path(self) -> Path:
        return self.config.index_dir / "topics.json"

    def load_tags(self) -> dict[str, list[str]]:
        if not self._tags_path.exists():
            return {}
        return json.loads(self._tags_path.read_text())

    def load_topics(self) -> dict[str, list[str]]:
        if not self._topics_path.exists():
            return {}
        return json.loads(self._topics_path.read_text())

    def update(self, chunk: Chunk, file_path: Path) -> None:
        tags = self.load_tags()
        for tag in chunk.tags:
            tags.setdefault(tag, [])
            if chunk.id not in tags[tag]:
                tags[tag].append(chunk.id)
        self._tags_path.write_text(json.dumps(tags, indent=2))

        topics = self.load_topics()
        folder = file_path.parent.name
        topics.setdefault(folder, [])
        if chunk.id not in topics[folder]:
            topics[folder].append(chunk.id)
        self._topics_path.write_text(json.dumps(topics, indent=2))

    def update_cross_links(self, chunks: list[Chunk], knowledge_store) -> None:
        """Update links in chunk files for chunks that share tags."""
        tag_to_chunks: dict[str, list[str]] = {}
        for chunk in chunks:
            for tag in chunk.tags:
                tag_to_chunks.setdefault(tag, []).append(chunk.id)

        for chunk in chunks:
            linked = set()
            for tag in chunk.tags:
                for cid in tag_to_chunks.get(tag, []):
                    if cid != chunk.id:
                        linked.add(cid)
            if linked:
                knowledge_store.update_links(chunk.id, list(linked))

    def search(self, query: str, tags: list[str] | None = None) -> list[str]:
        """Return chunk IDs matching tags or query keywords."""
        tag_index = self.load_tags()
        matched: set[str] = set()

        search_tags = tags or []
        if not search_tags:
            query_lower = query.lower()
            search_tags = [t for t in tag_index if query_lower in t.lower()]

        for tag in search_tags:
            matched.update(tag_index.get(tag, []))

        return list(matched)
