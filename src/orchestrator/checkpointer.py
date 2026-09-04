"""
LangGraph Audit State Checkpointer.

Persists state machine checkpoints to disk or database for time-travel debugging
and regulatory audit replay.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.orchestrator.state import BankingTestState

logger = logging.getLogger("BankAI.Checkpointer")


class AuditCheckpointer:
    """
    State Checkpointer saving immutable snapshots of test run states.
    """

    def __init__(self, checkpoint_dir: Optional[str] = None):
        self.checkpoint_dir = Path(checkpoint_dir or "./checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(self, state: BankingTestState, step_name: str) -> str:
        """Serialize state snapshot to JSON checkpoint file."""
        checkpoint_id = f"{state.run_id}_{step_name}_{int(state.created_at.timestamp())}"
        filepath = self.checkpoint_dir / f"{checkpoint_id}.json"

        # Prepare serializable state dictionary
        data = {
            "checkpoint_id": checkpoint_id,
            "run_id": state.run_id,
            "journey": state.business_journey,
            "status": state.status.value,
            "persona": state.persona_type,
            "step_name": step_name,
            "pending_human_review": state.pending_human_review,
            "healed_locators": state.healed_locators,
            "compliance_findings": state.compliance_findings,
            "logs": state.audit_logs
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved audit checkpoint '{checkpoint_id}' to {filepath}")
        return str(filepath)

    def list_checkpoints(self, run_id: str) -> List[str]:
        """Find all checkpoint files for a given run_id."""
        matches = list(self.checkpoint_dir.glob(f"{run_id}_*.json"))
        return [str(p) for p in matches]
