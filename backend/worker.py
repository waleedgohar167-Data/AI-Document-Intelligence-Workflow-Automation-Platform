import time
import uuid
import json
import os
import datetime
from sqlalchemy import update
from app.core.database import SessionLocal, ProcessingJob, DocumentRecord, AuditEvent, JobStatus
from app.services.parser import extract_pdf, extract_docx
from app.schemas.classification import NormalizedDocument
from app.services.classifier import classify_document, CONFIDENCE_THRESHOLD

STORAGE_PARSED_DIR = "storage/parsed"
os.makedirs(STORAGE_PARSED_DIR, exist_ok=True)

def log_audit(db, doc_id, event_name, details=""):
    event = AuditEvent(id=str(uuid.uuid4()), document_id=doc_id, event_name=event_name, details=details)
    db.add(event)
    db.commit()

def sync_document_status(db, doc_id, status):
    """Point 3: Ensure Document and Job status are perfectly synced"""
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    if doc:
        doc.status = status
        db.commit()

def claim_next_job(db):
    """Point 1 & 14: Atomic Processing Job Claiming"""
    # SQLite atomic lock simulation using UPDATE rowcount
    now = datetime.datetime.utcnow()
    job = db.query(ProcessingJob).filter(ProcessingJob.status == JobStatus.QUEUED.value).first()
    
    if not job:
        return None

    stmt = (
        update(ProcessingJob)
        .where(ProcessingJob.id == job.id, ProcessingJob.status == JobStatus.QUEUED.value)
        .values(status=JobStatus.PROCESSING.value, started_at=now)
    )
    result = db.execute(stmt)
    db.commit()
    
    # If rowcount is 0, another worker grabbed it first
    if result.rowcount == 0:
        return None
        
    db.refresh(job)
    sync_document_status(db, job.document_id, JobStatus.PROCESSING.value)
    return job

def persist_result(doc_id: str, data: dict):
    """Point 9 & 10: Persist output idemptotently to disk for Day 4"""
    file_path = os.path.join(STORAGE_PARSED_DIR, f"{doc_id}.json")
    with open(file_path, "w") as f:
        json.dump(data, f, indent=2)

def process_job(db, job):
    doc_id = job.document_id
    current_stage = "PARSING"
    log_audit(db, doc_id, "PARSING_STARTED")
    
    try:
        doc_record = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
        if not doc_record or not os.path.exists(doc_record.storage_reference):
            raise FileNotFoundError("Source file not found on disk.")
            
        file_path = doc_record.storage_reference
        file_type = doc_record.file_type
        
        # Point 12: Accurate sequence of events
        if "wordprocessingml" in file_type:
            result = extract_docx(file_path, doc_id)
        else:
            if "image" in file_type:
                log_audit(db, doc_id, "OCR_STARTED")
                
            result = extract_pdf(file_path, doc_id, file_type)
            
            if result["extraction_method"] in ["ocr", "mixed"]:
                log_audit(db, doc_id, "OCR_COMPLETED")

        # Empty result failure check (Point 11)
        if not result["blocks"]:
            raise ValueError("Extraction returned empty blocks.")

        persist_result(doc_id, result)
        log_audit(db, doc_id, "PARSING_COMPLETED", f"Method: {result['extraction_method']}")
        
        # --- NEW DAY 4 CLASSIFICATION STAGE ---
        current_stage = "CLASSIFICATION"
        log_audit(db, doc_id, "CLASSIFICATION_STARTED")
        
        # Validate through Pydantic
        normalized_doc = NormalizedDocument(**result)
        classification = classify_document(normalized_doc)
        
        doc_record.document_type = classification.document_type
        doc_record.confidence_score = classification.confidence
        
        if classification.confidence < CONFIDENCE_THRESHOLD:
            doc_record.requires_human_review = True
            final_status = JobStatus.NEEDS_REVIEW.value
            log_audit(db, doc_id, "CLASSIFICATION_UNCERTAIN", f"Score: {classification.confidence}. Reason: {classification.reasoning}")
        else:
            final_status = JobStatus.CLASSIFIED.value
            log_audit(db, doc_id, "DOCUMENT_CLASSIFIED", f"Type: {classification.document_type}, Score: {classification.confidence}")

        # Finalize processing job
        job.status = final_status
        job.completed_at = datetime.datetime.utcnow()
        doc_record.status = final_status
        db.commit()
        print(f"Successfully processed and classified document {doc_id} as {classification.document_type}")
        
    except Exception as e:
        job.status = JobStatus.FAILED.value
        job.failed_at = datetime.datetime.utcnow()
        job.failure_reason = str(e)
        
        # Ensure doc_record exists before attempting to update it in the exception block
        if 'doc_record' in locals() and doc_record:
            doc_record.status = JobStatus.FAILED.value
            
        db.commit()
        
        # Log failure based on which stage the error occurred in
        log_audit(db, doc_id, f"{current_stage}_FAILED", str(e))
        print(f"Failed {current_stage.lower()} document {doc_id}: {e}")

def run_worker():
    print("Worker loop started...")
    while True:
        db = SessionLocal()
        try:
            job = claim_next_job(db)
            if job:
                process_job(db, job)
        finally:
            db.close()
        time.sleep(3)

if __name__ == "__main__":
    run_worker()