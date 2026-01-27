"""Phoenix observability integration for Google ADK.

This module provides a simple wrapper around Phoenix's auto-instrumentation
for Google ADK. Phoenix automatically traces all agent interactions, tool calls,
and model requests without requiring custom tracing code.

Usage:
    from skill_framework.observability.telemetry import setup_telemetry

    # Setup once at application start
    setup_telemetry(project_name="my-agent-app")

    # All ADK operations are now automatically traced
"""

import os
from typing import Optional

from .logging_config import get_logger

logger = get_logger(__name__)

_initialized = False


def setup_telemetry(
    project_name: str = "skill_framework",
    auto_instrument: bool = True,
) -> Optional[object]:
    """
    Setup Phoenix observability for Google ADK.

    This uses Phoenix's auto-instrumentation which automatically traces:
    - Agent runs and interactions
    - Tool calls and results
    - Model requests and responses
    - Full context and metadata

    Environment variables:
        PHOENIX_API_KEY: Phoenix API key (required for Phoenix Cloud)
        PHOENIX_COLLECTOR_ENDPOINT: Phoenix endpoint URL
        PHOENIX_CLIENT_HEADERS: Optional headers (for legacy instances)

    Args:
        project_name: Project name for organizing traces in Phoenix
        auto_instrument: Enable automatic instrumentation of ADK operations

    Returns:
        TracerProvider instance if successful, None otherwise
    """
    global _initialized

    if _initialized:
        logger.warning("Telemetry already initialized, skipping setup")
        return None

    try:
        from phoenix.otel import register

        logger.info(f"Initializing Phoenix telemetry: project={project_name}")

        tracer_provider = register(
            project_name=project_name,
            auto_instrument=auto_instrument,
        )

        _initialized = True

        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "not set")
        logger.info(
            f"Phoenix telemetry initialized: project={project_name}, "
            f"endpoint={endpoint}, auto_instrument={auto_instrument}"
        )

        return tracer_provider

    except ImportError:
        logger.warning(
            "Phoenix not installed. Install with: "
            "pip install openinference-instrumentation-google-adk arize-phoenix-otel"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Phoenix telemetry: {e}")
        return None


def is_initialized() -> bool:
    """Check if telemetry has been initialized."""
    return _initialized


def configure_from_env() -> Optional[object]:
    """
    Configure Phoenix telemetry from environment variables.

    Reads configuration from:
        PHOENIX_PROJECT_NAME: Project name (default: "skill_framework")
        PHOENIX_API_KEY: API key for Phoenix Cloud
        PHOENIX_COLLECTOR_ENDPOINT: Phoenix endpoint URL
        PHOENIX_AUTO_INSTRUMENT: Enable auto-instrumentation (default: "true")

    Returns:
        TracerProvider instance if successful, None otherwise
    """
    project_name = os.getenv("PHOENIX_PROJECT_NAME", "skill_framework")
    auto_instrument = os.getenv("PHOENIX_AUTO_INSTRUMENT", "true").lower() == "true"

    return setup_telemetry(
        project_name=project_name,
        auto_instrument=auto_instrument,
    )
