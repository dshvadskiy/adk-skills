"""Integration tests for Google ADK adapter.

These tests verify the ADKAdapter implementation works correctly.
Tests that require actual ADK credentials are marked with @pytest.mark.adk_credentials.

To run credential-requiring tests:
    pytest tests/integration/test_adk_integration.py -m adk_credentials
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from skill_framework.agent import AgentBuilder
from skill_framework.integration.base_adapter import LLMResponse, ToolCall


# Only import ADKAdapter if google.adk is available
try:
    from skill_framework.integration.adk_adapter import ADKAdapter

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    ADKAdapter = None  # type: ignore


pytestmark = pytest.mark.skipif(not ADK_AVAILABLE, reason="google-adk not installed")


@pytest.fixture
def skills_dir() -> Path:
    """Path to test skills directory."""
    return Path(__file__).parent.parent.parent / "skills"


@pytest.fixture
def adk_adapter() -> "ADKAdapter":
    """Create ADK adapter instance."""
    return ADKAdapter(model="gemini-2.5-flash", app_name="test_app")


class TestADKAdapterBasics:
    """Basic unit tests for ADKAdapter that don't require credentials."""

    def test_adapter_initialization(self, adk_adapter: "ADKAdapter") -> None:
        """Test adapter initializes with correct defaults."""
        assert adk_adapter.model == "gemini-2.5-flash"
        assert adk_adapter.app_name == "test_app"
        assert adk_adapter.agent is None
        assert adk_adapter.runner is None

    def test_format_tools_passthrough(self, adk_adapter: "ADKAdapter") -> None:
        """Test format_tools returns tools as-is."""
        tools = [
            {"name": "test_tool", "description": "A test tool"},
            {"name": "other_tool", "description": "Another tool"},
        ]
        formatted = adk_adapter.format_tools(tools)
        assert formatted == tools

    def test_format_tool_result(self, adk_adapter: "ADKAdapter") -> None:
        """Test tool result formatting."""
        result = adk_adapter.format_tool_result(
            tool_call_id="call_123",
            result={"success": True, "data": "test"},
        )

        assert result["type"] == "function_response"
        assert result["id"] == "call_123"
        assert result["response"] == {"success": True, "data": "test"}

    def test_get_latest_user_message_string(self, adk_adapter: "ADKAdapter") -> None:
        """Test extracting latest user message from string content."""
        messages = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "Response"},
            {"role": "user", "content": "Latest message"},
        ]
        result = adk_adapter._get_latest_user_message(messages)
        assert result == "Latest message"

    def test_get_latest_user_message_structured(
        self, adk_adapter: "ADKAdapter"
    ) -> None:
        """Test extracting latest user message from structured content."""
        messages = [
            {
                "role": "user",
                "content": [{"text": "Part 1"}, {"text": "Part 2"}],
            },
        ]
        result = adk_adapter._get_latest_user_message(messages)
        assert result == "Part 1 Part 2"

    def test_get_latest_user_message_empty(self, adk_adapter: "ADKAdapter") -> None:
        """Test extracting message when no user messages exist."""
        messages = [
            {"role": "assistant", "content": "Only assistant"},
        ]
        result = adk_adapter._get_latest_user_message(messages)
        assert result is None

    def test_register_tool_handler(self, adk_adapter: "ADKAdapter") -> None:
        """Test tool handler registration."""

        def my_handler(args: dict) -> str:
            return "result"

        adk_adapter.register_tool_handler("my_tool", my_handler)
        assert "my_tool" in adk_adapter._tool_handlers
        assert adk_adapter._tool_handlers["my_tool"] == my_handler


class TestADKAdapterWithMocks:
    """Tests using mocked ADK components."""

    @pytest.mark.asyncio
    async def test_send_message_creates_agent_if_needed(
        self, adk_adapter: "ADKAdapter"
    ) -> None:
        """Test that send_message creates agent on first call."""
        # Mock the ADK components
        mock_agent = MagicMock()
        mock_runner = MagicMock()

        # Mock session service
        mock_session_service = MagicMock()
        mock_session_service.create_session = AsyncMock()
        mock_runner.session_service = mock_session_service

        # Create async generator for run_async
        async def mock_run_async(*args, **kwargs):
            # Yield a final response event
            event = MagicMock()
            event.is_final_response.return_value = True
            event.content = MagicMock()
            event.content.parts = [MagicMock(text="Hello from ADK")]
            event.get_function_calls = MagicMock(return_value=[])
            yield event

        mock_runner.run_async = mock_run_async

        with patch(
            "skill_framework.integration.adk_adapter.Agent", return_value=mock_agent
        ), patch(
            "skill_framework.integration.adk_adapter.InMemoryRunner",
            return_value=mock_runner,
        ):
            response = await adk_adapter.send_message(
                messages=[{"role": "user", "content": "Hello"}],
                system_prompt="You are helpful.",
                tools=[],
                agent_name="test_agent",
            )

            assert response.content == "Hello from ADK"
            assert response.stop_reason == "end_turn"
            # Verify session was created
            mock_session_service.create_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_handles_tool_calls(
        self, adk_adapter: "ADKAdapter"
    ) -> None:
        """Test that send_message correctly extracts tool calls."""
        mock_agent = MagicMock()
        mock_runner = MagicMock()

        # Mock session service
        mock_session_service = MagicMock()
        mock_session_service.create_session = AsyncMock()
        mock_runner.session_service = mock_session_service

        # Create a mock function call
        mock_function_call = MagicMock()
        mock_function_call.name = "test_tool"
        mock_function_call.args = {"param": "value"}

        async def mock_run_async(*args, **kwargs):
            event = MagicMock()
            event.is_final_response.return_value = False
            event.content = MagicMock()
            event.content.parts = []
            event.get_function_calls = MagicMock(return_value=[mock_function_call])
            yield event

        mock_runner.run_async = mock_run_async

        with patch(
            "skill_framework.integration.adk_adapter.Agent", return_value=mock_agent
        ), patch(
            "skill_framework.integration.adk_adapter.InMemoryRunner",
            return_value=mock_runner,
        ):
            response = await adk_adapter.send_message(
                messages=[{"role": "user", "content": "Use a tool"}],
                system_prompt="You are helpful.",
                tools=[],
            )

            assert response.has_tool_calls
            assert len(response.tool_calls) == 1
            assert response.tool_calls[0].name == "test_tool"
            assert response.tool_calls[0].input == {"param": "value"}
            assert response.stop_reason == "tool_use"

    @pytest.mark.asyncio
    async def test_send_message_no_user_message(
        self, adk_adapter: "ADKAdapter"
    ) -> None:
        """Test send_message handles missing user message gracefully."""
        response = await adk_adapter.send_message(
            messages=[{"role": "assistant", "content": "Only assistant"}],
            system_prompt="You are helpful.",
            tools=[],
        )

        assert response.content == "No user message found"
        assert response.stop_reason == "error"

    def test_format_messages_converts_to_adk(self, adk_adapter: "ADKAdapter") -> None:
        """Test message formatting to ADK Content objects."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        with patch("skill_framework.integration.adk_adapter.types") as mock_types:
            mock_types.Content = MagicMock()
            mock_types.Part = MagicMock()

            adk_adapter.format_messages(messages)

            # Verify Content was created for each message
            assert mock_types.Content.call_count == 2


class TestADKAdapterWithAgentBuilder:
    """Tests for ADKAdapter integration with AgentBuilder."""

    @pytest.mark.asyncio
    async def test_builder_with_adk_adapter(
        self, skills_dir: Path, adk_adapter: "ADKAdapter"
    ) -> None:
        """Test AgentBuilder works with ADKAdapter."""
        builder = AgentBuilder(skills_directory=skills_dir)
        session_id = builder.create_session("test-session")

        # Get system prompt and tools
        system_prompt = builder.build_system_prompt("You are a helpful assistant.")
        tools = builder.get_tools()

        # Verify skill meta-tool is included
        tool_names = [t.get("name") for t in tools]
        assert "Skill" in tool_names

        # Verify system prompt includes skill info
        assert "hello-world" in system_prompt
        assert "Available Skills" in system_prompt

    @pytest.mark.asyncio
    async def test_skill_activation_with_adk(self, skills_dir: Path) -> None:
        """Test skill activation flow with ADK adapter."""
        builder = AgentBuilder(skills_directory=skills_dir)
        session_id = builder.create_session("test-session")

        # Activate skill directly
        result = await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id=session_id,
        )

        assert result.success
        assert result.skill_name == "hello-world"

        # Verify messages were injected
        messages = builder.get_messages_for_api(session_id)
        assert len(messages) == 2  # metadata + instructions

        # Verify first message is visible metadata
        assert "<command-message>" in messages[0]["content"]

        # Verify second message has skill instructions
        assert "hello-world" in messages[1]["content"].lower()


@pytest.mark.adk_credentials
@pytest.mark.skip(reason="Requires ADK credentials - run with: pytest -m adk_credentials")
class TestADKAdapterLive:
    """Live tests requiring actual ADK credentials.

    These tests are skipped by default. Run with:
        pytest tests/integration/test_adk_integration.py -m adk_credentials --no-skip

    Requires:
        - GOOGLE_API_KEY or GOOGLE_APPLICATION_CREDENTIALS environment variable
        - Network access to Google APIs
    """

    @pytest.mark.asyncio
    async def test_live_agent_creation(self) -> None:
        """Test creating a real ADK agent."""
        adapter = ADKAdapter(model="gemini-2.5-flash")

        def greet(name: str) -> str:
            """Greet a person by name."""
            return f"Hello, {name}!"

        agent = adapter.create_agent(
            name="greeter",
            instruction="You are a friendly greeter. Use the greet tool when asked.",
            description="A simple greeting agent",
            tools=[greet],
        )

        assert agent is not None
        assert adapter.runner is not None

    @pytest.mark.asyncio
    async def test_live_conversation(self) -> None:
        """Test a real conversation with ADK agent."""
        adapter = ADKAdapter(model="gemini-2.5-flash")

        def get_time() -> str:
            """Get the current time."""
            from datetime import datetime

            return datetime.now().strftime("%H:%M:%S")

        adapter.create_agent(
            name="time_agent",
            instruction="You can tell the time using the get_time tool.",
            tools=[get_time],
        )

        response = await adapter.send_message(
            messages=[{"role": "user", "content": "What time is it?"}],
            system_prompt="You can tell the time.",
            tools=[],
            user_id="test_user",
            session_id="test_session",
        )

        # Should get either a text response or a tool call
        assert response.content is not None or response.has_tool_calls

    @pytest.mark.asyncio
    async def test_live_skill_activation_flow(self, skills_dir: Path) -> None:
        """Test complete skill activation with live ADK."""
        adapter = ADKAdapter(model="gemini-2.5-flash")
        builder = AgentBuilder(skills_directory=skills_dir)

        session_id = builder.create_session("live-test")
        system_prompt = builder.build_system_prompt("You are a helpful assistant.")

        # Create a simple skill handler tool
        async def skill_tool(skill_name: str) -> dict:
            result = await builder.handle_skill_activation(
                skill_name=skill_name,
                session_id=session_id,
            )
            return {"success": result.success, "skill": result.skill_name}

        adapter.create_agent(
            name="skill_agent",
            instruction=system_prompt,
            tools=[skill_tool],
        )

        # Add user message
        builder.add_user_message(session_id, "Activate the hello-world skill")

        response = await adapter.send_message(
            messages=builder.get_messages_for_api(session_id),
            system_prompt=system_prompt,
            tools=[],
            user_id="test_user",
            session_id=session_id,
        )

        # The agent should respond in some way
        assert response.content is not None or response.has_tool_calls
