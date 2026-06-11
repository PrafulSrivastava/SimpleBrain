# tests/test_mcp.py
import json
import pytest
from simplebrain.mcp.server import create_mcp_server
from simplebrain.config import BrainConfig


def test_mcp_server_has_expected_tools(config):
    server = create_mcp_server(config)
    tool_names = [t.name for t in server.list_tools()]
    expected = [
        "add_text_note", "add_voice_note", "job_status",
        "search", "get_chunk", "list_topics", "list_tags",
        "list_pending_folder_proposals", "confirm_folder_proposal",
        "reject_folder_proposal", "list_conflicts", "resolve_conflict",
        "revert_resolution", "run_healer", "get_brain_status",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_mcp_add_text_note_returns_job_id(config):
    server = create_mcp_server(config)
    result = server.call_tool("add_text_note", {
        "text": "Hello brain", "user": "alice", "device": "mac"
    })
    data = json.loads(result[0].text)
    assert "job_id" in data


def test_mcp_add_voice_note_returns_job_id(config):
    import base64
    server = create_mcp_server(config)
    fake_audio = base64.b64encode(b"fake audio data").decode()
    result = server.call_tool("add_voice_note", {
        "audio_b64": fake_audio,
        "filename": "test.wav",
        "user": "alice",
        "device": "iphone",
    })
    data = json.loads(result[0].text)
    assert "job_id" in data


def test_mcp_job_status_pending(config):
    server = create_mcp_server(config)
    result_add = server.call_tool("add_text_note", {
        "text": "Status test", "user": "alice"
    })
    job_id = json.loads(result_add[0].text)["job_id"]

    result_status = server.call_tool("job_status", {"job_id": job_id})
    data = json.loads(result_status[0].text)
    assert data["job_id"] == job_id
    assert data["status"] == "pending"


def test_mcp_job_status_not_found(config):
    server = create_mcp_server(config)
    result = server.call_tool("job_status", {"job_id": "nonexistent"})
    data = json.loads(result[0].text)
    assert data["status"] == "complete_or_not_found"


def test_mcp_search_empty(config):
    server = create_mcp_server(config)
    result = server.call_tool("search", {"query": "nothing here"})
    data = json.loads(result[0].text)
    assert "results" in data
    assert data["results"] == []


def test_mcp_search_with_tags(config):
    server = create_mcp_server(config)
    result = server.call_tool("search", {"query": "mcp", "tags": ["#mcp"]})
    data = json.loads(result[0].text)
    assert "results" in data


def test_mcp_get_chunk_not_found(config):
    server = create_mcp_server(config)
    result = server.call_tool("get_chunk", {"chunk_id": "badid"})
    data = json.loads(result[0].text)
    assert "error" in data


def test_mcp_get_chunk_existing(config):
    from simplebrain.store.knowledge import KnowledgeStore
    from simplebrain.models import Chunk

    ks = KnowledgeStore(config)
    (config.knowledge_dir / "projects").mkdir(exist_ok=True)
    chunk = Chunk(
        content="MCP is a protocol.",
        source_raw="test.txt",
        tags=["#mcp"],
        user="alice",
    )
    ks.write(chunk, "projects")

    server = create_mcp_server(config)
    result = server.call_tool("get_chunk", {"chunk_id": chunk.id})
    data = json.loads(result[0].text)
    assert data["id"] == chunk.id
    assert data["content"] == "MCP is a protocol."
    assert "#mcp" in data["tags"]


def test_mcp_list_topics_and_tags(config):
    server = create_mcp_server(config)

    result_topics = server.call_tool("list_topics", {})
    data_topics = json.loads(result_topics[0].text)
    assert "topics" in data_topics

    result_tags = server.call_tool("list_tags", {})
    data_tags = json.loads(result_tags[0].text)
    assert "tags" in data_tags


def test_mcp_list_topics_populated(config):
    from simplebrain.store.knowledge import KnowledgeStore
    from simplebrain.store.index import IndexStore
    from simplebrain.models import Chunk

    ks = KnowledgeStore(config)
    idx = IndexStore(config)
    (config.knowledge_dir / "projects").mkdir(exist_ok=True)
    chunk = Chunk(content="A note.", source_raw="t.txt", tags=["#mcp"], user="alice")
    path = ks.write(chunk, "projects")
    idx.update(chunk, path)

    server = create_mcp_server(config)
    result = server.call_tool("list_topics", {})
    data = json.loads(result[0].text)
    assert "projects" in data["topics"]
    assert data["topics"]["projects"] == 1


def test_mcp_list_pending_folder_proposals_empty(config):
    server = create_mcp_server(config)
    result = server.call_tool("list_pending_folder_proposals", {})
    data = json.loads(result[0].text)
    assert data["proposals"] == []


def test_mcp_confirm_folder_proposal(config):
    from simplebrain.brain.grower import SelfGrower
    grower = SelfGrower(config)
    proposal = grower.create_proposal("cooking", "Food content detected", "chunk1")

    server = create_mcp_server(config)
    result = server.call_tool("confirm_folder_proposal", {
        "proposal_id": proposal.id
    })
    data = json.loads(result[0].text)
    assert data["confirmed"] is True
    assert data["folder"] == "cooking"


def test_mcp_reject_folder_proposal(config):
    from simplebrain.brain.grower import SelfGrower
    grower = SelfGrower(config)
    proposal = grower.create_proposal("cooking", "Food content detected", "chunk1")

    server = create_mcp_server(config)
    result = server.call_tool("reject_folder_proposal", {
        "proposal_id": proposal.id,
        "target_folder": "general",
    })
    data = json.loads(result[0].text)
    assert data["rejected"] is True


def test_mcp_list_conflicts_empty(config):
    server = create_mcp_server(config)
    result = server.call_tool("list_conflicts", {})
    data = json.loads(result[0].text)
    assert data["conflicts"] == []


def test_mcp_resolve_conflict(config):
    from simplebrain.brain.healer import SelfHealer
    from simplebrain.models import Conflict, ConflictType

    healer = SelfHealer(config)
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=["c1", "c2"],
        summary="Test conflict",
        snapshot={"chunks": {"c1": "v1", "c2": "v2"}},
    )
    healer._save_pending(conflict)

    server = create_mcp_server(config)
    result = server.call_tool("resolve_conflict", {
        "conflict_id": conflict.id,
        "resolution": "keep_newer",
        "resolved_by": "alice",
    })
    data = json.loads(result[0].text)
    assert data["resolved"] is True


def test_mcp_revert_resolution(config):
    from simplebrain.brain.healer import SelfHealer
    from simplebrain.models import Conflict, ConflictType, Resolution

    healer = SelfHealer(config)
    conflict = Conflict(
        type=ConflictType.FACTUAL,
        chunks_involved=["c1"],
        summary="Test",
        snapshot={"chunks": {}},
    )
    healer._save_pending(conflict)
    healer.resolve(conflict.id, Resolution.KEEP_NEWER, "alice")

    server = create_mcp_server(config)
    result = server.call_tool("revert_resolution", {
        "conflict_id": conflict.id
    })
    data = json.loads(result[0].text)
    assert data["reverted"] is True


def test_mcp_get_brain_status(config):
    server = create_mcp_server(config)
    result = server.call_tool("get_brain_status", {})
    data = json.loads(result[0].text)
    assert "queue_depth" in data
    assert "pending_conflicts" in data
    assert "pending_proposals" in data
    assert data["queue_depth"] == 0


def test_mcp_get_brain_status_with_queued_job(config):
    server = create_mcp_server(config)
    # Add a note to increment queue depth
    server.call_tool("add_text_note", {"text": "Queue test", "user": "alice"})

    result = server.call_tool("get_brain_status", {})
    data = json.loads(result[0].text)
    assert data["queue_depth"] == 1


def test_mcp_unknown_tool(config):
    server = create_mcp_server(config)
    result = server.call_tool("nonexistent_tool", {})
    data = json.loads(result[0].text)
    assert "error" in data
    assert "nonexistent_tool" in data["error"]
