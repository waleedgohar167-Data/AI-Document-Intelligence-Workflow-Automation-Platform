import pytest
from app.services.confidence import calculate_routing_decision
from app.services.validator import validate_document

def test_conf_086_passed_auto_approves():
    # Overall: 0.95*0.4 + 0.90*0.6 = 0.92 (>0.85). Critical Fields = 0.90 (Passes floor)
    res = calculate_routing_decision("invoice", 0.95, {"total": {"confidence": 0.90}, "currency": {"confidence": 0.90}, "invoice_number": {"confidence": 0.90}, "supplier": {"confidence": 0.90}, "invoice_date": {"confidence": 0.90}}, True)
    assert res["decision"] == "AUTO_APPROVED"

def test_conf_exactly_at_threshold():
    # Overall: 0.775*0.4 + 0.90*0.6 = 0.85 (Exactly threshold). Critical Fields = 0.90 (Passes floor)
    res = calculate_routing_decision("invoice", 0.775, {"total": {"confidence": 0.90}, "currency": {"confidence": 0.90}, "invoice_number": {"confidence": 0.90}, "supplier": {"confidence": 0.90}, "invoice_date": {"confidence": 0.90}}, True)
    assert res["decision"] == "AUTO_APPROVED"

def test_conf_below_threshold():
    # Overall: 0.75*0.4 + 0.90*0.6 = 0.84 (<0.85). Critical Fields = 0.90 (Passes floor)
    res = calculate_routing_decision("invoice", 0.75, {"total": {"confidence": 0.90}, "currency": {"confidence": 0.90}, "invoice_number": {"confidence": 0.90}, "supplier": {"confidence": 0.90}, "invoice_date": {"confidence": 0.90}}, True)
    assert res["decision"] == "NEEDS_REVIEW"

def test_conf_high_but_validation_fails():
    res = calculate_routing_decision("invoice", 0.99, {"total": {"confidence": 0.99}, "currency": {"confidence": 0.99}, "invoice_number": {"confidence": 0.99}, "supplier": {"confidence": 0.99}, "invoice_date": {"confidence": 0.99}}, False)
    assert res["decision"] == "NEEDS_REVIEW"

def test_one_critical_field_fails():
    # High overall score, but one critical field (total) is 0.40, below the 0.90 floor!
    res = calculate_routing_decision("invoice", 0.99, {"total": {"confidence": 0.40}, "currency": {"confidence": 0.99}, "invoice_number": {"confidence": 0.99}, "supplier": {"confidence": 0.99}, "invoice_date": {"confidence": 0.99}}, True)
    assert res["decision"] == "NEEDS_REVIEW"

def test_decimal_rounding_edge_case():
    data = {"subtotal": {"value": "4250.00"}, "tax": {"value": "425.00"}, "total": {"value": "4675.00"}}
    res = validate_document("invoice", data, [])
    assert res["passed"] == True

def test_invalid_dates_fail():
    data = {"invoice_date": {"value": "2026-10-10"}, "due_date": {"value": "2026-10-01"}}
    res = validate_document("invoice", data, [])
    assert res["passed"] == False