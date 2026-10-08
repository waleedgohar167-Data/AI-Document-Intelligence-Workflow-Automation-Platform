from sqlalchemy import create_engine, Column, String, DateTime, Text, Enum, Float, Boolean, event
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import enum

# SQLite database setup
engine = create_engine("sqlite:///./documents.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    PARSED = "parsed"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    VALIDATED = "validated"          # MODULE 6 STATUS
    VALIDATION_FAILED = "validation_failed" # MODULE 6 STATUS
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"            # MODULE 7 STATUS
    REJECTED = "rejected"            # MODULE 7 STATUS
    FAILED = "failed"

class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String)
    file_type = Column(String)
    upload_timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    status = Column(String, default=JobStatus.QUEUED.value)
    storage_reference = Column(String)
    
    # Classification Storage
    document_type = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True) # Initial classification score
    requires_human_review = Column(Boolean, default=False)
    
    # Extraction Storage (Day 5)
    extracted_data = Column(Text, nullable=True)
    
    # Validation & Confidence Storage (Modules 6 & 7)
    validation_results = Column(Text, nullable=True)
    confidence_breakdown = Column(Text, nullable=True)
    final_confidence_score = Column(Float, nullable=True) # Mod 7 Aggregated Score

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    status = Column(String, default=JobStatus.QUEUED.value)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)

# ---------------------------------------------------------
# DAY 8: UPDATED AUDIT EVENT TABLE (Task 1)
# ---------------------------------------------------------
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    event_type = Column(String, index=True)
    actor = Column(String, default="system")
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    payload = Column(Text, default="{}") # JSON string
    model_version = Column(String, nullable=True)
    policy_version = Column(String, nullable=True)

# ---------------------------------------------------------
# DAY 8: STRICT IMMUTABILITY (Task 5)
# ---------------------------------------------------------
@event.listens_for(AuditEvent, "before_update")
def prevent_audit_update(mapper, connection, target):
    raise Exception("Strict Immutability Violation: Audit events cannot be modified.")

@event.listens_for(AuditEvent, "before_delete")
def prevent_audit_delete(mapper, connection, target):
    raise Exception("Strict Immutability Violation: Audit events cannot be deleted.")

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()