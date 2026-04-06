import json
import requests
from dataclasses import dataclass, field
from chunker import CodeChunk
import config


# ── Prompts ────────────────────────────────────────────────────────────────────

PASS_1_SYSTEM = """You are an expert security engineer and bug hunter.
Your job is to find real, concrete issues in code — not nitpicks.
Focus ONLY on:
- Logic errors and off-by-one bugs
- Null / None dereferences
- Security vulnerabilities: SQL injection, XSS, path traversal, command injection, insecure deserialization, hardcoded secrets
- Resource leaks (unclosed files, connections)
- Race conditions and concurrency bugs
- Unhandled exceptions that could crash the program
- Incorrect error handling

For each issue found, output a JSON array. Each item must have:
  "severity": "CRITICAL" | "WARNING"
  "title": short title
  "line_hint": approximate line number or null
  "description": clear explanation of the problem
  "fix": concrete fix suggestion

If no issues found, return an empty array [].
Return ONLY valid JSON. No markdown, no explanation outside the JSON."""

PASS_2_SYSTEM = """You are a senior software engineer doing a code quality review.
Focus ONLY on:
- Poor naming (variables, functions, classes)
- Functions that are too long or do too many things
- Missing or inadequate docstrings/comments
- Dead code or unused imports
- Repeated code that should be extracted
- Violation of language best practices (e.g. PEP8 for Python)
- Missing type hints (Python)
- Magic numbers/strings that should be constants

For each issue found, output a JSON array. Each item must have:
  "severity": "WARNING" | "SUGGESTION"
  "title": short title
  "line_hint": approximate line number or null
  "description": explanation
  "fix": concrete improvement suggestion

If no issues found, return an empty array [].
Return ONLY valid JSON. No markdown, no explanation outside the JSON."""


# ── Data model ─────────────────────────────────────────────────────────────────

@dataclass
class ReviewIssue:
    severity: str        # CRITICAL | WARNING | SUGGESTION
    title: str
    description: str
    fix: str
    line_hint: int | None = None
    chunk_name: str = ""


@dataclass
class ChunkReview:
    chunk: CodeChunk
    issues: list[ReviewIssue] = field(default_factory=list)
    error: str | None = None


# ── LLM backends ───────────────────────────────────────────────────────────────

def _call_ollama(system: str, user: str) -> str:
    url = f"{config.OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": config.OLLAMA_MODEL,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _call_claude(system: str, user: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text


def _call_openai(system: str, user: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content


def _llm_call(system: str, user: str) -> str:
    """Route to configured backend."""
    backend = config.BACKEND.lower()
    if backend == "ollama":
        return _call_ollama(system, user)
    elif backend == "claude":
        return _call_claude(system, user)
    elif backend == "openai":
        return _call_openai(system, user)
    else:
        raise ValueError(f"Unknown LLM_BACKEND: {backend!r}")


# ── Parsing ────────────────────────────────────────────────────────────────────

def _parse_issues(raw: str, chunk_name: str) -> list[ReviewIssue]:
    """Parse JSON array from LLM response, tolerating minor formatting issues."""
    # Strip markdown fences if present
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first [...] block
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return []
        else:
            return []

    issues = []
    for item in data:
        if not isinstance(item, dict):
            continue
        issues.append(ReviewIssue(
            severity=item.get("severity", "SUGGESTION").upper(),
            title=item.get("title", "Untitled issue"),
            description=item.get("description", ""),
            fix=item.get("fix", ""),
            line_hint=item.get("line_hint"),
            chunk_name=chunk_name,
        ))
    return issues


# ── Main review logic ──────────────────────────────────────────────────────────

def review_chunk(chunk: CodeChunk) -> ChunkReview:
    """Run both review passes on a single code chunk."""
    user_msg = f"Review this {chunk.language} code (chunk: {chunk.name}, lines {chunk.start_line}-{chunk.end_line}):\n\n```{chunk.language}\n{chunk.code}\n```"

    issues: list[ReviewIssue] = []
    error = None

    try:
        # Pass 1 — Security & bugs
        raw1 = _llm_call(PASS_1_SYSTEM, user_msg)
        issues.extend(_parse_issues(raw1, chunk.name))

        # Pass 2 — Style & best practices
        raw2 = _llm_call(PASS_2_SYSTEM, user_msg)
        issues.extend(_parse_issues(raw2, chunk.name))

    except Exception as e:
        error = str(e)

    return ChunkReview(chunk=chunk, issues=issues, error=error)


def review_chunks(chunks: list[CodeChunk], progress_cb=None) -> list[ChunkReview]:
    """Review all chunks, optionally calling progress_cb(i, total, chunk_name) after each."""
    results = []
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if progress_cb:
            progress_cb(i, total, chunk.name)
        results.append(review_chunk(chunk))
    return results