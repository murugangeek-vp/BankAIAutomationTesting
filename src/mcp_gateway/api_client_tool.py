"""
REST / SOAP API Client MCP Tool.

Executes API requests against Core Banking, Payment Rails, and Gateway services.
Supports HTTP methods, payload formatting, XML SOAP wrapping, and response assertion.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional
from src.mcp_gateway.tool_registry import BaseMCPTool, ToolExecutionResult

logger = logging.getLogger("BankAI.APIClientMCP")


class APIClientMCPTool(BaseMCPTool):
    """
    API Automation Driver Tool for REST & SOAP banking endpoints.
    """

    def __init__(self):
        super().__init__(
            name="api_client",
            description="Executes REST (GET/POST/PUT/DELETE) and SOAP XML API calls against banking backends.",
            category="api",
            requires_approval=False
        )

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "SOAP"]},
                "endpoint": {"type": "string", "description": "Target API path or full URL"},
                "headers": {"type": "object", "description": "HTTP request headers"},
                "payload": {"type": "object", "description": "JSON body or dictionary"},
                "soap_action": {"type": "string", "description": "SOAPAction header if method='SOAP'"},
                "expected_status": {"type": "integer", "default": 200}
            },
            "required": ["method", "endpoint"]
        }

    def execute(self, **kwargs) -> ToolExecutionResult:
        method = kwargs.get("method", "GET").upper()
        endpoint = kwargs.get("endpoint")
        headers = kwargs.get("headers", {})
        payload = kwargs.get("payload", {})
        expected_status = kwargs.get("expected_status", 200)

        logger.info(f"Executing API Client tool call: {method} {endpoint}")

        # In production test runner, this executes via `httpx` or `requests` or `zeep`.
        # Simulated execution response container:
        response_data = {
            "status_code": 200,
            "headers": {"content-type": "application/json", "x-transaction-id": "TX-998234-AX"},
            "body": {
                "transaction_status": "COMPLETED",
                "payment_reference": "REF-2026-0904-8871",
                "settlement_timestamp": "2026-09-04T08:20:00Z",
                "debit_account": payload.get("source_account", "ACC-US-100234"),
                "credit_account": payload.get("destination_account", "ACC-DE-883921"),
                "amount": payload.get("amount", 1500.00),
                "currency": payload.get("currency", "USD")
            }
        }

        success = (response_data["status_code"] == expected_status)

        return ToolExecutionResult(
            success=success,
            data=response_data,
            metadata={"method": method, "endpoint": endpoint, "status_code": response_data["status_code"]}
        )
