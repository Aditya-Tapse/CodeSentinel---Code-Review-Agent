# 🛡️ CodeSentinel

> **Agentic AI code review tool** — multi-pass LLM analysis for bugs, security vulnerabilities, and code quality issues.

Built with Python, Ollama, CodeLlama, AST parsing, and GitHub API integration. Runs entirely locally at zero cost using Ollama, with optional cloud LLM support (Claude / OpenAI).

---

## Features

- **AST-based semantic chunking** — splits Python code into logical units (functions/classes) using Python's `ast` module, preserving context for accurate analysis
- **Multi-pass LLM chaining** — separates concern detection across two passes:
  - Pass 1: Logic errors, security vulnerabilities (SQLi, XSS, path traversal, hardcoded secrets, race conditions)
  - Pass 2: Style, naming, best practices, missing docstrings, dead code
- **Severity-ranked reports** — issues ranked as `CRITICAL` / `WARNING` / `SUGGESTION`
- **GitHub PR integration** — fetches diffs via GitHub API and reviews changed lines per file
- **Local-first** — runs on Ollama (CodeLlama / Mistral) with zero API cost
- **Pluggable backends** — switch to Claude or OpenAI via environment config
- **Rich terminal output** — colored, formatted output via `rich`
- **Markdown reports** — auto-saved after every review

---

## Project Structure

```
codesentinel/
├── main.py              # CLI entrypoint (Click)
├── chunker.py           # AST-based semantic code chunker
├── reviewer.py          # Multi-pass LLM chaining logic
├── github_client.py     # GitHub PR diff fetcher
├── reporter.py          # Markdown report + terminal output
├── config.py            # Environment/backend configuration
├── requirements.txt
├── .env.example
└── sample_buggy.py      # Test file with intentional bugs
```

---

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/codesentinel.git
cd codesentinel
```

### 2. Create a virtual environment

```bash
python -m venv venv

# Activate
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install and start Ollama

```bash
# Install (Linux / macOS)
curl -fsSL https://ollama.com/install.sh | sh

# Pull the recommended model
ollama pull codellama:13b

# Ollama runs automatically as a background service
# Verify it's up:
curl http://localhost:11434/api/tags
```

### 5. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
# LLM Backend: "ollama" | "claude" | "openai"
LLM_BACKEND=ollama
OLLAMA_MODEL=codellama:13b
OLLAMA_BASE_URL=http://localhost:11434

# Optional cloud APIs
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o

# Required for --pr mode
GITHUB_TOKEN=your_github_token_here

# Chunking
MAX_CHUNK_LINES=150
```

---

## Usage

### Review a local file

```bash
python main.py review --file path/to/your_script.py
```

### Review a GitHub PR

```bash
python main.py review --pr https://github.com/owner/repo/pull/42
```

### Save report to a specific file

```bash
python main.py review --file app.py --output report.md
```

### Override model or backend at runtime

```bash
python main.py review --file app.py --model mistral:7b
python main.py review --file app.py --backend openai
```

### Other commands

```bash
# List available Ollama models
python main.py models

# Show current configuration
python main.py config-show
```
t
