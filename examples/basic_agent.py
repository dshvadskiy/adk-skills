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

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent/ ".env")

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
        model = model_name or os.getenv("MODEL_NAME", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        model_id = os.getenv("MODEL_ID", model)  # Default to model name if not specified
        return LiteLlm(model=f"bedrock/{model}", model_id=model_id)

    elif provider == "azure":
        from google.adk.models.lite_llm import LiteLlm
        if not model_name:
            raise ValueError("Azure requires --model to specify deployment name")
        return LiteLlm(model=f"azure/{model_name}")

    else:
        raise ValueError(f"Unknown provider: {provider}")


async def run_agent(provider: str, model_name: str | None = None) -> None:
    """Run an interactive agent with skill support."""
    skills_dir = Path(__file__).parent.parent / "skills"

    print("=" * 60)
    print(f"Skill Framework Agent - {provider.upper()}")
    print("=" * 60)

    # Create model based on provider
    model = create_model(provider, model_name)
    print(f"\nUsing model: {model}")

    # Create adapter and builder
    adapter = ADKAdapter(model=model, app_name="skill_demo")
    builder = AgentBuilder(skills_directory=skills_dir)

    # Create skill-enabled agent (all wiring handled automatically)
    agent = builder.create_agent(
        adapter=adapter,
        name="skill_agent",
        instruction="You are a helpful assistant with access to skills.",
    )

    # Show available skills
    print("\nAvailable skills:")
    for name, description in agent.available_skills.items():
        print(f"  - {name}: {description}")

    print("\nType 'quit' to exit")
    print("-" * 60)

    # Interactive loop
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() == "quit":
            print("Goodbye!")
            break

        # Send message and get response (message tracking handled automatically)
        try:
            response = await agent.chat(user_input)
            print(f"\nAgent: {response}")
        except Exception as e:
            print(f"\nError: {e}")


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
        print(f"Error: Missing environment variables for {provider}: {', '.join(missing)}")
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
