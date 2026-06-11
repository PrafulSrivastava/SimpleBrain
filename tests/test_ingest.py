from pathlib import Path
from simplebrain.ingest.service import IngestService
from simplebrain.models import JobType, JobStatus


def test_add_text_note_returns_job_id(config):
    svc = IngestService(config)
    job_id = svc.add_text_note("Hello world", user="alice", device="mac")
    assert isinstance(job_id, str)
    assert len(job_id) > 0


def test_add_text_note_saves_to_raw(config):
    svc = IngestService(config)
    svc.add_text_note("Hello world", user="alice", device="mac")
    files = list(config.raw_transcripts_dir.glob("*.txt"))
    assert len(files) == 1
    assert files[0].read_text() == "Hello world"


def test_add_text_note_enqueues_job(config):
    svc = IngestService(config)
    svc.add_text_note("Hello world", user="alice", device="mac")
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    job = q.dequeue()
    assert job is not None
    assert job.type == JobType.TEXT
    assert job.user == "alice"


def test_add_voice_note_saves_audio(config):
    svc = IngestService(config)
    fake_audio = b"RIFF....fake audio data"
    job_id = svc.add_voice_note(fake_audio, filename="test.wav",
                                 user="alice", device="iphone")
    audio_files = list(config.raw_audio_dir.glob("*.wav"))
    assert len(audio_files) == 1


def test_add_voice_note_enqueues_job(config):
    svc = IngestService(config)
    fake_audio = b"RIFF....fake audio data"
    svc.add_voice_note(fake_audio, filename="test.wav",
                       user="alice", device="iphone")
    from simplebrain.ingest.queue import FileQueue
    q = FileQueue(config)
    job = q.dequeue()
    assert job is not None
    assert job.type == JobType.VOICE
