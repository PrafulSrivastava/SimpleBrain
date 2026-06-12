from __future__ import annotations
import json
import litellm
from pathlib import Path
from typing import Optional, Tuple
from simplebrain.config import BrainConfig
from simplebrain.logger import get_logger, llm_log_enabled
from simplebrain.models import Chunk, FolderProposal
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.brain.grower import SelfGrower

log = get_logger(__name__)

_FILE_PROMPT = """You are a knowledge organiser for a second brain.

Brain purpose: {brain_summary}

You must file the following chunk into exactly one of the available folders.
Study the folder descriptions and any existing content samples to choose the best fit.
If truly no folder fits, propose a new one.

--- AVAILABLE FOLDERS ---
{folder_context}

--- CHUNK TO FILE ---
Tags:    {tags}
Content: {content}

Return JSON only, no explanation:
{{"folder": "folder_name", "is_new": true/false, "reasoning": "one sentence"}}"""

# How many existing chunks to sample per folder to give the LLM real context
_SAMPLE_CHUNKS_PER_FOLDER = 2
# Max chars of each sampled chunk to include in prompt
_SAMPLE_CHUNK_CHARS = 200


def _build_folder_context(folder_details: list[dict], knowledge_dir: Path) -> str:
    """
    Build a rich folder context block for the filing prompt.
    For each folder: name, description, and up to N sample chunk titles.
    """
    lines = []
    for fd in folder_details:
        name = fd["name"]
        display = fd.get("display", name)
        desc = fd.get("description", "")
        lines.append(f"\n[{name}]  ({display})")
        if desc:
            lines.append(f"  Purpose: {desc}")

        # Sample existing chunks from this folder for concrete context
        folder_path = knowledge_dir / name
        if folder_path.exists():
            md_files = sorted(folder_path.glob("*.md"))[:_SAMPLE_CHUNKS_PER_FOLDER]
            if md_files:
                lines.append("  Existing notes (samples):")
                for md in md_files:
                    try:
                        import frontmatter as _fm
                        post = _fm.load(str(md))
                        title = post.get("title") or md.stem
                        snippet = post.content[:_SAMPLE_CHUNK_CHARS].replace("\n", " ")
                        lines.append(f"    - {title}: {snippet}")
                    except Exception:
                        lines.append(f"    - {md.stem}")
            else:
                lines.append("  (no notes yet)")
        else:
            lines.append("  (no notes yet)")

    return "\n".join(lines)


def _load_brain_summary(config: BrainConfig) -> str:
    try:
        setup = json.loads((config.meta_dir / "setup.json").read_text(encoding="utf-8"))
        return setup.get("summary", "")
    except Exception:
        return ""


class FileStage:
    def __init__(self, config: BrainConfig):
        self.config = config
        self.knowledge = KnowledgeStore(config)
        self.grower = SelfGrower(config)

    def run(self, chunk: Chunk) -> Tuple[Chunk, Optional[FolderProposal]]:
        folder_details = self.grower.get_folder_details()
        log.debug("[chunk=%s] FileStage — %d folder(s) available: %s",
                  chunk.id, len(folder_details), [f["name"] for f in folder_details])

        folder_context = _build_folder_context(folder_details, self.config.knowledge_dir)
        brain_summary  = _load_brain_summary(self.config)

        prompt = _FILE_PROMPT.format(
            brain_summary=brain_summary or "(not specified)",
            folder_context=folder_context or "(no folders defined yet)",
            tags=chunk.tags or "(none)",
            content=chunk.content[:600],
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

        # Strip thinking preamble then parse the FIRST complete JSON object
        brace = raw.find("{")
        if brace > 0:
            raw = raw[brace:]
        try:
            data, _ = json.JSONDecoder().raw_decode(raw)
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

        log.info("[chunk=%s] FileStage — filing to %r (reason: %s)", chunk.id, folder, reasoning)
        self.knowledge.write(chunk, folder)
        return chunk, None
