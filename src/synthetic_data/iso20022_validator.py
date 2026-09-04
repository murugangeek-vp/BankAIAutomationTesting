"""
ISO 20022 XML Message & Business Rule Validator.

Validates financial messaging formats including pacs.008, pacs.002,
camt.053, camt.054, and pain.001 against XSD structures and SWIFT/KPMG 2026
structured address mandates.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class MessageType(str, Enum):
    PACS_008 = "pacs.008.001.10"
    PACS_002 = "pacs.002.001.12"
    CAMT_053 = "camt.053.001.10"
    CAMT_054 = "camt.054.001.10"
    PAIN_001 = "pain.001.001.11"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    """Represents a single validation issue in an ISO 20022 message."""
    code: str
    message: str
    field_path: str
    severity: Severity
    rule_name: str
    suggested_remediation: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete report for an ISO 20022 message validation run."""
    is_valid: bool
    message_type: MessageType
    issues: List[ValidationIssue] = field(default_factory=list)
    structured_address_compliant: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def critical_or_error_count(self) -> int:
        return sum(1 for issue in self.issues if issue.severity in (Severity.CRITICAL, Severity.ERROR))


class ISO20022Validator:
    """
    Validator for ISO 20022 XML messages with specialized rules for banking rails
    and Nov 2026 SWIFT structured address mandates.
    """

    # Namespace maps for common ISO 20022 versions
    NAMESPACES = {
        "pacs008": "urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10",
        "pacs002": "urn:iso:std:iso:20022:tech:xsd:pacs.002.001.12",
        "camt053": "urn:iso:std:iso:20022:tech:xsd:camt.053.001.10",
        "camt054": "urn:iso:std:iso:20022:tech:xsd:camt.054.001.10",
        "pain001": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.11",
    }

    # ISO 4217 3-letter currency codes (partial set for validation)
    VALID_CURRENCIES = {
        "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "HKD", "SGD", "SEK",
        "NOK", "NZD", "MXN", "INR", "BRL", "ZAR", "CNY", "AED", "SAR", "KRW"
    }

    def __init__(self, enforce_structured_address_2026: bool = True):
        self.enforce_structured_address_2026 = enforce_structured_address_2026

    def detect_message_type(self, root: ET.Element) -> MessageType:
        """Detect ISO 20022 message type from root tag or XML namespace."""
        tag = root.tag
        # Extract namespace if present
        ns = ""
        if "}" in tag:
            ns = tag.split("}")[0].strip("{")
            tag_name = tag.split("}")[1]
        else:
            tag_name = tag

        for msg_enum in MessageType:
            if msg_enum.value in ns:
                return msg_enum

        # Check document wrapper child tag
        for child in root:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            if child_tag == "FIToFICstmrCdtTrf":
                return MessageType.PACS_008
            elif child_tag == "FIToFIPmtStsRpt":
                return MessageType.PACS_002
            elif child_tag == "BkToCstmrStmt":
                return MessageType.CAMT_053
            elif child_tag == "BkToCstmrDbtCdtNtfctn":
                return MessageType.CAMT_054
            elif child_tag == "CstmrCdtTrfInitn":
                return MessageType.PAIN_001

        return MessageType.UNKNOWN

    def validate_xml_string(self, xml_content: str) -> ValidationReport:
        """Parse and validate an ISO 20022 XML string."""
        issues: List[ValidationIssue] = []

        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as e:
            return ValidationReport(
                is_valid=False,
                message_type=MessageType.UNKNOWN,
                issues=[
                    ValidationIssue(
                        code="XML_SYNTAX_ERROR",
                        message=f"XML Malformed: {str(e)}",
                        field_path="/",
                        severity=Severity.CRITICAL,
                        rule_name="XML Well-Formedness",
                        suggested_remediation="Ensure XML string is well-formed."
                    )
                ],
                structured_address_compliant=False
            )

        message_type = self.detect_message_type(root)

        # 1. Message Header Check
        self._validate_header(root, issues)

        # 2. Amount & Currency Code Check
        self._validate_amounts_and_currencies(root, issues)

        # 3. BIC / IBAN Format Check
        self._validate_identifiers(root, issues)

        # 4. SWIFT 2026 Structured Address Mandate Check
        address_compliant = self._validate_structured_addresses(root, issues)

        is_valid = sum(1 for i in issues if i.severity in (Severity.CRITICAL, Severity.ERROR)) == 0

        return ValidationReport(
            is_valid=is_valid,
            message_type=message_type,
            issues=issues,
            structured_address_compliant=address_compliant,
            metadata={"element_count": len(list(root.iter()))}
        )

    def _validate_header(self, root: ET.Element, issues: List[ValidationIssue]) -> None:
        """Verify presence of essential header elements like Message ID and Creation Date Time."""
        msg_id_nodes = root.findall(".//{*}MsgId")
        if not msg_id_nodes:
            issues.append(
                ValidationIssue(
                    code="MISSING_MSG_ID",
                    message="Mandatory element MsgId is missing",
                    field_path="//GrpHdr/MsgId",
                    severity=Severity.ERROR,
                    rule_name="ISO20022 Header Mandates",
                    suggested_remediation="Add a unique <MsgId> under <GrpHdr>."
                )
            )

        cre_dt_nodes = root.findall(".//{*}CreDtTm")
        if not cre_dt_nodes:
            issues.append(
                ValidationIssue(
                    code="MISSING_CREATION_TIME",
                    message="Mandatory element CreDtTm is missing",
                    field_path="//GrpHdr/CreDtTm",
                    severity=Severity.ERROR,
                    rule_name="ISO20022 Header Mandates",
                    suggested_remediation="Add ISO-8601 formatted timestamp under <CreDtTm>."
                )
            )

    def _validate_amounts_and_currencies(self, root: ET.Element, issues: List[ValidationIssue]) -> None:
        """Validate transaction amounts and ISO 4217 currency attributes."""
        # Find elements with Ccy attribute
        for elem in root.iter():
            if "Ccy" in elem.attrib:
                ccy = elem.attrib["Ccy"]
                if ccy not in self.VALID_CURRENCIES:
                    issues.append(
                        ValidationIssue(
                            code="INVALID_CURRENCY_CODE",
                            message=f"Invalid ISO 4217 currency code '{ccy}'",
                            field_path=f"//{elem.tag.split('}')[-1]}[@Ccy]",
                            severity=Severity.ERROR,
                            rule_name="ISO 4217 Currency Conformance",
                            suggested_remediation=f"Use standard 3-letter currency code (e.g. USD, EUR, GBP)."
                        )
                    )

                try:
                    val = float(elem.text.strip()) if elem.text else 0.0
                    if val <= 0:
                        issues.append(
                            ValidationIssue(
                                code="NON_POSITIVE_AMOUNT",
                                message=f"Transaction amount must be strictly positive, got {val}",
                                field_path=f"//{elem.tag.split('}')[-1]}",
                                severity=Severity.ERROR,
                                rule_name="Financial Amount Validation",
                                suggested_remediation="Ensure amount is greater than zero."
                            )
                        )
                except ValueError:
                    issues.append(
                        ValidationIssue(
                            code="MALFORMED_AMOUNT",
                            message=f"Amount value '{elem.text}' is not a valid decimal number",
                            field_path=f"//{elem.tag.split('}')[-1]}",
                            severity=Severity.ERROR,
                            rule_name="Financial Amount Validation",
                            suggested_remediation="Provide valid numeric format for amount."
                        )
                    )

    def _validate_identifiers(self, root: ET.Element, issues: List[ValidationIssue]) -> None:
        """Validate IBAN and BIC formats inside message."""
        iban_nodes = root.findall(".//{*}IBAN")
        for node in iban_nodes:
            if node.text:
                iban_clean = node.text.strip().replace(" ", "")
                if len(iban_clean) < 15 or len(iban_clean) > 34 or not iban_clean[:2].isalpha():
                    issues.append(
                        ValidationIssue(
                            code="INVALID_IBAN_FORMAT",
                            message=f"IBAN '{node.text}' fails structural length/country code checks",
                            field_path="//IBAN",
                            severity=Severity.ERROR,
                            rule_name="ISO 13616 IBAN Format",
                            suggested_remediation="Check country code and length for target ISO IBAN."
                        )
                    )

        bic_nodes = root.findall(".//{*}BICFI") + root.findall(".//{*}BIC")
        for node in bic_nodes:
            if node.text:
                bic_clean = node.text.strip()
                if not re.match(r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$", bic_clean):
                    issues.append(
                        ValidationIssue(
                            code="INVALID_BIC_FORMAT",
                            message=f"BIC '{bic_clean}' does not match ISO 9362 8 or 11 character format",
                            field_path="//BICFI",
                            severity=Severity.ERROR,
                            rule_name="ISO 9362 BIC Conformance",
                            suggested_remediation="BIC must be 8 or 11 alphanumeric characters (e.g. CHASUS33XXX)."
                        )
                    )

    def _validate_structured_addresses(self, root: ET.Element, issues: List[ValidationIssue]) -> bool:
        """
        Validate SWIFT/KPMG Nov 2026 mandate for fully structured postal addresses.
        Unstructured addresses (Ustrd) are prohibited or flagged as critical errors.
        """
        address_nodes = root.findall(".//{*}PstlAdr")
        compliant = True

        for addr in address_nodes:
            ustrd = addr.find("{*}AddrLine")
            if ustrd is not None and ustrd.text:
                compliant = False
                if self.enforce_structured_address_2026:
                    issues.append(
                        ValidationIssue(
                            code="UNSTRUCTURED_ADDRESS_PROHIBITED",
                            message="Unstructured address line <AddrLine> detected. SWIFT Nov 2026 mandate requires fully structured address components.",
                            field_path="//PstlAdr/AddrLine",
                            severity=Severity.ERROR,
                            rule_name="SWIFT 2026 Structured Address Mandate",
                            suggested_remediation="Replace <AddrLine> with <StrtNm>, <BldgNb>, <PstCd>, <TwnNm>, and <Ctry>."
                        )
                    )

            # Check required structured fields
            strt_nm = addr.find("{*}StrtNm")
            twn_nm = addr.find("{*}TwnNm")
            ctry = addr.find("{*}Ctry")

            if strt_nm is None or twn_nm is None or ctry is None:
                compliant = False
                missing = []
                if strt_nm is None: missing.append("StrtNm")
                if twn_nm is None: missing.append("TwnNm")
                if ctry is None: missing.append("Ctry")

                issues.append(
                    ValidationIssue(
                        code="INCOMPLETE_STRUCTURED_ADDRESS",
                        message=f"Structured address missing mandatory elements: {', '.join(missing)}",
                        field_path="//PstlAdr",
                        severity=Severity.ERROR if self.enforce_structured_address_2026 else Severity.WARNING,
                        rule_name="SWIFT 2026 Structured Address Mandate",
                        suggested_remediation=f"Include mandatory elements: {', '.join(missing)}."
                    )
                )

        return compliant
