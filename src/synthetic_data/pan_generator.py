"""
Synthetic PAN (Primary Account Number) generator.

Generates Luhn-valid card numbers using non-existent BIN (Bank Identification
Number) ranges. These PANs pass checksum validation but will never match
a real cardholder — critical for PCI-DSS scope reduction (Section 3.3).

Test BIN ranges used:
  - 999900-999999: Reserved test range (not allocated by card networks)
  - 400000-400099: Visa test range
  - 510000-510099: Mastercard test range
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from src.core.logging_config import get_logger

logger = get_logger(__name__)


class CardNetwork(str, Enum):
    """Card networks with test BIN ranges."""
    VISA = "visa"
    MASTERCARD = "mastercard"
    AMEX = "amex"
    DISCOVER = "discover"
    TEST = "test"


# Test-only BIN prefixes — these do NOT correspond to real issuers
TEST_BINS: dict[CardNetwork, list[str]] = {
    CardNetwork.VISA: ["400000", "400001", "400002", "400099"],
    CardNetwork.MASTERCARD: ["510000", "510001", "510099", "520000"],
    CardNetwork.AMEX: ["340000", "370000"],
    CardNetwork.DISCOVER: ["601100", "601199"],
    CardNetwork.TEST: ["999900", "999901", "999999"],
}

# PAN lengths by network
PAN_LENGTHS: dict[CardNetwork, int] = {
    CardNetwork.VISA: 16,
    CardNetwork.MASTERCARD: 16,
    CardNetwork.AMEX: 15,
    CardNetwork.DISCOVER: 16,
    CardNetwork.TEST: 16,
}


@dataclass
class GeneratedPAN:
    """A generated test PAN with metadata."""
    pan: str
    network: CardNetwork
    bin_prefix: str
    masked: str  # e.g., "4000 00** **** 1234"
    is_test_range: bool = True
    luhn_valid: bool = True

    def __str__(self) -> str:
        return self.masked


def _luhn_checksum(number: str) -> int:
    """Calculate Luhn checksum digit."""
    digits = [int(d) for d in number]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]

    total = sum(odd_digits)
    for d in even_digits:
        d *= 2
        if d > 9:
            d -= 9
        total += d

    return total % 10


def _generate_luhn_valid(prefix: str, length: int, rng: random.Random) -> str:
    """Generate a Luhn-valid number with the given prefix and total length."""
    remaining = length - len(prefix) - 1  # -1 for check digit
    body = prefix + "".join([str(rng.randint(0, 9)) for _ in range(remaining)])

    # Calculate check digit
    check = _luhn_checksum(body + "0")
    check_digit = (10 - check) % 10

    return body + str(check_digit)


def _mask_pan(pan: str) -> str:
    """Mask a PAN for display: show first 6 and last 4 digits."""
    if len(pan) <= 10:
        return pan
    visible_start = pan[:6]
    visible_end = pan[-4:]
    masked_middle = "*" * (len(pan) - 10)
    raw = visible_start + masked_middle + visible_end
    # Format with spaces every 4 characters
    return " ".join([raw[i:i + 4] for i in range(0, len(raw), 4)])


class PANGenerator:
    """
    Generates Luhn-valid synthetic PANs using test-only BIN ranges.

    Deterministic generator (ADR-5): all PANs are checksum-valid
    but use non-existent BIN ranges, ensuring they can never match
    a real cardholder's account.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def generate(
        self,
        network: CardNetwork = CardNetwork.TEST,
    ) -> GeneratedPAN:
        """
        Generate a single Luhn-valid test PAN.

        Args:
            network: Card network for BIN prefix selection.

        Returns:
            A GeneratedPAN with valid checksum.
        """
        bins = TEST_BINS.get(network, TEST_BINS[CardNetwork.TEST])
        bin_prefix = self._rng.choice(bins)
        length = PAN_LENGTHS.get(network, 16)

        pan = _generate_luhn_valid(bin_prefix, length, self._rng)

        result = GeneratedPAN(
            pan=pan,
            network=network,
            bin_prefix=bin_prefix,
            masked=_mask_pan(pan),
            is_test_range=True,
            luhn_valid=True,
        )

        logger.debug("pan_generated", network=network.value, masked=result.masked)
        return result

    def generate_batch(
        self,
        count: int,
        network: Optional[CardNetwork] = None,
        unique: bool = True,
    ) -> list[GeneratedPAN]:
        """Generate a batch of test PANs."""
        results: list[GeneratedPAN] = []
        seen: set[str] = set()

        for _ in range(count * 3):  # Max attempts
            if len(results) >= count:
                break

            net = network or self._rng.choice(list(CardNetwork))
            pan = self.generate(network=net)

            if unique and pan.pan in seen:
                continue

            seen.add(pan.pan)
            results.append(pan)

        logger.info("pan_batch_generated", count=len(results), requested=count)
        return results

    @staticmethod
    def validate_luhn(pan: str) -> bool:
        """Validate a PAN using Luhn algorithm."""
        try:
            return _luhn_checksum(pan) == 0
        except (ValueError, IndexError):
            return False


# ---------------------------------------------------------------------------
# Convenience functions
# ---------------------------------------------------------------------------

def generate_test_pan(network: CardNetwork = CardNetwork.TEST, seed: Optional[int] = None) -> str:
    """Quick-access function to generate a single test PAN string."""
    return PANGenerator(seed=seed).generate(network=network).pan


def generate_test_pans(count: int, seed: Optional[int] = None) -> list[str]:
    """Quick-access function to generate multiple test PAN strings."""
    return [p.pan for p in PANGenerator(seed=seed).generate_batch(count)]
