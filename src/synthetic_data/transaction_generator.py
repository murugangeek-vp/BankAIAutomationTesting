"""
Synthetic transaction history generator.

Generates contextually coherent transaction data using deterministic
financial identifiers (IBAN, PAN, routing numbers) with LLM-optional
narrative enrichment for descriptions and merchant names.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from src.core.logging_config import get_logger
from src.synthetic_data.iban_generator import IBANGenerator
from src.synthetic_data.pan_generator import PANGenerator

logger = get_logger(__name__)


class TransactionType(str, Enum):
    """Types of banking transactions."""
    CREDIT = "credit"
    DEBIT = "debit"
    TRANSFER = "transfer"
    PAYMENT = "payment"
    WITHDRAWAL = "withdrawal"
    DEPOSIT = "deposit"
    FEE = "fee"
    INTEREST = "interest"
    REFUND = "refund"
    FX_CONVERSION = "fx_conversion"


class TransactionStatus(str, Enum):
    """Transaction processing status."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"
    ON_HOLD = "on_hold"


@dataclass
class SyntheticTransaction:
    """A synthetic banking transaction for test data."""
    id: str = field(default_factory=lambda: uuid4().hex[:16])
    type: TransactionType = TransactionType.DEBIT
    status: TransactionStatus = TransactionStatus.COMPLETED
    amount: float = 0.0
    currency: str = "USD"
    description: str = ""
    timestamp: str = ""
    sender_iban: str = ""
    receiver_iban: str = ""
    sender_name: str = ""
    receiver_name: str = ""
    reference: str = ""
    category: str = ""
    balance_after: float = 0.0
    fx_rate: Optional[float] = None
    fx_original_amount: Optional[float] = None
    fx_original_currency: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# Sample narrative data for realistic transaction descriptions
MERCHANT_NAMES = [
    "Whole Foods Market", "Amazon.com", "Starbucks", "Target Corp",
    "Shell Gas Station", "Netflix Inc", "Spotify", "Electric Company",
    "Water Utility Board", "City Parking Authority", "Delta Airlines",
    "Hilton Hotels", "CVS Pharmacy", "Uber Technologies", "DoorDash",
]

TRANSFER_DESCRIPTIONS = [
    "Monthly rent payment", "Salary transfer", "Investment contribution",
    "Insurance premium", "Loan repayment", "Child support",
    "Utility bill payment", "Tax payment", "Charitable donation",
    "Freelance payment", "Consulting fee", "Equipment purchase",
]

CATEGORIES = [
    "groceries", "dining", "transportation", "utilities", "entertainment",
    "healthcare", "housing", "education", "insurance", "investments",
    "travel", "shopping", "subscriptions", "fees", "income",
]

SENDER_NAMES = [
    "John Smith", "Jane Doe", "ACME Corp", "Global Trading LLC",
    "TechStart Inc", "City Council", "State Treasury", "PayCo Services",
]

RECEIVER_NAMES = [
    "Alice Johnson", "Bob Williams", "Metro Utilities", "Sunrise Properties",
    "National Insurance Co", "First Investments LLC", "CloudTech Solutions",
]


class TransactionGenerator:
    """
    Generates synthetic transaction histories with realistic patterns.

    Uses deterministic financial identifiers from IBAN/PAN generators
    and enriches with narrative context (descriptions, merchant names).
    """

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._iban_gen = IBANGenerator(seed=seed)
        self._pan_gen = PANGenerator(seed=seed)

    def generate_transaction(
        self,
        tx_type: Optional[TransactionType] = None,
        amount_range: tuple[float, float] = (10.0, 5000.0),
        currency: str = "USD",
        base_date: Optional[datetime] = None,
    ) -> SyntheticTransaction:
        """Generate a single synthetic transaction."""
        if tx_type is None:
            tx_type = self._rng.choice(list(TransactionType))

        if base_date is None:
            base_date = datetime.now(timezone.utc)

        amount = round(self._rng.uniform(*amount_range), 2)
        offset_hours = self._rng.randint(0, 720)  # Up to 30 days back
        timestamp = (base_date - timedelta(hours=offset_hours)).isoformat()

        sender_iban = self._iban_gen.generate_iban().iban
        receiver_iban = self._iban_gen.generate_iban().iban

        description = self._rng.choice(
            MERCHANT_NAMES if tx_type == TransactionType.DEBIT
            else TRANSFER_DESCRIPTIONS
        )

        return SyntheticTransaction(
            type=tx_type,
            status=self._rng.choice(list(TransactionStatus)),
            amount=amount,
            currency=currency,
            description=description,
            timestamp=timestamp,
            sender_iban=sender_iban,
            receiver_iban=receiver_iban,
            sender_name=self._rng.choice(SENDER_NAMES),
            receiver_name=self._rng.choice(RECEIVER_NAMES),
            reference=f"REF-{uuid4().hex[:8].upper()}",
            category=self._rng.choice(CATEGORIES),
            balance_after=round(self._rng.uniform(1000, 50000), 2),
        )

    def generate_history(
        self,
        count: int = 50,
        currency: str = "USD",
        days_back: int = 90,
    ) -> list[SyntheticTransaction]:
        """Generate a chronological transaction history."""
        base_date = datetime.now(timezone.utc)
        transactions = []

        for _ in range(count):
            tx = self.generate_transaction(
                currency=currency,
                base_date=base_date,
            )
            transactions.append(tx)

        # Sort chronologically
        transactions.sort(key=lambda t: t.timestamp)

        # Recalculate running balance
        balance = round(self._rng.uniform(5000, 100000), 2)
        for tx in transactions:
            if tx.type in (TransactionType.CREDIT, TransactionType.DEPOSIT, TransactionType.INTEREST, TransactionType.REFUND):
                balance += tx.amount
            else:
                balance -= tx.amount
            tx.balance_after = round(balance, 2)

        logger.info("transaction_history_generated", count=len(transactions), days_back=days_back)
        return transactions

    def generate_cross_border_payment(
        self,
        source_country: str = "US",
        target_country: str = "GB",
        amount: float = 10000.0,
        source_currency: str = "USD",
        target_currency: str = "GBP",
    ) -> SyntheticTransaction:
        """Generate a cross-border payment with FX conversion data."""
        fx_rate = round(self._rng.uniform(0.7, 1.5), 6)

        return SyntheticTransaction(
            type=TransactionType.FX_CONVERSION,
            status=TransactionStatus.COMPLETED,
            amount=round(amount * fx_rate, 2),
            currency=target_currency,
            description=f"Cross-border transfer {source_country} → {target_country}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            sender_iban=self._iban_gen.generate_iban(country_code=source_country).iban,
            receiver_iban=self._iban_gen.generate_iban(country_code=target_country).iban,
            sender_name=self._rng.choice(SENDER_NAMES),
            receiver_name=self._rng.choice(RECEIVER_NAMES),
            reference=f"SWIFT-{uuid4().hex[:8].upper()}",
            category="transfer",
            fx_rate=fx_rate,
            fx_original_amount=amount,
            fx_original_currency=source_currency,
        )
