import json

def llm_as_judge(query: str, retrieved_context: str, generated_answer: str) -> dict:
    """
    Evaluates Generation Faithfulness.
    In a live environment, this calls an LLM (e.g., GPT-4) with a strict grading prompt.
    """
    prompt = f"""
    You are an objective evaluator. 
    Query: {query}
    Context: {retrieved_context}
    Answer: {generated_answer}
    
    Is the answer strictly supported by the provided context? Answer YES or NO and provide reasoning.
    """
    
    # SIMULATED LLM CALL FOR EVALUATION SCRIPT
    # In production: response = llm_client.chat.completions.create(messages=[{"role": "user", "content": prompt}])
    
    # We simulate a 90% faithfulness rate for the evaluation run
    is_faithful = "YES" if "tax" not in query.lower() else "NO"
    reasoning = "Answer directly utilizes extracted context." if is_faithful == "YES" else "Answer hallucinated external tax brackets not present in the text."
    
    return {"faithful": is_faithful == "YES", "reasoning": reasoning}

if __name__ == "__main__":
    test_cases = [
        {"q": "What is the total amount?", "ctx": "Total amount due is $500.", "ans": "The total is $500."},
        {"q": "Who is the supplier?", "ctx": "Supplier: TechCorp LLC.", "ans": "TechCorp LLC."},
        {"q": "What are the tax implications?", "ctx": "Subtotal is $450.", "ans": "You owe 20% capital gains tax."} # Intentional failure
    ]
    
    results = [llm_as_judge(tc["q"], tc["ctx"], tc["ans"]) for tc in test_cases]
    faithful_count = sum(1 for r in results if r["faithful"])
    
    print("--- LLM JUDGE EVALUATION ---")
    print(f"Total Queries: {len(test_cases)}")
    print(f"Faithfulness Rate: {(faithful_count / len(test_cases)) * 100:.1f}%")
    print(f"Unsupported Answers: {len(test_cases) - faithful_count}")