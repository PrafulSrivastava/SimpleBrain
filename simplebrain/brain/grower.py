from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from simplebrain.config import BrainConfig
from simplebrain.models import FolderProposal, FolderProposalStatus


class SelfGrower:
    def __init__(self, config: BrainConfig):
        self.config = config

    @property
    def _structure_path(self) -> Path:
        return self.config.meta_dir / "structure.json"

    def load_structure(self) -> dict:
        if not self._structure_path.exists():
            return {"folders": [], "pending_proposals": []}
        return json.loads(self._structure_path.read_text())

    def save_structure(self, structure: dict) -> None:
        self._structure_path.parent.mkdir(parents=True, exist_ok=True)
        self._structure_path.write_text(json.dumps(structure, indent=2))

    def get_folders(self) -> list[str]:
        return self.load_structure().get("folders", [])

    def create_proposal(self, folder: str, reasoning: str,
                        chunk_id: str) -> FolderProposal:
        proposal = FolderProposal(
            proposed_folder=folder,
            reasoning=reasoning,
            held_chunk_ids=[chunk_id],
        )
        structure = self.load_structure()
        structure.setdefault("pending_proposals", [])
        structure["pending_proposals"].append(json.loads(proposal.model_dump_json()))
        self.save_structure(structure)
        return proposal

    def confirm_proposal(self, proposal_id: str) -> Optional[FolderProposal]:
        structure = self.load_structure()
        for p in structure.get("pending_proposals", []):
            if p["id"] == proposal_id:
                p["status"] = FolderProposalStatus.CONFIRMED
                structure["folders"].append(p["proposed_folder"])
                self.save_structure(structure)
                return FolderProposal(**p)
        return None

    def reject_proposal(self, proposal_id: str) -> Optional[FolderProposal]:
        structure = self.load_structure()
        for p in structure.get("pending_proposals", []):
            if p["id"] == proposal_id:
                p["status"] = FolderProposalStatus.REJECTED
                self.save_structure(structure)
                return FolderProposal(**p)
        return None

    def list_pending(self) -> list[FolderProposal]:
        structure = self.load_structure()
        return [
            FolderProposal(**p)
            for p in structure.get("pending_proposals", [])
            if p["status"] == FolderProposalStatus.PENDING
        ]
