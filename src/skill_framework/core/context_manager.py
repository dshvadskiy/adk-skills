"""Context manager for skill execution context modifications."""

from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .skill_loader import SkillMetadata


class ContextManager:
    """
    Manages execution context modifications for skills.

    Each skill can modify the execution context to enable/disable
    specific capabilities, tools, or permissions.
    """

    def __init__(self) -> None:
        """Initialize ContextManager with default execution context."""
        self.default_context = {
            "allowed_tools": [],
            "file_permissions": "none",
            "network_access": False,
            "max_execution_time": 300,
            "max_memory": 2048,
            "working_directory": "/tmp",
            "environment_variables": {},
        }

    def modify_for_skill(
        self,
        skill_name: str,
        skill_metadata: "SkillMetadata",
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Modify execution context based on skill requirements.

        This is where tool permissions are scoped per skill.

        Args:
            skill_name: Name of skill being activated
            skill_metadata: Skill metadata from SKILL.md
            current_context: Current execution context to modify

        Returns:
            Modified execution context
        """
        # Start with current context
        modified = deepcopy(current_context)

        # Apply skill-specific tool permissions
        if skill_metadata.required_tools:
            modified["allowed_tools"] = list(
                set(modified.get("allowed_tools", []) + skill_metadata.required_tools)
            )

        # Add optional tools if available
        if skill_metadata.optional_tools:
            available_tools = modified.get("all_available_tools", [])
            for tool in skill_metadata.optional_tools:
                if tool in available_tools and tool not in modified["allowed_tools"]:
                    modified["allowed_tools"].append(tool)

        # Apply execution constraints
        if skill_metadata.max_execution_time:
            modified["max_execution_time"] = min(
                modified.get("max_execution_time", 999999),
                skill_metadata.max_execution_time,
            )

        if skill_metadata.max_memory:
            modified["max_memory"] = min(
                modified.get("max_memory", 999999),
                skill_metadata.max_memory,
            )

        # Network access
        if skill_metadata.network_access:
            modified["network_access"] = True

        # Skill-specific context modifications
        modified = self._apply_skill_specific_context(
            skill_name, skill_metadata, modified
        )

        # Track active skill
        modified["active_skill"] = skill_name
        modified["skill_version"] = skill_metadata.version

        return modified

    def _apply_skill_specific_context(
        self,
        skill_name: str,
        skill_metadata: "SkillMetadata",
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Apply skill-specific context modifications.

        This is where you define custom behavior per skill.

        Args:
            skill_name: Name of skill
            skill_metadata: Skill metadata
            context: Current context to modify

        Returns:
            Modified context with skill-specific adjustments
        """
        # Example: PDF processing needs file operations
        if skill_name == "pdf" or "pdf" in skill_metadata.tags:
            context["file_permissions"] = "read_write"
            context["allowed_file_extensions"] = [".pdf", ".txt", ".json"]

        # Example: Data analysis needs more memory
        if "data-analysis" in skill_metadata.tags:
            context["max_memory"] = max(context.get("max_memory", 2048), 4096)

        # Example: Report generation needs output directory
        if skill_name == "report-generation":
            context["output_directory"] = "/tmp/reports"
            context["file_permissions"] = "read_write"

        # Example: Fraud detection needs database access
        if skill_name == "fraud-analysis":
            context["database_access"] = True
            context["allowed_tables"] = ["transactions", "users", "alerts"]

        return context

    def restore_default_context(self) -> dict[str, Any]:
        """
        Restore default execution context.

        Returns:
            Deep copy of default context
        """
        return deepcopy(self.default_context)
