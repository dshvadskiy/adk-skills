"""Agent builder for constructing agents with Skills support."""

from pathlib import Path
from typing import Any, AsyncIterator, Callable, Optional, TYPE_CHECKING

from ..core.skill_meta_tool import SkillMetaTool, SkillActivationResult
from ..tools.tool_registry import ToolRegistry
from .conversation import ConversationManager

if TYPE_CHECKING:
    from ..integration.base_adapter import BaseLLMAdapter


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

    # =========================================================================
    # Adapter Integration - Simplified Agent Creation
    # =========================================================================

    def create_agent(
        self,
        adapter: "BaseLLMAdapter",
        name: str = "skill_agent",
        instruction: str = "You are a helpful assistant.",
        description: str = "",
        session_id: Optional[str] = None,
    ) -> "SkillEnabledAgent":
        """
        Create a skill-enabled agent with all wiring handled automatically.

        This is the main entry point for creating agents. It:
        - Creates the skill tool with dynamic docstring
        - Builds the system prompt with skill metadata
        - Configures the adapter with the agent
        - Sets up conversation tracking
        - Registers execution tools (bash_tool, read_file, write_file)

        Args:
            adapter: LLM adapter (e.g., ADKAdapter)
            name: Agent name
            instruction: Base system instruction
            description: Agent description
            session_id: Optional session ID (auto-generated if not provided)

        Returns:
            SkillEnabledAgent for interaction

        Example:
            builder = AgentBuilder(skills_directory=skills_dir)
            agent = builder.create_agent(
                adapter=ADKAdapter(model="gemini-2.0-flash"),
                instruction="You are a helpful assistant."
            )
            async for response in agent.chat("Hello"):
                print(response)
        """
        # Generate session ID if not provided
        if session_id is None:
            import uuid

            session_id = f"session-{uuid.uuid4().hex[:8]}"

        # Create session
        self.create_session(session_id)

        # Build skill tool with dynamic docstring
        skill_tool = self._create_skill_tool(session_id)

        # Create universal execution tools that work with active skill context
        bash_tool = self._create_universal_bash_tool(session_id)
        read_file_tool = self._create_universal_read_file_tool(session_id)
        write_file_tool = self._create_universal_write_file_tool(session_id)

        # Build system prompt with skill awareness
        system_prompt = self._build_skill_aware_prompt(instruction)

        # Configure adapter with agent (include all tools)
        adapter.create_agent(
            name=name,
            instruction=system_prompt,
            description=description or f"{name} with skill support",
            tools=[skill_tool, bash_tool, read_file_tool, write_file_tool],
        )

        return SkillEnabledAgent(
            builder=self,
            adapter=adapter,
            session_id=session_id,
            system_prompt=system_prompt,
        )

    def _create_skill_tool(self, session_id: str) -> Callable[[str], str]:
        """
        Create ADK-compatible skill tool with dynamic docstring.

        The tool's docstring contains skill metadata for LLM discovery.
        Full skill content is loaded on-demand when activated (progressive disclosure).

        Args:
            session_id: Session ID for tracking activations

        Returns:
            Callable skill tool function
        """
        skill_meta_tool = self.skill_meta_tool
        conversation_manager = self.conversation_manager

        # Build skill list from metadata
        skill_list = "\n".join(
            f"        - {name}: {meta.description}"
            for name, meta in skill_meta_tool.skills_metadata.items()
        )

        def skill_tool(skill_name: str) -> str:
            """Activate a skill - docstring replaced dynamically."""
            try:
                # Progressive disclosure: load full content ON-DEMAND
                skill_content = skill_meta_tool.loader.load_skill(skill_name)
                metadata = skill_meta_tool.skills_metadata.get(skill_name)

                if not metadata:
                    available = list(skill_meta_tool.skills_metadata.keys())
                    return f"Skill '{skill_name}' not found. Available: {available}"

                # Track activation
                conversation_manager.activate_skill(session_id, skill_name)

                # Store skill context for tool creation
                skill_directory = self.skills_dir / skill_name
                conversation_manager.update_context(
                    session_id=session_id,
                    context_updates={
                        "active_skill_name": skill_name,
                        "active_skill_directory": str(skill_directory),
                    },
                )

                # Check if skill has scripts
                scripts_dir = skill_directory / "scripts"
                if scripts_dir.exists() and scripts_dir.is_dir():
                    tools_info = "\n\n**Available Tools**: bash_tool, read_file, write_file are now active for this skill."
                else:
                    tools_info = ""

                # Return full instructions (loaded on-demand, not at startup)
                return f"""# Skill Activated: {skill_name} (v{metadata.version})

{skill_content.instructions}{tools_info}

This skill remains active. Apply these instructions to related requests."""
            except Exception as e:
                return f"Error activating skill '{skill_name}': {e}"

        # Set dynamic docstring with skill metadata
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

    def _build_skill_aware_prompt(self, base_instruction: str) -> str:
        """
        Build system prompt with skill awareness instructions.

        Args:
            base_instruction: User's base instruction

        Returns:
            Complete system prompt with skill metadata and usage guidelines
        """
        skill_awareness = """

IMPORTANT: Proactively activate skills based on user intent:
- When a user's request matches a skill's purpose, activate that skill immediately
- Do NOT wait for the user to explicitly say "activate" or "use" a skill
- Match the user's intent to available skill descriptions

Once a skill is activated, it remains active - continue following its instructions for all related requests."""

        return self.build_system_prompt(base_instruction + skill_awareness)

    def _create_execution_tools_for_skill(self, skill_name: str) -> list[Callable]:
        """
        Create execution tools for a skill with scripts.

        This creates bash_tool, read_file, and write_file tools that are
        scoped to the skill's directory and permissions.

        Args:
            skill_name: Name of the activated skill

        Returns:
            List of tool functions for ADK Agent
        """
        from ..integration.adk_tools import (
            create_bash_tool_with_skill_executor,
            create_read_file_tool,
            create_write_file_tool,
        )
        from ..core.script_executor import ScriptExecutor, ExecutionConstraints

        tools = []

        # Get skill metadata and directory
        metadata = self.skill_meta_tool.skills_metadata.get(skill_name)
        if not metadata:
            return tools

        skill_directory = self.skills_dir / skill_name
        scripts_dir = skill_directory / "scripts"

        # Only create tools if skill has scripts directory
        if not scripts_dir.exists() or not scripts_dir.is_dir():
            return tools

        # Create ScriptExecutor with skill's constraints
        constraints = ExecutionConstraints(
            max_execution_time=metadata.max_execution_time or 300,
            max_memory=metadata.max_memory,
            network_access=metadata.network_access,
            working_directory=skill_directory,
        )

        script_executor = ScriptExecutor(
            skill_name=skill_name,
            skill_directory=skill_directory,
            allowed_tools=metadata.allowed_tools,
            constraints=constraints,
        )

        # Create bash tool with ScriptExecutor
        bash_tool = create_bash_tool_with_skill_executor(script_executor)
        tools.append(bash_tool)

        # Create file I/O tools scoped to skill directory
        read_tool = create_read_file_tool(str(skill_directory))
        write_tool = create_write_file_tool(str(skill_directory))
        tools.append(read_tool)
        tools.append(write_tool)

        return tools

    def _create_universal_bash_tool(
        self, session_id: str
    ) -> Callable[[str, Optional[str]], str]:
        """
        Create a universal bash_tool that works with the currently active skill.

        This tool checks if a skill with scripts is active and uses its ScriptExecutor.

        Args:
            session_id: Session ID for context lookup

        Returns:
            Callable bash_tool function
        """
        conversation_manager = self.conversation_manager

        def bash_tool(command: str, working_directory: Optional[str] = None) -> str:
            """Execute a bash command using the active skill's permissions.

            IMPORTANT: Only works when a skill with scripts is active.
            Commands are restricted by the skill's allowed-tools permissions.

            Args:
                command: The bash command to execute
                working_directory: Optional working directory (relative to skill directory)

            Returns:
                Command output or error message
            """
            # Get conversation state
            state = conversation_manager.get_conversation(session_id)
            if not state:
                return "Error: No active session. Activate a skill first."

            # Check if there's an active skill
            if not state.active_skills:
                return "Error: No skill is currently active. Activate a skill with scripts before using bash_tool."

            # Get the active skill name
            active_skill = state.active_skills[-1]  # Most recently activated

            # Create executor for this skill
            execution_tools = self._create_execution_tools_for_skill(active_skill)
            if not execution_tools:
                return f"Error: Skill '{active_skill}' does not have scripts directory. Cannot execute commands."

            # Use the bash tool (first in list)
            bash_executor = execution_tools[0]
            return bash_executor(command, working_directory)

        return bash_tool

    def _create_universal_read_file_tool(self, session_id: str) -> Callable[[str], str]:
        """
        Create a universal read_file tool that works with the currently active skill.

        Args:
            session_id: Session ID for context lookup

        Returns:
            Callable read_file function
        """
        conversation_manager = self.conversation_manager

        def read_file(file_path: str) -> str:
            """Read a file from the active skill's directory.

            Args:
                file_path: Relative path to file from skill directory

            Returns:
                File contents or error message
            """
            # Get conversation state
            state = conversation_manager.get_conversation(session_id)
            if not state:
                return "Error: No active session. Activate a skill first."

            # Check if there's an active skill
            if not state.active_skills:
                return "Error: No skill is currently active. Activate a skill before using read_file."

            # Get the active skill name
            active_skill = state.active_skills[-1]

            # Create executor for this skill
            execution_tools = self._create_execution_tools_for_skill(active_skill)
            if not execution_tools or len(execution_tools) < 2:
                return f"Error: Skill '{active_skill}' does not have file I/O tools."

            # Use the read_file tool (second in list)
            read_executor = execution_tools[1]
            return read_executor(file_path)

        return read_file

    def _create_universal_write_file_tool(
        self, session_id: str
    ) -> Callable[[str, str], str]:
        """
        Create a universal write_file tool that works with the currently active skill.

        Args:
            session_id: Session ID for context lookup

        Returns:
            Callable write_file function
        """
        conversation_manager = self.conversation_manager

        def write_file(file_path: str, content: str) -> str:
            """Write content to a file in the active skill's directory.

            Args:
                file_path: Relative path to file from skill directory
                content: Content to write

            Returns:
                Success message or error
            """
            # Get conversation state
            state = conversation_manager.get_conversation(session_id)
            if not state:
                return "Error: No active session. Activate a skill first."

            # Check if there's an active skill
            if not state.active_skills:
                return "Error: No skill is currently active. Activate a skill before using write_file."

            # Get the active skill name
            active_skill = state.active_skills[-1]

            # Create executor for this skill
            execution_tools = self._create_execution_tools_for_skill(active_skill)
            if not execution_tools or len(execution_tools) < 3:
                return f"Error: Skill '{active_skill}' does not have file I/O tools."

            # Use the write_file tool (third in list)
            write_executor = execution_tools[2]
            return write_executor(file_path, content)

        return write_file


class SkillEnabledAgent:
    """
    High-level agent interface for skill-enabled conversations.

    Provides a simple API for interacting with the agent:
    - chat(): Send messages and get responses
    - get_active_skills(): Check which skills are active
    """

    def __init__(
        self,
        builder: AgentBuilder,
        adapter: "BaseLLMAdapter",
        session_id: str,
        system_prompt: str,
    ):
        self._builder = builder
        self._adapter = adapter
        self._session_id = session_id
        self._system_prompt = system_prompt

    @property
    def session_id(self) -> str:
        """Get the session ID."""
        return self._session_id

    @property
    def active_skills(self) -> list[str]:
        """Get list of currently active skills."""
        return self._builder.get_active_skills(self._session_id)

    @property
    def available_skills(self) -> dict[str, str]:
        """Get available skills with descriptions."""
        return {
            name: meta.description
            for name, meta in self._builder.skill_meta_tool.skills_metadata.items()
        }

    async def chat(self, message: str) -> str:
        """
        Send a message and get a response.

        Handles message tracking automatically.

        Args:
            message: User message

        Returns:
            Agent response text

        Example:
            response = await agent.chat("Say hello in Spanish")
            print(response)
        """
        # Track user message
        self._builder.add_user_message(self._session_id, message)

        # Send to LLM
        response = await self._adapter.send_message(
            messages=self._builder.get_messages_for_api(self._session_id),
            system_prompt=self._system_prompt,
            tools=[],  # Tools registered with agent, not per-message
            session_id=self._session_id,
        )

        # Track assistant response
        if response.content:
            self._builder.add_assistant_message(self._session_id, response.content)

        return response.content or ""

    async def chat_stream(self, message: str) -> AsyncIterator[str]:
        """
        Send a message and stream the response.

        Note: Streaming support depends on adapter implementation.
        Falls back to non-streaming if not supported.

        Args:
            message: User message

        Yields:
            Response text chunks
        """
        # For now, fall back to non-streaming
        # TODO: Implement streaming when adapter supports it
        response = await self.chat(message)
        yield response
