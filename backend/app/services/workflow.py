import json
import time
import logging
import uuid
import requests
from app.core.database import DocumentRecord, DeadLetterQueue, AuditEvent

logger = logging.getLogger(__name__)

# IMPROVEMENT 3: Configurable Trigger Mappings per Document Type
WORKFLOW_MAPPINGS = {
    "INVOICE": {
        "actions": ["Create accounts payable record", "Notify finance team"],
        "destination_url": "http://127.0.0.1:8000/mock-erp/ingest"
    },
    "PURCHASE_ORDER": {
        "actions": ["Create procurement record", "Notify procurement team"],
        "destination_url": "http://127.0.0.1:8000/mock-erp/ingest"
    },
    "CONTRACT": {
        "actions": ["Create CRM record", "Assign relationship owner", "Send confirmation"],
        "destination_url": "http://127.0.0.1:8000/mock-erp/ingest"
    }
}

def log_audit(db, document_id: str, event_type: str, payload_data: dict = None):
    """Creates an immutable audit record for workflow events."""
    event = AuditEvent(
        id=str(uuid.uuid4()),
        document_id=document_id,
        event_type=event_type,
        payload=json.dumps(payload_data) if payload_data else "{}"
    )
    db.add(event)
    db.commit()
    logger.info(f"AUDIT [{event_type}] Doc: {document_id}")

def dispatch_with_backoff(db, document_id: str, payload: dict, destination_url: str, max_retries: int = 3) -> bool:
    """
    ELITE FEATURE: Exponential backoff for fault-tolerant webhook delivery.
    Prevents data loss if the downstream legacy ERP is temporarily offline.
    """
    # IMPROVEMENT 4: Audit triggered
    log_audit(db, document_id, "WORKFLOW_TRIGGERED", {"destination": destination_url})

    for attempt in range(max_retries):
        try:
            # IMPROVEMENT 2: Hitting the Mock ERP
            response = requests.post(destination_url, json=payload, timeout=5.0)
            response.raise_for_status()
            
            # IMPROVEMENT 4: Audit delivered
            log_audit(db, document_id, "WORKFLOW_DELIVERED", {"attempt": attempt + 1})
            logger.info(f"Webhook delivered successfully on attempt {attempt + 1}")
            return True
            
        except Exception as e:
            wait_time = 2 ** attempt  # 1s, 2s, 4s...
            # IMPROVEMENT 4: Audit every retry
            log_audit(db, document_id, "WORKFLOW_RETRY_ATTEMPTED", {
                "attempt_number": attempt + 1,
                "delay_seconds": wait_time,
                "error": str(e)
            })
            logger.warning(f"Webhook failed: {str(e)}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
            
    # IMPROVEMENT 4: Audit final failure
    log_audit(db, document_id, "WORKFLOW_FAILED", {"max_retries": max_retries})
    logger.error("Webhook failed completely after max retries. Sending to Dead Letter Queue (DLQ).")
    
    # IMPROVEMENT 1: Create DLQ Record
    dlq_record = DeadLetterQueue(
        dlq_id=str(uuid.uuid4()),
        document_id=document_id,
        payload=payload,
        destination_url=destination_url,
        retry_count=max_retries,
        last_error="Max retries exhausted",
        status="PENDING"
    )
    db.add(dlq_record)
    db.commit()
    
    log_audit(db, document_id, "WORKFLOW_DLQ_CREATED", {"dlq_id": dlq_record.dlq_id})
    return False

def trigger_webhook_automation(db, doc_id: str):
    """
    Constructs the enterprise payload and triggers the fault-tolerant dispatcher.
    Only fires for strictly APPROVED documents.
    """
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    
    if not doc or doc.status != "APPROVED":
        return False
        
    # IMPROVEMENT 3: Grab the correct mapping based on document type
    doc_type = (doc.document_type or "INVOICE").upper()
    mapping = WORKFLOW_MAPPINGS.get(doc_type, WORKFLOW_MAPPINGS["INVOICE"])
        
    # Construct a strictly typed enterprise payload
    payload = {
        "event_type": "document.approved",
        "timestamp": doc.upload_timestamp.isoformat() if doc.upload_timestamp else None,
        "actions": mapping["actions"],
        "data": {
            "document_id": doc.id,
            "document_type": doc_type,
            "extracted_data": json.loads(doc.extracted_data) if doc.extracted_data else {}
        }
    }
    
    # Fire the fault-tolerant dispatcher
    success = dispatch_with_backoff(db, doc.id, payload, mapping["destination_url"])
    
    return success