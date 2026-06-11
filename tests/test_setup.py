import json
from unittest.mock import patch, MagicMock
from simplebrain.setup.wizard import SetupWizard
from simplebrain.config import BrainConfig


def _mock_llm(content):
    mock = MagicMock()
    mock.choices[0].message.content = content
    return mock


def test_setup_saves_config(config):
    answers = {
        "purpose": "My software projects and research notes",
        "users": ["alice"],
        "topics": ["projects", "research", "personal"],
        "healer_schedule": "daily",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    }
    mock_resp = _mock_llm(json.dumps(["projects", "research", "personal", "archive"]))

    with patch("simplebrain.setup.wizard.litellm.completion",
               return_value=mock_resp):
        wizard = SetupWizard(config)
        wizard.run(answers)

    setup_file = config.meta_dir / "setup.json"
    assert setup_file.exists()
    data = json.loads(setup_file.read_text())
    assert data["users"] == ["alice"]


def test_setup_creates_folders(config):
    answers = {
        "purpose": "Personal notes",
        "users": ["alice"],
        "topics": ["journal", "work"],
        "healer_schedule": "weekly",
        "llm_provider": "openai",
        "llm_model": "gpt-4o-mini",
    }
    mock_resp = _mock_llm(json.dumps(["journal", "work", "archive"]))

    with patch("simplebrain.setup.wizard.litellm.completion",
               return_value=mock_resp):
        wizard = SetupWizard(config)
        folders = wizard.run(answers)

    for folder in folders:
        assert (config.knowledge_dir / folder).exists()
