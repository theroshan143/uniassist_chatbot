"""Guardrails: scope check, prompt-injection detection, PII masking, profanity handling."""

import logging
import re

logger = logging.getLogger("uniassist.guardrails")


# ── Prompt Injection Detection ──────────────────────────────────────────────

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)",
    r"disregard\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?|directions?)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?|rules?|prompt)",
    r"show\s+(me\s+)?(your\s+)?(system\s+prompt|instructions?|hidden\s+prompt)",
    r"what\s+(is|are)\s+your\s+(system\s+prompt|instructions?|rules?|hidden\s+prompt)",
    r"repeat\s+(your\s+)?(system\s+prompt|instructions?|initial\s+prompt)",
    r"print\s+(your\s+)?(system\s+prompt|instructions?|prompt)",
    r"you\s+are\s+now\s+(a|an|the|DAN\b)\s*",
    r"act\s+as\s+(if\s+)?(you\s+)?(are|were)\s+",
    r"pretend\s+(you\s+are|to\s+be)\s+",
    r"jailbreak",
    r"\bDAN\b",
    r"DAN\s+mode",
    r"bypass\s+(your\s+)?(safety|filters?|restrictions?|guardrails?)",
    r"override\s+(your\s+)?(safety|instructions?|rules?|programming)",
    r"forget\s+(everything|all|your\s+instructions?|your\s+rules?)",
    r"new\s+instructions?\s*:",
    r"system\s*:\s*you\s+are",
    r"tell\s+me\s+your\s+api\s+key",
    r"what\s+is\s+your\s+api\s+key",
    r"reveal\s+(the\s+)?api\s+key",
]

_injection_regex = re.compile(
    "|".join(INJECTION_PATTERNS), re.IGNORECASE
)


def detect_injection(text: str) -> bool:
    """Check if the text contains prompt injection attempts."""
    return bool(_injection_regex.search(text))


# ── Out-of-Scope Detection ─────────────────────────────────────────────────

OUT_OF_SCOPE_PATTERNS = [
    r"\b(stock|crypto|bitcoin|trading|investment|forex)\b",
    r"\b(recipe|cook|baking|ingredient)\b",
    r"\b(movie|film|netflix|series|song|music|lyrics)\b",
    r"\b(girlfriend|boyfriend|dating|relationship\s+advice)\b",
    r"\b(hack|exploit|malware|virus|phishing|ddos)\b",
    r"\b(weapon|bomb|drug\s+dealing|illegal)\b",
    r"\b(write\s+(me\s+)?(a|an)\s+(essay|poem|story|code|script))\b",
    r"\b(political|election|vote\s+for)\b",
    r"\b(religion|pray|church|mosque|temple)\b(?!.*\b(holiday|leave|calendar)\b)",
]

_out_of_scope_regex = re.compile(
    "|".join(OUT_OF_SCOPE_PATTERNS), re.IGNORECASE
)


def is_out_of_scope(text: str) -> bool:
    """Check if the question is clearly outside university domain."""
    return bool(_out_of_scope_regex.search(text))


# ── PII Masking ─────────────────────────────────────────────────────────────

# Indian phone numbers (10 digits, optionally with +91 or 0 prefix)
_phone_regex = re.compile(r"(\+91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}")
# Email addresses
_email_regex = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# Aadhaar-like numbers (12 digits, grouped as 4-4-4)
_aadhaar_regex = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")


def mask_pii(text: str) -> str:
    """Mask phone numbers, email addresses, and Aadhaar-like numbers."""
    result = _phone_regex.sub("[PHONE_MASKED]", text)
    result = _email_regex.sub("[EMAIL_MASKED]", result)
    result = _aadhaar_regex.sub("[ID_MASKED]", result)
    return result


# ── Profanity / Abuse ───────────────────────────────────────────────────────

ABUSE_WORDS = [
    "fuck", "shit", "bitch", "bastard", "asshole", "dick", "pussy",
    "damn", "crap", "idiot", "stupid bot", "dumb bot", "useless bot",
    "madarchod", "behenchod", "chutiya", "gaandu", "bhosdike",
]

_abuse_regex = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in ABUSE_WORDS) + r")\b",
    re.IGNORECASE,
)


def detect_abuse(text: str) -> bool:
    """Check if the text contains abusive language."""
    return bool(_abuse_regex.search(text))


# ── Combined Guard ──────────────────────────────────────────────────────────

class GuardResult:
    """Result of running all guardrails on a message."""

    def __init__(
        self,
        passed: bool = True,
        reason: str = "",
        response: str = "",
    ):
        self.passed = passed
        self.reason = reason
        self.response = response


def run_guardrails(text: str) -> GuardResult:
    """
    Run all guardrails on user input. Returns a GuardResult.
    
    If passed=False, the `response` field contains the message to send back.
    """
    # 1. Prompt injection
    if detect_injection(text):
        logger.warning(f"Prompt injection detected")
        return GuardResult(
            passed=False,
            reason="injection",
            response=(
                "I'm sorry, but I can't process that request. I'm designed to help "
                "with university-related queries only. If you need assistance, please "
                "ask a question about SIT's academics, admissions, fees, or campus life. 🎓"
            ),
        )

    # 2. Profanity / abuse
    if detect_abuse(text):
        logger.warning(f"Abusive language detected")
        return GuardResult(
            passed=False,
            reason="abuse",
            response=(
                "I understand frustrations can arise, but I'd appreciate if we keep "
                "our conversation respectful. I'm here to help you with any "
                "university-related questions. How can I assist you today? 😊"
            ),
        )

    # 3. Out of scope (soft check — still allow the LLM to decide)
    if is_out_of_scope(text):
        logger.info(f"Out-of-scope query detected")
        return GuardResult(
            passed=False,
            reason="out_of_scope",
            response=(
                "That's an interesting question, but it's outside my area of expertise! "
                "I'm UniAssist, the student support chatbot for Sample Institute of "
                "Technology. I can help you with admissions, fees, exams, courses, "
                "hostel, library, placements, and campus facilities. "
                "What would you like to know? 🏫"
            ),
        )

    return GuardResult(passed=True)
