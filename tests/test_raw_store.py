from pathlib import Path
from simplebrain.config import BrainConfig
from simplebrain.store.raw import RawStore


def test_save_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()
    store = RawStore(config)

    content = b"%PDF-1.4 fake pdf content"
    rel_path = store.save_document(content, "report.pdf", "abc12345")

    saved = tmp_path / rel_path
    assert saved.exists()
    assert saved.read_bytes() == content
    assert saved.suffix == ".pdf"
    assert "abc12345" in saved.name
