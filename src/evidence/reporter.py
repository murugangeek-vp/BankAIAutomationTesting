"""
Compliance Report Generator.

Exports complete audit packages in JSON and PDF formats containing:
- Test execution summary & pass/fail verdicts
- Oracle Critic evaluations & compliance tags (SOX-404, PCI-DSS, SWIFT 2026)
- Self-healing locator proposals and ratification status
- Cryptographic hash-chained audit ledger verification digest
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from src.orchestrator.state import BankingTestState
from src.evidence.ledger import ImmutableAuditLedger

logger = logging.getLogger("BankAI.ComplianceReporter")


class ComplianceReportGenerator:
    """
    Generator for regulator-defensible JSON and PDF compliance reports.
    """

    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = Path(output_dir or "./reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_report(self, state: BankingTestState, ledger: ImmutableAuditLedger) -> str:
        """Generate structured JSON compliance audit package."""
        is_chain_valid = ledger.verify_chain_integrity()

        report_data = {
            "report_metadata": {
                "generator": "BankAI Enterprise Automation Framework v1.0",
                "compliance_standard": "ISO 20022 / SOX-404 / PCI-DSS / SWIFT 2026",
                "run_id": state.run_id,
                "journey": state.business_journey,
                "persona": state.persona_type,
                "status": state.status.value,
                "ledger_chain_valid": is_chain_valid,
                "ledger_block_count": len(ledger.chain),
                "critic_oracle_passed": state.oracle_checklist_passed
            },
            "execution_metrics": state.metrics,
            "compliance_findings": state.compliance_findings,
            "healed_locators": state.healed_locators,
            "pending_human_review": state.pending_human_review,
            "audit_ledger_summary": [
                {
                    "index": b.index,
                    "agent": b.agent_id,
                    "action": b.action_type,
                    "hash": b.hash
                }
                for b in ledger.chain
            ]
        }

        filepath = self.output_dir / f"compliance_report_{state.run_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        logger.info(f"Generated JSON compliance report: {filepath}")
        return str(filepath)

    def generate_pdf_summary_markdown(self, state: BankingTestState, ledger: ImmutableAuditLedger) -> str:
        """Generate formatted Markdown report suitable for conversion to executive PDF."""
        md = f"""# Enterprise Banking AI Automation Testing — Compliance Audit Report

**Run ID:** `{state.run_id}`  
**Business Journey:** `{state.business_journey}`  
**Persona Profile:** `{state.persona_type}`  
**Execution Verdict:** **`{state.status.value}`**  
**Audit Ledger Cryptographic Verification:** `{"PASSED (Tamper-Free)" if ledger.verify_chain_integrity() else "FAILED (Tampering Detected)"}`  

---

## 1. Executive Summary

The automated multi-agent test execution for journey **{state.business_journey}** finished with status **{state.status.value}**.
Oracle Critic verification against human checklist: **{"PASSED" if state.oracle_checklist_passed else "FAILED"}**.

## 2. Regulatory Compliance Findings
"""
        if state.compliance_findings:
            for finding in state.compliance_findings:
                md += f"- ⚠️ {finding}\n"
        else:
            md += "- ✅ No regulatory compliance violations detected.\n"

        md += f"""
## 3. Self-Healing Locator Proposals & Ratification
**Pending Human Approval:** `{state.pending_human_review}`  

| Step ID | Original Locator | Proposed Healed Locator |
|---|---|---|
"""
        if state.healed_locators:
            for step_id, loc in state.healed_locators.items():
                md += f"| `{step_id}` | `original` | `{loc}` |\n"
        else:
            md += "| N/A | No locator healing required | N/A |\n"

        md += f"""
## 4. Cryptographic Audit Ledger Blocks
Total Ledger Blocks: `{len(ledger.chain)}`  

| Block Index | Timestamp | Agent Role | Action Type | SHA-256 Digest |
|---|---|---|---|---|
"""
        for block in ledger.chain:
            md += f"| {block.index} | {block.timestamp:.2f} | `{block.agent_id}` | `{block.action_type}` | `{block.hash[:16]}...` |\n"

        filepath = self.output_dir / f"compliance_report_{state.run_id}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)

        return str(filepath)
