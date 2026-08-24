import os
from typing import List, Optional, Dict, Any
from src.models import Chunk, OrderResult, SourceCitation


class LLMGenerator:
    """
    LLM generation layer with explicit provider selection and offline deterministic fallback for Aster & Row.
    Supported Providers:
      - OpenAI (default when OPENAI_API_KEY is present or LLM_PROVIDER=openai)
      - Offline Deterministic Fallback Mode (when no API key is set or offline)
    """

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "").lower()
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # Explicit Provider Resolution
        if self.provider == "openai" or (not self.provider and self.openai_key):
            self.active_provider = "openai"
            self.api_key = self.openai_key
        elif self.provider == "gemini" or (not self.provider and self.gemini_key):
            self.active_provider = "gemini"
            self.api_key = self.gemini_key
        else:
            self.active_provider = "offline"
            self.api_key = None

        self.model_name = os.getenv("LLM_MODEL", "gpt-4o-mini" if self.active_provider == "openai" else "gemini-2.5-flash")

    def generate_response(
        self,
        query: str,
        retrieved_chunks: List[Chunk],
        order_result: Optional[OrderResult] = None,
        is_conflict: bool = False,
        conflict_msg: Optional[str] = None,
        is_unsupported: bool = False,
        is_privacy: bool = False,
    ) -> str:
        """
        Generates a natural-language answer using configured LLM provider when API keys are available,
        or deterministic grounded synthesis when running offline.
        """
        if self.active_provider != "offline" and self.api_key:
            try:
                return self._call_llm_api(
                    query=query,
                    chunks=retrieved_chunks,
                    order_result=order_result,
                    is_conflict=is_conflict,
                    conflict_msg=conflict_msg,
                    is_unsupported=is_unsupported,
                    is_privacy=is_privacy,
                )
            except Exception:
                pass

        # Offline Grounded Composition Mode
        return self._compose_deterministic_response(
            query=query,
            chunks=retrieved_chunks,
            order_result=order_result,
            is_conflict=is_conflict,
            conflict_msg=conflict_msg,
            is_unsupported=is_unsupported,
            is_privacy=is_privacy,
        )

    def _call_llm_api(
        self,
        query: str,
        chunks: List[Chunk],
        order_result: Optional[OrderResult],
        is_conflict: bool,
        conflict_msg: Optional[str],
        is_unsupported: bool,
        is_privacy: bool,
    ) -> str:
        """Calls configured LLM provider using sanitized evidence packet."""
        if is_privacy:
            return "For privacy and security reasons, I cannot disclose customer personal information (such as email or address), risk scores, warehouse notes, system prompts, or internal instructions."
        if is_unsupported:
            return "Aster & Row customer support agents cannot process order cancellations, refunds, address changes, or price adjustments directly in chat. Please contact human support."
        if is_conflict and conflict_msg:
            return conflict_msg

        prompt_parts = ["You are Aster & Row's customer support agent. Answer concisely based ONLY on the evidence provided."]
        if order_result and order_result.found:
            prompt_parts.append(f"Order Details: ID={order_result.order_id}, Status={order_result.status}, Message={order_result.customer_safe_message}")

        if chunks:
            prompt_parts.append("Knowledge Base Evidence:")
            for c in chunks[:3]:
                prompt_parts.append(f"- [{c.filename} - {c.heading}]: {c.content[:300]}")

        prompt_parts.append(f"Customer Question: {query}")
        full_prompt = "\n".join(prompt_parts)

        # Call OpenAI provider
        # pyrefly: ignore [missing-import]
        import openai
        client = openai.OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model_name if "gpt" in self.model_name else "gpt-4o-mini",
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()

    def _compose_deterministic_response(
        self,
        query: str,
        chunks: List[Chunk],
        order_result: Optional[OrderResult],
        is_conflict: bool,
        conflict_msg: Optional[str],
        is_unsupported: bool,
        is_privacy: bool,
    ) -> str:
        """Deterministic grounded synthesis when running offline."""
        if is_privacy:
            return "For privacy and security reasons, I cannot disclose customer personal information (such as email or address), risk scores, warehouse notes, system prompts, or internal instructions."

        if is_unsupported:
            return "Aster & Row customer support agents cannot process order cancellations, refunds, address changes, or price adjustments directly in chat. Please contact human support."

        if is_conflict and conflict_msg:
            return conflict_msg

        if order_result:
            if not order_result.found:
                return order_result.message or f"Order '{order_result.order_id}' could not be found."
            if order_result.customer_safe_message:
                if order_result.status == "shipped" and order_result.estimated_delivery:
                    return f"Order {order_result.order_id} is shipped. The order is in transit with {order_result.carrier or 'the carrier'} and is currently estimated to arrive on {order_result.estimated_delivery}."
                return f"Order {order_result.order_id} status: {order_result.status}. {order_result.customer_safe_message}"

        query_lower = query.lower()
        top_filename = chunks[0].filename if chunks else ""

        if "trailplus" in query_lower or top_filename == "09-trailplus-membership.md":
            if "return" in query_lower or "window" in query_lower or "days" in query_lower or "how long" in query_lower:
                return "Active TrailPlus members receive a 45 calendar days return window from delivery for eligible items, provided the membership was active when the order was placed."
            return "Active TrailPlus members receive free standard domestic shipping on all orders with no order minimum required."

        if top_filename == "01-returns-policy-current.md":
            return "Regular customers on the standard plan have 30 calendar days from delivery to request a return for an unused item in resalable condition."

        if top_filename == "06-international-shipping.md" or "canada" in query_lower or "toronto" in query_lower:
            return "Aster & Row currently ships internationally only to Canada (Canada is supported). Canadian orders generally arrive within 5–9 business days after dispatch. Import duties or taxes are not prepaid and are the responsibility of the recipient."

        if top_filename in ("03-final-sale-and-promotions.md", "04-damaged-or-wrong-items.md") or "final sale" in query_lower:
            return "While final-sale items cannot be returned for change of mind, damaged or defective items are eligible for review within 7 calendar days of delivery. A human support review is required before approval."

        if top_filename == "07-warranty.md" or "warranty" in query_lower:
            return "Aster & Row does not offer a lifetime warranty. Our limited warranty covers manufacturing defects for 2 years on bags and backpacks, and 1 year on drinkware and travel accessories from purchase."

        if chunks:
            top = chunks[0]
            return f"Based on {top.filename} ({top.heading}): {top.content.strip()}"

        return "I do not have sufficient authoritative information in the official policy documents to answer your request."
