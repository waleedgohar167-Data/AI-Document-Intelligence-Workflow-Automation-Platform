from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, DocumentRecord, JobStatus, AuditEvent
from pydantic import BaseModel
import json, uuid, datetime

router = APIRouter(prefix="/review", tags=["Human Review"])

class RejectRequest(BaseModel):
    reason: str
    reviewer_id: str

class FieldPatchRequest(BaseModel):
    field_name: str
    corrected_value: str
    reviewer_id: str

def log_audit(db, doc_id, event_name, details=""):
    db.add(AuditEvent(id=str(uuid.uuid4()), document_id=doc_id, event_name=event_name, details=details))

@router.get("/queue")
def get_review_queue(db: Session = Depends(get_db)):
    docs = db.query(DocumentRecord).filter(DocumentRecord.status == JobStatus.NEEDS_REVIEW.value).all()
    return [{"id": d.id, "type": d.document_type, "confidence": d.final_confidence_score} for d in docs]

@router.get("/queue/{document_id}")
def get_document_for_review(document_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": doc.id,
        "type": doc.document_type,
        "extracted_data": json.loads(doc.extracted_data) if doc.extracted_data else {},
        "validation_results": json.loads(doc.validation_results) if doc.validation_results else {},
        "storage_reference": doc.storage_reference
    }

@router.post("/{document_id}/approve")
def approve_document(document_id: str, reviewer_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    doc.status = JobStatus.APPROVED.value
    doc.requires_human_review = False
    log_audit(db, document_id, "DOCUMENT_APPROVED", f"Reviewer: {reviewer_id}")
    db.commit()
    return {"status": "approved"}

@router.post("/{document_id}/reject")
def reject_document(document_id: str, payload: RejectRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    doc.status = JobStatus.REJECTED.value
    log_audit(db, document_id, "DOCUMENT_REJECTED", f"Reason: {payload.reason}. Reviewer: {payload.reviewer_id}")
    db.commit()
    return {"status": "rejected"}

@router.patch("/{document_id}/fields")
def correct_field(document_id: str, payload: FieldPatchRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    data = json.loads(doc.extracted_data)
    
    original = str(data.get(payload.field_name, {}).get("value", "null"))
    # Update dict
    if payload.field_name not in data:
        data[payload.field_name] = {}
    data[payload.field_name]["value"] = payload.corrected_value
    data[payload.field_name]["confidence"] = 1.0 # Human corrected = 100%
    
    doc.extracted_data = json.dumps(data)
    log_audit(db, document_id, "FIELD_CORRECTED", f"{payload.field_name}: {original} -> {payload.corrected_value} by {payload.reviewer_id}")
    db.commit()
    return {"status": "updated", "field": payload.field_name}