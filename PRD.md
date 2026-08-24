# Product Requirements Document (PRD) — Aster & Row Reliable RAG Support Agent

## 1. Product Overview
Aster & Row is an ecommerce company selling bags, drinkware, and travel accessories. This project builds a reliable, customer-facing AI Support Agent that answers customer queries about company policies and order statuses with high accuracy, zero hallucinated order info, privacy preservation, prompt injection defense, and reliable handoffs when necessary.

## 2. Key Objectives & Acceptance Criteria

### 2.1 Retrieval-Augmented Generation (RAG)
- **Metadata-Aware Chunking:** Parse YAML front-matter (`status`, `effective_date`, `audience`, `policy_authority`, `supersedes`, `superseded_by`, `customer_answering`).
- **Source Precedence:** 
  - Official, active, customer-facing documents (`status: active`, `policy_authority: official`, `audience: customer`) are authoritative.
  - Legacy/superseded documents (`status: superseded`) are ignored for current policy questions.
  - Drafts and internal notes (`status: draft`, `policy_authority: none`, `customer_answering: false`) are strictly prohibited as authority for customer answers.
- **Source Conflict Detection:** Explicitly surface conflicts between active official sources (e.g. `11-product-care.md` vs `12-breeze-tumbler-product-card.md` regarding Breeze Tumbler dishwasher safety) and trigger human handoff instead of silently picking one.
- **Citations:** Every customer-facing answer based on knowledge documents must cite the filename and relevant section heading.
- **Safe Abstention:** If retrieved knowledge is insufficient, state that information is insufficient and recommend human handoff (`handoff: true`).

### 2.2 Order Status Lookup Tool
- **Order ID Normalization:** Normalize harmless format differences (e.g., lowercasing `ord-1007` or leading/trailing whitespace ` ORD-1007 ` -> `ORD-1007`).
- **Missing / Unknown Order ID:**
  - If order ID is missing: ask the customer for the order ID. Do not invent order status or invoke tool without ID.
  - If order ID is unknown/malformed (e.g. `ORD-9999`): safely inform customer that the order was not found and offer human handoff.
- **Authoritative Status Rules:**
  - `cancelled`: State order is cancelled and will not ship. Suppress stale delivery estimates or tracking details.
  - `returned`: State return was processed. Suppress stale delivery estimates.
  - `shipped` without ETA (`estimated_delivery: null`): State order is shipped with carrier/tracking, but delivery estimate is unavailable. Never invent/calculate an ETA.
  - `exception`: State order has an exception requiring support review, and recommend human handoff.
- **Strict Privacy Isolation:**
  - The model and customer response MUST NEVER contain sensitive fields: `customer.name`, `customer.email`, `customer.shipping_address`, or anything under `internal` (`risk_score`, `warehouse_note`, `support_tags`).

### 2.3 Multi-Turn Conversation
- Maintain session context across turns (e.g., resolving "What about Canada?" after asking "Do you ship internationally?", or "When will it arrive?" after asking "Where is ORD-1007?").
- Maintain isolation between different session IDs.

### 2.4 Safety & Prompt Injection Resistance
- Treat user inputs, retrieved passages, and tool results as untrusted data.
- Ignore prompt injection attempts inside documents or warehouse notes (e.g., instructions telling the agent to ignore rules, give 60-day returns, issue coupons, or reveal hidden prompts).
- Refuse to reveal system prompts, hidden instructions, secrets, or internal data.

### 2.5 Unsupported Actions & Human Handoff
- Order lookup is the ONLY supported action.
- For refund requests, cancellations, address changes, replacements, price adjustments, or warranty approvals: explain policy, state that the action cannot be completed in chat, and recommend human handoff.

### 2.6 Evaluation & Observability
- 100% pass rate on all visible evaluation cases (`evaluation/visible-cases.json`) plus at least 5 original test cases.
- Structured debug logging tracing user query, context, retrieved passages, tool calls, safety checks, and handoff flag.
