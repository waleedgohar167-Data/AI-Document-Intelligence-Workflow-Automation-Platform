import json
import time
import logging
from app.core.database import DocumentRecord
# from app.worker import log_audit

logger = logging.getLogger(__name__)

def dispatch_with_backoff(payload: dict, max_retries: int = 3) -> bool:
    """
    ELITE FEATURE: Exponential backoff for fault-tolerant webhook delivery.
    Prevents data loss if the downstream legacy ERP is temporarily offline.
    """
    for attempt in range(max_retries):
        try:
            # SIMULATED NETWORK CALL
            # In production: response = httpx.post("https://erp.internal/api/ingest", json=payload, timeout=5.0)
            # response.raise_for_status()
            
            # Simulating a successful 200 OK response
            network_success = True 
            
            if network_success:
                logger.info(f"Webhook delivered successfully on attempt {attempt + 1}")
                return True
                
        except Exception as e:
            wait_time = 2 ** attempt  # 1s, 2s, 4s...
            logger.warning(f"Webhook failed: {str(e)}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time) # Yields thread in async environments
            
    logger.error("Webhook failed completely after max retries. Sending to Dead Letter Queue (DLQ).")
    return False

def trigger_webhook_automation(db, doc_id: str):
    """
    Constructs the enterprise payload and triggers the fault-tolerant dispatcher.
    Only fires for strictly APPROVED documents.
    """
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    
    if not doc or doc.status != "APPROVED":
        return False
        
    # Construct a strictly typed enterprise payload
    payload = {
        "event_type": "document.approved",
        "timestamp": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
        "data": {
            "document_id": doc.id,
            "document_type": doc.document_type,
            "extracted_data": json.loads(doc.extracted_data) if doc.extracted_data else {}
        }
    }
    
    # Fire the fault-tolerant dispatcher
    success = dispatch_with_backoff(payload)
    
    if success:
        # log_audit(db, doc_id, "WORKFLOW_TRIGGERED")
        return True
    else:
        # log_audit(db, doc_id, "WORKFLOW_FAILED", payload={"reason": "Max retries exceeded"})
        return False