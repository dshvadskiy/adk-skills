# Code Execution in Agent Skills

Complete guide to code execution capabilities in the Agent Skills Framework.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Creating Skills with Scripts](#creating-skills-with-scripts)
4. [Security Model](#security-model)
5. [Script Execution](#script-execution)
6. [Examples](#examples)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The Agent Skills Framework supports **safe, sandboxed code execution** within skills. This enables skills to:

- Execute Python scripts for data analysis, processing, and automation
- Run shell commands with fine-grained permission control
- Access local files and resources within defined boundaries
- Enforce execution constraints (timeouts, memory limits, network access)

### Key Features

- **Permission-based execution**: Skills declare required tools using `allowed-tools` field
- **Scoped permissions**: Restrict commands to specific patterns (e.g., `Bash(python:*)` allows only Python)
- **Execution constraints**: Enforce timeouts, memory limits, and network isolation
- **Path safety**: Automatic path traversal prevention and directory restrictions
- **Environment isolation**: Skills run with controlled environment variables

---

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│ SKILL.md                                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ allowed-tools: "Bash(python:*),Read,Write"              │ │
│ │ max_execution_time: 300                                 │ │
│ │ network_access: false                                   │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ SkillMetaTool.activate_skill()                              │
│ 1. Parse allowed-tools                                      │
│ 2. Create ExecutionConstraints                              │
│ 3. Instantiate ScriptExecutor                               │
│ 4. Inject permissions message                               │
│ 5. Resolve {baseDir} variables                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ ScriptExecutor                                               │
│ - Validates script paths (prevent traversal)                │
│ - Checks command permissions                                │
│ - Enforces execution constraints                            │
│ - Captures stdout/stderr                                    │
│ - Returns ExecutionResult                                   │
└─────────────────────────────────────────────────────────────┘
```

### Execution Flow

1. **Skill Activation**: Agent activates skill with `allowed-tools` metadata
2. **Executor Creation**: `ScriptExecutor` created with permissions and constraints
3. **Command Validation**: Each command checked against allowed patterns
4. **Safe Execution**: Scripts run with timeout, path restrictions, and environment isolation
5. **Result Capture**: stdout, stderr, exit code, and execution time captured

---

## Creating Skills with Scripts

### Directory Structure

```
skills/my-skill/
├── SKILL.md              # Skill definition with allowed-tools
├── scripts/              # Executable scripts (required)
│   ├── process.py
│   ├── analyze.py
│   └── visualize.py
├── references/           # Documentation (optional)
│   └── REFERENCE.md
└── requirements.txt      # Python dependencies (optional)
```

### SKILL.md Format

```yaml
---
name: my-skill
description: Description of what this skill does
version: 1.0.0
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
max_execution_time: 300
max_memory: 512
network_access: false
python_packages:
  - pandas>=2.0.0
  - numpy>=1.24.0
system_packages: []
---

# Skill Instructions

Use the scripts in {baseDir}/scripts/ to perform tasks:

## Available Scripts

### process.py
Process data files:
```bash
python {baseDir}/scripts/process.py input.csv --output output.csv
```

### analyze.py
Analyze data:
```bash
python {baseDir}/scripts/analyze.py data.csv --stats
```
```

### allowed-tools Syntax

The `allowed-tools` field uses a comma-separated or space-separated format:

**Format**: `"Tool(scope:pattern),Tool(scope:pattern),..."`

**Examples**:

```yaml
# Allow any Python command
allowed-tools: "Bash(python:*)"

# Allow specific git commands
allowed-tools: "Bash(git status:*),Bash(git log:*)"

# Allow Python, jq, and file operations
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"

# Multiple tools with different scopes
allowed-tools: "Bash(python:*),Bash(git:*),Read,Write,Execute"
```

**Permission Patterns**:

| Pattern | Meaning | Example |
|---------|---------|---------|
| `Bash(python:*)` | Any python command | `python script.py`, `python -m module` |
| `Bash(git status:*)` | Only git status | `git status`, `git status --short` |
| `Bash(git:*)` | Any git command | `git status`, `git commit`, `git push` |
| `Read` | Read file operations | File reading |
| `Write` | Write file operations | File writing |
| `Execute` | Execute permissions | Script execution |

---

## Security Model

### Permission Enforcement

1. **Command Validation**: Every command checked against `allowed-tools` patterns
2. **Path Restrictions**: Scripts must be in `scripts/` subdirectory
3. **Path Traversal Prevention**: Automatic detection and blocking of `../` attacks
4. **Working Directory**: Execution restricted to skill directory and subdirectories

### Execution Constraints

```python
@dataclass
class ExecutionConstraints:
    max_execution_time: int = 300      # Timeout in seconds
    max_memory: Optional[int] = None   # Memory limit in MB (Linux only)
    network_access: bool = False       # Network isolation
    allowed_commands: List[str] = []   # Permitted command patterns
    working_directory: Optional[Path] = None  # Execution directory
```

### Environment Isolation

Scripts run with controlled environment variables:

```python
env = {
    'SKILL_NAME': 'my-skill',
    'SKILL_DIR': '/path/to/skill',
    'SCRIPTS_DIR': '/path/to/skill/scripts',
    'PATH': os.environ.get('PATH'),
    # User-provided env vars merged here
}
```

### Security Best Practices

1. **Minimal Permissions**: Only grant necessary tools
2. **Scoped Commands**: Use specific patterns (e.g., `git status:*` not `git:*`)
3. **Timeout Enforcement**: Always set `max_execution_time`
4. **Network Isolation**: Keep `network_access: false` unless required
5. **Input Validation**: Scripts should validate all inputs
6. **Error Handling**: Scripts should handle errors gracefully

---

## Script Execution

### {baseDir} Variable

The `{baseDir}` variable is automatically resolved to the skill's absolute path:

**In SKILL.md**:
```markdown
Run the analysis script:
```bash
python {baseDir}/scripts/analyze.py data.csv
```
```

**After resolution**:
```bash
python /absolute/path/to/skills/my-skill/scripts/analyze.py data.csv
```

### Script Requirements

1. **Location**: Must be in `scripts/` subdirectory
2. **Shebang**: Include `#!/usr/bin/env python3` for Python scripts
3. **Executable**: Set executable permissions (`chmod +x`)
4. **Error Handling**: Use try/except blocks and return proper exit codes
5. **Help Messages**: Implement `--help` with argparse or similar

### Example Script Template

```python
#!/usr/bin/env python3
"""
Script description.

Usage:
    python script.py <input> [--option VALUE]
"""

import argparse
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("input", help="Input file")
    parser.add_argument("--option", help="Optional parameter")
    
    args = parser.parse_args()
    
    try:
        # Validate input
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"Error: File not found: {args.input}", file=sys.stderr)
            return 1
        
        # Process
        result = process_data(input_path, args.option)
        
        # Output
        print(result)
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

def process_data(input_path, option):
    """Process data and return result."""
    # Implementation here
    pass

if __name__ == "__main__":
    sys.exit(main())
```

### ExecutionResult

Scripts return an `ExecutionResult` object:

```python
@dataclass
class ExecutionResult:
    success: bool           # True if exit_code == 0
    exit_code: int          # Process exit code
    stdout: str             # Standard output
    stderr: str             # Standard error
    execution_time: float   # Execution time in seconds
    command: str            # Command that was executed
    error: Optional[str]    # Error message if failed
```

---

## Examples

### Example 1: Data Analysis Skill

See `skills/data-analysis/` for a complete example with:
- CSV/JSON data extraction and filtering
- Statistical analysis with correlations
- Chart generation (histogram, scatter, bar, line)
- Comprehensive documentation

**Key Files**:
- `SKILL.md`: Skill definition with `allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"`
- `scripts/extract.py`: Data extraction (140 lines)
- `scripts/stats.py`: Statistical analysis (180 lines)
- `scripts/visualize.py`: Visualization (250 lines)
- `references/REFERENCE.md`: Complete API documentation

**Usage Example**:
```bash
# Extract specific columns
python {baseDir}/scripts/extract.py data.csv --columns name,age,salary

# Calculate statistics
python {baseDir}/scripts/stats.py data.csv --correlations

# Create visualization
python {baseDir}/scripts/visualize.py data.csv --type scatter --x age --y salary --output chart.png
```

### Example 2: Simple Processing Skill

```yaml
---
name: csv-processor
description: Process CSV files with Python
version: 1.0.0
allowed-tools: "Bash(python:*),Read,Write"
max_execution_time: 60
network_access: false
python_packages:
  - pandas>=2.0.0
---

# CSV Processor

Process CSV files using pandas.

## Usage

```bash
python {baseDir}/scripts/process.py input.csv --filter "age > 30" --output filtered.csv
```
```

### Example 3: Git Analysis Skill

```yaml
---
name: git-analyzer
description: Analyze git repository history
version: 1.0.0
allowed-tools: "Bash(git:*),Read"
max_execution_time: 120
network_access: false
---

# Git Analyzer

Analyze git repository commits and changes.

## Commands

```bash
# Analyze recent commits
git log --oneline --since="1 week ago"

# Find changes in specific file
git log --follow -- path/to/file
```
```

---

## Deployment

### Local Development

1. **Install Dependencies**:
```bash
uv sync --dev
```

2. **Create Skill with Scripts**:
```bash
mkdir -p skills/my-skill/scripts
touch skills/my-skill/SKILL.md
touch skills/my-skill/scripts/process.py
chmod +x skills/my-skill/scripts/process.py
```

3. **Test Execution**:
```bash
uv run pytest tests/integration/test_skill_execution.py -v
```

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy application
COPY . /app

# Install Python dependencies
RUN pip install -e .

# Copy skills
COPY skills/ /app/skills/

# Run agent
CMD ["python", "examples/basic_agent.py"]
```

### AWS Bedrock AgentCore

```python
from skill_framework.agent import AgentBuilder
from skill_framework.integration.adk_adapter import ADKAdapter

# Create agent with skills
builder = AgentBuilder(skills_directory="./skills")
adapter = ADKAdapter(builder)

# Deploy to Bedrock
# (See deployment/aws/agentcore/ for complete example)
```

### GCP Vertex AI

```python
from skill_framework.agent import AgentBuilder

# Create agent with skills
builder = AgentBuilder(skills_directory="./skills")

# Deploy to Vertex AI
# (See deployment/gcp/agent_engine/ for complete example)
```

### Security Considerations for Production

1. **Container Isolation**: Run skills in separate containers
2. **Resource Limits**: Enforce CPU and memory limits at container level
3. **Network Policies**: Use network policies to restrict outbound connections
4. **File System**: Mount skills directory as read-only
5. **Secrets Management**: Use secret managers for credentials
6. **Audit Logging**: Log all script executions with timestamps
7. **Rate Limiting**: Implement rate limits on script execution

---

## Troubleshooting

### Common Issues

#### Issue: "Permission denied" when executing script

**Cause**: Script not executable or command not in `allowed-tools`

**Solution**:
```bash
# Make script executable
chmod +x skills/my-skill/scripts/script.py

# Check allowed-tools in SKILL.md
allowed-tools: "Bash(python:*)"
```

#### Issue: "Path traversal attack detected"

**Cause**: Script path contains `../` or is outside skill directory

**Solution**:
```python
# ❌ Bad: Path traversal
python ../../etc/passwd

# ✅ Good: Relative to skill directory
python {baseDir}/scripts/process.py
```

#### Issue: "Command not allowed"

**Cause**: Command not matching any `allowed-tools` pattern

**Solution**:
```yaml
# Add command pattern to allowed-tools
allowed-tools: "Bash(python:*),Bash(git:*)"
```

#### Issue: "Timeout exceeded"

**Cause**: Script execution exceeded `max_execution_time`

**Solution**:
```yaml
# Increase timeout in SKILL.md
max_execution_time: 600  # 10 minutes
```

#### Issue: "Module not found" in Python script

**Cause**: Required package not installed

**Solution**:
```yaml
# Add to SKILL.md
python_packages:
  - pandas>=2.0.0
  - numpy>=1.24.0

# Install dependencies
pip install pandas numpy
```

### Debugging Tips

1. **Check Script Syntax**:
```bash
python -m py_compile skills/my-skill/scripts/script.py
```

2. **Test Script Directly**:
```bash
cd skills/my-skill
python scripts/script.py --help
```

3. **Check Permissions**:
```bash
ls -la skills/my-skill/scripts/
```

4. **View Execution Logs**:
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

5. **Validate SKILL.md**:
```bash
uv run python scripts/validate_skills.py
```

### Performance Optimization

1. **Cache Results**: Cache expensive computations
2. **Streaming Output**: Use streaming for large outputs
3. **Parallel Execution**: Run independent scripts in parallel
4. **Lazy Loading**: Load data only when needed
5. **Memory Management**: Process large files in chunks

---

## API Reference

### ScriptExecutor

```python
class ScriptExecutor:
    def __init__(
        self,
        skill_name: str,
        skill_directory: Path,
        allowed_tools: Optional[str] = None,
        constraints: Optional[ExecutionConstraints] = None
    )
    
    def execute(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None
    ) -> ExecutionResult
    
    def is_command_allowed(self, command: str) -> bool
    
    def validate_script_path(self, script_path: str) -> Path
```

### ExecutionConstraints

```python
@dataclass
class ExecutionConstraints:
    max_execution_time: int = 300
    max_memory: Optional[int] = None
    network_access: bool = False
    allowed_commands: List[str] = field(default_factory=list)
    working_directory: Optional[Path] = None
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    command: str
    error: Optional[str] = None
```

---

## Additional Resources

- **Specification**: See [CODE_EXECUTION_SPEC.md](CODE_EXECUTION_SPEC.md) for detailed architecture
- **Tasks**: See [CODE_EXECUTION_TASKS.md](CODE_EXECUTION_TASKS.md) for implementation progress
- **Examples**: See `skills/data-analysis/` for complete working example
- **Tests**: See `tests/unit/test_script_executor.py` for usage examples

---

## Contributing

When adding code execution features:

1. **Security First**: Always consider security implications
2. **Test Coverage**: Maintain >90% test coverage
3. **Documentation**: Update this guide with new features
4. **Examples**: Provide working examples
5. **Validation**: Run full test suite before committing

```bash
# Validation checklist
uv run pytest tests/ -v
uv run mypy src/
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
```
