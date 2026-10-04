from app.schemas.classification import NormalizedDocument, ClassificationResult

# Task 5: Defined Threshold
CONFIDENCE_THRESHOLD = 0.75

def classify_document(doc: NormalizedDocument) -> ClassificationResult:
    text_content = " ".join([block.text.lower() for block in doc.blocks])
    
    invoice_keywords = {"invoice", "total due", "tax", "due date", "bill to", "remittance"}
    po_keywords = {"purchase order", "po number", "vendor", "shipping", "qty", "unit price", "delivery date"}
    contract_keywords = {"agreement", "parties", "hereby", "terms and conditions", "signature", "confidentiality", "binding"}
    
    scores = {
        "invoice": sum(1 for kw in invoice_keywords if kw in text_content),
        "purchase_order": sum(1 for kw in po_keywords if kw in text_content),
        "contract": sum(1 for kw in contract_keywords if kw in text_content)
    }
    
    max_score = max(scores.values()) if scores.values() else 0
    
    # Task 3: Handle Unknown
    if max_score == 0:
        return ClassificationResult(
            document_type="unknown",
            confidence=0.1,
            classification_method="deterministic_keyword_heuristic",
            reasoning="No identifying keywords found in document text."
        )
    
    best_match = max(scores, key=scores.get)
    confidence = min(max_score / 4.0, 0.95) 
    
    return ClassificationResult(
        document_type=best_match,
        confidence=round(confidence, 2),
        classification_method="deterministic_keyword_heuristic",
        reasoning=f"Matched {max_score} highly specific vocabulary keywords for {best_match}."
    )