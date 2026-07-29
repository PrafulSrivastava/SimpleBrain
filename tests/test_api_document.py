import base64
from fastapi.testclient import TestClient
from simplebrain.config import BrainConfig
from simplebrain.api.routes import create_app


def test_post_document(tmp_path):
    config = BrainConfig(brain_root=tmp_path, user="test")
    config.init_dirs()
    (config.meta_dir / "structure.json").write_text(
        '{"folders": [], "pending_proposals": []}'
    )

    app = create_app(config)
    client = TestClient(app)

    pdf_content = b"%PDF-1.4 test content"
    b64 = base64.b64encode(pdf_content).decode()

    resp = client.post("/notes/document", json={
        "file_b64": b64,
        "filename": "test.pdf",
        "user": "testuser",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data

    # Verify file was saved
    docs = list(config.raw_documents_dir.glob("*"))
    assert len(docs) == 1
    assert docs[0].read_bytes() == pdf_content
