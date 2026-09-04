"""
Unit tests for MCP Gateway, Tool Registry, and PII Redaction Proxy.
"""

import pytest
from src.mcp_gateway.pii_redaction_proxy import PIIRedactionProxy
from src.mcp_gateway.tool_registry import MCPToolRegistry
from src.mcp_gateway.playwright_tool import PlaywrightMCPTool
from src.mcp_gateway.api_client_tool import APIClientMCPTool
from src.mcp_gateway.db_connector_tool import DBConnectorMCPTool
from src.mcp_gateway.iso20022_tool import ISO20022MCPTool


def test_pii_redaction_proxy():
    proxy = PIIRedactionProxy()
    sample_text = "Account IBAN DE89370400440532013000 transfer $500 for user test@example.com"
    res = proxy.redact_text(sample_text)
    assert "[REDACTED_IBAN_" in res.cleaned_text
    assert "[REDACTED_EMAIL_" in res.cleaned_text
    assert "test@example.com" not in res.cleaned_text
    assert res.redaction_count >= 2


def test_mcp_tool_registry_registration():
    registry = MCPToolRegistry()
    playwright_tool = PlaywrightMCPTool()
    api_tool = APIClientMCPTool()

    registry.register_tool(playwright_tool)
    registry.register_tool(api_tool)

    tools = registry.list_tools()
    assert len(tools) == 2
    assert registry.get_tool("playwright_driver") is not None


def test_mcp_tool_invocation_with_pii_redaction():
    registry = MCPToolRegistry()
    registry.register_tool(PlaywrightMCPTool())

    res = registry.invoke_tool(
        tool_name="playwright_driver",
        agent_id="test-agent",
        kwargs={"action": "navigate", "url": "https://banking.example.com"}
    )
    assert res.success is True
    assert res.data["status"] == "navigated"


def test_db_reconciler_tool():
    db_tool = DBConnectorMCPTool()
    res = db_tool.execute(operation="verify_double_entry", transaction_id="TX-100")
    assert res.success is True
    assert res.data["is_balanced"] is True
    assert res.data["total_debits"] == res.data["total_credits"]
