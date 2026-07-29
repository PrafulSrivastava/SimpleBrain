# tests/test_docling_stage.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from simplebrain.config import BrainConfig
from simplebrain.models import Job, JobType
from simplebrain.pipeline.docling_stage import DoclingStage


def test_docling_stage_converts_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()

    # Write a fake document
    doc_path = config.raw_documents_dir / "20260728T120000-abc12345.pdf"
    doc_path.write_bytes(b"%PDF-1.4 fake content")

    job = Job(type=JobType.DOCUMENT, user="test", id="abc12345")
    job.raw_path = str(doc_path.relative_to(tmp_path))

    # Mock docling to avoid needing real PDF parsing in tests
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = "# Extracted Title\n\nSome content from the PDF."

    mock_result = MagicMock()
    mock_result.document = mock_doc

    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result

    with patch("simplebrain.pipeline.docling_stage.DocumentConverter", return_value=mock_converter):
        stage = DoclingStage(config)
        result = stage.run(job)

    assert result.transcript_path is not None
    transcript = (tmp_path / result.transcript_path).read_text(encoding="utf-8")
    assert "Extracted Title" in transcript
    assert "Some content from the PDF" in transcript
