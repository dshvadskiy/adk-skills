#!/usr/bin/env python3
"""FastAPI chat server for demonstrating Skills framework.

Provides:
- REST API for chat interactions
- WebSocket support for real-time streaming
- Skill activation visualization
- Multiple LLM provider support

Usage:
    # Install web dependencies
    uv sync --extra web

    # Run server (default: Bedrock)
    uv run python examples/chat_server.py

    # Run with specific provider
    uv run python examples/chat_server.py --provider openai

    # Custom port
    uv run python examples/chat_server.py --port 8080

Then open http://localhost:8000 in your browser.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any

import re
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Suppress ADK warnings
warnings.filterwarnings("ignore", message=".*EXPERIMENTAL.*")
warnings.filterwarnings("ignore", message=".*non-text parts.*")

# Configure LiteLLM
import litellm
litellm.drop_params = True

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from skill_framework.agent import AgentBuilder
from skill_framework.integration.adk_adapter import ADKAdapter
from skill_framework.artifact_publisher import (
    ArtifactPublisher, LocalBackend, get_publisher
)

# Setup logging
logger = logging.getLogger(__name__)


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    active_skills: list[str]
    files: list[dict[str, str]] | None = None  # [{"filename": "x.pptx", "url": "/api/files/abc123", "mime_type": "..."}]


# Global state
app = FastAPI(title="Skills Framework Chat")
agent_instance = None
builder_instance = None
artifact_publisher: ArtifactPublisher | None = None
tool_outputs: list[str] = []  # Store tool outputs for FILE_OUTPUT extraction


def extract_file_outputs_from_tool_output(tool_output: str) -> list[dict[str, str]] | None:
    """Extract file output markers from tool output and publish artifacts."""
    pattern = r'FILE_OUTPUT:\s*\{"path":\s*"([^"]+)",\s*"filename":\s*"([^"]+)",\s*"mime_type":\s*"([^"]+)"\}'
    matches = re.findall(pattern, tool_output)
    
    if not matches:
        return None
    
    publisher = get_publisher()
    files = []
    valid_paths = [(Path(p), fn, mt) for p, fn, mt in matches if Path(p).exists()]
    
    if not valid_paths:
        return None
    
    if len(valid_paths) == 1:
        path, filename, mime_type = valid_paths[0]
        artifact = publisher.publish(path)
        files.append({
            "filename": artifact.filename,
            "url": artifact.url,
            "mime_type": artifact.mime_type,
        })
    else:
        paths = [p for p, _, _ in valid_paths]
        artifact = publisher.publish_many(paths)
        files.append({
            "filename": artifact.filename,
            "url": artifact.url,
            "mime_type": artifact.mime_type,
        })
    
    return files


def bash_tool_wrapper(original_bash_tool):
    """Wrap bash_tool to capture FILE_OUTPUT markers."""
    def wrapper(command: str, working_directory: str | None = None) -> str:
        result = original_bash_tool(command, working_directory)
        tool_outputs.append(result)
        return result
    return wrapper


def extract_file_outputs() -> list[dict[str, str]] | None:
    """Extract FILE_OUTPUT from all captured tool outputs."""
    all_files = []
    for output in tool_outputs:
        files = extract_file_outputs_from_tool_output(output)
        if files:
            all_files.extend(files)
    tool_outputs.clear()
    return all_files if all_files else None


def create_model(provider: str, model_name: str | None = None):
    """Create ADK-compatible model based on provider."""
    if provider == "gemini":
        return model_name or "gemini-2.0-flash"

    elif provider == "openai":
        from google.adk.models.lite_llm import LiteLlm
        model = model_name or "gpt-4o"
        return LiteLlm(model=f"openai/{model}")

    elif provider == "anthropic":
        from google.adk.models.lite_llm import LiteLlm
        model = model_name or "claude-3-5-sonnet-20241022"
        return LiteLlm(model=f"anthropic/{model}")

    elif provider == "bedrock":
        from google.adk.models.lite_llm import LiteLlm
        model_id = model_name or os.getenv("MODEL_ID") or os.getenv("MODEL_NAME", "anthropic.claude-3-5-sonnet-20241022-v2:0")
        model_id = model_id.replace("bedrock/", "")
        
        if "arn:aws:bedrock" in model_id or "inference-profile" in model_id:
            model_str = f"bedrock/converse/{model_id}"
        else:
            model_str = f"bedrock/{model_id}"
        
        return LiteLlm(model=model_str)

    elif provider == "azure":
        from google.adk.models.lite_llm import LiteLlm
        if not model_name:
            raise ValueError("Azure requires model name")
        return LiteLlm(model=f"azure/{model_name}")

    else:
        raise ValueError(f"Unknown provider: {provider}")


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup."""
    global agent_instance, builder_instance, artifact_publisher
    
    # Initialize Phoenix telemetry FIRST (before creating any agents)
    from skill_framework.observability.telemetry import setup_telemetry
    setup_telemetry(project_name="skill_chat_server", auto_instrument=True)
    logger.info("Phoenix telemetry initialized")
    
    # Initialize artifact publisher (auto-configures from env)
    artifact_publisher = get_publisher()
    
    # Monkey-patch ScriptExecutor to capture tool outputs
    from skill_framework.core.script_executor import ScriptExecutor
    original_execute = ScriptExecutor.execute
    
    def patched_execute(self, *args, **kwargs):
        result = original_execute(self, *args, **kwargs)
        if result.stdout:
            tool_outputs.append(result.stdout)
        return result
    
    ScriptExecutor.execute = patched_execute
    
    # Skills directory loaded from SKILLS_DIR env var or defaults to ./skills
    from skill_framework.config import Config
    skills_dir = Config.get_skills_dir()
    
    provider = os.getenv("LLM_PROVIDER", "bedrock")
    model_name = os.getenv("MODEL_NAME")
    
    logger.info(f"Initializing agent with provider: {provider}")
    logger.info(f"Skills directory: {skills_dir}")
    model = create_model(provider, model_name)
    
    adapter = ADKAdapter(model=model, app_name="skill_chat_demo")
    builder_instance = AgentBuilder()  # Uses SKILLS_DIR from .env
    
    agent_instance = builder_instance.create_agent(
        adapter=adapter,
        name="chat_agent",
        instruction="""You are a helpful assistant with access to skills and tools.

CRITICAL INSTRUCTIONS:
- When a user asks you to CREATE, GENERATE, or BUILD something, you MUST use the appropriate tools
- DO NOT just describe what you would create - actually create it using tools
- When a skill provides bash_tool, read_file, or write_file, USE THEM to accomplish tasks
- After activating a skill, READ the instructions carefully and FOLLOW them exactly
- If instructions say to use bash_tool, you MUST call bash_tool - do not skip this step

Example of CORRECT behavior:
User: "Create a presentation"
You: *activates skill* → *calls bash_tool to run script* → "Done! Here's your file"

Example of INCORRECT behavior:
User: "Create a presentation"  
You: *activates skill* → "Here's what the presentation contains..." ❌ NO FILE CREATED

When appropriate, use skills to enhance your responses.""",
    )
    
    logger.info(f"Agent initialized with {len(agent_instance.available_skills)} skills")


@app.get("/", response_class=HTMLResponse)
async def get_index():
    """Serve the chat UI."""
    html_file = Path(__file__).parent / "static" / "chat.html"
    if html_file.exists():
        return FileResponse(html_file)
    
    # Fallback inline HTML if static file doesn't exist
    return HTMLResponse(content=get_inline_html())


@app.get("/favicon.ico")
async def get_favicon():
    """Return empty favicon to prevent 404."""
    return HTMLResponse(content="", status_code=204)


@app.get("/api/files/{file_id}")
async def download_file(file_id: str):
    """Download a generated file (local backend only)."""
    publisher = get_publisher()
    
    # Only works with LocalBackend
    if not isinstance(publisher.backend, LocalBackend):
        raise HTTPException(status_code=400, detail="Direct download not available with S3 backend")
    
    file_path = publisher.backend.get_file(file_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )


@app.get("/api/skills")
async def get_skills():
    """Get available skills."""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    return {
        "skills": [
            {"name": name, "description": desc}
            for name, desc in agent_instance.available_skills.items()
        ]
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat message via REST API."""
    if not agent_instance:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    # Use agent's session_id (each agent has its own session)
    # For multi-session support, we'd need to create separate agents per session
    session_id = agent_instance.session_id
    
    try:
        tool_outputs.clear()  # Clear previous outputs
        response = await agent_instance.chat(request.message)
        
        # Get active skills
        active_skills = agent_instance.active_skills
        
        # Extract files from tool outputs
        files = extract_file_outputs()
        
        return ChatResponse(
            response=response,
            session_id=session_id,
            active_skills=active_skills,
            files=files,
        )
    except Exception as e:
        import traceback
        logger.error(f"Error in chat endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Handle chat via WebSocket for streaming responses."""
    await websocket.accept()
    session_id = agent_instance.session_id
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_message = message_data.get("message", "")
            
            if not user_message:
                continue
            
            # Send acknowledgment
            await websocket.send_json({
                "type": "ack",
                "session_id": session_id,
            })
            
            # Get response (for now, non-streaming)
            try:
                response = await agent_instance.chat(user_message)
                
                # Get active skills
                active_skills = agent_instance.active_skills
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "content": response,
                    "session_id": session_id,
                    "active_skills": active_skills,
                })
                
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "error": str(e),
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")


def get_inline_html() -> str:
    """Fallback inline HTML if static file doesn't exist."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skills Framework Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            width: 90%;
            max-width: 800px;
            height: 90vh;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
        }
        .header {
            padding: 20px;
            border-bottom: 1px solid #e5e7eb;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 16px 16px 0 0;
        }
        .header h1 { font-size: 24px; margin-bottom: 8px; }
        .header p { font-size: 14px; opacity: 0.9; }
        .skills-bar {
            padding: 12px 20px;
            background: #f9fafb;
            border-bottom: 1px solid #e5e7eb;
            font-size: 13px;
            color: #6b7280;
        }
        .skill-tag {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 12px;
            margin-right: 8px;
            font-size: 12px;
        }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f9fafb;
        }
        .message {
            margin-bottom: 16px;
            display: flex;
            gap: 12px;
        }
        .message.user { justify-content: flex-end; }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 12px;
            line-height: 1.5;
        }
        .message.user .message-content {
            background: #667eea;
            color: white;
        }
        .message.assistant .message-content {
            background: white;
            color: #1f2937;
            border: 1px solid #e5e7eb;
        }
        .input-area {
            padding: 20px;
            border-top: 1px solid #e5e7eb;
            background: white;
            border-radius: 0 0 16px 16px;
        }
        .input-container {
            display: flex;
            gap: 12px;
        }
        input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
        }
        button {
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
        }
        button:hover { background: #5568d3; }
        button:disabled { background: #9ca3af; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 Skills Framework Chat</h1>
            <p>Demonstrating progressive skill activation</p>
        </div>
        <div class="skills-bar">
            <span id="skills-label">Available skills: Loading...</span>
            <span id="active-skills"></span>
        </div>
        <div class="messages" id="messages"></div>
        <div class="input-area">
            <div class="input-container">
                <input type="text" id="message-input" placeholder="Type your message..." />
                <button id="send-btn">Send</button>
            </div>
        </div>
    </div>
    
    <script>
        let sessionId = null;
        
        async function loadSkills() {
            const response = await fetch('/api/skills');
            const data = await response.json();
            document.getElementById('skills-label').textContent = 
                `Available skills: ${data.skills.map(s => s.name).join(', ')}`;
        }
        
        function addMessage(role, content) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            messageDiv.innerHTML = `<div class="message-content">${content}</div>`;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function updateActiveSkills(skills) {
            const activeSkillsDiv = document.getElementById('active-skills');
            if (skills && skills.length > 0) {
                activeSkillsDiv.innerHTML = skills.map(s => 
                    `<span class="skill-tag">✓ ${s}</span>`
                ).join('');
            } else {
                activeSkillsDiv.innerHTML = '';
            }
        }
        
        async function sendMessage() {
            const input = document.getElementById('message-input');
            const message = input.value.trim();
            if (!message) return;
            
            input.value = '';
            addMessage('user', message);
            
            const sendBtn = document.getElementById('send-btn');
            sendBtn.disabled = true;
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message, session_id: sessionId })
                });
                
                const data = await response.json();
                sessionId = data.session_id;
                addMessage('assistant', data.response);
                updateActiveSkills(data.active_skills);
            } catch (error) {
                addMessage('assistant', `Error: ${error.message}`);
            } finally {
                sendBtn.disabled = false;
                input.focus();
            }
        }
        
        document.getElementById('send-btn').addEventListener('click', sendMessage);
        document.getElementById('message-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
        
        loadSkills();
    </script>
</body>
</html>
"""


def main():
    """Run the chat server."""
    parser = argparse.ArgumentParser(description="Skills Framework Chat Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--provider", choices=["gemini", "openai", "anthropic", "bedrock", "azure"],
                       help="LLM provider (overrides .env)")
    parser.add_argument("--model", help="Model name (overrides .env)")
    args = parser.parse_args()
    
    # Set environment variables from args if provided
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["MODEL_NAME"] = args.model
    
    import uvicorn
    logger.info(f"\n🚀 Starting Skills Framework Chat Server")
    logger.info(f"📍 Open http://localhost:{args.port} in your browser\n")
    
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
