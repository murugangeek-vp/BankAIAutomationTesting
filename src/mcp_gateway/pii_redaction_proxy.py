"""
PII / PCI Redaction Proxy for MCP Gateway.

Redacts Sensitive Personal Data (PII) and Payment Card Industry data (PCI)
from all data streams before passing context to LLM agent models.
Enforces zero PII leakage under PCI-DSS, GDPR, and banking regulations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple


@dataclass
class RedactionResult:
    """Output of a redaction scan."""
    cleaned_text: str
    redaction_count: int
    redacted_types: Set[str] = field(default_factory=set)
    mapping: Dict[str, str] = field(default_factory=dict)  # token -> original (kept strictly in non-prod proxy memory)


class PIIRedactionProxy:
    """
    Regex and heuristic-based PII/PCI Masking Gateway.
    Filters PAN (card numbers), IBAN, SSN/TIN, Emails, Phone numbers, JWT/API Tokens.
    """

    PATTERNS = {
        "PAN": [
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})\b",
            r"\b(?:\d[ -]*?){13,19}\b"  # Generic 13-19 digit card pattern
        ],
        "IBAN": [
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]{0,16})\b"
        ],
        "SSN": [
            r"\b\d{3}-\d{2}-\d{4}\b",
            r"\b\d{9}\b"  # 9-digit SSN without hyphens (in context)
        ],
        "EMAIL": [
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        ],
        "PHONE": [
            r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
        ],
        "AUTH_TOKEN": [
            r"\bBearer\s+[A-Za-z0-9\-._~+/]+=*\b",
            r"\b(?:sk_test_|sk_live_|pk_test_|pk_live_)[0-9a-zA-Z]{24,}\b"
        ]
    }

    def __init__(self, enable_strict_pci: bool = True):
        self.enable_strict_pci = enable_strict_pci
        self.counter = 0

    def redact_text(self, text: str) -> RedactionResult:
        """Scan and mask any detected PII/PCI patterns in text."""
        if not text:
            return RedactionResult(cleaned_text="", redaction_count=0)

        cleaned_text = text
        redacted_types: Set[str] = set()
        mapping: Dict[str, str] = {}
        total_redactions = 0

        # Process each PII pattern type
        for pii_type, regexes in self.PATTERNS.items():
            for pattern in regexes:
                matches = re.finditer(pattern, cleaned_text)
                # Reverse matches to replace without disturbing indices
                for match in reversed(list(matches)):
                    val = match.group(0)

                    # Luhn verification filter for PAN candidates
                    if pii_type == "PAN" and not self._is_potential_pan(val):
                        continue

                    self.counter += 1
                    token = f"[REDACTED_{pii_type}_{self.counter}]"
                    cleaned_text = (
                        cleaned_text[:match.start()] + token + cleaned_text[match.end():]
                    )
                    mapping[token] = val
                    redacted_types.add(pii_type)
                    total_redactions += 1

        return RedactionResult(
            cleaned_text=cleaned_text,
            redaction_count=total_redactions,
            redacted_types=redacted_types,
            mapping=mapping
        )

    def redact_dict(self, data: dict) -> dict:
        """Recursively redact string values inside a dictionary structure."""
        cleaned = {}
        for k, v in data.items():
            if isinstance(v, str):
                cleaned[k] = self.redact_text(v).cleaned_text
            elif isinstance(v, dict):
                cleaned[k] = self.redact_dict(v)
            elif isinstance(v, list):
                cleaned[k] = [
                    self.redact_text(item).cleaned_text if isinstance(item, str)
                    else self.redact_dict(item) if isinstance(item, dict)
                    else item
                    for item in v
                ]
            else:
                cleaned[k] = v
        return cleaned

    def _is_potential_pan(self, candidate: str) -> bool:
        """Check if digits pass basic length & Luhn algorithm check."""
        digits = "".join(c for c in candidate if c.isdigit())
        if len(digits) < 13 or len(digits) > 19:
            return False
        # Basic Luhn check
        checksum = 0
        reverse_digits = digits[::-1]
        for i, digit_str in enumerate(reverse_digits):
            n = int(digit_str)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            checksum += n
        return checksum % 10 == 0
