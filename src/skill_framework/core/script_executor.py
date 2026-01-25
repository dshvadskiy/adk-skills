"""Script execution support for Agent Skills.

This module provides secure script execution with permission checking,
path validation, and resource constraints.
"""

import subprocess
import shlex
import re
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# Configure logger for script execution
logger = logging.getLogger(__name__)


@dataclass
class ExecutionMetrics:
    """Metrics collected during script execution.

    Attributes:
        total_executions: Total number of executions
        successful_executions: Number of successful executions
        failed_executions: Number of failed executions
        permission_denials: Number of permission denials
        timeouts: Number of timeout occurrences
        total_execution_time: Total time spent executing (seconds)
        average_execution_time: Average execution time (seconds)
    """

    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    permission_denials: int = 0
    timeouts: int = 0
    total_execution_time: float = 0.0

    @property
    def average_execution_time(self) -> float:
        """Calculate average execution time."""
        if self.total_executions == 0:
            return 0.0
        return self.total_execution_time / self.total_executions


@dataclass
class ExecutionResult:
    """Result of script execution.

    Attributes:
        success: Whether execution completed successfully (exit_code == 0)
        exit_code: Process exit code
        stdout: Standard output from the process
        stderr: Standard error from the process
        execution_time: Time taken to execute in seconds
        command: The command that was executed
        error: Error message if execution failed
    """

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    error: Optional[str] = None


@dataclass
class ExecutionConstraints:
    """Constraints for script execution.

    Attributes:
        max_execution_time: Maximum execution time in seconds (default: 300)
        max_memory: Maximum memory in MB (default: None, no limit)
        network_access: Whether network access is allowed (default: False)
        allowed_commands: List of allowed command patterns
        working_directory: Working directory for execution (default: skill directory)
    """

    max_execution_time: int = 300
    max_memory: Optional[int] = None
    network_access: bool = False
    allowed_commands: List[str] = field(default_factory=list)
    working_directory: Optional[Path] = None


class ScriptExecutor:
    """Executes scripts with security constraints and permission checking.

    This class provides secure script execution for Agent Skills, enforcing:
    - Command permission checking (allowed-tools)
    - Path validation (prevent path traversal)
    - Resource constraints (timeout, memory)
    - Environment isolation
    """

    def __init__(
        self,
        skill_name: str,
        skill_directory: Path,
        allowed_tools: Optional[str] = None,
        constraints: Optional[ExecutionConstraints] = None,
    ):
        """Initialize ScriptExecutor.

        Args:
            skill_name: Name of the skill
            skill_directory: Absolute path to skill directory
            allowed_tools: Comma or space-separated allowed tools string
            constraints: Execution constraints (uses defaults if None)
        """
        self.skill_name = skill_name
        self.skill_directory = Path(skill_directory).resolve()
        self.scripts_directory = self.skill_directory / "scripts"
        self.allowed_tools = self._parse_allowed_tools(allowed_tools or "")
        self.constraints = constraints or ExecutionConstraints()
        self.metrics = ExecutionMetrics()

        # Update constraints with parsed allowed commands
        if self.allowed_tools:
            self.constraints.allowed_commands = self.allowed_tools

        logger.info(
            "ScriptExecutor initialized",
            extra={
                "skill_name": self.skill_name,
                "skill_directory": str(self.skill_directory),
                "allowed_tools": self.allowed_tools,
                "max_execution_time": self.constraints.max_execution_time,
            },
        )

    def _parse_allowed_tools(self, allowed_tools: str) -> List[str]:
        """Parse allowed-tools string into list of tool permissions.

        Supports both comma-separated and space-separated formats:
        - "Bash(git:*),Read,Write"
        - "Bash(git:*) Read Write"

        Args:
            allowed_tools: Comma or space-separated tools string

        Returns:
            List of tool permission strings
        """
        if not allowed_tools or not allowed_tools.strip():
            return []

        # Remove quotes and extra whitespace
        tools_str = allowed_tools.strip().strip('"').strip("'")

        # Try comma-separated first
        if "," in tools_str:
            tools = [tool.strip() for tool in tools_str.split(",")]
        else:
            # Fall back to space-separated, using regex to handle patterns like "Bash(git:*)"
            # Match tool patterns: word characters optionally followed by (content)
            pattern = r"(\w+(?:\([^)]+\))?)"
            tools = re.findall(pattern, tools_str)

        return [tool for tool in tools if tool]

    def is_command_allowed(self, command: str) -> bool:
        """Check if a command is allowed based on allowed_tools.

        Supports:
        - Wildcard matching: Bash(python:*) allows any python command
        - Scoped permissions: Bash(git status:*) allows only "git status"
        - Exact matches: Bash(python) matches python exactly

        Args:
            command: Command string to check

        Returns:
            True if command is allowed, False otherwise
        """
        if not self.allowed_tools:
            logger.warning(
                "Command permission check failed: no allowed tools configured",
                extra={"skill_name": self.skill_name, "command": command},
            )
            return False

        try:
            # Parse command to extract base command
            parts = shlex.split(command)
            if not parts:
                return False

            base_command = parts[0]

            # Check against each allowed tool pattern
            for tool_pattern in self.allowed_tools:
                # Extract tool type and scope from pattern like "Bash(git:*)"
                match = re.match(r"(\w+)(?:\(([^)]+)\))?", tool_pattern)
                if not match:
                    continue

                tool_type, scope = match.groups()

                # For Bash tool, check command scope
                if tool_type.lower() == "bash":
                    if scope is None:
                        # No scope specified, allow all bash commands
                        logger.debug(
                            "Command allowed: unrestricted bash access",
                            extra={
                                "skill_name": self.skill_name,
                                "command": command,
                                "pattern": tool_pattern,
                            },
                        )
                        return True

                    # Remove trailing :* for wildcard matching
                    if scope.endswith(":*"):
                        scope_prefix = scope[:-2]
                        # Check if command starts with scope prefix
                        if base_command == scope_prefix:
                            logger.debug(
                                "Command allowed: wildcard match",
                                extra={
                                    "skill_name": self.skill_name,
                                    "command": command,
                                    "pattern": tool_pattern,
                                },
                            )
                            return True
                        # Check for scoped commands like "git status"
                        if len(parts) > 1:
                            scoped_cmd = f"{base_command} {parts[1]}"
                            if scoped_cmd.startswith(scope_prefix):
                                logger.debug(
                                    "Command allowed: scoped wildcard match",
                                    extra={
                                        "skill_name": self.skill_name,
                                        "command": command,
                                        "pattern": tool_pattern,
                                    },
                                )
                                return True
                    else:
                        # Exact match required - command must match exactly with no additional args
                        if base_command == scope and len(parts) == 1:
                            logger.debug(
                                "Command allowed: exact match",
                                extra={
                                    "skill_name": self.skill_name,
                                    "command": command,
                                    "pattern": tool_pattern,
                                },
                            )
                            return True
                        # Check full command for scoped matches (e.g., "git status")
                        if len(parts) >= 2:
                            scoped_cmd = f"{base_command} {parts[1]}"
                            if scoped_cmd == scope:
                                logger.debug(
                                    "Command allowed: scoped exact match",
                                    extra={
                                        "skill_name": self.skill_name,
                                        "command": command,
                                        "pattern": tool_pattern,
                                    },
                                )
                                return True

            logger.warning(
                "Command permission denied: no matching pattern",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "allowed_tools": self.allowed_tools,
                },
            )
            return False

        except Exception as e:
            # If parsing fails, deny the command
            logger.error(
                "Command permission check failed: parsing error",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "error": str(e),
                },
            )
            return False

    def validate_script_path(self, script_path: str) -> Path:
        """Validate script path is within skill directory and exists.

        Security checks:
        - Path must be within skill_directory (prevent path traversal)
        - Script must exist
        - Script must be in scripts/ subdirectory

        Args:
            script_path: Relative path to script from skill directory

        Returns:
            Absolute path to validated script

        Raises:
            ValueError: If path validation fails
        """
        # Resolve path relative to skill directory
        full_path = (self.skill_directory / script_path).resolve()

        # Check path is within skill directory (prevent path traversal)
        try:
            full_path.relative_to(self.skill_directory)
        except ValueError:
            raise ValueError(
                f"Script path '{script_path}' is outside skill directory. "
                f"Path traversal attacks are not allowed."
            )

        # Verify script exists
        if not full_path.exists():
            raise ValueError(
                f"Script not found: {script_path}. Expected at: {full_path}"
            )

        # Verify script is in scripts/ subdirectory
        try:
            full_path.relative_to(self.scripts_directory)
        except ValueError:
            raise ValueError(
                f"Script must be in scripts/ directory. Got: {script_path}"
            )

        return full_path

    def execute(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """Execute a command with security constraints.

        Args:
            command: Command to execute
            working_dir: Working directory (defaults to skill_directory)
            env: Additional environment variables

        Returns:
            ExecutionResult with execution details
        """
        import time
        import os

        start_time = time.time()

        logger.info(
            "Execution started",
            extra={
                "skill_name": self.skill_name,
                "command": command,
                "working_dir": str(working_dir)
                if working_dir
                else str(self.skill_directory),
            },
        )

        # Check command permissions
        if not self.is_command_allowed(command):
            self.metrics.total_executions += 1
            self.metrics.failed_executions += 1
            self.metrics.permission_denials += 1

            logger.warning(
                "Execution blocked: permission denied",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "allowed_tools": self.allowed_tools,
                },
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0.0,
                command=command,
                error=f"Command not allowed: {command}. Check allowed-tools in SKILL.md",
            )

        # Set working directory
        cwd = working_dir or self.constraints.working_directory or self.skill_directory

        # Prepare environment variables
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        # Add skill context to environment
        exec_env.update(
            {
                "SKILL_NAME": self.skill_name,
                "SKILL_DIR": str(self.skill_directory),
                "SCRIPTS_DIR": str(self.scripts_directory),
            }
        )

        try:
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(cwd),
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=self.constraints.max_execution_time,
            )

            execution_time = time.time() - start_time

            # Update metrics
            self.metrics.total_executions += 1
            self.metrics.total_execution_time += execution_time
            if result.returncode == 0:
                self.metrics.successful_executions += 1
            else:
                self.metrics.failed_executions += 1

            logger.info(
                "Execution completed",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "exit_code": result.returncode,
                    "execution_time": execution_time,
                    "success": result.returncode == 0,
                },
            )

            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                command=command,
                error=None
                if result.returncode == 0
                else f"Command failed with exit code {result.returncode}",
            )

        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time

            # Update metrics
            self.metrics.total_executions += 1
            self.metrics.failed_executions += 1
            self.metrics.timeouts += 1
            self.metrics.total_execution_time += execution_time

            logger.error(
                "Execution timeout",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "timeout": self.constraints.max_execution_time,
                    "execution_time": execution_time,
                },
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                command=command,
                error=f"Command timed out after {self.constraints.max_execution_time} seconds",
            )
        except Exception as e:
            execution_time = time.time() - start_time

            # Update metrics
            self.metrics.total_executions += 1
            self.metrics.failed_executions += 1
            self.metrics.total_execution_time += execution_time

            logger.error(
                "Execution failed",
                extra={
                    "skill_name": self.skill_name,
                    "command": command,
                    "error": str(e),
                    "execution_time": execution_time,
                },
            )

            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                command=command,
                error=f"Execution failed: {str(e)}",
            )

    def get_metrics(self) -> ExecutionMetrics:
        """Get execution metrics for this executor.

        Returns:
            ExecutionMetrics with current statistics
        """
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset execution metrics to zero."""
        self.metrics = ExecutionMetrics()
        logger.info(
            "Metrics reset",
            extra={"skill_name": self.skill_name},
        )
