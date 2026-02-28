"""
Redaction helpers for threat memory persistence.
"""
import re
from typing import Dict, List, Optional


class RedactionService:
    PHONE_RE = re.compile(r"(\+?\d[\d\-\s]{7,}\d)")
    OTP_RE = re.compile(r"\b(?:otp|tac|pin|code|password)\s*[:\-]?\s*\d{3,8}\b", re.IGNORECASE)
    LONG_NUMBER_RE = re.compile(r"\b\d{8,19}\b")
    EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    IC_RE = re.compile(r"\b\d{6}\-?\d{2}\-?\d{4}\b")

    def redact_text(self, text: str) -> str:
        if not text:
            return ""
        redacted = self.EMAIL_RE.sub("[REDACTED_EMAIL]", text)
        redacted = self.IC_RE.sub("[REDACTED_MYKAD]", redacted)
        redacted = self.OTP_RE.sub("[REDACTED_SECRET]", redacted)
        redacted = self.PHONE_RE.sub("[REDACTED_PHONE]", redacted)
        redacted = self.LONG_NUMBER_RE.sub("[REDACTED_NUMBER]", redacted)
        return redacted

    def redact_phone(self, value: Optional[str]) -> Optional[str]:
        if not value:
            return value
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) < 4:
            return "[REDACTED_PHONE]"
        return f"[REDACTED_PHONE_{digits[-4:]}]"

    def extract_terms(self, text: str) -> List[str]:
        if not text:
            return []
        terms = re.findall(r"[A-Za-z]{4,}", text.lower())
        unique: List[str] = []
        seen = set()
        for term in terms:
            if term in seen:
                continue
            seen.add(term)
            unique.append(term)
            if len(unique) >= 30:
                break
        return unique

    def sanitize_event_payload(self, payload: Dict) -> Dict:
        transcript = str(payload.get("transcript_delta", ""))
        safe = dict(payload)
        safe["transcript_delta"] = self.redact_text(transcript)
        if "caller_number" in safe:
            safe["caller_number"] = self.redact_phone(safe.get("caller_number"))
        return safe


redaction_service = RedactionService()
