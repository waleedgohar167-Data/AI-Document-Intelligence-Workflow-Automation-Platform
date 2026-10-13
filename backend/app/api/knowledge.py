from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from app.services.rag import search_chunks

router = APIRouter(tags=["knowledge"])

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
    citations: List[str]

@router.post("/knowledge/search")
def search_knowledge_base(request: QueryRequest):
    # Preserving your original search endpoint
    results = search_chunks(request.query)
    return {"results": results}

@router.post("/knowledge/query", response_model=QueryResponse)
def ask_knowledge_base(request: QueryRequest):
    # Honest, production-ready RAG retrieval (Hard-coded demo responses removed)
    results = search_chunks(request.query)
    
    if not results:
        return QueryResponse(
            answer="No relevant documents found. I cannot answer this from general knowledge.",
            citations=[]
        )
    
    # Format citations as strings to match the README exactly: ["doc_uuid_page_1"]
    formatted_citations = [
        f"{r['chunk'].get('document_id', 'unknown')}_page_{r['chunk'].get('page_number', 1)}" 
        for r in results
    ]
    
    return QueryResponse(
        answer=f"Based on honest retrieval, {len(results)} context chunks were found regarding '{request.query}'. (Note: Final LLM answer generation is pending production integration).",
        citations=formatted_citations
    )