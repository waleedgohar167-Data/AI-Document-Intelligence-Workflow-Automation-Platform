from decimal import Decimal, InvalidOperation

def safe_decimal(val):
    if val is None: return None
    try: return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError): return None

def validate_document(doc_type: str, extracted_data: dict, missing_fields: list) -> dict:
    failures = []
    
    for field in missing_fields:
        failures.append({"field": field, "rule": "required_field_not_null", "actual_value": "null"})

    if doc_type == "invoice":
        sub = safe_decimal(extracted_data.get("subtotal", {}).get("value"))
        tax = safe_decimal(extracted_data.get("tax", {}).get("value"))
        tot = safe_decimal(extracted_data.get("total", {}).get("value"))
        
        if sub is not None and tax is not None and tot is not None:
            if sub + tax != tot:  # Exact Decimal matching
                failures.append({"field": "total", "rule": "math_subtotal_plus_tax", "actual_value": str(tot)})
            if sub < Decimal("0") or tax < Decimal("0") or tot < Decimal("0"):
                failures.append({"field": "amounts", "rule": "must_be_positive", "actual_value": f"sub:{sub}, tax:{tax}, tot:{tot}"})

        inv_date = extracted_data.get("invoice_date", {}).get("value")
        due_date = extracted_data.get("due_date", {}).get("value")
        if inv_date and due_date:
            if inv_date > due_date:
                failures.append({"field": "invoice_date", "rule": "before_or_equal_to_due_date", "actual_value": f"{inv_date} > {due_date}"})

    elif doc_type == "purchase_order":
        items = extracted_data.get("items", [])
        calculated_total = Decimal("0.0")
        for i, item in enumerate(items):
            qty = safe_decimal(item.get("quantity", {}).get("value"))
            price = safe_decimal(item.get("unit_price", {}).get("value"))
            if qty is not None and qty < Decimal("0"):
                failures.append({"field": f"items[{i}].quantity", "rule": "must_be_positive", "actual_value": str(qty)})
            if price is not None and price < Decimal("0"):
                failures.append({"field": f"items[{i}].unit_price", "rule": "must_be_positive", "actual_value": str(price)})
            if qty is not None and price is not None:
                calculated_total += (qty * price)
            
        tot = safe_decimal(extracted_data.get("total", {}).get("value"))
        if tot is not None and calculated_total != tot:
            failures.append({"field": "total", "rule": "line_items_match_total", "actual_value": str(tot)})

    elif doc_type == "contract":
        eff_date = extracted_data.get("effective_date", {}).get("value")
        term_date = extracted_data.get("termination_date", {}).get("value")
        if eff_date and term_date:
            if term_date < eff_date:
                failures.append({"field": "termination_date", "rule": "after_or_equal_to_effective_date", "actual_value": f"{term_date} < {eff_date}"})
                
    return {"passed": len(failures) == 0, "failures": failures}