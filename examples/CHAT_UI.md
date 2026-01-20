# Skills Framework Chat UI

A modern web-based chat interface for demonstrating the Skills meta-tool architecture with Google ADK.

## Features

- **Real-time chat interface** with clean, modern UI
- **Progressive skill activation** - skills load on-demand when needed
- **Visual skill indicators** - see which skills are available and active
- **Multiple LLM providers** - Bedrock, OpenAI, Anthropic, Gemini, Azure
- **WebSocket support** - ready for streaming responses (future enhancement)
- **Session management** - maintains conversation context

## Quick Start

### 1. Install Dependencies

```bash
# Install web dependencies
uv sync --extra web
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# For AWS Bedrock (default)
AWS_REGION=us-east-1
MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# For OpenAI
# OPENAI_API_KEY=your-key-here

# For Anthropic
# ANTHROPIC_API_KEY=your-key-here

# For Google Gemini
# GOOGLE_API_KEY=your-key-here
```

### 3. Run the Server

```bash
# Default (uses Bedrock)
uv run python examples/chat_server.py

# With specific provider
uv run python examples/chat_server.py --provider openai

# Custom port
uv run python examples/chat_server.py --port 8080
```

### 4. Open Browser

Navigate to `http://localhost:8000`

## Architecture

### Backend (`chat_server.py`)

FastAPI server with:
- **REST API** (`/api/chat`) - Standard request/response
- **WebSocket** (`/ws/chat`) - Real-time streaming (ready for enhancement)
- **Skills API** (`/api/skills`) - List available skills
- **Agent integration** - Uses `AgentBuilder` and `ADKAdapter`

### Frontend (`static/chat.html`)

Single-page application with:
- **Message history** - User and assistant messages
- **Skill visualization** - Available and active skills
- **Typing indicators** - Shows when agent is thinking
- **Suggestion chips** - Quick-start prompts
- **Responsive design** - Works on desktop and mobile

## API Endpoints

### GET `/api/skills`

Returns available skills:

```json
{
  "skills": [
    {
      "name": "hello-world",
      "description": "A simple greeting skill"
    }
  ]
}
```

### POST `/api/chat`

Send a chat message:

**Request:**
```json
{
  "message": "Hello!",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "response": "Hello! How can I help you?",
  "session_id": "abc-123",
  "active_skills": ["hello-world"]
}
```

### WebSocket `/ws/chat`

Real-time chat (ready for streaming):

**Send:**
```json
{
  "message": "Hello!"
}
```

**Receive:**
```json
{
  "type": "response",
  "content": "Hello! How can I help?",
  "session_id": "abc-123",
  "active_skills": []
}
```

## Skills Demonstration

The chat UI showcases the core Skills framework features:

1. **Progressive Disclosure** - Skills load only when activated
2. **Two-Message Pattern** - Visible metadata + hidden instructions
3. **Context Management** - Session-based conversation tracking
4. **Skill Lifecycle** - Activation/deactivation visualization

Try these prompts to see skills in action:

- "What skills do you have?" - Lists available skills
- "Say hello in a creative way" - Activates `hello-world` skill
- "Help me brainstorm ideas" - Activates `brainstorming` skill

## Customization

### Adding Custom Styles

Edit `examples/static/chat.html` and modify the `<style>` section.

### Changing Colors

Update the gradient in the CSS:

```css
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Adding New Skills

1. Create a new skill directory in `skills/`
2. Add a `SKILL.md` file with YAML frontmatter
3. Restart the server
4. Skills appear automatically in the UI

## Development

### Running in Development Mode

```bash
# Auto-reload on code changes
uv run uvicorn examples.chat_server:app --reload --port 8000
```

### Testing Different Providers

```bash
# Test with OpenAI
uv run python examples/chat_server.py --provider openai --model gpt-4o

# Test with Anthropic
uv run python examples/chat_server.py --provider anthropic

# Test with Gemini
uv run python examples/chat_server.py --provider gemini
```

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Streaming responses via WebSocket
- [ ] Message editing and regeneration
- [ ] Export conversation history
- [ ] Dark mode toggle
- [ ] Skill configuration UI
- [ ] Multi-user support with authentication
- [ ] Conversation branching
- [ ] Code syntax highlighting in responses

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
uv run python examples/chat_server.py --port 8080
```

### Skills Not Loading

Check that `skills/` directory exists and contains valid `SKILL.md` files.

### Agent Not Responding

Verify your API keys are set correctly in `.env` and the provider is configured.

### CORS Errors

The server allows all origins by default. For production, configure CORS properly:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Production Deployment

For production use:

1. Set proper CORS origins
2. Add authentication/authorization
3. Use environment variables for secrets
4. Enable HTTPS
5. Add rate limiting
6. Configure logging and monitoring
7. Use a production ASGI server (already using uvicorn)

Example production command:

```bash
uv run uvicorn examples.chat_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

## License

Same as the Skills Framework project.
