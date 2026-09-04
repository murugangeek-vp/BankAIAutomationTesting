"""
Unit tests for Evidence Artifacts & Immutable Cryptographic Audit Ledger.
"""

import pytest
from src.evidence.ledger import ImmutableAuditLedger
from src.evidence.reporter import ComplianceReportGenerator
from src.orchestrator.state import BankingTestState, ExecutionStatus


def test_immutable_audit_ledger_integrity():
    ledger = ImmutableAuditLedger(run_id="RUN-TEST-001")
    assert len(ledger.chain) == 1
    assert ledger.chain[0].action_type == "GENESIS"

    # Add blocks
    ledger.record_event(agent_id="PlannerAgent", action_type="PLAN", payload={"steps": 5})
    ledger.record_event(agent_id="ExecutorAgent", action_type="TOOL_CALL", payload={"status": "OK"})

    assert len(ledger.chain) == 3
    assert ledger.verify_chain_integrity() is True


def test_audit_ledger_tamper_detection():
    ledger = ImmutableAuditLedger(run_id="RUN-TEST-002")
    ledger.record_event(agent_id="PlannerAgent", action_type="PLAN", payload={"steps": 3})

    assert ledger.verify_chain_integrity() is True

    # Intentionally tamper with a block's payload
    ledger.chain[1].payload["steps"] = 999

    # Verification must fail after tampering
    assert ledger.verify_chain_integrity() is False


def test_compliance_report_generator():
    reporter = ComplianceReportGenerator()
    state = BankingTestState(run_id="RUN-TEST-003", business_journey="CROSS_BORDER_PAYMENT", status=ExecutionStatus.PASSED)
    ledger = ImmutableAuditLedger(run_id=state.run_id)

    report_path = reporter.generate_json_report(state, ledger)
    assert report_path.endswith(".json")
