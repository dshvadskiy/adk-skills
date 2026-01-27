# Observability Guide

Complete guide for logging and OpenTelemetry tracing in the Skills Framework.

## Table of Contents

1. [Overview](#overview)
2. [Setup Guide](#setup-guide)
3. [Logging Guide](#logging-guide)
4. [OTEL Tracing Guide](#otel-tracing-guide)
5. [Phoenix Integration](#phoenix-integration)
6. [Troubleshooting](#troubleshooting)
7. [Examples](#examples)

---

## Overview

The Skills Framework provides comprehensive observability through:

- **Structured Logging**: JSON-formatted logs with contextual information
- **OpenTelemetry Tracing**: Distributed tracing for agent conversations
- **Arize Phoenix Integration**: Real-time trace visualization and analysis

### Architecture

```
┌─────────────────┐
│  Agent Request  │
└────────┬────────┘
         │
         ├──> Logging (JSON/Text)
         │    └──> Console/File
         │
         └──> OTEL Spans
              └──> Phoenix Collector (http://localhost:6006)
                   └──> Phoenix Dashboard
```

### Key Features

- **Progressive Disclosure**: Logs skill activation and content loading
- **Tool Execution Tracking**: Trace every tool call with inputs/outputs
- **Model Call Visibility**: See all LLM interactions with token counts
- **Context Propagation**: Track skill context across operations
- **Performance Metrics**: Measure execution time and resource usage

---

## Setup Guide

### 1. Install Phoenix

Phoenix is a lightweight observability tool for LLM applications.

```bash
# Install Phoenix
pip install arize-phoenix-otel

# Or with uv
uv pip install arize-phoenix-otel
```

### 2. Start Phoenix Server

```bash
# Start Phoenix on default port (6006)
python -m phoenix.server.main serve

# Or specify custom port
python -m phoenix.server.main serve --port 6007
```

Phoenix dashboard will be available at `http://localhost:6006`

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Logging Configuration
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=json  # json or text

# OpenTelemetry Configuration
PHOENIX_COLLECTOR_ENDPOINT=http://localhost:6006
OTEL_SERVICE_NAME=skill_framework
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=development
```

### 4. Initialize in Your Application

```python
import os
from skill_framework.observability.logging_config import setup_logging
from skill_framework.observability.telemetry import setup_telemetry

# Setup logging
setup_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format_type=os.getenv("LOG_FORMAT", "json")
)

# Setup OTEL with Phoenix
setup_telemetry(
    service_name="my_agent",
    phoenix_endpoint=os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:6006"),
    environment="development"
)
```

### 5. Verify Setup

Run your agent and check:

1. **Logs**: Should appear in console (JSON or text format)
2. **Phoenix**: Open `http://localhost:6006` - traces should appear in real-time
3. **Traces**: Click on any trace to see detailed span information

---

## Logging Guide

### Log Levels

Use appropriate log levels for different scenarios:

| Level | When to Use | Example |
|-------|-------------|---------|
| **DEBUG** | Verbose details for troubleshooting | Parsing YAML, message content |
| **INFO** | Normal operations | Skill loaded, agent created |
| **WARNING** | Issues that don't stop execution | Permission denied, validation failed |
| **ERROR** | Failures requiring attention | File not found, API error |

### Structured Logging

All logs are JSON-formatted by default for machine parsing:

```json
{
  "timestamp": "2024-01-27T12:00:00Z",
  "level": "INFO",
  "logger": "skill_framework.core.skill_loader",
  "message": "Skill loaded: hello-world v1.0.0",
  "module": "skill_loader",
  "function": "load_skill",
  "line": 84,
  "context": {
    "skill_name": "hello-world",
    "session_id": "session-abc123"
  }
}
```

### Adding Contextual Information

Use `add_context()` to add fields to all subsequent logs:

```python
from skill_framework.observability.logging_config import add_context, get_logger

logger = get_logger(__name__)

# Add context for this operation
add_context(skill_name="data-analysis", session_id="session-123")

# All logs will now include these fields
logger.info("Processing data")  # Includes skill_name and session_id
```

### Text Format (Development)

For local development, use text format for readability:

```bash
LOG_FORMAT=text
```

Output:
```
2024-01-27 12:00:00 - skill_framework.core.skill_loader - INFO - Skill loaded: hello-world v1.0.0
```

### Logging Best Practices

1. **Use appropriate levels**: Don't log everything at INFO
2. **Include context**: Add skill_name, session_id, tool_name
3. **Avoid sensitive data**: Never log API keys, passwords, user data
4. **Be concise**: Log messages should be clear and actionable
5. **Use structured data**: Add context fields instead of string interpolation

---

## OTEL Tracing Guide

### Understanding Spans and Traces

- **Trace**: Complete journey of a request (e.g., user message → agent response)
- **Span**: Single operation within a trace (e.g., skill activation, tool execution)
- **Parent-Child Relationship**: Spans nest to show operation hierarchy

Example trace structure:
```
agent.send_message (root span)
├── session.ensure
├── skill.activate
│   ├── skill_loader.load_skill
│   └── message_injector.create_messages
├── tool.execute (bash_tool)
└── model.generate
```

### Automatic Instrumentation

The framework automatically traces:

- **Agent Operations**: `agent.create`, `agent.send_message`, `agent.send_message_streaming`
- **Session Management**: `session.ensure`, `session.create`
- **Skill Lifecycle**: `skill.activate`, `skill.deactivate`
- **Tool Execution**: `tool.execute` with tool name and inputs
- **Model Calls**: `model.generate` with token counts

### Span Attributes

Each span includes relevant attributes:

**Agent Spans**:
```python
{
    "agent.name": "skill_agent",
    "agent.model": "gemini-2.0-flash",
    "agent.session_id": "session-abc123",
    "agent.message_count": 5,
    "agent.tool_calls": 2,
    "agent.response_length": 1024
}
```

**Skill Spans**:
```python
{
    "skill.name": "data-analysis",
    "skill.version": "1.0.0",
    "skill.activation_mode": "auto"
}
```

**Tool Spans**:
```python
{
    "tool.name": "bash_tool",
    "tool.input_keys": ["command", "working_directory"],
    "tool.input_size": 256
}
```

### Custom Instrumentation

Add custom spans for your operations:

```python
from skill_framework.observability.telemetry import get_tracer, add_span_attributes

tracer = get_tracer()

with tracer.start_as_current_span("custom.operation") as span:
    span.set_attribute("custom.param", "value")
    
    # Your operation
    result = do_something()
    
    # Add more attributes
    add_span_attributes(result_size=len(result))
```

### Span Events

Record important milestones within a span:

```python
from skill_framework.observability.telemetry import add_span_event

add_span_event("data_loaded", {"row_count": 1000})
add_span_event("processing_started")
add_span_event("processing_completed", {"duration_ms": 150})
```

### Error Handling

Errors are automatically recorded in spans:

```python
from skill_framework.observability.telemetry import set_span_error

try:
    risky_operation()
except Exception as e:
    set_span_error(e)  # Marks span as error and records exception
    raise
```

---

## Phoenix Integration

### Accessing the Dashboard

1. Start Phoenix: `python -m phoenix.server.main serve`
2. Open browser: `http://localhost:6006`
3. Traces appear in real-time as your agent runs

### Dashboard Features

**Traces View**:
- See all traces with duration, status, and span count
- Filter by service, operation, status (success/error)
- Sort by duration to find slow operations

**Trace Details**:
- Waterfall view showing span hierarchy
- Span attributes and events
- Error details with stack traces
- Timeline showing concurrent operations

**Search and Filter**:
```
# Find traces with errors
status:error

# Find specific skill activations
skill.name:data-analysis

# Find slow operations
duration:>1s

# Combine filters
skill.name:fraud-analysis AND status:error
```

### Analyzing Performance

1. **Identify Bottlenecks**: Look for spans with long duration
2. **Check Tool Usage**: See which tools are called most frequently
3. **Monitor Errors**: Filter by `status:error` to find failures
4. **Track Token Usage**: View model call attributes for token counts

### Exporting Traces

Phoenix supports exporting traces for analysis:

1. Select traces in the dashboard
2. Click "Export" button
3. Choose format (JSON, CSV)
4. Analyze in your preferred tool

---

## Troubleshooting

### Logs Not Appearing

**Issue**: No logs in console

**Solutions**:
1. Check log level: `LOG_LEVEL=DEBUG` for verbose output
2. Verify logging is initialized: Call `setup_logging()` before any operations
3. Check logger name: Use `get_logger(__name__)` not `logging.getLogger()`

### Traces Not in Phoenix

**Issue**: Phoenix dashboard shows no traces

**Solutions**:
1. **Phoenix not running**: Start with `python -m phoenix.server.main serve`
2. **Wrong endpoint**: Check `PHOENIX_COLLECTOR_ENDPOINT` matches Phoenix port
3. **Firewall**: Ensure port 6006 is accessible
4. **Telemetry not initialized**: Call `setup_telemetry()` at startup

### Connection Refused

**Issue**: `Connection refused to localhost:6006`

**Solutions**:
1. Start Phoenix server
2. Check port: Phoenix default is 6006, verify with `netstat -an | grep 6006`
3. Use correct endpoint: `http://localhost:6006` (include `http://`)

### High Memory Usage

**Issue**: Application using too much memory

**Solutions**:
1. Reduce log level: Use `INFO` instead of `DEBUG`
2. Disable file logging: Remove `LOG_FILE` from environment
3. Batch span processing: Phoenix uses BatchSpanProcessor by default

### Missing Span Attributes

**Issue**: Spans don't show expected attributes

**Solutions**:
1. Check attribute names: Must be strings
2. Verify span is recording: Use `span.is_recording()`
3. Add attributes before span ends

---

## Examples

### Basic Logging

```python
from skill_framework.observability.logging_config import get_logger, add_context

logger = get_logger(__name__)

# Simple logging
logger.info("Operation started")
logger.debug("Processing item", extra={"item_id": 123})
logger.warning("Rate limit approaching")
logger.error("Operation failed", exc_info=True)

# With context
add_context(user_id="user-123", session_id="session-456")
logger.info("User action")  # Includes user_id and session_id
```

### Custom Tracing

```python
from skill_framework.observability.telemetry import (
    get_tracer,
    add_span_attributes,
    add_span_event,
    set_span_error
)

tracer = get_tracer()

with tracer.start_as_current_span("data.process") as span:
    # Set initial attributes
    span.set_attribute("data.source", "database")
    span.set_attribute("data.format", "csv")
    
    # Record events
    add_span_event("loading_started")
    
    try:
        data = load_data()
        add_span_event("loading_completed", {"row_count": len(data)})
        
        # Process data
        result = process_data(data)
        
        # Add result attributes
        add_span_attributes(
            result_size=len(result),
            processing_time_ms=100
        )
        
        return result
        
    except Exception as e:
        set_span_error(e)
        raise
```

### Filtering Traces in Phoenix

```python
# In Phoenix dashboard search:

# Find all skill activations
operation:skill.activate

# Find errors in data-analysis skill
skill.name:data-analysis AND status:error

# Find slow tool executions
operation:tool.execute AND duration:>500ms

# Find specific session
agent.session_id:session-abc123

# Combine multiple filters
skill.name:fraud-analysis AND tool.name:bash_tool AND status:success
```

### Environment-Based Configuration

```python
import os
from skill_framework.observability.logging_config import configure_from_env
from skill_framework.observability.telemetry import configure_from_env as configure_telemetry_from_env

# Load configuration from environment variables
configure_from_env()  # Uses LOG_LEVEL, LOG_FORMAT, LOG_FILE
configure_telemetry_from_env()  # Uses OTEL_SERVICE_NAME, PHOENIX_COLLECTOR_ENDPOINT

# Now logging and tracing are configured
```

---

## Performance Impact

Observability has minimal overhead:

- **Logging**: <1% CPU overhead with INFO level
- **OTEL Tracing**: <5% latency increase
- **Phoenix**: Async batch processing, no blocking

### Optimization Tips

1. **Production**: Use `LOG_LEVEL=INFO` and `LOG_FORMAT=json`
2. **Development**: Use `LOG_LEVEL=DEBUG` and `LOG_FORMAT=text`
3. **Disable if needed**: Set `PHOENIX_COLLECTOR_ENDPOINT=""` to disable OTEL
4. **Sampling**: For high-volume production, implement trace sampling

---

## Best Practices

### Logging
- Use structured logging (JSON) in production
- Add contextual information with `add_context()`
- Log at appropriate levels (DEBUG for details, INFO for operations)
- Never log sensitive data (API keys, passwords, PII)

### Tracing
- Create spans for logical operations, not every function
- Add meaningful attributes to spans
- Record events for important milestones
- Handle exceptions properly with `set_span_error()`

### Phoenix
- Keep Phoenix running during development
- Use filters to find specific traces
- Export traces for offline analysis
- Monitor error rates and performance trends

---

## Additional Resources

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Arize Phoenix Documentation](https://docs.arize.com/phoenix)
- [Python Logging Best Practices](https://docs.python.org/3/howto/logging.html)
- [Skills Framework GitHub](https://github.com/your-org/adk-skills)
