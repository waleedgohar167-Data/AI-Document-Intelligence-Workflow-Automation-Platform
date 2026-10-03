import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, DocumentRecord, ProcessingJob
from app.api import documents

client = TestClient(app)

def test_upload_successful_pdf_and_db_records():
    file_content = b"%PDF-1.4 dummy content"
    response = client.post(
        "/documents",
        files={"file": ("test_invoice.pdf", file_content, "application/pdf")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    
    # Verify Document and Job records were created correctly in DB
    db = SessionLocal()
    try:
        doc_record = db.query(DocumentRecord).filter(DocumentRecord.id == data["document_id"]).first()
        assert doc_record is not None
        assert doc_record.status == "pending"
        assert doc_record.original_filename == "test_invoice.pdf"

        job_record = db.query(ProcessingJob).filter(ProcessingJob.document_id == data["document_id"]).first()
        assert job_record is not None
        assert job_record.status == "queued"
    finally:
        db.close()

def test_unsupported_file_type():
    file_content = b"dummy text content"
    response = client.post(
        "/documents",
        files={"file": ("test.txt", file_content, "text/plain")}
    )
    assert response.status_code == 415
    data = response.json()
    assert data["detail"]["error"] == "Unsupported file type"

def test_oversized_file(monkeypatch):
    monkeypatch.setattr(documents, "MAX_FILE_SIZE", 10)
    file_content = b"This is definitively larger than 10 bytes."
    response = client.post(
        "/documents",
        files={"file": ("large.pdf", file_content, "application/pdf")}
    )
    assert response.status_code == 413
    data = response.json()
    assert data["detail"]["error"] == "File too large"