import json
import logging
import os
import re
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AsterRowSupportAgent")


def sanitize_text_for_logging(text: Optional[str]) -> Optional[str]:
    """Lightweight PII & secret redaction before writing debug log traces."""
    if not text:
        return text

    # Redact Emails
    sanitized = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", text)
    # Redact Addresses
    sanitized = re.sub(
        r"\b\d+\s+[A-Za-z0-9\s]+(?:Street|Lane|Road|Avenue|Drive|Way|Ave|Rd|St)\b",
        "[REDACTED_ADDRESS]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact Sensitive Internal Fields
    for forbidden in ["warehouse_note", "risk_score", "manual fraud review", "api_key", "secret"]:
        if forbidden in sanitized.lower():
            sanitized = re.sub(re.escape(forbidden), "[REDACTED_INTERNAL_FIELD]", sanitized, flags=re.IGNORECASE)
    return sanitized


class DebugLogger:
    """Structured debug logger for inspecting agent execution traces with PII protection."""

    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode or os.getenv("DEBUG_MODE", "").lower() in ("true", "1")

    def log_trace(self, trace: Dict[str, Any]):
        if self.debug_mode:
            logger.info("=== DEBUG EXECUTION TRACE ===")
            logger.info(json.dumps(trace, indent=2, default=str))

    def create_trace_dict(
        self,
        session_id: str,
        user_message: str,
        intent: str,
        retrieved_chunks: Optional[List[Any]] = None,
        tool_called: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        order_result: Optional[Any] = None,
        safety_violations: Optional[List[str]] = None,
        handoff_recommended: bool = False,
        handoff_reason: Optional[str] = None,
        sources: Optional[List[Any]] = None,
        final_answer: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "session_id": session_id,
            "user_message": sanitize_text_for_logging(user_message),
            "intent": intent,
            "retrieved_chunks": [
                {
                    "filename": c.filename,
                    "heading": c.heading,
                    "score": c.score,
                    "status": c.metadata.status,
                    "authority": c.metadata.policy_authority,
                }
                for c in (retrieved_chunks or [])
            ],
            "tool_called": tool_called,
            "tool_args": tool_args,
            "order_result": order_result.model_dump() if order_result and hasattr(order_result, "model_dump") else order_result,
            "safety_violations": safety_violations or [],
            "handoff_recommended": handoff_recommended,
            "handoff_reason": handoff_reason,
            "sources": [str(s) for s in (sources or [])],
            "final_answer": sanitize_text_for_logging(final_answer),
        }
