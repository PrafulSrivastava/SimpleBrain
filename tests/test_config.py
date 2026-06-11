# tests/test_config.py
from pathlib import Path
from simplebrain.config import BrainConfig


def test_config_creates_directories(brain_dir):
    config = BrainConfig(brain_root=brain_dir, user="alice", device="mac")
    assert (brain_dir / "_raw" / "audio").exists()
    assert (brain_dir / "_queue").exists()
    assert (brain_dir / "knowledge").exists()


def test_config_paths(brain_dir):
    config = BrainConfig(brain_root=brain_dir, user="alice", device="mac")
    assert config.queue_dir == brain_dir / "_queue"
    assert config.raw_audio_dir == brain_dir / "_raw" / "audio"
    assert config.raw_transcripts_dir == brain_dir / "_raw" / "transcripts"
    assert config.knowledge_dir == brain_dir / "knowledge"
    assert config.index_dir == brain_dir / "_index"
    assert config.conflicts_dir == brain_dir / "_conflicts"
    assert config.meta_dir == brain_dir / "_meta"
