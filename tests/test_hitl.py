"""
Unit tests for Human-in-the-Loop (HITL) Review Queue & API controllers.
"""

import pytest
from src.hitl.review_queue import HITLReviewQueue, ReviewItem, ReviewStatus
from src.hitl.api import HITLAPIController


def test_hitl_review_queue_enqueue_and_approve():
    queue = HITLReviewQueue()
    item = ReviewItem(
        item_id="REV-001",
        run_id="RUN-100",
        item_type="HEALER_RATIFICATION",
        title="Approve button locator change",
        description="Text changed in DOM",
        confidence_score=0.88,
        patch_diff="--- old\n+++ new"
    )

    queue.enqueue_item(item)
    pending = queue.list_pending_items()
    assert len(pending) == 1
    assert pending[0].item_id == "REV-001"

    updated = queue.submit_review(item_id="REV-001", approved=True, reviewer_id="qa_lead_01", comments="Ratified locator change.")
    assert updated is not None
    assert updated.status == ReviewStatus.APPROVED
    assert len(queue.list_pending_items()) == 0


def test_hitl_api_controller():
    controller = HITLAPIController()
    summary = controller.get_dashboard_summary()
    assert summary["pass_rate_percent"] == 97.6
    assert summary["audit_ledger_status"] == "TAMPER_FREE_VERIFIED"
