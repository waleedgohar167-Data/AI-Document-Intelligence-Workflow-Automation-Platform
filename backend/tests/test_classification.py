import pytest
from app.schemas.classification import NormalizedDocument
from app.services.classifier import classify_document, CONFIDENCE_THRESHOLD

def create_mock_doc(text: str) -> NormalizedDocument:
    return NormalizedDocument(
        document_id="123",
        extraction_method="native",
        blocks=[{"text": text, "page_number": 1, "position": None, "source_file": "file.pdf", "method": "native"}],
        metadata={"extraction_timestamp": "2026-01-01", "pages_processed": 1, "warnings": []}
    )

def test_invoice_classification():
    """Test: Invoice document classified correctly with confidence above threshold"""
    doc = create_mock_doc("This is an INVOICE. The total due is $500. Remittance address below.")
    result = classify_document(doc)
    assert result.document_type == "invoice"
    assert result.confidence >= CONFIDENCE_THRESHOLD

def test_po_classification():
    """Test: Purchase order document classified correctly"""
    doc = create_mock_doc("PURCHASE ORDER. PO Number: 999. Vendor: ACME Corp. Delivery Date: Tomorrow.")
    result = classify_document(doc)
    assert result.document_type == "purchase_order"
    assert result.confidence >= CONFIDENCE_THRESHOLD

def test_contract_classification():
    """Test: Contract document classified correctly"""
    doc = create_mock_doc("This Agreement is binding between the parties hereby. Signature required for confidentiality.")
    result = classify_document(doc)
    assert result.document_type == "contract"
    assert result.confidence >= CONFIDENCE_THRESHOLD

def test_unknown_document_handling():
    """Test: Unknown document type handled without exception"""
    doc = create_mock_doc("Just a random text document with no identifying financial keywords.")
    result = classify_document(doc)
    assert result.document_type == "unknown"
    assert result.confidence == 0.1
    assert result.reasoning == "No identifying keywords found in document text."

def test_low_confidence_flagging():
    """Test: Low confidence document flagged for human review (Threshold logic)"""
    doc = create_mock_doc("Contains one keyword: invoice. But nothing else.")
    result = classify_document(doc)
    assert result.document_type == "invoice"
    assert result.confidence < CONFIDENCE_THRESHOLD