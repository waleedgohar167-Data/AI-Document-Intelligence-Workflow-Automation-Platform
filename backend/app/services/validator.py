from datetime import date

def validate_document(doc_type: str, extracted_data: dict, missing_fields: list) -> dict:
    failures = []
    
    # 1. Check missing fields globally
    for field in missing_fields:
        failures.append({"field": field, "rule": "required_field_not_null", "actual_value": "null"})

    if doc_type == "invoice":
        # Subtotal + Tax == Total
        sub = extracted_data.get("subtotal", {}).get("value", 0.0)
        tax = extracted_data.get("tax", {}).get("value", 0.0)
        tot = extracted_data.get("total", {}).get("value", 0.0)
        if sub is not None and tax is not None and tot is not None:
            if abs((sub + tax) - tot) > 0.01:
                failures.append({"field": "total", "rule": "math_subtotal_plus_tax", "actual_value": str(tot)})
            if sub < 0 or tax < 0 or tot < 0:
                failures.append({"field": "amounts", "rule": "must_be_positive", "actual_value": f"sub:{sub}, tax:{tax}, tot:{tot}"})

        # Dates
        inv_date = extracted_data.get("invoice_date", {}).get("value")
        due_date = extracted_data.get("due_date", {}).get("value")
        if inv_date and due_date:
            if inv_date > due_date:
                failures.append({"field": "invoice_date", "rule": "before_or_equal_to_due_date", "actual_value": f"{inv_date} > {due_date}"})

        # Currency
        currency = extracted_data.get("currency", {}).get("value")
        if currency and currency not in ["USD", "EUR", "GBP", "PKR", "AED"]:
            failures.append({"field": "currency", "rule": "accepted_currency_set", "actual_value": str(currency)})

    elif doc_type == "purchase_order":
        items = extracted_data.get("items", [])
        calculated_total = 0.0
        for i, item in enumerate(items):
            qty = item.get("quantity", {}).get("value", 0.0)
            price = item.get("unit_price", {}).get("value", 0.0)
            if qty < 0:
                failures.append({"field": f"items[{i}].quantity", "rule": "must_be_positive", "actual_value": str(qty)})
            if price < 0:
                failures.append({"field": f"items[{i}].unit_price", "rule": "must_be_positive", "actual_value": str(price)})
            calculated_total += (qty * price)
            
        tot = extracted_data.get("total", {}).get("value")
        if tot is not None and abs(calculated_total - tot) > 0.01:
            failures.append({"field": "total", "rule": "line_items_match_total", "actual_value": str(tot)})

    elif doc_type == "contract":
        eff_date = extracted_data.get("effective_date", {}).get("value")
        term_date = extracted_data.get("termination_date", {}).get("value")
        if eff_date and term_date:
            if term_date < eff_date:
                failures.append({"field": "termination_date", "rule": "after_or_equal_to_effective_date", "actual_value": f"{term_date} < {eff_date}"})
                
        parties = extracted_data.get("parties", {}).get("value", [])
        if len(parties) < 2:
            failures.append({"field": "parties", "rule": "at_least_two_parties", "actual_value": str(parties)})
            
        if not extracted_data.get("governing_law"):
             failures.append({"field": "governing_law", "rule": "required_field_not_null", "actual_value": "null"})

    return {
        "passed": len(failures) == 0,
        "failures": failures
    }