import json
from simplebrain.ingest.queue import FileQueue
from simplebrain.models import Job, JobType, JobStatus


def test_enqueue_creates_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="_raw/transcripts/x.txt")
    q.enqueue(job)
    files = list(config.queue_dir.glob("*.json"))
    assert len(files) == 1
    data = json.loads(files[0].read_text())
    assert data["id"] == job.id


def test_dequeue_returns_oldest_job(config):
    q = FileQueue(config)
    job1 = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    job2 = Job(type=JobType.TEXT, user="alice", raw_path="b.txt")
    q.enqueue(job1)
    q.enqueue(job2)
    result = q.dequeue()
    assert result is not None
    assert result.id == job1.id


def test_dequeue_empty_returns_none(config):
    q = FileQueue(config)
    assert q.dequeue() is None


def test_mark_failed_moves_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    q.enqueue(job)
    q.mark_failed(job, error="boom")
    assert len(list(config.queue_dir.glob("*.json"))) == 0
    failed = list((config.queue_dir / "failed").glob("*.json"))
    assert len(failed) == 1


def test_complete_removes_file(config):
    q = FileQueue(config)
    job = Job(type=JobType.TEXT, user="alice", raw_path="a.txt")
    q.enqueue(job)
    q.complete(job)
    assert len(list(config.queue_dir.glob("*.json"))) == 0
