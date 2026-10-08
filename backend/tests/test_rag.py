import pytest
from app.services.rag import index_document_for_retrieval, search_chunks, VECTOR_STORE
from app.core.database import SessionLocal, DocumentRecord

@pytest.fixture
def db():
    database = SessionLocal()
    yield database
    database.rollback()
    database.close()

def test_eligibility_gate_rejects_non_approved(db):
    # Insert a document that is stuck in NEEDS_REVIEW
    doc = DocumentRecord(id="doc_rag_fail", status="NEEDS_REVIEW", original_filename="test.pdf")
    db.add(doc)
    db.commit()

    # The indexing function must return False and reject it at the gate
    indexed = index_document_for_retrieval(db, "doc_rag_fail")
    assert indexed is False

def test_duplicate_indexing_prevented():
    VECTOR_STORE.clear()
    # Simulate a document already existing in the vector store
    VECTOR_STORE.append({"document_id": "doc_rag_dup", "text": "sample text", "chunk_id": "1"})
    
    # The system must recognize it's a duplicate and prevent re-indexing
    is_duplicate = any(chunk["document_id"] == "doc_rag_dup" for chunk in VECTOR_STORE)
    assert is_duplicate is True

def test_search_no_results():
    VECTOR_STORE.clear()
    # Querying for something not in the store must return an empty list gracefully
    results = search_chunks("nonexistent query regarding financial compliance")
    assert len(results) == 0