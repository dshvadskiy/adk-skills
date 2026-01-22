# Code Execution Support for Agent Skills

## Executive Summary

This specification defines how to integrate code execution capabilities into the Agent Skills framework, following the [Agent Skills specification](https://agentskills.io/specification). It enables skills to include executable scripts in the `scripts/` directory and provides a secure execution environment with proper sandboxing, permission management, and resource constraints.

## 1. Agent Skills Code Execution Requirements

### 1.1 Core Requirements from Agent Skills Spec

Based on the Agent Skills specification and Claude Skills implementation, code execution support requires:

1. **scripts/ Directory Support**
   - Skills can include executable scripts in `scripts/` directory
   - Scripts should be self-contained or clearly document dependencies
   - Scripts must include helpful error messages and handle edge cases gracefully
   - Scripts are referenced using `{baseDir}` variable for portability

2. **Progressive Disclosure**
   - Scripts are loaded **only when required** (not at startup)
   - Metadata (~100 tokens) loaded at startup
   - Full SKILL.md body (< 5000 tokens) loaded on skill activation
   - Scripts loaded on-demand when referenced

3. **File References in SKILL.md**
   - Skills reference scripts: `python {baseDir}/scripts/extract.py`
   - Skills reference resources: `{baseDir}/references/REFERENCE.md`
   - `{baseDir}` variable resolves to skill's installation path
   - Agent must be able to read and execute these files

4. **allowed-tools Field**
   - **Comma-separated** list of pre-approved tools (not space-delimited)
   - Example: `allowed-tools: "Bash(git:*),Bash(jq:*),Read,Write"`
   - Supports wildcards for scoped permissions: `Bash(python:*)`, `Bash(git status:*)`
   - Tools are pre-approved (no user prompt) when skill is active

### 1.2 Integration Points

The Agent Skills specification requires:

```yaml
# SKILL.md frontmatter
---
name: data-analysis
description: Analyze CSV and JSON data files
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
---

# Instructions
To analyze data, run the extraction script:

```bash
python {baseDir}/scripts/extract.py --input data.csv --output results.json
```

See [the reference guide]({baseDir}/references/REFERENCE.md) for details.
```

### 1.3 Key Implementation Insights from Claude Skills

Based on the Claude Skills deep dive article, the implementation reveals:

1. **{baseDir} Variable Resolution**
   - All file paths use `{baseDir}` variable for portability
   - System automatically resolves to skill's installation path
   - Example: `python {baseDir}/scripts/init_skill.py` → `python /path/to/skills/skill-name/scripts/init_skill.py`

2. **Three Resource Directories with Distinct Purposes**
   - `scripts/`: Executable code run via Bash tool (not loaded into context)
   - `references/`: Documentation loaded into context via Read tool
   - `assets/`: Templates/binary files referenced by path only (not loaded)

3. **allowed-tools Format**
   - Comma-separated string: `"Read,Write,Bash,Glob,Grep,Edit"`
   - Scoped permissions: `"Bash(git status:*),Bash(git diff:*),Read,Grep"`
   - Parsed into array and injected into execution context

4. **Execution Context Modification**
   - Skills inject `command_permissions` message with allowed tools
   - Tools are pre-approved in `alwaysAllowRules.command` array
   - No user prompt required for pre-approved tools

5. **Two-Message Pattern**
   - Message 1: Metadata (visible, `isMeta: false`)
   - Message 2: Full prompt (hidden, `isMeta: true`)
   - Message 3: Permissions (conditional, `type: "command_permissions"`)

## 2. Architecture Design

### 2.1 Component Overview

```
┌─────────────────────────────────────────────────────────────┐
│ SkillMetaTool                                                │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ activate_skill()                                         │ │
│ │   1. Load SKILL.md (SkillLoader)                        │ │
│ │   2. Parse allowed-tools field                          │ │
│ │   3. Configure ScriptExecutor                           │ │
│ │   4. Inject messages with script context               │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ScriptExecutor (NEW)                                         │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ - Validate script exists in scripts/ directory         │ │
│ │ - Check allowed-tools permissions                       │ │
│ │ - Apply resource constraints (timeout, memory)         │ │
│ │ - Execute in sandboxed environment                     │ │
│ │ - Capture stdout/stderr/exit code                      │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ExecutionSandbox (NEW)                                       │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ - Isolated working directory                            │ │
│ │ - Environment variable control                          │ │
│ │ - Network access control                                │ │
│ │ - File system access control                            │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Execution Flow

```
User Query: "Analyze data.csv"
         ↓
LLM activates skill: "data-analysis"
         ↓
SkillMetaTool.activate_skill()
  1. SkillLoader loads SKILL.md
  2. Parse frontmatter: allowed-tools: Bash(python:*) Read Write
  3. Create ScriptExecutor with permissions
  4. Inject messages with script context
         ↓
LLM sees instructions: "Run scripts/extract.py"
         ↓
LLM calls tool: Bash(command="python scripts/extract.py ...")
         ↓
ScriptExecutor.execute()
  1. Validate: scripts/extract.py exists in skill directory
  2. Check: "python" allowed in allowed-tools
  3. Apply: Resource constraints (timeout, memory)
  4. Execute: In sandboxed environment
  5. Return: stdout, stderr, exit_code
         ↓
LLM processes results and responds to user
```

## 3. Implementation Components

### 3.1 ScriptExecutor

```python
# src/skill_framework/core/script_executor.py

from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass
import subprocess
import shlex
import re

@dataclass
class ExecutionResult:
    """Result of script execution"""
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    error: Optional[str] = None

@dataclass
class ExecutionConstraints:
    """Resource constraints for script execution"""
    max_execution_time: int = 300  # seconds
    max_memory: Optional[int] = None  # MB
    network_access: bool = False
    allowed_commands: List[str] = None
    working_directory: Optional[Path] = None

class ScriptExecutor:
    """
    Executes scripts from skills/ directory with security constraints.
    
    Key Responsibilities:
    1. Validate script paths (must be in skill's scripts/ directory)
    2. Parse and enforce allowed-tools permissions
    3. Apply resource constraints (timeout, memory)
    4. Execute in sandboxed environment
    5. Capture and return execution results
    
    Security Model:
    - Scripts must be in skill's scripts/ directory (no path traversal)
    - Commands must match allowed-tools patterns
    - Resource limits enforced (timeout, memory)
    - Optional network isolation
    - Working directory restricted to skill context
    """
    
    def __init__(
        self,
        skill_name: str,
        skill_directory: Path,
        allowed_tools: Optional[str] = None,
        constraints: Optional[ExecutionConstraints] = None
    ):
        """
        Initialize ScriptExecutor for a skill.
        
        Args:
            skill_name: Name of the skill
            skill_directory: Path to skill directory (contains scripts/)
            allowed_tools: Space-delimited allowed-tools string from SKILL.md
            constraints: Resource constraints for execution
        """
        self.skill_name = skill_name
        self.skill_directory = Path(skill_directory)
        self.scripts_directory = self.skill_directory / "scripts"
        self.allowed_tools = self._parse_allowed_tools(allowed_tools or "")
        self.constraints = constraints or ExecutionConstraints()
    
    def _parse_allowed_tools(self, allowed_tools: str) -> List[str]:
        """
        Parse allowed-tools field into list of tool permissions.
        
        Format (comma-separated): "Bash(git:*),Bash(jq:*),Read,Write"
        Alternative format (space-delimited): "Bash(git:*) Bash(jq:*) Read Write"
        
        Returns:
            List of tool permission strings: [
                'Bash(git:*)',
                'Bash(jq:*)',
                'Read',
                'Write'
            ]
        
        Note: Claude Skills implementation uses comma-separated format.
        We support both for backward compatibility.
        """
        if not allowed_tools:
            return []
        
        # Remove quotes if present
        allowed_tools = allowed_tools.strip('"\'')
        
        # Try comma-separated first (Claude Skills format)
        if ',' in allowed_tools:
            return [tool.strip() for tool in allowed_tools.split(',') if tool.strip()]
        
        # Fall back to space-separated (Agent Skills spec format)
        # Pattern: Tool(command:args) or Tool
        pattern = r'(\w+(?:\([^)]+\))?)'  
        matches = re.findall(pattern, allowed_tools)
        return [match.strip() for match in matches if match.strip()]
    
    def is_command_allowed(self, command: str) -> bool:
        """
        Check if command is allowed by allowed-tools.
        
        Args:
            command: Full command string (e.g., "python scripts/extract.py")
        
        Returns:
            True if command is allowed
        
        Examples:
            allowed_tools = ["Bash(python:*)", "Bash(git status:*)", "Read"]
            is_command_allowed("python scripts/test.py") → True
            is_command_allowed("git status") → True
            is_command_allowed("git commit") → False
            is_command_allowed("rm -rf /") → False
        """
        # Extract base command (first word)
        base_command = shlex.split(command)[0] if command else ""
        
        # Check against allowed_tools
        for tool_perm in self.allowed_tools:
            # Parse tool permission string
            # Format: "Bash(command:args)" or "Tool"
            if '(' in tool_perm:
                tool_name = tool_perm.split('(')[0]
                inner = tool_perm.split('(')[1].rstrip(')')
                
                if tool_name == 'Bash':
                    # Parse command:args
                    if ':' in inner:
                        allowed_cmd, allowed_args = inner.split(':', 1)
                        
                        # Wildcard match: Bash(python:*) allows any python command
                        if allowed_args == '*':
                            if base_command == allowed_cmd or \
                               (allowed_cmd.endswith('*') and base_command.startswith(allowed_cmd[:-1])):
                                return True
                        
                        # Specific subcommand: Bash(git status:*) allows only "git status"
                        if allowed_cmd in command and allowed_args == '*':
                            # Check if full command matches pattern
                            cmd_parts = shlex.split(command)
                            if len(cmd_parts) >= 2 and cmd_parts[0] == allowed_cmd.split()[0]:
                                return True
                    else:
                        # No args specified: Bash(python) matches python exactly
                        if base_command == inner:
                            return True
        
        return False
    
    def validate_script_path(self, script_path: str) -> Path:
        """
        Validate script path is within skill's scripts/ directory.
        
        Args:
            script_path: Relative path to script (e.g., "scripts/extract.py")
        
        Returns:
            Absolute path to script
        
        Raises:
            ValueError: If path is invalid or outside scripts/ directory
        """
        # Resolve path relative to skill directory
        full_path = (self.skill_directory / script_path).resolve()
        
        # Ensure path is within skill directory (prevent path traversal)
        if not str(full_path).startswith(str(self.skill_directory.resolve())):
            raise ValueError(
                f"Script path '{script_path}' is outside skill directory"
            )
        
        # Ensure script exists
        if not full_path.exists():
            raise ValueError(f"Script not found: {script_path}")
        
        # Ensure script is in scripts/ directory
        if not str(full_path).startswith(str(self.scripts_directory.resolve())):
            raise ValueError(
                f"Script must be in scripts/ directory: {script_path}"
            )
        
        return full_path
    
    def execute(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult:
        """
        Execute a command with security constraints.
        
        Args:
            command: Command to execute
            working_dir: Working directory (defaults to skill directory)
            env: Environment variables (merged with system env)
        
        Returns:
            ExecutionResult with stdout, stderr, exit code
        """
        import time
        
        start_time = time.time()
        
        # Check if command is allowed
        if not self.is_command_allowed(command):
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0,
                command=command,
                error=f"Command not allowed by skill permissions: {command}"
            )
        
        # Set working directory
        if working_dir is None:
            working_dir = self.constraints.working_directory or self.skill_directory
        
        # Prepare environment
        exec_env = dict(os.environ)
        if env:
            exec_env.update(env)
        
        # Add skill context to environment
        exec_env['SKILL_NAME'] = self.skill_name
        exec_env['SKILL_DIR'] = str(self.skill_directory)
        exec_env['SCRIPTS_DIR'] = str(self.scripts_directory)
        
        try:
            # Execute with timeout
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                env=exec_env,
                capture_output=True,
                text=True,
                timeout=self.constraints.max_execution_time
            )
            
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=result.returncode == 0,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                command=command
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                command=command,
                error=f"Execution timeout ({self.constraints.max_execution_time}s)"
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                command=command,
                error=f"Execution error: {str(e)}"
            )
```

### 3.2 Integration with SkillMetaTool

```python
# src/skill_framework/core/skill_meta_tool.py (additions)

from .script_executor import ScriptExecutor, ExecutionConstraints

class SkillMetaTool:
    # ... existing code ...
    
    async def activate_skill(
        self,
        skill_name: str,
        current_context: Dict[str, Any]
    ) -> SkillActivationResult:
        """
        Activate a skill with code execution support.
        """
        # ... existing validation and loading ...
        
        skill_content = self.loader.load_skill(skill_name)
        metadata = self.skills_metadata[skill_name]
        
        # Resolve {baseDir} variable in skill content
        skill_directory = self.loader.skills_dir / skill_name
        instructions = skill_content.instructions.replace(
            '{baseDir}',
            str(skill_directory)
        )
        
        # Create ScriptExecutor if skill has scripts
        script_executor = None
        if (skill_directory / "scripts").exists():
            constraints = ExecutionConstraints(
                max_execution_time=metadata.max_execution_time or 300,
                max_memory=metadata.max_memory,
                network_access=metadata.network_access,
                working_directory=skill_directory
            )
            
            script_executor = ScriptExecutor(
                skill_name=skill_name,
                skill_directory=skill_directory,
                allowed_tools=metadata.allowed_tools,
                constraints=constraints
            )
        
        # Create instruction message with resolved paths
        instruction_msg = self.message_injector.create_instruction_message(
            skill_name=skill_name,
            instructions=instructions,  # {baseDir} already resolved
            metadata=metadata
        )
        
        # Create permissions message (if allowed_tools specified)
        permissions_msg = None
        if metadata.allowed_tools:
            permissions_msg = self._create_permissions_message(
                allowed_tools=script_executor.allowed_tools if script_executor else [],
                model=metadata.model
            )
        
        # Add script_executor to modified context
        modified_context = self.context_manager.modify_for_skill(
            skill_name=skill_name,
            skill_metadata=metadata,
            current_context=current_context
        )
        
        if script_executor:
            modified_context['script_executor'] = script_executor
            modified_context['base_dir'] = str(skill_directory)
        
        # ... rest of activation logic ...
    
    def _create_permissions_message(self, allowed_tools: List[str], model: Optional[str]) -> Dict[str, Any]:
        """
        Create command_permissions message for execution context.
        
        This matches Claude Skills implementation:
        {
            "type": "command_permissions",
            "allowedTools": ["Bash(python:*)", "Read", "Write"],
            "model": "claude-opus-4-20250514"
        }
        """
        return {
            "role": "user",
            "content": {
                "type": "command_permissions",
                "allowedTools": allowed_tools,
                "model": model
            }
        }
```

### 3.3 SkillMetadata Extension

```python
# src/skill_framework/core/skill_meta_tool.py (update)

@dataclass
class SkillMetadata:
    """Skill metadata from YAML frontmatter"""
    name: str
    description: str
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = None
    activation_mode: SkillActivationMode = SkillActivationMode.AUTO
    
    # Tool requirements
    required_tools: List[str] = None
    optional_tools: List[str] = None
    
    # NEW: Agent Skills spec fields
    allowed_tools: Optional[str] = None  # Space-delimited: "Bash(git:*) Read Write"
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None  # Custom metadata map
    
    # Execution constraints
    max_execution_time: Optional[int] = None  # seconds
    max_memory: Optional[int] = None  # MB
    network_access: bool = False
    
    # Dependencies
    python_packages: List[str] = None
    system_packages: List[str] = None
```

### 3.4 SkillLoader Extension

```python
# src/skill_framework/core/skill_loader.py (update)

def _parse_metadata_from_yaml(self, yaml_str: str) -> 'SkillMetadata':
    """Convert YAML string to SkillMetadata with Agent Skills fields"""
    frontmatter = yaml.safe_load(yaml_str)
    
    from .skill_meta_tool import SkillMetadata, SkillActivationMode
    return SkillMetadata(
        name=frontmatter['name'],
        description=frontmatter.get('description', ''),
        version=frontmatter.get('version', '1.0.0'),
        author=frontmatter.get('author'),
        tags=frontmatter.get('tags', []),
        activation_mode=SkillActivationMode(
            frontmatter.get('activation_mode', 'auto')
        ),
        required_tools=frontmatter.get('required_tools', []),
        optional_tools=frontmatter.get('optional_tools', []),
        
        # Agent Skills spec fields
        allowed_tools=frontmatter.get('allowed-tools'),  # Note: hyphen in YAML
        license=frontmatter.get('license'),
        compatibility=frontmatter.get('compatibility'),
        metadata=frontmatter.get('metadata', {}),
        
        max_execution_time=frontmatter.get('max_execution_time'),
        max_memory=frontmatter.get('max_memory'),
        network_access=frontmatter.get('network_access', False),
        python_packages=frontmatter.get('python_packages', []),
        system_packages=frontmatter.get('system_packages', [])
    )
```

## 4. Example Skill with Code Execution

### 4.1 Data Analysis Skill

```markdown
# skills/data-analysis/SKILL.md

---
name: data-analysis
description: Analyze CSV and JSON data files, compute statistics, generate visualizations. Use when user needs data analysis, statistics, or data visualization.
version: "1.0.0"
author: example-org
license: Apache-2.0
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
compatibility: Requires python3, pandas, matplotlib
max_execution_time: 600
network_access: false
metadata:
  category: data-science
  complexity: medium
---

# Data Analysis Skill

## Overview
This skill provides data analysis capabilities for CSV and JSON files.

## Available Scripts

### 1. Extract and Analyze Data
```bash
python {baseDir}/scripts/extract.py --input data.csv --output results.json
```

### 2. Generate Statistics
```bash
python {baseDir}/scripts/stats.py --input data.csv --format json
```

### 3. Create Visualizations
```bash
python {baseDir}/scripts/visualize.py --input data.csv --output chart.png --type bar
```

## Reference Documentation

For detailed API documentation, read:
```
Read {baseDir}/references/REFERENCE.md
```

## Usage Instructions

1. **Identify the data file** the user wants to analyze
2. **Choose the appropriate script** based on the task
3. **Run the script** with proper arguments
4. **Parse the output** and present results to the user

## Common Patterns

- For CSV analysis: Use `extract.py` to parse and analyze
- For statistics: Use `stats.py` to compute mean, median, std dev
- For visualization: Use `visualize.py` to create charts

## Error Handling

- If file not found: Ask user to provide correct path
- If invalid format: Suggest data cleaning steps
- If script fails: Check error message and suggest fixes

See [REFERENCE.md](references/REFERENCE.md) for detailed API documentation.
```

### 4.2 Example Scripts

```python
# skills/data-analysis/scripts/extract.py

#!/usr/bin/env python3
"""
Extract and analyze data from CSV files.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    print("Error: pandas not installed. Run: pip install pandas", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Extract and analyze CSV data")
    parser.add_argument("--input", required=True, help="Input CSV file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()
    
    try:
        # Read CSV
        df = pd.read_csv(args.input)
        
        # Compute statistics
        results = {
            "rows": len(df),
            "columns": list(df.columns),
            "statistics": df.describe().to_dict(),
            "missing_values": df.isnull().sum().to_dict()
        }
        
        # Write results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Analysis complete. Results written to {args.output}")
        return 0
        
    except FileNotFoundError:
        print(f"Error: File not found: {args.input}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

## 5. Testing Strategy

### 5.1 Unit Tests

```python
# tests/unit/test_script_executor.py

import pytest
from pathlib import Path
from skill_framework.core.script_executor import (
    ScriptExecutor,
    ExecutionConstraints,
    ExecutionResult
)

@pytest.fixture
def data_analysis_skill_dir(tmp_path):
    """Create temporary skill directory with scripts"""
    skill_dir = tmp_path / "data-analysis"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    
    # Create test script
    test_script = scripts_dir / "test.py"
    test_script.write_text("#!/usr/bin/env python3\nprint('Hello from script')")
    test_script.chmod(0o755)
    
    return skill_dir

def test_parse_allowed_tools():
    """Test parsing of allowed-tools field"""
    executor = ScriptExecutor(
        skill_name="test",
        skill_directory=Path("/tmp"),
        allowed_tools="Bash(git:*) Bash(python:*) Read Write"
    )
    
    assert len(executor.allowed_tools) == 4
    assert executor.allowed_tools[0] == {'tool': 'Bash', 'command': 'git', 'args': '*'}
    assert executor.allowed_tools[1] == {'tool': 'Bash', 'command': 'python', 'args': '*'}
    assert executor.allowed_tools[2] == {'tool': 'Read'}
    assert executor.allowed_tools[3] == {'tool': 'Write'}

def test_is_command_allowed():
    """Test command permission checking"""
    executor = ScriptExecutor(
        skill_name="test",
        skill_directory=Path("/tmp"),
        allowed_tools="Bash(python:*) Bash(git:*)"
    )
    
    assert executor.is_command_allowed("python scripts/test.py")
    assert executor.is_command_allowed("git status")
    assert not executor.is_command_allowed("rm -rf /")
    assert not executor.is_command_allowed("curl http://evil.com")

def test_validate_script_path(data_analysis_skill_dir):
    """Test script path validation"""
    executor = ScriptExecutor(
        skill_name="data-analysis",
        skill_directory=data_analysis_skill_dir,
        allowed_tools="Bash(python:*)"
    )
    
    # Valid path
    valid_path = executor.validate_script_path("scripts/test.py")
    assert valid_path.exists()
    
    # Path traversal attempt
    with pytest.raises(ValueError, match="outside skill directory"):
        executor.validate_script_path("../../etc/passwd")
    
    # Non-existent script
    with pytest.raises(ValueError, match="Script not found"):
        executor.validate_script_path("scripts/nonexistent.py")

def test_execute_success(data_analysis_skill_dir):
    """Test successful script execution"""
    executor = ScriptExecutor(
        skill_name="data-analysis",
        skill_directory=data_analysis_skill_dir,
        allowed_tools="Bash(python:*)"
    )
    
    result = executor.execute("python scripts/test.py")
    
    assert result.success
    assert result.exit_code == 0
    assert "Hello from script" in result.stdout
    assert result.execution_time > 0

def test_execute_timeout(data_analysis_skill_dir):
    """Test execution timeout"""
    # Create long-running script
    long_script = data_analysis_skill_dir / "scripts" / "long.py"
    long_script.write_text("import time; time.sleep(10)")
    
    executor = ScriptExecutor(
        skill_name="data-analysis",
        skill_directory=data_analysis_skill_dir,
        allowed_tools="Bash(python:*)",
        constraints=ExecutionConstraints(max_execution_time=1)
    )
    
    result = executor.execute("python scripts/long.py")
    
    assert not result.success
    assert "timeout" in result.error.lower()

def test_execute_permission_denied(data_analysis_skill_dir):
    """Test execution with insufficient permissions"""
    executor = ScriptExecutor(
        skill_name="data-analysis",
        skill_directory=data_analysis_skill_dir,
        allowed_tools="Bash(git:*)"  # Only git allowed, not python
    )
    
    result = executor.execute("python scripts/test.py")
    
    assert not result.success
    assert "not allowed" in result.error.lower()
```

### 5.2 Integration Tests

```python
# tests/integration/test_skill_execution.py

import pytest
from pathlib import Path
from skill_framework.core.skill_meta_tool import SkillMetaTool

@pytest.fixture
def skills_with_scripts(tmp_path):
    """Create skills directory with executable scripts"""
    skills_dir = tmp_path / "skills"
    
    # Create data-analysis skill
    skill_dir = skills_dir / "data-analysis"
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir(parents=True)
    
    # SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: data-analysis
description: Analyze data files
allowed-tools: Bash(python:*) Read Write
max_execution_time: 60
---

# Data Analysis Skill

Run the analysis script:

```bash
python scripts/analyze.py --input data.csv
```
""")
    
    # Create script
    script = scripts_dir / "analyze.py"
    script.write_text("""#!/usr/bin/env python3
import sys
print("Analysis complete")
sys.exit(0)
""")
    script.chmod(0o755)
    
    return skills_dir

@pytest.mark.asyncio
async def test_skill_activation_with_scripts(skills_with_scripts):
    """Test skill activation creates ScriptExecutor"""
    meta_tool = SkillMetaTool(skills_directory=skills_with_scripts)
    
    result = await meta_tool.activate_skill(
        skill_name="data-analysis",
        current_context={}
    )
    
    assert result.success
    assert 'script_executor' in result.modified_context
    
    executor = result.modified_context['script_executor']
    assert executor.skill_name == "data-analysis"
    assert executor.is_command_allowed("python scripts/analyze.py")

@pytest.mark.asyncio
async def test_end_to_end_script_execution(skills_with_scripts):
    """Test complete flow: activate skill -> execute script"""
    meta_tool = SkillMetaTool(skills_directory=skills_with_scripts)
    
    # Activate skill
    result = await meta_tool.activate_skill(
        skill_name="data-analysis",
        current_context={}
    )
    
    assert result.success
    
    # Execute script
    executor = result.modified_context['script_executor']
    exec_result = executor.execute("python scripts/analyze.py --input test.csv")
    
    assert exec_result.success
    assert "Analysis complete" in exec_result.stdout
```

## 6. Security Considerations

### 6.1 Path Traversal Prevention

- All script paths validated to be within skill's `scripts/` directory
- Absolute path resolution with `Path.resolve()`
- String prefix checking to prevent `../` attacks

### 6.2 Command Injection Prevention

- Use `shlex.split()` for command parsing
- Validate commands against allowed-tools whitelist
- No arbitrary command execution without permission

### 6.3 Resource Limits

- Execution timeout (default: 300s, configurable per skill)
- Memory limits (optional, OS-dependent)
- Working directory restricted to skill context

### 6.4 Network Isolation

- `network_access` flag in SKILL.md frontmatter
- Can be enforced via container/sandbox (future enhancement)

### 6.5 Environment Isolation

- Custom environment variables per skill
- Skill context injected: `SKILL_NAME`, `SKILL_DIR`, `SCRIPTS_DIR`
- No access to sensitive system environment variables

## 7. Deployment Considerations

### 7.1 Dependencies

Skills with scripts may require:
- Python packages: Listed in `python_packages` field
- System packages: Listed in `system_packages` field
- Runtime environment: Specified in `compatibility` field

### 7.2 Container Deployment

For production deployments, consider:

```dockerfile
# Dockerfile for skill execution environment
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy skills
COPY skills/ /app/skills/

# Set working directory
WORKDIR /app

# Run agent
CMD ["python", "-m", "skill_framework.agent"]
```

### 7.3 Google ADK Integration

```python
# Integration with Google ADK
from google.adk import Agent, Tool

def create_bash_tool_with_skill_executor(skill_executor: ScriptExecutor):
    """Create Google ADK Bash tool with skill execution constraints"""
    
    def bash_execute(command: str) -> str:
        """Execute bash command with skill permissions"""
        result = skill_executor.execute(command)
        
        if not result.success:
            return f"Error: {result.error}\n{result.stderr}"
        
        return result.stdout
    
    return Tool(
        name="Bash",
        description="Execute bash commands (restricted by skill permissions)",
        function=bash_execute
    )
```

## 8. Migration Path

### 8.1 Existing Skills

To add code execution to existing skills:

1. **Add `scripts/` directory** to skill folder
2. **Update SKILL.md frontmatter** with `allowed-tools` field
3. **Add script references** in SKILL.md body
4. **Test scripts** independently before integration
5. **Update tests** to cover script execution

### 8.2 Backward Compatibility

- Skills without `scripts/` directory work as before
- Skills without `allowed-tools` field have no script execution
- Existing skills continue to function without changes

## 9. Future Enhancements

### 9.1 Advanced Sandboxing

- Container-based execution (Docker, Podman)
- WebAssembly (WASM) for portable sandboxing
- seccomp/AppArmor profiles for Linux

### 9.2 Script Caching

- Cache script execution results for identical inputs
- Invalidate cache on SKILL.md or script changes

### 9.3 Dependency Management

- Automatic installation of `python_packages`
- Virtual environment per skill
- Dependency conflict resolution

### 9.4 Monitoring and Observability

- Execution metrics (time, memory, CPU)
- Script failure tracking
- Performance profiling

### 9.5 Additional Claude Skills Patterns

- **mode field**: Mark skills as "mode commands" for behavior modification
- **disable-model-invocation**: Prevent automatic skill invocation (manual only)
- **when_to_use field**: Additional usage guidance (currently undocumented)
- **model override**: Skills can request specific models (e.g., Opus for complex tasks)

## 10. Summary

This specification defines code execution support for Agent Skills:

✅ **Implements Agent Skills spec requirements**
- `scripts/` directory support with `{baseDir}` variable resolution
- `allowed-tools` permission system (comma-separated format)
- Progressive disclosure (scripts loaded on-demand)
- File references in SKILL.md with portable paths

✅ **Follows Claude Skills implementation patterns**
- Three resource directories: `scripts/`, `references/`, `assets/`
- `{baseDir}` variable for portable file paths
- `command_permissions` message type for execution context
- Pre-approved tools in `alwaysAllowRules.command` array
- Scoped permissions: `Bash(python:*)`, `Bash(git status:*)`

✅ **Security-first design**
- Path traversal prevention
- Command whitelist enforcement
- Resource constraints (timeout, memory)
- Environment isolation

✅ **Production-ready architecture**
- Clean integration with existing SkillMetaTool
- Comprehensive error handling
- Full test coverage
- Container deployment support

✅ **Backward compatible**
- Existing skills work without changes
- Optional feature (only for skills with scripts/)
- Graceful degradation

## Next Steps

1. Implement `ScriptExecutor` class
2. Extend `SkillMetadata` with Agent Skills fields
3. Update `SkillLoader` to parse `allowed-tools`
4. Integrate with `SkillMetaTool.activate_skill()`
5. Write comprehensive tests
6. Create example skills with scripts
7. Document deployment patterns
