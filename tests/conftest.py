import pytest
import tempfile
from pathlib import Path
from simplebrain.config import BrainConfig


@pytest.fixture
def brain_dir(tmp_path: Path) -> Path:
    """A temporary directory pre-structured as a SimpleBrain root."""
    for folder in ["_raw/audio", "_raw/transcripts", "_queue/failed",
                   "_index", "_conflicts/pending", "_meta",
                   "knowledge/_unfiled"]:
        (tmp_path / folder).mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def config(brain_dir: Path) -> BrainConfig:
    return BrainConfig(brain_root=brain_dir, user="testuser", device="test")
