"""
Critic / Oracle Validator Agent.

Validates Executor agent output against human-authored test oracles and compliance checklists.
Reflects 2026 benchmark findings: oracle-guided agents achieve up to 49% F1 defect detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, AgentResponse, AgentRole
from src.mcp_gateway.tool_registry import MCPToolRegistry

logger = logging.getLogger("BankAI.CriticAgent")


@dataclass
class OracleChecklist:
    """Human-authored oracle expectations for a given test flow."""
    checklist_id: str
    expected_status_code: int = 200
    require_double_entry_balance: bool = True
    require_iso20022_conformance: bool = True
    require_swift_2026_address: bool = True
    expected_response_fields: List[str] = field(default_factory=list)


@dataclass
class CriticismVerdict:
    """Critic evaluation result."""
    passed: bool
    confidence_score: float
    checks_evaluated: int
    failed_checks: List[str] = field(default_factory=list)
    compliance_findings: List[str] = field(default_factory=list)


class CriticAgent(BaseAgent):
    """
    Critic Agent responsible for verifying test execution results against
    rigorous human test oracles, regulatory mandates, and financial invariants.
    """

    def __init__(self, agent_id: str = "critic-01", tool_registry: Optional[MCPToolRegistry] = None):
        super().__init__(
            agent_id=agent_id,
            name="Oracle Verification Critic",
            role=AgentRole.CRITIC,
            tool_registry=tool_registry,
            token_budget=15000
        )

    def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> AgentResponse:
        """
        Evaluates execution results against an OracleChecklist.
        """
        execution_results = input_data.get("execution_results", [])
        oracle_dict = input_data.get("oracle_checklist", {})

        oracle = OracleChecklist(
            checklist_id=oracle_dict.get("checklist_id", "CHK-SWIFT-2026"),
            expected_status_code=oracle_dict.get("expected_status_code", 200),
            require_double_entry_balance=oracle_dict.get("require_double_entry_balance", True),
            require_iso20022_conformance=oracle_dict.get("require_iso20022_conformance", True),
            require_swift_2026_address=oracle_dict.get("require_swift_2026_address", True)
        )

        logger.info(f"[{self.agent_id}] Evaluating execution results against Oracle checklist '{oracle.checklist_id}'")

        verdict = self._evaluate_results(execution_results, oracle)

        return self.create_response(
            success=verdict.passed,
            content=f"Oracle evaluation completed. Passed: {verdict.passed} ({verdict.checks_evaluated - len(verdict.failed_checks)}/{verdict.checks_evaluated} checks passed)",
            data={
                "checklist_id": oracle.checklist_id,
                "passed": verdict.passed,
                "confidence_score": verdict.confidence_score,
                "checks_evaluated": verdict.checks_evaluated,
                "failed_checks": verdict.failed_checks,
                "compliance_findings": verdict.compliance_findings
            },
            tokens_used=350
        )

    def _evaluate_results(self, execution_results: List[Dict[str, Any]], oracle: OracleChecklist) -> CriticismVerdict:
        failed_checks: List[str] = []
        findings: List[str] = []
        total_checks = 0

        for res in execution_results:
            tool_data = res.get("tool_result", {})
            surface = res.get("surface")

            # Check 1: Tool invocation success
            total_checks += 1
            if not res.get("success", False):
                failed_checks.append(f"Step {res.get('step_id')} tool invocation reported failure.")

            # Check 2: API status code check
            if surface == "API":
                total_checks += 1
                status = tool_data.get("status_code", 0)
                if status != oracle.expected_status_code:
                    failed_checks.append(f"API HTTP status code was {status}, expected {oracle.expected_status_code}.")

            # Check 3: DB Ledger double-entry balance check
            if surface == "DB" and oracle.require_double_entry_balance:
                total_checks += 1
                is_balanced = tool_data.get("is_balanced", False)
                if not is_balanced:
                    failed_checks.append("DB double-entry check failed: total debits do not equal total credits.")
                    findings.append("CRITICAL: Ledger double-entry imbalance detected!")

            # Check 4: ISO 20022 message & address check
            if surface == "ISO20022":
                if oracle.require_iso20022_conformance:
                    total_checks += 1
                    if not tool_data.get("is_valid", False):
                        failed_checks.append("ISO 20022 XML validation failed schema/business rules.")

                if oracle.require_swift_2026_address:
                    total_checks += 1
                    if not tool_data.get("structured_address_compliant", False):
                        failed_checks.append("SWIFT 2026 Mandate Violation: Unstructured address present.")
                        findings.append("WARNING: Non-compliant address line detected for Nov 2026 SWIFT mandate.")

        passed = len(failed_checks) == 0
        confidence = 0.98 if passed else 0.85

        return CriticismVerdict(
            passed=passed,
            confidence_score=confidence,
            checks_evaluated=max(total_checks, 1),
            failed_checks=failed_checks,
            compliance_findings=findings
        )
