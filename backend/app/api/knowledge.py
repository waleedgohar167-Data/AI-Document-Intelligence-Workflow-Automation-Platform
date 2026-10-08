from fastapi import APIRouter
from pydantic import BaseModel
from app.services.rag import search_chunks

router = APIRouter()

class QueryRequest(BaseModel):
    query: str

@router.post("/knowledge/search")
def search_knowledge_base(request: QueryRequest):
    results = search_chunks(request.query)
    return {"results": results}

@router.post("/knowledge/query")
def ask_knowledge_base(request: QueryRequest):
    # Task 5: Grounded Q&A
    results = search_chunks(request.query)
    
    if not results:
        return {
            "answer": "No relevant documents found. I cannot answer this from general knowledge.",
            "citations": [],
            "retrieved_chunks": []
        }
    
    # Mock LLM generation grounded strictly in the retrieved text
    citations = [{"document_id": r["chunk"]["document_id"], "page_number": r["chunk"]["page_number"]} for r in results]
    
    return {
        "answer": f"Based on the provided documents, here is the information regarding '{request.query}'.",
        "citations": citations,
        "retrieved_chunks": [r["chunk"] for r in results]
    }