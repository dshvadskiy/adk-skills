# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **specification project** for a Skills meta-tool architecture built on **Google ADK** (Agent Development Kit), following Claude Code's design patterns. The primary artifact is [SPEC.md](SPEC.md), which defines a production-ready implementation for:

- **Progressive disclosure**: Load skill content only when needed to minimize context window usage
- **Two-message injection pattern**: Visible metadata message + hidden instruction message (isMeta=true)
- **Dynamic permission scoping**: Modify tool access per skill
- **LLM-based skill selection**: Let the LLM decide which skill to activate via tool description matching

## Project Status

Currently specification-only. No implementation exists yet. The SPEC.md contains:
- Complete architectural specification with diagrams
- Full pseudocode for all core components (~1500 lines)
- Test framework examples with pytest
- Deployment patterns for AWS Bedrock AgentCore and GCP Vertex AI

## Architecture Quick Reference

### Core Flow
```
User Query → LLM sees Skill meta-tool → LLM calls Skill tool
→ Load SKILL.md on-demand → Inject 2 messages → Modify context → Continue
```

### Key Components (all defined in SPEC.md sections 3.1-3.5)
- **SkillMetaTool**: Single "Skill" tool in tools array, manages lifecycle
- **SkillLoader**: Parses SKILL.md files (YAML frontmatter + markdown body)
- **MessageInjector**: Creates two-message pattern (visible + hidden)
- **ContextManager**: Modifies execution context per skill
- **PermissionManager**: Fine-grained tool permissions (READ/WRITE/EXECUTE/ADMIN)

### SKILL.md Format
```yaml
---
name: skill-name
description: What this skill does
version: 1.0.0
required_tools: [bash_tool, python_execute]
activation_mode: auto | manual | preload
max_execution_time: 300
network_access: false
---

# Skill Instructions
Full markdown instructions loaded on-demand...
```

## Development Workflow

### Task Completion Checklist

**A task is only complete when ALL checks pass:**

```bash
# 1. Run all tests
uv run pytest tests/ -v

# 2. Type checking
uv run mypy src/

# 3. Linting
uv run ruff check src/ tests/

# 4. Formatting verification
uv run ruff format --check src/ tests/
```

### Recommended Tools (add to pyproject.toml dev dependencies)

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=4.1",      # Coverage reporting
    "mypy>=1.8",            # Static type checking
    "ruff>=0.3",            # Fast linter + formatter (replaces flake8, black, isort)
    "types-PyYAML>=6.0",    # Type stubs for PyYAML
]
```

### Tool Configuration (add to pyproject.toml)

```toml
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_ignores = true
exclude = ["tests/"]

[tool.ruff]
target-version = "py310"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
ignore = ["E501"]  # Line length handled by formatter

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
```

### Quick Validation Command

```bash
# Run all checks in sequence (copy-paste friendly)
uv run pytest tests/ && uv run mypy src/ && uv run ruff check src/ tests/ && uv run ruff format --check src/ tests/
```

### Why These Tools?

| Tool | Purpose | Why Recommended |
|------|---------|---------------|
| **pytest** | Testing | Already in use, excellent async support |
| **mypy** | Type checking | Catches type errors before runtime, strict mode for quality |
| **ruff** | Linting + Formatting | 10-100x faster than flake8/black, single tool for both |
| **pytest-cov** | Coverage | Ensures adequate test coverage |

## Project Structure
```
src/skill_framework/
├── core/           # SkillMetaTool, SkillLoader, MessageInjector
├── integration/    # Google ADK adapters (future)
└── utils/
skills/             # SKILL.md definitions (hello-world for testing)
tests/unit/         # Unit tests - minimal mocking, real fixtures
```

### Commands
```bash
uv sync --dev                           # Install dependencies
uv run pytest tests/                    # Run all tests
uv run pytest tests/unit/               # Unit tests only
uv run pytest tests/ --cov=src/         # Tests with coverage
uv run mypy src/                        # Type check
uv run ruff check src/ tests/           # Lint
uv run ruff format src/ tests/          # Format code
```

## Testing Philosophy

**Principle: Test real behavior with real files, minimal mocking.**

- Tests use the actual `skills/hello-world/SKILL.md` fixture
- No mocks for core classes (SkillLoader, MessageInjector, SkillMetaTool)
- Only mock external dependencies (filesystem for error cases, time for timestamps)
- Each test file covers one component with focused, meaningful tests
- Consolidate related assertions into single tests where logical

### Test Organization
- `test_skill_loader.py` - SKILL.md parsing and progressive disclosure
- `test_message_injector.py` - Two-message pattern (visible + hidden)
- `test_skill_meta_tool.py` - Skill lifecycle and activation

## Key Implementation Details

### Two-Message Pattern (Critical)
Message 1 (visible):
```python
{'role': 'user', 'content': '<command-message>Activating skill: X</command-message>'}
```

Message 2 (hidden from UI, sent to LLM):
```python
{'role': 'user', 'content': '...full instructions...', 'isMeta': True}
```

### Progressive Disclosure
- System prompt contains **metadata only** (name, description, version)
- Full SKILL.md content loaded **on-demand** when skill activated
- Caching optional for performance

### Agent Framework
- **Google ADK** (Agent Development Kit) - primary agent framework
- Deployment targets: AWS Bedrock, GCP Vertex AI, Anthropic API