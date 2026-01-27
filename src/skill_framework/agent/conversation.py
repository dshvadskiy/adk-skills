"""Conversation manager for managing conversation state and message history."""

from datetime import datetime, timezone
from typing import Any, Optional

from dataclasses import dataclass, field

from ..observability.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    """Single conversation message"""

    role: str
    content: Any
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    isMeta: bool = False


@dataclass
class ConversationState:
    """State of ongoing conversation"""

    session_id: str
    messages: list[Message] = field(default_factory=list)
    active_skills: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ConversationManager:
    """
    Manages conversation state and message history.

    Handles:
    - Message injection (two-message pattern)
    - Context tracking
    - Skill activation state
    - History management
    """

    def __init__(self) -> None:
        self.conversations: dict[str, ConversationState] = {}

    def create_conversation(self, session_id: str) -> ConversationState:
        """Create new conversation"""
        logger.info(f"Creating new conversation: {session_id}")
        state = ConversationState(session_id=session_id)
        self.conversations[session_id] = state
        return state

    def get_conversation(self, session_id: str) -> Optional[ConversationState]:
        """Get existing conversation"""
        return self.conversations.get(session_id)

    def add_user_message(
        self,
        session_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add user message to conversation"""
        state = self.get_conversation(session_id)
        if not state:
            state = self.create_conversation(session_id)

        message = Message(
            role="user",
            content=content,
            metadata=metadata or {},
        )

        state.messages.append(message)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        logger.debug(
            f"User message added to {session_id}, content_length={len(content)}"
        )

    def add_assistant_message(
        self,
        session_id: str,
        content: Any,
        metadata: Optional[dict] = None,
    ) -> None:
        """Add assistant response"""
        state = self.get_conversation(session_id)
        if not state:
            raise ValueError(f"Conversation {session_id} not found")

        message = Message(
            role="assistant",
            content=content,
            metadata=metadata or {},
        )

        state.messages.append(message)
        state.updated_at = datetime.now(timezone.utc).isoformat()
        logger.debug(f"Assistant message added to {session_id}")

    def inject_skill_messages(
        self,
        session_id: str,
        metadata_message: dict[str, Any],
        instruction_message: dict[str, Any],
    ) -> None:
        """
        Inject two-message pattern for skill activation.

        Message 1: Visible metadata
        Message 2: Hidden instructions (isMeta=true)
        """
        state = self.get_conversation(session_id)
        if not state:
            raise ValueError(f"Conversation {session_id} not found")

        skill_name = metadata_message.get("metadata", {}).get("skill_name", "unknown")
        logger.info(f"Injecting skill messages for {skill_name} in {session_id}")

        msg1 = Message(
            role=metadata_message["role"],
            content=metadata_message["content"],
            metadata=metadata_message.get("metadata", {}),
            isMeta=False,
        )
        state.messages.append(msg1)

        msg2 = Message(
            role=instruction_message["role"],
            content=instruction_message["content"],
            metadata=instruction_message.get("metadata", {}),
            isMeta=True,
        )
        state.messages.append(msg2)

        state.updated_at = datetime.now(timezone.utc).isoformat()

    def get_messages_for_api(
        self,
        session_id: str,
        include_meta: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get messages formatted for LLM API.

        Args:
            session_id: Conversation ID
            include_meta: Include hidden (isMeta=true) messages

        Returns:
            List of message dicts for API
        """
        state = self.get_conversation(session_id)
        if not state:
            return []

        api_messages = []

        for msg in state.messages:
            if msg.isMeta and not include_meta:
                continue

            api_messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                }
            )

        return api_messages

    def get_visible_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Get only visible messages (for UI display)"""
        state = self.get_conversation(session_id)
        if not state:
            return []

        return [
            {
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "metadata": msg.metadata,
            }
            for msg in state.messages
            if not msg.isMeta
        ]

    def update_context(self, session_id: str, context_updates: dict[str, Any]) -> None:
        """Update conversation context"""
        state = self.get_conversation(session_id)
        if state:
            state.context.update(context_updates)
            state.updated_at = datetime.now(timezone.utc).isoformat()

    def activate_skill(self, session_id: str, skill_name: str) -> None:
        """Mark skill as active in conversation"""
        state = self.get_conversation(session_id)
        if state and skill_name not in state.active_skills:
            state.active_skills.append(skill_name)
            logger.info(f"Skill activated: {skill_name} in session {session_id}")

    def deactivate_skill(self, session_id: str, skill_name: str) -> None:
        """Mark skill as inactive"""
        state = self.get_conversation(session_id)
        if state and skill_name in state.active_skills:
            state.active_skills.remove(skill_name)
            logger.info(f"Skill deactivated: {skill_name} in session {session_id}")
