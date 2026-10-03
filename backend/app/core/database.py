from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

# SQLite database setup for Day 2
engine = create_engine("sqlite:///./documents.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Task 3: Document Record Creation
class DocumentRecord(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, index=True)
    original_filename = Column(String)
    file_type = Column(String)
    upload_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String, default="pending")
    storage_reference = Column(String)

# Task 4: Processing Job Creation
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, index=True)
    status = Column(String, default="queued")

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()