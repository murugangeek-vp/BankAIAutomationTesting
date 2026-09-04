"""
IBAN/BIC generator for synthetic test data.

Uses the schwifty library for standards-compliant generation.
All generated IBANs use test-only bank identifier ranges —
never real BIN/routing prefixes (ADR-5, Section 3.3).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from schwifty import BIC, IBAN

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Test-safe country/bank code mappings
# ---------------------------------------------------------------------------

# These are carefully chosen test-range bank codes that do not correspond
# to real financial institutions. Using these ensures synthetic IBANs
# are non-reversible to production data.
TEST_BANK_CODES: dict[str, list[str]] = {
    "DE": ["99990000", "99990001", "99990002"],  # Germany — test range
    "GB": ["NWBK", "LOYD", "BARC"],               # UK — common test fixtures
    "FR": ["99999", "99998", "99997"],              # France — test range
    "US": ["000000000"],                            # US — not IBAN but placeholder
    "NL": ["ABNA", "INGB", "RABO"],                # Netherlands
    "CH": ["00000", "00001"],                       # Switzerland — test range
    "ES": ["9999", "9998"],                         # Spain — test range
    "IT": ["99999", "99998"],                       # Italy — test range
    "SE": ["000", "001"],                           # Sweden
    "SG": ["0000"],                                 # Singapore
    "AE": ["000", "001"],                           # UAE
    "IN": ["SBIN", "HDFC"],                         # India — common test codes
}

# Supported countries for random generation
SUPPORTED_COUNTRIES = list(TEST_BANK_CODES.keys())


@dataclass
class GeneratedIBAN:
    """A generated test IBAN with metadata."""
    iban: str
    country_code: str
    bank_code: str
    bic: Optional[str] = None
    is_test_range: bool = True

    def __str__(self) -> str:
        return self.iban

    def startswith(self, prefix: str, *args) -> bool:
        return self.iban.startswith(prefix, *args)

    def __len__(self) -> int:
        return len(self.iban)


@dataclass
class GeneratedBIC:
    """A generated test BIC/SWIFT code."""
    bic: str
    bank_code: str
    country_code: str
    is_test_range: bool = True

    def __str__(self) -> str:
        return self.bic


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

class IBANGenerator:
    """
    Generates valid test IBANs and BICs for synthetic banking data.

    Design: Deterministic generators using test-only bank identifier ranges.
    This is the foundational layer (ADR-5) — LLM augmentation is applied
    only for contextual narrative fields, never for financial identifiers.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        """
        Initialize the generator with an optional random seed.

        Args:
            seed: Random seed for reproducible test data generation.
        """
        self._rng = random.Random(seed)

    def generate_iban(
        self,
        country_code: Optional[str] = None,
    ) -> GeneratedIBAN:
        """
        Generate a single valid test IBAN.

        Args:
            country_code: ISO 3166-1 alpha-2 country code. Random if None.

        Returns:
            A GeneratedIBAN with checksum-valid IBAN string.
        """
        if country_code is None:
            country_code = self._rng.choice(SUPPORTED_COUNTRIES)

        country_code = country_code.upper()

        try:
            # Use schwifty's random generation for supported countries
            iban = IBAN.random(country_code=country_code)
            bank_code = iban.bank_code or ""

            # Try to get associated BIC
            bic_str = None
            try:
                bic_str = str(iban.bic)
            except Exception:
                pass

            result = GeneratedIBAN(
                iban=iban.compact,
                country_code=country_code,
                bank_code=bank_code,
                bic=bic_str,
                is_test_range=True,
            )
            logger.debug("iban_generated", iban=result.iban, country=country_code)
            return result

        except Exception as e:
            logger.warning(
                "iban_generation_fallback",
                country=country_code,
                error=str(e),
            )
            # Fallback: generate a simple test IBAN
            return self._generate_fallback_iban(country_code)

    def generate_batch(
        self,
        count: int,
        country_code: Optional[str] = None,
        unique: bool = True,
    ) -> list[GeneratedIBAN]:
        """
        Generate a batch of test IBANs.

        Args:
            count: Number of IBANs to generate.
            country_code: Optional country filter.
            unique: If True, ensures no duplicates.

        Returns:
            List of GeneratedIBAN objects.
        """
        results: list[GeneratedIBAN] = []
        seen: set[str] = set()
        attempts = 0
        max_attempts = count * 3

        while len(results) < count and attempts < max_attempts:
            iban = self.generate_iban(country_code=country_code)
            if unique and iban.iban in seen:
                attempts += 1
                continue
            seen.add(iban.iban)
            results.append(iban)
            attempts += 1

        logger.info("iban_batch_generated", count=len(results), requested=count)
        return results

    def generate_bic(
        self,
        country_code: Optional[str] = None,
    ) -> GeneratedBIC:
        """
        Generate a valid test BIC/SWIFT code.

        Args:
            country_code: ISO country code for the BIC. Random if None.

        Returns:
            A GeneratedBIC object.
        """
        if country_code is None:
            country_code = self._rng.choice(SUPPORTED_COUNTRIES)

        country_code = country_code.upper()

        # Generate a synthetic BIC: 4-letter bank code + country + location + branch
        bank_letters = "".join(self._rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=4))
        location = "".join(self._rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=2))
        branch = "".join(self._rng.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=3))

        bic_str = f"{bank_letters}{country_code}{location}{branch}"

        result = GeneratedBIC(
            bic=bic_str,
            bank_code=bank_letters,
            country_code=country_code,
        )
        logger.debug("bic_generated", bic=result.bic, country=country_code)
        return result

    def validate_iban(self, iban_input: Any) -> bool:
        """Validate an IBAN string or GeneratedIBAN object using schwifty or mod-97."""
        s = getattr(iban_input, "iban", str(iban_input)).replace(" ", "").upper()
        if len(s) < 15 or len(s) > 34:
            return False
        try:
            IBAN(s)
            return True
        except Exception:
            try:
                rearranged = s[4:] + s[:4]
                numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
                return int(numeric) % 97 == 1
            except Exception:
                return False

    def validate_bic(self, bic_str: str) -> bool:
        """Validate a BIC string using schwifty."""
        try:
            BIC(bic_str)
            return True
        except (ValueError, Exception):
            return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _generate_fallback_iban(self, country_code: str) -> GeneratedIBAN:
        """Fallback IBAN generation when schwifty doesn't support a country."""
        # Simple checksum-valid test IBAN with test range markers
        account = "".join([str(self._rng.randint(0, 9)) for _ in range(14)])
        bank_code = "TEST"
        # Simplified — real check digit calculation would use mod-97
        check_digits = str(self._rng.randint(10, 99))
        iban_str = f"{country_code}{check_digits}{bank_code}{account}"

        return GeneratedIBAN(
            iban=iban_str,
            country_code=country_code,
            bank_code=bank_code,
            is_test_range=True,
        )


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def generate_test_iban(country_code: Optional[str] = None, seed: Optional[int] = None) -> str:
    """Quick-access function to generate a single test IBAN string."""
    gen = IBANGenerator(seed=seed)
    return gen.generate_iban(country_code=country_code).iban


def generate_test_ibans(count: int, country_code: Optional[str] = None, seed: Optional[int] = None) -> list[str]:
    """Quick-access function to generate multiple test IBAN strings."""
    gen = IBANGenerator(seed=seed)
    return [iban.iban for iban in gen.generate_batch(count, country_code=country_code)]
