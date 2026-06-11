import json
from unittest.mock import patch, MagicMock
from simplebrain.pipeline.file import FileStage
from simplebrain.models import Chunk, FolderProposalStatus


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_file_to_existing_folder(config):
    # Create existing folder structure
    (config.knowledge_dir / "projects").mkdir()
    structure = {"folders": ["projects", "research"]}
    (config.meta_dir / "structure.json").write_text(json.dumps(structure))

    chunk = Chunk(content="Working on MCP server.", source_raw="t.txt",
                  tags=["#mcp"], user="alice")
    mock_resp = _mock_llm('{"folder": "projects", "is_new": false}')

    with patch("simplebrain.pipeline.file.litellm.completion",
               return_value=mock_resp):
        stage = FileStage(config)
        filed_chunk, proposal = stage.run(chunk)

    assert filed_chunk.file_path is not None
    assert "projects" in filed_chunk.file_path
    assert proposal is None


def test_file_creates_proposal_for_new_folder(config):
    structure = {"folders": ["projects"]}
    (config.meta_dir / "structure.json").write_text(json.dumps(structure))

    chunk = Chunk(content="Cooking recipe for pasta.", source_raw="t.txt",
                  tags=["#cooking"], user="alice")
    mock_resp = _mock_llm('{"folder": "cooking", "is_new": true, "reasoning": "No food folder exists"}')

    with patch("simplebrain.pipeline.file.litellm.completion",
               return_value=mock_resp):
        stage = FileStage(config)
        filed_chunk, proposal = stage.run(chunk)

    assert proposal is not None
    assert proposal.proposed_folder == "cooking"
    assert proposal.status == FolderProposalStatus.PENDING
    assert filed_chunk.file_path is not None
    assert "_unfiled" in filed_chunk.file_path
