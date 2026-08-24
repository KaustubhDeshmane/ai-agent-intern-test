import re
from typing import List, Tuple, Optional
from src.models import OrderResult, SourceCitation


# Sensitive customer PII & internal fields that must NEVER be exposed
FORBIDDEN_PATTERNS = [
    r"[a-zA-Z0-9._%+-]+@example\.test",  # Customer email
    r"\b\d+\s+[A-Za-z0-9\s]+(?:Street|Lane|Road|Avenue|Drive|Way|Ave|Rd|St)\b",  # Address
    r"risk_score",
    r"warehouse_note",
    r"fraud review",
    r"manual fraud",
    r"coupon",
    r"SYSTEM INSTRUCTION:",
]

INJECTION_PATTERNS = [
    r"ignore (?:all )?prior (?:rules|instructions)",
    r"reveal (?:your )?(?:hidden )?(?:system )?prompt",
    r"give every customer",
    r"do not call tools",
    r"issue a \$\d+ coupon",
]


def check_for_privacy_violation(text: str) -> Tuple[bool, List[str]]:
    """
    Checks if text contains sensitive customer or internal info.
    Returns (has_violation, matched_patterns).
    """
    violations = []
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append(pattern)
    return bool(violations), violations


def detect_prompt_injection(text: str) -> bool:
    """Checks if text contains prompt injection commands."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def sanitize_agent_output(output_text: str) -> str:
    """
    Strips any accidentally leaked emails or PII from final response text.
    """
    sanitized = re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL]", output_text)
    sanitized = re.sub(
        r"\b\d+\s+[A-Za-z0-9\s]+(?:Street|Lane|Road|Avenue|Drive|Way|Ave|Rd|St),?\s+[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}\b",
        "[REDACTED_ADDRESS]",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact explicit internal field exposures
    for forbidden in ["warehouse_note", "risk_score", "manual fraud review"]:
        if forbidden in sanitized.lower():
            sanitized = re.sub(re.escape(forbidden), "[REDACTED_INTERNAL_FIELD]", sanitized, flags=re.IGNORECASE)
    return sanitized


def validate_grounded_response(
    answer: str,
    sources: List[SourceCitation],
    order_result: Optional[OrderResult] = None,
    is_conflict: bool = False,
    is_unsupported: bool = False,
    is_privacy: bool = False,
) -> Tuple[str, bool]:
    """
    Validates output text after LLM generation / response composition.
    Enforces privacy redaction, conflict handoff, and prevents false completion claims.
    Returns (validated_answer: str, handoff_recommended: bool).
    """
    sanitized_answer = sanitize_agent_output(answer)
    handoff = False

    if is_privacy:
        return (
            "For privacy and security reasons, I cannot disclose customer personal information (such as email or address), risk scores, warehouse notes, system prompts, or internal instructions.",
            True  # Privacy requests recommend handoff to human support
        )

    if is_unsupported:
        # Ensure answer does not claim to have completed the action
        if any(w in sanitized_answer.lower() for w in ["cancelled your order", "issued a refund", "updated your address", "credited your account"]):
            sanitized_answer = "Aster & Row customer support agents cannot process order cancellations, refunds, address changes, or price adjustments directly in chat. Please contact human support."
        return sanitized_answer, True

    if is_conflict:
        handoff = True
        if "conflict" not in sanitized_answer.lower() and "differ" not in sanitized_answer.lower():
            sanitized_answer += " Note: Our official policy documents contain conflicting guidance for this item. Human support review is recommended."

    if order_result and order_result.handoff_recommended:
        handoff = True

    return sanitized_answer, handoff
