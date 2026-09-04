"""
US Routing Number (ABA RTN) generator for synthetic test data.

Generates valid 9-digit routing numbers using the ABA checksum algorithm
with test-only Federal Reserve district prefixes.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from src.core.logging_config import get_logger

logger = get_logger(__name__)

# Test-only routing number prefixes (Federal Reserve district codes 00-12)
# We use the 00 prefix range which is reserved for US government/test
TEST_ROUTING_PREFIXES = [
    "0000",  # Test range — not assigned to any real bank
    "0001",
    "0002",
    "9999",  # Reserved test range
]


@dataclass
class GeneratedRoutingNumber:
    """A generated test ABA routing number."""
    routing_number: str
    prefix: str
    is_test_range: bool = True
    checksum_valid: bool = True

    def __str__(self) -> str:
        return self.routing_number


def _aba_checksum(digits: str) -> int:
    """
    Calculate ABA routing number checksum.
    Formula: 3(d1+d4+d7) + 7(d2+d5+d8) + (d3+d6+d9) ≡ 0 (mod 10)
    """
    d = [int(c) for c in digits]
    return (3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + (d[2] + d[5] + d[8])) % 10


def _generate_valid_routing(prefix: str, rng: random.Random) -> str:
    """Generate a 9-digit ABA routing number with valid checksum."""
    # Fill digits 5-8 randomly
    middle = "".join([str(rng.randint(0, 9)) for _ in range(4)])
    partial = prefix + middle  # 8 digits

    # Calculate check digit (digit 9)
    d = [int(c) for c in partial]
    # We need: 3(d1+d4+d7) + 7(d2+d5+d8) + (d3+d6+d9) ≡ 0 (mod 10)
    partial_sum = 3 * (d[0] + d[3] + d[6]) + 7 * (d[1] + d[4] + d[7]) + d[2] + d[5]
    check_digit = (10 - (partial_sum % 10)) % 10

    return partial + str(check_digit)


class RoutingNumberGenerator:
    """
    Generates valid ABA routing numbers for test data.

    Uses test-only prefix ranges (0000, 0001, 9999) that are not
    allocated to real financial institutions.
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    def generate(self) -> GeneratedRoutingNumber:
        """Generate a single valid test routing number."""
        prefix = self._rng.choice(TEST_ROUTING_PREFIXES)
        rtn = _generate_valid_routing(prefix, self._rng)

        result = GeneratedRoutingNumber(
            routing_number=rtn,
            prefix=prefix,
        )
        logger.debug("routing_number_generated", rtn=result.routing_number)
        return result

    def generate_routing_number(self) -> str:
        """Alias returning 9-digit routing string."""
        return self.generate().routing_number

    @staticmethod
    def validate_checksum(routing_number: str) -> bool:
        """Alias for validate checksum."""
        return RoutingNumberGenerator.validate(routing_number)

    def generate_batch(self, count: int, unique: bool = True) -> list[GeneratedRoutingNumber]:
        """Generate a batch of test routing numbers."""
        results: list[GeneratedRoutingNumber] = []
        seen: set[str] = set()

        for _ in range(count * 3):
            if len(results) >= count:
                break
            rtn = self.generate()
            if unique and rtn.routing_number in seen:
                continue
            seen.add(rtn.routing_number)
            results.append(rtn)

        logger.info("routing_batch_generated", count=len(results))
        return results

    @staticmethod
    def validate(routing_number: str) -> bool:
        """Validate an ABA routing number checksum."""
        if len(routing_number) != 9 or not routing_number.isdigit():
            return False
        return _aba_checksum(routing_number) == 0


def generate_test_routing_number(seed: Optional[int] = None) -> str:
    """Quick-access function to generate a single test routing number."""
    return RoutingNumberGenerator(seed=seed).generate().routing_number
