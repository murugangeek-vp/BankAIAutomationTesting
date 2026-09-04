"""
Shared state schema for the LangGraph orchestration layer.

This TypedDict defines the "whiteboard" that all agent nodes read from
and write to. LangGraph checkpoints this state automatically, enabling
audit-replay "time travel" — a hard requirement for SOX/PCI/RBI/PSD2 audits.

Design principle: Every field that an auditor might ask about ("what did
the agent see?", "what did it decide?", "what evidence supports the verdict?")
must be in this state so it gets checkpointed.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Optional, Sequence
from uuid import uuid4

from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums for structured state fields
# ---------------------------------------------------------------------------

class TestStatus(str, Enum):
    """Status of an individual test case."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    HEALED = "healed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"
    ERROR = "error"


class HealStatus(str, Enum):
    """Status of a healer-proposed fix."""
    PROPOSED = "proposed"
    AUTO_APPLIED = "auto_applied"
    QUEUED_FOR_REVIEW = "queued_for_review"
    RATIFIED = "ratified"
    REJECTED = "rejected"


class FindingSeverity(str, Enum):
    """Severity of an exploratory agent finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AgentDecisionType(str, Enum):
    """Types of decisions agents make — all logged for audit."""
    PLAN_CREATED = "plan_created"
    TEST_EXECUTED = "test_executed"
    HEAL_PROPOSED = "heal_proposed"
    HEAL_APPLIED = "heal_applied"
    HEAL_REJECTED = "heal_rejected"
    FINDING_REPORTED = "finding_reported"
    VERDICT_ADVISORY = "verdict_advisory"
    BUDGET_FALLBACK = "budget_fallback"
    HUMAN_ESCALATION = "human_escalation"


# ---------------------------------------------------------------------------
# Structured sub-models
# ---------------------------------------------------------------------------

class TestCase(BaseModel):
    """A single test case in the plan graph."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    description: str = ""
    test_type: str = "e2e"  # e2e | api | db | iso20022 | exploratory
    persona: Optional[str] = None
    priority: int = 1  # 1=highest
    status: TestStatus = TestStatus.PENDING
    assertions: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None
    is_compliance_critical: bool = False


class HealProposal(BaseModel):
    """A self-healing fix proposed by the Healer agent."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    test_case_id: str
    failure_type: str  # locator_drift | env_flake | real_regression
    old_locator: str
    new_locator: str
    confidence: float = Field(ge=0.0, le=1.0)
    status: HealStatus = HealStatus.PROPOSED
    rationale: str = ""
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    diff: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class Finding(BaseModel):
    """A candidate defect discovered by an exploratory agent."""
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str
    description: str
    severity: FindingSeverity = FindingSeverity.MEDIUM
    agent_role: str = "executor"
    evidence: dict[str, Any] = Field(default_factory=dict)
    steps_to_reproduce: list[str] = Field(default_factory=list)
    is_confirmed: bool = False  # Always False until human triage
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AgentDecision(BaseModel):
    """
    An auditable decision record.
    Every AI decision is captured here and written to the immutable ledger.
    """
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    decision_type: AgentDecisionType
    agent_role: str
    description: str
    rationale: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    confidence: Optional[float] = None


class TokenUsage(BaseModel):
    """Track token consumption per agent for cost governance."""
    agent_role: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Main graph state
# ---------------------------------------------------------------------------

class OrchestratorState(BaseModel):
    """
    The shared state for the LangGraph orchestration graph.

    All agent nodes read from and write to this state. LangGraph checkpoints
    it after every node execution, giving us full audit replay capability.

    Uses Annotated types with operator.add for fields that accumulate
    across nodes (messages, decisions, findings, etc.).
    """

    # --- Run metadata ---
    run_id: str = Field(default_factory=lambda: uuid4().hex)
    environment: str = "dev"
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    # --- Message history (LangGraph accumulates via operator.add) ---
    messages: Annotated[Sequence[BaseMessage], operator.add] = Field(
        default_factory=list
    )

    # --- Test plan ---
    test_plan: list[TestCase] = Field(default_factory=list)
    current_test_index: int = 0

    # --- Execution results ---
    passed_count: int = 0
    failed_count: int = 0
    healed_count: int = 0
    skipped_count: int = 0

    # --- Healer proposals ---
    heal_proposals: list[HealProposal] = Field(default_factory=list)
    pending_human_review: list[HealProposal] = Field(default_factory=list)

    # --- Findings (exploratory agents) ---
    findings: list[Finding] = Field(default_factory=list)

    # --- Audit trail ---
    decisions: list[AgentDecision] = Field(default_factory=list)

    # --- Token budget ---
    token_budget: int = 500_000
    tokens_consumed: int = 0
    token_usage_by_agent: list[TokenUsage] = Field(default_factory=list)
    budget_exhausted: bool = False

    # --- Routing control ---
    next_node: Optional[str] = None
    should_heal: bool = False
    should_escalate: bool = False
    iteration_count: int = 0
    max_iterations: int = 100

    # --- Persona context ---
    active_persona: Optional[str] = None
    persona_config: dict[str, Any] = Field(default_factory=dict)

    # --- Synthetic data ---
    synthetic_data_generated: dict[str, Any] = Field(default_factory=dict)

    # --- ISO 20022 context ---
    iso20022_messages: list[dict[str, Any]] = Field(default_factory=list)
    iso20022_validation_results: list[dict[str, Any]] = Field(default_factory=list)

    # --- Error state ---
    last_error: Optional[str] = None
    error_count: int = 0

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# High-Level Orchestrator Dataclasses & Enums
# ---------------------------------------------------------------------------

class ExecutionStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    RUNNING = "RUNNING"
    REQUIRES_APPROVAL = "REQUIRES_APPROVAL"
    CANCELLED = "CANCELLED"


@dataclass
class StepExecutionRecord:
    step_id: str
    action: str
    target: str
    status: ExecutionStatus
    duration_ms: float = 0.0
    error_message: Optional[str] = None


@dataclass
class BankingTestState:
    run_id: str
    business_journey: str
    status: ExecutionStatus = ExecutionStatus.RUNNING
    persona_type: str = "corporate_treasurer"
    synthetic_data: dict[str, Any] = field(default_factory=dict)
    step_history: list[StepExecutionRecord] = field(default_factory=list)
    healed_locators: dict[str, str] = field(default_factory=dict)
    pending_human_review: bool = False
    oracle_checklist_passed: bool = True
    compliance_findings: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    audit_logs: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_log(self, agent: str, message: str, level: str = "INFO") -> None:
        self.audit_logs.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "message": message,
            "level": level
        })

