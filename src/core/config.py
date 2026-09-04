"""
Global configuration management for the Banking AI Testing Framework.

Provides a centralized, type-safe configuration system using Pydantic Settings.
Supports environment variables, .env files, and YAML config overrides.
All settings relevant to agents, LLM routing, MCP gateway, PII redaction,
and observability are managed here.
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Optional

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentRole(str, Enum):
    """Agent roles in the multi-agent architecture."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    HEALER = "healer"
    CRITIC = "critic"
    SYNTHETIC_DATA = "synthetic_data"
    PERSONA = "persona"


class ModelTier(str, Enum):
    """LLM routing tiers — frontier for reasoning, economy for bulk tasks."""
    FRONTIER = "frontier"
    ECONOMY = "economy"


class EnvironmentType(str, Enum):
    """Deployment environments — agents NEVER connect to production."""
    DEV = "dev"
    STAGING = "staging"
    CI = "ci"
    # NOTE: No PRODUCTION value — by architectural design (ADR-2, Section 3.4).


# ---------------------------------------------------------------------------
# Sub-configurations
# ---------------------------------------------------------------------------

class LLMConfig(BaseSettings):
    """LLM provider and routing configuration."""
    model_config = SettingsConfigDict(env_prefix="LLM_")

    frontier_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Frontier reasoning model for Planner/Critic roles."
    )
    economy_model: str = Field(
        default="claude-haiku-4-20250414",
        description="Smaller/cheaper model for high-volume healing/summarization."
    )
    max_tokens_per_run: int = Field(
        default=500_000,
        description="Hard token budget per CI run. Agents fall back to deterministic on exhaustion."
    )
    temperature_frontier: float = Field(default=0.1, ge=0.0, le=1.0)
    temperature_economy: float = Field(default=0.0, ge=0.0, le=1.0)
    api_key_env_var: str = Field(
        default="ANTHROPIC_API_KEY",
        description="Environment variable name holding the LLM API key."
    )
    request_timeout_seconds: int = Field(default=120)
    max_retries: int = Field(default=3)


class MCPConfig(BaseSettings):
    """MCP Tool Gateway configuration."""
    model_config = SettingsConfigDict(env_prefix="MCP_")

    playwright_server_cmd: str = Field(
        default="npx @playwright/mcp@latest",
        description="Command to start the Playwright MCP server."
    )
    transport: str = Field(
        default="stdio",
        description="MCP transport: stdio | sse | streamable-http"
    )
    tool_timeout_seconds: int = Field(default=60)
    max_concurrent_tools: int = Field(default=10)


class PIIConfig(BaseSettings):
    """PII redaction proxy settings — hard architectural gate (Section 3.4)."""
    model_config = SettingsConfigDict(env_prefix="PII_")

    enabled: bool = Field(
        default=True,
        description="PII redaction MUST be enabled. Disabling requires explicit security review."
    )
    spacy_model: str = Field(default="en_core_web_lg")
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0, le=1.0,
        description="Minimum confidence for a PII detection to trigger redaction."
    )
    custom_patterns: list[str] = Field(
        default_factory=lambda: [
            r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b",  # IBAN
            r"\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b",                 # BIC/SWIFT
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",            # PAN
            r"\b\d{3}-\d{2}-\d{4}\b",                                   # SSN
            r"\b\d{9}\b",                                                # Routing number
        ],
        description="Regex patterns for financial PII beyond standard Presidio entities."
    )


class HealerConfig(BaseSettings):
    """Self-healing governance settings (Section 3.2)."""
    model_config = SettingsConfigDict(env_prefix="HEALER_")

    auto_heal_confidence_threshold: float = Field(
        default=0.85,
        ge=0.0, le=1.0,
        description="Below this threshold, heals queue for human review instead of auto-applying."
    )
    max_heal_attempts: int = Field(default=3)
    require_human_ratification: bool = Field(
        default=True,
        description="Healed locators must be ratified by a human before hardening into the suite."
    )
    eligible_failure_types: list[str] = Field(
        default_factory=lambda: ["locator_drift"],
        description="Only these failure types are eligible for auto-heal. Never assertion/business-logic."
    )


class ObservabilityConfig(BaseSettings):
    """Observability and tracing configuration."""
    model_config = SettingsConfigDict(env_prefix="OBS_")

    langsmith_tracing: bool = Field(default=True)
    langsmith_project: str = Field(default="bank-ai-testing")
    otel_endpoint: str = Field(default="http://localhost:4317")
    otel_service_name: str = Field(default="bank-ai-testing-framework")
    enable_screencast: bool = Field(
        default=True,
        description="Playwright Screencast for audit-friendly video evidence."
    )


class EvidenceConfig(BaseSettings):
    """Audit evidence and immutable ledger configuration."""
    model_config = SettingsConfigDict(env_prefix="EVIDENCE_")

    ledger_path: Path = Field(
        default=Path("evidence/audit_ledger"),
        description="Path for the immutable append-only run ledger."
    )
    screenshot_path: Path = Field(default=Path("evidence/screenshots"))
    video_path: Path = Field(default=Path("evidence/videos"))
    report_path: Path = Field(default=Path("evidence/reports"))
    hash_chain_enabled: bool = Field(
        default=True,
        description="Enable hash-chaining for tamper-evident audit trail."
    )


# ---------------------------------------------------------------------------
# Master configuration
# ---------------------------------------------------------------------------

class FrameworkConfig(BaseSettings):
    """
    Master configuration for the Banking AI Testing Framework.

    Loads from environment variables (prefixed), .env file, and
    optionally from a YAML config file specified by FRAMEWORK_CONFIG_PATH.
    """
    model_config = SettingsConfigDict(
        env_prefix="BANK_TEST_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Environment ---
    environment: EnvironmentType = Field(default=EnvironmentType.DEV)
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent
    )
    config_path: Optional[Path] = Field(
        default=None,
        description="Path to YAML config file for overrides."
    )

    # --- Sub-configs ---
    llm: LLMConfig = Field(default_factory=LLMConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    pii: PIIConfig = Field(default_factory=PIIConfig)
    healer: HealerConfig = Field(default_factory=HealerConfig)
    observability: ObservabilityConfig = Field(default_factory=ObservabilityConfig)
    evidence: EvidenceConfig = Field(default_factory=EvidenceConfig)

    # --- CI/CD ---
    smoke_timeout_minutes: int = Field(default=10)
    regression_timeout_minutes: int = Field(default=90)
    max_parallel_executors: int = Field(default=4)

    @field_validator("environment", mode="before")
    @classmethod
    def validate_no_production(cls, v: Any) -> Any:
        """Enforce that agents NEVER connect to production (ADR, Section 3.4)."""
        if isinstance(v, str) and v.lower() in ("prod", "production"):
            raise ValueError(
                "CRITICAL: Agents are architecturally prohibited from connecting to "
                "production environments. This is enforced at config level, network "
                "policy level, and IAM level. See Section 3.4 / Section 5."
            )
        return v

    def model_post_init(self, __context: Any) -> None:
        """Load YAML overrides if config_path is set."""
        if self.config_path and self.config_path.exists():
            with open(self.config_path) as f:
                overrides = yaml.safe_load(f) or {}
            # Apply overrides to sub-configs
            for key, value in overrides.items():
                if hasattr(self, key) and isinstance(value, dict):
                    sub = getattr(self, key)
                    for k, v in value.items():
                        if hasattr(sub, k):
                            object.__setattr__(sub, k, v)

        # Set LangSmith env vars for automatic tracing
        if self.observability.langsmith_tracing:
            os.environ.setdefault("LANGSMITH_TRACING", "true")
            os.environ.setdefault("LANGSMITH_PROJECT", self.observability.langsmith_project)

        # Ensure evidence directories exist
        for dir_field in (
            self.evidence.ledger_path,
            self.evidence.screenshot_path,
            self.evidence.video_path,
            self.evidence.report_path,
        ):
            abs_path = self.project_root / dir_field
            abs_path.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_config: Optional[FrameworkConfig] = None


def get_config(**overrides: Any) -> FrameworkConfig:
    """Get or create the global framework configuration (singleton)."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = FrameworkConfig(**overrides)
    return _config


def reset_config() -> None:
    """Reset config singleton (for testing)."""
    global _config  # noqa: PLW0603
    _config = None
