from __future__ import annotations
import json
import litellm
from simplebrain.config import BrainConfig
from simplebrain.brain.grower import SelfGrower

_STRUCTURE_PROMPT = """You are setting up a knowledge base. Based on the user's description,
generate a list of top-level folder names for organising their notes.
Keep it to 4-8 folders. Use lowercase, hyphen-separated names.
Always include an "archive" folder.

Purpose: {purpose}
Suggested topics: {topics}

Return a JSON array of folder name strings only."""


class SetupWizard:
    def __init__(self, config: BrainConfig):
        self.config = config

    def run(self, answers: dict) -> list[str]:
        """Run setup with provided answers. Returns list of created folder names.

        Args:
            answers: dict with keys:
                - purpose (str): What the brain is for
                - users (list[str]): Who will use it
                - topics (list[str]): Suggested topic areas
                - healer_schedule (str): daily/weekly/manual
                - llm_provider (str): openai/anthropic/ollama
                - llm_model (str): e.g. gpt-4o-mini

        Returns:
            list[str]: Names of folders created under knowledge_dir
        """
        prompt = _STRUCTURE_PROMPT.format(
            purpose=answers["purpose"],
            topics=", ".join(answers.get("topics", [])),
        )
        response = litellm.completion(
            model=answers.get("llm_model", "gpt-4o-mini"),
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.choices[0].message.content.strip()

        try:
            folders = json.loads(raw)
            if not isinstance(folders, list):
                folders = answers.get("topics", []) + ["archive"]
        except json.JSONDecodeError:
            folders = answers.get("topics", []) + ["archive"]

        # Ensure "archive" is always present
        if "archive" not in folders:
            folders.append("archive")

        # Create knowledge folders
        for folder in folders:
            (self.config.knowledge_dir / folder).mkdir(parents=True, exist_ok=True)

        # Persist folder structure via SelfGrower
        grower = SelfGrower(self.config)
        structure = grower.load_structure()
        structure["folders"] = folders
        grower.save_structure(structure)

        # Save full setup config to _meta/setup.json
        setup_data = {**answers, "folders": folders}
        (self.config.meta_dir / "setup.json").write_text(
            json.dumps(setup_data, indent=2), encoding="utf-8"
        )

        return folders
