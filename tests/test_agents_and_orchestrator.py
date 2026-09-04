"""
Unit tests for Multi-Agent System & LangGraph Orchestrator.
"""

import pytest
from src.mcp_gateway.tool_registry import MCPToolRegistry
from src.mcp_gateway.playwright_tool import PlaywrightMCPTool
from src.mcp_gateway.api_client_tool import APIClientMCPTool
from src.mcp_gateway.db_connector_tool import DBConnectorMCPTool
from src.mcp_gateway.iso20022_tool import ISO20022MCPTool
from src.agents.planner_agent import PlannerAgent
from src.agents.executor_agent import ExecutorAgent
from src.agents.healer_agent import HealerAgent, FailureClassification
from src.agents.critic_agent import CriticAgent
from src.orchestrator.graph import BankingTestOrchestratorGraph
from src.orchestrator.state import ExecutionStatus


@pytest.fixture
def setup_mcp_registry():
    registry = MCPToolRegistry()
    registry.register_tool(PlaywrightMCPTool())
    registry.register_tool(APIClientMCPTool())
    registry.register_tool(DBConnectorMCPTool())
    registry.register_tool(ISO20022MCPTool())
    return registry


def test_planner_agent_decomposition(setup_mcp_registry):
    planner = PlannerAgent(tool_registry=setup_mcp_registry)
    res = planner.process({"requirement": "Test SWIFT Wire", "journey_type": "CROSS_BORDER_PAYMENT"}, {})
    assert res.success is True
    assert res.data["step_count"] == 6


def test_healer_agent_classification(setup_mcp_registry):
    healer = HealerAgent(tool_registry=setup_mcp_registry)
    # Test locator drift diagnosis
    res_drift = healer.process({"step_id": "STEP-01", "error_log": "Element getByRole('button', name='Submit Wire Transfer') not found", "locator": "getByRole('button', name='Submit Wire Transfer')"}, {})
    assert res_drift.data["classification"] == FailureClassification.LOCATOR_DRIFT.value
    assert res_drift.data["auto_apply_eligible"] is True

    # Test real bug diagnosis
    res_bug = healer.process({"step_id": "STEP-02", "error_log": "AssertionError: total_debits != total_credits"}, {})
    assert res_bug.data["classification"] == FailureClassification.REAL_BUG.value
    assert res_bug.data["auto_apply_eligible"] is False


def test_orchestrator_graph_end_to_end(setup_mcp_registry):
    graph = BankingTestOrchestratorGraph(tool_registry=setup_mcp_registry)
    state = graph.run_journey(
        requirement="Validate cross-border wire payment with structured address",
        journey_type="CROSS_BORDER_PAYMENT",
        persona_type="corporate_treasurer"
    )

    assert state.status in (ExecutionStatus.PASSED, ExecutionStatus.REQUIRES_APPROVAL)
    assert len(state.step_history) == 6
    assert state.oracle_checklist_passed is True
