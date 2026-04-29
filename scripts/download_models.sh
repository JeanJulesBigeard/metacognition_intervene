#!/usr/bin/env bash
set -euo pipefail

# Start Ollama if needed
if ! curl -sf http://localhost:11434/api/tags >/dev/null; then
  echo "Ollama is not responding on localhost:11434."
  echo "Start it first with: ollama serve"
  exit 1
fi

MODELS=(
  "qwen2.5:14b"
  "olmo2:13b"
  "mistral-small"
  "gemma4:26b"
  "qwen3.5:27b"
  "gemma4:31b"
  "deepseek-r1:32b"
)

for model in "${MODELS[@]}"; do
  echo "=================================================="
  echo "Pulling $model"
  echo "=================================================="
  ollama pull "$model"
done

echo
echo "Done. Installed models:"
ollama list