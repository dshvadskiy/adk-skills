#!/bin/bash
# Quick start script for Skills Framework Chat UI

set -e

echo "🚀 Starting Skills Framework Chat Server"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating template..."
    cat > .env << 'EOF'
# AWS Bedrock (default)
AWS_REGION=us-east-1
MODEL_ID=anthropic.claude-3-5-sonnet-20241022-v2:0

# Uncomment for other providers:
# OPENAI_API_KEY=your-key-here
# ANTHROPIC_API_KEY=your-key-here
# GOOGLE_API_KEY=your-key-here
EOF
    echo "✓ Created .env template. Please configure your API keys."
    echo ""
fi

# Install dependencies if needed
if ! uv pip list | grep -q fastapi; then
    echo "📦 Installing web dependencies..."
    uv sync --extra web
    echo ""
fi

# Default values
PORT=${PORT:-8000}
PROVIDER=${PROVIDER:-bedrock}

echo "Configuration:"
echo "  Provider: $PROVIDER"
echo "  Port: $PORT"
echo ""
echo "📍 Server will be available at: http://localhost:$PORT"
echo "Press Ctrl+C to stop"
echo ""

# Run server
uv run python examples/chat_server.py --provider "$PROVIDER" --port "$PORT"
