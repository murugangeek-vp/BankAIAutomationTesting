# Enterprise Banking AI Automation Testing Framework
## System Architecture, Flow Diagrams & Deployment Guide (2026 Baseline)

---

## 1. System Architecture Diagram

```mermaid
graph TB
    subgraph CI_CD["CI/CD & Operational Triggers"]
        GHA["GitHub Actions Workflow"]
        CRON["Nightly Exploratory Trigger"]
        PR["PR Merge Gate (<10m Smoke)"]
    end

    subgraph ORCHESTRATOR["Multi-Agent Orchestration Layer (LangGraph)"]
        STATE["BankingTestState & Checkpointer"]
        PLANNER["Planner Agent (Test Graph Architect)"]
        PERSONA["Persona Agent (Behavioral Archetypes)"]
        SYNTH["Synthetic Data Agent (Non-Reversible Data)"]
        EXECUTOR["Executor Agent (Multi-Surface Driver)"]
        CRITIC["Critic Agent (Oracle Checklist Validator)"]
        HEALER["Healer Agent (Failure Classifier & Locator Fixer)"]
    end

    subgraph SECURITY["Security & Privacy Gateway"]
        PII_PROXY["PII / PCI Redaction Proxy (PAN, IBAN, SSN, Credentials)"]
        REGISTRY["MCP Tool Gateway & Execution Tracker"]
    end

    subgraph TOOLS["MCP Tools & Automation Core"]
        PLAYWRIGHT["Playwright Web/Mobile MCP (Accessibility Tree)"]
        API_CLIENT["REST / SOAP API Client Tool"]
        DB_RECON["DB Ledger Double-Entry Reconciler"]
        ISO_VALIDATOR["ISO 20022 XML & Address Validator"]
    end

    subgraph SUT["System Under Test (Non-Prod Isolation)"]
        WEB_UI["Online & Mobile Banking Portals"]
        CORE_API["Core Banking REST/SOAP Endpoints"]
        LEDGER_DB["Core Banking SQL/NoSQL Ledger DB"]
        PAYMENT_RAILS["ISO 20022 SWIFT Rails (pacs.008, pacs.002)"]
    end

    subgraph EVIDENCE["Evidence & Auditability"]
        LEDGER["Immutable SHA-256 Hash-Chained Ledger"]
        COLLECTOR["Artifact Collector (Screencasts, HAR, Logs)"]
        REPORTER["Compliance Package Generator (JSON / PDF)"]
        DASHBOARD["HITL Web Dashboard & Ratification Queue"]
    end

    GHA --> STATE
    PR --> STATE
    CRON --> STATE

    STATE --> PLANNER
    PLANNER --> PERSONA
    PERSONA --> SYNTH
    SYNTH --> EXECUTOR
    EXECUTOR --> CRITIC
    EXECUTOR -. Failure .-> HEALER

    EXECUTOR --> PII_PROXY
    PII_PROXY --> REGISTRY

    REGISTRY --> PLAYWRIGHT
    REGISTRY --> API_CLIENT
    REGISTRY --> DB_RECON
    REGISTRY --> ISO_VALIDATOR

    PLAYWRIGHT --> WEB_UI
    API_CLIENT --> CORE_API
    DB_RECON --> LEDGER_DB
    ISO_VALIDATOR --> PAYMENT_RAILS

    CRITIC --> LEDGER
    HEALER --> DASHBOARD
    LEDGER --> REPORTER
    COLLECTOR --> REPORTER
```

---

## 2. Multi-Agent Journey Execution Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as QA Engineer / CI Pipeline
    participant Orch as LangGraph Orchestrator
    participant Plan as Planner Agent
    participant Pers as Persona Agent
    participant Synth as Synthetic Data Agent
    participant Exec as Executor Agent
    participant MCP as MCP Tool Gateway (PII Proxy)
    participant Critic as Critic Agent
    participant Healer as Healer Agent
    participant HITL as HITL Ratification Dashboard
    participant Ledger as Immutable Audit Ledger

    User->>Orch: Run Journey ("Validate Cross-Border Wire Transfer")
    Orch->>Ledger: Record Event (GENESIS Block)
    Orch->>Plan: Decompose Requirement
    Plan-->>Orch: Return TestPlan (6 Steps)
    Orch->>Ledger: Record Event (PLAN_CREATED)

    Orch->>Pers: Load Persona Profile (Corporate Treasurer)
    Pers-->>Orch: Parameterize Step Timing & Retry Rules

    Orch->>Synth: Generate Financial Identifiers
    Synth-->>Orch: Return Test-Safe IBAN (DE89...), BIC, PAN, ABA Routing

    loop For Each Step in TestPlan
        Orch->>Exec: Execute Step (Web / API / DB / ISO20022)
        Exec->>MCP: Invoke Tool Call (Redact PII Pre-flight)
        MCP-->>Exec: Return Tool Result (Redact PII Post-flight)
        Exec-->>Orch: Step Execution Result
        Orch->>Ledger: Record Event (TOOL_INVOCATION)

        alt Step Failed (Locator Drift)
            Orch->>Healer: Diagnose Failure
            Healer-->>Orch: Proposal (Confidence: 88%, Classification: LOCATOR_DRIFT)
            Orch->>HITL: Enqueue Proposal for Human Ratification
            Orch->>Ledger: Record Event (HEAL_PROPOSED)
        end
    end

    Orch->>Critic: Evaluate Run vs Oracle Checklist
    Critic-->>Orch: Verdict (Passed: True, Confidence: 98%)
    Orch->>Ledger: Record Event (CRITIC_VERDICT & Final Digest)
    Orch-->>User: Execution Complete (Status: PASSED / REQUIRES_APPROVAL)
```

---

## 3. PII & PCI Security Proxy Flow Diagram

```mermaid
flowchart LR
    SUT["System Under Test Data"] --> MATCH{"Scan Regex & NER Patterns"}
    MATCH -- PAN Card Number --> MASK1["Mask with [REDACTED_PAN_n]"]
    MATCH -- IBAN Account --> MASK2["Mask with [REDACTED_IBAN_n]"]
    MATCH -- SSN / Tax ID --> MASK3["Mask with [REDACTED_SSN_n]"]
    MATCH -- Email / Phone --> MASK4["Mask with [REDACTED_EMAIL_n]"]
    MATCH -- Bearer / API Keys --> MASK5["Mask with [REDACTED_AUTH_TOKEN_n]"]
    
    MASK1 --> CLEAN["Cleaned Context Container"]
    MASK2 --> CLEAN
    MASK3 --> CLEAN
    MASK4 --> CLEAN
    MASK5 --> CLEAN

    CLEAN --> LLM["LLM Agent Context (Zero Production PII Ingestion)"]
```

---

## 4. Step-by-Step Execution Guide

### Option A: Command Line Interface (CLI)
Run the automated multi-agent suite directly using Pytest:

```bash
# 1. Activate your virtual environment and install dependencies
pip install -r requirements.txt

# 2. Run all tests with verbose output
python -m pytest tests/ -v

# 3. Run a specific test module
python -m pytest tests/test_agents_and_orchestrator.py -v
```

### Option B: Interactive Python API
You can run an end-to-end multi-agent test journey programmatically:

```python
from src.orchestrator.graph import BankingTestOrchestratorGraph
from src.evidence.ledger import ImmutableAuditLedger
from src.evidence.reporter import ComplianceReportGenerator

# Initialize Orchestrator Graph
orchestrator = BankingTestOrchestratorGraph()

# Trigger Multi-Agent Journey Execution
state = orchestrator.run_journey(
    requirement="Validate SWIFT pacs.008 wire transfer with structured address",
    journey_type="CROSS_BORDER_PAYMENT",
    persona_type="corporate_treasurer"
)

print(f"Run ID: {state.run_id}")
print(f"Execution Status: {state.status.value}")
print(f"Oracle Checklist Passed: {state.oracle_checklist_passed}")

# Export Audit Package
ledger = ImmutableAuditLedger(run_id=state.run_id)
reporter = ComplianceReportGenerator()
json_report_path = reporter.generate_json_report(state, ledger)
print(f"Audit Package Generated: {json_report_path}")
```

### Option C: Web Dashboard Portal
To launch the interactive Web Dashboard:

```bash
# Start local HTTP server
python src/dashboard/server.py
```
- Navigate to `http://localhost:8080` in your web browser.
- **Features**:
  - View real-time executive pass rate and SWIFT 2026 conformance metrics.
  - Review and ratify pending self-healing locator diffs in the **HITL Ratification Queue**.
  - Trigger new interactive multi-agent test runs across custom persona profiles.
  - Inspect the **Immutable Cryptographic Audit Ledger** SHA-256 block chain.

---

## 5. Deployment Guide

### Environment Prerequisites
- **Python**: 3.11 or higher
- **Docker**: 24.0+ & Docker Compose v2.20+
- **Playwright**: Chromium browser binaries (`python -m playwright install --with-deps chromium`)

### Local Docker Deployment
Run the complete containerized stack using Docker Compose:

```bash
# 1. Build and start services
docker-compose up --build -d

# 2. Check running container status
docker-compose ps

# 3. Stream server logs
docker-compose logs -f bankai-orchestrator
```

### CI/CD Deployment (GitHub Actions)
The repository includes an enterprise-grade GitHub Actions pipeline at `.github/workflows/ci.yml`:
- **PR Merge Gate**: Runs the deterministic smoke suite in `< 10 minutes` to block broken code merges.
- **Nightly Suite**: Triggers exploratory bug-hunting agents and full ISO 20022 conformance sweeps at 02:00 UTC.

---

## 6. Audit & Regulatory Compliance Summary

| Regulation / Standard | Framework Control Implementation |
|---|---|
| **SOX 404 & Internal Audit** | Every AI decision and tool call is recorded in an immutable append-only SHA-256 hash-chained ledger (`src/evidence/ledger.py`). |
| **PCI-DSS 4.0** | Non-reversible test BIN ranges (`400099`, `510000`, `999900`) combined with pre-flight PII proxy redaction prevent credit card data leakage. |
| **SWIFT & KPMG Nov 2026 Mandate** | Dedicated structured address conformance suite (`src/synthetic_data/address_validator.py`) enforces structured postal elements (`StrtNm`, `BldgNb`, `TwnNm`, `Ctry`). |
| **PSD2 / Strong Customer Auth (SCA)** | Persona-based simulation of 2FA tokens and session timeouts (`src/synthetic_data/persona_profiles.py`). |
