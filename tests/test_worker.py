import json
from unittest.mock import patch, MagicMock
from simplebrain.pipeline.worker import BackgroundWorker
from simplebrain.ingest.service import IngestService
from simplebrain.models import JobStatus, JobType


def _mock_llm_chunk(text):
    mock = MagicMock()
    mock.choices[0].message.content = json.dumps([text])
    return mock


def _mock_llm_tag():
    mock = MagicMock()
    mock.choices[0].message.content = '["#test"]'
    return mock


def _mock_llm_file():
    mock = MagicMock()
    mock.choices[0].message.content = '{"folder": "general", "is_new": false}'
    return mock


def test_worker_processes_text_job(config):
    (config.knowledge_dir / "general").mkdir()
    (config.meta_dir / "structure.json").write_text(
        json.dumps({"folders": ["general"]})
    )

    svc = IngestService(config)
    job_id = svc.add_text_note("Hello MCP world.", user="alice", device="mac")

    def mock_completion(model, messages, **kwargs):
        content = messages[0]["content"]
        if "chunker" in content:
            return _mock_llm_chunk("Hello MCP world.")
        elif "Extract tags" in content:
            return _mock_llm_tag()
        else:
            return _mock_llm_file()

    with patch("simplebrain.pipeline.chunk.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.tag.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.file.litellm.completion", side_effect=mock_completion):
        worker = BackgroundWorker(config)
        worker.process_one()

    # Queue should be empty
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    assert q.dequeue() is None

    # A chunk file should exist
    chunks = list(config.knowledge_dir.rglob("*.md"))
    non_unfiled = [c for c in chunks if "_unfiled" not in str(c)]
    assert len(non_unfiled) >= 1


def test_worker_returns_false_when_queue_empty(config):
    worker = BackgroundWorker(config)
    result = worker.process_one()
    assert result is False


def test_worker_marks_failed_on_exception(config):
    svc = IngestService(config)
    job_id = svc.add_text_note("Some note.", user="alice", device="mac")

    with patch("simplebrain.pipeline.transcribe.TranscribeStage.run",
               side_effect=RuntimeError("transcribe boom")):
        worker = BackgroundWorker(config)
        result = worker.process_one()

    assert result is False

    # Job should be in failed queue
    failed = list((config.queue_dir / "failed").glob("*.json"))
    assert len(failed) == 1


def test_worker_processes_multiple_jobs(config):
    (config.knowledge_dir / "general").mkdir()
    (config.meta_dir / "structure.json").write_text(
        json.dumps({"folders": ["general"]})
    )

    svc = IngestService(config)
    svc.add_text_note("Note one.", user="alice", device="mac")
    svc.add_text_note("Note two.", user="alice", device="mac")

    def mock_completion(model, messages, **kwargs):
        content = messages[0]["content"]
        if "chunker" in content:
            mock = MagicMock()
            mock.choices[0].message.content = '["A note."]'
            return mock
        elif "Extract tags" in content:
            return _mock_llm_tag()
        else:
            return _mock_llm_file()

    with patch("simplebrain.pipeline.chunk.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.tag.litellm.completion", side_effect=mock_completion), \
         patch("simplebrain.pipeline.file.litellm.completion", side_effect=mock_completion):
        worker = BackgroundWorker(config)
        r1 = worker.process_one()
        r2 = worker.process_one()
        r3 = worker.process_one()

    assert r1 is True
    assert r2 is True
    assert r3 is False  # Queue exhausted
