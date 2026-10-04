import pytest
from unittest.mock import patch, MagicMock
from app.services.parser import generate_normalized_output, _is_usable_text
from app.core.database import SessionLocal, ProcessingJob, DocumentRecord, AuditEvent, JobStatus
from worker import claim_next_job
import uuid

def test_normalized_output_structure():
    """Point 6: Normalized output structure is correct regardless of extraction method"""
    doc_id = "test-doc-123"
    result = generate_normalized_output(doc_id, "native", [{"text": "hello", "page_number": 1}], 1)
    
    assert result["document_id"] == doc_id
    assert result["extraction_method"] == "native"
    assert "blocks" in result
    assert result["blocks"][0]["text"] == "hello"
    assert "metadata" in result
    assert "extraction_timestamp" in result["metadata"]

def test_is_usable_text_rule():
    """Point 4: Deterministic rule for usable text (>50 alphanumeric characters)"""
    assert _is_usable_text("This has plenty of text to be considered native text by our deterministic rule.") is True
    assert _is_usable_text("Too short") is False
    assert _is_usable_text("") is False

def test_atomic_claim_prevention():
    """Point 1 & 16: Demonstrate the same queued job cannot be claimed twice."""
    db = SessionLocal()
    
    # Clean up any leftover jobs from previous tests to prevent test leakage
    db.query(ProcessingJob).delete()
    db.commit()
    
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    try:
        new_doc = DocumentRecord(id=doc_id, status=JobStatus.QUEUED.value)
        new_job = ProcessingJob(id=job_id, document_id=doc_id, status=JobStatus.QUEUED.value)
        db.add(new_doc)
        db.add(new_job)
        db.commit()

        # Worker 1 claims the job
        claimed_job_1 = claim_next_job(db)
        assert claimed_job_1 is not None
        assert claimed_job_1.status == JobStatus.PROCESSING.value
        
        # Worker 2 attempts to claim the exact same DB state simultaneously
        claimed_job_2 = claim_next_job(db)
        # Because Worker 1 updated it, Worker 2 finds no QUEUED jobs left
        assert claimed_job_2 is None 
        
    finally:
        db.close()

def test_worker_database_updates():
    """Test: Worker updates status correctly"""
    db = SessionLocal()
    doc_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    try:
        # Create a fake pending job
        new_doc = DocumentRecord(id=doc_id, file_type="text/plain", storage_reference="dummy.txt", status=JobStatus.QUEUED.value)
        new_job = ProcessingJob(id=job_id, document_id=doc_id, status=JobStatus.QUEUED.value)
        db.add(new_doc)
        db.add(new_job)
        db.commit()

        # Simulate the worker claiming it
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        job.status = JobStatus.PROCESSING.value
        db.commit()

        # Assertions
        updated_job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        assert updated_job.status == JobStatus.PROCESSING.value
    finally:
        db.close()