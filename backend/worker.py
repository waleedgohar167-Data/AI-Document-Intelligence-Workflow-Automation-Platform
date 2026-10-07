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
from app.services.extractor import extract_structured_data
from app.services.validator import validate_document
from app.services.confidence import calculate_routing_decision

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
    
    if result.rowcount == 0:
        return None
        
    db.refresh(job)
    sync_document_status(db, job.document_id, JobStatus.PROCESSING.value)
    return job

def persist_result(doc_id: str, data: dict):
    """Point 9 & 10: Persist output idemptotently to disk"""
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
        
        # 1. PARSING STAGE
        if "wordprocessingml" in file_type:
            result = extract_docx(file_path, doc_id)
        else:
            if "image" in file_type:
                log_audit(db, doc_id, "OCR_STARTED")
                
            result = extract_pdf(file_path, doc_id, file_type)
            
            if result["extraction_method"] in ["ocr", "mixed"]:
                log_audit(db, doc_id, "OCR_COMPLETED")

        if not result["blocks"]:
            raise ValueError("Extraction returned empty blocks.")

        persist_result(doc_id, result)
        log_audit(db, doc_id, "PARSING_COMPLETED", f"Method: {result['extraction_method']}")
        
        # 2. CLASSIFICATION STAGE
        current_stage = "CLASSIFICATION"
        log_audit(db, doc_id, "CLASSIFICATION_STARTED")
        
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

        # 3. EXTRACTION STAGE
        if classification.document_type != "unknown":
            current_stage = "EXTRACTION"
            log_audit(db, doc_id, "EXTRACTION_STARTED")
            
            try:
                extracted_dict, missing_fields = extract_structured_data(normalized_doc, classification.document_type)
                
                # Use default=str to serialize Date objects gracefully for the database
                doc_record.extracted_data = json.dumps(extracted_dict, default=str)
                
                for missing_field in missing_fields:
                    log_audit(db, doc_id, "REQUIRED_FIELD_MISSING", f"Field: {missing_field} in {classification.document_type}")
                
                log_audit(db, doc_id, "EXTRACTION_COMPLETED", f"Type: {classification.document_type}")
                
                # 4. MODULE 6: VALIDATION STAGE
                current_stage = "VALIDATION"
                log_audit(db, doc_id, "VALIDATION_STARTED")
                
                val_result = validate_document(classification.document_type, extracted_dict, missing_fields)
                doc_record.validation_results = json.dumps(val_result)
                
                if val_result["passed"]:
                    log_audit(db, doc_id, "VALIDATION_PASSED")
                    final_status = JobStatus.VALIDATED.value
                else:
                    log_audit(db, doc_id, "VALIDATION_FAILED", json.dumps(val_result["failures"]))
                    final_status = JobStatus.VALIDATION_FAILED.value
                
                # 5. MODULE 7: CONFIDENCE & ROUTING STAGE
                current_stage = "CONFIDENCE_ROUTING"
                conf_result = calculate_routing_decision(classification.document_type, classification.confidence, extracted_dict, val_result["passed"])
                
                doc_record.final_confidence_score = conf_result["overall_confidence"]
                
                # Improvement 6: Store config in audit record
                log_audit(db, doc_id, "ROUTING_DECISION_CALCULATED", json.dumps(conf_result))
                
                if conf_result["decision"] == "NEEDS_REVIEW":
                    doc_record.requires_human_review = True
                    final_status = JobStatus.NEEDS_REVIEW.value
                    log_audit(db, doc_id, "HUMAN_REVIEW_REQUIRED", json.dumps({"reasons": conf_result["decision_reasons"]}))
                else:
                    final_status = JobStatus.APPROVED.value
                    log_audit(db, doc_id, "AUTO_APPROVED", f"Score: {conf_result['overall_confidence']}")

            except Exception as extract_err:
                raise Exception(f"{extract_err}")

        # Finalize processing job
        job.status = final_status
        job.completed_at = datetime.datetime.utcnow()
        doc_record.status = final_status
        db.commit()
        print(f"Successfully processed document {doc_id} to status: {final_status}")
        
    except Exception as e:
        job.status = JobStatus.FAILED.value
        job.failed_at = datetime.datetime.utcnow()
        job.failure_reason = str(e)
        
        if 'doc_record' in locals() and doc_record:
            doc_record.status = JobStatus.FAILED.value
            
        db.commit()
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