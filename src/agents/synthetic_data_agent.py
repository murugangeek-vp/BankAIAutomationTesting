"""
Synthetic Data Agent.

Combines deterministic banking generators (IBAN, PAN, ABA Routing, ISO 20022 addresses)
with LLM-driven narrative generation for transaction descriptions, merchant names,
and customer profiles. Enforces zero production PII derivation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.agents.base_agent import BaseAgent, AgentResponse, AgentRole
from src.mcp_gateway.tool_registry import MCPToolRegistry
from src.synthetic_data.iban_generator import IBANGenerator
from src.synthetic_data.pan_generator import PANGenerator, CardBrand
from src.synthetic_data.routing_generator import RoutingNumberGenerator
from src.synthetic_data.transaction_generator import TransactionGenerator

logger = logging.getLogger("BankAI.SyntheticDataAgent")


class SyntheticDataAgent(BaseAgent):
    """
    Synthetic Data Agent producing non-reversible, compliance-safe synthetic financial datasets.
    """

    def __init__(self, agent_id: str = "synthdata-01", tool_registry: Optional[MCPToolRegistry] = None):
        super().__init__(
            role=AgentRole.SYNTHETIC_DATA,
            agent_id=agent_id,
            name="Synthetic Financial Data Generator",
            tool_registry=tool_registry,
            token_budget=10000
        )
        self.iban_gen = IBANGenerator()
        self.pan_gen = PANGenerator()
        self.routing_gen = RoutingNumberGenerator()
        self.tx_gen = TransactionGenerator()

    def get_system_prompt(self) -> str:
        return "You are the Synthetic Data Agent. Your role is to generate non-reversible, checksum-valid financial identifiers and narrative transaction data."

    def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> AgentResponse:
        """
        Generates structured synthetic datasets based on request parameters.
        """
        dataset_type = input_data.get("dataset_type", "ACCOUNT_PAIR")
        country = input_data.get("country", "DE")
        count = input_data.get("count", 1)

        logger.info(f"[{self.agent_id}] Generating synthetic dataset: {dataset_type} ({count} items)")

        if dataset_type == "ACCOUNT_PAIR":
            pairs = []
            for _ in range(count):
                source_iban = self.iban_gen.generate_iban(country_code=country)
                dest_iban = self.iban_gen.generate_iban(country_code="US" if country != "US" else "GB")
                source_bic = self.iban_gen.generate_bic(country_code=country)
                dest_bic = self.iban_gen.generate_bic(country_code="US" if country != "US" else "GB")

                pairs.append({
                    "source_iban": source_iban,
                    "source_bic": source_bic,
                    "dest_iban": dest_iban,
                    "dest_bic": dest_bic,
                    "routing_number": self.routing_gen.generate_routing_number()
                })

            return self.create_response(
                success=True,
                content=f"Generated {count} synthetic account pair(s).",
                data={"dataset_type": dataset_type, "items": pairs},
                tokens_used=150
            )

        elif dataset_type == "CARDS":
            cards = []
            for _ in range(count):
                pan = self.pan_gen.generate_pan(brand=CardBrand.VISA)
                cards.append({
                    "card_number": pan.pan,
                    "brand": pan.brand.value,
                    "bin": pan.bin_prefix,
                    "masked": pan.masked_pan,
                    "cvv": pan.cvv,
                    "expiry": pan.expiration_date
                })

            return self.create_response(
                success=True,
                content=f"Generated {count} synthetic payment card(s).",
                data={"dataset_type": dataset_type, "items": cards},
                tokens_used=120
            )

        elif dataset_type == "TRANSACTIONS":
            txs = self.tx_gen.generate_history(count=count)
            return self.create_response(
                success=True,
                content=f"Generated {count} synthetic transaction history record(s).",
                data={"dataset_type": dataset_type, "items": [t.__dict__ for t in txs]},
                tokens_used=200
            )

        else:
            return self.create_response(
                success=False,
                content=f"Unsupported synthetic dataset type '{dataset_type}'",
                error_message="Invalid dataset type"
            )
