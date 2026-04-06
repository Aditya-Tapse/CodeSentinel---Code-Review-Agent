import re
from dataclasses import dataclass
from chunker import CodeChunk
import config


@dataclass
class PRInfo:
    repo: str
    pr_number: int
    title: str
    author: str
    base_branch: str
    head_branch: str
    files_changed: int
    additions: int
    deletions: int


def _parse_pr_url(url: str) -> tuple[str, int]:
    """Extract 'owner/repo' and PR number from a GitHub PR URL."""
    pattern = r"github\.com/([^/]+/[^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse GitHub PR URL: {url!r}\nExpected format: https://github.com/owner/repo/pull/123")
    return match.group(1), int(match.group(2))


def fetch_pr_chunks(pr_url: str) -> tuple[PRInfo, list[CodeChunk]]:
    """
    Fetch a GitHub PR diff and return PR metadata + list of CodeChunks (one per changed file).
    Requires GITHUB_TOKEN in environment for private repos or to avoid rate limits.
    """
    try:
        from github import Github, GithubException
    except ImportError:
        raise ImportError("PyGithub not installed. Run: pip install PyGithub")

    repo_name, pr_number = _parse_pr_url(pr_url)

    g = Github(config.GITHUB_TOKEN or None)

    try:
        repo = g.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch PR: {e}")

    info = PRInfo(
        repo=repo_name,
        pr_number=pr_number,
        title=pr.title,
        author=pr.user.login,
        base_branch=pr.base.ref,
        head_branch=pr.head.ref,
        files_changed=pr.changed_files,
        additions=pr.additions,
        deletions=pr.deletions,
    )

    chunks: list[CodeChunk] = []

    for pr_file in pr.get_files():
        filename = pr_file.filename
        patch = pr_file.patch  # unified diff string

        if patch is None:
            # Binary file or file too large
            continue

        # Extract only added lines (+) from the diff for review
        added_lines = []
        current_line = 0
        start_line = None

        for line in patch.splitlines():
            if line.startswith("@@"):
                # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
                m = re.search(r"\+(\d+)", line)
                if m:
                    current_line = int(m.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                if start_line is None:
                    start_line = current_line
                added_lines.append(line[1:])  # strip leading +
                current_line += 1
            elif not line.startswith("-"):
                current_line += 1

        if not added_lines:
            continue

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        lang_map = {
            "py": "python", "js": "javascript", "ts": "typescript",
            "jsx": "javascript", "tsx": "typescript", "java": "java",
            "go": "go", "rb": "ruby", "rs": "rust", "cpp": "cpp",
            "c": "c", "cs": "csharp", "php": "php",
        }
        language = lang_map.get(ext, ext or "unknown")

        chunks.append(CodeChunk(
            name=filename,
            chunk_type="raw_block",
            start_line=start_line or 1,
            end_line=(start_line or 1) + len(added_lines) - 1,
            code="\n".join(added_lines),
            language=language,
        ))

    return info, chunks