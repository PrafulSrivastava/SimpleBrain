from __future__ import annotations
import json
import litellm
from typing import Optional, Tuple
from simplebrain.config import BrainConfig
from simplebrain.models import Chunk, FolderProposal
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.brain.grower import SelfGrower

_FILE_PROMPT = """You are a knowledge organiser. Given a chunk of text and its tags,
decide which folder it belongs in from the available folders.
If no folder fits well, propose a new folder name.

Available folders: {folders}
Tags: {tags}
Content: {content}

Return JSON: {{"folder": "folder_name", "is_new": true/false, "reasoning": "why"}}
Only return JSON, no explanation."""


class FileStage:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.knowledge = KnowledgeStore(config)
        self.grower = SelfGrower(config)

    def run(self, chunk: Chunk) -> Tuple[Chunk, Optional[FolderProposal]]:
        folders = self.grower.get_folders()
        prompt = _FILE_PROMPT.format(
            folders=folders or ["(none yet)"],
            tags=chunk.tags,
            content=chunk.content[:500],
        )
        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Fallback: file to _unfiled
            self.knowledge.write_unfiled(chunk)
            return chunk, None

        folder = data.get("folder", "_unfiled")
        is_new = data.get("is_new", False)
        reasoning = data.get("reasoning", "")

        if is_new:
            proposal = self.grower.create_proposal(folder, reasoning, chunk.id)
            self.knowledge.write_unfiled(chunk)
            return chunk, proposal
        else:
            self.knowledge.write(chunk, folder)
            return chunk, None
