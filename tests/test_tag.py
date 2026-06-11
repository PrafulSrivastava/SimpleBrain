# tests/test_tag.py
from unittest.mock import patch
from simplebrain.pipeline.tag import TagStage
from simplebrain.models import Chunk


def _mock_llm(content):
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_tag_extracts_tags(config):
    chunk = Chunk(content="MCP is a protocol for AI tools.",
                  source_raw="test.txt", user="alice")
    mock_response = _mock_llm('["#mcp", "#ai", "#protocol"]')
    with patch("simplebrain.pipeline.tag.litellm.completion",
               return_value=mock_response):
        stage = TagStage(config)
        result = stage.run(chunk)
    assert "#mcp" in result.tags
    assert "#ai" in result.tags


def test_tag_handles_malformed_llm_response(config):
    chunk = Chunk(content="Some content.", source_raw="test.txt", user="alice")
    mock_response = _mock_llm("not valid json")
    with patch("simplebrain.pipeline.tag.litellm.completion",
               return_value=mock_response):
        stage = TagStage(config)
        result = stage.run(chunk)
    assert result.tags == []
