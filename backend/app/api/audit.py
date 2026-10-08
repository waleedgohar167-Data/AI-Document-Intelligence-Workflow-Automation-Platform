from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db, AuditEvent
import json

router = APIRouter()

@router.get("/documents/{document_id}/audit")
def get_document_audit_history(document_id: str, db: Session = Depends(get_db)):
    events = db.query(AuditEvent).filter(AuditEvent.document_id == document_id).order_by(AuditEvent.timestamp.asc()).all()
    if not events:
        raise HTTPException(status_code=404, detail="No audit history found for this document.")
    
    return [
        {
            "event_id": e.id, "event_type": e.event_type, "actor": e.actor,
            "timestamp": e.timestamp, "payload": json.loads(e.payload),
            "model_version": e.model_version, "policy_version": e.policy_version
        } for e in events
    ]

@router.get("/audit/events")
def get_all_audit_events(event_type: str = None, db: Session = Depends(get_db)):
    query = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
    if event_type:
        query = query.filter(AuditEvent.event_type == event_type)
    
    events = query.limit(100).all()
    return [{"event_id": e.id, "event_type": e.event_type, "timestamp": e.timestamp} for e in events]