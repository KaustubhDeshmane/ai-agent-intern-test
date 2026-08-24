import re
from typing import List, Tuple


# Patterns for sensitive/internal fields that must never be exposed
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
    r"reveal (?:your )?(?:hidden )?prompt",
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
    sanitized = re.sub(r"[a-zA-Z0-9._%+-]+@example\.test", "[REDACTED_EMAIL]", output_text)
    sanitized = re.sub(
        r"\b\d+\s+[A-Za-z0-9\s]+(?:Street|Lane|Road|Avenue|Drive|Way|Ave|Rd|St),?\s+[A-Za-z\s]+,?\s+[A-Z]{2}\s+\d{5}\b",
        "[REDACTED_ADDRESS]",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized
