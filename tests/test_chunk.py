# tests/test_chunk.py
from unittest.mock import patch
from simplebrain.pipeline.chunk import ChunkStage
from simplebrain.models import Job, JobType, Chunk


def _mock_llm(content):
    """Returns a mock litellm completion with given content."""
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_chunk_single_small_note(config):
    # Write a small transcript
    transcript = config.raw_transcripts_dir / "test.txt"
    transcript.write_text("Today I learned about MCP servers.")
    job = Job(type=JobType.TEXT, user="alice", device="mac",
              raw_path="", transcript_path=str(transcript.relative_to(config.brain_root)))

    mock_response = _mock_llm('["Today I learned about MCP servers."]')
    with patch("simplebrain.pipeline.chunk.litellm.completion",
               return_value=mock_response):
        stage = ChunkStage(config)
        chunks = stage.run(job)

    assert len(chunks) == 1
    assert chunks[0].content == "Today I learned about MCP servers."
    assert chunks[0].user == "alice"
    assert chunks[0].device == "mac"


def test_chunk_large_note_creates_parent_links(config):
    transcript = config.raw_transcripts_dir / "large.txt"
    transcript.write_text("Note about MCP. Note about chunking.")
    job = Job(type=JobType.TEXT, user="alice", device="mac",
              raw_path="", transcript_path=str(transcript.relative_to(config.brain_root)))

    mock_response = _mock_llm('["Note about MCP.", "Note about chunking."]')
    with patch("simplebrain.pipeline.chunk.litellm.completion",
               return_value=mock_response):
        stage = ChunkStage(config)
        chunks = stage.run(job)

    assert len(chunks) == 2
    assert all(c.parent == chunks[0].parent for c in chunks)
