"""Integration tests for ADK code execution with skills.

Tests the complete flow:
1. Create ADK agent with skill support
2. Activate skill with scripts
3. Execute scripts through bash tool
4. Verify permissions are enforced
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.skill_framework.agent.agent_builder import AgentBuilder
from src.skill_framework.integration.adk_adapter import ADKAdapter


@pytest.fixture
def skills_dir(tmp_path: Path) -> Path:
    """Create temporary skills directory with data-analysis skill."""
    skills = tmp_path / "skills"
    skills.mkdir()

    # Create data-analysis skill
    data_analysis = skills / "data-analysis"
    data_analysis.mkdir()

    # Create SKILL.md
    skill_md = data_analysis / "SKILL.md"
    skill_md.write_text("""---
name: data-analysis
description: Analyze CSV data with Python scripts
version: 1.0.0
allowed-tools: "Bash(python:*),Read,Write"
max_execution_time: 60
network_access: false
---

# Data Analysis Skill

You can analyze CSV data using Python scripts.

## Available Scripts

1. **extract.py** - Extract data from CSV
   Usage: `python {baseDir}/scripts/extract.py <file.csv>`

2. **stats.py** - Calculate statistics
   Usage: `python {baseDir}/scripts/stats.py <file.csv>`

## Instructions

When the user asks to analyze data:
1. Use bash_tool to run the appropriate script
2. Present the results clearly
""")

    # Create scripts directory
    scripts_dir = data_analysis / "scripts"
    scripts_dir.mkdir()

    # Create extract.py script
    extract_script = scripts_dir / "extract.py"
    extract_script.write_text("""#!/usr/bin/env python3
import sys

if len(sys.argv) < 2:
    print("Usage: extract.py <file.csv>")
    sys.exit(1)

print(f"Extracting data from {sys.argv[1]}")
print("Columns: name, age, city")
print("Rows: 100")
""")

    # Create stats.py script
    stats_script = scripts_dir / "stats.py"
    stats_script.write_text("""#!/usr/bin/env python3
import sys

if len(sys.argv) < 2:
    print("Usage: stats.py <file.csv>")
    sys.exit(1)

print(f"Statistics for {sys.argv[1]}")
print("Mean age: 35.5")
print("Median age: 34.0")
print("Total rows: 100")
""")

    return skills


@pytest.fixture
def agent_builder(skills_dir: Path) -> AgentBuilder:
    """Create AgentBuilder with test skills."""
    return AgentBuilder(skills_directory=skills_dir)


@pytest.fixture
def mock_adk_adapter() -> ADKAdapter:
    """Create a mock ADK adapter for testing."""
    adapter = ADKAdapter(model="gemini-2.0-flash")
    # Mock the agent and runner
    adapter._agent = MagicMock()
    adapter._runner = MagicMock()
    return adapter


class TestADKCodeExecution:
    """Test ADK integration with code execution."""

    def test_create_execution_tools_for_skill(self, agent_builder: AgentBuilder):
        """Test creating execution tools for a skill with scripts."""
        # Create tools for data-analysis skill
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")

        # Should have 3 tools: bash, read_file, write_file
        assert len(tools) == 3

        # All should be callable
        for tool in tools:
            assert callable(tool)

    def test_create_execution_tools_for_skill_without_scripts(
        self, agent_builder: AgentBuilder, skills_dir: Path
    ):
        """Test that skills without scripts don't get execution tools."""
        # Create skill without scripts directory
        no_scripts = skills_dir / "no-scripts"
        no_scripts.mkdir()

        skill_md = no_scripts / "SKILL.md"
        skill_md.write_text("""---
name: no-scripts
description: A skill without scripts
version: 1.0.0
---

# No Scripts Skill

This skill has no scripts directory.
""")

        # Reload skills
        agent_builder.skill_meta_tool.reload_skills()

        # Create tools - should be empty
        tools = agent_builder._create_execution_tools_for_skill("no-scripts")
        assert len(tools) == 0

    def test_bash_tool_executes_allowed_command(self, agent_builder: AgentBuilder):
        """Test bash tool executes commands allowed by skill permissions."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        bash_tool = tools[0]  # First tool is bash

        # Execute allowed command (python is allowed)
        result = bash_tool("python --version")

        # Should succeed (or fail with python not found, but not permission denied)
        assert "not allowed" not in result.lower()

    def test_bash_tool_blocks_unauthorized_command(self, agent_builder: AgentBuilder):
        """Test bash tool blocks commands not in allowed-tools."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        bash_tool = tools[0]

        # Try to execute unauthorized command (git not allowed)
        result = bash_tool("git status")

        # Should be blocked
        assert "not allowed" in result.lower()

    def test_bash_tool_executes_skill_script(
        self, agent_builder: AgentBuilder, skills_dir: Path
    ):
        """Test bash tool can execute skill scripts."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        bash_tool = tools[0]

        # Get skill directory
        skill_dir = skills_dir / "data-analysis"

        # Execute extract.py script
        result = bash_tool(f"python {skill_dir}/scripts/extract.py test.csv")

        # Should succeed and show output
        assert "✓" in result or "Extracting data" in result

    def test_read_file_tool_reads_from_skill_directory(
        self, agent_builder: AgentBuilder, skills_dir: Path
    ):
        """Test read_file tool can read files from skill directory."""
        # Create a test file
        skill_dir = skills_dir / "data-analysis"
        test_file = skill_dir / "test.txt"
        test_file.write_text("Hello from skill directory")

        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        read_tool = tools[1]  # Second tool is read_file

        # Read the file
        result = read_tool("test.txt")

        # Should contain file content
        assert "Hello from skill directory" in result

    def test_read_file_tool_blocks_path_traversal(self, agent_builder: AgentBuilder):
        """Test read_file tool prevents path traversal attacks."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        read_tool = tools[1]

        # Try path traversal
        result = read_tool("../../etc/passwd")

        # Should be blocked
        assert "outside skill directory" in result.lower()

    def test_write_file_tool_writes_to_skill_directory(
        self, agent_builder: AgentBuilder, skills_dir: Path
    ):
        """Test write_file tool can write files to skill directory."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        write_tool = tools[2]  # Third tool is write_file

        # Write a file
        result = write_tool("output.txt", "Test output content")

        # Should succeed
        assert "✓" in result or "Successfully wrote" in result

        # Verify file was created
        skill_dir = skills_dir / "data-analysis"
        output_file = skill_dir / "output.txt"
        assert output_file.exists()
        assert output_file.read_text() == "Test output content"

    def test_write_file_tool_blocks_path_traversal(self, agent_builder: AgentBuilder):
        """Test write_file tool prevents path traversal attacks."""
        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("data-analysis")
        write_tool = tools[2]

        # Try path traversal
        result = write_tool("../../etc/malicious", "bad content")

        # Should be blocked
        assert "outside skill directory" in result.lower()

    def test_execution_tools_respect_timeout(
        self, agent_builder: AgentBuilder, skills_dir: Path
    ):
        """Test that execution tools respect max_execution_time constraint."""
        # Create a skill with short timeout
        short_timeout = skills_dir / "short-timeout"
        short_timeout.mkdir()

        skill_md = short_timeout / "SKILL.md"
        skill_md.write_text("""---
name: short-timeout
description: Skill with 1 second timeout
version: 1.0.0
allowed-tools: "Bash(sleep:*)"
max_execution_time: 1
---

# Short Timeout Skill
""")

        # Create scripts directory
        scripts_dir = short_timeout / "scripts"
        scripts_dir.mkdir()

        # Reload skills
        agent_builder.skill_meta_tool.reload_skills()

        # Create execution tools
        tools = agent_builder._create_execution_tools_for_skill("short-timeout")
        bash_tool = tools[0]

        # Try to run command that exceeds timeout
        result = bash_tool("sleep 5")

        # Should timeout
        assert "timed out" in result.lower() or "timeout" in result.lower()
