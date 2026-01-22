"""ADK tool wrappers for skill execution.

This module provides ADK-compatible tool functions that wrap
ScriptExecutor for autonomous script execution by the LLM.
"""

from typing import Callable, Optional

from ..core.script_executor import ExecutionResult, ScriptExecutor


def create_bash_tool_with_skill_executor(
    script_executor: Optional[ScriptExecutor] = None,
) -> Callable[[str, Optional[str]], str]:
    """
    Create an ADK-compatible bash tool that uses ScriptExecutor.

    This tool allows the LLM to autonomously execute commands
    with proper permission checking and security constraints.

    Args:
        script_executor: ScriptExecutor instance (from skill context)

    Returns:
        Callable bash tool function for ADK Agent

    Example:
        # In AgentBuilder when skill is activated:
        bash_tool = create_bash_tool_with_skill_executor(
            script_executor=context['script_executor']
        )
        agent = Agent(tools=[bash_tool, ...])
    """

    def bash_tool(command: str, working_directory: Optional[str] = None) -> str:
        """Execute a bash command with security constraints.

        IMPORTANT: Only commands allowed by the active skill's permissions
        can be executed. Check the skill's allowed-tools before attempting
        to run commands.

        Args:
            command: The bash command to execute (e.g., "python script.py")
            working_directory: Optional working directory (defaults to skill directory)

        Returns:
            Command output or error message formatted for LLM consumption.

        Example:
            result = bash_tool("python {baseDir}/scripts/extract.py data.csv")
        """
        if script_executor is None:
            return (
                "Error: No script executor available. "
                "Bash tool can only be used within an active skill that has scripts."
            )

        # Parse working directory if provided
        from pathlib import Path

        working_dir = None
        if working_directory:
            working_dir = Path(working_directory)

        # Execute command using ScriptExecutor
        result: ExecutionResult = script_executor.execute(
            command=command,
            working_dir=working_dir,
        )

        # Format result for LLM consumption
        return _format_execution_result_for_llm(result)

    return bash_tool


def _format_execution_result_for_llm(result: ExecutionResult) -> str:
    """
    Format ExecutionResult as a clear, LLM-friendly string.

    Args:
        result: ExecutionResult from ScriptExecutor

    Returns:
        Formatted string with execution details
    """
    if result.success:
        output = f"✓ Command executed successfully (exit code: {result.exit_code})\n"
        output += f"Execution time: {result.execution_time:.2f}s\n\n"

        if result.stdout:
            output += "Output:\n"
            output += result.stdout

        if result.stderr:
            output += "\n\nWarnings/Info:\n"
            output += result.stderr

        return output.strip()
    else:
        output = f"✗ Command failed (exit code: {result.exit_code})\n"
        output += f"Command: {result.command}\n"

        if result.error:
            output += f"\nError: {result.error}\n"

        if result.stderr:
            output += f"\nError details:\n{result.stderr}"

        if result.stdout:
            output += f"\n\nPartial output:\n{result.stdout}"

        return output.strip()


def create_read_file_tool(base_directory: str) -> Callable[[str], str]:
    """
    Create an ADK-compatible tool for reading files within skill directory.

    This provides safe file reading with path validation.

    Args:
        base_directory: Base directory for file operations (skill directory)

    Returns:
        Callable read_file tool function for ADK Agent
    """
    from pathlib import Path

    base_path = Path(base_directory).resolve()

    def read_file(file_path: str) -> str:
        """Read a file from the skill directory.

        Args:
            file_path: Relative path to file from skill directory

        Returns:
            File contents or error message
        """
        try:
            # Resolve path relative to base directory
            full_path = (base_path / file_path).resolve()

            # Security check: ensure path is within base directory
            try:
                full_path.relative_to(base_path)
            except ValueError:
                return (
                    f"Error: Path '{file_path}' is outside skill directory. "
                    "Path traversal is not allowed."
                )

            # Check file exists
            if not full_path.exists():
                return f"Error: File not found: {file_path}"

            if not full_path.is_file():
                return f"Error: Path is not a file: {file_path}"

            # Read file
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            return f"File: {file_path}\n\n{content}"

        except Exception as e:
            return f"Error reading file '{file_path}': {str(e)}"

    return read_file


def create_write_file_tool(base_directory: str) -> Callable[[str, str], str]:
    """
    Create an ADK-compatible tool for writing files within skill directory.

    This provides safe file writing with path validation.

    Args:
        base_directory: Base directory for file operations (skill directory)

    Returns:
        Callable write_file tool function for ADK Agent
    """
    from pathlib import Path

    base_path = Path(base_directory).resolve()

    def write_file(file_path: str, content: str) -> str:
        """Write content to a file in the skill directory.

        Args:
            file_path: Relative path to file from skill directory
            content: Content to write to the file

        Returns:
            Success message or error
        """
        try:
            # Resolve path relative to base directory
            full_path = (base_path / file_path).resolve()

            # Security check: ensure path is within base directory
            try:
                full_path.relative_to(base_path)
            except ValueError:
                return (
                    f"Error: Path '{file_path}' is outside skill directory. "
                    "Path traversal is not allowed."
                )

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"✓ Successfully wrote {len(content)} bytes to {file_path}"

        except Exception as e:
            return f"Error writing file '{file_path}': {str(e)}"

    return write_file
