# Architecture & Design — Aster & Row Support Agent

## Architecture Principles
1. **Determinism First:** Core routing, order lookups, privacy filtering, source precedence rules, and handoff logic are handled by explicit Python logic rather than unconstrained LLM loops.
2. **Strict Component Separation:** Clear boundaries between Retrieval (RAG), Order Tooling, Safety/Privacy Guardrails, Session Management, and LLM Response Generation.
3. **Defense-in-Depth Privacy & Safety:** PII and internal fields are stripped before data touches the LLM prompt. Untrusted retrieved text or tool output is isolated from system instructions.

## Component Overview

```
                          +-------------------+
                          |   User Message    |
                          +---------+---------+
                                    |
                                    v
                          +-------------------+
                          |  Session Manager  |
                          | (Context & History)|
                          +---------+---------+
                                    |
                                    v
                          +-------------------+
                          |   Intent Router   |
                          | (Order vs RAG vs  |
                          |  Unsupported)     |
                          +----+---------+----+
                               |         |
               +---------------v-+     +-v-------------------+
               |  Order Tool     |     |   RAG Retrieval     |
               | - ID Normalize  |     | - Front-matter      |
               | - Lookup json   |     | - Precedence filter |
               | - Privacy filter|     | - Vector / TF-IDF   |
               | - Status logic  |     | - Conflict check    |
               +-------+---------+     +---------+-----------+
                       |                         |
                       +------------+------------+
                                    |
                                    v
                          +-------------------+
                          | Safety & Grounding|
                          |  Guardrails       |
                          +---------+---------+
                                    |
                                    v
                          +-------------------+
                          | LLM Response Gen  |
                          | (Grounded Output) |
                          +---------+---------+
                                    |
                                    v
                          +-------------------+
                          | Final Output with |
                          | Sources & Handoff |
                          +-------------------+
```

### Module Breakdown

1. `src/config.py`: System configuration, model parameters, path constants (`snapshot_at`, filenames).
2. `src/models.py`: Pydantic data structures (`DocumentMetadata`, `Chunk`, `OrderResult`, `AgentResponse`, `EvaluationCase`, `DebugTrace`).
3. `src/rag/`:
   - `document_parser.py`: YAML front-matter extractor and metadata validator.
   - `chunker.py`: Heading-aware Markdown splitter.
   - `retriever.py`: Hybrid TF-IDF / Cosine similarity retriever over indexed markdown chunks.
   - `precedence.py`: Authoritative filtering and conflict detection module.
4. `src/tools/`:
   - `order_tool.py`: Order status lookup, ID normalization, privacy filter, stale ETA suppressor, status rules.
5. `src/agent/`:
   - `session.py`: In-memory multi-turn conversation session manager.
   - `router.py`: Deterministic intent classifier (Order Lookup, Policy RAG, Unsupported Action).
   - `safety.py`: Prompt injection detection, system prompt shielding, privacy enforcement.
   - `support_agent.py`: Main support agent orchestrator compiling response, citations, and handoff flag.
6. `src/observability.py`: Structured logger capturing full debug trace for every turn.
7. `evaluation/evaluate.py`: Comprehensive test runner evaluating accuracy, citations, tool calls, privacy, and handoff across all evaluation cases.
