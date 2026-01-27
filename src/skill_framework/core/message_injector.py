"""Message injector for two-message pattern implementation."""

from datetime import datetime, timezone
from typing import Any

from .skill_loader import SkillMetadata
from ..observability.logging_config import get_logger

logger = get_logger(__name__)


class MessageInjector:
    """
    Implements two-message injection pattern for skills.

    Message 1: Visible metadata (command-message)
    - Shows in UI/logs
    - Indicates skill activation
    - Helps user understand what's happening

    Message 2: Hidden instructions (isMeta=true)
    - Not shown in UI
    - Contains full SKILL.md instructions
    - Provides context to LLM
    """

    def create_metadata_message(
        self,
        skill_name: str,
        metadata: SkillMetadata,
    ) -> dict[str, Any]:
        """
        Create visible metadata message (Message 1).

        This message appears in conversation history and UI.
        Uses <command-message> XML tag for identification.
        """
        logger.debug(f"Creating metadata message for skill: {skill_name}")
        return {
            "role": "user",
            "content": (
                f"<command-message>"
                f"Activating skill: {skill_name} (v{metadata.version})"
                f"</command-message>"
            ),
            "metadata": {
                "type": "skill_activation",
                "skill_name": skill_name,
                "skill_version": metadata.version,
                "timestamp": self._get_timestamp(),
                "visible": True,
            },
        }

    def create_instruction_message(
        self,
        skill_name: str,
        instructions: str,
        metadata: SkillMetadata,
    ) -> dict[str, Any]:
        """
        Create hidden instruction message (Message 2).

        CRITICAL: This message has isMeta=true which means:
        - It's sent to the LLM for context
        - It's NOT shown in UI/conversation history
        - It provides the actual skill instructions

        This is the core of progressive disclosure.
        """
        logger.debug(
            f"Creating instruction message for skill: {skill_name}, "
            f"instructions_length={len(instructions)}"
        )
        return {
            "role": "user",
            "content": self._format_instructions(skill_name, instructions, metadata),
            "isMeta": True,  # CRITICAL: Hides from UI
            "metadata": {
                "type": "skill_instructions",
                "skill_name": skill_name,
                "skill_version": metadata.version,
                "timestamp": self._get_timestamp(),
                "visible": False,
            },
        }

    def _format_instructions(
        self,
        skill_name: str,
        instructions: str,
        metadata: SkillMetadata,
    ) -> str:
        """
        Format skill instructions for injection.

        Adds skill context and metadata to instructions.
        """
        formatted = f"# {skill_name} Skill\n\n"

        # Add metadata context
        formatted += f"**Version:** {metadata.version}\n"

        if metadata.author:
            formatted += f"**Author:** {metadata.author}\n"

        if metadata.tags:
            formatted += f"**Tags:** {', '.join(metadata.tags)}\n"

        if metadata.required_tools:
            formatted += f"**Required Tools:** {', '.join(metadata.required_tools)}\n"

        formatted += "\n---\n\n"

        # Add actual instructions
        formatted += instructions

        # Add constraints if any
        if metadata.max_execution_time:
            formatted += f"\n\n**Execution Time Limit:** {metadata.max_execution_time}s"

        if not metadata.network_access:
            formatted += "\n\n**Note:** Network access is disabled for this skill."

        return formatted

    def _get_timestamp(self) -> str:
        """Get ISO format timestamp."""
        return datetime.now(timezone.utc).isoformat()
