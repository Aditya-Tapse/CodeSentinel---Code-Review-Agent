import os
from dotenv import load_dotenv

load_dotenv()

# LLM Backend: "ollama" | "claude" | "openai"
BACKEND = os.getenv("LLM_BACKEND", "ollama")

# Ollama settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "codellama:13b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Cloud API keys (optional)
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

# GitHub
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

# Review settings
MAX_CHUNK_LINES = int(os.getenv("MAX_CHUNK_LINES", "150"))