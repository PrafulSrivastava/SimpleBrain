from simplebrain.models import JobType, Job


def test_document_job_type_exists():
    assert JobType.DOCUMENT == "document"


def test_create_document_job():
    job = Job(type=JobType.DOCUMENT, user="test")
    assert job.type == JobType.DOCUMENT
    assert job.raw_path is None
