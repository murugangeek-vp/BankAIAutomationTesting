"""
Structured Address Conformance Validator.

Validates postal address structures against international banking mandates
(SWIFT/KPMG Nov 2026 ISO 20022 mandate and FATF Travel Rule requirements).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AddressType(str, Enum):
    RESIDENTIAL = "ADDR"
    BUSINESS = "BIZZ"
    REGISTERED = "REGISTERED"
    POST_OFFICE_BOX = "POBX"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass
class StructuredAddress:
    """
    Standard ISO 20022 Structured Postal Address container.
    """
    street_name: Optional[str] = None
    building_number: Optional[str] = None
    building_name: Optional[str] = None
    floor: Optional[str] = None
    post_box: Optional[str] = None
    room: Optional[str] = None
    post_code: Optional[str] = None
    town_name: Optional[str] = None
    town_location_name: Optional[str] = None
    district_name: Optional[str] = None
    country_sub_division: Optional[str] = None
    country: Optional[str] = None  # ISO 3166-1 alpha-2 (e.g. US, DE, GB)
    address_lines: List[str] = field(default_factory=list)  # Unstructured lines (prohibited under Nov 2026 rules)

    @property
    def is_fully_structured(self) -> bool:
        """Returns True if mandatory structured fields exist and no unstructured lines are present."""
        has_mandatory = bool(self.street_name and self.town_name and self.country)
        has_no_unstructured = len(self.address_lines) == 0
        return has_mandatory and has_no_unstructured


@dataclass
class AddressValidationResult:
    is_valid: bool
    is_swift_2026_compliant: bool
    fatf_travel_rule_compliant: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    normalized_address: Optional[StructuredAddress] = None


class StructuredAddressValidator:
    """
    Validates physical/postal addresses against banking compliance standards:
    - SWIFT 2026 ISO 20022 structured address requirement
    - FATF Travel Rule completeness (originator/beneficiary address verification)
    - ISO 3166-1 country code validation
    """

    ISO_COUNTRY_CODES = {
        "AF", "AX", "AL", "DZ", "AS", "AD", "AO", "AI", "AQ", "AG", "AR", "AM", "AW", "AU", "AT",
        "AZ", "BS", "BH", "BD", "BB", "BY", "BE", "BZ", "BJ", "BM", "BT", "BO", "BQ", "BA", "BW",
        "BV", "BR", "IO", "BN", "BG", "BF", "BI", "CV", "KH", "CM", "CA", "KY", "CF", "TD", "CL",
        "CN", "CX", "CC", "CO", "KM", "CD", "CG", "CK", "CR", "CI", "HR", "CU", "CW", "CY", "CZ",
        "DK", "DJ", "DM", "DO", "EC", "EG", "SV", "GQ", "ER", "EE", "SZ", "ET", "FK", "FO", "FJ",
        "FI", "FR", "GF", "PF", "TF", "GA", "GM", "GE", "DE", "GH", "GI", "GR", "GL", "GD", "GP",
        "GU", "GT", "GG", "GN", "GW", "GY", "HT", "HM", "VA", "HN", "HK", "HU", "IS", "IN", "ID",
        "IR", "IQ", "IE", "IM", "IL", "IT", "JM", "JP", "JE", "JO", "KZ", "KE", "KI", "KP", "KR",
        "KW", "KG", "LA", "LV", "LB", "LS", "LR", "LY", "LI", "LT", "LU", "MO", "MG", "MW", "MY",
        "MV", "ML", "MT", "MH", "MQ", "MR", "MU", "YT", "MX", "FM", "MD", "MC", "MN", "ME", "MS",
        "MA", "MZ", "MM", "NA", "NR", "NP", "NL", "NC", "NZ", "NI", "NE", "NG", "NU", "NF", "MK",
        "MP", "NO", "OM", "PK", "PW", "PS", "PA", "PG", "PY", "PE", "PH", "PN", "PL", "PT", "PR",
        "QA", "RE", "RO", "RU", "RW", "BL", "SH", "KN", "LC", "MF", "PM", "VC", "WS", "SM", "ST",
        "SA", "SN", "RS", "SC", "SL", "SG", "SX", "SK", "SI", "SB", "SO", "ZA", "GS", "SS", "ES",
        "LK", "SD", "SR", "SJ", "SE", "CH", "SY", "TW", "TJ", "TZ", "TH", "TL", "TG", "TK", "TO",
        "TT", "TN", "TR", "TM", "TC", "TV", "UG", "UA", "AE", "GB", "US", "UM", "UY", "UZ", "VU",
        "VE", "VN", "VG", "VI", "WF", "EH", "YE", "ZM", "ZW"
    }

    def validate(self, address: StructuredAddress) -> AddressValidationResult:
        """Perform comprehensive validation on a structured address object."""
        errors: List[str] = []
        warnings: List[str] = []

        # 1. Country Code Check
        if not address.country:
            errors.append("Country code (Ctry) is mandatory.")
        elif address.country.upper() not in self.ISO_COUNTRY_CODES:
            errors.append(f"Country code '{address.country}' is not a valid ISO 3166-1 alpha-2 code.")

        # 2. Town Name Check
        if not address.town_name or not address.town_name.strip():
            errors.append("Town name (TwnNm) is mandatory.")

        # 3. Street Name / Post Box Check
        if not address.street_name and not address.post_box:
            errors.append("Either Street Name (StrtNm) or Post Box (PstBx) must be specified.")

        # 4. SWIFT Nov 2026 Mandate Check
        swift_2026_compliant = True
        if address.address_lines:
            swift_2026_compliant = False
            errors.append(
                "SWIFT 2026 Mandate Violation: Unstructured address lines (AddrLine) are prohibited. "
                "Use structured fields (StrtNm, BldgNb, PstCd, TwnNm, Ctry)."
            )

        if not address.street_name or not address.town_name or not address.country:
            swift_2026_compliant = False

        # 5. FATF Travel Rule Completeness Check
        fatf_compliant = bool(
            address.country and
            address.town_name and
            (address.street_name or address.post_box or address.building_number)
        )

        if not fatf_compliant:
            warnings.append("Address does not satisfy FATF Travel Rule full originator completeness criteria.")

        is_valid = len(errors) == 0

        return AddressValidationResult(
            is_valid=is_valid,
            is_swift_2026_compliant=swift_2026_compliant,
            fatf_travel_rule_compliant=fatf_compliant,
            errors=errors,
            warnings=warnings,
            normalized_address=address
        )

    def normalize(self, raw_lines: List[str], country_hint: str = "US") -> StructuredAddress:
        """
        Attempt to parse unstructured lines into a structured address container (best-effort normalization).
        """
        addr = StructuredAddress(country=country_hint.upper())
        if not raw_lines:
            return addr

        # Simple heuristic parser for testing data
        if len(raw_lines) >= 1:
            line1 = raw_lines[0].strip()
            match = re.match(r"^(\d+[\w-]*)\s+(.*)$", line1)
            if match:
                addr.building_number = match.group(1)
                addr.street_name = match.group(2)
            else:
                addr.street_name = line1

        if len(raw_lines) >= 2:
            line2 = raw_lines[1].strip()
            # Town, State Zip parsing
            match = re.match(r"^([^,]+),\s*([A-Z]{2})\s*(\d{5}(-\d{4})?)?$", line2)
            if match:
                addr.town_name = match.group(1)
                addr.country_sub_division = match.group(2)
                if match.group(3):
                    addr.post_code = match.group(3)
            else:
                addr.town_name = line2

        return addr
