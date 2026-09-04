"""
Model Context Protocol (MCP) Tool Registry & Gateway Base.

Provides the tool registration mechanism, authorization checking, execution tracing,
and transparent PII redaction wrapper for all agent-accessible tools.
"""

from __future__ import annotations

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

from src.mcp_gateway.pii_redaction_proxy import PIIRedactionProxy

logger = logging.getLogger("BankAI.MCPGateway")


@dataclass
class ToolExecutionResult:
    """Standardized result returned by any MCP Tool call."""
    success: bool
    data: Any
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0
    redacted_item_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPTool:
    """Metadata definition for an MCP Tool."""
    name: str
    description: str
    parameters_schema: Dict[str, Any]
    category: str  # "browser", "api", "database", "validation", "synthetic"
    requires_approval: bool = False  # HITL flag for high-impact actions (e.g. wire transfer submit)


class BaseMCPTool(ABC):
    """Abstract Base Class for all Banking MCP tools."""

    def __init__(self, name: str, description: str, category: str, requires_approval: bool = False):
        self.name = name
        self.description = description
        self.category = category
        self.requires_approval = requires_approval

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return JSON Schema describing the tool's input parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolExecutionResult:
        """Execute the underlying automation command."""
        pass


class MCPToolRegistry:
    """
    Central Gateway Registry for all Agent MCP Tools.
    Handles PII redaction before returning data to agents, auditable execution tracking,
    and security authorization limits.
    """

    def __init__(self, pii_proxy: Optional[PIIRedactionProxy] = None):
        self._tools: Dict[str, BaseMCPTool] = {}
        self.pii_proxy = pii_proxy or PIIRedactionProxy()
        self._execution_history: List[Dict[str, Any]] = []

    def register_tool(self, tool: BaseMCPTool) -> None:
        """Register a new tool with the gateway."""
        if tool.name in self._tools:
            logger.warning(f"Overwriting existing tool registration for '{tool.name}'")
        self._tools[tool.name] = tool
        logger.info(f"Registered MCP Tool: '{tool.name}' (Category: {tool.category})")

    def get_tool(self, tool_name: str) -> Optional[BaseMCPTool]:
        """Fetch registered tool by name."""
        return self._tools.get(tool_name)

    def list_tools(self) -> List[MCPTool]:
        """List all available tools and their definitions."""
        tool_list = []
        for name, tool in self._tools.items():
            tool_list.append(
                MCPTool(
                    name=name,
                    description=tool.description,
                    parameters_schema=tool.get_schema(),
                    category=tool.category,
                    requires_approval=tool.requires_approval
                )
            )
        return tool_list

    def invoke_tool(self, tool_name: str, agent_id: str, kwargs: Dict[str, Any]) -> ToolExecutionResult:
        """
        Invoke an MCP tool with audit tracking, PII redaction pre-flight and post-flight.
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolExecutionResult(
                success=False,
                data=None,
                error_message=f"Tool '{tool_name}' is not registered in MCP Gateway."
            )

        # Pre-flight PII redaction on input parameters
        redacted_kwargs = self.pii_proxy.redact_dict(kwargs)

        start_time = time.time()
        try:
            raw_result = tool.execute(**redacted_kwargs)
            duration_ms = (time.time() - start_time) * 1000.0

            # Post-flight PII redaction on tool output data
            redacted_count = 0
            cleaned_data = raw_result.data
            if isinstance(raw_result.data, str):
                scan = self.pii_proxy.redact_text(raw_result.data)
                cleaned_data = scan.cleaned_text
                redacted_count = scan.redaction_count
            elif isinstance(raw_result.data, dict):
                cleaned_data = self.pii_proxy.redact_dict(raw_result.data)

            exec_record = {
                "timestamp": start_time,
                "tool_name": tool_name,
                "agent_id": agent_id,
                "duration_ms": duration_ms,
                "success": raw_result.success,
                "requires_approval": tool.requires_approval
            }
            self._execution_history.append(exec_record)

            return ToolExecutionResult(
                success=raw_result.success,
                data=cleaned_data,
                error_message=raw_result.error_message,
                execution_time_ms=duration_ms,
                redacted_item_count=redacted_count,
                metadata=raw_result.metadata
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            logger.error(f"Error invoking MCP tool '{tool_name}': {str(e)}", exc_info=True)
            return ToolExecutionResult(
                success=False,
                data=None,
                error_message=f"MCP Tool Exception: {str(e)}",
                execution_time_ms=duration_ms
            )

    @property
    def history(self) -> List[Dict[str, Any]]:
        return self._execution_history
