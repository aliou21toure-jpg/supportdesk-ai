"""Remove personal data before ticket text is sent to a third-party AI model."""

import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("[EMAIL]", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    # 13–19 digit card numbers, optionally separated by spaces or dashes
    ("[CARD]", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    ("[PHONE]", re.compile(r"(?<!\w)(?:\+?\d{1,3}[ .-]?)?(?:\(\d{3}\)|\d{3})[ .-]?\d{3}[ .-]?\d{4}\b")),
    ("[SECRET]", re.compile(r"\b(?:sk|pk|api|key|token)[-_][A-Za-z0-9_-]{12,}\b", re.IGNORECASE)),
]


def redact(text: str) -> str:
    for placeholder, pattern in _PATTERNS:
        text = pattern.sub(placeholder, text)
    return text
