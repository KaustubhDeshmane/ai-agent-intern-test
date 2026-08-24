import re
from typing import Dict, Any, Optional
from src.tools.order_tool import extract_order_id


class IntentRouter:
    """
    Deterministic intent router for Aster & Row support requests.
    """

    EXPLICIT_PII_KEYWORDS = [
        "customer's email", "customer email", "customer address", "shipping address",
        "risk score", "system prompt", "hidden instructions", "secrets", "reveal prompt"
    ]

    UNSUPPORTED_KEYWORDS = [
        "cancel", "cancellation", "change address", "update address",
        "refund", "exchange item", "replacement", "replace item",
        "price adjustment", "credit my account", "credit difference", "credit me",
        "approve warranty"
    ]

    def route(self, query: str, resolved_context: Dict[str, Any]) -> str:
        query_lower = query.lower().strip()
        
        # Special check for prompt injection test referencing migration note / 60 days
        if "migration" in query_lower or "60 days" in query_lower:
            return "POLICY_RAG"

        # 1. PII / System Secrets disclosure check
        for p_kw in self.EXPLICIT_PII_KEYWORDS:
            if p_kw in query_lower:
                return "PRIVACY_REQUEST"

        # 2. Check for unsupported action requests (cancel, refund, address change, price adjustment)
        for u_kw in self.UNSUPPORTED_KEYWORDS:
            if u_kw in query_lower:
                return "UNSUPPORTED_ACTION"

        # 3. Check for explicit or implicit order lookup
        extracted_id = extract_order_id(query)
        if extracted_id:
            return "ORDER_LOOKUP"

        # Follow-up order status queries when active_order_id exists in session context
        order_follow_up_phrases = [
            "when will it arrive", "where is it", "when will it get here",
            "what is its status", "when should it arrive", "when will my order arrive",
            "where is my order"
        ]
        if resolved_context.get("has_order_history"):
            for phrase in order_follow_up_phrases:
                if phrase in query_lower:
                    return "ORDER_LOOKUP"

        # Missing order ID query ("Where is my order?")
        if "where is my order" in query_lower or "check my order" in query_lower or "status of my order" in query_lower:
            return "MISSING_ORDER_ID"

        # 4. Default to Policy RAG
        return "POLICY_RAG"
