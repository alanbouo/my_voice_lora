#!/bin/bash
set -e

# Start Ollama if not already running
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 3
fi

# Ensure model is available
ollama pull qwen2.5:7b

# Start FastAPI
echo "Starting FastAPI..."
source .venv/bin/activate
uvicorn api:app --host 127.0.0.1 --port 8000
