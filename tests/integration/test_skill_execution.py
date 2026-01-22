"""Integration tests for skill activation with script execution."""

from pathlib import Path

import pytest

from skill_framework.core import SkillMetaTool


class TestSkillExecutionIntegration:
    """Integration tests for complete skill activation flow with scripts."""

    @pytest.fixture
    def test_skills_dir(self, tmp_path: Path) -> Path:
        """Create a temporary skills directory with test skills."""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        return skills_dir

    @pytest.fixture
    def skill_with_scripts(self, test_skills_dir: Path) -> Path:
        """Create a complete skill with scripts/ directory."""
        skill_dir = test_skills_dir / "data-analysis"
        skill_dir.mkdir()

        # Create scripts directory
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create test script
        test_script = scripts_dir / "analyze.py"
        test_script.write_text(
            """#!/usr/bin/env python3
import sys
print("Analysis complete")
print(f"Args: {sys.argv[1:]}", file=sys.stderr)
"""
        )
        test_script.chmod(0o755)

        # Create SKILL.md
        skill_content = """---
name: data-analysis
description: Analyze data with Python scripts
version: 1.0.0
allowed-tools: "Bash(python:*),Read,Write"
max_execution_time: 60
max_memory: 512
network_access: false
---

# Data Analysis Skill

Run analysis: python {baseDir}/scripts/analyze.py
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        return skill_dir

    @pytest.fixture
    def skill_without_scripts(self, test_skills_dir: Path) -> Path:
        """Create a skill without scripts/ directory."""
        skill_dir = test_skills_dir / "simple-skill"
        skill_dir.mkdir()

        skill_content = """---
name: simple-skill
description: Simple skill without scripts
version: 1.0.0
---

# Simple Skill

This skill has no scripts.
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        return skill_dir

    @pytest.mark.asyncio
    async def test_activate_skill_creates_script_executor(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test that activating a skill with scripts/ creates ScriptExecutor."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        assert result.success is True

        # Verify ScriptExecutor in context
        ctx = result.modified_context
        assert "script_executor" in ctx
        assert "base_dir" in ctx

        # Verify executor configuration
        executor = ctx["script_executor"]
        assert executor.skill_name == "data-analysis"
        assert executor.skill_directory == skill_with_scripts.resolve()
        assert executor.scripts_directory == (skill_with_scripts / "scripts").resolve()

        # Verify constraints
        assert executor.constraints.max_execution_time == 60
        assert executor.constraints.max_memory == 512
        assert executor.constraints.network_access is False

        # Verify allowed tools parsed
        assert len(executor.allowed_tools) == 3
        assert "Bash(python:*)" in executor.allowed_tools
        assert "Read" in executor.allowed_tools
        assert "Write" in executor.allowed_tools

    @pytest.mark.asyncio
    async def test_activate_skill_without_scripts_no_executor(
        self, test_skills_dir: Path, skill_without_scripts: Path
    ):
        """Test that activating a skill without scripts/ does not create executor."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="simple-skill",
            current_context={},
        )

        assert result.success is True

        # Verify NO ScriptExecutor in context
        ctx = result.modified_context
        assert "script_executor" not in ctx
        assert "base_dir" not in ctx

    @pytest.mark.asyncio
    async def test_basedir_variable_resolution_in_instructions(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test that {baseDir} is resolved in skill instructions."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        assert result.success is True

        # Check instruction message has resolved paths
        instructions = result.instruction_message["content"]
        expected_path = str(skill_with_scripts.resolve())

        assert "{baseDir}" not in instructions
        assert f"python {expected_path}/scripts/analyze.py" in instructions

    @pytest.mark.asyncio
    async def test_end_to_end_script_execution(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test complete flow: activate skill → execute script → verify output."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        # Step 1: Activate skill
        result = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        assert result.success is True
        executor = result.modified_context["script_executor"]

        # Step 2: Execute script through executor
        exec_result = executor.execute(
            command="python scripts/analyze.py arg1 arg2",
            working_dir=skill_with_scripts,
        )

        # Step 3: Verify execution
        assert exec_result.success is True
        assert exec_result.exit_code == 0
        assert "Analysis complete" in exec_result.stdout
        assert "Args: ['arg1', 'arg2']" in exec_result.stderr
        assert exec_result.execution_time > 0

    @pytest.mark.asyncio
    async def test_skill_with_invalid_allowed_tools(self, test_skills_dir: Path):
        """Test skill activation with invalid allowed-tools format."""
        skill_dir = test_skills_dir / "invalid-tools"
        skill_dir.mkdir()

        skill_content = """---
name: invalid-tools
description: Skill with invalid tools
version: 1.0.0
allowed-tools: ""
---

# Invalid Tools Skill
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        # Should still activate successfully (empty allowed_tools is valid)
        result = await meta_tool.activate_skill(
            skill_name="invalid-tools",
            current_context={},
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_permissions_message_created_for_skill_with_scripts(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test that permissions message is created when skill has allowed-tools."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        assert result.success is True

        # Verify permissions message
        assert result.permissions_message is not None
        perms_msg = result.permissions_message

        assert perms_msg["role"] == "user"
        assert perms_msg["content"]["type"] == "command_permissions"
        assert "Bash(python:*)" in perms_msg["content"]["allowedTools"]
        assert "Read" in perms_msg["content"]["allowedTools"]
        assert "Write" in perms_msg["content"]["allowedTools"]

    @pytest.mark.asyncio
    async def test_script_execution_with_timeout(self, test_skills_dir: Path):
        """Test script execution respects timeout constraints."""
        # Create skill with very short timeout
        skill_dir = test_skills_dir / "timeout-test"
        skill_dir.mkdir()
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create a long-running script
        slow_script = scripts_dir / "slow.py"
        slow_script.write_text(
            """#!/usr/bin/env python3
import time
time.sleep(10)
print("Done")
"""
        )
        slow_script.chmod(0o755)

        # Create skill with 1 second timeout
        skill_content = """---
name: timeout-test
description: Test timeout
version: 1.0.0
allowed-tools: "Bash(python:*)"
max_execution_time: 1
---

# Timeout Test Skill
"""
        (skill_dir / "SKILL.md").write_text(skill_content)

        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="timeout-test",
            current_context={},
        )

        executor = result.modified_context["script_executor"]

        # Execute with short timeout (should timeout)
        exec_result = executor.execute(
            command="python scripts/slow.py",
            working_dir=skill_dir,
        )

        # Should fail due to timeout
        assert exec_result.success is False
        assert "timed out" in exec_result.error.lower()

    @pytest.mark.asyncio
    async def test_script_execution_permission_denied(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test that unauthorized commands are blocked."""
        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        result = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        executor = result.modified_context["script_executor"]

        # Try to execute unauthorized command (git not in allowed-tools)
        exec_result = executor.execute(
            command="git status",
            working_dir=skill_with_scripts,
        )

        # Should fail due to permission denied
        assert exec_result.success is False
        assert "not allowed" in exec_result.error.lower()

    @pytest.mark.asyncio
    async def test_multiple_skills_with_different_executors(
        self, test_skills_dir: Path, skill_with_scripts: Path
    ):
        """Test that multiple skills can have different executors."""
        # Create second skill with different permissions
        skill2_dir = test_skills_dir / "git-helper"
        skill2_dir.mkdir()
        scripts2_dir = skill2_dir / "scripts"
        scripts2_dir.mkdir()

        skill2_content = """---
name: git-helper
description: Git helper skill
version: 1.0.0
allowed-tools: "Bash(git:*),Read"
max_execution_time: 30
---

# Git Helper Skill
"""
        (skill2_dir / "SKILL.md").write_text(skill2_content)

        meta_tool = SkillMetaTool(skills_directory=test_skills_dir)

        # Activate first skill
        result1 = await meta_tool.activate_skill(
            skill_name="data-analysis",
            current_context={},
        )

        # Activate second skill
        result2 = await meta_tool.activate_skill(
            skill_name="git-helper",
            current_context={},
        )

        # Both should succeed
        assert result1.success is True
        assert result2.success is True

        # Verify different executors
        executor1 = result1.modified_context["script_executor"]
        executor2 = result2.modified_context["script_executor"]

        assert executor1.skill_name == "data-analysis"
        assert executor2.skill_name == "git-helper"

        assert executor1.constraints.max_execution_time == 60
        assert executor2.constraints.max_execution_time == 30

        assert "Bash(python:*)" in executor1.allowed_tools
        assert "Bash(git:*)" in executor2.allowed_tools
