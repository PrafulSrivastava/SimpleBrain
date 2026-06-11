# tests/test_healer.py
import json
from unittest.mock import patch, MagicMock
from simplebrain.brain.healer import SelfHealer
from simplebrain.store.knowledge import KnowledgeStore
from simplebrain.models import Chunk, ConflictType, ConflictStatus, Resolution


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_healer_detects_factual_conflict(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="MCP uses HTTP transport.", source_raw="t.txt",
               tags=["#mcp"], user="alice")
    c2 = Chunk(content="MCP does not use HTTP transport.", source_raw="t.txt",
               tags=["#mcp"], user="alice")
    ks.write(c1, "projects")
    ks.write(c2, "projects")

    conflict_response = json.dumps([{
        "type": "factual_conflict",
        "chunks_involved": [c1.id, c2.id],
        "summary": "Contradiction about MCP transport"
    }])
    mock_resp = _mock_llm(conflict_response)

    with patch("simplebrain.brain.healer.litellm.completion",
               return_value=mock_resp):
        healer = SelfHealer(config)
        conflicts = healer.scan()

    assert len(conflicts) == 1
    assert conflicts[0].type == ConflictType.FACTUAL


def test_healer_resolve_and_log(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="Version A.", source_raw="t.txt",
               tags=["#test"], user="alice")
    c2 = Chunk(content="Version B.", source_raw="t.txt",
               tags=["#test"], user="alice")
    ks.write(c1, "projects")
    ks.write(c2, "projects")

    healer = SelfHealer(config)
    from simplebrain.models import Conflict, ConflictType
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=[c1.id, c2.id],
        summary="Test conflict",
        snapshot={"chunks": {c1.id: c1.content, c2.id: c2.content}}
    )
    healer._save_pending(conflict)
    healer.resolve(conflict.id, Resolution.KEEP_NEWER, resolved_by="alice")

    log = healer.load_resolution_log()
    assert any(e["id"] == conflict.id for e in log)


def test_healer_revert(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir()
    c1 = Chunk(content="Original content.", source_raw="t.txt",
               tags=["#test"], user="alice")
    ks.write(c1, "projects")

    healer = SelfHealer(config)
    from simplebrain.models import Conflict, ConflictType
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=[c1.id],
        summary="Test",
        snapshot={"chunks": {c1.id: "Original content."}}
    )
    healer._save_pending(conflict)
    healer.resolve(conflict.id, Resolution.KEEP_NEWER, resolved_by="alice")
    healer.revert(conflict.id, knowledge_store=ks)

    log = healer.load_resolution_log()
    entry = next(e for e in log if e["id"] == conflict.id)
    assert entry["status"] == ConflictStatus.REVERTED


def test_healer_list_pending(config):
    healer = SelfHealer(config)
    from simplebrain.models import Conflict, ConflictType
    c = Conflict(
        type=ConflictType.STRUCTURAL,
        chunks_involved=["abc", "def"],
        summary="Duplicate chunks"
    )
    healer._save_pending(c)

    pending = healer.list_pending()
    assert any(p.id == c.id for p in pending)


def test_healer_scan_no_conflicts(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "notes").mkdir()
    c1 = Chunk(content="Cats are mammals.", source_raw="t.txt",
               tags=["#animals"], user="alice")
    c2 = Chunk(content="Dogs are also mammals.", source_raw="t.txt",
               tags=["#animals"], user="alice")
    ks.write(c1, "notes")
    ks.write(c2, "notes")

    with patch("simplebrain.brain.healer.litellm.completion",
               return_value=_mock_llm("[]")):
        healer = SelfHealer(config)
        conflicts = healer.scan()

    assert conflicts == []


def test_healer_scan_handles_malformed_llm_response(config):
    ks = KnowledgeStore(config)
    (config.knowledge_dir / "misc").mkdir()
    c1 = Chunk(content="Note A.", source_raw="t.txt", tags=["#x"], user="alice")
    c2 = Chunk(content="Note B.", source_raw="t.txt", tags=["#x"], user="alice")
    ks.write(c1, "misc")
    ks.write(c2, "misc")

    with patch("simplebrain.brain.healer.litellm.completion",
               return_value=_mock_llm("not valid json at all")):
        healer = SelfHealer(config)
        conflicts = healer.scan()

    # Should gracefully return empty list on parse failure
    assert conflicts == []
