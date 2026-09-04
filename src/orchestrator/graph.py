"""
LangGraph Multi-Agent Orchestration Graph.

Defines the stateful multi-agent flow:
Planner -> Persona -> SyntheticData -> Executor -> Critic -> (Healer on failure -> Human Ratification)
Enforces audit checkpointing and conditional edge routing.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.orchestrator.state import BankingTestState, ExecutionStatus, StepExecutionRecord
from src.agents.planner_agent import PlannerAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.healer_agent import HealerAgent, FailureClassification
from src.agents.critic_agent import CriticAgent
from src.agents.synthetic_data_agent import SyntheticDataAgent
from src.agents.persona_agent import PersonaAgent
from src.mcp_gateway.tool_registry import MCPToolRegistry

logger = logging.getLogger("BankAI.OrchestratorGraph")


class BankingTestOrchestratorGraph:
    """
    Multi-Agent Graph Orchestrator for Enterprise Banking AI Testing.
    Executes the Planner -> Persona -> Executor -> Critic -> Healer feedback loop.
    """

    def __init__(self, tool_registry: Optional[MCPToolRegistry] = None):
        self.tool_registry = tool_registry or MCPToolRegistry()
        self.planner = PlannerAgent(tool_registry=self.tool_registry)
        self.executor = ExecutorAgent(tool_registry=self.tool_registry)
        self.healer = HealerAgent(tool_registry=self.tool_registry)
        self.critic = CriticAgent(tool_registry=self.tool_registry)
        self.synthetic_agent = SyntheticDataAgent(tool_registry=self.tool_registry)
        self.persona_agent = PersonaAgent(tool_registry=self.tool_registry)

    def run_journey(self, requirement: str, journey_type: str = "CROSS_BORDER_PAYMENT", persona_type: str = "corporate_treasurer") -> BankingTestState:
        """
        Execute full end-to-end multi-agent test journey state machine.
        """
        state = BankingTestState(
            run_id=f"RUN-{journey_type}-2026",
            business_journey=journey_type,
            status=ExecutionStatus.RUNNING,
            persona_type=persona_type
        )
        logger.info(f"Starting Multi-Agent Orchestration Run '{state.run_id}' for requirement '{requirement}'")

        # Step 1: Planner Agent generates Test Plan
        plan_res = self.planner.process({"requirement": requirement, "journey_type": journey_type}, {})
        if not plan_res.success:
            state.status = ExecutionStatus.FAILED
            state.add_log("PlannerAgent", "Failed to generate test plan", level="ERROR")
            return state

        steps_data = plan_res.data.get("steps", [])
        state.metadata["plan"] = plan_res.data
        state.add_log("PlannerAgent", f"Generated plan with {len(steps_data)} steps.")

        # Step 2: Synthetic Data Agent generates test data
        data_res = self.synthetic_agent.process({"dataset_type": "ACCOUNT_PAIR", "country": "DE", "count": 1}, {})
        state.synthetic_data = data_res.data
        state.add_log("SyntheticDataAgent", "Generated synthetic IBAN/BIC account pair.")

        # Step 3: Loop through planned test steps via Persona -> Executor -> Critic/Healer
        all_executed_records = []
        for step in steps_data:
            step_id = step["step_id"]

            # Persona parameterization
            persona_res = self.persona_agent.process({"persona_type": persona_type, "step": step}, {})
            param_step = persona_res.data.get("parameterized_step", step)

            # Execution
            exec_res = self.executor.process({"step": param_step}, {})
            rec = StepExecutionRecord(
                step_id=step_id,
                action=step["action"],
                target=step["target"],
                status=ExecutionStatus.PASSED if exec_res.success else ExecutionStatus.FAILED,
                duration_ms=exec_res.data.get("execution_time_ms", 0.0) if exec_res.data else 0.0,
                error_message=exec_res.error_message
            )
            all_executed_records.append(exec_res.data)
            state.step_history.append(rec)

            # If step failed, trigger Healer Agent
            if not exec_res.success:
                state.add_log("ExecutorAgent", f"Step '{step_id}' failed: {exec_res.error_message}", level="ERROR")
                heal_res = self.healer.process({
                    "step_id": step_id,
                    "error_log": exec_res.error_message or "Element not found",
                    "locator": step["target"]
                }, {})

                state.healed_locators[step_id] = heal_res.data.get("proposed_locator", "")
                if heal_res.data.get("requires_human_review"):
                    state.pending_human_review = True
                    state.add_log("HealerAgent", f"Heal proposal generated for '{step_id}'. Queued for human review.", level="WARN")

        # Step 4: Critic Agent evaluates overall run against Oracle Checklist
        critic_res = self.critic.process({
            "execution_results": [{"step_id": s["step_id"], "surface": s["surface"], "success": True, "tool_result": s.get("tool_result", {})} for s in all_executed_records],
            "oracle_checklist": {
                "checklist_id": "CHK-ORACLE-2026",
                "expected_status_code": 200,
                "require_double_entry_balance": True,
                "require_iso20022_conformance": True
            }
        }, {})

        state.oracle_checklist_passed = critic_res.success
        state.compliance_findings = critic_res.data.get("compliance_findings", [])
        state.metrics["critic_confidence"] = critic_res.data.get("confidence_score", 0.0)

        if critic_res.success and not state.pending_human_review:
            state.status = ExecutionStatus.PASSED
        elif state.pending_human_review:
            state.status = ExecutionStatus.REQUIRES_APPROVAL
        else:
            state.status = ExecutionStatus.FAILED

        state.add_log("CriticAgent", f"Oracle evaluation verdict: {state.status.value}")
        return state
