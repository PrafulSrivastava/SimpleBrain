# simplebrain/brain/healer.py
from __future__ import annotations
import json
import litellm
from datetime import datetime
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.models import (Conflict, ConflictType, ConflictStatus,
                                 Resolution)
from simplebrain.store.knowledge import KnowledgeStore

_HEAL_PROMPT = """You are a knowledge consistency checker. Review the following chunks
from the same knowledge base folder and identify:
1. Factual conflicts (contradicting statements)
2. Structural issues (duplicates, orphans)
3. Pivots (topic drift)

Chunks:
{chunks}

Return a JSON array of conflicts found. Each conflict:
{{"type": "factual_conflict|structural_issue|pivot",
  "chunks_involved": ["id1", "id2"],
  "summary": "brief description"}}

Return empty array [] if no conflicts found. Return only JSON."""


class SelfHealer:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _log_path(self) -> Path:
        return self.config.conflicts_dir / "resolution-log.json"

    @property
    def _pending_dir(self) -> Path:
        return self.config.conflicts_dir / "pending"

    def load_resolution_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        return json.loads(self._log_path.read_text())

    def _save_log(self, log: list[dict]) -> None:
        self._log_path.write_text(json.dumps(log, indent=2))

    def _save_pending(self, conflict: Conflict) -> None:
        self._pending_dir.mkdir(parents=True, exist_ok=True)
        path = self._pending_dir / f"{conflict.id}.json"
        path.write_text(conflict.model_dump_json(indent=2))

    def scan(self) -> list[Conflict]:
        """Scan all knowledge folders for conflicts. Returns new conflicts."""
        all_conflicts: list[Conflict] = []

        for folder in self.config.knowledge_dir.iterdir():
            if not folder.is_dir() or folder.name.startswith("_"):
                continue
            chunk_files = list(folder.glob("*.md"))
            if len(chunk_files) < 2:
                continue

            chunks_text = []
            for cf in chunk_files[:20]:  # limit context size
                try:
                    import frontmatter
                    post = frontmatter.load(str(cf))
                    chunks_text.append(f"ID:{post['id']} — {post.content[:200]}")
                except Exception:
                    continue

            prompt = _HEAL_PROMPT.format(chunks="\n".join(chunks_text))
            response = litellm.completion(
                model=self.config.llm_model,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.choices[0].message.content.strip()
            try:
                items = json.loads(raw)
                for item in items:
                    conflict = Conflict(
                        type=ConflictType(item["type"]),
                        chunks_involved=item["chunks_involved"],
                        summary=item["summary"],
                    )
                    self._save_pending(conflict)
                    all_conflicts.append(conflict)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

        return all_conflicts

    def resolve(self, conflict_id: str, resolution: Resolution,
                resolved_by: str) -> None:
        """Mark a pending conflict as resolved, append to log, remove from pending."""
        pending_path = self._pending_dir / f"{conflict_id}.json"
        if not pending_path.exists():
            raise FileNotFoundError(f"Conflict {conflict_id} not found")

        conflict = Conflict(**json.loads(pending_path.read_text()))
        conflict.resolution = resolution
        conflict.resolved_by = resolved_by
        conflict.resolved_at = datetime.utcnow()
        conflict.status = ConflictStatus.RESOLVED

        log = self.load_resolution_log()
        log.append(json.loads(conflict.model_dump_json()))
        self._save_log(log)
        pending_path.unlink()

    def revert(self, conflict_id: str,
               knowledge_store: Optional[KnowledgeStore] = None) -> None:
        """Revert chunk content to snapshot recorded at conflict detection time."""
        log = self.load_resolution_log()
        entry = next((e for e in log if e["id"] == conflict_id), None)
        if not entry:
            raise FileNotFoundError(f"Resolution {conflict_id} not in log")

        ks = knowledge_store or KnowledgeStore(self.config)
        snapshot = entry.get("snapshot", {}).get("chunks", {})
        for chunk_id, original_content in snapshot.items():
            try:
                chunk = ks.read(chunk_id)
                if chunk.file_path:
                    path = self.config.brain_root / chunk.file_path
                    import frontmatter
                    post = frontmatter.load(str(path))
                    post.content = original_content
                    path.write_text(frontmatter.dumps(post), encoding="utf-8")
            except FileNotFoundError:
                continue

        entry["status"] = ConflictStatus.REVERTED
        self._save_log(log)

    def list_pending(self) -> list[Conflict]:
        """Return all conflicts still awaiting resolution."""
        self._pending_dir.mkdir(parents=True, exist_ok=True)
        return [
            Conflict(**json.loads(p.read_text()))
            for p in self._pending_dir.glob("*.json")
        ]
