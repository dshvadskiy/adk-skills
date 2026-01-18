"""Agent builder for constructing agents with Skills support."""

from pathlib import Path
from typing import Any, Callable, Optional

from ..core.skill_meta_tool import SkillMetaTool, SkillActivationResult
from ..tools.tool_registry import ToolRegistry
from .conversation import ConversationManager


class AgentBuilder:
    """
    Builds agents with Skills support.

    Orchestrates:
    - Skill meta-tool setup
    - Tool registry
    - System prompt construction
    - Conversation management

    The AgentBuilder is framework-agnostic - it prepares all components
    needed for an agent but doesn't depend on a specific LLM provider.
    """

    def __init__(
        self,
        skills_directory: Path,
        enable_cache: bool = True,
    ):
        """
        Initialize agent builder.

        Args:
            skills_directory: Path to skills folder
            enable_cache: Enable skill caching
        """
        self.skills_dir = Path(skills_directory)

        # Initialize skill meta-tool
        self.skill_meta_tool = SkillMetaTool(
            skills_directory=self.skills_dir,
            cache_enabled=enable_cache,
        )

        # Initialize tool registry
        self.tool_registry = ToolRegistry()

        # Register Skill meta-tool
        self.tool_registry.register_tool(
            name="Skill",
            definition=self.skill_meta_tool.get_tool_definition(),
        )

        # Conversation manager for state tracking
        self.conversation_manager = ConversationManager()

        # Tool handlers (name -> async callable)
        self._tool_handlers: dict[str, Callable] = {}

    def register_tool(
        self,
        name: str,
        definition: dict[str, Any],
        handler: Optional[Callable] = None,
    ) -> "AgentBuilder":
        """
        Register a tool with the agent.

        Args:
            name: Tool identifier
            definition: Tool definition dict (name, description, parameters)
            handler: Optional async handler function

        Returns:
            Self for method chaining
        """
        self.tool_registry.register_tool(name, definition)
        if handler:
            self._tool_handlers[name] = handler
        return self

    def build_system_prompt(self, base_instruction: str) -> str:
        """
        Build complete system prompt including skills section.

        Args:
            base_instruction: Base system instruction

        Returns:
            Complete system prompt with skills metadata
        """
        prompt = base_instruction

        # Add skills section (metadata only - progressive disclosure)
        skills_section = self.skill_meta_tool.get_system_prompt_section()
        if skills_section:
            prompt += "\n\n" + skills_section

        # Add tool usage guidelines
        prompt += "\n\n## Tool Usage\n\n"
        prompt += (
            "You have access to various tools. To use a skill, call the Skill tool "
            "with the appropriate skill name. Once a skill is activated, follow its "
            "specific instructions carefully.\n"
        )

        return prompt

    def get_tools(
        self,
        additional_tools: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Get all tool definitions for LLM.

        Args:
            additional_tools: Extra tools to include

        Returns:
            List of all tool definitions
        """
        tools = []

        # Add all registered tools (includes Skill meta-tool)
        tools.extend(self.tool_registry.get_all_tool_definitions())

        # Add additional tools if provided
        if additional_tools:
            tools.extend(additional_tools)

        return tools

    async def handle_skill_activation(
        self,
        skill_name: str,
        session_id: str,
        current_context: Optional[dict[str, Any]] = None,
    ) -> SkillActivationResult:
        """
        Handle Skill tool invocation.

        This is called when the LLM invokes the Skill tool.
        Activates the skill and injects messages into conversation.

        Args:
            skill_name: Name of skill to activate
            session_id: Conversation session ID
            current_context: Current execution context

        Returns:
            SkillActivationResult with messages and context
        """
        context = current_context or {}

        # Activate the skill
        result = await self.skill_meta_tool.activate_skill(
            skill_name=skill_name,
            current_context=context,
        )

        if result.success:
            # Inject messages into conversation
            self.conversation_manager.inject_skill_messages(
                session_id=session_id,
                metadata_message=result.metadata_message,
                instruction_message=result.instruction_message,
            )

            # Update conversation context
            self.conversation_manager.update_context(
                session_id=session_id,
                context_updates=result.modified_context,
            )

            # Track skill as active
            self.conversation_manager.activate_skill(session_id, skill_name)

        return result

    async def handle_tool_call(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        session_id: str,
        current_context: Optional[dict[str, Any]] = None,
    ) -> Any:
        """
        Handle a tool call from the LLM.

        Routes to appropriate handler based on tool name.

        Args:
            tool_name: Name of tool being called
            tool_input: Tool input parameters
            session_id: Conversation session ID
            current_context: Current execution context

        Returns:
            Tool execution result
        """
        # Special handling for Skill meta-tool
        if tool_name == "Skill":
            return await self.handle_skill_activation(
                skill_name=tool_input.get("skill_name", ""),
                session_id=session_id,
                current_context=current_context,
            )

        # Check for registered handler
        if tool_name in self._tool_handlers:
            handler = self._tool_handlers[tool_name]
            return await handler(tool_input, current_context or {})

        # No handler found
        raise ValueError(f"No handler registered for tool: {tool_name}")

    def create_session(self, session_id: str) -> str:
        """
        Create a new conversation session.

        Args:
            session_id: Unique session identifier

        Returns:
            Session ID
        """
        self.conversation_manager.create_conversation(session_id)
        return session_id

    def get_messages_for_api(
        self,
        session_id: str,
        include_meta: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get messages formatted for LLM API.

        Args:
            session_id: Conversation session ID
            include_meta: Include hidden skill instruction messages

        Returns:
            List of message dicts for API
        """
        return self.conversation_manager.get_messages_for_api(
            session_id=session_id,
            include_meta=include_meta,
        )

    def add_user_message(self, session_id: str, content: str) -> None:
        """Add user message to conversation."""
        self.conversation_manager.add_user_message(session_id, content)

    def add_assistant_message(self, session_id: str, content: Any) -> None:
        """Add assistant message to conversation."""
        self.conversation_manager.add_assistant_message(session_id, content)

    def get_active_skills(self, session_id: str) -> list[str]:
        """Get list of active skills in session."""
        state = self.conversation_manager.get_conversation(session_id)
        return state.active_skills if state else []

    def deactivate_skill(self, session_id: str, skill_name: str) -> None:
        """Deactivate a skill in the session."""
        self.skill_meta_tool.deactivate_skill(skill_name)
        self.conversation_manager.deactivate_skill(session_id, skill_name)
