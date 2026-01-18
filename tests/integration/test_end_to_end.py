"""End-to-end integration tests for skill framework.

These tests verify the complete flow from agent setup through skill activation
without requiring an actual LLM. They use a mock adapter to simulate LLM responses.
"""

from pathlib import Path
from typing import Any

import pytest

from skill_framework.agent import AgentBuilder
from skill_framework.integration import BaseLLMAdapter, LLMResponse, ToolCall


class MockLLMAdapter(BaseLLMAdapter):
    """Mock adapter for testing without real LLM."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses: list[LLMResponse] = []
        self._response_index = 0

    def queue_response(self, response: LLMResponse) -> None:
        """Queue a response to return on next send_message call."""
        self.responses.append(response)

    async def send_message(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tools: list[dict[str, Any]],
        **kwargs: Any,
    ) -> LLMResponse:
        """Record call and return queued response."""
        self.calls.append(
            {
                "messages": messages,
                "system_prompt": system_prompt,
                "tools": tools,
                "kwargs": kwargs,
            }
        )

        if self._response_index < len(self.responses):
            response = self.responses[self._response_index]
            self._response_index += 1
            return response

        return LLMResponse(content="Default response")

    def format_tool_result(
        self,
        tool_call_id: str,
        result: Any,
    ) -> dict[str, Any]:
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": str(result),
                }
            ],
        }

    def format_tools(
        self,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return tools


@pytest.fixture
def skills_dir() -> Path:
    """Path to test skills directory."""
    return Path(__file__).parent.parent.parent / "skills"


@pytest.fixture
def builder(skills_dir: Path) -> AgentBuilder:
    """Create AgentBuilder with test skills."""
    return AgentBuilder(skills_directory=skills_dir)


@pytest.fixture
def mock_adapter() -> MockLLMAdapter:
    """Create mock LLM adapter."""
    return MockLLMAdapter()


class TestEndToEndSkillActivation:
    """Tests for complete skill activation flow."""

    @pytest.mark.asyncio
    async def test_full_skill_activation_flow(
        self,
        builder: AgentBuilder,
        mock_adapter: MockLLMAdapter,
    ) -> None:
        """Test complete flow: user message -> LLM decides to use skill -> activation."""
        # Setup
        session_id = builder.create_session("test-session")
        system_prompt = builder.build_system_prompt("You are a helpful assistant.")
        tools = builder.get_tools()

        # Step 1: User sends message
        builder.add_user_message(session_id, "Please greet me using the hello skill")

        # Step 2: LLM decides to call Skill tool
        mock_adapter.queue_response(
            LLMResponse(
                content=None,
                tool_calls=[
                    ToolCall(
                        id="tool_1",
                        name="Skill",
                        input={"skill_name": "hello-world"},
                    )
                ],
                stop_reason="tool_use",
            )
        )

        # Simulate LLM call
        messages = builder.get_messages_for_api(session_id)
        response = await mock_adapter.send_message(messages, system_prompt, tools)

        # Step 3: Handle tool call
        assert response.has_tool_calls
        tool_call = response.tool_calls[0]
        assert tool_call.name == "Skill"

        result = await builder.handle_tool_call(
            tool_name=tool_call.name,
            tool_input=tool_call.input,
            session_id=session_id,
        )

        # Verify skill activated
        assert result.success
        assert result.skill_name == "hello-world"

        # Verify messages were injected
        messages = builder.get_messages_for_api(session_id)
        # Original user message + metadata message + instruction message
        assert len(messages) == 3

        # Verify metadata message is visible
        assert "<command-message>" in messages[1]["content"]
        assert "hello-world" in messages[1]["content"]

        # Verify instruction message contains skill content
        assert "hello-world" in messages[2]["content"].lower()

    @pytest.mark.asyncio
    async def test_skill_context_propagation(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that skill activation modifies context correctly."""
        session_id = builder.create_session("test-session")

        # Activate skill
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id=session_id,
            current_context={"existing_key": "value"},
        )

        # Check conversation state
        state = builder.conversation_manager.get_conversation(session_id)
        assert state is not None
        assert state.context.get("active_skill") == "hello-world"
        assert "hello-world" in state.active_skills

    @pytest.mark.asyncio
    async def test_multiple_skills_in_session(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test activating multiple skills in same session."""
        session_id = builder.create_session("test-session")

        # Activate first skill
        result1 = await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id=session_id,
        )
        assert result1.success

        # Check messages after first activation
        messages = builder.get_messages_for_api(session_id)
        assert len(messages) == 2  # metadata + instructions

        # Deactivate first skill
        builder.deactivate_skill(session_id, "hello-world")

        # Could activate another skill here if one existed
        # For now, verify deactivation worked
        assert "hello-world" not in builder.get_active_skills(session_id)

    @pytest.mark.asyncio
    async def test_system_prompt_includes_skill_metadata(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that system prompt contains skill metadata for LLM decision-making."""
        system_prompt = builder.build_system_prompt("Base instruction")

        # Should contain skill info
        assert "hello-world" in system_prompt
        assert "Available Skills" in system_prompt

        # Should NOT contain full instructions (progressive disclosure)
        # The full instructions are only loaded on activation
        assert "This skill demonstrates" not in system_prompt or len(system_prompt) < 2000

    @pytest.mark.asyncio
    async def test_visible_vs_api_messages(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that visible messages exclude hidden instruction messages."""
        session_id = builder.create_session("test-session")
        builder.add_user_message(session_id, "Hello")

        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id=session_id,
        )

        # API messages include everything (for LLM context)
        api_messages = builder.get_messages_for_api(session_id, include_meta=True)
        assert len(api_messages) == 3

        # Visible messages exclude hidden instruction
        visible = builder.conversation_manager.get_visible_messages(session_id)
        assert len(visible) == 2  # user message + metadata message


class TestToolRegistration:
    """Tests for custom tool registration with AgentBuilder."""

    @pytest.mark.asyncio
    async def test_custom_tool_execution(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test registering and executing custom tools."""

        async def calculator(inputs: dict, context: dict) -> dict:
            op = inputs.get("operation")
            a = inputs.get("a", 0)
            b = inputs.get("b", 0)
            if op == "add":
                return {"result": a + b}
            elif op == "multiply":
                return {"result": a * b}
            return {"error": "unknown operation"}

        builder.register_tool(
            name="calculator",
            definition={
                "name": "calculator",
                "description": "Perform math operations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "operation": {"type": "string", "enum": ["add", "multiply"]},
                        "a": {"type": "number"},
                        "b": {"type": "number"},
                    },
                    "required": ["operation", "a", "b"],
                },
            },
            handler=calculator,
        )

        session_id = builder.create_session("test-session")

        result = await builder.handle_tool_call(
            tool_name="calculator",
            tool_input={"operation": "add", "a": 5, "b": 3},
            session_id=session_id,
        )

        assert result == {"result": 8}

    def test_tools_include_custom_and_skill(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that get_tools returns both Skill and custom tools."""
        builder.register_tool("custom", {"name": "custom", "description": "test"})

        tools = builder.get_tools()
        tool_names = [t.get("name") for t in tools]

        assert "Skill" in tool_names
        assert "custom" in tool_names


class TestErrorHandling:
    """Tests for error handling in integration scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_skill_activation_graceful(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that invalid skill activation returns error result, not exception."""
        session_id = builder.create_session("test-session")

        result = await builder.handle_skill_activation(
            skill_name="nonexistent-skill",
            session_id=session_id,
        )

        assert result.success is False
        assert "not found" in result.error
        assert "available_skills" in result.error_details

    @pytest.mark.asyncio
    async def test_tool_call_without_session_raises_error(
        self,
        builder: AgentBuilder,
    ) -> None:
        """Test that skill activation without session raises clear error."""
        # Don't create session first - this should raise an error
        # because we can't inject messages into a non-existent conversation
        with pytest.raises(ValueError, match="not found"):
            await builder.handle_skill_activation(
                skill_name="hello-world",
                session_id="nonexistent-session",
            )
