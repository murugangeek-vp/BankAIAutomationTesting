"""
Persona Agent.

Injects behavioral archetype traits (Corporate Treasurer, Fraud Prober, Accessibility User)
into Executor test execution streams to simulate diverse human interactions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.agents.base_agent import BaseAgent, AgentResponse, AgentRole
from src.mcp_gateway.tool_registry import MCPToolRegistry
from src.synthetic_data.persona_profiles import PersonaCatalog, PersonaType

logger = logging.getLogger("BankAI.PersonaAgent")


class PersonaAgent(BaseAgent):
    """
    Persona Agent responsible for parameterizing Executor step actions with behavioral profile traits.
    """

    def __init__(self, agent_id: str = "persona-01", tool_registry: Optional[MCPToolRegistry] = None):
        super().__init__(
            agent_id=agent_id,
            name="Behavioral Archetype Persona Driver",
            role=AgentRole.PERSONA,
            tool_registry=tool_registry,
            token_budget=10000
        )
        self.catalog = PersonaCatalog()

    def process(self, input_data: Dict[str, Any], context: Dict[str, Any]) -> AgentResponse:
        """
        Retrieves a target persona profile and parameterizes step interactions.
        """
        persona_key = input_data.get("persona_type", "CORPORATE_TREASURER")
        step_input = input_data.get("step", {})

        try:
            p_type = PersonaType(persona_key.lower())
        except ValueError:
            p_type = PersonaType.RETAIL_FAST

        profile = self.catalog.get_persona(p_type)
        logger.info(f"[{self.agent_id}] Parameterizing step with persona '{profile.persona_name}'")

        # Inject behavioral parameters into step definition
        parameterized_step = dict(step_input)
        parameterized_step["typing_speed_wpm"] = profile.behavioral.typing_speed_wpm
        parameterized_step["think_time_ms"] = int(profile.behavioral.average_think_time_sec * 1000)
        parameterized_step["screen_reader_enabled"] = profile.behavioral.screen_reader_enabled
        parameterized_step["retry_count"] = profile.behavioral.patience_score

        return self.create_response(
            success=True,
            content=f"Step parameterized for persona '{profile.persona_name}'.",
            data={
                "persona_id": profile.persona_id,
                "persona_name": profile.persona_name,
                "archetype": profile.persona_type.value,
                "parameterized_step": parameterized_step,
                "compliance_checklist": profile.compliance_checks
            },
            tokens_used=180
        )
