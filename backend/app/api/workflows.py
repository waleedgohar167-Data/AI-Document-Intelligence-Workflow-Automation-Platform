from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import logging
from app.core.database import get_db, DeadLetterQueue
from app.services.workflow import dispatch_with_backoff, log_audit

logger = logging.getLogger(__name__)
router = APIRouter(tags=["workflows"])

# IMPROVEMENT 2: Mock ERP Service
@router.post("/mock-erp/ingest")
async def mock_erp_ingest(request: Request):
    payload = await request.json()
    
    # Simulate a failure if a specific test flag is passed
    if payload.get("data", {}).get("document_id") == "FAIL_ME":
        logger.error("Mock ERP rejecting payload (Simulated Failure).")
        raise HTTPException(status_code=500, detail="Simulated ERP Failure")
        
    logger.info(f"Mock ERP successfully received payload: {payload}")
    return {"status": "success", "message": "Payload accepted by Mock ERP"}

# IMPROVEMENT 1: DLQ Replay Endpoint
@router.post("/workflows/dlq/{dlq_id}/replay")
def replay_dlq(dlq_id: str, db: Session = Depends(get_db)):
    record = db.query(DeadLetterQueue).filter(DeadLetterQueue.dlq_id == dlq_id).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="DLQ record not found")
    if record.status == "REPLAYED":
        raise HTTPException(status_code=400, detail="Payload already replayed successfully")
        
    # Attempt redelivery using the logic we just updated
    success = dispatch_with_backoff(
        db=db,
        document_id=record.document_id,
        payload=record.payload,
        destination_url=record.destination_url
    )
    
    if success:
        record.status = "REPLAYED"
        db.commit()
        log_audit(db, record.document_id, "WORKFLOW_REPLAYED", {"dlq_id": dlq_id})
        return {"status": "success", "message": "Replay successful"}
    else:
        log_audit(db, record.document_id, "WORKFLOW_REPLAY_FAILED", {"dlq_id": dlq_id})
        raise HTTPException(status_code=500, detail="Replay failed again. Payload remains in DLQ.")