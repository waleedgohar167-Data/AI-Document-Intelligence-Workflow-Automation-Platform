# Architecture Decision Records (ADR)

## ADR-001: Separation of Probabilistic and Deterministic Logic
*   **Decision:** The system will use an LLM for structured extraction, but will strictly pass all AI output through Pydantic validators before persistence.
*   **Reason:** LLMs hallucinate math and dates. A business cannot automatically pay an invoice if `subtotal + tax != total`. 
*   **Trade-off:** Slightly higher latency and development time to write strict schemas, but prevents critical downstream business failures.
         
## ADR-002: Day 1 Infrastructure
*   **Decision:** Implement FastAPI shell and Pydantic models first. Exclude LangChain, LLMs, and Vector databases for V0.
*   **Reason:** AI extraction is useless if the underlying data routing and validation pipeline does not exist. The core business workflow must dictate the AI architecture, not the other way around.


# Day 3: OCR and Parsing Architecture Decisions

## OCR Library Choice: PyTesseract + pdfplumber
**What I chose:** 
I chose `pytesseract` wrapped over Google's Tesseract OCR engine. To handle scanned PDFs seamlessly, I paired it with `pdfplumber`'s internal `.to_image()` functionality.

**Alternatives considered:** 
- AWS Textract / Google Cloud Vision: Offers superior cloud-based accuracy, but introduces external network dependencies, API latency, and authentication barriers not suitable for local V1 pipeline development.
- PyMuPDF + system Poppler: Fast image extraction, but notoriously fragile across different operating systems (especially Windows) due to strict C++ binary dependencies.

**Why this approach is appropriate for this stage:**
Tesseract provides a deterministic, completely local, and free text extraction baseline. By using `pdfplumber` to convert PDF pages into images in-memory, I completely bypassed the need to force the team to install `poppler-utils` on their local machines. This ensures the repository remains highly portable, resilient, and easy to evaluate immediately upon cloning.

**Limitations:**
Tesseract struggles with complex multi-column layouts, heavy skew, and handwritten text without a dedicated pre-processing layer (binarization, deskewing). These edge cases will require an upgrade to cloud-based OCR or a specialized layout parser in a production environment.

# Architectural Decisions & Technical Documentation

## 1. System Architecture (Development vs. Production)
**Current Development Implementation (Day 3):**
- **Database:** SQLite (Relational, file-based).
- **Storage:** Local filesystem (`storage/documents` and `storage/parsed`).
- **Concurrency:** Simulated atomic locks using `UPDATE ... WHERE ...` rowcount checks.

**Intended Production Target:**
- **Database:** PostgreSQL (with `SELECT FOR UPDATE` for strict worker locking).
- **Storage:** Amazon S3 / Cloud Object Storage.

## 2. OCR Technology & "Mixed PDF" Parsing Decision
**Technology Selected:** `pytesseract` combined with `pdfplumber`.
**Logic:** A deterministic heuristic (>50 alphanumeric characters) is run per-page. If usable text exists, native extraction is used. If not, the page is rendered to an image and pushed through OCR.
**Why:** It avoids failing an entire document just because one page is scanned. It allows us to tag the document as `mixed` extraction.
**Limitations:** Positional bounding boxes across native and OCR layers operate on completely different coordinate systems, so position metadata is currently explicitly set to `Null` to avoid data corruption down the pipeline. Complex table structures in OCR pages will require a stronger cloud API (e.g., AWS Textract) in the future.

## 3. Idempotent JSON Persistence
**Decision:** Parsed blocks are saved as JSON files in `storage/parsed/{doc_id}.json`. 
**Why:** By separating the parsed representation into an independent file, the database stays lightweight. It also provides an idempotent structure: if a worker crashes and retries, the JSON file is simply cleanly overwritten without duplicating text blocks in a database table. Document and Job statuses are kept strictly synced.

## 4. Classification Stage (Day 4)
**Approach Chosen:** Deterministic Keyword Frequency Heuristic.
**Alternatives Considered:** 
- *LLM Structured Output (GPT-4o/Claude):* Too costly and slow for initial routing, introduces external API dependencies not ideal for local V1 review.
- *Machine Learning (Random Forest/Naive Bayes via scikit-learn):* Highly effective, but requires a labeled training dataset (TF-IDF vectorization) which doesn't exist yet at this stage of the project.
**Why this is appropriate:** A heuristic engine provides a completely deterministic, zero-dependency baseline. It is instantly testable, requires no model weights, and perfectly demonstrates the core pipeline mechanics (thresholding, DB updates, audit logging).
**Confidence Threshold:** `0.75` (75%). I selected this threshold to ensure that documents with only a single stray keyword match are safely diverted to the `needs_review` state, preventing false positives from progressing to structured data extraction.
**Future Iteration:** In a production V2, this heuristic would be replaced by a locally hosted lightweight Transformer model (e.g., LayoutLMv3) to analyze both spatial structure and semantic meaning, falling back to an LLM only for highly ambiguous `needs_review` edge cases.

## 5. Structured Extraction (Day 5)
**Extraction Schema Design:**
Defined explicit Pydantic models for `Invoice`, `PurchaseOrder`, and `Contract` using a generic `ExtractedField[T]` to encapsulate value, confidence, source_page, and supporting_text.

**Handling non-conforming LLM output:**
All extraction models use strict Python typing (e.g., `date`, `PositiveFloat`). If the LLM generates output that violates these constraints (or emits invalid JSON), a `ValueError` is caught by the worker. The worker absorbs the exception, logs an `EXTRACTION_FAILED` audit event, and safely marks the job as `failed` without crashing the asynchronous polling loop.

**Handling missing required fields:**
To capture partial valid data even if the LLM omits a field, fields are defined as `Optional` in Pydantic. However, a post-validation routine explicitly checks the conceptually "required" fields. If missing, it logs a `REQUIRED_FIELD_MISSING` audit event while preserving the rest of the extraction.

**Why per-field confidence and source tracking matters:**
If an LLM extracts an invoice total of $5,000, a human reviewer must be able to instantly click and see the exact bounding box (`source_page` and `supporting_text`) that generated it. A single document-level confidence score cannot isolate specific hallucinations; per-field confidence allows us to auto-approve 9 fields and flag 1 single field for manual review.