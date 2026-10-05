import pytest
from app.schemas.classification import NormalizedDocument
from app.services.extractor import extract_structured_data

def create_mock_doc(text: str) -> NormalizedDocument:
    return NormalizedDocument(
        document_id="123", extraction_method="native",
        blocks=[{"text": text, "page_number": 1, "position": None, "source_file": "file.pdf", "method": "native"}],
        metadata={"extraction_timestamp": "2026-01-01", "pages_processed": 1, "warnings": []}
    )

def test_invoice_extraction_success():
    doc = create_mock_doc("dummy")
    data, missing = extract_structured_data(doc, "invoice")
    assert "invoice_number" in data
    assert data["invoice_number"]["value"] == "INV-100"
    assert data["invoice_number"]["confidence"] == 0.95
    assert len(missing) == 0

def test_po_extraction_success():
    doc = create_mock_doc("dummy")
    data, missing = extract_structured_data(doc, "purchase_order")
    assert "items" in data
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"]["value"] == 10.0

def test_contract_extraction_success():
    doc = create_mock_doc("dummy")
    data, missing = extract_structured_data(doc, "contract")
    assert "parties" in data
    assert "Party A" in data["parties"]["value"]

def test_missing_required_field_handled():
    doc = create_mock_doc("MISSING_FIELD")
    data, missing = extract_structured_data(doc, "invoice")
    assert "supplier" in data
    assert "invoice_number" in missing

def test_invalid_llm_json_handled():
    doc = create_mock_doc("INVALID_JSON")
    with pytest.raises(ValueError, match="Invalid LLM output"):
        extract_structured_data(doc, "invoice")