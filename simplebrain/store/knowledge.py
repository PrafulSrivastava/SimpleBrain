from __future__ import annotations
from pathlib import Path
from datetime import datetime
import frontmatter
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk


class KnowledgeStore:
    def __init__(self, config: BrainConfig):
        self.config = config

    def write(self, chunk: Chunk, folder: str) -> Path:
        target_dir = self.config.knowledge_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{chunk.id}.md"
        self._write_chunk_file(chunk, path)
        chunk.file_path = str(path.relative_to(self.config.brain_root))
        return path

    def write_unfiled(self, chunk: Chunk) -> Path:
        return self.write(chunk, "_unfiled")

    def _write_chunk_file(self, chunk: Chunk, path: Path) -> None:
        post = frontmatter.Post(
            content=chunk.content,
            id=chunk.id,
            created=chunk.created.isoformat(),
            source_raw=chunk.source_raw,
            tags=chunk.tags,
            links=chunk.links,
            parent=chunk.parent,
            user=chunk.user,
            device=chunk.device,
        )
        path.write_text(frontmatter.dumps(post), encoding="utf-8")

    def read(self, chunk_id: str) -> Chunk:
        matches = list(self.config.knowledge_dir.rglob(f"{chunk_id}.md"))
        if not matches:
            raise FileNotFoundError(f"Chunk {chunk_id} not found")
        post = frontmatter.load(str(matches[0]))
        return Chunk(
            id=post["id"],
            created=datetime.fromisoformat(post["created"]),
            source_raw=post["source_raw"],
            tags=post.get("tags", []),
            links=post.get("links", []),
            parent=post.get("parent"),
            user=post["user"],
            device=post.get("device", "unknown"),
            content=post.content,
            file_path=str(matches[0].relative_to(self.config.brain_root)),
        )

    def update_links(self, chunk_id: str, links: list[str]) -> None:
        matches = list(self.config.knowledge_dir.rglob(f"{chunk_id}.md"))
        if not matches:
            return
        post = frontmatter.load(str(matches[0]))
        post["links"] = links
        matches[0].write_text(frontmatter.dumps(post), encoding="utf-8")
