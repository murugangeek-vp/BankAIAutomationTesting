"""
Structured logging configuration for the Banking AI Testing Framework.

Provides audit-grade, structured logging using structlog with:
- JSON output for machine-parseable audit trails
- Console output with rich formatting for development
- Immutable context binding for trace correlation
- Automatic agent role / run ID tagging on every log line
- Log levels enforced per banking compliance requirements
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import structlog
from rich.console import Console
from rich.logging import RichHandler

from src.core.config import EnvironmentType, get_config


# ---------------------------------------------------------------------------
# Custom processors
# ---------------------------------------------------------------------------

def add_timestamp(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add ISO 8601 UTC timestamp — required for immutable audit ledger."""
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def add_run_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Add run ID and environment context if not already bound."""
    event_dict.setdefault("run_id", "unbound")
    event_dict.setdefault("environment", "unknown")
    return event_dict


def redact_sensitive_fields(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Redact known-sensitive field names from log output.
    Defense-in-depth — PII proxy is the primary gate, this is a secondary net.
    """
    sensitive_keys = {
        "api_key", "password", "secret", "token", "credential",
        "pan", "ssn", "iban", "account_number", "routing_number",
    }
    for key in list(event_dict.keys()):
        if key.lower() in sensitive_keys:
            event_dict[key] = "***REDACTED***"
    return event_dict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def configure_logging(
    environment: EnvironmentType | None = None,
    log_level: str = "INFO",
    json_output: bool | None = None,
) -> None:
    """
    Configure structured logging for the framework.

    Args:
        environment: Override environment detection from config.
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_output: Force JSON output. If None, auto-detects (JSON for CI/staging, rich for dev).
    """
    if environment is None:
        try:
            environment = get_config().environment
        except Exception:
            environment = EnvironmentType.DEV

    if json_output is None:
        json_output = environment in (EnvironmentType.CI, EnvironmentType.STAGING)

    # --- Shared processors ---
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        add_timestamp,
        add_run_context,
        redact_sensitive_fields,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        # Machine-parseable for CI, audit, and log aggregators
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        # Human-readable with rich formatting for local dev
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # --- Standard library logging integration ---
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    # Clear existing handlers
    root = logging.getLogger()
    root.handlers.clear()

    if json_output:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
    else:
        handler = RichHandler(
            console=Console(stderr=True),
            show_path=False,
            rich_tracebacks=True,
        )
        handler.setFormatter(formatter)

    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Suppress noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "opentelemetry", "langsmith"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------

def get_logger(
    name: str,
    agent_role: str | None = None,
    run_id: str | None = None,
    **initial_context: Any,
) -> structlog.stdlib.BoundLogger:
    """
    Get a bound structured logger with optional agent/run context.

    Args:
        name: Logger name (typically __name__ of the calling module).
        agent_role: Agent role string for context binding.
        run_id: Unique run identifier for trace correlation.
        **initial_context: Additional key-value pairs bound to every log entry.

    Returns:
        A structlog BoundLogger pre-configured with context.
    """
    logger = structlog.get_logger(name)

    bindings: dict[str, Any] = {**initial_context}
    if agent_role:
        bindings["agent_role"] = agent_role
    if run_id:
        bindings["run_id"] = run_id

    if bindings:
        logger = logger.bind(**bindings)

    return logger  # type: ignore[return-value]


def generate_run_id() -> str:
    """Generate a unique run ID for trace correlation across agents."""
    return f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid4().hex[:8]}"
