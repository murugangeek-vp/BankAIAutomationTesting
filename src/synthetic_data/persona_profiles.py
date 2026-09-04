"""
Persona profiles for persona-based journey simulation.

Defines behavioral archetypes (retail user, corporate treasurer,
fraud actor, accessibility persona) that parameterize the Executor agent.
Each persona includes behavioral patterns, transaction profiles,
and test scenarios that the persona would typically exercise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PersonaType(str, Enum):
    """Supported persona archetypes."""
    RETAIL_USER = "retail_user"
    CORPORATE_TREASURER = "corporate_treasurer"
    FRAUD_ACTOR = "fraud_actor"
    ACCESSIBILITY_USER = "accessibility_user"
    ELDER_USER = "elder_user"
    HIGH_NET_WORTH = "high_net_worth"
    SMALL_BUSINESS = "small_business"


@dataclass
class TransactionProfile:
    """Transaction behavior profile for a persona."""
    avg_transaction_amount: float = 100.0
    max_transaction_amount: float = 5000.0
    daily_transaction_limit: int = 10
    preferred_currencies: list[str] = field(default_factory=lambda: ["USD", "EUR"])
    typical_recipients: int = 5
    cross_border_frequency: float = 0.1  # 10% of transactions
    bulk_payment_enabled: bool = False
    recurring_payments: int = 3


@dataclass
class BehaviorPattern:
    """UI interaction behavior pattern for a persona."""
    typing_speed: str = "normal"  # slow | normal | fast
    navigation_style: str = "sequential"  # sequential | random | goal-directed
    error_tolerance: float = 0.8  # How often they retry vs abandon
    session_duration_minutes: int = 15
    uses_search: bool = True
    uses_keyboard_shortcuts: bool = False
    screen_reader_enabled: bool = False
    preferred_language: str = "en"
    timezone: str = "UTC"
    typing_speed_wpm: int = 60
    average_think_time_sec: float = 2.0
    patience_score: int = 3


@dataclass
class PersonaProfile:
    """
    Complete persona definition for test journey simulation.

    Each persona carries a behavioral archetype that the Executor agent
    uses to parameterize its test interactions, creating realistic
    and diverse test coverage.
    """
    type: PersonaType
    name: str
    description: str
    transaction_profile: TransactionProfile
    behavior: BehaviorPattern
    test_scenarios: list[str] = field(default_factory=list)
    risk_indicators: list[str] = field(default_factory=list)
    compliance_checks: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def persona_id(self) -> str:
        return self.type.value

    @property
    def persona_name(self) -> str:
        return self.name

    @property
    def persona_type(self) -> PersonaType:
        return self.type

    @property
    def behavioral(self) -> BehaviorPattern:
        return self.behavior


# ---------------------------------------------------------------------------
# Pre-built persona definitions
# ---------------------------------------------------------------------------

PERSONAS: dict[PersonaType, PersonaProfile] = {
    PersonaType.RETAIL_USER: PersonaProfile(
        type=PersonaType.RETAIL_USER,
        name="Sarah Chen — Retail Banking Customer",
        description=(
            "A typical retail banking customer who uses online banking "
            "for daily transactions, bill payments, and account management. "
            "Moderate tech literacy, expects intuitive UI flows."
        ),
        transaction_profile=TransactionProfile(
            avg_transaction_amount=150.0,
            max_transaction_amount=5000.0,
            daily_transaction_limit=10,
            preferred_currencies=["USD"],
            typical_recipients=5,
            cross_border_frequency=0.05,
            bulk_payment_enabled=False,
            recurring_payments=4,
        ),
        behavior=BehaviorPattern(
            typing_speed="normal",
            navigation_style="sequential",
            error_tolerance=0.7,
            session_duration_minutes=10,
            uses_search=True,
        ),
        test_scenarios=[
            "Login and view account balances",
            "Initiate domestic P2P transfer",
            "Set up recurring bill payment",
            "Download monthly statement (camt.053)",
            "Update personal information",
            "View transaction history with filters",
            "Request checkbook / debit card",
            "Contact customer support via chat",
        ],
        compliance_checks=[
            "KYC data visibility matches entitlements",
            "Transaction limits enforced per account tier",
            "Session timeout after inactivity",
            "2FA required for high-value transfers",
        ],
    ),

    PersonaType.CORPORATE_TREASURER: PersonaProfile(
        type=PersonaType.CORPORATE_TREASURER,
        name="Marcus Johnson — Corporate Treasury Manager",
        description=(
            "A corporate treasurer managing multi-entity, multi-currency "
            "accounts. Performs bulk payments (pain.001), cross-border transfers "
            "(pacs.008), and liquidity management. High transaction volumes, "
            "strict approval workflows."
        ),
        transaction_profile=TransactionProfile(
            avg_transaction_amount=50000.0,
            max_transaction_amount=10_000_000.0,
            daily_transaction_limit=200,
            preferred_currencies=["USD", "EUR", "GBP", "CHF", "JPY"],
            typical_recipients=50,
            cross_border_frequency=0.6,
            bulk_payment_enabled=True,
            recurring_payments=20,
        ),
        behavior=BehaviorPattern(
            typing_speed="fast",
            navigation_style="goal-directed",
            error_tolerance=0.9,
            session_duration_minutes=60,
            uses_search=True,
            uses_keyboard_shortcuts=True,
        ),
        test_scenarios=[
            "Upload bulk payment file (pain.001) with 500+ payments",
            "Initiate cross-border FX conversion payment (pacs.008)",
            "Review and approve pending payment batch",
            "Multi-level approval workflow (maker-checker-approver)",
            "Real-time liquidity dashboard across entities",
            "Intraday statement download (camt.054)",
            "End-of-day statement reconciliation (camt.053)",
            "Set up standing instructions for FX hedging",
            "Manage beneficiary lists with AML screening",
            "SWIFT gpi payment tracking end-to-end",
        ],
        compliance_checks=[
            "Dual-control / maker-checker enforced for all payments",
            "FX rate transparency and fee disclosure",
            "SWIFT structured address compliance (Nov 2026 deadline)",
            "Sanctions/AML screening before payment release",
            "Segregation of duties between entities",
            "Audit trail for every approval action",
        ],
    ),

    PersonaType.FRAUD_ACTOR: PersonaProfile(
        type=PersonaType.FRAUD_ACTOR,
        name="Adversarial Agent — Fraud Simulation",
        description=(
            "Simulates a fraud actor probing velocity limits, account takeover "
            "vectors, social engineering paths, and payment manipulation attempts. "
            "Tests the bank's defensive controls and detection capabilities."
        ),
        transaction_profile=TransactionProfile(
            avg_transaction_amount=999.0,
            max_transaction_amount=9999.0,
            daily_transaction_limit=50,
            preferred_currencies=["USD", "EUR", "GBP"],
            typical_recipients=20,
            cross_border_frequency=0.8,
            bulk_payment_enabled=False,
            recurring_payments=0,
        ),
        behavior=BehaviorPattern(
            typing_speed="fast",
            navigation_style="random",
            error_tolerance=1.0,  # Never gives up
            session_duration_minutes=5,
            uses_search=False,
        ),
        test_scenarios=[
            "Rapid-fire login attempts (velocity check)",
            "Account takeover via password reset flow",
            "Transaction amount just below reporting threshold ($9,999)",
            "Rapid sequential transfers to multiple new beneficiaries",
            "Modify beneficiary details mid-payment-flow",
            "Attempt to bypass 2FA via session manipulation",
            "Cross-border payments to high-risk jurisdictions",
            "Duplicate payment submission (idempotency test)",
            "Attempt to access other users' account data (IDOR)",
            "Inject malicious payloads in payment reference fields",
        ],
        risk_indicators=[
            "Multiple failed login attempts",
            "Unusual transaction velocity",
            "New device / unusual geolocation",
            "Payments to sanctioned countries",
            "Amount structuring below reporting thresholds",
        ],
        compliance_checks=[
            "Rate limiting on authentication endpoints",
            "AML transaction monitoring alerts trigger correctly",
            "IDOR protection across all account-scoped endpoints",
            "Input validation on all payment fields",
            "Idempotency key enforcement prevents duplicate payments",
        ],
    ),

    PersonaType.ACCESSIBILITY_USER: PersonaProfile(
        type=PersonaType.ACCESSIBILITY_USER,
        name="Alex Rivera — Screen Reader User",
        description=(
            "A visually impaired user navigating the banking portal with a screen "
            "reader (NVDA/JAWS). Tests WCAG 2.1 AA compliance, keyboard navigation, "
            "ARIA landmarks, and accessible error announcements."
        ),
        transaction_profile=TransactionProfile(
            avg_transaction_amount=200.0,
            max_transaction_amount=3000.0,
            daily_transaction_limit=5,
        ),
        behavior=BehaviorPattern(
            typing_speed="slow",
            navigation_style="sequential",
            error_tolerance=0.5,  # Lower tolerance — frustrated by inaccessible flows
            session_duration_minutes=20,
            uses_search=True,
            uses_keyboard_shortcuts=True,
            screen_reader_enabled=True,
        ),
        test_scenarios=[
            "Complete login flow using keyboard only",
            "Navigate account dashboard via ARIA landmarks",
            "Initiate transfer using screen reader",
            "Read and understand error messages via live regions",
            "Navigate data tables (transaction history) with screen reader",
            "Complete form submission without mouse interaction",
            "Verify color contrast ratios on all text elements",
            "Test focus management after modal dialogs",
        ],
        compliance_checks=[
            "All interactive elements have accessible names",
            "Focus order follows visual layout",
            "Error messages announced via aria-live regions",
            "Form inputs have associated labels",
            "Images have alt text (decorative images have empty alt)",
            "Color is not the sole means of conveying information",
            "Minimum contrast ratio 4.5:1 for normal text",
            "Skip navigation link present",
        ],
    ),

    PersonaType.ELDER_USER: PersonaProfile(
        type=PersonaType.ELDER_USER,
        name="Dorothy Hayes — Senior Banking Customer",
        description=(
            "An elderly customer with limited digital literacy. "
            "Needs clear, simple navigation, large text, and helpful "
            "error messages. Tests usability for less tech-savvy users."
        ),
        transaction_profile=TransactionProfile(
            avg_transaction_amount=300.0,
            max_transaction_amount=2000.0,
            daily_transaction_limit=3,
        ),
        behavior=BehaviorPattern(
            typing_speed="slow",
            navigation_style="sequential",
            error_tolerance=0.3,  # Very low — gives up quickly
            session_duration_minutes=25,
            uses_search=False,
        ),
        test_scenarios=[
            "Login with clear step-by-step guidance",
            "View account balance with large font",
            "Simple domestic transfer with confirmation",
            "Understand and recover from form errors",
            "Print transaction receipt",
            "Access help/FAQ from any page",
        ],
        compliance_checks=[
            "Text resizable to 200% without loss of content",
            "Clear, jargon-free error messages",
            "Confirmation step before irreversible actions",
            "Easy access to customer support",
        ],
    ),
}


def get_persona(persona_type: PersonaType) -> PersonaProfile:
    """Get a pre-built persona profile by type."""
    return PERSONAS.get(persona_type, PERSONAS[PersonaType.RETAIL_USER])


def list_personas() -> list[PersonaType]:
    """List all available persona types."""
    return list(PERSONAS.keys())


class PersonaCatalog:
    """Catalog wrapper class for persona lookups."""
    def get_persona(self, persona_type: PersonaType) -> PersonaProfile:
        return get_persona(persona_type)

    def list_personas(self) -> list[PersonaType]:
        return list_personas()
