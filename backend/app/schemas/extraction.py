from pydantic import BaseModel, Field, PositiveFloat
from typing import TypeVar, Generic, Optional, List
from datetime import date

T = TypeVar('T')

class ExtractedField(BaseModel, Generic[T]):
    value: T
    confidence: float = Field(ge=0.0, le=1.0)
    source_page: Optional[int] = None
    supporting_text: Optional[str] = None

class LineItem(BaseModel):
    description: ExtractedField[str]
    quantity: ExtractedField[PositiveFloat]
    unit_price: ExtractedField[PositiveFloat]

class InvoiceExtraction(BaseModel):
    invoice_number: Optional[ExtractedField[str]] = None
    supplier: Optional[ExtractedField[str]] = None
    invoice_date: Optional[ExtractedField[date]] = None
    due_date: Optional[ExtractedField[date]] = None
    subtotal: Optional[ExtractedField[PositiveFloat]] = None
    tax: Optional[ExtractedField[PositiveFloat]] = None
    total: Optional[ExtractedField[PositiveFloat]] = None
    currency: Optional[ExtractedField[str]] = None

class POExtraction(BaseModel):
    po_number: Optional[ExtractedField[str]] = None
    supplier: Optional[ExtractedField[str]] = None
    items: Optional[List[LineItem]] = None
    total: Optional[ExtractedField[PositiveFloat]] = None

class ContractExtraction(BaseModel):
    parties: Optional[ExtractedField[List[str]]] = None
    effective_date: Optional[ExtractedField[date]] = None
    termination_date: Optional[ExtractedField[date]] = None
    renewal_conditions: Optional[ExtractedField[str]] = None
    payment_terms: Optional[ExtractedField[str]] = None
    governing_law: Optional[ExtractedField[str]] = None

def get_required_fields(doc_type: str) -> List[str]:
    if doc_type == "invoice":
        return ["invoice_number", "supplier", "invoice_date", "due_date", "subtotal", "tax", "total", "currency"]
    elif doc_type == "purchase_order":
        return ["po_number", "supplier", "items", "total"]
    elif doc_type == "contract":
        return ["parties", "effective_date"]
    return []