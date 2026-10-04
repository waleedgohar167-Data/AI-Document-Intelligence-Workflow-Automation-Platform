from sqlalchemy import create_engine, Column, String, DateTime, Text, Enum, Float, Boolean
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
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"

class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String)
    file_type = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default=JobStatus.QUEUED.value)
    storage_reference = Column(String)
    
    # Task 4 & 5: Classification Storage
    document_type = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    requires_human_review = Column(Boolean, default=False)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    status = Column(String, default=JobStatus.QUEUED.value)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    failure_reason = Column(Text, nullable=True)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    event_name = Column(String)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()