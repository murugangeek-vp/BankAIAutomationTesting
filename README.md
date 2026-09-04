# Enterprise Banking AI Automation Testing Framework
### Autonomous Multi-Agent Testing with Deterministic Core & HITL Governance (2026 Baseline)

---

## Architecture Overview

This framework implements a hybrid architecture for mission-critical enterprise banking automation:
1. **Deterministic Automation Core**: Playwright (accessibility-tree first), REST/SOAP API clients, ISO 20022 message validators, and double-entry ledger reconciliation DB drivers.
2. **Multi-Agent AI System (LangGraph)**:
   - **Planner Agent**: Decomposes requirements/BRDs into multi-surface test graphs.
   - **Executor Agent**: Drives test step execution via MCP Gateway tools.
   - **Healer Agent**: Classifies failures (`LOCATOR_DRIFT` vs `REAL_BUG` vs `ENVIRONMENT_FLAKE`) and generates locator diffs with confidence scores.
   - **Critic Agent**: Oracle-guided verification matching execution against human checklists (doubling defect detection F1 per 2026 Testing Frontier benchmarks).
   - **Synthetic Data Agent**: Generates checksum-valid IBAN, PAN, ABA routing, and ISO 20022 addresses with zero PII derivation.
   - **Persona Agent**: Parameterizes step execution with behavioral user archetypes (Corporate Treasurer, Retail User, Fraud Prober, Accessibility User).
3. **MCP Tool Gateway & PII Redaction Proxy**: Intercepts all SUT data and redacts PANs, IBANs, SSNs, emails, and credentials before LLM model context ingestion.
4. **Immutable Cryptographic Audit Ledger**: Hashes every agent decision and tool call into an append-only SHA-256 chain for SOX, PCI-DSS, RBI, and SWIFT 2026 auditability.
5. **Human-in-the-Loop (HITL) Dashboard**: Web portal for ratifying self-healing proposals before code repository merge.

---

## Directory Structure

```
f:/AI/BankAIAutomationTesting/
├── .github/workflows/ci.yml       # GitHub Actions CI pipeline
├── docker-compose.yml             # Docker Compose local environment
├── Dockerfile                     # Container image definition
├── pyproject.toml                 # Project metadata & dependency spec
├── requirements.txt               # Dependencies
├── doc/
│   └── implementation_plan_v1.0.md# Technical Architecture & Strategy
├── src/
│   ├── agents/                    # Multi-Agent Implementations
│   │   ├── base_agent.py          # Abstract Agent base class with HITL hooks
│   │   ├── planner_agent.py       # Test decomposition agent
│   │   ├── executor_agent.py      # MCP tool driver agent
│   │   ├── healer_agent.py        # Failure classification & locator healing
│   │   ├── critic_agent.py        # Oracle-guided validator agent
│   │   ├── synthetic_data_agent.py# Non-reversible synthetic data generator
│   │   └── persona_agent.py       # User behavioral archetype driver
│   ├── core/                      # Configuration, logging, exception hierarchy
│   │   ├── config.py
│   │   ├── exceptions.py
│   │   └── logging_config.py
│   ├── synthetic_data/            # Banking Data Generators & Validators
│   │   ├── iban_generator.py      # ISO 13616 IBAN / ISO 9362 BIC generator
│   │   ├── pan_generator.py       # Luhn-valid synthetic card PAN generator
│   │   ├── routing_generator.py   # ABA 9-digit routing number generator
│   │   ├── persona_profiles.py    # Persona behavioral catalog
│   │   ├── transaction_generator.py # Contextual financial transactions
│   │   ├── iso20022_validator.py  # pacs.008, pacs.002, camt.053, pain.001 validator
│   │   └── address_validator.py   # SWIFT Nov 2026 structured address validator
│   ├── mcp_gateway/               # Model Context Protocol Gateway & Security
│   │   ├── pii_redaction_proxy.py # Presidio/regex PII/PCI masking proxy
│   │   ├── tool_registry.py       # Central MCP tool gateway & execution audit
│   │   ├── playwright_tool.py     # Accessibility-tree-first Playwright driver
│   │   ├── api_client_tool.py     # REST/SOAP API execution tool
│   │   ├── db_connector_tool.py   # DB double-entry ledger reconciler
│   │   └── iso20022_tool.py       # ISO 20022 validation MCP tool
│   ├── orchestrator/              # LangGraph Stateful Orchestration
│   │   ├── state.py               # Shared BankingTestState dataclass
│   │   ├── graph.py               # State machine execution graph
│   │   └── checkpointer.py        # Audit-replay time-travel checkpointer
│   ├── evidence/                  # Evidence Collection & Compliance
│   │   ├── ledger.py              # SHA-256 hash-chained immutable audit ledger
│   │   ├── collector.py           # Screencast, HAR trace, screenshot collector
│   │   ├── reporter.py            # JSON & PDF compliance report generator
│   │   └── observability.py       # OpenTelemetry & LangSmith tracing helper
│   ├── hitl/                      # Human-in-the-Loop Governance & Ratification
│   │   ├── review_queue.py        # Queue for pending locator heal approvals
│   │   └── api.py                 # REST controllers for UI dashboard
│   └── dashboard/                 # Web Dashboard
│       ├── index.html             # High-aesthetic dark mode portal
│       └── server.py              # Local HTTP dashboard server
└── tests/                         # Comprehensive Automated Test Suite
    ├── test_synthetic_data.py
    ├── test_mcp_gateway.py
    ├── test_agents_and_orchestrator.py
    ├── test_evidence_and_ledger.py
    └── test_hitl.py
```

---

## Running the Dashboard & Tests

### 1. Run Automated Test Suite
```bash
pytest tests/ -v
```

### 2. Launch Local Web Dashboard
```bash
python src/dashboard/server.py
# Access dashboard at http://localhost:8080
```

### 3. Docker Deployment
```bash
docker-compose up --build
```