# Architecture Decision Records (ADR)

## ADR-001: Separation of Probabilistic and Deterministic Logic
*   **Decision:** The system will use an LLM for structured extraction, but will strictly pass all AI output through Pydantic validators before persistence.
*   **Reason:** LLMs hallucinate math and dates. A business cannot automatically pay an invoice if `subtotal + tax != total`. 
*   **Trade-off:** Slightly higher latency and development time to write strict schemas, but prevents critical downstream business failures.

## ADR-002: Day 1 Infrastructure
*   **Decision:** Implement FastAPI shell and Pydantic models first. Exclude LangChain, LLMs, and Vector databases for V0.
*   **Reason:** AI extraction is useless if the underlying data routing and validation pipeline does not exist. The core business workflow must dictate the AI architecture, not the other way around.