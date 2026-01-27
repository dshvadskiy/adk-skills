# ADK Skills Framework

Skills meta-tool architecture for Google ADK agents with progressive disclosure, two-message injection pattern, and dynamic permission scoping.

## Quick Start

### Try the Chat UI

Experience the Skills framework in action with our web-based chat interface:

```bash
# Install dependencies
uv sync --extra web

# Run the chat server
./run_chat.sh

# Or manually:
uv run python examples/chat_server.py
```

Then open `http://localhost:8000` in your browser.

See [`examples/CHAT_UI.md`](examples/CHAT_UI.md) for detailed documentation.

### Command Line Agent

Run the basic CLI agent:

```bash
uv sync
uv run python examples/basic_agent.py
```

## Documentation

- **[SPEC.md](SPEC.md)** - Complete architectural specification with pseudocode
- **[CODE_EXECUTION.md](CODE_EXECUTION.md)** - Code execution guide for skills with scripts
- **[CONFIG.md](CONFIG.md)** - Configuration guide (environment variables, deployment)
- **[CHAT_UI.md](examples/CHAT_UI.md)** - Web chat interface documentation
- **[AGENTS.md](AGENTS.md)** - Development guidelines for Claude Code
- **[TASKS.md](TASKS.md)** - Project task tracking

## Features

- **Progressive Disclosure** - Load skill content only when needed
- **Two-Message Pattern** - Visible metadata + hidden instructions (isMeta=true)
- **Dynamic Permissions** - Fine-grained tool access control per skill
- **LLM-Based Selection** - Let the LLM decide which skill to activate
- **Code Execution** - Safe, sandboxed script execution with permission control
- **Multi-Provider Support** - Works with Bedrock, OpenAI, Anthropic, Gemini, Azure

## Project Status

Currently in active development. Core framework is implemented with:
- ✅ Skill loading and parsing
- ✅ Message injection system
- ✅ Context management
- ✅ Agent builder and ADK integration
- ✅ Web-based chat UI
- ✅ Code execution with ScriptExecutor
- ✅ Permission-based command validation
- ✅ Execution constraints (timeout, memory, network)
- 🚧 Permission system (in progress)
- 🚧 Comprehensive test coverage (203 tests passing)
## Code Execution

Skills can include executable scripts with fine-grained permission control:

```yaml
---
name: data-analysis
description: Analyze CSV/JSON data with Python
allowed-tools: "Bash(python:*),Bash(jq:*),Read,Write"
max_execution_time: 300
network_access: false
---

# Instructions

Analyze data using scripts:

```bash
python {baseDir}/scripts/analyze.py data.csv --stats
```
```

**Key Features**:
- Permission-based execution (`allowed-tools` field)
- Scoped command patterns (e.g., `Bash(python:*)` allows only Python)
- Automatic path traversal prevention
- Execution constraints (timeout, memory limits)
- Environment isolation with controlled variables

**Example**: See `skills/data-analysis/` for a complete working example with data extraction, statistical analysis, and visualization scripts.

**Documentation**: See [CODE_EXECUTION.md](CODE_EXECUTION.md) for complete guide.
