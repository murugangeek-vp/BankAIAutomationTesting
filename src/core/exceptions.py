"""
Custom exception hierarchy for the Banking AI Testing Framework.

Provides structured, categorized exceptions that carry audit-relevant metadata
(agent role, run ID, evidence references) for every failure path.
Banking compliance requires reconstructable evidence for all failures,
so exceptions include context that flows into the immutable audit ledger.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BankTestFrameworkError(Exception):
    """
    Base exception for all framework errors.

    Carries audit metadata so every caught exception can be logged
    with full context into the immutable evidence ledger.
    """

    def __init__(
        self,
        message: str,
        *,
        agent_role: Optional[str] = None,
        run_id: Optional[str] = None,
        evidence: Optional[dict[str, Any]] = None,
        severity: str = "ERROR",
    ) -> None:
        super().__init__(message)
        self.agent_role = agent_role
        self.run_id = run_id
        self.evidence = evidence or {}
        self.severity = severity
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_audit_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for the immutable audit ledger."""
        return {
            "error_type": type(self).__name__,
            "message": str(self),
            "agent_role": self.agent_role,
            "run_id": self.run_id,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "evidence": self.evidence,
        }


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------

class ConfigurationError(BankTestFrameworkError):
    """Invalid or missing configuration."""
    pass


class ProductionEnvironmentError(ConfigurationError):
    """
    Raised when an agent attempts to connect to a production environment.
    This is a hard architectural constraint (Section 3.4, Section 5).
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(
            message or (
                "CRITICAL SECURITY VIOLATION: Agent attempted to connect to a production "
                "environment. Agents are architecturally prohibited from production access. "
                "This is enforced at config, network, and IAM levels."
            ),
            severity="CRITICAL",
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Agent errors
# ---------------------------------------------------------------------------

class AgentError(BankTestFrameworkError):
    """Base exception for agent-layer failures."""
    pass


class PlannerError(AgentError):
    """Planner agent failed to decompose a test plan."""
    pass


class ExecutorError(AgentError):
    """Executor agent encountered an execution failure."""
    pass


class HealerError(AgentError):
    """Healer agent failed during self-healing."""
    pass


class HealerConfidenceBelowThreshold(HealerError):
    """
    Healer's proposed fix has confidence below the auto-heal threshold.
    This triggers routing to the human review queue (HITL gate).
    """

    def __init__(
        self,
        message: str,
        *,
        confidence: float,
        threshold: float,
        proposed_fix: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.confidence = confidence
        self.threshold = threshold
        self.proposed_fix = proposed_fix or {}


class CriticError(AgentError):
    """Critic/Validator agent encountered a validation failure."""
    pass


class ComplianceCriticalFinding(CriticError):
    """
    Critic agent flagged a compliance-critical assertion failure.
    This MUST be escalated to human review — AI never adjudicates (ADR-2).
    """

    def __init__(
        self,
        message: str,
        *,
        checklist_item: Optional[str] = None,
        expected: Optional[Any] = None,
        actual: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, severity="CRITICAL", **kwargs)
        self.checklist_item = checklist_item
        self.expected = expected
        self.actual = actual


# ---------------------------------------------------------------------------
# MCP / Tool errors
# ---------------------------------------------------------------------------

class MCPError(BankTestFrameworkError):
    """MCP Tool Gateway error."""
    pass


class MCPToolNotFoundError(MCPError):
    """Requested MCP tool is not registered in the gateway."""
    pass


class MCPToolTimeoutError(MCPError):
    """MCP tool call exceeded the configured timeout."""
    pass


# ---------------------------------------------------------------------------
# PII errors
# ---------------------------------------------------------------------------

class PIIRedactionError(BankTestFrameworkError):
    """PII redaction proxy encountered an error — hard stop, not soft fail."""

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(
            message or "PII redaction proxy failed. Cannot proceed — data may leak to LLM context.",
            severity="CRITICAL",
            **kwargs,
        )


class PIILeakDetected(PIIRedactionError):
    """
    Post-redaction audit detected residual PII in content about to be sent to an LLM.
    This is a hard stop — the request is blocked.
    """
    pass


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

class ValidationError(BankTestFrameworkError):
    """Base for data/message validation failures."""
    pass


class ISO20022ValidationError(ValidationError):
    """ISO 20022 message failed XSD or business-rule validation."""

    def __init__(
        self,
        message: str,
        *,
        message_type: Optional[str] = None,
        schema_errors: Optional[list[str]] = None,
        business_rule_errors: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.message_type = message_type
        self.schema_errors = schema_errors or []
        self.business_rule_errors = business_rule_errors or []


class StructuredAddressError(ISO20022ValidationError):
    """
    Structured address conformance failure — critical for Nov 2026 SWIFT deadline.
    """
    pass


# ---------------------------------------------------------------------------
# Synthetic data errors
# ---------------------------------------------------------------------------

class SyntheticDataError(BankTestFrameworkError):
    """Synthetic data generation failed."""
    pass


class ProductionDataDetected(SyntheticDataError):
    """
    Detected production-derived data in a synthetic data pipeline.
    Hard gate — blocks generation (Section 3.3).
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(
            message or "Production-derived data detected in synthetic data pipeline. Generation blocked.",
            severity="CRITICAL",
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Evidence / audit errors
# ---------------------------------------------------------------------------

class EvidenceError(BankTestFrameworkError):
    """Evidence collection or audit ledger error."""
    pass


class AuditLedgerCorruptionError(EvidenceError):
    """
    Hash-chain integrity check failed on the audit ledger.
    Indicates potential tampering — escalate immediately.
    """

    def __init__(self, message: str = "", **kwargs: Any) -> None:
        super().__init__(
            message or "Audit ledger hash-chain integrity check failed. Possible tampering detected.",
            severity="CRITICAL",
            **kwargs,
        )


# ---------------------------------------------------------------------------
# Budget / cost errors
# ---------------------------------------------------------------------------

class TokenBudgetExhausted(BankTestFrameworkError):
    """
    Token budget for this run is exhausted.
    Agents must gracefully degrade to deterministic-only execution (Section 8).
    """

    def __init__(
        self,
        message: str = "",
        *,
        budget: int = 0,
        consumed: int = 0,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            message or f"Token budget exhausted ({consumed}/{budget}). Falling back to deterministic execution.",
            severity="WARNING",
            **kwargs,
        )
        self.budget = budget
        self.consumed = consumed
