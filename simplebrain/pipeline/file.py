from __future__ import annotations
import json
import litellm
from typing import Optional, Tuple
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger, llm_log_enabled
from simplebrain.models import Chunk, FolderProposal
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.brain.grower import SelfGrower

log = get_logger(__name__)

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
        log.debug("[chunk=%s] FileStage — available folders: %s", chunk.id, folders)

        prompt = _FILE_PROMPT.format(
            folders=folders or ["(none yet)"],
            tags=chunk.tags,
            content=chunk.content[:500],
        )

        if llm_log_enabled():
            log.debug("[chunk=%s] LLM file request — model=%s\n--- PROMPT ---\n%s\n--------------",
                      chunk.id, self.config.llm_model, prompt)

        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        if llm_log_enabled():
            log.debug("[chunk=%s] LLM file response — chars=%d\n--- RESPONSE ---\n%s\n----------------",
                      chunk.id, len(raw), raw[:500])

        # Strip thinking preamble
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            raw = raw[brace_start : brace_end + 1]

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            log.warning("[chunk=%s] LLM file response is not valid JSON (%s) — filing to _unfiled. raw=%r",
                        chunk.id, exc, raw[:200])
            self.knowledge.write_unfiled(chunk)
            return chunk, None

        folder    = data.get("folder", "_unfiled")
        is_new    = data.get("is_new", False)
        reasoning = data.get("reasoning", "")

        if is_new:
            log.info("[chunk=%s] FileStage — LLM proposes new folder %r: %s",
                     chunk.id, folder, reasoning)
            proposal = self.grower.create_proposal(folder, reasoning, chunk.id)
            self.knowledge.write_unfiled(chunk)
            return chunk, proposal

        log.info("[chunk=%s] FileStage — filing to folder %r (reasoning: %s)",
                 chunk.id, folder, reasoning)
        self.knowledge.write(chunk, folder)
        return chunk, None
