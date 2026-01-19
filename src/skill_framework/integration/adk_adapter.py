"""Google ADK adapter for LLM integration."""

from collections.abc import AsyncIterator
from typing import Any, Optional, Union

from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from .base_adapter import BaseLLMAdapter, LLMResponse, ToolCall

# Type alias for ADK-compatible models
# Can be a string (Gemini model ID) or any ADK model wrapper (LiteLlm, Ollama, etc.)
ADKModel = Union[str, Any]


class ADKAdapter(BaseLLMAdapter):
    """
    Google ADK adapter implementing BaseLLMAdapter.

    Integrates with Google's Agent Development Kit for:
    - Agent creation and configuration with any ADK-compatible model
    - Tool registration in ADK format
    - Conversation handling via InMemoryRunner
    - Event processing and response normalization
    - Streaming response support

    The adapter is model-agnostic - it accepts any ADK-compatible model:
    - String for native Gemini models ("gemini-2.0-flash")
    - LiteLlm wrapper for OpenAI, Anthropic, Bedrock, etc.
    - Ollama wrapper for local models
    - Any other ADK-compatible model instance

    Usage:
        # Native Gemini
        adapter = ADKAdapter(model="gemini-2.0-flash")

        # OpenAI via LiteLLM
        from google.adk.models.lite_llm import LiteLlm
        adapter = ADKAdapter(model=LiteLlm(model="openai/gpt-4o"))

        # Anthropic Claude via LiteLLM
        adapter = ADKAdapter(model=LiteLlm(model="anthropic/claude-3-5-sonnet-20241022"))

        # Amazon Bedrock via LiteLLM
        adapter = ADKAdapter(model=LiteLlm(model="bedrock/anthropic.claude-3-sonnet-20240229-v1:0"))

        # Local Ollama
        from google.adk.models.ollama import Ollama
        adapter = ADKAdapter(model=Ollama(model="llama3.2:latest"))

        # Send message
        response = await adapter.send_message(
            messages=[{"role": "user", "content": "Hello"}],
            system_prompt="You are helpful.",
            tools=[...]
        )

        # Streaming
        async for chunk in adapter.send_message_streaming(...):
            if chunk.is_streaming:
                print(chunk.content, end="")
    """

    def __init__(
        self,
        model: ADKModel = "gemini-2.0-flash",
        app_name: str = "skill_framework",
    ):
        """
        Initialize ADK adapter with any ADK-compatible model.

        Args:
            model: ADK-compatible model - can be:
                   - str: Gemini model ID ("gemini-2.0-flash", "gemini-2.5-pro")
                   - LiteLlm: LiteLLM wrapper for OpenAI, Anthropic, Bedrock, Azure, etc.
                   - Ollama: Local Ollama model wrapper
                   - Any other ADK-compatible model instance
            app_name: Application name for the runner
        """
        self.model = model
        self.app_name = app_name
        self._agent: Optional[Agent] = None
        self._runner: Optional[InMemoryRunner] = None
        self._tool_handlers: dict[str, Any] = {}
        self._sessions: set[str] = set()  # Track created sessions

    def create_agent(
        self,
        name: str,
        instruction: str,
        description: str = "",
        tools: Optional[list[Any]] = None,
    ) -> Agent:
        """
        Create an ADK Agent instance.

        Args:
            name: Agent name
            instruction: System instruction for the agent
            description: Agent description
            tools: List of tool functions or FunctionTool instances

        Returns:
            Configured Agent instance
        """
        self._agent = Agent(
            name=name,
            model=self.model,
            instruction=instruction,
            description=description or f"{name} agent",
            tools=tools or [],
        )
        self._runner = InMemoryRunner(
            agent=self._agent,
            app_name=self.app_name,
        )
        self._sessions.clear()  # Reset sessions on new agent
        return self._agent

    async def ensure_session(self, user_id: str, session_id: str) -> None:
        """
        Ensure a session exists for the given user and session IDs.

        ADK requires sessions to be created before run_async.

        Args:
            user_id: User identifier
            session_id: Session identifier
        """
        if self._runner is None:
            return

        session_key = f"{user_id}:{session_id}"
        if session_key in self._sessions:
            return

        # Create session using runner's session service
        session_service = self._runner.session_service
        await session_service.create_session(
            app_name=self.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        self._sessions.add(session_key)

    def register_tool_handler(self, name: str, handler: Any) -> None:
        """
        Register a tool handler function.

        ADK tools are typically Python functions that get called directly.
        This method stores handlers for manual tool execution if needed.

        Args:
            name: Tool name
            handler: Callable that handles tool invocations
        """
        self._tool_handlers[name] = handler

    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        user_id: str = "default_user",
        session_id: str = "default_session",
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send messages to ADK agent and get response.

        This method handles the complete conversation turn:
        1. Creates/updates agent if needed
        2. Sends the latest user message
        3. Processes events from the runner
        4. Returns normalized LLMResponse

        Args:
            messages: Conversation history
            system_prompt: System instruction (used if agent needs creation)
            tools: Tool definitions (used for agent creation)
            user_id: User identifier for the session
            session_id: Session identifier
            **kwargs: Additional options (e.g., agent_name, description)

        Returns:
            Standardized LLMResponse
        """
        # Ensure agent exists
        if self._agent is None or self._runner is None:
            agent_name = kwargs.get("agent_name", "skill_agent")
            description = kwargs.get("description", "")
            tool_functions = kwargs.get("tool_functions", [])

            self.create_agent(
                name=agent_name,
                instruction=system_prompt,
                description=description,
                tools=tool_functions,
            )

        # Ensure session exists (ADK requires this before run_async)
        await self.ensure_session(user_id, session_id)

        # Get the latest user message
        latest_message = self._get_latest_user_message(messages)
        if not latest_message:
            return LLMResponse(
                content="No user message found",
                stop_reason="error",
            )

        # Create ADK content from message
        adk_content = types.Content(
            role="user",
            parts=[types.Part(text=latest_message)],
        )

        # Run agent and collect response
        response_text = ""
        tool_calls: list[ToolCall] = []
        raw_events: list[Any] = []

        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=adk_content,
        ):
            raw_events.append(event)

            # Process tool calls
            if event.content and hasattr(event, "get_function_calls"):
                function_calls = event.get_function_calls()
                if function_calls:
                    for fc in function_calls:
                        tool_calls.append(
                            ToolCall(
                                id=getattr(fc, "id", f"call_{len(tool_calls)}"),
                                name=fc.name,
                                input=dict(fc.args) if fc.args else {},
                            )
                        )

            # Process final response
            if event.is_final_response() and event.content:
                if event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            response_text += part.text

        return LLMResponse(
            content=response_text if response_text else None,
            tool_calls=tool_calls,
            stop_reason="end_turn" if not tool_calls else "tool_use",
            raw_response=raw_events,
        )

    async def send_message_streaming(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        user_id: str = "default_user",
        session_id: str = "default_session",
        **kwargs: Any,
    ) -> AsyncIterator[LLMResponse]:
        """
        Stream responses from ADK agent.

        Yields intermediate LLMResponse chunks as they arrive from the model,
        with is_streaming=True. The final chunk has is_streaming=False and
        contains tool_calls if any were made.

        Args:
            messages: Conversation history
            system_prompt: System instruction (used if agent needs creation)
            tools: Tool definitions (used for agent creation)
            user_id: User identifier for the session
            session_id: Session identifier
            **kwargs: Additional options (e.g., agent_name, description)

        Yields:
            LLMResponse chunks - intermediate chunks have is_streaming=True,
            final chunk has is_streaming=False with stop_reason set.
        """
        # Ensure agent exists (lazy initialization)
        if self._agent is None or self._runner is None:
            agent_name = kwargs.get("agent_name", "skill_agent")
            description = kwargs.get("description", "")
            tool_functions = kwargs.get("tool_functions", [])

            self.create_agent(
                name=agent_name,
                instruction=system_prompt,
                description=description,
                tools=tool_functions,
            )

        # Ensure session exists (ADK requires this before run_async)
        await self.ensure_session(user_id, session_id)

        # Get the latest user message
        latest_message = self._get_latest_user_message(messages)
        if not latest_message:
            yield LLMResponse(
                content="No user message found",
                stop_reason="error",
                is_streaming=False,
            )
            return

        # Create ADK content from message
        adk_content = types.Content(
            role="user",
            parts=[types.Part(text=latest_message)],
        )

        # Track tool calls across events
        tool_calls: list[ToolCall] = []

        async for event in self._runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=adk_content,
        ):
            # Collect tool calls
            if event.content and hasattr(event, "get_function_calls"):
                function_calls = event.get_function_calls()
                if function_calls:
                    for fc in function_calls:
                        tool_calls.append(
                            ToolCall(
                                id=getattr(fc, "id", f"call_{len(tool_calls)}"),
                                name=fc.name,
                                input=dict(fc.args) if fc.args else {},
                            )
                        )

            # Yield intermediate content chunks
            if event.content and event.content.parts and not event.is_final_response():
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        yield LLMResponse(
                            content=part.text,
                            is_streaming=True,
                        )

            # Final response
            if event.is_final_response():
                final_content = None
                if event.content and event.content.parts:
                    text_parts = []
                    for part in event.content.parts:
                        if hasattr(part, "text") and part.text:
                            text_parts.append(part.text)
                    if text_parts:
                        final_content = "".join(text_parts)

                yield LLMResponse(
                    content=final_content,
                    tool_calls=tool_calls,
                    stop_reason="end_turn" if not tool_calls else "tool_use",
                    is_streaming=False,
                )

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
    ) -> dict[str, Any]:
        """
        Format tool result for ADK.

        ADK handles tool results internally through function return values.
        This method provides a compatible format for manual handling.

        Args:
            tool_call_id: ID of the tool call
            result: Tool execution result

        Returns:
            Formatted tool result
        """
        return {
            "type": "function_response",
            "id": tool_call_id,
            "response": result,
        }

    def format_tools(
        self,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Format tool definitions for ADK.

        ADK tools are typically Python functions with docstrings.
        This method converts standard tool definitions to ADK format.

        Note: For actual ADK usage, prefer passing callable functions
        directly to Agent(tools=[...]) rather than definitions.

        Args:
            tools: Tool definitions in standard format

        Returns:
            Tool definitions (ADK uses functions directly)
        """
        # ADK prefers actual callable functions over definitions
        # Return as-is for compatibility, but recommend using
        # tool_functions parameter in send_message
        return tools

    def format_messages(
        self,
        messages: list[dict[str, Any]],
    ) -> list[types.Content]:
        """
        Format messages for ADK Content format.

        Args:
            messages: Messages in standard format

        Returns:
            Messages as ADK Content objects
        """
        adk_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Map roles to ADK format
            adk_role = "user" if role == "user" else "model"

            # Create Content object
            adk_content = types.Content(
                role=adk_role,
                parts=[types.Part(text=content)] if isinstance(content, str) else [],
            )
            adk_messages.append(adk_content)

        return adk_messages

    def _get_latest_user_message(
        self,
        messages: list[dict[str, Any]],
    ) -> Optional[str]:
        """
        Extract the latest user message from conversation.

        Args:
            messages: Conversation history

        Returns:
            Latest user message content or None
        """
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    return content
                # Handle structured content (e.g., list of parts)
                if isinstance(content, list):
                    texts = [
                        p.get("text", "")
                        for p in content
                        if isinstance(p, dict) and "text" in p
                    ]
                    return " ".join(texts)
        return None

    @property
    def agent(self) -> Optional[Agent]:
        """Get the current ADK Agent instance."""
        return self._agent

    @property
    def runner(self) -> Optional[InMemoryRunner]:
        """Get the current InMemoryRunner instance."""
        return self._runner
