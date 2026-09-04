"""
OpenTelemetry & LangSmith Observability Integration.

Configures distributed tracing across Multi-Agent execution steps, MCP gateway calls,
and LLM token spend monitoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("BankAI.Observability")


class ObservabilityTracer:
    """
    OpenTelemetry & LangSmith tracing helper for Multi-Agent AI runs.
    """

    def __init__(self, service_name: str = "BankAI-Orchestrator"):
        self.service_name = service_name
        self.active_spans: Dict[str, Any] = {}

    def start_agent_span(self, agent_id: str, span_name: str) -> str:
        """Start a named agent execution trace span."""
        span_id = f"span_{agent_id}_{span_name}"
        self.active_spans[span_id] = {"name": span_name, "agent": agent_id, "status": "RUNNING"}
        logger.info(f"[OTel Trace] Started span '{span_name}' for agent '{agent_id}'")
        return span_id

    def end_agent_span(self, span_id: str, success: bool = True, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Close an active agent trace span with metrics."""
        if span_id in self.active_spans:
            self.active_spans[span_id]["status"] = "SUCCESS" if success else "FAILED"
            if attributes:
                self.active_spans[span_id].update(attributes)
            logger.info(f"[OTel Trace] Closed span '{span_id}' (Success: {success})")
