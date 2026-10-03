import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db, DocumentRecord, ProcessingJob

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx"
}
MAX_FILE_SIZE = 10 * 1024 * 1024
STORAGE_DIR = "storage/documents"
os.makedirs(STORAGE_DIR, exist_ok=True)

@router.post("/documents")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Task 5 Error: Unsupported file type
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=415, detail={"error": "Unsupported file type", "allowed": list(ALLOWED_MIME_TYPES.keys())})
    
    # Task 5 Error: File too large
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail={"error": "File too large", "max_size_bytes": MAX_FILE_SIZE})

    doc_id = str(uuid.uuid4())
    ext = ALLOWED_MIME_TYPES.get(file.content_type, "")
    storage_path = os.path.join(STORAGE_DIR, f"{doc_id}{ext}")
    
    # Task 5 Error: Storage failure
    try:
        with open(storage_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": "Storage failure", "message": str(e)})

    # Task 3 & 4: Database records, and Task 5 Error: Database write failure
    try:
        new_doc = DocumentRecord(
            id=doc_id,
            original_filename=file.filename,
            file_type=file.content_type,
            status="pending",
            storage_reference=storage_path
        )
        new_job = ProcessingJob(
            id=str(uuid.uuid4()),
            document_id=doc_id,
            status="queued"
        )
        db.add(new_doc)
        db.add(new_job)
        db.commit()
    except Exception as e:
        db.rollback()
        if os.path.exists(storage_path):
            os.remove(storage_path) # Clean up file if DB fails
        raise HTTPException(status_code=500, detail={"error": "Database write failure", "message": str(e)})

    return {"document_id": doc_id, "status": "success"}