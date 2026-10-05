import json
from pydantic import ValidationError
from app.schemas.classification import NormalizedDocument
from app.schemas.extraction import InvoiceExtraction, POExtraction, ContractExtraction, get_required_fields

def simulate_llm_extraction(doc_type: str, text: str) -> str:
    """Simulate LLM output. In production, this would be a prompt to GPT-4o or Claude."""
    if "INVALID_JSON" in text:
        return "{ oops this is broken json "
        
    if doc_type == "invoice":
        if "MISSING_FIELD" in text:
            # Purposely omit 'invoice_number'
            return '{"supplier": {"value": "Acme", "confidence": 0.99, "source_page": 1, "supporting_text": "Acme Corp"}}'
            
        return json.dumps({
            "invoice_number": {"value": "INV-100", "confidence": 0.95, "source_page": 1, "supporting_text": "INV-100"},
            "supplier": {"value": "Acme Corp", "confidence": 0.98, "source_page": 1, "supporting_text": "Acme Corp"},
            "invoice_date": {"value": "2026-01-01", "confidence": 0.9, "source_page": 1, "supporting_text": "Jan 1, 2026"},
            "due_date": {"value": "2026-01-31", "confidence": 0.9, "source_page": 1, "supporting_text": "Jan 31, 2026"},
            "subtotal": {"value": 400.0, "confidence": 0.99, "source_page": 1, "supporting_text": "$400.00"},
            "tax": {"value": 40.0, "confidence": 0.99, "source_page": 1, "supporting_text": "$40.00"},
            "total": {"value": 440.0, "confidence": 0.99, "source_page": 1, "supporting_text": "$440.00"},
            "currency": {"value": "USD", "confidence": 0.99, "source_page": 1, "supporting_text": "USD"}
        })
    elif doc_type == "purchase_order":
        return json.dumps({
            "po_number": {"value": "PO-999", "confidence": 0.9, "source_page": 1, "supporting_text": "PO-999"},
            "supplier": {"value": "Vendor Inc", "confidence": 0.9, "source_page": 1, "supporting_text": "Vendor Inc"},
            "items": [
                {
                    "description": {"value": "Widget", "confidence": 0.9, "source_page": 1, "supporting_text": "Widget"},
                    "quantity": {"value": 10.0, "confidence": 0.9, "source_page": 1, "supporting_text": "10"},
                    "unit_price": {"value": 5.0, "confidence": 0.9, "source_page": 1, "supporting_text": "$5.00"}
                }
            ],
            "total": {"value": 50.0, "confidence": 0.9, "source_page": 1, "supporting_text": "$50.00"}
        })
    elif doc_type == "contract":
        return json.dumps({
            "parties": {"value": ["Party A", "Party B"], "confidence": 0.9, "source_page": 1, "supporting_text": "Party A and Party B"},
            "effective_date": {"value": "2026-01-01", "confidence": 0.9, "source_page": 1, "supporting_text": "Jan 1, 2026"}
        })
    return "{}"

def extract_structured_data(doc: NormalizedDocument, doc_type: str) -> tuple[dict, list[str]]:
    text = " ".join([b.text for b in doc.blocks])
    raw_json = simulate_llm_extraction(doc_type, text)
    
    try:
        parsed_data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid LLM output (JSON Decode Error): {e}")

    try:
        if doc_type == "invoice":
            model = InvoiceExtraction(**parsed_data)
        elif doc_type == "purchase_order":
            model = POExtraction(**parsed_data)
        elif doc_type == "contract":
            model = ContractExtraction(**parsed_data)
        else:
            raise ValueError(f"Unsupported extraction type: {doc_type}")
    except ValidationError as e:
        raise ValueError(f"Invalid LLM output (Schema Violation): {e}")

    # Check for missing logical requirements
    missing_fields = []
    model_dict = model.model_dump(exclude_none=True)
    for field in get_required_fields(doc_type):
        if field not in model_dict:
            missing_fields.append(field)
            
    return model_dict, missing_fields