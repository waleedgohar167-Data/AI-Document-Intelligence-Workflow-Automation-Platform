import pytest
from app.services.workflow import trigger_webhook_automation
from app.core.database import SessionLocal, DocumentRecord

@pytest.fixture
def db():
    database = SessionLocal()
    database.query(DocumentRecord).delete()
    database.commit()
    yield database
    database.query(DocumentRecord).delete()
    database.commit()
    database.close()

def test_workflow_triggers_on_approved(db):
    doc = DocumentRecord(id="doc_wf_1", status="APPROVED", extracted_data='{"total": 100}')
    db.add(doc)
    db.commit()
    
    result = trigger_webhook_automation(db, "doc_wf_1")
    assert result is True

def test_workflow_blocked_on_needs_review(db):
    doc = DocumentRecord(id="doc_wf_2", status="NEEDS_REVIEW", extracted_data='{"total": 100}')
    db.add(doc)
    db.commit()
    
    # Must fail because human review is still pending
    result = trigger_webhook_automation(db, "doc_wf_2")
    assert result is False