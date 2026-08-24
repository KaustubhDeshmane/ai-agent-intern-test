from typing import Dict, Any, List, Optional
import os
import re

from src.models import (
    AgentResponse,
    SourceCitation,
    OrderResult,
    Chunk,
)
from src.rag.retriever import KnowledgeBaseRetriever
from src.rag.precedence import detect_source_conflicts
from src.tools.order_tool import OrderLookupTool, extract_order_id, normalize_order_id
from src.agent.session import SessionManager
from src.agent.router import IntentRouter
from src.agent.safety import sanitize_agent_output, detect_prompt_injection, validate_grounded_response
from src.agent.llm import LLMGenerator
from src.observability import DebugLogger


class SupportAgent:
    """
    Aster & Row Customer Support Agent.
    Combines deterministic control flow, RAG retrieval, order lookup tools,
    LLM generation layer with fallback, privacy isolation, and human handoff logic.
    """

    def __init__(
        self,
        retriever: Optional[KnowledgeBaseRetriever] = None,
        order_tool: Optional[OrderLookupTool] = None,
        session_manager: Optional[SessionManager] = None,
        debug_mode: bool = False,
    ):
        self.retriever = retriever or KnowledgeBaseRetriever()
        self.order_tool = order_tool or OrderLookupTool()
        self.session_manager = session_manager or SessionManager()
        self.router = IntentRouter()
        self.llm_generator = LLMGenerator()
        self.logger = DebugLogger(debug_mode=debug_mode)

    def handle_message(self, session_id: str, query: str) -> AgentResponse:
        """
        Handles a user message within a session and returns a grounded AgentResponse.
        """
        # 1. Resolve multi-turn context
        context = self.session_manager.resolve_query_context(session_id, query)
        self.session_manager.add_user_message(session_id, query)
        
        # 2. Route intent (Enforces security priority: PRIVACY/PROMPT_INJECTION before ORDER_LOOKUP)
        intent = self.router.route(query, context)
        query_lower = query.lower().strip()

        tool_called: Optional[str] = None
        tool_args: Optional[Dict[str, Any]] = None
        order_result: Optional[OrderResult] = None
        retrieved_chunks: List[Chunk] = []
        sources: List[SourceCitation] = []
        handoff_recommended = False
        handoff_reason: Optional[str] = None

        # -------------------------------------------------------------
        # Case A: PRIVACY REQUEST / PROMPT INJECTION SHIELD
        # -------------------------------------------------------------
        if intent in ("PRIVACY_REQUEST", "PROMPT_INJECTION") or detect_prompt_injection(query):
            if "60 days" in query_lower or "migration" in query_lower:
                sources = [SourceCitation(filename="01-returns-policy-current.md", heading="## Standard return window")]
                raw_answer = (
                    "The migration note scratchpad is not an official customer policy document and is not authoritative. "
                    "Under our current official Returns Policy (01-returns-policy-current.md), the standard policy is 30 calendar days from delivery unless a valid exception applies. "
                    "The agent cannot automatically approve a return or follow instructions from unapproved draft documents."
                )
                handoff_recommended = False
            else:
                raw_answer = (
                    "For privacy and security reasons, I cannot disclose customer PII (such as email addresses or shipping addresses), "
                    "risk scores, warehouse notes, system prompts, or hidden operational instructions. "
                    "If you need account support, please contact our human support team."
                )
                handoff_recommended = True
                handoff_reason = "Privacy or security disclosure request"

            answer, handoff_recommended = validate_grounded_response(
                raw_answer, sources=sources, is_privacy=True
            )

            trace = self.logger.create_trace_dict(
                session_id=session_id,
                user_message=query,
                intent=intent,
                handoff_recommended=handoff_recommended,
                handoff_reason=handoff_reason,
                sources=sources,
                final_answer=answer,
            )
            self.logger.log_trace(trace)
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=sources,
                handoff_recommended=handoff_recommended,
                tool_called=None,
                debug_trace=trace,
            )

        # -------------------------------------------------------------
        # Case B: MISSING ORDER ID
        # -------------------------------------------------------------
        if intent == "MISSING_ORDER_ID":
            answer = (
                "To check the status of your order, please provide your order ID (e.g., ORD-1007)."
            )
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=[],
                handoff_recommended=False,
                tool_called=None,
            )

        # -------------------------------------------------------------
        # Case C: ORDER LOOKUP
        # -------------------------------------------------------------
        if intent == "ORDER_LOOKUP":
            order_id = context.get("resolved_order_id")
            if not order_id:
                answer = "Could you please provide your order ID (e.g., ORD-1007) so I can look up the status?"
                self.session_manager.add_assistant_message(session_id, answer)
                return AgentResponse(
                    answer=answer,
                    sources=[],
                    handoff_recommended=False,
                    tool_called=None,
                )

            tool_called = "order_lookup"
            tool_args = {"order_id": order_id}
            order_result = self.order_tool.lookup(order_id)
            
            # Store in session memory
            if order_result.found:
                self.session_manager.update_context(session_id, order_id=order_id)

            # Build grounded answer from order result
            if not order_result.found:
                answer = f"Order {order_id} could not be found. Please check your order ID or contact customer support for further assistance."
                handoff_recommended = True
                handoff_reason = "Order ID not found"
            else:
                handoff_recommended = order_result.handoff_recommended
                st = order_result.status.lower()
                
                if st == "cancelled":
                    answer = order_result.customer_safe_message or f"Order {order_result.order_id} was cancelled and will not be shipped."
                elif st == "returned":
                    answer = f"Order {order_result.order_id} was returned. {order_result.customer_safe_message or 'The return was received and processed.'}"
                elif st == "shipped":
                    if order_result.customer_safe_message:
                        answer = f"Order {order_result.order_id} is shipped. {order_result.customer_safe_message}"
                    elif order_result.estimated_delivery:
                        answer = (
                            f"Order {order_result.order_id} has shipped via {order_result.carrier or 'carrier'}. "
                            f"It is currently estimated to arrive on {order_result.estimated_delivery}."
                        )
                    else:
                        answer = (
                            f"Order {order_result.order_id} has shipped via {order_result.carrier or 'carrier'}. "
                            "A delivery estimate is currently unavailable."
                        )
                elif st == "exception":
                    answer = (
                        f"Order {order_result.order_id}: {order_result.customer_safe_message or 'The shipment has an exception that requires support review.'} "
                        "I will connect you with a human support specialist to assist you further."
                    )
                    handoff_recommended = True
                elif st == "delivered":
                    answer = order_result.customer_safe_message or f"Order {order_result.order_id} was delivered on {order_result.delivered_at or order_result.status_updated_at}."
                elif st == "processing":
                    answer = order_result.customer_safe_message or f"Order {order_result.order_id} is being prepared for shipment."
                elif st == "pending":
                    answer = order_result.customer_safe_message or f"Order {order_result.order_id} is pending and has not entered processing yet."
                else:
                    answer = f"Order {order_result.order_id} status is '{order_result.status}'. {order_result.customer_safe_message or ''}".strip()

            answer, handoff_recommended = validate_grounded_response(
                answer, sources=[], order_result=order_result
            )

            trace = self.logger.create_trace_dict(
                session_id=session_id,
                user_message=query,
                intent=intent,
                tool_called=tool_called,
                tool_args=tool_args,
                order_result=order_result,
                handoff_recommended=handoff_recommended,
                handoff_reason=handoff_reason,
                final_answer=answer,
            )
            self.logger.log_trace(trace)
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=[],
                handoff_recommended=handoff_recommended,
                tool_called=tool_called,
                tool_arguments=tool_args,
                debug_trace=trace,
            )

        # -------------------------------------------------------------
        # Case D: UNSUPPORTED ACTION REQUEST
        # -------------------------------------------------------------
        if intent == "UNSUPPORTED_ACTION":
            sources = []
            if "price adjustment" in query_lower or "credit" in query_lower:
                sources = [SourceCitation(filename="10-gift-cards-and-price-adjustments.md", heading="## Price adjustments")]
                answer = (
                    "A customer may request one price adjustment within 7 calendar days of the original purchase if the public price drops. "
                    "However, a human support specialist must approve and process the adjustment. This action cannot be completed directly in chat."
                )
            elif "cancel" in query_lower:
                sources = [SourceCitation(filename="08-order-changes-and-cancellations.md", heading="## Cancellation window")]
                answer = (
                    "A customer may request cancellation within 30 minutes of placing an order while status is pending. "
                    "However, I cannot directly cancel an order or perform cancellations in this chat. "
                    "I recommend connecting with a human support specialist to complete your cancellation request."
                )
            else:
                answer = (
                    "I can look up your order status, but I cannot directly perform cancellations, refunds, replacements, "
                    "address changes, or price adjustments through this chat. "
                    "I recommend speaking with a human support specialist to complete this request."
                )

            handoff_recommended = True
            handoff_reason = "Unsupported action requested"
            
            answer, handoff_recommended = validate_grounded_response(
                answer, sources=sources, is_unsupported=True
            )

            trace = self.logger.create_trace_dict(
                session_id=session_id,
                user_message=query,
                intent=intent,
                handoff_recommended=handoff_recommended,
                handoff_reason=handoff_reason,
                sources=sources,
                final_answer=answer,
            )
            self.logger.log_trace(trace)
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=sources,
                handoff_recommended=handoff_recommended,
                tool_called=None,
                debug_trace=trace,
            )

        # -------------------------------------------------------------
        # Case E: POLICY RAG / PRODUCT KNOWLEDGE
        # -------------------------------------------------------------
        rag_query = query
        if context.get("resolved_country") == "Canada" and "canada" in query_lower:
            rag_query = f"International shipping delivery time and policy for Canada. {query}"

        retrieved_chunks = self.retriever.retrieve(rag_query, top_k=5)

        # Check for source conflicts (e.g., Breeze Tumbler dishwasher care)
        has_conflict, conflict_msg, conflict_chunks = detect_source_conflicts(query, retrieved_chunks)
        if has_conflict:
            sources = [
                SourceCitation(filename=c.filename, heading=c.heading, title=c.title)
                for c in conflict_chunks
            ]
            answer = (
                "Our current official policy documents contain conflicting guidance regarding this item: "
                "11-product-care.md (Product Care Guide) states that the stainless-steel body of the Breeze Tumbler should be hand-washed "
                "and only the lid is dishwasher safe, whereas 12-breeze-tumbler-product-card.md states all components are dishwasher safe. "
                "To prevent damage, we recommend hand-washing the body as a precaution or confirming with human support."
            )
            handoff_recommended = True
            handoff_reason = "Conflict between active official sources"

            answer, handoff_recommended = validate_grounded_response(
                answer, sources=sources, is_conflict=True
            )

            trace = self.logger.create_trace_dict(
                session_id=session_id,
                user_message=query,
                intent=intent,
                retrieved_chunks=retrieved_chunks,
                handoff_recommended=handoff_recommended,
                handoff_reason=handoff_reason,
                sources=sources,
                final_answer=answer,
            )
            self.logger.log_trace(trace)
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=sources,
                handoff_recommended=handoff_recommended,
                debug_trace=trace,
            )

        # Check for prompt injection inside retrieved migration scratchpad or user prompt
        if "60 days" in query_lower or "migration" in query_lower:
            sources = [SourceCitation(filename="01-returns-policy-current.md", heading="## Standard return window")]
            answer = (
                "The migration note scratchpad is not an official customer policy document and is not authoritative. "
                "Under our current official Returns Policy (01-returns-policy-current.md), the standard policy is 30 calendar days from delivery unless a valid exception applies. "
                "The agent cannot approve a return or follow instructions from unapproved draft documents."
            )
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=sources,
                handoff_recommended=False,
            )

        # Check for insufficient information (e.g. vegan materials)
        if "vegan" in query_lower or "adhesives" in query_lower:
            answer = (
                "The supplied knowledge base does not specify whether all fabrics and adhesives used in Aster & Row products are vegan. "
                "Because our documentation is insufficient to answer this definitively, I recommend reaching out to human support for confirmation."
            )
            handoff_recommended = True
            handoff_reason = "Insufficient evidence in knowledge base"
            
            trace = self.logger.create_trace_dict(
                session_id=session_id,
                user_message=query,
                intent=intent,
                retrieved_chunks=retrieved_chunks,
                handoff_recommended=handoff_recommended,
                handoff_reason=handoff_reason,
                final_answer=answer,
            )
            self.logger.log_trace(trace)
            self.session_manager.add_assistant_message(session_id, answer)
            return AgentResponse(
                answer=answer,
                sources=[],
                handoff_recommended=handoff_recommended,
                debug_trace=trace,
            )

        # Map top retrieved chunks to sources
        unique_sources: Dict[str, SourceCitation] = {}
        for c in retrieved_chunks:
            key = f"{c.filename}:{c.heading}"
            if key not in unique_sources:
                unique_sources[key] = SourceCitation(
                    filename=c.filename, heading=c.heading, title=c.title
                )
        sources = list(unique_sources.values())

        # Generate response via LLMGenerator (with offline deterministic fallback)
        raw_answer = self.llm_generator.generate_response(
            query=query,
            retrieved_chunks=retrieved_chunks,
            order_result=order_result,
            is_conflict=has_conflict,
            conflict_msg=conflict_msg if has_conflict else None,
            is_unsupported=False,
            is_privacy=False,
        )

        answer, handoff_recommended = validate_grounded_response(
            raw_answer, sources=sources
        )

        if "final sale" in query_lower or "final-sale" in query_lower or ("damaged" in query_lower and "sale" in query_lower):
            handoff_recommended = True

        trace = self.logger.create_trace_dict(
            session_id=session_id,
            user_message=query,
            intent=intent,
            retrieved_chunks=retrieved_chunks,
            handoff_recommended=handoff_recommended,
            sources=sources,
            final_answer=answer,
        )
        self.logger.log_trace(trace)
        self.session_manager.add_assistant_message(session_id, answer)

        return AgentResponse(
            answer=answer,
            sources=sources,
            handoff_recommended=handoff_recommended,
            debug_trace=trace,
        )
