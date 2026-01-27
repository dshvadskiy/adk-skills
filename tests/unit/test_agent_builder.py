"""Unit tests for AgentBuilder."""

from pathlib import Path

import pytest

from skill_framework.agent import AgentBuilder


@pytest.fixture
def skills_dir() -> Path:
    """Path to test skills directory."""
    return Path(__file__).parent.parent.parent / "skills"


@pytest.fixture
def builder(skills_dir: Path) -> AgentBuilder:
    """Create AgentBuilder instance with test skills."""
    return AgentBuilder(skills_directory=skills_dir)


class TestAgentBuilderInit:
    """Tests for AgentBuilder initialization."""

    def test_init_creates_skill_meta_tool(self, builder: AgentBuilder) -> None:
        """AgentBuilder creates SkillMetaTool instance."""
        assert builder.skill_meta_tool is not None

    def test_init_creates_tool_registry(self, builder: AgentBuilder) -> None:
        """AgentBuilder creates ToolRegistry instance."""
        assert builder.tool_registry is not None

    def test_init_creates_conversation_manager(self, builder: AgentBuilder) -> None:
        """AgentBuilder creates ConversationManager instance."""
        assert builder.conversation_manager is not None

    def test_init_registers_skill_meta_tool(self, builder: AgentBuilder) -> None:
        """AgentBuilder registers Skill meta-tool in registry."""
        assert builder.tool_registry.has_tool("Skill")

    def test_init_with_cache_disabled(self, skills_dir: Path) -> None:
        """AgentBuilder can be created with cache disabled."""
        builder = AgentBuilder(skills_directory=skills_dir, enable_cache=False)
        assert builder.skill_meta_tool.cache_enabled is False


class TestRegisterTool:
    """Tests for tool registration."""

    def test_register_tool_adds_to_registry(self, builder: AgentBuilder) -> None:
        """register_tool adds tool definition to registry."""
        tool_def = {
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {"type": "object", "properties": {}},
        }
        builder.register_tool("test_tool", tool_def)
        assert builder.tool_registry.has_tool("test_tool")

    def test_register_tool_returns_self(self, builder: AgentBuilder) -> None:
        """register_tool returns self for method chaining."""
        tool_def = {"name": "test_tool", "description": "Test"}
        result = builder.register_tool("test_tool", tool_def)
        assert result is builder

    def test_register_tool_with_handler(self, builder: AgentBuilder) -> None:
        """register_tool stores handler function."""

        async def handler(inputs, context):
            return "result"

        builder.register_tool("test_tool", {"name": "test_tool"}, handler=handler)
        assert "test_tool" in builder._tool_handlers

    def test_method_chaining(self, builder: AgentBuilder) -> None:
        """Multiple tools can be registered via chaining."""
        builder.register_tool("tool1", {"name": "tool1"}).register_tool(
            "tool2", {"name": "tool2"}
        ).register_tool("tool3", {"name": "tool3"})

        assert builder.tool_registry.has_tool("tool1")
        assert builder.tool_registry.has_tool("tool2")
        assert builder.tool_registry.has_tool("tool3")


class TestBuildSystemPrompt:
    """Tests for system prompt construction."""

    def test_includes_base_instruction(self, builder: AgentBuilder) -> None:
        """System prompt includes base instruction."""
        base = "You are a helpful assistant."
        prompt = builder.build_system_prompt(base)
        assert base in prompt

    def test_includes_skills_section(self, builder: AgentBuilder) -> None:
        """System prompt includes skills metadata section."""
        prompt = builder.build_system_prompt("Base instruction")
        assert "Available Skills" in prompt

    def test_includes_tool_usage_section(self, builder: AgentBuilder) -> None:
        """System prompt includes tool usage guidelines."""
        prompt = builder.build_system_prompt("Base instruction")
        assert "Tool Usage" in prompt

    def test_skills_section_contains_hello_world(self, builder: AgentBuilder) -> None:
        """System prompt lists hello-world skill."""
        prompt = builder.build_system_prompt("Base instruction")
        assert "hello-world" in prompt


class TestGetTools:
    """Tests for tool collection."""

    def test_includes_skill_meta_tool(self, builder: AgentBuilder) -> None:
        """get_tools includes Skill meta-tool."""
        tools = builder.get_tools()
        skill_tool = next((t for t in tools if t.get("name") == "Skill"), None)
        assert skill_tool is not None

    def test_includes_registered_tools(self, builder: AgentBuilder) -> None:
        """get_tools includes all registered tools."""
        builder.register_tool("custom_tool", {"name": "custom_tool"})
        tools = builder.get_tools()
        custom_tool = next((t for t in tools if t.get("name") == "custom_tool"), None)
        assert custom_tool is not None

    def test_includes_additional_tools(self, builder: AgentBuilder) -> None:
        """get_tools includes additional tools parameter."""
        additional = [{"name": "extra_tool", "description": "Extra"}]
        tools = builder.get_tools(additional_tools=additional)
        extra_tool = next((t for t in tools if t.get("name") == "extra_tool"), None)
        assert extra_tool is not None

    def test_empty_additional_tools(self, builder: AgentBuilder) -> None:
        """get_tools works with None additional_tools."""
        tools = builder.get_tools(additional_tools=None)
        assert len(tools) >= 1  # At least Skill meta-tool


class TestSessionManagement:
    """Tests for session/conversation management."""

    def test_create_session(self, builder: AgentBuilder) -> None:
        """create_session creates conversation state."""
        session_id = builder.create_session("test-session-1")
        assert session_id == "test-session-1"
        assert (
            builder.conversation_manager.get_conversation("test-session-1") is not None
        )

    def test_add_user_message(self, builder: AgentBuilder) -> None:
        """add_user_message adds to conversation."""
        builder.create_session("session-1")
        builder.add_user_message("session-1", "Hello")
        messages = builder.get_messages_for_api("session-1")
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"

    def test_add_assistant_message(self, builder: AgentBuilder) -> None:
        """add_assistant_message adds to conversation."""
        builder.create_session("session-1")
        builder.add_user_message("session-1", "Hello")
        builder.add_assistant_message("session-1", "Hi there!")
        messages = builder.get_messages_for_api("session-1")
        assert len(messages) == 2
        assert messages[1]["content"] == "Hi there!"

    def test_get_messages_for_api(self, builder: AgentBuilder) -> None:
        """get_messages_for_api returns formatted messages."""
        builder.create_session("session-1")
        builder.add_user_message("session-1", "Test message")
        messages = builder.get_messages_for_api("session-1")
        assert messages[0] == {"role": "user", "content": "Test message"}


class TestSkillActivation:
    """Tests for skill activation handling."""

    @pytest.mark.asyncio
    async def test_handle_skill_activation_success(self, builder: AgentBuilder) -> None:
        """handle_skill_activation activates valid skill."""
        builder.create_session("session-1")
        result = await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        assert result.success is True
        assert result.skill_name == "hello-world"

    @pytest.mark.asyncio
    async def test_handle_skill_activation_injects_messages(
        self, builder: AgentBuilder
    ) -> None:
        """handle_skill_activation injects two-message pattern."""
        builder.create_session("session-1")
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        messages = builder.get_messages_for_api("session-1")
        # Should have metadata message + instruction message
        assert len(messages) == 2

    @pytest.mark.asyncio
    async def test_handle_skill_activation_tracks_active_skill(
        self, builder: AgentBuilder
    ) -> None:
        """handle_skill_activation marks skill as active."""
        builder.create_session("session-1")
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        active = builder.get_active_skills("session-1")
        assert "hello-world" in active

    @pytest.mark.asyncio
    async def test_handle_skill_activation_invalid_skill(
        self, builder: AgentBuilder
    ) -> None:
        """handle_skill_activation fails for invalid skill."""
        builder.create_session("session-1")
        result = await builder.handle_skill_activation(
            skill_name="nonexistent-skill",
            session_id="session-1",
        )
        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_handle_skill_activation_updates_context(
        self, builder: AgentBuilder
    ) -> None:
        """handle_skill_activation updates conversation context."""
        builder.create_session("session-1")
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        state = builder.conversation_manager.get_conversation("session-1")
        assert state.context.get("active_skill") == "hello-world"


class TestToolCallHandling:
    """Tests for tool call routing."""

    @pytest.mark.asyncio
    async def test_handle_tool_call_skill(self, builder: AgentBuilder) -> None:
        """handle_tool_call routes Skill calls correctly."""
        builder.create_session("session-1")
        result = await builder.handle_tool_call(
            tool_name="Skill",
            tool_input={"skill_name": "hello-world"},
            session_id="session-1",
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_handle_tool_call_custom_handler(self, builder: AgentBuilder) -> None:
        """handle_tool_call routes to custom handler."""

        async def custom_handler(inputs, context):
            return {"result": inputs.get("value", 0) * 2}

        builder.register_tool(
            "double",
            {"name": "double", "description": "Double a value"},
            handler=custom_handler,
        )
        builder.create_session("session-1")

        result = await builder.handle_tool_call(
            tool_name="double",
            tool_input={"value": 5},
            session_id="session-1",
        )
        assert result == {"result": 10}

    @pytest.mark.asyncio
    async def test_handle_tool_call_unknown_tool(self, builder: AgentBuilder) -> None:
        """handle_tool_call raises for unknown tool."""
        builder.create_session("session-1")

        with pytest.raises(ValueError, match="No handler registered"):
            await builder.handle_tool_call(
                tool_name="unknown_tool",
                tool_input={},
                session_id="session-1",
            )


class TestSkillDeactivation:
    """Tests for skill deactivation."""

    @pytest.mark.asyncio
    async def test_deactivate_skill(self, builder: AgentBuilder) -> None:
        """deactivate_skill removes skill from active list."""
        builder.create_session("session-1")
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        assert "hello-world" in builder.get_active_skills("session-1")

        builder.deactivate_skill("session-1", "hello-world")
        assert "hello-world" not in builder.get_active_skills("session-1")

    @pytest.mark.asyncio
    async def test_deactivate_skill_removes_from_meta_tool(
        self, builder: AgentBuilder
    ) -> None:
        """deactivate_skill also deactivates in SkillMetaTool."""
        builder.create_session("session-1")
        await builder.handle_skill_activation(
            skill_name="hello-world",
            session_id="session-1",
        )
        assert builder.skill_meta_tool.is_skill_active("hello-world")

        builder.deactivate_skill("session-1", "hello-world")
        assert not builder.skill_meta_tool.is_skill_active("hello-world")
