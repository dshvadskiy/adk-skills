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

## Development

### Project Structure
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
uv sync --dev
uv run pytest tests/         # Run all tests
uv run pytest tests/unit/    # Unit tests only
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
