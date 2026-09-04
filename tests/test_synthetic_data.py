"""
Unit tests for Synthetic Data Generators and ISO 20022 / Address Validators.
"""

import pytest
from src.synthetic_data.iban_generator import IBANGenerator
from src.synthetic_data.pan_generator import PANGenerator, CardBrand
from src.synthetic_data.routing_generator import RoutingNumberGenerator
from src.synthetic_data.iso20022_validator import ISO20022Validator, MessageType
from src.synthetic_data.address_validator import StructuredAddressValidator, StructuredAddress


def test_iban_generator_validity():
    gen = IBANGenerator()
    iban_de = gen.generate_iban(country_code="DE")
    assert iban_de.startswith("DE")
    assert len(iban_de) == 22
    assert gen.validate_iban(iban_de) is True


def test_pan_generator_luhn_check():
    gen = PANGenerator()
    pan = gen.generate_pan(brand=CardBrand.VISA)
    assert pan.pan.startswith("4999")
    assert gen.validate_luhn(pan.pan) is True
    assert pan.masked_pan.startswith("4999-99**")


def test_routing_generator_checksum():
    gen = RoutingNumberGenerator()
    rtn = gen.generate_routing_number()
    assert len(rtn) == 9
    assert gen.validate_checksum(rtn) is True


def test_iso20022_validator_pacs008():
    validator = ISO20022Validator()
    xml_sample = """<?xml version="1.0" encoding="UTF-8"?>
    <Document xmlns="urn:iso:std:iso:20022:tech:xsd:pacs.008.001.10">
        <FIToFICstmrCdtTrf>
            <GrpHdr>
                <MsgId>MSG-2026-0904-001</MsgId>
                <CreDtTm>2026-09-04T08:00:00Z</CreDtTm>
            </GrpHdr>
            <CdtTrfTxInf>
                <Amt><InstdAmt Ccy="USD">1500.00</InstdAmt></Amt>
                <Cdtr>
                    <PstlAdr>
                        <StrtNm>Wall Street</StrtNm>
                        <BldgNb>100</BldgNb>
                        <TwnNm>New York</TwnNm>
                        <Ctry>US</Ctry>
                    </PstlAdr>
                </Cdtr>
            </CdtTrfTxInf>
        </FIToFICstmrCdtTrf>
    </Document>"""

    report = validator.validate_xml_string(xml_sample)
    assert report.is_valid is True
    assert report.message_type == MessageType.PACS_008
    assert report.structured_address_compliant is True


def test_swift_2026_address_mandate_failure():
    validator = StructuredAddressValidator()
    # Unstructured address should violate SWIFT 2026 mandate
    bad_addr = StructuredAddress(
        address_lines=["100 Wall Street, New York, NY 10005"],
        country="US"
    )
    result = validator.validate(bad_addr)
    assert result.is_swift_2026_compliant is False
    assert len(result.errors) > 0
