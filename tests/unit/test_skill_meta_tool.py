"""Tests for SkillMetaTool - skill lifecycle and activation."""

from pathlib import Path

import pytest

from skill_framework.core import (
    SkillMetaTool,
    SkillActivationMode,
    SkillActivationResult,
)


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
        assert (
            "hello-world"
            in tool_def["input_schema"]["properties"]["skill_name"]["enum"]
        )
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
        meta_tool._skill_cache["hello-world"] = meta_tool.loader.load_skill(
            "hello-world"
        )
        assert "hello-world" in meta_tool._skill_cache

        # Clear cache
        meta_tool.clear_cache()
        assert "hello-world" not in meta_tool._skill_cache

        # Repopulate and reload
        meta_tool._skill_cache["hello-world"] = meta_tool.loader.load_skill(
            "hello-world"
        )
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

    @pytest.mark.asyncio
    async def test_basedir_variable_resolution(self, tmp_path: Path):
        """Test {baseDir} variable resolution in skill instructions."""
        # Create test skill with {baseDir} in instructions
        skill_dir = tmp_path / "test-basedir"
        skill_dir.mkdir()

        skill_content = """---
name: test-basedir
description: Test baseDir resolution
---

# Test Skill

Run script: python {baseDir}/scripts/test.py
Also try: {basedir}/scripts/another.py
Multiple: {baseDir}/file1.txt and {BASEDIR}/file2.txt
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool
        meta_tool = SkillMetaTool(skills_directory=tmp_path)

        # Activate skill
        result = await meta_tool.activate_skill(
            skill_name="test-basedir",
            current_context={},
        )

        assert result.success is True

        # Check that {baseDir} is resolved in instruction message
        instructions = result.instruction_message["content"]
        expected_path = str((tmp_path / "test-basedir").resolve())

        # All variations should be replaced
        assert "{baseDir}" not in instructions
        assert "{basedir}" not in instructions
        assert "{BASEDIR}" not in instructions

        # Absolute paths should be present
        assert f"python {expected_path}/scripts/test.py" in instructions
        assert f"{expected_path}/scripts/another.py" in instructions
        assert f"{expected_path}/file1.txt" in instructions
        assert f"{expected_path}/file2.txt" in instructions

    def test_resolve_basedir_variable_method(
        self, meta_tool: SkillMetaTool, tmp_path: Path
    ):
        """Test _resolve_basedir_variable method directly."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        instructions = """
        Run: python {baseDir}/scripts/test.py
        Also: {basedir}/data.csv
        And: {BASEDIR}/config.json
        """

        resolved = meta_tool._resolve_basedir_variable(instructions, skill_dir)
        expected_path = str(skill_dir.resolve())

        # All case variations replaced
        assert "{baseDir}" not in resolved
        assert "{basedir}" not in resolved
        assert "{BASEDIR}" not in resolved

        # Absolute path present
        assert f"{expected_path}/scripts/test.py" in resolved
        assert f"{expected_path}/data.csv" in resolved
        assert f"{expected_path}/config.json" in resolved

    def test_resolve_basedir_multiple_occurrences(
        self, meta_tool: SkillMetaTool, tmp_path: Path
    ):
        """Test that multiple {baseDir} occurrences are all replaced."""
        skill_dir = tmp_path / "multi-test"
        skill_dir.mkdir()

        instructions = "{baseDir}/file1 {baseDir}/file2 {baseDir}/file3"
        resolved = meta_tool._resolve_basedir_variable(instructions, skill_dir)
        expected_path = str(skill_dir.resolve())

        # All occurrences replaced
        assert resolved.count(expected_path) == 3
        assert "{baseDir}" not in resolved

    @pytest.mark.asyncio
    async def test_script_executor_created_with_scripts_directory(self, tmp_path: Path):
        """Test that ScriptExecutor is created when skill has scripts/ directory."""
        # Create skill with scripts/ directory
        skill_dir = tmp_path / "script-skill"
        skill_dir.mkdir()
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create test script
        test_script = scripts_dir / "test.py"
        test_script.write_text("#!/usr/bin/env python3\nprint('Hello')")

        skill_content = """---
name: script-skill
description: Skill with scripts
version: 1.0.0
allowed-tools: "Bash(python:*),Read"
max_execution_time: 60
max_memory: 512
network_access: false
---

# Script Skill

Run: python {baseDir}/scripts/test.py
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool and activate skill
        meta_tool = SkillMetaTool(skills_directory=tmp_path)
        result = await meta_tool.activate_skill(
            skill_name="script-skill",
            current_context={},
        )

        assert result.success is True

        # Check that script_executor is in context
        ctx = result.modified_context
        assert "script_executor" in ctx
        assert "base_dir" in ctx

        # Verify ScriptExecutor configuration
        executor = ctx["script_executor"]
        assert executor.skill_name == "script-skill"
        assert executor.skill_directory == skill_dir.resolve()
        assert executor.scripts_directory == scripts_dir.resolve()

        # Verify constraints
        assert executor.constraints.max_execution_time == 60
        assert executor.constraints.max_memory == 512
        assert executor.constraints.network_access is False

        # Verify base_dir
        assert ctx["base_dir"] == str(skill_dir.resolve())

    @pytest.mark.asyncio
    async def test_no_script_executor_without_scripts_directory(self, tmp_path: Path):
        """Test that ScriptExecutor is NOT created when skill has no scripts/ directory."""
        # Create skill WITHOUT scripts/ directory
        skill_dir = tmp_path / "no-scripts-skill"
        skill_dir.mkdir()

        skill_content = """---
name: no-scripts-skill
description: Skill without scripts
version: 1.0.0
---

# No Scripts Skill

This skill has no scripts directory.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool and activate skill
        meta_tool = SkillMetaTool(skills_directory=tmp_path)
        result = await meta_tool.activate_skill(
            skill_name="no-scripts-skill",
            current_context={},
        )

        assert result.success is True

        # Check that script_executor is NOT in context
        ctx = result.modified_context
        assert "script_executor" not in ctx
        assert "base_dir" not in ctx

    @pytest.mark.asyncio
    async def test_script_executor_with_default_constraints(self, tmp_path: Path):
        """Test ScriptExecutor uses default constraints when not specified in metadata."""
        # Create skill with scripts/ but no execution constraints
        skill_dir = tmp_path / "default-constraints"
        skill_dir.mkdir()
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        skill_content = """---
name: default-constraints
description: Skill with default constraints
version: 1.0.0
---

# Default Constraints Skill
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool and activate skill
        meta_tool = SkillMetaTool(skills_directory=tmp_path)
        result = await meta_tool.activate_skill(
            skill_name="default-constraints",
            current_context={},
        )

        assert result.success is True

        # Check that script_executor uses defaults
        executor = result.modified_context["script_executor"]
        assert executor.constraints.max_execution_time == 300  # default
        assert executor.constraints.max_memory is None  # default
        assert executor.constraints.network_access is False  # default

    @pytest.mark.asyncio
    async def test_permissions_message_created_with_allowed_tools(self, tmp_path: Path):
        """Test that permissions message is created when skill has allowed-tools."""
        # Create skill with allowed-tools
        skill_dir = tmp_path / "permissions-skill"
        skill_dir.mkdir()

        skill_content = """---
name: permissions-skill
description: Skill with allowed tools
version: 1.0.0
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
---

# Permissions Skill

This skill has allowed tools.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool and activate skill
        meta_tool = SkillMetaTool(skills_directory=tmp_path)
        result = await meta_tool.activate_skill(
            skill_name="permissions-skill",
            current_context={},
        )

        assert result.success is True

        # Check that permissions_message is created
        assert result.permissions_message is not None
        perms_msg = result.permissions_message

        # Verify message structure
        assert perms_msg["role"] == "user"
        assert "content" in perms_msg

        content = perms_msg["content"]
        assert content["type"] == "command_permissions"
        assert "allowedTools" in content

        # Verify parsed tools
        allowed_tools = content["allowedTools"]
        assert len(allowed_tools) == 4
        assert "Bash(python:*)" in allowed_tools
        assert "Bash(jq:*)" in allowed_tools
        assert "Read" in allowed_tools
        assert "Write" in allowed_tools

    @pytest.mark.asyncio
    async def test_no_permissions_message_without_allowed_tools(self, tmp_path: Path):
        """Test that permissions message is NOT created when skill has no allowed-tools."""
        # Create skill without allowed-tools
        skill_dir = tmp_path / "no-permissions-skill"
        skill_dir.mkdir()

        skill_content = """---
name: no-permissions-skill
description: Skill without allowed tools
version: 1.0.0
---

# No Permissions Skill
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        # Create meta tool and activate skill
        meta_tool = SkillMetaTool(skills_directory=tmp_path)
        result = await meta_tool.activate_skill(
            skill_name="no-permissions-skill",
            current_context={},
        )

        assert result.success is True

        # Check that permissions_message is None
        assert result.permissions_message is None

    def test_create_permissions_message_method(self, meta_tool: SkillMetaTool):
        """Test _create_permissions_message method directly."""
        # Test with tools and model
        msg = meta_tool._create_permissions_message(
            allowed_tools=["Bash(python:*)", "Read", "Write"],
            model="claude-opus-4-20250514",
        )

        assert msg["role"] == "user"
        assert msg["content"]["type"] == "command_permissions"
        assert msg["content"]["allowedTools"] == ["Bash(python:*)", "Read", "Write"]
        assert msg["content"]["model"] == "claude-opus-4-20250514"

        # Test without model
        msg_no_model = meta_tool._create_permissions_message(
            allowed_tools=["Bash(git:*)"],
            model=None,
        )

        assert msg_no_model["role"] == "user"
        assert msg_no_model["content"]["type"] == "command_permissions"
        assert msg_no_model["content"]["allowedTools"] == ["Bash(git:*)"]
        assert "model" not in msg_no_model["content"]
