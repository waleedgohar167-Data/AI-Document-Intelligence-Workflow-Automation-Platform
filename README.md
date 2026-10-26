AI Document Intelligence and Workflow Automation Platform

Project Title and One Line Description

A Python and FastAPI prototype that accepts business documents and provides components for text parsing, simulated structured extraction, validation, review routing, retrieval, and webhook workflows.

Maturity: Independent engineering project for local evaluation, with implemented components, simulations, and incomplete integrations; it is not a commercially deployed client product.

Business Problem

Finance, procurement, and operations teams receive invoices, purchase orders, and contracts whose contents must be transferred into structured business records. Different document layouts make consistent capture, validation, and downstream processing difficult.

The costs include staff time spent reading and re-entering fields, rework when records disagree, delayed approvals, and time spent investigating failed transfers. Those costs depend on document volume, complexity, and existing processes; this project has not measured customer savings or financial impact.

Manual processing scales with the number of documents and the people available to review them. As volume grows, teams need a consistent way to validate records, identify exceptions, track decisions, and recover failed integrations without repeatedly reconstructing what happened.

Solution Overview

The platform's intended workflow combines document ingestion, parsing, classification, structured extraction, deterministic validation, review decisions, searchable context, and downstream delivery behind a Python API.

The implementation separates those responsibilities into services around local file storage and a relational database. This makes the individual rules and interfaces inspectable, while keeping the initial development environment relatively small.

Current outputs: an upload acknowledgement with a document identifier, stored document/job records, component-level parsing and validation outputs, simulated structured-field responses, and retrieval endpoint responses. Review and webhook modules exist in source but are not fully integrated into the running application.

Intended client outputs after integration: validated structured records, explicit review outcomes, source references, delivery results, and an audit history. A complete upload-to-delivery workflow has not yet been verified at the documented revision. Live model extraction, semantic embeddings, and generated answers are not implemented.

Complete Architecture

The architecture is a modular backend rather than a deployed set of independent services. The diagram is embedded below; dashed connections identify broken or incomplete integration, not a successful end-to-end execution.

flowchart TD
    A["Document upload API"] --> B["MIME, signature and size checks"]
    B --> C["Local files and SQLite document/job records"]
    C --> D["Polling worker"]
    D -. "blocked by audit schema mismatch" .-> E["PDF, image or DOCX parsing"]
    E --> F["Keyword classification"]
    F --> G["Simulated field extraction"]
    G --> H["Validation and confidence routing"]
    H -. "integration incomplete" .-> I["Human review"]
    H -. "integration incomplete" .-> J["Keyword retrieval and Q&A scaffold"]
    H -. "integration incomplete" .-> K["Webhook dispatch and failed-payload queue"]
    B -->|"invalid signature event"| L["SQLite audit records"]
    K --> L
    D -. "logging defect" .-> L

Component

Responsibility and connection

FastAPI application

Registers document and knowledge routes and exposes interactive API documentation; review, audit, and workflow routers are currently omitted.

Upload gateway

Checks the claimed MIME type, header bytes, and size before storing accepted files and creating document/job records.

Local source storage

Keeps uploads in storage/documents/ under generated identifiers; workers obtain the file path from the document record.

Relational persistence

Stores documents, processing jobs, audit events, and failed webhook payloads in SQLite through SQLAlchemy.

Polling worker

Claims queued jobs using a conditional database update and contains the processing sequence; its first processing audit call currently fails.

Parser and OCR

Extracts native PDF text, falls back to Tesseract where a page has insufficient native text, reads images, and extracts DOCX paragraphs into normalized blocks.

Classifier

Matches keywords in parsed text to invoice, purchase-order, contract, or unknown categories.

Structured extractor

Produces fixed example responses, parses their JSON, applies Pydantic models, and identifies missing required fields; a real model call is absent.

Validator and routing policy

Check selected required-field, arithmetic, and date rules and combine supplied confidence scores to choose automatic approval or review.

Review router

Defines field correction, approval, and rejection actions; it needs registration and compatible audit logging before use.

Retrieval service and knowledge routes

Define an approval-gated index, keyword matching, and context/citation responses; indexing defects and missing integration currently prevent normal population through the upload workflow.

Workflow service and routes

Define JSON webhook dispatch, bounded backoff, failed-payload persistence, a mock receiver, and replay; approval does not currently trigger the service.

Audit trail

SQLite triggers reject ordinary updates and deletes to audit rows; upload rejection and workflow code emit events, while worker/review logging is incompatible with the model.

Data flow: accepted uploads create a pending document and a queued job; the worker is intended to parse the source, store normalized JSON in storage/parsed/, classify and validate fields, and persist the resulting decision. Approved records are intended to feed retrieval and delivery. Audit records provide event history where logging is implemented correctly; they are not yet a complete trace of that lifecycle.

The SQLite path and storage directories are relative to the process working directory. The retrieval list is process-local memory: it is lost on restart and is not shared between a separately running API and worker.

Complete Pipeline

The sequence below describes each stage and its current implementation boundary.

Upload: The API checks supported MIME types, header signatures, and a 10 MiB size limit, then stores the source file and job records so processing has a traceable input.

Parse/OCR: The parsing service converts PDF, image, or DOCX content into normalized text blocks so downstream functions can operate on text, although the current worker fails before reaching this stage.

Classify: Keyword rules assign a supported category or unknown so the next stage can select an appropriate field schema.

Extract: The current extractor returns simulated field values and validates their JSON/schema shape to exercise downstream logic; real document-dependent model extraction remains pending.

Validate: Deterministic functions check required fields and selected arithmetic/date relationships to identify defined inconsistencies before approval.

Confidence Score: The routing service combines classification and supplied field scores to apply a review policy, with scores treated as configuration inputs rather than measured probabilities of correctness.

Auto Approve or Human Review: The routing function returns an approval or review decision based on validation and thresholds, while manual-review endpoints remain unregistered and require fixes.

Persist: SQLAlchemy models store document, job, extraction, validation, and event data so state can be inspected, but completion of the worker's final persistence path is blocked by its logging defect.

Search: The retrieval prototype ranks in-memory chunks using query-word matches to locate candidate context, with automatic indexing still unconnected and affected by metadata/status mismatches.

Q&A: The query endpoint returns an empty-context response or a context-count message with citation strings to expose retrieval context; factual answer generation is not implemented.

Workflow: The dispatch service attempts delivery to a local mock destination and stores persistently failed payloads for replay, but it is not yet invoked by the approval path.

Audit: Event-producing components append database records to support inspection of system actions, with worker/review compatibility and lifecycle completeness still outstanding.

Section 6 — Technology Stack

Technology

Role and reason for use

Python

Provides a common language for API handlers, parsing, validation, orchestration, and tests.

FastAPI

Defines HTTP routes and generates an inspectable OpenAPI contract for local evaluation.

Uvicorn

Runs the FastAPI application as an ASGI server.

Pydantic v2

Defines document and field structures and checks JSON values against declared types.

SQLAlchemy

Maps document, job, audit, and failed-delivery records to relational tables.

SQLite

Supplies local file-backed persistence without requiring a separate database server.

pdfplumber

Extracts native PDF text and renders PDF pages for OCR fallback.

Tesseract and pytesseract

Provide a local OCR engine and Python wrapper for images and scanned pages.

Pillow

Opens and handles image inputs used by the OCR path.

python-docx

Reads DOCX paragraphs into the same normalized representation used downstream.

Python decimal.Decimal

Supports decimal arithmetic in selected validation rules; extraction schemas still contain floating-point fields.

Python keyword rules and in-memory lists

Provide inspectable classification and retrieval baselines without training or external model services.

requests

Sends the workflow service's HTTP webhook payloads.

pytest

Runs the existing component and selected API/database checks.

FastAPI TestClient and httpx

Exercise registered API handlers from the test suite.

FPDF (fpdf import)

Generates the small synthetic PDF example set; it is not required to start the API.

Docker and Docker Compose

Describe a containerized API launch, although the supplied configuration still needs dependency, OCR, worker, and persistence corrections.

Git and GitHub

Version the implementation and provide source references for review.

No live OpenAI/other LLM API, embedding model, external vector database, Redis broker, or production ERP connection is part of the documented runtime.

Key Engineering Decisions

These five choices describe the implementation and its design alternatives; they do not imply that all integrations are complete.

Decision

Alternative considered

Reason and accepted trade-off

Inspect file-header bytes alongside the claimed MIME type.

Trust extensions or client-provided MIME headers alone.

Header checks catch simple mismatches before processing, but cannot establish complete file validity or malware safety.

Separate deterministic validation from extraction.

Rely on model self-validation or a confidence score alone.

Explicit rules make arithmetic and date checks inspectable, at the cost of maintaining schema-specific logic; passing them does not prove source accuracy.

Use SQLite and SQLAlchemy for local persistence.

Require a PostgreSQL service for initial development.

Local setup stays smaller, while concurrent writes, migrations, and multi-instance operation need further engineering; the current database URL is hard-coded.

Store exhausted webhook deliveries in a database-backed dead-letter queue.

Retain failed payloads only in memory or application logs.

Stored payloads can support later inspection and replay, while transactional consistency, idempotency, and integrated recovery tests remain necessary.

Gate retrieval indexing on approval status.

Index every uploaded document immediately.

The intended gate excludes unreviewed data, but status conventions, indexing defects, revocation behavior, and application integration must be reconciled before relying on it.

Evaluation Results

Day 11 benchmark status

No reproducible Day 11 model-quality benchmark results were supplied. The later component-test run in Section 13 is reported separately and is not presented as Day 11 evaluation evidence.

Evaluation area

Genuine result available

Interpretation

Classification

No validated accuracy, precision, recall, or F1 benchmark.

Keyword examples exist in tests, but there is no representative labeled classification evaluation.

Extraction

No validated field exact-match or extraction-quality benchmark.

Tests validate fixed simulated outputs and error cases, not real extraction from varied source documents.

Retrieval

No validated recall-at-k or ranking benchmark.

Search uses keywords and an in-memory list; there is no verified query/relevance dataset or semantic retrieval evaluation.

Generation

No validated faithfulness or citation-correctness benchmark.

Answer generation is absent and the supplied judge script simulates judgments.

Dataset description

generate_dataset.py creates five synthetic examples in evaluation_dataset/:

File

Purpose

1_valid_invoice.pdf

Small invoice-text example.

2_valid_contract.pdf

Small contract-text example.

3_valid_receipt.pdf

Receipt example outside the classifier's three named target categories.

4_noise_email.pdf

Unrelated text packaged as a PDF.

5_malicious_fake.pdf

Plain text with a PDF extension, intended to exercise header rejection; it is not malware.

This is a smoke-test set, not a representative business dataset. The earlier description of a 45-document evaluation corpus is not substantiated by the supplied generator and checked-in examples.

What the evaluation scripts actually measure

evaluate_metrics.py checks upload HTTP responses and averages request duration; it does not wait for the worker, calculate classification/extraction quality, or measure end-to-end latency percentiles.

evaluate_faithfulness.py uses a keyword condition to simulate judgments; it does not call an LLM judge.

The existing EVALUATION.md contains numerical claims not established by these scripts and requires correction before it can be treated as evaluation evidence.

Known failure cases and verification limits

The earlier source-review checks reproduced a worker TypeError from incompatible audit fields and an indexing AttributeError from doc.filename. They also confirmed native extraction from a generated text PDF, upload acceptance, invalid-header rejection, and an empty-index query response. These are individual behavior checks, not a completed end-to-end evaluation.

Classification ambiguity, scanned-document OCR quality, noisy layouts, and real model behavior have no measured failure rates. Future results should include dataset provenance, labels, scoring code, the exact commit/environment, and raw outputs.

Demonstration

Loom link: pending — a final accessible recording has not been supplied.

The planned walkthrough will show the locally running application with a non-sensitive sample document, explain the processing and validation decisions, and identify implemented functions, simulations, and outstanding integration work. A complete upload-to-delivery demonstration requires the blockers in Section 14 to be resolved and retested. This paragraph describes the recording plan, not a video that has already been completed.

API Documentation

Base URL: http://127.0.0.1:8000. There is no /api/v1 prefix in the reviewed application. Swagger UI and OpenAPI JSON describe the registered routes when the API is running.

Examples below use illustrative identifiers and timestamps; they are API-contract examples, not saved execution evidence.

Registered endpoints

1. Upload document

Method/path: POST /documents

Request: multipart/form-data with one file; supported claimed types are PDF, JPEG, PNG, and DOCX, with a 10 MiB limit and matching header bytes.

Response: JSON containing document_id and status; success means ingestion accepted, not processing complete.

Example request from the repository root on macOS/Linux/WSL:

curl -X POST http://127.0.0.1:8000/documents \
  -F "file=@evaluation_dataset/1_valid_invoice.pdf;type=application/pdf"

Example success response (200):

{"document_id": "550e8400-e29b-41d4-a716-446655440000", "status": "success"}

Relevant errors include 400 for a mismatched signature, 413 for size, 415 for unsupported MIME type, and 500 for storage/database failure.

2. Search document context

Method/path: POST /knowledge/search

Request: JSON with a string query.

Response: JSON with a results array of chunk/relevance-score objects, or an empty array; current ranking is keyword-based.

Example request:

POST /knowledge/search HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{"query": "invoice total"}

Example response for an empty index:

{"results": []}

3. Query knowledge context

Method/path: POST /knowledge/query

Request: JSON with a string query.

Response: JSON with an answer string and a citations array; with matches, the current answer is a context-count message rather than a generated factual answer.

Example request:

POST /knowledge/query HTTP/1.1
Host: 127.0.0.1:8000
Content-Type: application/json

{"query": "What is the invoice total?"}

Example response for an empty index:

{
  "answer": "No relevant documents found. I cannot answer this from general knowledge.",
  "citations": []
}

4. Health stub

Method/path: GET /health

Request: No body.

Response: JSON with a timestamp and static status fields; this does not check database connectivity or worker readiness.

Example request: GET /health.

{
  "status": "healthy",
  "timestamp": "2026-10-26T16:00:00",
  "database": "disconnected_v0",
  "worker_queue": "disconnected_v0"
}

Defined endpoints that are not registered

The following seven routes exist in source but currently return routing-level 404 responses through app.main. Their source-declared contracts are documented below; displayed success responses are illustrative and require router registration, relevant fixes, valid records, and verification. Reviewer identifiers are caller-supplied, not authenticated identities.

5. Approve a reviewed document

Method/path: POST /review/{document_id}/approve

Request: Path identifier and required query parameter reviewer_id; no body; the source handler requires document status needs_review.

Example request: POST /review/demo-doc-001/approve?reviewer_id=reviewer-demo

Declared response: JSON {"status": "approved"}; missing records and invalid states have 404/400 branches, while the current audit-field mismatch prevents successful completion.

6. Reject a reviewed document

Method/path: POST /review/{document_id}/reject

Request: Path identifier and JSON strings reason and reviewer_id; document status must be needs_review.

Example request: POST /review/demo-doc-001/reject with:

{"reason": "Source document requires clarification", "reviewer_id": "reviewer-demo"}

Declared response: JSON {"status": "rejected"}; the current audit-field mismatch also affects this action.

7. Correct a field

Method/path: PATCH /review/{document_id}/fields

Request: JSON strings field_name, corrected_value, and reviewer_id, plus optional reason; document status must be needs_review.

Example request: PATCH /review/demo-doc-001/fields with:

{
  "field_name": "total",
  "corrected_value": "110.00",
  "reviewer_id": "reviewer-demo",
  "reason": "Checked against the sample document"
}

Declared response: JSON such as {"status": "updated", "new_decision": "NEEDS_REVIEW"}; the routing decision can alternatively be AUTO_APPROVED, but logging and validation integration require correction.

8. Read a document's audit history

Method/path: GET /documents/{document_id}/audit

Request: Path identifier; no body.

Example request: GET /documents/demo-doc-001/audit

Declared response: A chronological JSON array of event objects; no matching events produces a 404 branch.

[
  {
    "event_id": "event-demo-001",
    "event_type": "WORKFLOW_TRIGGERED",
    "actor": "system",
    "timestamp": "2026-10-26T16:00:00",
    "payload": {"destination": "http://127.0.0.1:8000/mock-erp/ingest"},
    "model_version": null,
    "policy_version": null
  }
]

9. List audit events

Method/path: GET /audit/events

Request: Optional query parameter event_type; no body.

Example request: GET /audit/events?event_type=WORKFLOW_TRIGGERED

Declared response: A JSON array of up to 100 recent event summaries, newest first.

[
  {
    "event_id": "event-demo-001",
    "event_type": "WORKFLOW_TRIGGERED",
    "timestamp": "2026-10-26T16:00:00"
  }
]

10. Send to the mock ERP receiver

Method/path: POST /mock-erp/ingest

Request: JSON payload for a local receiver, not a real ERP connector.

Example request: POST /mock-erp/ingest with:

{"event_type": "document.approved", "data": {"document_id": "demo-doc-001"}}

Declared response: JSON {"status": "success", "message": "Payload accepted by Mock ERP"}; setting data.document_id to FAIL_ME selects the handler's simulated 500 failure branch.

11. Replay a failed webhook payload

Method/path: POST /workflows/dlq/{dlq_id}/replay

Request: Existing dead-letter queue identifier; no body.

Example request: POST /workflows/dlq/demo-dlq-001/replay

Declared response: JSON {"status": "success", "message": "Replay successful"} after successful redelivery; the source also defines 404 for a missing entry, 400 for an already replayed entry, and 500 for another delivery failure.

Section 12 — Running Locally

These steps launch the current API in a separate local data directory. They do not repair the integration defects or enable an end-to-end workflow. Setup duration has not been measured, so an under-15-minute installation is a target rather than a verified result.

Prerequisites

Git and Python with venv support; the reference verification used Python 3.12.14.

Access to Python package downloads and a writable local working directory.

For image/scanned-page OCR, the Tesseract executable must be installed separately and available on PATH; pytesseract does not include it.

Non-sensitive sample documents; the repository includes synthetic PDF examples.

1. Clone the documented revision

git clone https://github.com/waleedgohar167-Data/AI-Document-Intelligence-Workflow-Automation-Platform.git
cd AI-Document-Intelligence-Workflow-Automation-Platform
git checkout d63d8229b4b5c4d5b919caddf0b6d3db1c40db4d
python -m venv .venv

The checkout pins the source inspected for this README. When code is fixed, update the documented revision and repeat the relevant verification.

2. Activate the environment

macOS/Linux:

source .venv/bin/activate

Windows PowerShell:

.\.venv\Scripts\Activate.ps1

3. Install the reference dependencies

The checked-in requirements file omits several imported packages. These explicit top-level versions match the earlier verification environment; a complete repository dependency lock remains outstanding.

python -m pip install --upgrade pip
python -m pip install fastapi==0.162.0 uvicorn==0.54.0 pydantic==2.14.1 sqlalchemy==2.1.6
python -m pip install python-multipart==0.0.32 httpx==0.28.1 pytest==9.1.1 requests==2.34.2
python -m pip install pdfplumber==0.11.9 pytesseract==0.3.13 Pillow==12.3.0 python-docx==1.2.0

If exercising OCR, check the separate system installation:

tesseract --version

The existing PDF examples can be used without running the generator. Regenerating them requires the FPDF Python package, which is not part of the API dependency set above.

4. Start the API with separate local data

From the repository root with the virtual environment active:

python -c "from pathlib import Path; Path('.local-run').mkdir(exist_ok=True)"
cd .local-run
python -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8000 --reload

This stores documents.db and storage/ beneath .local-run, avoiding use of the database already checked into backend.

Open Swagger UI or ReDoc. Registered upload and knowledge endpoints can be inspected here. An upload acknowledgement does not mean the document has completed processing.

5. Worker execution boundary

The API does not start the worker. After repairing the worker audit defect, activate the same environment in another terminal, use the same .local-run directory, and run:

python ../backend/worker.py

Sharing a working directory aligns the SQLite and file paths; it does not make the in-memory retrieval index shared across processes or connect the missing approval callbacks.

Environment variables and configuration

Setting

Current behavior

AUTO_APPROVE_THRESHOLD

Read from the process environment by the routing service; default 0.85.

CRITICAL_FIELD_THRESHOLD

Read from the process environment; default 0.90.

DATABASE_URL

Not consumed by the current database module; its SQLite URL is hard-coded.

OPENAI_API_KEY

Not used by the simulated extractor; providing a key does not add a model integration.

.env files

Not automatically loaded by the current application.

Webhook destination

Set in the Python WORKFLOW_MAPPINGS dictionary and currently points to a local mock endpoint.

To override routing thresholds on macOS/Linux, export them in the worker's terminal before launch:

export AUTO_APPROVE_THRESHOLD=0.85
export CRITICAL_FIELD_THRESHOLD=0.90

Equivalent Windows PowerShell syntax:

$env:AUTO_APPROVE_THRESHOLD = "0.85"
$env:CRITICAL_FIELD_THRESHOLD = "0.90"

These are policy thresholds, not measured accuracy. The score formula is 0.40 * classification_score + 0.60 * average_field_score, with validation failure and critical-field checks evaluated separately.

Container status

The Dockerfile and Compose configuration are included but have not been validated as a complete installation path. They inherit the incomplete dependency manifest, omit the Tesseract executable, and launch only the API. Correct those issues and define worker/storage behavior before presenting Docker startup as a reproducible workflow.

Testing

Recorded component-test run

The existing suite at commit d63d822 completed with 39 tests passed and 4 warnings during the 26 October 2026 documentation review, using Python 3.12.14, the reference dependencies, a fresh temporary SQLite database, and no application-source changes. This is a component-test result, not a model benchmark or a claim of complete coverage.

Test area

Count

What the tests exercise

Audit

2

Ordinary update/delete rejection through SQLite triggers.

Classification

5

Selected keyword categories, unknown text, and low-score behavior.

Extraction

5

Fixed simulated responses, missing fields, and invalid JSON.

Validation and routing

10

Selected arithmetic/date rules and confidence-policy boundaries.

Ingestion

3

Upload acknowledgement/records, unsupported MIME type, and size rejection.

Parsing and jobs

4

Normalized-output helpers, text-usability checks, job claiming, and state updates.

Retrieval

6

Selected in-memory behavior, revocation, empty context, and an isolated authorization illustration.

Schemas

2

Invoice schema acceptance and arithmetic rejection.

Workflow

2

An approval gate and a dispatcher return-value check.

Total

39

Selected components and API/database behavior.

No coverage percentage was measured. The suite does not prove live OCR/model quality, a functioning complete worker run, real tenant isolation, successful approved-document indexing, DLQ replay through the API, or load resilience. The workflow test accepts either boolean result without asserting successful delivery or a persisted DLQ entry; the tenant example does not exercise application authorization.

Run the suite

In a disposable checkout with a fresh database, the standard command from backend is:

python -m pytest tests -v

Some tests delete document/job rows from the configured database. Use an isolated working directory instead of a database containing records you need to retain.

From the repository root on macOS/Linux/WSL, with the virtual environment active:

python - <<'PY'
import os
import sys
import tempfile
from pathlib import Path
import pytest

backend = Path("backend").resolve()
sys.path.insert(0, str(backend))
original_directory = Path.cwd()
with tempfile.TemporaryDirectory() as work:
    try:
        os.chdir(work)
        result = pytest.main([str(backend / "tests"), "-q", "-p", "no:cacheprovider"])
    finally:
        database_module = sys.modules.get("app.core.database")
        if database_module is not None:
            database_module.engine.dispose()
        os.chdir(original_directory)
raise SystemExit(result)
PY

For Windows PowerShell, run the same isolated launcher as a here-string:

@'
import os
import sys
import tempfile
from pathlib import Path
import pytest

backend = Path("backend").resolve()
sys.path.insert(0, str(backend))
original_directory = Path.cwd()
with tempfile.TemporaryDirectory() as work:
    try:
        os.chdir(work)
        result = pytest.main([str(backend / "tests"), "-q", "-p", "no:cacheprovider"])
    finally:
        database_module = sys.modules.get("app.core.database")
        if database_module is not None:
            database_module.engine.dispose()
        os.chdir(original_directory)
raise SystemExit(result)
'@ | python -

The webhook test attempts a request to the local mock address on port 8000. Run it only when that port is unused or belongs to your disposable test application; it is not fully isolated by a mocked transport.

Section 14 — Known Limitations

Limitation

Current impact

Required change

Audit-model mismatch

Worker/review helpers pass event_name and details, but the model defines event_type and payload; the worker raises before entering its processing error handler.

Align helpers and model fields, then test the complete processing/error paths.

Status conventions differ

Worker/review write lowercase approved; indexing/workflow gates expect uppercase APPROVED.

Use a shared status representation and verify transitions across modules.

Index metadata mismatch

doc.filename is absent, and the parser uses page_number rather than the indexer's page lookup.

Correct metadata mapping and test indexing against actual parsed documents.

Missing router/callback integration

Review, audit, and workflow routes are not registered; approval does not invoke indexing or webhook dispatch.

Register the routes and connect actions with explicit failure handling and integration tests.

Simulated extraction and retrieval

Fixed fields/embeddings and keyword ranking cannot establish model extraction or semantic retrieval quality.

Add and evaluate actual integrations; preserve clear simulation labels until then.

Process-local retrieval state

The index is lost on restart and is not shared with a separate worker.

Introduce shared persistence and an indexing/rebuild/revocation strategy.

Incomplete recovery behavior

There is no stale-job recovery policy, and webhook backoff blocks its calling thread.

Define job leases/recovery, delivery idempotency, retry scheduling, and replay tests.

Partial numeric validation

Selected checks use Decimal, but extraction schemas still use floats and standalone validators differ.

Align data types and rule behavior throughout extraction, review, storage, and delivery.

No authentication or tenant enforcement

Caller-supplied reviewer identifiers and public-style API routes do not establish trusted access.

Add authentication, authorization, tenant boundaries, and verified reviewer attribution before real client access.

Audit protection is limited

SQLite triggers block normal row changes but can be altered by a privileged database owner; event coverage is incomplete.

Define an audit threat model, access restrictions, complete event emission, and retention/export controls.

Setup and deployment are incomplete

Dependencies are not fully locked, configuration is partly hard-coded, and Docker does not provide the complete environment.

Complete the manifest/configuration and validate clean installation, migrations, storage, and backup/recovery.

Evidence is incomplete

No validated model benchmark, final Loom recording, or Day 14 screenshot package is included.

Capture verifiable results and evidence from the corrected revision and align every public description.

For a real client deployment, also define the supported document types, acceptable error/review rates, data-handling requirements, monitoring, concurrency expectations, and downstream integration contract. Changing a database URL or adding a model key alone would not make this prototype production-ready.

Future Work

Deliberately deferred scope

The initial design deferred a live LLM integration, an external vector database, trained classification models, and a dedicated review dashboard to focus on backend structure. Those choices are separate from the integration defects above, which require correction rather than being described as intentional omissions.

Next implementation priorities

Restore a complete local path: fix audit fields, status conventions, index metadata, router registration, and approval callbacks; prove the workflow with an integration test using a non-sensitive document.

Make setup reproducible: complete dependency pinning, active configuration loading, isolated tests, and coordinated API/worker startup.

Replace simulated extraction: integrate an explicitly configured model, handle invalid/partial responses, and measure field accuracy on labeled examples while preserving deterministic validation and review routing.

Implement shared retrieval and generation: add persistent indexing, real embeddings where appropriate, source metadata, and grounded answers with a reproducible query/answer evaluation set.

Improve operational controls: implement authenticated access, reviewer attribution, job recovery, webhook idempotency, useful health checks, and monitoring appropriate to the target deployment.

Expand usability and document coverage: build the review interface, improve OCR for difficult layouts/languages, and evaluate broader document sets after the core workflow is verified.

Each completed change should update this README, the portfolio, evaluation material, and demonstration to the same verified revision.
