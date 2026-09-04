"""
Evidence Artifact Collector.

Collects Playwright Screencast recordings, network HAR files, accessibility tree dumps,
and console logs for audit package archiving.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("BankAI.EvidenceCollector")


@dataclass
class EvidencePackage:
    """Artifact collection bundle for a completed test run."""
    run_id: str
    screencast_video_path: Optional[str] = None
    har_network_trace_path: Optional[str] = None
    accessibility_tree_path: Optional[str] = None
    console_logs_path: Optional[str] = None
    audit_ledger_path: Optional[str] = None
    screenshots: List[str] = field(default_factory=list)


class EvidenceCollector:
    """
    Manager for persisting and packaging raw execution evidence artifacts.
    """

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or "./evidence_store")
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def prepare_run_directory(self, run_id: str) -> Path:
        """Create structured subdirectory for run artifacts."""
        run_dir = self.storage_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "screenshots").mkdir(exist_ok=True)
        return run_dir

    def record_screencast(self, run_id: str, video_bytes: bytes) -> str:
        """Save Playwright Screencast video file."""
        run_dir = self.prepare_run_directory(run_id)
        filepath = run_dir / "screencast.webm"
        with open(filepath, "wb") as f:
            f.write(video_bytes)
        logger.info(f"Saved screencast video to {filepath}")
        return str(filepath)

    def attach_screenshot(self, run_id: str, step_id: str, image_bytes: bytes) -> str:
        """Save screenshot image artifact."""
        run_dir = self.prepare_run_directory(run_id)
        filepath = run_dir / "screenshots" / f"{step_id}.png"
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        return str(filepath)
