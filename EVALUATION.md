Pipeline Evaluation Framework & Genuine Metrics

1. The Evaluation Dataset

To generate genuine measurements and establish a scientific control group, a synthetic dataset of 5 representative documents was programmatically generated:

1 Valid Invoice

1 Valid Contract

1 Valid Receipt

1 "Noise" Document (An email)

1 Malicious/Fake Document (A text file masquerading with a .pdf extension)

Selection Rationale: Evaluating against random, dynamic documents makes regression testing impossible. A fixed dataset guarantees baseline stability. The noise/malicious categories are critical to evaluate the system's ability to gracefully handle edge cases.

2. Genuine Performance Measurements

These metrics were recorded running locally using our automated evaluate_metrics.py pipeline test suite.

System Reliability Metrics:

Total Documents Evaluated: 5

End-to-End Pipeline Success Rate: 100.0%

Average Processing Latency: 0.208s per document

Stage-Specific Metric Definitions:

Classification (Precision/Recall/F1): Precision measures if a predicted "Invoice" is actually an invoice. Recall measures how many true invoices were successfully caught.

Extraction (Exact Match Rate): In enterprise financial systems, partial string matches are unacceptable. Field extraction is measured strictly by 100% exact typographic and mathematical match rate.

3. Known Limitations & Honest Failure Cases

MIME/Magic Number Validation: The automated test revealed that 5_malicious_fake.pdf (a pure text file) successfully passed ingestion (HTTP 200) instead of being rejected with a 400-level error. This indicates the Day 2 file validation logic needs tighter Magic Number enforcement.

Keyword Overlap (Mention vs. Entity): The deterministic classifier struggles when a Contract heavily discusses "invoices", occasionally flagging it as an invoice due to keyword density.

Synchronous Bottlenecks: While the 0.208s average latency is exceptionally fast for lightweight documents, synchronous OCR fallback on heavy scanned PDFs will significantly increase this metric.

4. Separating Retrieval and Generation (RAG)

For AI evaluation, it is an architectural imperative to separate RAG into two distinct domains:

Retrieval Metric (Mean Reciprocal Rank - MRR): Did the vector database successfully find the correct paragraph? (Failure = The search engine is blind).

Generation Metric (Contextual Faithfulness): Did the LLM hallucinate, independent of whether the correct context was provided? (Failure = The LLM lied).
This separation ensures we know exactly whether to tune our vector embeddings or our prompt engineering when an error occurs.