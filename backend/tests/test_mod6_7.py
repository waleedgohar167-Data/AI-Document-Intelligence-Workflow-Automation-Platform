import pytest
from app.services.validator import validate_document
from app.services.confidence import calculate_overall_confidence

def test_valid_invoice_passes():
    data = {
        "subtotal": {"value": 100.0}, "tax": {"value": 10.0}, "total": {"value": 110.0},
        "invoice_date": {"value": "2026-01-01"}, "due_date": {"value": "2026-01-31"},
        "currency": {"value": "USD"}
    }
    res = validate_document("invoice", data, [])
    assert res["passed"] == True

def test_invalid_invoice_fails():
    data = {"subtotal": {"value": 100.0}, "tax": {"value": 10.0}, "total": {"value": 999.0}}
    res = validate_document("invoice", data, [])
    assert res["passed"] == False
    assert res["failures"][0]["field"] == "total"

def test_confidence_routing():
    data = {"field1": {"confidence": 0.99}, "field2": {"confidence": 0.95}}
    # Passed validation, high confidence
    res = calculate_overall_confidence(0.95, data, True)
    assert res["review_required"] == False
    
    # Failed validation forces review
    res_fail = calculate_overall_confidence(0.95, data, False)
    assert res_fail["review_required"] == True