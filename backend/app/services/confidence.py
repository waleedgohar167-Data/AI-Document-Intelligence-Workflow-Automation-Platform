import os

# Configurable via environment variable
AUTO_APPROVE_THRESHOLD = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.85"))

def calculate_overall_confidence(classification_score: float, extracted_data: dict, validation_passed: bool) -> dict:
    field_scores = []
    
    # Recursively find all 'confidence' keys in the nested extraction dict
    def extract_confidences(d):
        if isinstance(d, dict):
            if 'confidence' in d and isinstance(d['confidence'], (int, float)):
                field_scores.append(d['confidence'])
            for v in d.values():
                extract_confidences(v)
        elif isinstance(d, list):
            for item in d:
                extract_confidences(item)

    extract_confidences(extracted_data)
    
    avg_field_confidence = sum(field_scores) / len(field_scores) if field_scores else 0.0
    
    # Formula: 40% classification, 60% extraction average. 
    overall_confidence = (classification_score * 0.4) + (avg_field_confidence * 0.6)
    
    # Deterministic Override
    review_required = False
    if not validation_passed:
        review_required = True
        overall_confidence = min(overall_confidence, 0.5) # Penalize score if math fails
    elif overall_confidence < AUTO_APPROVE_THRESHOLD:
        review_required = True

    return {
        "overall_confidence": round(overall_confidence, 3),
        "confidence_breakdown": {
            "classification_score": classification_score,
            "average_field_confidence": round(avg_field_confidence, 3),
            "validation_passed": validation_passed,
            "configured_threshold": AUTO_APPROVE_THRESHOLD
        },
        "review_required": review_required
    }