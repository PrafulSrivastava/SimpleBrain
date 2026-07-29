# tests/test_worker_docling.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType
from simplebrain.ingest.queue import FileQueue
from simplebrain.pipeline.worker import BackgroundWorker


def test_worker_processes_document_job(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()

    # Setup: structure.json needed by FileStage
    meta = config.meta_dir / "structure.json"
    meta.write_text('{"folders": [{"name": "general", "description": "General"}], "pending_proposals": []}')
    setup = config.meta_dir / "setup.json"
    setup.write_text('{"summary": "test brain", "healer_schedule": "manual"}')

    # Queue a document job
    doc_path = config.raw_documents_dir / "20260728T120000-testdoc1.pdf"
    doc_path.write_bytes(b"fake pdf")
    job = Job(type=JobType.DOCUMENT, user="test", id="testdoc1")
    job.raw_path = str(doc_path.relative_to(tmp_path))
    queue = FileQueue(config)
    queue.enqueue(job)

    # Mock Docling and LLM calls
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Report\n\nImportant findings about testing."
    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    mock_llm_responses = [
        # ChunkStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='["Important findings about testing."]'))]),
        # TagStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"title": "Testing Report", "tags": ["#testing", "#report"]}'))]),
        # FileStage response
        MagicMock(choices=[MagicMock(message=MagicMock(content='{"folder": "general", "is_new": false, "reasoning": "fits general"}'))]),
    ]

    with patch("simplebrain.pipeline.docling_stage.DocumentConverter", return_value=mock_converter):
        with patch("litellm.completion", side_effect=mock_llm_responses):
            worker = BackgroundWorker(config)
            result = worker.process_one()

    assert result is True
    # Verify chunk was written
    knowledge_files = list(config.knowledge_dir.rglob("*.md"))
    readme_files = [f for f in knowledge_files if f.name == "README.md"]
    chunk_files = [f for f in knowledge_files if f.name != "README.md"]
    assert len(chunk_files) >= 1
