import pytest
from app.core.database import SessionLocal, AuditEvent
import uuid

@pytest.fixture
def db():
    database = SessionLocal()
    yield database
    database.rollback()
    database.close()

def test_audit_immutability_update(db):
    event_id = str(uuid.uuid4())
    event = AuditEvent(id=event_id, document_id="doc_test_1", event_type="DOCUMENT_UPLOADED", payload="{}")
    db.add(event)
    db.commit()
    
    # Attempting to modify an existing audit record must raise our strict immutability exception
    with pytest.raises(Exception, match="Strict Immutability Violation"):
        event.payload = '{"tampered": true}'
        db.commit()
    db.rollback()

def test_audit_immutability_delete(db):
    event_id = str(uuid.uuid4())
    event = AuditEvent(id=event_id, document_id="doc_test_2", event_type="DOCUMENT_UPLOADED", payload="{}")
    db.add(event)
    db.commit()
    
    # Attempting to delete an audit record must raise our strict immutability exception
    with pytest.raises(Exception, match="Strict Immutability Violation"):
        db.delete(event)
        db.commit()
    db.rollback()