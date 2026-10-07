from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db, DocumentRecord, JobStatus, AuditEvent
from pydantic import BaseModel
import json, uuid, datetime
from app.services.validator import validate_document
from app.services.confidence import calculate_routing_decision

router = APIRouter(prefix="/review", tags=["Human Review"])

class RejectRequest(BaseModel):
    reason: str
    reviewer_id: str

class FieldPatchRequest(BaseModel):
    field_name: str
    corrected_value: str
    reviewer_id: str
    reason: str = "Human correction"

def log_audit(db, doc_id, event_name, details=""):
    db.add(AuditEvent(id=str(uuid.uuid4()), document_id=doc_id, event_name=event_name, details=details))

@router.post("/{document_id}/approve")
def approve_document(document_id: str, reviewer_id: str, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    if doc.status != JobStatus.NEEDS_REVIEW.value:
        raise HTTPException(status_code=400, detail=f"Invalid state transition: {doc.status} -> APPROVED")
    
    doc.status = JobStatus.APPROVED.value
    doc.requires_human_review = False
    log_audit(db, document_id, "DOCUMENT_APPROVED", f"Reviewer: {reviewer_id}")
    db.commit()
    return {"status": "approved"}

@router.post("/{document_id}/reject")
def reject_document(document_id: str, payload: RejectRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    if doc.status != JobStatus.NEEDS_REVIEW.value:
        raise HTTPException(status_code=400, detail=f"Invalid state transition: {doc.status} -> REJECTED")
        
    doc.status = JobStatus.REJECTED.value
    log_audit(db, document_id, "DOCUMENT_REJECTED", f"Reason: {payload.reason}. Reviewer: {payload.reviewer_id}")
    db.commit()
    return {"status": "rejected"}

@router.patch("/{document_id}/fields")
def correct_field(document_id: str, payload: FieldPatchRequest, db: Session = Depends(get_db)):
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    if doc.status != JobStatus.NEEDS_REVIEW.value:
        raise HTTPException(status_code=400, detail="Document must be in NEEDS_REVIEW state to patch fields.")
        
    data = json.loads(doc.extracted_data)
    if payload.field_name not in data: data[payload.field_name] = {}
    
    original_val = data[payload.field_name].get("value")
    data[payload.field_name]["history"] = data[payload.field_name].get("history", [])
    data[payload.field_name]["history"].append({
        "original_value": str(original_val),
        "corrected_value": payload.corrected_value,
        "reviewer_id": payload.reviewer_id,
        "reviewed_at": datetime.datetime.utcnow().isoformat(),
        "reason": payload.reason
    })
    
    data[payload.field_name]["value"] = payload.corrected_value
    data[payload.field_name]["confidence"] = 1.0 
    doc.extracted_data = json.dumps(data)
    log_audit(db, document_id, "FIELD_CORRECTED", f"{payload.field_name}: {original_val} -> {payload.corrected_value}")
    
    # Re-Validation
    val_result = validate_document(doc.document_type, data, [])
    doc.validation_results = json.dumps(val_result)
    
    conf_result = calculate_routing_decision(doc.document_type, doc.confidence_score, data, val_result["passed"])
    doc.final_confidence_score = conf_result["overall_confidence"]
    
    if conf_result["decision"] == "AUTO_APPROVED":
        doc.status = JobStatus.APPROVED.value
        log_audit(db, document_id, "DOCUMENT_APPROVED", "Re-validation passed thresholds")
    
    db.commit()
    return {"status": "updated", "new_decision": conf_result["decision"]}