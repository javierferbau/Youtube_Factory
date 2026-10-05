#!/bin/bash
export OLLAMA_HOST=0.0.0.0:11435
export OLLAMA_MODELS=/home/javierferb/.ollama/models
exec /home/javierferb/.local/bin/ollama serve
