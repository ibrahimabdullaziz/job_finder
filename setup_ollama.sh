#!/bin/bash
# Setup Ollama and pull Qwen 3.5 model for local LLM inference

set -e

echo "=== Job Finder: Ollama + Qwen 3.5 Setup ==="

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ollama
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
else
    echo "Ollama already installed: $(which ollama)"
fi

# Start Ollama server if not running
if ! curl -s http://localhost:11434/api/tags &> /dev/null; then
    echo "Starting Ollama server..."
    ollama serve &
    sleep 3
fi

# Pull the model
MODEL="${1:-qwen3.5:9b}"
echo "Pulling model: $MODEL"
ollama pull "$MODEL"

# Verify
echo ""
echo "=== Verification ==="
echo "Available models:"
ollama list
echo ""
echo "Testing generation..."
curl -s http://localhost:11434/api/generate -d "{\"model\": \"$MODEL\", \"prompt\": \"Say hello in one sentence.\", \"stream\": false}" | python3 -c "import sys,json; print(json.load(sys.stdin).get('response','ERROR'))"
echo ""
echo "=== Setup complete! ==="
