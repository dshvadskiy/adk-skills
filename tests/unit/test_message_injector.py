"""Tests for MessageInjector - two-message pattern implementation."""

from pathlib import Path

import pytest

from skill_framework.core import SkillLoader, SkillMetadata
from skill_framework.core.message_injector import MessageInjector


class TestMessageInjector:
    """Test two-message injection pattern using real hello-world fixture."""

    @pytest.fixture
    def skills_dir(self) -> Path:
        """Return the project's skills directory."""
        return Path(__file__).parent.parent.parent / "skills"

    @pytest.fixture
    def loader(self, skills_dir: Path) -> SkillLoader:
        """Create SkillLoader instance."""
        return SkillLoader(skills_dir=skills_dir)

    @pytest.fixture
    def metadata(self, loader: SkillLoader) -> SkillMetadata:
        """Load hello-world skill metadata."""
        return loader.load_metadata("hello-world")

    @pytest.fixture
    def instructions(self, loader: SkillLoader) -> str:
        """Load hello-world skill instructions."""
        return loader.load_skill("hello-world").instructions

    @pytest.fixture
    def injector(self) -> MessageInjector:
        """Create MessageInjector instance."""
        return MessageInjector()

    def test_metadata_message_structure(
        self, injector: MessageInjector, metadata: SkillMetadata
    ):
        """Test Message 1: visible metadata message for UI display."""
        msg = injector.create_metadata_message("hello-world", metadata)

        # Core structure
        assert msg["role"] == "user"
        assert "<command-message>" in msg["content"]
        assert "</command-message>" in msg["content"]
        assert "hello-world" in msg["content"]
        assert "v1.0.0" in msg["content"]

        # Metadata flags
        assert msg["metadata"]["visible"] is True
        assert msg["metadata"]["type"] == "skill_activation"
        assert msg["metadata"]["skill_name"] == "hello-world"
        assert msg["metadata"]["skill_version"] == "1.0.0"
        assert "timestamp" in msg["metadata"]

        # Should NOT have isMeta
        assert "isMeta" not in msg

        # Concise for UI (single line)
        lines = msg["content"].strip().split("\n")
        assert len(lines) == 1

    def test_instruction_message_structure(
        self,
        injector: MessageInjector,
        metadata: SkillMetadata,
        instructions: str,
    ):
        """Test Message 2: hidden instruction message with isMeta=true."""
        msg = injector.create_instruction_message("hello-world", instructions, metadata)

        # Core structure - CRITICAL: isMeta hides from UI
        assert msg["role"] == "user"
        assert msg["isMeta"] is True

        # Metadata flags
        assert msg["metadata"]["visible"] is False
        assert msg["metadata"]["type"] == "skill_instructions"
        assert "timestamp" in msg["metadata"]

        # Content includes skill instructions and context
        assert "# hello-world Skill" in msg["content"]
        assert "Hello World Skill" in msg["content"]
        assert "When this skill is activated" in msg["content"]
        assert "**Version:** 1.0.0" in msg["content"]
        assert "**Author:** ADK Skills Team" in msg["content"]
        assert "**Tags:** test, example" in msg["content"]
        assert "**Execution Time Limit:** 30s" in msg["content"]
        assert "Network access is disabled" in msg["content"]
        assert "---" in msg["content"]  # Separator

    def test_two_message_pattern_visibility_difference(
        self,
        injector: MessageInjector,
        metadata: SkillMetadata,
        instructions: str,
    ):
        """Test that the two messages have distinct visibility settings."""
        msg1 = injector.create_metadata_message("hello-world", metadata)
        msg2 = injector.create_instruction_message("hello-world", instructions, metadata)

        # Message 1: visible, no isMeta
        assert msg1["metadata"]["visible"] is True
        assert "isMeta" not in msg1
        assert msg1["metadata"]["type"] == "skill_activation"

        # Message 2: hidden, has isMeta
        assert msg2["metadata"]["visible"] is False
        assert msg2["isMeta"] is True
        assert msg2["metadata"]["type"] == "skill_instructions"


class TestMessageInjectorMinimalMetadata:
    """Test MessageInjector with minimal metadata (no optional fields)."""

    @pytest.fixture
    def injector(self) -> MessageInjector:
        """Create MessageInjector instance."""
        return MessageInjector()

    def test_instruction_message_omits_missing_fields(self, injector: MessageInjector):
        """Test that optional fields are omitted when not present."""
        metadata = SkillMetadata(
            name="minimal-skill",
            description="A minimal skill",
            version="1.0.0",
        )

        msg = injector.create_instruction_message(
            "minimal-skill", "Test instructions", metadata
        )

        # Required fields present
        assert "**Version:** 1.0.0" in msg["content"]

        # Optional fields absent
        assert "**Author:**" not in msg["content"]
        assert "**Tags:**" not in msg["content"]
        assert "**Required Tools:**" not in msg["content"]
        assert "**Execution Time Limit:**" not in msg["content"]

    def test_instruction_message_with_network_access(self, injector: MessageInjector):
        """Test that network disabled note is omitted when network_access=True."""
        metadata = SkillMetadata(
            name="network-skill",
            description="A skill with network access",
            version="1.0.0",
            network_access=True,
        )

        msg = injector.create_instruction_message(
            "network-skill", "Test instructions", metadata
        )

        assert "Network access is disabled" not in msg["content"]
