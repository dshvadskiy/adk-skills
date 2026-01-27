#!/usr/bin/env python3
"""Basic agent example demonstrating skill activation with Google ADK.

Supports multiple LLM providers via ADK's model abstraction:
    - Google Gemini (native, best performance)
    - OpenAI GPT models via LiteLLM
    - Anthropic Claude via LiteLLM
    - Amazon Bedrock models via LiteLLM
    - Azure OpenAI via LiteLLM

Requirements:
    - For Gemini: GOOGLE_API_KEY environment variable
    - For OpenAI: OPENAI_API_KEY environment variable
    - For Anthropic: ANTHROPIC_API_KEY environment variable
    - For Bedrock: AWS credentials configured

Usage:
    # Default (Gemini)
    uv run python examples/basic_agent.py

    # OpenAI
    uv run python examples/basic_agent.py --provider openai

    # Anthropic Claude
    uv run python examples/basic_agent.py --provider anthropic
"""

import argparse
import asyncio
import os
import sys
import warnings
from pathlib import Path

# Suppress ADK experimental feature warnings
warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")
warnings.filterwarnings("ignore", message=".*non-text parts.*")

# Configure LiteLLM to drop unsupported parameters for Bedrock
import litellm
litellm.drop_params = True

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

# Setup observability (logging and OTEL)
from skill_framework.observability.logging_config import setup_logging
from skill_framework.observability.telemetry import setup_telemetry

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_format = os.getenv("LOG_FORMAT", "json")
setup_logging(level=log_level, format_type=log_format)

# Configure Phoenix telemetry (auto-instrumentation)
phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006")
tracer_provider = setup_telemetry(
    project_name="skill_framework_agent",
    auto_instrument=True,
)

import logging
logger = logging.getLogger(__name__)

if tracer_provider:
    logger.info(f"✓ Phoenix telemetry enabled: endpoint={phoenix_endpoint}")
else:
    logger.warning("⚠ Phoenix telemetry not available (install: pip install openinference-instrumentation-google-adk arize-phoenix-otel)")

logger.info(f"Observability configured: log_level={log_level}")

from skill_framework.agent import AgentBuilder
from skill_framework.integration.adk_adapter import ADKAdapter


def create_model(provider: str, model_name: str | None = None):
    """
    Create an ADK-compatible model based on provider.

    Args:
        provider: Provider name (gemini, openai, anthropic, bedrock, azure)
        model_name: Optional model name override

    Returns:
        ADK-compatible model (string or wrapper instance)
    """
    if provider == "gemini":
        # Native Gemini - just return the model string
        return model_name or "gemini-2.0-flash"

    elif provider == "openai":
        from google.adk.models.lite_llm import LiteLlm
        model = model_name or "gpt-4o"
        return LiteLlm(model=f"openai/{model}")

    elif provider == "anthropic":
        from google.adk.models.lite_llm import LiteLlm
        model = model_name or "claude-3-5-sonnet-20241022"
        return LiteLlm(model=f"anthropic/{model}")

    elif provider == "bedrock":
        from google.adk.models.lite_llm import LiteLlm
        # Get model ID - prefer MODEL_ID, then MODEL_NAME, then default
        model_id = model_name or os.getenv("MODEL_ID") or os.getenv("MODEL_NAME", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        
        # Strip any existing bedrock/ prefix
        model_id = model_id.replace("bedrock/", "")
        
        # If it's an ARN or inference profile, use converse route
        if "arn:aws:bedrock" in model_id or "inference-profile" in model_id:
            model_str = f"bedrock/converse/{model_id}"
        else:
            model_str = f"bedrock/{model_id}"
        
        logger.info(f"Using model: {model_str}")
        return LiteLlm(model=model_str)

    elif provider == "azure":
        from google.adk.models.lite_llm import LiteLlm
        if not model_name:
            raise ValueError("Azure requires --model to specify deployment name")
        return LiteLlm(model=f"azure/{model_name}")

    else:
        raise ValueError(f"Unknown provider: {provider}")


async def run_agent(provider: str, model_name: str | None = None) -> None:
    """Run an interactive agent with skill support."""
    # Skills directory loaded from SKILLS_DIR env var or defaults to ./skills
    from skill_framework.config import Config
    skills_dir = Config.get_skills_dir()

    logger.info("=" * 60)
    logger.info(f"Skill Framework Agent - {provider.upper()}")
    logger.info("=" * 60)
    logger.info(f"Skills directory: {skills_dir}")

    # Create model based on provider
    model = create_model(provider, model_name)
    logger.info(f"Using model: {model}")

    # Create adapter and builder (skills_directory is optional, uses config)
    adapter = ADKAdapter(model=model, app_name="skill_demo")
    builder = AgentBuilder()  # Uses SKILLS_DIR from .env

    # Create skill-enabled agent (all wiring handled automatically)
    agent = builder.create_agent(
        adapter=adapter,
        name="skill_agent",
        instruction="You are a helpful assistant with access to skills.",
    )

    # Show available skills
    logger.info("\nAvailable skills:")
    for name, description in agent.available_skills.items():
        logger.info(f"  - {name}: {description}")

    logger.info("\nType 'quit' to exit")
    logger.info("-" * 60)

    # Interactive loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            logger.info("Goodbye!")
            break

        # Send message and get response (message tracking handled automatically)
        try:
            response = await agent.chat(user_input)
            logger.info(f"\nAgent: {response}")
        except Exception as e:
            logger.error(f"\nError: {e}")


def check_credentials(provider: str) -> bool:
    """Check if required credentials are available for the provider."""
    required_vars = {
        "gemini": ["GOOGLE_API_KEY"],
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "bedrock": [],  # AWS credentials via boto3, MODEL_ID/MODEL_NAME optional with defaults
        "azure": ["AZURE_API_KEY", "AZURE_API_BASE"],
    }

    missing = [var for var in required_vars.get(provider, []) if not os.environ.get(var)]
    if missing:
        logger.error(f"Error: Missing environment variables for {provider}: {', '.join(missing)}")
        return False
    return True


def main() -> None:
    """Entry point."""
    parser = argparse.ArgumentParser(
        description="Run skill-enabled agent with multiple LLM providers"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "anthropic", "bedrock", "azure"],
        default="bedrock",
        help="LLM provider to use (default: bedrock)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Model name override (provider-specific)",
    )
    args = parser.parse_args()

    if not check_credentials(args.provider):
        sys.exit(1)

    asyncio.run(run_agent(args.provider, args.model))


if __name__ == "__main__":
    main()
