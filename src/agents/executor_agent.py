"""
Executor Agent.

Drives multi-surface test steps by dispatching tool invocations to the MCP Gateway
(Web/Mobile Playwright, REST/SOAP API, DB ledger verification, and ISO 20022 validator).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, AgentResponse, AgentRole
from src.mcp_gateway.tool_registry import MCPToolRegistry, ToolExecutionResult

logger = logging.getLogger("BankAI.ExecutorAgent")


class ExecutorAgent(BaseAgent):
    """
    Executor Agent responsible for invoking MCP tools to perform automated test steps.
    """

    def __init__(self, agent_id: str = "executor-01", tool_registry: Optional[MCPToolRegistry] = None):
        super().__init__(
            role=AgentRole.EXECUTOR,
            agent_id=agent_id,
            name="Test Driver Executor",
            tool_registry=tool_registry,
            token_budget=20000
        )

    def get_system_prompt(self) -> str:
        return "You are the Executor Agent. Your role is to drive multi-surface test steps across Web, Mobile, API, and DB using MCP tools."

    def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> AgentResponse:
        """
        Executes a single TestStep or list of TestSteps.
        """
        step = input_data.get("step")
        if not step:
            return self.create_response(
                success=False,
                content="Executor Agent requires a 'step' input object.",
                error_message="Missing step parameter"
            )

        step_id = step.get("step_id", "UNKNOWN")
        surface = step.get("surface", "WEB")
        action = step.get("action", "")
        target = step.get("target", "")

        logger.info(f"[{self.agent_id}] Executing step '{step_id}' on surface '{surface}' via MCP")

        if not self.tool_registry:
            return self.create_response(
                success=False,
                content=f"Executor unable to execute step '{step_id}': Tool registry not attached.",
                error_message="ToolRegistry missing"
            )

        # Route step execution to appropriate MCP tool
        if surface == "WEB":
            tool_res = self.tool_registry.invoke_tool(
                tool_name="playwright_driver",
                agent_id=self.agent_id,
                kwargs={"action": action, "role": "button", "name": target} if action != "navigate" else {"action": "navigate", "url": target}
            )

        elif surface == "API":
            tool_res = self.tool_registry.invoke_tool(
                tool_name="api_client",
                agent_id=self.agent_id,
                kwargs={"method": action, "endpoint": target, "payload": step.get("payload", {})}
            )

        elif surface == "DB":
            tool_res = self.tool_registry.invoke_tool(
                tool_name="db_reconciler",
                agent_id=self.agent_id,
                kwargs={"operation": action, "transaction_id": "TX-998234-AX"}
            )

        elif surface == "ISO20022":
            sample_xml = step.get("payload", {}).get("xml_content", "<Document><FIToFICstmrCdtTrf><GrpHdr><MsgId>M123</MsgId><CreDtTm>2026-09-04T08:00:00Z</CreDtTm></GrpHdr></FIToFICstmrCdtTrf></Document>")
            tool_res = self.tool_registry.invoke_tool(
                tool_name="iso20022_validator",
                agent_id=self.agent_id,
                kwargs={"action": "validate_xml", "xml_content": sample_xml}
            )

        else:
            return self.create_response(
                success=False,
                content=f"Unsupported surface '{surface}' for step '{step_id}'",
                error_message=f"Unsupported surface {surface}"
            )

        return self.create_response(
            success=tool_res.success,
            content=f"Step {step_id} execution completed on surface {surface}.",
            data={
                "step_id": step_id,
                "surface": surface,
                "tool_result": tool_res.data,
                "execution_time_ms": tool_res.execution_time_ms,
                "redacted_item_count": tool_res.redacted_item_count
            },
            tokens_used=280,
            error_message=tool_res.error_message
        )
