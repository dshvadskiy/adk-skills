"""Tests for SkillMetaTool - skill lifecycle and activation."""

from pathlib import Path

import pytest

from skill_framework.core import SkillMetaTool, SkillActivationMode, SkillActivationResult


class TestSkillActivationMode:
    """Test SkillActivationMode enum."""

    def test_activation_modes(self):
        """Test all activation mode values and string conversion."""
        assert SkillActivationMode.AUTO.value == "auto"
        assert SkillActivationMode.MANUAL.value == "manual"
        assert SkillActivationMode.PRELOAD.value == "preload"

        # String conversion
        assert SkillActivationMode("auto") == SkillActivationMode.AUTO
        assert SkillActivationMode("manual") == SkillActivationMode.MANUAL


class TestSkillActivationResult:
    """Test SkillActivationResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful activation result."""
        result = SkillActivationResult(
            success=True,
            skill_name="test-skill",
            metadata_message={"role": "user", "content": "test"},
            instruction_message={"role": "user", "content": "instructions"},
            modified_context={"active_skill": "test-skill"},
        )

        assert result.success is True
        assert result.skill_name == "test-skill"
        assert result.error is None
        assert result.error_details is None

    def test_failed_result_with_error(self):
        """Test creating a failed activation result with error details."""
        result = SkillActivationResult(
            success=False,
            skill_name="nonexistent",
            metadata_message={},
            instruction_message={},
            modified_context={},
            error="Skill 'nonexistent' not found",
            error_details={"available_skills": ["hello-world"]},
        )

        assert result.success is False
        assert "not found" in result.error
        assert "available_skills" in result.error_details


class TestSkillMetaTool:
    """Test SkillMetaTool using real hello-world fixture."""

    @pytest.fixture
    def skills_dir(self) -> Path:
        """Return the project's skills directory."""
        return Path(__file__).parent.parent.parent / "skills"

    @pytest.fixture
    def meta_tool(self, skills_dir: Path) -> SkillMetaTool:
        """Create SkillMetaTool instance."""
        return SkillMetaTool(skills_directory=skills_dir, cache_enabled=True)

    def test_loads_skill_metadata_on_init(self, meta_tool: SkillMetaTool):
        """Test that metadata is loaded on initialization (progressive disclosure)."""
        # Metadata loaded
        assert "hello-world" in meta_tool.skills_metadata
        metadata = meta_tool.skills_metadata["hello-world"]
        assert metadata.name == "hello-world"
        assert metadata.description == "A simple test skill that greets the user"

        # Full content NOT in cache (progressive disclosure)
        assert "hello-world" not in meta_tool._skill_cache

    def test_get_tool_definition(self, meta_tool: SkillMetaTool):
        """Test tool definition for LLM tools array."""
        tool_def = meta_tool.get_tool_definition()

        assert tool_def["name"] == "Skill"
        assert "description" in tool_def
        assert "input_schema" in tool_def

        # Skill appears in enum and description
        assert "hello-world" in tool_def["input_schema"]["properties"]["skill_name"]["enum"]
        assert "hello-world" in tool_def["description"]
        assert "greets the user" in tool_def["description"]

    def test_get_system_prompt_section(self, meta_tool: SkillMetaTool):
        """Test system prompt section includes skill metadata."""
        section = meta_tool.get_system_prompt_section()

        assert "hello-world" in section
        assert "A simple test skill" in section
        assert "Available Skills" in section
        assert "v1.0.0" in section
        assert "test" in section  # tags
        assert "example" in section

    @pytest.mark.asyncio
    async def test_activate_skill_success(self, meta_tool: SkillMetaTool):
        """Test successful skill activation with two-message pattern."""
        result = await meta_tool.activate_skill(
            skill_name="hello-world",
            current_context={"allowed_tools": [], "max_execution_time": 600},
        )

        # Success
        assert result.success is True
        assert result.skill_name == "hello-world"
        assert result.error is None

        # Message 1: Visible metadata
        msg1 = result.metadata_message
        assert msg1["role"] == "user"
        assert "<command-message>" in msg1["content"]
        assert "hello-world" in msg1["content"]
        assert msg1["metadata"]["visible"] is True
        assert msg1["metadata"]["type"] == "skill_activation"

        # Message 2: Hidden instructions (isMeta=true)
        msg2 = result.instruction_message
        assert msg2["role"] == "user"
        assert msg2["isMeta"] is True
        assert "Hello World Skill" in msg2["content"]
        assert msg2["metadata"]["visible"] is False
        assert msg2["metadata"]["type"] == "skill_instructions"

        # Context modified
        ctx = result.modified_context
        assert ctx["active_skill"] == "hello-world"
        assert ctx["skill_version"] == "1.0.0"
        assert ctx["max_execution_time"] == 30  # skill limit

        # Cached after activation
        assert "hello-world" in meta_tool._skill_cache

        # Tracked as active
        assert meta_tool.is_skill_active("hello-world")
        assert "hello-world" in meta_tool.get_active_skills()

    @pytest.mark.asyncio
    async def test_activate_nonexistent_skill(self, meta_tool: SkillMetaTool):
        """Test activating skill that doesn't exist."""
        result = await meta_tool.activate_skill(
            skill_name="nonexistent",
            current_context={},
        )

        assert result.success is False
        assert "not found" in result.error
        assert "available_skills" in result.error_details

    def test_deactivate_skill(self, meta_tool: SkillMetaTool):
        """Test skill deactivation."""
        # Manually activate
        meta_tool.active_skills["hello-world"] = {
            "metadata": meta_tool.skills_metadata["hello-world"],
            "activated_at": "2024-01-01T00:00:00Z",
        }

        assert meta_tool.is_skill_active("hello-world")

        meta_tool.deactivate_skill("hello-world")
        assert not meta_tool.is_skill_active("hello-world")

        # Deactivating nonexistent skill is safe
        meta_tool.deactivate_skill("nonexistent")  # no error

    def test_reload_and_clear_cache(self, meta_tool: SkillMetaTool):
        """Test cache management operations."""
        # Populate cache
        meta_tool._skill_cache["hello-world"] = meta_tool.loader.load_skill("hello-world")
        assert "hello-world" in meta_tool._skill_cache

        # Clear cache
        meta_tool.clear_cache()
        assert "hello-world" not in meta_tool._skill_cache

        # Repopulate and reload
        meta_tool._skill_cache["hello-world"] = meta_tool.loader.load_skill("hello-world")
        meta_tool.reload_skills()
        assert "hello-world" not in meta_tool._skill_cache
        assert "hello-world" in meta_tool.skills_metadata

    def test_empty_skills_directory(self, tmp_path: Path):
        """Test handling of empty or nonexistent skills directory."""
        # Empty directory
        empty_dir = tmp_path / "empty_skills"
        empty_dir.mkdir()
        meta_tool = SkillMetaTool(skills_directory=empty_dir)
        assert len(meta_tool.skills_metadata) == 0
        assert meta_tool.get_system_prompt_section() == ""

        # Nonexistent directory
        meta_tool = SkillMetaTool(skills_directory=tmp_path / "nonexistent")
        assert len(meta_tool.skills_metadata) == 0
