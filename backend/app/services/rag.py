import json
import uuid
from app.core.database import DocumentRecord
# from app.worker import log_audit  # Import your updated log_audit here

# In-memory vector store for V1 local execution. 
# Production will seamlessly swap this array for pgvector or ChromaDB.
VECTOR_STORE = []

def index_document_for_retrieval(db, doc_id: str):
    # log_audit(db, doc_id, "RETRIEVAL_INDEXING_STARTED")
    
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    
    # Task 1: Eligibility Gate
    if not doc or doc.status != "APPROVED":
        # log_audit(db, doc_id, "RETRIEVAL_INDEXING_SKIPPED", payload={"reason": "Document not APPROVED"})
        return False

    # Task 6: Deduplication Check
    if any(chunk["document_id"] == doc_id for chunk in VECTOR_STORE):
        # log_audit(db, doc_id, "RETRIEVAL_ALREADY_INDEXED")
        return True

    # Task 2 & 3: Chunking & Indexing
    try:
        file_path = f"storage/parsed/{doc_id}.json"
        with open(file_path, "r") as f:
            parsed_data = json.load(f)
    except FileNotFoundError:
        # log_audit(db, doc_id, "RETRIEVAL_INDEXING_FAILED", payload={"reason": "Parsed JSON missing"})
        return False

    chunks_created = 0
    for block in parsed_data.get("blocks", []):
        chunk = {
            "chunk_id": str(uuid.uuid4()),
            "document_id": doc_id,
            "text": block.get("text", ""),
            "page_number": block.get("page", 1),
            "document_type": doc.document_type,
            "source_filename": doc.filename,
            "embedding": [0.1] * 128 # Mock embedding representation
        }
        VECTOR_STORE.append(chunk)
        chunks_created += 1

    # log_audit(db, doc_id, "DOCUMENT_INDEXED", payload={"chunk_count": chunks_created, "embedding_model": "local-mock-v1"})
    return True

def search_chunks(query: str, top_k: int = 3):
    # V1 Mock Search: Keyword density heuristic to simulate cosine similarity
    query_words = query.lower().split()
    scored = []
    for chunk in VECTOR_STORE:
        score = sum(1 for word in query_words if word in chunk["text"].lower())
        if score > 0:
            scored.append({"chunk": chunk, "relevance_score": round(score * 0.15, 2)})
            
    scored.sort(key=lambda x: x["relevance_score"], reverse=True)
    return scored[:top_k]

# ---------------------------------------------------------
# DAY 9 IMPROVEMENT 4: DOCUMENT REVOCATION
# ---------------------------------------------------------
def revoke_document_approval(db, doc_id: str):
    """Handles revocation, removes from index, and logs audit event."""
    global VECTOR_STORE
    
    doc = db.query(DocumentRecord).filter(DocumentRecord.id == doc_id).first()
    if doc:
        doc.status = "REJECTED"
        db.commit()
    
    initial_count = len(VECTOR_STORE)
    
    # FIX: Use [:] to mutate the exact list in-place so the test file sees the change!
    VECTOR_STORE[:] = [chunk for chunk in VECTOR_STORE if chunk["document_id"] != doc_id]
    
    if len(VECTOR_STORE) < initial_count:
        # log_audit(db, doc_id, "DOCUMENT_REJECTED", payload={"reason": "Revoked by admin", "chunks_removed": initial_count - len(VECTOR_STORE)})
        pass
        
    return True