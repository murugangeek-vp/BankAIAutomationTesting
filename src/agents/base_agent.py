"""
Abstract base agent with HITL hooks and audit integration.

All framework agents inherit from this base, which provides:
- Standardized lifecycle (plan → execute → validate → report)
- HITL approval gates for compliance-critical operations
- Automatic audit decision logging
- Token budget tracking and graceful degradation
- Structured error handling with evidence capture
"""

from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Any, Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.core.config import AgentRole, FrameworkConfig, ModelTier, get_config
from src.core.exceptions import (
    AgentError,
    TokenBudgetExhausted,
)
from src.core.logging_config import get_logger
from src.orchestrator.state import (
    AgentDecision,
    AgentDecisionType,
    OrchestratorState,
    TokenUsage,
)


from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentResponse:
    """Standardized response container for agent operations."""
    success: bool
    content: str
    data: Dict[str, Any] = field(default_factory=dict)
    tokens_used: int = 0
    error_message: Optional[str] = None


class BaseAgent(abc.ABC):
    """
    Abstract base for all agents in the Banking AI Testing Framework.

    Provides the shared infrastructure every agent needs:
    - LLM access with model-tier routing (frontier vs economy)
    - HITL hooks (pre-action approval, post-action review)
    - Token budget tracking
    - Audit decision recording
    - Structured logging with agent context
    """

    def __init__(
        self,
        role: AgentRole,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        tool_registry: Optional[Any] = None,
        token_budget: int = 10000,
        model_tier: ModelTier = ModelTier.ECONOMY,
        config: Optional[FrameworkConfig] = None,
    ) -> None:
        self.role = role
        self.agent_id = agent_id or f"{role.value}-01"
        self.name = name or f"Agent-{role.value}"
        self.tool_registry = tool_registry
        self.token_budget = token_budget
        self.model_tier = model_tier
        self.config = config or get_config()
        self.logger = get_logger(
            name=f"agent.{role.value}",
            agent_role=role.value,
        )

    def create_response(
        self,
        success: bool,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        error_message: Optional[str] = None,
    ) -> AgentResponse:
        """Helper method to construct an AgentResponse."""
        return AgentResponse(
            success=success,
            content=content,
            data=data or {},
            tokens_used=tokens_used,
            error_message=error_message
        )

        # Initialize LLM based on model tier
        model_name = (
            self.config.llm.frontier_model
            if model_tier == ModelTier.FRONTIER
            else self.config.llm.economy_model
        )
        temperature = (
            self.config.llm.temperature_frontier
            if model_tier == ModelTier.FRONTIER
            else self.config.llm.temperature_economy
        )

        self._llm = ChatAnthropic(
            model=model_name,
            temperature=temperature,
            max_tokens=4096,
            timeout=self.config.llm.request_timeout_seconds,
            max_retries=self.config.llm.max_retries,
        )

    # ------------------------------------------------------------------
    # Abstract interface — subclasses MUST implement
    # ------------------------------------------------------------------

    @abc.abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent role."""
        ...

    @abc.abstractmethod
    async def process(self, state: OrchestratorState) -> OrchestratorState:
        """
        Core processing logic for this agent.

        This is the main entry point called by the LangGraph node.
        Subclasses implement domain-specific logic here.
        """
        ...

    # ------------------------------------------------------------------
    # LLM interaction
    # ------------------------------------------------------------------

    async def invoke_llm(
        self,
        prompt: str,
        state: OrchestratorState,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Invoke the LLM with budget tracking and audit logging.

        Checks token budget before each call and gracefully degrades
        to deterministic execution on exhaustion (Section 8).
        """
        if state.budget_exhausted:
            self.logger.warning(
                "token_budget_exhausted_fallback",
                tokens_consumed=state.tokens_consumed,
                token_budget=state.token_budget,
            )
            raise TokenBudgetExhausted(
                budget=state.token_budget,
                consumed=state.tokens_consumed,
                agent_role=self.role.value,
                run_id=state.run_id,
            )

        sys_prompt = system_prompt or self.get_system_prompt()
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=prompt),
        ]

        self.logger.info(
            "llm_invoke_start",
            model=self._llm.model,
            prompt_length=len(prompt),
        )

        try:
            response = await self._llm.ainvoke(messages)

            # Track token usage
            usage = response.usage_metadata or {}
            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            total_tokens = input_tokens + output_tokens

            state.tokens_consumed += total_tokens
            state.token_usage_by_agent.append(
                TokenUsage(
                    agent_role=self.role.value,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model=self._llm.model,
                )
            )

            # Check if budget is now exhausted
            if state.tokens_consumed >= state.token_budget:
                state.budget_exhausted = True
                self.logger.warning(
                    "token_budget_reached",
                    consumed=state.tokens_consumed,
                    budget=state.token_budget,
                )

            self.logger.info(
                "llm_invoke_complete",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_consumed=state.tokens_consumed,
            )

            return response.content  # type: ignore[return-value]

        except Exception as e:
            self.logger.error("llm_invoke_failed", error=str(e))
            raise AgentError(
                f"LLM invocation failed: {e}",
                agent_role=self.role.value,
                run_id=state.run_id,
            ) from e

    # ------------------------------------------------------------------
    # HITL (Human-in-the-Loop) hooks
    # ------------------------------------------------------------------

    async def request_human_approval(
        self,
        action_description: str,
        evidence: dict[str, Any],
        state: OrchestratorState,
        auto_approve_in_ci: bool = False,
    ) -> bool:
        """
        Request human approval for a compliance-critical action.

        In CI mode, can optionally auto-approve non-critical actions
        to avoid blocking the pipeline. Critical actions ALWAYS require
        human review (ADR-2).

        Returns True if approved, False if rejected/pending.
        """
        from src.core.config import EnvironmentType

        self.logger.info(
            "hitl_approval_requested",
            action=action_description,
            auto_approve_ci=auto_approve_in_ci,
        )

        # Record the escalation decision
        self.record_decision(
            state=state,
            decision_type=AgentDecisionType.HUMAN_ESCALATION,
            description=f"Human approval requested: {action_description}",
            evidence=evidence,
        )

        # In CI with auto-approve enabled for non-critical items
        if auto_approve_in_ci and self.config.environment == EnvironmentType.CI:
            self.logger.info("hitl_auto_approved_ci", action=action_description)
            return True

        # Queue for human review — actual approval happens via HITL dashboard
        state.should_escalate = True
        return False

    async def notify_human(
        self,
        message: str,
        severity: str = "INFO",
        evidence: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Send a notification to the human supervisor.
        Used for findings, warnings, and FYI-level updates.
        """
        self.logger.info(
            "hitl_notification",
            message=message,
            severity=severity,
            evidence_keys=list((evidence or {}).keys()),
        )

    # ------------------------------------------------------------------
    # Audit decision recording
    # ------------------------------------------------------------------

    def record_decision(
        self,
        state: OrchestratorState,
        decision_type: AgentDecisionType,
        description: str,
        rationale: str = "",
        evidence: Optional[dict[str, Any]] = None,
        confidence: Optional[float] = None,
    ) -> AgentDecision:
        """
        Record an auditable decision to the orchestrator state.

        Every agent decision is captured in the state, which gets
        checkpointed by LangGraph and written to the immutable audit ledger.
        """
        decision = AgentDecision(
            decision_type=decision_type,
            agent_role=self.role.value,
            description=description,
            rationale=rationale,
            evidence=evidence or {},
            confidence=confidence,
        )
        state.decisions.append(decision)

        self.logger.info(
            "decision_recorded",
            decision_type=decision_type.value,
            description=description,
            confidence=confidence,
        )

        return decision

    # ------------------------------------------------------------------
    # Lifecycle wrapper
    # ------------------------------------------------------------------

    async def run(self, state: OrchestratorState) -> OrchestratorState:
        """
        Full lifecycle execution with error handling and audit wrapping.

        This is what the LangGraph node calls. It wraps the subclass's
        process() method with standardized pre/post processing.
        """
        self.logger.info(
            "agent_run_start",
            run_id=state.run_id,
            iteration=state.iteration_count,
        )

        try:
            state = await self.process(state)

            self.logger.info(
                "agent_run_complete",
                run_id=state.run_id,
                decisions_count=len(state.decisions),
            )

        except TokenBudgetExhausted:
            self.logger.warning("agent_budget_exhausted_graceful_degradation")
            self.record_decision(
                state=state,
                decision_type=AgentDecisionType.BUDGET_FALLBACK,
                description="Token budget exhausted — falling back to deterministic execution.",
            )

        except AgentError as e:
            self.logger.error("agent_run_failed", error=str(e))
            state.last_error = str(e)
            state.error_count += 1
            self.record_decision(
                state=state,
                decision_type=AgentDecisionType.HUMAN_ESCALATION,
                description=f"Agent error requiring review: {e}",
                evidence=e.to_audit_dict(),
            )

        except Exception as e:
            self.logger.error("agent_run_unexpected_error", error=str(e), exc_info=True)
            state.last_error = f"Unexpected error in {self.role.value}: {e}"
            state.error_count += 1

        return state
