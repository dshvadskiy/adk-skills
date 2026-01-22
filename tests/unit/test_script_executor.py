"""Unit tests for ScriptExecutor class."""

import pytest
from pathlib import Path
import tempfile
from skill_framework.core.script_executor import (
    ScriptExecutor,
    ExecutionResult,
    ExecutionConstraints,
)


@pytest.fixture
def temp_skill_dir():
    """Create a temporary skill directory with scripts/ subdirectory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = Path(tmpdir) / "test-skill"
        skill_dir.mkdir()
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create a simple test script
        test_script = scripts_dir / "test.py"
        test_script.write_text(
            "#!/usr/bin/env python3\nprint('Hello from test script')\n"
        )
        test_script.chmod(0o755)

        # Create a script that exits with error
        error_script = scripts_dir / "error.py"
        error_script.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(1)\n")
        error_script.chmod(0o755)

        # Create a script that times out
        timeout_script = scripts_dir / "timeout.py"
        timeout_script.write_text(
            "#!/usr/bin/env python3\nimport time\ntime.sleep(10)\n"
        )
        timeout_script.chmod(0o755)

        yield skill_dir


class TestExecutionResult:
    """Test ExecutionResult dataclass."""

    def test_execution_result_creation(self):
        """Test creating ExecutionResult with all fields."""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            execution_time=1.5,
            command="echo test",
            error=None,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.stdout == "output"
        assert result.stderr == ""
        assert result.execution_time == 1.5
        assert result.command == "echo test"
        assert result.error is None

    def test_execution_result_with_error(self):
        """Test ExecutionResult with error."""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            stdout="",
            stderr="error output",
            execution_time=0.5,
            command="failing command",
            error="Command failed",
        )

        assert result.success is False
        assert result.exit_code == 1
        assert result.error == "Command failed"


class TestExecutionConstraints:
    """Test ExecutionConstraints dataclass."""

    def test_default_constraints(self):
        """Test default ExecutionConstraints values."""
        constraints = ExecutionConstraints()

        assert constraints.max_execution_time == 300
        assert constraints.max_memory is None
        assert constraints.network_access is False
        assert constraints.allowed_commands == []
        assert constraints.working_directory is None

    def test_custom_constraints(self):
        """Test creating ExecutionConstraints with custom values."""
        constraints = ExecutionConstraints(
            max_execution_time=60,
            max_memory=512,
            network_access=True,
            allowed_commands=["python", "git"],
            working_directory=Path("/tmp"),
        )

        assert constraints.max_execution_time == 60
        assert constraints.max_memory == 512
        assert constraints.network_access is True
        assert constraints.allowed_commands == ["python", "git"]
        assert constraints.working_directory == Path("/tmp")


class TestScriptExecutorInit:
    """Test ScriptExecutor initialization."""

    def test_basic_initialization(self, temp_skill_dir):
        """Test basic ScriptExecutor initialization."""
        executor = ScriptExecutor(
            skill_name="test-skill", skill_directory=temp_skill_dir
        )

        assert executor.skill_name == "test-skill"
        assert executor.skill_directory == temp_skill_dir.resolve()
        assert executor.scripts_directory == (temp_skill_dir / "scripts").resolve()
        assert executor.allowed_tools == []
        assert isinstance(executor.constraints, ExecutionConstraints)

    def test_initialization_with_allowed_tools(self, temp_skill_dir):
        """Test initialization with allowed_tools."""
        executor = ScriptExecutor(
            skill_name="test-skill",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*),Read,Write",
        )

        assert len(executor.allowed_tools) == 3
        assert "Bash(python:*)" in executor.allowed_tools
        assert "Read" in executor.allowed_tools
        assert "Write" in executor.allowed_tools

    def test_initialization_with_constraints(self, temp_skill_dir):
        """Test initialization with custom constraints."""
        constraints = ExecutionConstraints(max_execution_time=60, max_memory=256)

        executor = ScriptExecutor(
            skill_name="test-skill",
            skill_directory=temp_skill_dir,
            constraints=constraints,
        )

        assert executor.constraints.max_execution_time == 60
        assert executor.constraints.max_memory == 256


class TestParseAllowedTools:
    """Test _parse_allowed_tools method."""

    def test_comma_separated_format(self, temp_skill_dir):
        """Test parsing comma-separated allowed-tools."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        tools = executor._parse_allowed_tools("Bash(python:*),Bash(jq:*),Read,Write")

        assert len(tools) == 4
        assert "Bash(python:*)" in tools
        assert "Bash(jq:*)" in tools
        assert "Read" in tools
        assert "Write" in tools

    def test_space_separated_format(self, temp_skill_dir):
        """Test parsing space-separated allowed-tools."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        tools = executor._parse_allowed_tools("Bash(git:*) Read Write")

        assert len(tools) == 3
        assert "Bash(git:*)" in tools
        assert "Read" in tools
        assert "Write" in tools

    def test_empty_string(self, temp_skill_dir):
        """Test parsing empty allowed-tools string."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        tools = executor._parse_allowed_tools("")
        assert tools == []

        tools = executor._parse_allowed_tools("   ")
        assert tools == []

    def test_quoted_strings(self, temp_skill_dir):
        """Test parsing quoted allowed-tools strings."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        tools = executor._parse_allowed_tools('"Bash(python:*),Read"')

        assert len(tools) == 2
        assert "Bash(python:*)" in tools
        assert "Read" in tools

    def test_mixed_whitespace(self, temp_skill_dir):
        """Test parsing with mixed whitespace."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        tools = executor._parse_allowed_tools("  Bash(python:*)  ,  Read  ,  Write  ")

        assert len(tools) == 3
        assert "Bash(python:*)" in tools


class TestIsCommandAllowed:
    """Test is_command_allowed method."""

    def test_wildcard_pattern(self, temp_skill_dir):
        """Test wildcard pattern matching."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
        )

        assert executor.is_command_allowed("python script.py") is True
        assert executor.is_command_allowed("python -m pytest") is True
        assert executor.is_command_allowed("bash script.sh") is False

    def test_scoped_permissions(self, temp_skill_dir):
        """Test scoped permission matching."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(git status:*)",
        )

        assert executor.is_command_allowed("git status") is True
        assert executor.is_command_allowed("git status --short") is True
        assert executor.is_command_allowed("git commit") is False
        assert executor.is_command_allowed("git") is False

    def test_exact_match(self, temp_skill_dir):
        """Test exact command matching."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python)",
        )

        assert executor.is_command_allowed("python") is True
        assert executor.is_command_allowed("python script.py") is False

    def test_no_allowed_tools(self, temp_skill_dir):
        """Test with no allowed tools."""
        executor = ScriptExecutor(
            skill_name="test", skill_directory=temp_skill_dir, allowed_tools=""
        )

        assert executor.is_command_allowed("anything") is False
        assert executor.is_command_allowed("python") is False

    def test_multiple_patterns(self, temp_skill_dir):
        """Test multiple allowed patterns."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*),Bash(git:*)",
        )

        assert executor.is_command_allowed("python script.py") is True
        assert executor.is_command_allowed("git status") is True
        assert executor.is_command_allowed("bash script.sh") is False


class TestValidateScriptPath:
    """Test validate_script_path method."""

    def test_valid_path(self, temp_skill_dir):
        """Test validation of valid script path."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        validated_path = executor.validate_script_path("scripts/test.py")

        assert validated_path.exists()
        assert validated_path.is_relative_to(temp_skill_dir.resolve())
        assert validated_path.name == "test.py"

    def test_path_traversal_attack(self, temp_skill_dir):
        """Test prevention of path traversal attacks."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        with pytest.raises(ValueError, match="outside skill directory"):
            executor.validate_script_path("../../etc/passwd")

        with pytest.raises(ValueError, match="outside skill directory"):
            executor.validate_script_path("../../../tmp/malicious.py")

    def test_non_existent_script(self, temp_skill_dir):
        """Test validation of non-existent script."""
        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        with pytest.raises(ValueError, match="Script not found"):
            executor.validate_script_path("scripts/missing.py")

    def test_script_outside_scripts_directory(self, temp_skill_dir):
        """Test rejection of scripts outside scripts/ directory."""
        # Create a file outside scripts/
        (temp_skill_dir / "README.md").write_text("# Test")

        executor = ScriptExecutor(skill_name="test", skill_directory=temp_skill_dir)

        with pytest.raises(ValueError, match="must be in scripts/ directory"):
            executor.validate_script_path("README.md")


class TestExecute:
    """Test execute method."""

    def test_successful_execution(self, temp_skill_dir):
        """Test successful script execution."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
        )

        result = executor.execute("python scripts/test.py")

        assert result.success is True
        assert result.exit_code == 0
        assert "Hello from test script" in result.stdout
        assert result.error is None
        assert result.execution_time > 0

    def test_execution_with_error(self, temp_skill_dir):
        """Test execution of script that exits with error."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
        )

        result = executor.execute("python scripts/error.py")

        assert result.success is False
        assert result.exit_code == 1
        assert result.error is not None

    def test_timeout_enforcement(self, temp_skill_dir):
        """Test timeout enforcement."""
        constraints = ExecutionConstraints(max_execution_time=1)
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
            constraints=constraints,
        )

        result = executor.execute("python scripts/timeout.py")

        assert result.success is False
        assert "timed out" in result.error.lower()
        assert result.execution_time >= 1.0

    def test_permission_denied(self, temp_skill_dir):
        """Test execution of unauthorized command."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(git:*)",
        )

        result = executor.execute("python scripts/test.py")

        assert result.success is False
        assert "not allowed" in result.error.lower()
        assert result.exit_code == -1

    def test_environment_variables(self, temp_skill_dir):
        """Test environment variable injection."""
        # Create script that prints environment variables
        env_script = temp_skill_dir / "scripts" / "env.py"
        env_script.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "print(f\"SKILL_NAME={os.environ.get('SKILL_NAME')}\")\n"
            "print(f\"SKILL_DIR={os.environ.get('SKILL_DIR')}\")\n"
            "print(f\"SCRIPTS_DIR={os.environ.get('SCRIPTS_DIR')}\")\n"
        )
        env_script.chmod(0o755)

        executor = ScriptExecutor(
            skill_name="test-skill",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
        )

        result = executor.execute("python scripts/env.py")

        assert result.success is True
        assert "SKILL_NAME=test-skill" in result.stdout
        assert f"SKILL_DIR={temp_skill_dir.resolve()}" in result.stdout
        assert f"SCRIPTS_DIR={(temp_skill_dir / 'scripts').resolve()}" in result.stdout

    def test_custom_environment(self, temp_skill_dir):
        """Test execution with custom environment variables."""
        # Create script that prints custom env var
        custom_env_script = temp_skill_dir / "scripts" / "custom_env.py"
        custom_env_script.write_text(
            "#!/usr/bin/env python3\n"
            "import os\n"
            "print(os.environ.get('CUSTOM_VAR', 'not set'))\n"
        )
        custom_env_script.chmod(0o755)

        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(python:*)",
        )

        result = executor.execute(
            "python scripts/custom_env.py", env={"CUSTOM_VAR": "custom_value"}
        )

        assert result.success is True
        assert "custom_value" in result.stdout

    def test_custom_working_directory(self, temp_skill_dir):
        """Test execution with custom working directory."""
        executor = ScriptExecutor(
            skill_name="test",
            skill_directory=temp_skill_dir,
            allowed_tools="Bash(pwd:*)",
        )

        result = executor.execute("pwd", working_dir=temp_skill_dir / "scripts")

        assert result.success is True
        assert "scripts" in result.stdout
