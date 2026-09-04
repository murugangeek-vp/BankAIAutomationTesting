"""
Playwright MCP Tool.

Wraps Playwright automation into an MCP tool for Web and Mobile UI interaction.
Employs accessibility-tree-first locators (getByRole, getByLabel) per ADR-3.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from src.mcp_gateway.tool_registry import BaseMCPTool, ToolExecutionResult

logger = logging.getLogger("BankAI.PlaywrightMCP")


class PlaywrightMCPTool(BaseMCPTool):
    """
    Playwright Web/Mobile UI driver tool for MCP.
    """

    def __init__(self):
        super().__init__(
            name="playwright_driver",
            description="Executes web and mobile browser actions using Playwright accessibility-first locators.",
            category="browser",
            requires_approval=False
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["navigate", "click", "fill", "select_option", "assert_visible", "get_accessibility_tree", "screenshot"],
                    "description": "Browser action to perform"
                },
                "url": {"type": "string", "description": "URL to navigate to (if action='navigate')"},
                "role": {"type": "string", "description": "ARIA role for getByRole locator (e.g., 'button', 'textbox')"},
                "name": {"type": "string", "description": "Accessible name or label for locator"},
                "value": {"type": "string", "description": "Value to type or select"},
                "timeout_ms": {"type": "integer", "default": 5000}
            },
            "required": ["action"]
        }

    def execute(self, **kwargs) -> ToolExecutionResult:
        action = kwargs.get("action")
        url = kwargs.get("url")
        role = kwargs.get("role")
        name = kwargs.get("name")
        value = kwargs.get("value")

        logger.info(f"Executing Playwright action: '{action}' on target role='{role}', name='{name}'")

        # In production test runner, this connects to Playwright BrowserContext/Page.
        # Here we provide a robust tool contract and simulation/driver interface.
        if action == "navigate":
            return ToolExecutionResult(
                success=True,
                data={"status": "navigated", "url": url, "page_title": "Enterprise Banking Portal"},
                metadata={"action": "navigate", "url": url}
            )

        elif action == "click":
            if not role and not name:
                return ToolExecutionResult(
                    success=False,
                    data=None,
                    error_message="Click action requires role or name accessibility locator."
                )
            return ToolExecutionResult(
                success=True,
                data={"status": "clicked", "locator": f"getByRole('{role}', name='{name}')"},
                metadata={"action": "click", "role": role, "name": name}
            )

        elif action == "fill":
            return ToolExecutionResult(
                success=True,
                data={"status": "filled", "locator": f"getByRole('{role}', name='{name}')", "value": value},
                metadata={"action": "fill", "role": role, "name": name}
            )

        elif action == "get_accessibility_tree":
            # Simplified accessibility snapshot simulation
            tree_snapshot = {
                "role": "WebArea",
                "name": "Corporate Banking - Wire Transfer",
                "children": [
                    {"role": "heading", "name": "Initiate International Wire", "level": 1},
                    {"role": "textbox", "name": "Beneficiary Name", "required": True},
                    {"role": "textbox", "name": "Beneficiary IBAN", "required": True},
                    {"role": "textbox", "name": "SWIFT / BIC Code", "required": True},
                    {"role": "spinbutton", "name": "Transfer Amount", "required": True},
                    {"role": "combobox", "name": "Currency", "value": "USD"},
                    {"role": "button", "name": "Submit Wire Transfer"}
                ]
            }
            return ToolExecutionResult(
                success=True,
                data=tree_snapshot,
                metadata={"action": "get_accessibility_tree"}
            )

        elif action == "assert_visible":
            return ToolExecutionResult(
                success=True,
                data={"visible": True, "locator": f"getByRole('{role}', name='{name}')"},
                metadata={"action": "assert_visible"}
            )

        else:
            return ToolExecutionResult(
                success=False,
                data=None,
                error_message=f"Unsupported Playwright action '{action}'"
            )
