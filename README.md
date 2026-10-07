# AI Document Intelligence & Workflow Automation Platform

## 1. Business Scenario & Target User
**Target User:** Finance and Operations teams responsible for receiving, verifying, and routing inbound business documents.
**Business Problem:** Manually reviewing and cross-referencing math and dates on Invoices, Purchase Orders, and Contracts is error-prone and time-consuming. 
**Target Workflow (Day 1 Scope):** Establish a deterministic backend that enforces strict business rules on extracted data before it can be saved or routed. 

## 2. Supported Documents (V1)
The system currently defines strict schemas for:
*   **Invoices:** Validates that `subtotal + tax == total`, `invoice_date <= due_date`, and checks for supported currencies.
*   **Purchase Orders:** Validates that the sum of line items matches the PO total.
*   **Contracts:** Validates that the `effective_date <= termination_date`.

## 3. Architecture V0 (Data Flow)
Our initial architecture isolates the backend data validation from the (future) probabilistic LLM layer.

```text
Next.js UI
    ↓
FastAPI (Backend API)
    ↓
PostgreSQL / Object Storage
    ↓
Document Processing Pipeline
  [Upload]
    ↓
  [Store document]
    ↓
  [Create document record]
    ↓
  [Future: Parse/OCR]
    ↓
  [Future: Classification]
    ↓
  [Future: Extraction]
    ↓
  [Current: Deterministic Validation] (Pydantic)
    ↓
  [Future: Human Review / Persistence]

  ## Pipeline Architecture & Status

*   ✅ **Upload & Storage API** (Implemented)
*   ✅ **Parse/OCR** (Implemented)
*   ✅ **Classification** (Implemented - Deterministic Heuristic)
*   ✅ **Extraction** (Implemented - Pydantic Validation)
*   ✅ **Deterministic Validation** (Implemented - Strict Business Rules)
*   ✅ **Confidence Aggregation** (Implemented - Dual Signal)
*   ✅ **Human-in-the-Loop / Auto Approval** (Implemented)
*   ✅ **Persistence & Audit Events** (Implemented)
*   ⏳ **Workflow Automation & Webhooks** (Planned for Future)
*   ⏳ **Semantic Search / RAG** (Planned for Future)