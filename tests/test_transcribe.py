from unittest.mock import patch, MagicMock
from simplebrain.pipeline.transcribe import TranscribeStage
from simplebrain.models import Job, JobType


def test_transcribe_skipped_for_text(config):
    stage = TranscribeStage(config)
    job = Job(type=JobType.TEXT, user="alice",
              raw_path="_raw/transcripts/test.txt")
    result = stage.run(job)
    assert result.transcript_path == job.raw_path


def test_transcribe_voice_calls_whisper(config, tmp_path):
    # Write a fake audio file
    audio_path = config.raw_audio_dir / "test.wav"
    audio_path.write_bytes(b"fake")
    job = Job(type=JobType.VOICE, user="alice",
              raw_path=str(audio_path.relative_to(config.brain_root)))

    mock_segment = MagicMock()
    mock_segment.text = " Hello world"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], None)

    with patch("simplebrain.pipeline.transcribe.WhisperModel",
               return_value=mock_model):
        stage = TranscribeStage(config)
        result = stage.run(job)

    assert result.transcript_path is not None
    transcript_file = config.brain_root / result.transcript_path
    assert transcript_file.exists()
    assert "Hello world" in transcript_file.read_text()
