import pytest
from datetime import date
from app.schemas.document_schemas import InvoiceSchema
from pydantic import ValidationError

def test_invoice_valid_math_and_dates():
    # Should pass validation perfectly
    invoice = InvoiceSchema(
        invoice_number="INV-100",
        supplier="Acme Corp",
        invoice_date=date(2026, 10, 1),
        due_date=date(2026, 10, 31),
        subtotal=100.0,
        tax=10.0,
        total=110.0,
        currency="USD"
    )
    assert invoice.total == 110.0

def test_invoice_invalid_math():
    # Should fail because 100 + 10 != 500
    with pytest.raises(ValidationError) as excinfo:
        InvoiceSchema(
            invoice_number="INV-101",
            supplier="Acme Corp",
            invoice_date=date(2026, 10, 1),
            due_date=date(2026, 10, 31),
            subtotal=100.0,
            tax=10.0,
            total=500.0,
            currency="USD"
        )
    assert "Subtotal + Tax does not equal Total" in str(excinfo.value)