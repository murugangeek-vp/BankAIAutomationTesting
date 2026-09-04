"""
Cryptographic Immutable Audit Ledger.

Appends every AI agent decision, tool call, self-healing proposal, and compliance verdict
into a SHA-256 hash-chained immutable sequence for SOX/PCI/PSD2 auditability.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class LedgerBlock:
    """Individual block in the immutable audit chain."""
    index: int
    timestamp: float
    agent_id: str
    action_type: str  # "PLAN", "TOOL_INVOCATION", "HEAL_PROPOSAL", "CRITIC_VERDICT"
    payload: Dict[str, Any]
    previous_hash: str
    hash: str = ""

    def calculate_hash(self) -> str:
        """Compute SHA-256 digest of block contents and previous_hash."""
        block_content = {
            "index": self.index,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "payload": self.payload,
            "previous_hash": self.previous_hash
        }
        encoded = json.dumps(block_content, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class ImmutableAuditLedger:
    """
    Append-only SHA-256 hash-chained audit ledger for regulatory compliance.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.chain: List[LedgerBlock] = []
        # Create Genesis Block
        genesis = LedgerBlock(
            index=0,
            timestamp=time.time(),
            agent_id="SYSTEM",
            action_type="GENESIS",
            payload={"run_id": run_id, "baseline": "BankAI 2026 Audit Standard"},
            previous_hash="0" * 64
        )
        genesis.hash = genesis.calculate_hash()
        self.chain.append(genesis)

    def record_event(self, agent_id: str, action_type: str, payload: Dict[str, Any]) -> LedgerBlock:
        """Append a new audited decision event to the chain."""
        prev_block = self.chain[-1]
        new_block = LedgerBlock(
            index=len(self.chain),
            timestamp=time.time(),
            agent_id=agent_id,
            action_type=action_type,
            payload=payload,
            previous_hash=prev_block.hash
        )
        new_block.hash = new_block.calculate_hash()
        self.chain.append(new_block)
        return new_block

    def verify_chain_integrity(self) -> bool:
        """Verify that no block in the audit ledger has been tampered with or modified."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            if current.hash != current.calculate_hash():
                return False
            if current.previous_hash != previous.hash:
                return False

        return True

    def export_chain(self) -> List[Dict[str, Any]]:
        """Export chain as serializable dictionaries."""
        return [b.__dict__ for b in self.chain]
