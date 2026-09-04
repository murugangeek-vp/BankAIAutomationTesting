"""
Human-in-the-Loop Review Queue & Ratification Gateway.

Manages human approval workflows for locator self-healing ratification,
compliance hold sign-offs, and critical money-movement authorization gates.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BankAI.HITLQueue")


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    ESCALATED = "ESCALATED"


@dataclass
class ReviewItem:
    """Item queued for Human-in-the-Loop review."""
    item_id: str
    run_id: str
    item_type: str  # "HEALER_RATIFICATION", "COMPLIANCE_HOLD", "CRITICAL_ACTION"
    title: str
    description: str
    confidence_score: float
    patch_diff: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    created_at: float = field(default_factory=time.time)
    reviewed_at: Optional[float] = None
    reviewer_comments: Optional[str] = None
    reviewer_id: Optional[str] = None


class HITLReviewQueue:
    """
    Central queue for managing pending human approvals and ratification logs.
    """

    def __init__(self):
        self._items: Dict[str, ReviewItem] = {}

    def enqueue_item(self, item: ReviewItem) -> ReviewItem:
        """Add item to human review queue."""
        self._items[item.item_id] = item
        logger.info(f"Queued HITL Item '{item.item_id}' [{item.item_type}] for run '{item.run_id}'")
        return item

    def list_pending_items(self) -> List[ReviewItem]:
        """List all pending items awaiting human approval."""
        return [item for item in self._items.values() if item.status == ReviewStatus.PENDING]

    def get_item(self, item_id: str) -> Optional[ReviewItem]:
        """Get review item by ID."""
        return self._items.get(item_id)

    def submit_review(
        self, item_id: str, approved: bool, reviewer_id: str, comments: Optional[str] = None
    ) -> Optional[ReviewItem]:
        """Submit human review verdict (Approve or Reject)."""
        item = self.get_item(item_id)
        if not item:
            return None

        item.status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
        item.reviewed_at = time.time()
        item.reviewer_id = reviewer_id
        item.reviewer_comments = comments

        logger.info(
            f"HITL Item '{item_id}' reviewed by '{reviewer_id}': Verdict={item.status.value}"
        )
        return item
