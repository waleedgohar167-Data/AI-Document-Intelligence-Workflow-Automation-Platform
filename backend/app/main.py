from fastapi import FastAPI
from datetime import datetime

app = FastAPI(
    title="AI Document Intelligence API",
    description="Backend services for document parsing, extraction, and validation.",
    version="0.1.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "disconnected_v0",
        "worker_queue": "disconnected_v0"
    }