"""PII redaction for logs, traces, and streamed event payloads."""

import re
from typing import Any

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def redact_pii(text: str) -> str:
    text = _EMAIL.sub("[email]", text)
    text = _PHONE.sub("[phone]", text)
    text = _SSN.sub("[ssn]", text)
    return text


def redact_payload(payload: Any) -> Any:
    """Recursively redact string values in event/log payloads."""
    if isinstance(payload, str):
        return redact_pii(payload)
    if isinstance(payload, dict):
        return {key: redact_payload(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [redact_payload(item) for item in payload]
    return payload
