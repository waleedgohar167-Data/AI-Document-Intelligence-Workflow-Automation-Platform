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

## 6. Deterministic Validation (Module 6)
**Decision:** Built a strict validation rules engine independent of AI extraction. 
**Why:** Probabilistic models hallucinate. Deterministic software does not. By forcing the LLM's math through `abs((sub + tax) - tot) <= 0.01`, we protect downstream ERPs from data corruption.

## 7. Confidence & Human Review (Module 7)
**Decision:** `AUTO_APPROVE_THRESHOLD` is set to `0.85` via Environment Variable. 
**Why:** We aggregate classification (40%) and average field extraction (60%) confidence. Setting it at 0.85 balances automation with risk. Any document failing deterministic validation automatically has its score penalized and is forced into the Human Review Queue, proving that human review is a safety feature, not a failure.

## 8. Financial Precision 
**Decision:** All monetary validations use Python's `Decimal` type instead of `float`.
**Why:** Floating-point math introduces micro-inaccuracies (e.g., `0.1 + 0.2 = 0.30000000000000004`). Financial cross-checks (`subtotal + tax == total`) must be perfectly deterministic. 

## 9. Separating Confidence and Validation Signals 
**Decision:** Removed the artificial confidence score cap of 0.5. 
**Why:** A document can have 99% extraction confidence and still fail a business rule (e.g., `invoice_date > due_date`). Confidence and validation are separate facts. The routing decision evaluates them independently.

## 10. Critical Field Floor 
**Decision:** Auto-approval requires `validation_passed == True`, `overall_confidence >= AUTO_APPROVE_THRESHOLD`, AND all critical fields (e.g., `total`, `invoice_number`) must exceed `CRITICAL_FIELD_THRESHOLD`.
**Why:** Average confidence hides catastrophic localized failures. High confidence on line items cannot compensate for low confidence on the final total.

## 11. Protected Review State Transitions 
**Decision:** Human review endpoints strictly enforce valid state transitions (e.g., `NEEDS_REVIEW -> APPROVED`). 
**Why:** Prevents race conditions, double-approvals, or modifying documents already finalized.

## 12. Reviewer Attribution Security 
**Decision:** Reviewer identity is currently supplied by the API caller. 
**Why:** Authenticated reviewer identity and role enforcement are planned as part of security hardening. This will be addressed when formal JWT authentication is implemented.

## ADR-013: Audit Trail Immutability 
*   **Decision:** Immutability is strictly enforced at the database level using SQLAlchemy `before_update` and `before_delete` event listeners.
*   **Reason:** An audit trail is legally and operationally meaningless if the system (or a bad actor) can retroactively alter history. Raising exceptions at the ORM layer ensures silent status transitions are impossible.
*   **Decision:** Model and Policy versions are snapshotted on every event payload.
*   **Reason:** If the `AUTO_APPROVE_THRESHOLD` changes from 0.85 to 0.90, we must be able to explain exactly why a document was approved six months ago under the old policy.

## ADR-014: RAG Chunking Strategy 
*   **Decision:** Chunking maps directly to the parser's OCR/Text blocks (approx. paragraph size) rather than arbitrary character limits.
*   **Reason:** This preserves natural semantic boundaries and perfectly maps text back to its exact `page_number` for frontend UI highlighting and strict Q&A citation grounding.
*   **Limitations:** Highly complex multi-column tables may get fragmented.

## ADR-015: Vector Embedding Architecture 
*   **Decision:** Built an abstracted `VectorStore` interface currently running in-memory with a heuristic mock embedding for the V1 local review.
*   **Reason:** Forcing reviewers to install C++ compilers for `chromadb` or download heavy PyTorch weights for `sentence-transformers` violates the portability of Day 1. The interface is perfectly cleanly decoupled, allowing production to inject a pgvector/OpenAI implementation with zero changes to the business logic.

## ADR-016: Strict Database-Level Audit Immutability 
*   **Decision:** Replaced SQLAlchemy `before_update` hooks with SQLite native `CREATE TRIGGER` constraints.
*   **Reason:** Application-level enforcement is insufficient because bad actors or rogue scripts could connect directly to the database via raw SQL and modify records, bypassing the ORM entirely. Native DB triggers protect against raw SQL injection, direct DB administration edits, and application layer bypasses.

## ADR-017: Production RAG Implementation & Migration Path 
*   **Decision:** The current V1 system explicitly utilizes a non-persistent in-memory array for vector storage and a heuristic keyword mock for embeddings. This guarantees local portability for architectural review without heavy dependencies.
*   **Production Migration Path:** The array will be replaced by `pgvector` (PostgreSQL) or `ChromaDB`. The mock embeddings will be replaced by `text-embedding-3-small` (OpenAI) or a localized `sentence-transformers` model. 
*   **Evaluation Metrics:** Production retrieval will be validated using the RAGAS framework, specifically measuring Context Precision, Answer Relevance, and Faithfulness.

## ADR-018: OCR Chunking Strategy Limitations 
*   **Observation:** Current chunking maps 1:1 to OCR blocks.
*   **Honest Limitations:** OCR blocks frequently fragment natural semantic boundaries (e.g., a sentence split across two text blocks or pages). Currently, if a chunk logically spans multiple OCR blocks, it is treated as distinct chunks, which could degrade semantic retrieval. If a block theoretically spans pages, it retains the primary page metadata, limiting citation granularity.
*   **Future Improvement:** Implement a sliding-window character/token chunker combined with OCR block metadata to maintain natural sentence boundaries while retaining page citations.