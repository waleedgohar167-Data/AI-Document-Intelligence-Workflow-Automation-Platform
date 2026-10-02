from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import date

class InvoiceSchema(BaseModel):
    invoice_number: str = Field(..., description="Unique identifier for the invoice")
    supplier: str = Field(..., description="Name of the issuing company")
    invoice_date: date
    due_date: date
    subtotal: float
    tax: float
    total: float
    currency: str

    @model_validator(mode='after')
    def validate_invoice_logic(self):
        if self.invoice_date > self.due_date:
            raise ValueError("Deterministic Failure: Invoice date cannot be after due date.")
        if abs((self.subtotal + self.tax) - self.total) > 0.01:
            raise ValueError("Deterministic Failure: Subtotal + Tax does not equal Total.")
        if self.currency not in ["USD", "EUR", "GBP", "PKR"]:
            raise ValueError(f"Deterministic Failure: Unsupported currency {self.currency}.")
        return self

class ContractSchema(BaseModel):
    parties: List[str] = Field(..., min_length=2, description="Entities involved in the contract")
    effective_date: date
    termination_date: date
    renewal_conditions: str
    payment_terms: str
    governing_law: str

    @model_validator(mode='after')
    def validate_contract_dates(self):
        if self.effective_date > self.termination_date:
            raise ValueError("Deterministic Failure: Effective date must be before termination date.")
        return self

class PurchaseOrderItem(BaseModel):
    description: str
    quantity: int = Field(..., gt=0)
    unit_price: float = Field(..., ge=0)
    total_price: float

    @model_validator(mode='after')
    def validate_item_total(self):
        if abs((self.quantity * self.unit_price) - self.total_price) > 0.01:
            raise ValueError("Deterministic Failure: Item quantity * unit price does not equal total_price.")
        return self

class PurchaseOrderSchema(BaseModel):
    po_number: str
    supplier: str
    items: List[PurchaseOrderItem]
    total: float

    @model_validator(mode='after')
    def validate_po_total(self):
        calculated_total = sum(item.total_price for item in self.items)
        if abs(calculated_total - self.total) > 0.01:
            raise ValueError("Deterministic Failure: Sum of line items does not equal PO total.")
        return self