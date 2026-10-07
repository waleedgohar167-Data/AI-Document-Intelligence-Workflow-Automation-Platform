import os

AUTO_APPROVE_THRESHOLD = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.85"))
CRITICAL_FIELD_THRESHOLD = float(os.getenv("CRITICAL_FIELD_THRESHOLD", "0.90"))

CRITICAL_FIELDS = {
    "invoice": ["total", "currency", "invoice_number", "supplier", "invoice_date"],
    "purchase_order": ["po_number", "supplier", "total"],
    "contract": ["parties", "effective_date", "termination_date"]
}

def calculate_routing_decision(doc_type: str, classification_score: float, extracted_data: dict, validation_passed: bool) -> dict:
    field_scores = []
    def extract_confidences(d):
        if isinstance(d, dict):
            if 'confidence' in d and isinstance(d['confidence'], (int, float)): field_scores.append(d['confidence'])
            for v in d.values(): extract_confidences(v)
        elif isinstance(d, list):
            for item in d: extract_confidences(item)

    extract_confidences(extracted_data)
    avg_field_confidence = sum(field_scores) / len(field_scores) if field_scores else 0.0
    overall_confidence = (classification_score * 0.40) + (avg_field_confidence * 0.60)
    
    reasons = []
    if not validation_passed:
        reasons.append("validation_failed")
    if overall_confidence < AUTO_APPROVE_THRESHOLD:
        reasons.append("overall_confidence_below_threshold")
        
    critical_failed = False
    for cf in CRITICAL_FIELDS.get(doc_type, []):
        cf_score = extracted_data.get(cf, {}).get("confidence", 0.0)
        if cf_score < CRITICAL_FIELD_THRESHOLD:
            critical_failed = True
            reasons.append(f"critical_field_{cf}_below_threshold")

    if not validation_passed or overall_confidence < AUTO_APPROVE_THRESHOLD or critical_failed:
        decision = "NEEDS_REVIEW"
    else:
        decision = "AUTO_APPROVED"

    return {
        "overall_confidence": round(overall_confidence, 4),
        "validation_passed": validation_passed,
        "decision": decision,
        "decision_reasons": reasons,
        "configuration": {
            "auto_approval_threshold": AUTO_APPROVE_THRESHOLD,
            "critical_field_threshold": CRITICAL_FIELD_THRESHOLD,
            "confidence_formula_version": "v1.1",
            "validation_policy_version": "v1.1"
        }
    }