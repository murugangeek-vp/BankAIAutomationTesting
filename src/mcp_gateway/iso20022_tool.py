"""
ISO 20022 Message Validation MCP Tool.

Exposes ISO 20022 message structure validation and SWIFT Nov 2026 structured address
conformance checks to LLM agents via MCP.
"""

from __future__ import annotations

import logging
from typing import Any, Dict
from src.mcp_gateway.tool_registry import BaseMCPTool, ToolExecutionResult
from src.synthetic_data.iso20022_validator import ISO20022Validator
from src.synthetic_data.address_validator import StructuredAddressValidator, StructuredAddress

logger = logging.getLogger("BankAI.ISO20022MCP")


class ISO20022MCPTool(BaseMCPTool):
    """
    ISO 20022 XML Message Validation Tool for MCP Gateway.
    """

    def __init__(self):
        super().__init__(
            name="iso20022_validator",
            description="Validates ISO 20022 XML payment messages (pacs.008, pacs.002, camt.053, pain.001) and SWIFT 2026 address mandates.",
            category="validation",
            requires_approval=False
        )
        self.validator = ISO20022Validator(enforce_structured_address_2026=True)
        self.address_validator = StructuredAddressValidator()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["validate_xml", "validate_address"],
                    "description": "Validation operation"
                },
                "xml_content": {"type": "string", "description": "ISO 20022 XML message payload string"},
                "address_data": {
                    "type": "object",
                    "properties": {
                        "street_name": {"type": "string"},
                        "building_number": {"type": "string"},
                        "town_name": {"type": "string"},
                        "country": {"type": "string"},
                        "post_code": {"type": "string"}
                    }
                }
            },
            "required": ["action"]
        }

    def execute(self, **kwargs) -> ToolExecutionResult:
        action = kwargs.get("action")
        xml_content = kwargs.get("xml_content")
        address_data = kwargs.get("address_data")

        if action == "validate_xml":
            if not xml_content:
                return ToolExecutionResult(
                    success=False,
                    data=None,
                    error_message="Missing required parameter 'xml_content' for validate_xml action."
                )

            report = self.validator.validate_xml_string(xml_content)
            issues_summary = [
                {
                    "code": issue.code,
                    "message": issue.message,
                    "field": issue.field_path,
                    "severity": issue.severity.value,
                    "rule": issue.rule_name,
                    "remediation": issue.suggested_remediation
                }
                for issue in report.issues
            ]

            return ToolExecutionResult(
                success=report.is_valid,
                data={
                    "is_valid": report.is_valid,
                    "message_type": report.message_type.value,
                    "structured_address_compliant": report.structured_address_compliant,
                    "issue_count": len(report.issues),
                    "issues": issues_summary
                },
                metadata={"action": action, "message_type": report.message_type.value}
            )

        elif action == "validate_address":
            if not address_data:
                return ToolExecutionResult(
                    success=False,
                    data=None,
                    error_message="Missing required parameter 'address_data'."
                )

            addr = StructuredAddress(
                street_name=address_data.get("street_name"),
                building_number=address_data.get("building_number"),
                town_name=address_data.get("town_name"),
                country=address_data.get("country"),
                post_code=address_data.get("post_code")
            )
            res = self.address_validator.validate(addr)

            return ToolExecutionResult(
                success=res.is_valid,
                data={
                    "is_valid": res.is_valid,
                    "swift_2026_compliant": res.is_swift_2026_compliant,
                    "fatf_travel_rule_compliant": res.fatf_travel_rule_compliant,
                    "errors": res.errors,
                    "warnings": res.warnings
                },
                metadata={"action": action}
            )

        else:
            return ToolExecutionResult(
                success=False,
                data=None,
                error_message=f"Unsupported ISO 20022 tool action '{action}'"
            )
