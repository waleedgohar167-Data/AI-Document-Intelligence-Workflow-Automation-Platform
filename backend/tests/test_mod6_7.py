import pytest
from app.services.validator import validate_document
from app.services.confidence import calculate_routing_decision

def test_valid_invoice_passes():
    # Updated to use strings so our safe_decimal function parses them cleanly
    data = {
        "subtotal": {"value": "100.00"}, "tax": {"value": "10.00"}, "total": {"value": "110.00"},
        "invoice_date": {"value": "2026-01-01"}, "due_date": {"value": "2026-01-31"},
        "currency": {"value": "USD"}
    }
    res = validate_document("invoice", data, [])
    assert res["passed"] == True

def test_invalid_invoice_fails():
    data = {"subtotal": {"value": "100.00"}, "tax": {"value": "10.00"}, "total": {"value": "999.00"}}
    res = validate_document("invoice", data, [])
    assert res["passed"] == False
    assert res["failures"][0]["field"] == "total"

def test_confidence_routing():
    # Added the critical fields required by Improvement 4 to ensure auto-approval works
    data = {
        "total": {"confidence": 0.99}, 
        "currency": {"confidence": 0.99}, 
        "invoice_number": {"confidence": 0.99}, 
        "supplier": {"confidence": 0.99}, 
        "invoice_date": {"confidence": 0.99}
    }
    
    # Passed validation, high confidence -> AUTO_APPROVED
    res = calculate_routing_decision("invoice", 0.95, data, True)
    assert res["decision"] == "AUTO_APPROVED"
    
    # Failed validation forces review
    res_fail = calculate_routing_decision("invoice", 0.95, data, False)
    assert res_fail["decision"] == "NEEDS_REVIEW"