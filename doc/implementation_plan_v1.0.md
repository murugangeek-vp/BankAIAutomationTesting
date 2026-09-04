# Enterprise Banking Automation & Multi-Agent AI Testing Framework
### Architecture & Implementation Plan — 2026 Technology Baseline

---

## Executive Summary

This is a **hybrid framework**, not a pure "AI replaces QA" system: a deterministic Playwright/API/DB automation core (source of truth, auditable, regulator-defensible) wrapped by a **multi-agent AI layer** that handles test generation, self-healing, exploratory bug-hunting, synthetic data, and failure triage. That framing matters for banking specifically — 2026 field data (Angelov/Kong "Testing Frontier" benchmarks) shows even frontier models top out around **26–49% F1 for autonomous defect detection** even with Claude Sonnet 4.5/GPT-5.1-class models, and only reach the top end *when given a human-written test oracle/checklist*. So: **agents accelerate and augment; deterministic assertions still own pass/fail for regulatory evidence.** Anything else is a false sense of coverage in an audited environment.

Core approach: **Planner → Executor → Healer → Critic** agent pattern (2026's dominant pattern per Playwright's own official agent roles) sitting on top of a standard test pyramid (UI via Playwright, API/ISO 20022 message validation, DB/ledger reconciliation), orchestrated via **LangGraph** (chosen over CrewAI/AutoGen for this use case — see ADRs), with **MCP** as the tool-integration backbone and **Claude Agent SDK / Playwright MCP + Playwright CLI** as the browser-control layer.

---

## 1. Requirements Analysis

### Functional Requirements
- E2E web + mobile testing across online/mobile banking portals (retail, corporate/treasury)
- API & core banking validation: REST, SOAP, **ISO 20022** (pacs.008, pacs.002, camt.053/054, pain.001) message-level validation
- Cross-border payment rail testing (SWIFT gpi, real-time rails, correspondent banking hops)
- DB/ledger integrity checks (double-entry consistency, idempotency of postings, reconciliation)
- Autonomous exploratory testing for unmapped edge cases
- Synthetic financial data generation (IBAN/BIC, routing numbers, synthetic PANs, credit profiles) — **must be non-reversible, not derived from production PII**
- Persona-based journey simulation (retail user, corporate treasurer, fraud actor, elder/accessibility persona)
- Self-healing locators with human-reviewable diffs (no silent healing in regulated flows)

### Non-Functional Requirements (banking-specific weighting)
| NFR | Target | Why it's non-negotiable here |
|---|---|---|
| **Auditability** | Every test run + every AI decision must produce an immutable, timestamped evidence trail | SOX/PCI-DSS/RBI/PSD2 audits require reconstructable evidence |
| **PII/PCI zero-leak** | 100% masking of production-derived data in test envs; synthetic-only data by default | Regulatory + PCI-DSS scope reduction |
| **Determinism of verdicts** | AI never sets final pass/fail on compliance-critical assertions | Model F1 ceiling (~30-49%) is not audit-grade on its own |
| **Explainability** | Every AI-proposed heal/finding must include a machine-generated rationale mapped to evidence | Required for change-control sign-off |
| **Latency/throughput** | Full regression < 90 min on merge-to-main; smoke < 10 min | CI/CD velocity for core banking releases |
| **Reliability** | <2% flake rate on core suite | Flaky tests erode trust faster in banking QA orgs than anywhere else |
| **DR / RTO-RPO** | Test infra RTO < 4h (non-prod, so lower tier than prod, but CI can't be a SPOF for releases) | |
| **Cost control** | Hard token budget per PR/run; agents fall back to deterministic scripts on budget exhaustion | LLM-in-the-loop testing costs compound fast at bank release cadence |

---

## 2. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        CI/CD TRIGGER (GitHub Actions)                    │
│              PR merge · nightly regression · release gate                │
└───────────────────────────────┬────────────────────────────────────────-┘
                                 │
                 ┌───────────────▼────────────────┐
                 │   ORCHESTRATION LAYER (LangGraph)│
                 │   Stateful graph + checkpointing │
                 └───────────────┬────────────────┘
                                 │
     ┌────────────┬─────────────┼─────────────┬───────────────┐
     ▼             ▼             ▼             ▼               ▼
┌─────────┐  ┌───────────┐ ┌───────────┐ ┌───────────┐  ┌─────────────┐
│ Planner │  │  Executor │ │  Healer   │ │  Critic/  │  │ Synthetic   │
│  Agent  │  │  Agent(s) │ │  Agent    │ │ Validator │  │ Data Agent  │
│(decomp) │  │(Playwright│ │(locator/  │ │(oracle-   │  │(IBAN/BIC/   │
│         │  │ MCP/CLI,  │ │assert     │ │checklist  │  │ synth PAN/  │
│         │  │ REST, ISO │ │repair,    │ │matching,  │  │ persona     │
│         │  │ 20022,    │ │diff-based)│ │not final  │  │ profiles)   │
│         │  │ DB checks)│ │           │ │verdict)   │  │             │
└────┬────┘  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘  └──────┬──────┘
     │             │             │             │               │
     └─────────────┴──────┬──────┴─────────────┴───────────────┘
                           ▼
              ┌────────────────────────┐
              │   MCP TOOL GATEWAY      │
              │ Playwright MCP/CLI ·    │
              │ REST/SOAP clients ·     │
              │ ISO20022 validator ·    │
              │ DB connectors (SQL/NoSQL)│
              │ Secrets Manager · PII   │
              │ redaction proxy         │
              └────────────┬───────────┘
                            │
        ┌───────────────────┼────────────────────┐
        ▼                   ▼                     ▼
 ┌─────────────┐    ┌───────────────┐     ┌───────────────┐
 │ System Under │    │ Core Banking  │     │ Payment Rails │
 │ Test (Web/   │    │ APIs (REST/   │     │ (ISO 20022 /  │
 │ Mobile UI)   │    │ SOAP/gRPC)    │     │ SWIFT / RTP)  │
 └─────────────┘    └───────────────┘     └───────────────┘
                            │
              ┌─────────────▼─────────────┐
              │  EVIDENCE & OBSERVABILITY  │
              │ Immutable run ledger ·     │
              │ LangSmith/AI trace ·       │
              │ OpenTelemetry ·            │
              │ Screencast video capture · │
              │ Audit export (PDF/JSON)    │
              └────────────────────────────┘
```

### Component List
1. **Orchestration Layer** — LangGraph state machine; each node = one agent role; checkpointed for time-travel debugging and audit replay.
2. **Planner Agent** — decomposes a business journey ("cross-border payment with FX conversion and compliance hold") into a test plan graph; consumes requirements/Jira/BRD via RAG.
3. **Executor Agent(s)** — one pool per surface: Web (Playwright), Mobile (Appium/Playwright mobile), API (RestAssured/Requests + ISO 20022 schema validator), DB (SQL/NoSQL reconciliation checks). Deterministic scripts are the default execution path; the agent's job is to *drive* and *assemble* them, not freehand-improvise assertions on money-moving steps.
4. **Healer Agent** — triggered only on locator/DOM-level failures (never on assertion/business-logic failures); proposes a diff-based fix; **never auto-merges** — opens a PR with confidence score and evidence.
5. **Critic/Validator Agent** — given a human-authored checklist/oracle (this is the single highest-leverage finding from 2026 benchmark research — oracle-guided agents nearly double F1), validates Executor output against expected outcomes; flags but does not adjudicate compliance-critical checks.
6. **Synthetic Data Agent** — generates IBAN/BIC/routing numbers/synthetic PANs (Luhn-valid, non-existent BIN ranges), persona-consistent transaction histories; never samples/derives from production data.
7. **Persona Agents** — parameterize the Executor with behavioral archetypes (corporate treasurer doing bulk payments, retail user, fraud actor probing velocity limits, accessibility persona using screen reader flows).
8. **MCP Tool Gateway** — single integration point exposing Playwright (MCP + new 2026 token-efficient CLI mode), REST/SOAP clients, ISO 20022 message validators, DB connectors, and a **PII redaction proxy** all agents must pass through before results reach the LLM context.
9. **Evidence & Observability** — immutable, append-only run ledger (who/what/when/why for every AI decision) + OpenTelemetry traces + LangSmith/Arize for LLM-specific observability (token spend, hallucination flags, prompt versions) + Playwright Screencast (2026 feature) for human-reviewable video with action annotations.

---

## 3. Detailed Design

### 3.1 Automation Core (deterministic layer)
- **Web/Mobile**: Playwright (TS) as primary; use accessibility-tree-first locators (`getByRole`, `getByLabel`) as default — this is what makes self-healing tractable in 2026's agentic tooling, since agents reason over the accessibility tree, not CSS/XPath.
- **Mobile**: Playwright's mobile emulation for responsive web; Appium for native iOM/Android banking apps where WebView isn't sufficient.
- **API/Core Banking**: RestAssured (Java) or Python `requests`/`httpx` for REST; SOAP via `zeep`; **ISO 20022 validation** via schema-based validators (XSD + business rule layer) checking pacs.008/pacs.002 (credit transfer), camt.053/054 (statements), pain.001 (customer credit transfer initiation) — critically important given the **November 2026 KPMG/SWIFT deadline** for fully structured address data; build a dedicated structured-address conformance test suite now, not later.
- **DB/Ledger**: Automated double-entry verification (every debit has a matching credit, balances reconcile post-batch), idempotency-key replay tests (submit same payment twice, assert single posting), and eventual-consistency window assertions for async ledger updates.

### 3.2 Multi-Agent AI Layer
- **Orchestrator: LangGraph.** Chosen for this domain because (a) built-in checkpointing gives you audit-replay "time travel" for free — you can reconstruct exactly what an agent saw and decided at any point in a failed run, which is what a bank's internal audit function will ask for; (b) explicit graph edges make token cost and execution path predictable — important for cost governance in a regulated cost center; (c) framework-agnostic model support so you're not locked to one LLM vendor for a system that will need vendor risk review.
- **Tool protocol: MCP.** All agent-to-tool calls (Playwright, DB, REST/SOAP clients, secrets manager) go through MCP so tool access is auditable, swappable, and sandboxable — critical for a system with agents that can technically reach production-adjacent systems.
- **Model routing**: use a smaller/cheaper model for high-volume, low-risk tasks (locator healing suggestions, log summarization) and a frontier reasoning model for the Planner/Critic roles making testing-strategy decisions. Route through an LLM gateway (cost tracking, PII redaction pre-flight, fallback).
- **Self-healing governance** (directly reflecting 2026 field practice, e.g. Awesome Testing's "diagnose-before-repair" pattern):
  1. Failure occurs → Healer Agent classifies: *locator drift* vs *real regression* vs *environment flake*.
  2. Only locator-drift failures are eligible for auto-heal.
  3. Healer proposes a diff + confidence score; below a threshold, it queues for human review instead of auto-applying.
  4. Every heal is logged with before/after locator, screenshot diff, and confidence — and **healed locators must be "ratified"** (promoted from provisional to permanent) by a human before they harden into the suite, preventing the AI from quietly papering over a real bug turn after turn.
- **Exploratory "bug hunter" agents**: given a sandboxed non-prod environment + a persona + a goal ("find where the fee calculation disagrees with the disclosed schedule"), run perceive→plan→act→reflect loops (2026's dominant agentic-testing loop) and file findings as *candidate defects*, always evidence-attached (screenshot, network trace, replayable script) — a human triages, the agent never auto-files a Jira ticket as confirmed.

### 3.3 Synthetic Data Generation
- Deterministic generators for IBAN/BIC/routing numbers (checksum-valid, using test-only bank identifier ranges — never real BIN/routing prefixes) as the default, foundational layer.
- LLM-assisted **only** for generating *contextually coherent* surrounding data (transaction narratives, customer profiles, dispute descriptions) layered on top of the deterministic core — keeps compliance-sensitive identifiers deterministic and auditable while getting AI's strength in producing realistic variety.
- Hard gate: a data-classification pre-check blocks any generation prompt or agent context that includes real customer identifiers — enforced at the MCP gateway, not just by policy.

### 3.4 Security, Compliance, PII
- **PII Redaction Proxy** at the MCP gateway: all data passing between the System Under Test and any LLM call is masked (Presidio-style NER + regex for PAN/IBAN/SSN patterns) *before* it reaches model context — this addresses the exact risk 2026 Playwright-MCP guidance flags ("everything Claude sees gets sent to the API — stick to test data").
- Non-prod-only agent scope. Agents are never given credentials or network paths to production; enforced via network policy, not just IAM.
- Immutable audit ledger: every agent decision (tool call, healed locator, flagged finding) is written to an append-only store (e.g., hash-chained log or object storage with object-lock) — this is your evidence artifact for SOX/PCI/RBI/PSD2 auditors.
- Secrets: HashiCorp Vault or cloud-native Secrets Manager; agents pull short-lived scoped tokens per test run, never long-lived creds.

---

## 4. Architectural Decisions & Tradeoffs (ADRs)

**ADR-1: LangGraph over CrewAI/AutoGen for orchestration**
- *Decision*: LangGraph as the primary orchestrator.
- *Rationale*: Built-in checkpointing (audit replay), predictable/explicit execution graph (cost + compliance predictability), model-agnostic.
- *Tradeoff*: Steeper learning curve and more verbose setup than CrewAI's role-based DSL.
- *Alternatives considered*: CrewAI (fastest to prototype, weaker state/audit story — good for the initial POC/spike, not for the audited production system); AutoGen/Microsoft Agent Framework (strong if already all-in on Azure; conversational GroupChat pattern less deterministic/predictable for cost and compliance than a graph).

**ADR-2: Deterministic assertions own pass/fail; AI is advisory on compliance-critical paths**
- *Decision*: AI agents can propose findings, heal locators, and generate tests, but final pass/fail on money-movement and compliance assertions is always a deterministic check written by engineers.
- *Rationale*: 2026 benchmark data (Testing Frontier: 26-49% F1 for autonomous defect detection, doubling only with a human oracle) means unsupervised AI verdicts are not audit-grade yet.
- *Tradeoff*: Slower to "full autonomy" marketing story; more human test-design work upfront (writing the oracle/checklist the Critic agent validates against) — but this is also exactly the lever that gets you from ~26% to ~49% effectiveness, so it's a net win, not just a compliance tax.

**ADR-3: Accessibility-tree-first locators, not CSS/XPath**
- *Decision*: `getByRole`/`getByLabel`-style semantic locators as the default authoring pattern.
- *Rationale*: This is what makes both human maintenance *and* AI self-healing tractable — agents in 2026 reason over the accessibility tree, so tests written this way are healable; CSS/XPath-heavy suites are not.
- *Tradeoff*: Requires the banking UI itself to have decent accessibility semantics; may require collaboration with frontend teams (a good forcing function for WCAG compliance anyway).

**ADR-4: Playwright over Selenium/Cypress as primary web driver**
- *Decision*: Playwright primary; Selenium retained only for legacy suites mid-migration.
- *Rationale*: Native auto-wait, multi-tab/multi-context support (needed for multi-party payment flows), first-class MCP/CLI agentic tooling in 2026, and built-in Screencast for audit-friendly video evidence.
- *Tradeoff*: Selenium has broader legacy grid/enterprise tooling if the bank has existing Selenium Grid infra sunk cost.

**ADR-5: Deterministic-first synthetic data, LLM-augmented context only**
- *Decision*: IBAN/BIC/PAN/routing numbers generated deterministically (checksum-valid, test-range only); LLM only elaborates narrative/context fields.
- *Rationale*: Auditable, reproducible, zero risk of an LLM hallucinating a real/valid production-adjacent identifier.
- *Tradeoff*: Slightly less "creative" edge-case coverage than a pure-LLM approach, but far safer for compliance sign-off.

---

## 5. Security Architecture (Threat Model)

| Threat | Control |
|---|---|
| Prompt injection via malicious page content (e.g., a compromised test env page instructs the agent to exfiltrate data) | Sandboxed agent tool permissions via MCP; output-side allowlisting; treat all page content as untrusted input, never as instructions |
| PII/PCI data leaking into LLM provider logs | PII redaction proxy at gateway; non-prod-only data; contractual zero-retention terms with LLM provider where available |
| Agent auto-healing masking a real regression | Heal/no-heal classifier + human ratification gate before a heal becomes permanent |
| Credential sprawl (agents need broad tool access) | Short-lived scoped tokens per run via Vault/Secrets Manager; least-privilege MCP tool grants per agent role |
| Model/vendor lock-in or availability risk | Model-agnostic orchestration (LangGraph) + LLM gateway with fallback routing |
| Adversarial/fraud-persona agent misuse outside sandbox | Network-isolated non-prod environment; agents have zero network path to production, enforced at VPC/subnet level, not app config |
| Supply-chain risk in AI testing SDKs/MCP servers | Pin MCP server versions; internal review before adding third-party MCP servers (e.g., community Playwright MCP forks) to the trusted tool list |

---

## 6. Observability & Operations

- **Test observability**: OpenTelemetry traces across Executor→SUT calls; Prometheus/Grafana dashboards for pass rate, flake rate, heal rate, mean-time-to-green.
- **AI observability**: LangSmith or Arize for prompt/response logging, token spend per run, hallucination/groundedness flags, per-agent latency P99.
- **Evidence exports**: one-click audit package per release (test results + AI decision log + Screencast videos + ISO 20022 conformance report) exportable as PDF/JSON for regulator or internal audit requests.
- **Alerting**: flake-rate threshold breach, heal-queue backlog, token-budget overrun, and any Critic-agent flag on a compliance-tagged test all page the QA on-call.
- **Runbook**: documented escalation path when Healer confidence is low or when an exploratory agent files a high-severity candidate defect on a payment-rail flow — routes to a human SME within a defined SLA, not just a ticket queue.

---

## 7. CI/CD & Deployment Strategy

```
PR opened → Smoke suite (deterministic, <10 min, blocks merge)
Merge to main → Full regression (deterministic + Critic-validated agent suite, <90 min)
Nightly → Exploratory bug-hunter agents + full ISO 20022 conformance sweep
Pre-release gate → Full regression + manual sign-off on any open Healer PRs/candidate defects
```
- GitHub Actions as CI orchestrator; Docker containers per agent role (Planner/Executor/Healer/Critic each independently scalable/replaceable).
- Environment promotion: ephemeral test environments per PR (containerized SUT + synthetic data seed) to avoid state bleed between agent-driven exploratory runs.
- Healer output = PR, never direct commit; requires human review + green CI on the healed branch before merge.
- Canary the agent layer itself: roll out new agent-model versions or prompt changes to a subset of nightly runs before promoting to the PR-blocking smoke suite — treat prompt/model changes with the same rigor as code changes (versioned, reviewed, rollback-able).

---

## 8. Scaling Strategy

- Executor agents are horizontally scalable, stateless workers (parallel test execution via Playwright's built-in sharding) — scale by browser/API worker pool size, not by agent count.
- Orchestrator (LangGraph) checkpoints to a shared store (Redis/Postgres) so orchestration state survives worker restarts and enables resuming long exploratory runs.
- Token/cost budget enforced per-run at the LLM gateway; when a run exceeds budget, it falls back to deterministic-only execution rather than failing outright — graceful degradation, not a hard stop on release velocity.
- Isolate the exploratory "bug hunter" agents to a lower-priority, lower-frequency lane (nightly, not PR-blocking) so agentic non-determinism never gates release velocity — only the deterministic smoke/regression suites are release-blocking.

---

## 9. Risks, Bottlenecks & Mitigations

| Risk | Mitigation |
|---|---|
| Over-trusting agent-generated "no defect found" results (documented 2026 bias toward predicting no-defect) | Never treat agent silence as a pass; always pair exploratory agents with deterministic assertion coverage for known-critical paths |
| Autonomous defect-detection F1 ceiling (~26-49%) creates false confidence | Always supply a human-authored oracle/checklist to the Critic agent for compliance-critical flows; track and report Critic F1 against known-seeded defects quarterly to keep expectations calibrated |
| Silent self-healing hides real regressions | Human ratification gate; heal/no-heal classifier; log every heal with confidence + diff |
| PII leakage to LLM providers | Redaction proxy at MCP gateway is a hard architectural gate, not a policy request |
| ISO 20022 structured-address deadline (Nov 2026) missed | Stand up a dedicated structured-address conformance suite now; track against the 44%-of-banks-behind-schedule industry baseline as a forcing function |
| Token cost runaway from exploratory agents | Per-run budget caps + graceful fallback to deterministic execution |
| Vendor/model lock-in | Model-agnostic orchestration layer; LLM gateway abstraction |
| Team skill gap (QA engineers need to become "agent supervisors," per 2026 industry shift) | Invest in training QA engineers on prompt/oracle authoring and agent-output triage, not just script authoring |

---

## 10. Technology Stack Summary (2026 baseline)

| Layer | Technology | Notes |
|---|---|---|
| Web/mobile automation | **Playwright** (TS), Appium for native mobile | Accessibility-tree-first locators |
| Agentic browser control | **Playwright MCP** (exploratory/self-QA) + **Playwright CLI** (agentic, ~4x more token-efficient, CI-friendly) | New 2026 split — MCP for interactive/exploratory, CLI for high-volume agentic runs |
| API testing | RestAssured / Python `httpx` / `requests`, `zeep` for SOAP | |
| ISO 20022 validation | XSD schema validation + custom business-rule layer for pacs.008/pacs.002/camt.053/pain.001 | Structured-address conformance suite is a 2026 priority |
| Multi-agent orchestration | **LangGraph** (primary) — checkpointing, graph-based control | CrewAI acceptable for rapid POC/spike phase only |
| Agent roles | Planner / Executor / Healer / Critic (Playwright's own official 2026 agent pattern) + Synthetic Data + Persona agents | |
| Tool integration | **MCP** (Model Context Protocol) as the universal, auditable tool-access layer | |
| LLM(s) | Frontier reasoning model for Planner/Critic; smaller/cheaper model for high-volume healing/summarization tasks | Route via LLM gateway for cost + fallback control |
| AI observability | LangSmith or Arize; OpenTelemetry for infra tracing | |
| CI/CD | GitHub Actions, Docker | Ephemeral per-PR environments |
| Secrets | HashiCorp Vault / cloud Secrets Manager | Short-lived scoped tokens |
| PII protection | Redaction proxy (NER + regex) at the MCP gateway | Hard architectural gate |
| Evidence/audit | Immutable append-only run ledger, Playwright Screencast, exportable audit packages | Purpose-built for SOX/PCI/RBI/PSD2 |

---

## 11. Cost Optimization Notes

- Route the bulk of high-volume, low-stakes calls (locator healing suggestions, log summarization) to a cheaper/smaller model; reserve frontier-model spend for Planner/Critic reasoning steps.
- Use Playwright **CLI** (disk-based results) over MCP (streamed accessibility trees) for high-volume CI agentic runs — ~4x token reduction per the 2026 tooling shift; reserve MCP for interactive/exploratory sessions.
- Cap exploratory agent runs to nightly cadence, not every PR — this is where most uncontrolled token spend originates.
- Per-run token budgets with graceful fallback to deterministic-only execution prevent a single misbehaving agent loop from blowing the CI cost budget.
- Track cost-per-defect-found for agentic exploratory testing against cost-per-defect-found for traditional manual exploratory testing quarterly — kill or re-scope the agent lane if it's not beating that baseline.

---

## 12. Future Considerations

- As agent defect-detection F1 improves industry-wide (track the Testing Frontier benchmark trend), progressively expand the set of assertions the Critic agent can adjudicate — but keep the human-oracle-required gate for anything touching money movement or compliance until F1 is demonstrably audit-grade, not just "better than last quarter."
- Evaluate Microsoft Agent Framework (AutoGen's unified successor) if the bank's broader platform consolidates on Azure — cross-runtime interop via A2A/MCP means this migration path stays open without a rewrite.
- Extend persona-based testing to cover the specific fraud typologies your compliance/AML team is currently most concerned about — this is a natural fit for the Persona Agent pattern and gives Compliance a reason to co-invest in the framework.
- As the November 2026 ISO 20022 structured-address deadline passes, fold the conformance suite into standing regression rather than a special nightly sweep.

---

*This plan intentionally keeps AI agents in an advisory/accelerant role over compliance-critical verdicts, given the current (2026) autonomous-defect-detection benchmark ceiling. That's a starting posture, not a permanent one — revisit ADR-2 on a quarterly cadence as the field moves.*