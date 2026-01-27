"""Skill meta-tool for managing skill lifecycle."""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from .script_executor import ExecutionConstraints, ScriptExecutor
from .skill_loader import SkillContent, SkillLoader, SkillMetadata


class SkillActivationMode(Enum):
    """Modes for skill activation."""

    AUTO = "auto"  # LLM decides when to activate
    MANUAL = "manual"  # Explicit activation required
    PRELOAD = "preload"  # Load at conversation start


@dataclass
class SkillActivationResult:
    """Result of skill activation."""

    success: bool
    skill_name: str
    metadata_message: dict[str, Any]
    instruction_message: dict[str, Any]
    modified_context: dict[str, Any]
    permissions_message: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    error_details: Optional[dict[str, Any]] = None


class SkillMetaTool:
    """
    Meta-tool that manages skill lifecycle following Claude Code architecture.

    Key Responsibilities:
    1. Load skill metadata (progressive disclosure)
    2. Implement two-message injection pattern
    3. Modify execution context per skill
    4. Manage tool permissions
    5. Coordinate with LLM for skill selection

    Architecture Pattern:
    - Meta-tool appears as single "Skill" tool in tools array
    - LLM decides when to invoke based on task requirements
    - On invocation, loads full skill content on-demand
    - Injects two messages: visible + hidden (isMeta=true)
    - Modifies available tools and permissions
    """

    def __init__(
        self,
        skills_directory: Optional[Path] = None,
        cache_enabled: bool = True,
    ):
        """
        Initialize Skill Meta-Tool.

        Args:
            skills_directory: Path to skills folder (defaults to SKILLS_DIR env var)
            cache_enabled: Cache loaded skills in memory
        """
        if skills_directory is None:
            from ..config import Config
            skills_directory = Config.get_skills_dir()
        
        self.skills_dir = Path(skills_directory)
        self.cache_enabled = cache_enabled

        # Core component
        self.loader = SkillLoader(skills_dir=self.skills_dir)

        # Load metadata only (not full content) - progressive disclosure
        self.skills_metadata: dict[str, SkillMetadata] = {}
        self._load_all_metadata()

        # Skill content cache
        self._skill_cache: dict[str, SkillContent] = {}

        # Active skills in current session
        self.active_skills: dict[str, dict[str, Any]] = {}

    def _load_all_metadata(self) -> None:
        """
        Load metadata from all SKILL.md files.

        Only parses YAML frontmatter, not full content.
        This enables fast startup with minimal memory usage.
        """
        if not self.skills_dir.exists():
            return

        for skill_path in self.skills_dir.iterdir():
            if skill_path.is_dir() and (skill_path / "SKILL.md").exists():
                try:
                    metadata = self.loader.load_metadata(skill_path.name)
                    self.skills_metadata[metadata.name] = metadata
                except Exception:
                    # Skip invalid skills silently
                    pass

    def get_tool_definition(self) -> dict[str, Any]:
        """
        Get tool definition for LLM tools array.

        Returns:
            Tool definition dict for "Skill" meta-tool
        """
        return {
            "name": "Skill",
            "description": self._build_tool_description(),
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Name of skill to activate",
                        "enum": list(self.skills_metadata.keys()),
                    }
                },
                "required": ["skill_name"],
            },
        }

    def _build_tool_description(self) -> str:
        """
        Build tool description that helps LLM understand when to use skills.

        Critical: This is how LLM decides to invoke the Skill meta-tool.
        Must be clear and comprehensive.
        """
        base_desc = (
            "IMPORTANT: Automatically activate skills when the user's request matches a skill's purpose. "
            "Do NOT wait for explicit 'activate skill' requests - proactively use skills based on user intent.\n\n"
            "Available skills:\n"
        )

        for name, metadata in self.skills_metadata.items():
            base_desc += f"- {name}: {metadata.description}\n"

        base_desc += (
            "\nWhen the user's message relates to any skill's domain, call this tool immediately. "
            "Once activated, follow the skill's instructions for ALL related requests in the conversation."
        )

        return base_desc

    def get_system_prompt_section(self) -> str:
        """
        Generate skills section for system prompt.

        CRITICAL: Only includes metadata, NOT full instructions.
        This is progressive disclosure - full content loaded on-demand.

        Returns:
            String to include in system prompt
        """
        if not self.skills_metadata:
            return ""

        section = "\n## Available Skills\n\n"
        section += (
            "You have access to specialized skills for domain-specific tasks:\n\n"
        )

        for name, metadata in self.skills_metadata.items():
            section += f"**{name}** (v{metadata.version})\n"
            section += f"  {metadata.description}\n"

            if metadata.tags:
                section += f"  Tags: {', '.join(metadata.tags)}\n"

            section += "\n"

        section += (
            "IMPORTANT: Proactively activate skills when user requests match a skill's purpose. "
            "Do not wait for explicit activation requests - match user intent to skill descriptions. "
            "Once a skill is activated, it remains active and applies to all related requests.\n"
        )

        return section

    async def activate_skill(
        self,
        skill_name: str,
        current_context: dict[str, Any],
    ) -> SkillActivationResult:
        """
        Activate a skill using two-message pattern.

        This is the CORE implementation of the Skills architecture:
        1. Validate skill exists and can be loaded
        2. Load full SKILL.md content (progressive disclosure)
        3. Create metadata message (visible to user)
        4. Create instruction message (hidden, isMeta=true)
        5. Modify execution context (permissions, tools)
        6. Return activation result

        Args:
            skill_name: Name of skill to activate
            current_context: Current execution context

        Returns:
            SkillActivationResult with messages and context
        """
        # Import here to avoid circular dependency
        from .message_injector import MessageInjector

        # Step 1: Validate skill exists
        if skill_name not in self.skills_metadata:
            return SkillActivationResult(
                success=False,
                skill_name=skill_name,
                metadata_message={},
                instruction_message={},
                modified_context=current_context,
                error=f"Skill '{skill_name}' not found",
                error_details={"available_skills": list(self.skills_metadata.keys())},
            )

        try:
            # Step 2: Load full skill content (progressive disclosure)
            skill_content = self._load_skill_content(skill_name)
            metadata = self.skills_metadata[skill_name]

            # Resolve {baseDir} variable in instructions
            skill_directory = self.skills_dir / skill_name
            resolved_instructions = self._resolve_basedir_variable(
                skill_content.instructions, skill_directory
            )

            # Step 3 & 4: Create messages using MessageInjector
            injector = MessageInjector()
            metadata_msg = injector.create_metadata_message(
                skill_name=skill_name,
                metadata=metadata,
            )
            instruction_msg = injector.create_instruction_message(
                skill_name=skill_name,
                instructions=resolved_instructions,
                metadata=metadata,
            )

            # Step 4.5: Create permissions message if allowed_tools present
            permissions_msg = None
            if metadata.allowed_tools:
                # Parse allowed_tools to get list
                # Create temporary executor just to parse the tools
                temp_executor = ScriptExecutor(
                    skill_name=skill_name,
                    skill_directory=self.skills_dir / skill_name,
                    allowed_tools=metadata.allowed_tools,
                )
                parsed_tools = temp_executor.allowed_tools
                permissions_msg = self._create_permissions_message(
                    allowed_tools=parsed_tools,
                    model=None,  # Model can be added to metadata if needed
                )

            # Step 5: Modify execution context
            modified_context = self._modify_context_for_skill(
                skill_name=skill_name,
                metadata=metadata,
                current_context=current_context,
            )

            # Track active skill
            self.active_skills[skill_name] = {
                "metadata": metadata,
                "content": skill_content,
                "activated_at": self._get_timestamp(),
            }

            return SkillActivationResult(
                success=True,
                skill_name=skill_name,
                metadata_message=metadata_msg,
                instruction_message=instruction_msg,
                modified_context=modified_context,
                permissions_message=permissions_msg,
            )

        except Exception as e:
            return SkillActivationResult(
                success=False,
                skill_name=skill_name,
                metadata_message={},
                instruction_message={},
                modified_context=current_context,
                error=str(e),
                error_details={"exception_type": type(e).__name__},
            )

    def _load_skill_content(self, skill_name: str) -> SkillContent:
        """Load skill content with caching support."""
        if self.cache_enabled and skill_name in self._skill_cache:
            return self._skill_cache[skill_name]

        content = self.loader.load_skill(skill_name)

        if self.cache_enabled:
            self._skill_cache[skill_name] = content

        return content

    def _resolve_basedir_variable(
        self, instructions: str, skill_directory: Path
    ) -> str:
        """
        Replace {baseDir} and {basedir} variables with absolute skill directory path.

        Supports case-insensitive matching for flexibility.

        Args:
            instructions: Skill instructions with {baseDir} placeholders
            skill_directory: Absolute path to skill directory

        Returns:
            Instructions with all {baseDir} occurrences replaced
        """
        import re

        # Convert to absolute path string
        base_dir_str = str(skill_directory.resolve())

        # Replace both {baseDir} and {basedir} (case-insensitive)
        # Use regex for case-insensitive replacement
        resolved = re.sub(
            r"\{basedir\}", base_dir_str, instructions, flags=re.IGNORECASE
        )

        return resolved

    def _modify_context_for_skill(
        self,
        skill_name: str,
        metadata: SkillMetadata,
        current_context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Modify execution context based on skill requirements.

        This is where tool permissions are scoped per skill.
        Creates ScriptExecutor if skill has scripts/ directory.
        """
        modified = dict(current_context)

        # Apply skill-specific tool permissions
        allowed_tools = list(modified.get("allowed_tools", []))
        if metadata.required_tools:
            for tool in metadata.required_tools:
                if tool not in allowed_tools:
                    allowed_tools.append(tool)
        modified["allowed_tools"] = allowed_tools

        # Apply execution constraints
        if metadata.max_execution_time:
            current_max = modified.get("max_execution_time", 999999)
            modified["max_execution_time"] = min(
                current_max, metadata.max_execution_time
            )

        if metadata.max_memory:
            current_max = modified.get("max_memory", 999999)
            modified["max_memory"] = min(current_max, metadata.max_memory)

        # Network access
        if metadata.network_access:
            modified["network_access"] = True

        # Track active skill
        modified["active_skill"] = skill_name
        modified["skill_version"] = metadata.version

        # Create ScriptExecutor if skill has scripts/ directory
        skill_directory = self.skills_dir / skill_name
        scripts_dir = skill_directory / "scripts"

        if scripts_dir.exists() and scripts_dir.is_dir():
            # Create execution constraints from metadata
            constraints = ExecutionConstraints(
                max_execution_time=metadata.max_execution_time or 300,
                max_memory=metadata.max_memory,
                network_access=metadata.network_access,
                working_directory=skill_directory,
            )

            # Create ScriptExecutor
            script_executor = ScriptExecutor(
                skill_name=skill_name,
                skill_directory=skill_directory,
                allowed_tools=metadata.allowed_tools,
                constraints=constraints,
            )

            modified["script_executor"] = script_executor
            modified["base_dir"] = str(skill_directory.resolve())

        return modified

    def deactivate_skill(self, skill_name: str) -> None:
        """Deactivate a skill and remove from active skills."""
        if skill_name in self.active_skills:
            del self.active_skills[skill_name]

    def get_active_skills(self) -> list[str]:
        """Get list of currently active skills."""
        return list(self.active_skills.keys())

    def is_skill_active(self, skill_name: str) -> bool:
        """Check if skill is currently active."""
        return skill_name in self.active_skills

    def reload_skills(self) -> None:
        """Reload all skill metadata (for development)."""
        self.skills_metadata.clear()
        self._skill_cache.clear()
        self._load_all_metadata()

    def clear_cache(self) -> None:
        """Clear skill content cache."""
        self._skill_cache.clear()

    def _create_permissions_message(
        self,
        allowed_tools: list[str],
        model: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create command_permissions message for execution context.

        This matches Claude Skills implementation format:
        {
            "role": "user",
            "content": {
                "type": "command_permissions",
                "allowedTools": ["Bash(python:*)", "Read", "Write"],
                "model": "claude-opus-4-20250514"
            }
        }

        Args:
            allowed_tools: List of allowed tool patterns
            model: Optional model identifier

        Returns:
            Permissions message dict
        """
        content: dict[str, Any] = {
            "type": "command_permissions",
            "allowedTools": allowed_tools,
        }

        if model:
            content["model"] = model

        return {
            "role": "user",
            "content": content,
        }

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()
