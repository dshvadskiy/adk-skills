#!/usr/bin/env python3
"""Basic agent example demonstrating skill activation with Google ADK.

Requirements:
    - GOOGLE_API_KEY environment variable set

Usage:
    uv run python examples/basic_agent.py
"""

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
load_dotenv(Path(__file__).parent.parent / ".env")

from skill_framework.agent import AgentBuilder
from skill_framework.integration.adk_adapter import ADKAdapter


async def run_agent() -> None:
    """Run an interactive agent with skill support."""
    skills_dir = Path(__file__).parent.parent / "skills"

    print("=" * 60)
    print("Skill Framework Agent - Google ADK")
    print("=" * 60)

    # Create adapter and builder
    adapter = ADKAdapter(model="gemini-2.0-flash", app_name="skill_demo")
    builder = AgentBuilder(skills_directory=skills_dir)

    # Create session first (needed by skill_tool closure)
    session_id = builder.create_session("demo-session")

    # Create ADK-compatible skill tool using the framework's SkillMetaTool
    # This achieves progressive disclosure: metadata in docstring, full content on-demand
    def create_skill_tool(skill_meta_tool, conversation_manager, sess_id):
        """Factory to create skill_tool with dynamic docstring from metadata."""

        # Build skill list dynamically from loaded metadata (NOT hardcoded)
        skill_list = "\n".join(
            f"        - {name}: {meta.description}"
            for name, meta in skill_meta_tool.skills_metadata.items()
        )

        def skill_tool(skill_name: str) -> str:
            """Activate a skill - docstring replaced dynamically."""
            # Progressive disclosure: load full content ON-DEMAND
            try:
                skill_content = skill_meta_tool.loader.load_skill(skill_name)
                metadata = skill_meta_tool.skills_metadata.get(skill_name)

                if not metadata:
                    available = list(skill_meta_tool.skills_metadata.keys())
                    return f"Skill '{skill_name}' not found. Available: {available}"

                # Track activation
                conversation_manager.activate_skill(sess_id, skill_name)
                print(f"\n[Skill '{skill_name}' activated - loaded on-demand]")

                # Return full instructions (loaded on-demand, not at startup)
                return f"""# Skill Activated: {skill_name} (v{metadata.version})

{skill_content.instructions}

This skill remains active. Apply these instructions to related requests."""
            except Exception as e:
                return f"Error activating skill '{skill_name}': {e}"

        # Dynamically set docstring with current skill metadata
        skill_tool.__doc__ = f"""Activate a specialized skill based on user intent.

IMPORTANT: Call this automatically when user's request matches a skill's purpose.
Do NOT wait for explicit activation - proactively match intent to skills.

Available skills:
{skill_list}

Args:
    skill_name: Name of skill to activate.

Returns:
    Skill instructions to follow for the conversation."""

        return skill_tool

    skill_tool = create_skill_tool(
        builder.skill_meta_tool,
        builder.conversation_manager,
        session_id,
    )

    # Build system prompt with skill metadata
    base_instruction = """You are a helpful assistant with access to skills.

IMPORTANT: Proactively activate skills based on user intent:
- When a user's request matches a skill's purpose, activate that skill immediately
- Do NOT wait for the user to explicitly say "activate" or "use" a skill
- Match the user's intent to available skill descriptions

Once a skill is activated, it remains active - continue following its instructions for all related requests."""

    system_prompt = builder.build_system_prompt(base_instruction)

    # Show available skills
    print("\nAvailable skills:")
    for name, metadata in builder.skill_meta_tool.skills_metadata.items():
        print(f"  - {name}: {metadata.description}")

    print("\nType 'quit' to exit")
    print("-" * 60)

    # Create the ADK agent with Skill tool as a callable function
    adapter.create_agent(
        name="skill_agent",
        instruction=system_prompt,
        description="An agent that can activate and use skills",
        tools=[skill_tool],  # ADK uses callable functions as tools
    )

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

        # Add user message
        builder.add_user_message(session_id, user_input)

        # Send to LLM
        try:
            response = await adapter.send_message(
                messages=builder.get_messages_for_api(session_id),
                system_prompt=system_prompt,
                tools=[],  # Tools are registered with the agent, not per-message
                session_id=session_id,
            )
        except Exception as e:
            print(f"\nError: {e}")
            continue

        # Note: ADK handles tool calls automatically via the skill_tool function
        # The function is called by ADK and its return value is used in the conversation

        # Print response
        if response.content:
            print(f"\nAgent: {response.content}")
            builder.add_assistant_message(session_id, response.content)


def main() -> None:
    """Entry point."""
    if not os.environ.get("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable required")
        sys.exit(1)

    asyncio.run(run_agent())


if __name__ == "__main__":
    main()
