from pydantic import BaseModel
from typing import List, Optional

class TextBlock(BaseModel):
    text: str
    page_number: Optional[int]
    position: Optional[str]
    source_file: str
    method: str

class DocumentMetadata(BaseModel):
    extraction_timestamp: str
    pdf_parser_version: Optional[str] = None
    ocr_version: Optional[str] = None
    docx_version: Optional[str] = None
    pages_processed: int
    warnings: List[str] = []

class NormalizedDocument(BaseModel):
    document_id: str
    extraction_method: str
    blocks: List[TextBlock]
    metadata: DocumentMetadata

class ClassificationResult(BaseModel):
    document_type: str
    confidence: float
    classification_method: str
    reasoning: str