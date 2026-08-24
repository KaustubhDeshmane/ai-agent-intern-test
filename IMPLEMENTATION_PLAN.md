# Implementation Sequence — Aster & Row Support Agent

## Phase 1: Foundation + RAG Infrastructure
- Setup project directory structure (`src/`, `tests/`, `evaluation/`).
- Create configuration (`src/config.py`) and Pydantic models (`src/models.py`).
- Implement `src/rag/document_parser.py`: YAML front-matter parsing and metadata validation.
- Implement `src/rag/chunker.py`: Heading-aware Markdown chunking.
- Implement `src/rag/retriever.py` & `src/rag/precedence.py`: Vector / TF-IDF indexing, metadata filtering (`status == 'active'`, `policy_authority == 'official'`, `audience == 'customer'`), and source conflict detection (`11-product-care.md` vs `12-breeze-tumbler-product-card.md`).
- Write unit tests in `tests/test_rag.py`.
- **Verification:** Run unit tests and ensure all pass cleanly. Verify source knowledge base files remain unmodified.

## Phase 2: Order Tool, Agent & Multi-Turn Conversation
- Implement `src/tools/order_tool.py`:
  - Order ID normalization (`ord-1007` -> `ORD-1007`).
  - Privacy sanitization (strip `email`, `address`, `internal` notes/scores).
  - Status precedence logic (cancelled stale ETA removal, shipped without ETA, exception flag).
  - Unknown / missing order ID handling.
- Implement `src/agent/session.py`: Session memory and context resolution.
- Implement `src/agent/router.py`: Deterministic intent routing.
- Implement `src/agent/support_agent.py`: Agent orchestrator combining RAG, order tool, grounded prompt template, source citation formatting, and handoff rules.
- Write unit tests in `tests/test_order_tool.py`, `tests/test_session.py`, `tests/test_agent.py`.
- **Verification:** Run test suite and fix any failures.

## Phase 3: Safety, Evaluation & Observability
- Implement `src/agent/safety.py`: Prompt injection shield, system prompt protection, privacy compliance check.
- Implement `src/observability.py`: Structured debug logger.
- Implement `evaluation/evaluate.py`:
  - Execute all 13 visible test cases from `evaluation/visible-cases.json`.
  - Implement 5+ original evaluation test cases for edge cases.
  - Generate baseline and final evaluation report broken down by category.
- Update `README.md`, `.env.example`, bug diary, and known limitations.
- **Verification:** Run complete evaluation suite, verify 100% pass rate across visible and custom cases.
