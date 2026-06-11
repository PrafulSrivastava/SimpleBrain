from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.brain.grower import SelfGrower

_STRUCTURE_PROMPT = """\
You are a knowledge management expert setting up a personal second brain.

The user has described their needs in their own words. Based on this description, design
the ideal top-level folder structure for their knowledge base.

USER DESCRIPTION:
{description}

RULES:
- Propose 4-8 top-level folders. Quality over quantity -- fewer, broader folders beat many narrow ones.
- Folder names: lowercase, hyphen-separated, concise (1-3 words). No spaces.
- Each folder must have a clear, distinct purpose with no overlap between folders.
- Always include an "archive" folder for old or inactive content.
- Infer the healer schedule from the described usage intensity:
    daily   -> frequent, fast-moving notes (e.g. work logs, daily journaling)
    weekly  -> moderate cadence (e.g. book notes, project docs)
    manual  -> slow or archival (e.g. reference material, rarely updated)
- Write a one-sentence README for each folder that explains exactly what belongs there.

Respond with ONLY a valid JSON object -- no markdown fences, no explanation, nothing else:
{{
  "summary": "One sentence describing the overall purpose of this knowledge base.",
  "healer_schedule": "daily|weekly|manual",
  "folders": [
    {{
      "name": "folder-slug",
      "display": "Human Readable Name",
      "description": "One sentence: what belongs in this folder.",
      "examples": ["example item 1", "example item 2", "example item 3"]
    }}
  ]
}}"""

_README_TEMPLATE = """\
# {display}

{description}

## Examples
{examples}

---
*This folder was created automatically by SimpleBrain setup.*
"""


class SetupWizard:
    def __init__(self, config: BrainConfig):
        self.config = config

    # ------------------------------------------------------------------
    # Phase 1: ask the LLM to propose a structure (no files written yet)
    # ------------------------------------------------------------------

    def propose(self, description: str) -> dict:
        """Call the LLM with the user's free-form description.

        Returns a proposal dict with shape:
            {
              "summary": str,
              "healer_schedule": "daily|weekly|manual",
              "folders": [
                {"name": str, "display": str, "description": str, "examples": [str]}
              ]
            }

        All LLM config is read from self.config (populated from .env).
        Raises ValueError if the LLM returns unparseable JSON.
        """
        prompt = _STRUCTURE_PROMPT.format(description=description.strip())

        response = litellm.completion(
            **self.config.litellm_kwargs,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            lines = raw.splitlines()
            raw = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        # Some models (e.g. Gemma) emit a thinking/reasoning block before the JSON.
        # Extract the first top-level {...} object regardless of what precedes it.
        brace_start = raw.find("{")
        brace_end   = raw.rfind("}")
        if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
            raw = raw[brace_start : brace_end + 1]

        try:
            proposal = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"LLM returned invalid JSON.\n"
                f"Raw response:\n{raw}"
            ) from exc

        # Validate and normalise
        if not isinstance(proposal.get("folders"), list):
            raise ValueError("LLM response missing 'folders' list.")

        # Normalise healer_schedule — model may return e.g. "daily|weekly"
        schedule = str(proposal.get("healer_schedule", "daily")).lower()
        if "daily" in schedule:
            proposal["healer_schedule"] = "daily"
        elif "weekly" in schedule:
            proposal["healer_schedule"] = "weekly"
        else:
            proposal["healer_schedule"] = "manual"

        # Guarantee 'archive' is present
        names = [f["name"] for f in proposal["folders"]]
        if "archive" not in names:
            proposal["folders"].append({
                "name": "archive",
                "display": "Archive",
                "description": "Old or inactive content that is no longer actively referenced.",
                "examples": ["completed projects", "outdated references", "old notes"],
            })

        proposal.setdefault("summary", "Personal knowledge base.")
        proposal.setdefault("healer_schedule", "daily")

        return proposal

    # ------------------------------------------------------------------
    # Phase 2: create the structure on disk after user confirms
    # ------------------------------------------------------------------

    def apply(self, proposal: dict) -> list[str]:
        """Write folders, README files, and metadata based on an approved proposal.

        Args:
            proposal: the dict returned by propose()

        Returns:
            list[str]: folder slugs that were created under knowledge_dir
        """
        folders_meta = proposal["folders"]
        folder_names = [f["name"] for f in folders_meta]

        for folder in folders_meta:
            folder_path = self.config.knowledge_dir / folder["name"]
            folder_path.mkdir(parents=True, exist_ok=True)

            # Write a README.md describing the folder's purpose
            examples_md = "\n".join(f"- {ex}" for ex in folder.get("examples", []))
            readme = _README_TEMPLATE.format(
                display=folder["display"],
                description=folder["description"],
                examples=examples_md,
            )
            (folder_path / "README.md").write_text(readme, encoding="utf-8")

        # Persist folder structure via SelfGrower
        grower = SelfGrower(self.config)
        structure = grower.load_structure()
        structure["folders"] = folder_names
        grower.save_structure(structure)

        # Save full proposal + metadata to _meta/setup.json
        setup_data = {
            "summary": proposal.get("summary", ""),
            "healer_schedule": proposal.get("healer_schedule", "daily"),
            "folders": folders_meta,
            "llm_provider": self.config.llm_provider,
            "llm_model": self.config.llm_model,
        }
        (self.config.meta_dir / "setup.json").write_text(
            json.dumps(setup_data, indent=2), encoding="utf-8"
        )

        return folder_names
