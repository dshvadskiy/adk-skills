"""Tests for ConversationManager - conversation state and message history management."""

from datetime import datetime

import pytest

from skill_framework.agent import ConversationManager, ConversationState, Message


class TestMessage:
    """Test Message dataclass"""

    def test_message_creation(self):
        """Test creating a basic message"""
        msg = Message(
            role="user",
            content="Hello",
        )
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.isMeta is False
        assert isinstance(msg.timestamp, str)

    def test_message_with_metadata(self):
        """Test creating message with metadata"""
        msg = Message(
            role="assistant",
            content="Response",
            metadata={"key": "value"},
            isMeta=True,
        )
        assert msg.metadata == {"key": "value"}
        assert msg.isMeta is True

    def test_message_timestamp_format(self):
        """Test timestamp is ISO format"""
        msg = Message(role="user", content="test")
        assert datetime.fromisoformat(msg.timestamp.replace("Z", "+00:00"))


class TestConversationState:
    """Test ConversationState dataclass"""

    def test_state_creation(self):
        """Test creating conversation state"""
        state = ConversationState(session_id="test-session")
        assert state.session_id == "test-session"
        assert state.messages == []
        assert state.active_skills == []
        assert state.context == {}

    def test_state_with_messages(self):
        """Test state with messages"""
        msg = Message(role="user", content="Hello")
        state = ConversationState(
            session_id="test",
            messages=[msg],
            active_skills=["skill1"],
            context={"key": "value"},
        )
        assert len(state.messages) == 1
        assert state.active_skills == ["skill1"]
        assert state.context == {"key": "value"}


class TestConversationManager:
    """Test ConversationManager"""

    @pytest.fixture
    def manager(self):
        """Create ConversationManager instance"""
        return ConversationManager()

    def test_create_conversation(self, manager):
        """Test creating new conversation"""
        state = manager.create_conversation("session-1")
        assert state.session_id == "session-1"
        assert state in manager.conversations.values()

    def test_get_conversation(self, manager):
        """Test getting existing conversation"""
        manager.create_conversation("session-1")
        state = manager.get_conversation("session-1")
        assert state is not None
        assert state.session_id == "session-1"

    def test_get_nonexistent_conversation(self, manager):
        """Test getting nonexistent conversation returns None"""
        state = manager.get_conversation("nonexistent")
        assert state is None

    def test_add_user_message(self, manager):
        """Test adding user message"""
        manager.add_user_message("session-1", "Hello world")
        state = manager.get_conversation("session-1")
        assert state is not None
        assert len(state.messages) == 1
        assert state.messages[0].role == "user"
        assert state.messages[0].content == "Hello world"

    def test_add_user_message_with_metadata(self, manager):
        """Test adding user message with metadata"""
        manager.add_user_message(
            "session-1",
            "Hello",
            metadata={"user_id": "123"},
        )
        state = manager.get_conversation("session-1")
        assert state.messages[0].metadata == {"user_id": "123"}

    def test_add_user_message_creates_conversation(self, manager):
        """Test adding user message creates conversation if needed"""
        manager.add_user_message("new-session", "Test")
        state = manager.get_conversation("new-session")
        assert state is not None

    def test_add_assistant_message(self, manager):
        """Test adding assistant message"""
        manager.create_conversation("session-1")
        manager.add_assistant_message("session-1", "Response")
        state = manager.get_conversation("session-1")
        assert len(state.messages) == 1
        assert state.messages[0].role == "assistant"
        assert state.messages[0].content == "Response"

    def test_add_assistant_message_to_nonexistent_raises(self, manager):
        """Test adding assistant message to nonexistent conversation raises error"""
        with pytest.raises(ValueError, match="session-1 not found"):
            manager.add_assistant_message("session-1", "Response")

    def test_add_assistant_message_with_metadata(self, manager):
        """Test adding assistant message with metadata"""
        manager.create_conversation("session-1")
        manager.add_assistant_message(
            "session-1",
            "Response",
            metadata={"tokens": 10},
        )
        state = manager.get_conversation("session-1")
        assert state.messages[0].metadata == {"tokens": 10}

    def test_inject_skill_messages(self, manager):
        """Test injecting two-message pattern"""
        manager.create_conversation("session-1")
        metadata_message = {
            "role": "user",
            "content": "<command-message>Activating skill</command-message>",
            "metadata": {"type": "skill_activation"},
        }
        instruction_message = {
            "role": "user",
            "content": "Skill instructions",
            "metadata": {"type": "skill_instructions"},
        }

        manager.inject_skill_messages(
            "session-1", metadata_message, instruction_message
        )
        state = manager.get_conversation("session-1")

        assert len(state.messages) == 2
        assert state.messages[0].isMeta is False
        assert state.messages[1].isMeta is True
        assert "<command-message>" in state.messages[0].content
        assert "Skill instructions" in state.messages[1].content

    def test_inject_skill_messages_nonexistent_raises(self, manager):
        """Test injecting into nonexistent conversation raises error"""
        with pytest.raises(ValueError, match="session-1 not found"):
            manager.inject_skill_messages("session-1", {}, {})

    def test_get_messages_for_api(self, manager):
        """Test getting messages for API call"""
        manager.create_conversation("session-1")
        manager.add_user_message("session-1", "User msg")
        manager.add_assistant_message("session-1", "Assistant msg")

        messages = manager.get_messages_for_api("session-1")
        assert len(messages) == 2
        assert messages[0] == {"role": "user", "content": "User msg"}
        assert messages[1] == {"role": "assistant", "content": "Assistant msg"}

    def test_get_messages_for_api_excludes_meta(self, manager):
        """Test getting messages excludes meta when include_meta=False"""
        manager.create_conversation("session-1")
        manager.add_user_message("session-1", "Visible")
        msg = Message(role="user", content="Hidden", isMeta=True)
        state = manager.get_conversation("session-1")
        state.messages.append(msg)

        messages = manager.get_messages_for_api("session-1", include_meta=False)
        assert len(messages) == 1
        assert messages[0]["content"] == "Visible"

    def test_get_messages_for_api_includes_meta(self, manager):
        """Test getting messages includes meta when include_meta=True"""
        manager.create_conversation("session-1")
        manager.add_user_message("session-1", "Visible")
        msg = Message(role="user", content="Hidden", isMeta=True)
        state = manager.get_conversation("session-1")
        state.messages.append(msg)

        messages = manager.get_messages_for_api("session-1", include_meta=True)
        assert len(messages) == 2

    def test_get_messages_for_api_nonexistent(self, manager):
        """Test getting messages from nonexistent conversation returns empty"""
        messages = manager.get_messages_for_api("nonexistent")
        assert messages == []

    def test_get_visible_messages(self, manager):
        """Test getting visible messages for UI"""
        manager.create_conversation("session-1")
        manager.add_user_message("session-1", "Visible")
        msg = Message(role="user", content="Hidden", isMeta=True)
        state = manager.get_conversation("session-1")
        state.messages.append(msg)

        messages = manager.get_visible_messages("session-1")
        assert len(messages) == 1
        assert messages[0]["content"] == "Visible"
        assert "timestamp" in messages[0]

    def test_get_visible_messages_nonexistent(self, manager):
        """Test getting visible messages from nonexistent conversation returns empty"""
        messages = manager.get_visible_messages("nonexistent")
        assert messages == []

    def test_update_context(self, manager):
        """Test updating conversation context"""
        manager.create_conversation("session-1")
        manager.update_context("session-1", {"key": "value"})
        state = manager.get_conversation("session-1")
        assert state.context == {"key": "value"}

    def test_update_context_append(self, manager):
        """Test updating context appends to existing"""
        manager.create_conversation("session-1")
        manager.update_context("session-1", {"key1": "value1"})
        manager.update_context("session-1", {"key2": "value2"})
        state = manager.get_conversation("session-1")
        assert state.context == {"key1": "value1", "key2": "value2"}

    def test_update_context_nonexistent(self, manager):
        """Test updating context on nonexistent conversation does nothing"""
        manager.update_context("nonexistent", {"key": "value"})
        state = manager.get_conversation("nonexistent")
        assert state is None

    def test_activate_skill(self, manager):
        """Test activating a skill"""
        manager.create_conversation("session-1")
        manager.activate_skill("session-1", "skill1")
        state = manager.get_conversation("session-1")
        assert "skill1" in state.active_skills

    def test_activate_skill_duplicate(self, manager):
        """Test activating same skill twice doesn't duplicate"""
        manager.create_conversation("session-1")
        manager.activate_skill("session-1", "skill1")
        manager.activate_skill("session-1", "skill1")
        state = manager.get_conversation("session-1")
        assert state.active_skills == ["skill1"]

    def test_deactivate_skill(self, manager):
        """Test deactivating a skill"""
        manager.create_conversation("session-1")
        manager.activate_skill("session-1", "skill1")
        manager.deactivate_skill("session-1", "skill1")
        state = manager.get_conversation("session-1")
        assert "skill1" not in state.active_skills

    def test_deactivate_nonexistent_skill(self, manager):
        """Test deactivating nonexistent skill doesn't raise"""
        manager.create_conversation("session-1")
        manager.deactivate_skill("session-1", "nonexistent")
        state = manager.get_conversation("session-1")
        assert state.active_skills == []

    def test_full_conversation_flow(self, manager):
        """Test full conversation flow"""
        session_id = "session-1"
        manager.create_conversation(session_id)

        manager.add_user_message(session_id, "Hello")
        manager.add_assistant_message(session_id, "Hi there!")
        manager.activate_skill(session_id, "skill1")
        manager.update_context(session_id, {"user": "test"})

        state = manager.get_conversation(session_id)
        assert len(state.messages) == 2
        assert "skill1" in state.active_skills
        assert state.context == {"user": "test"}

        manager.deactivate_skill(session_id, "skill1")
        assert "skill1" not in state.active_skills
