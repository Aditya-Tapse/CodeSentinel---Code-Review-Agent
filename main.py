import sys
import click
from pathlib import Path

import config
from chunker import chunk_file
from reviewer import review_chunks
from reporter import generate_markdown, print_rich_summary


def _progress(i: int, total: int, name: str):
    try:
        from rich.console import Console
        Console().print(f"  [dim]Reviewing chunk {i+1}/{total}:[/dim] [cyan]{name}[/cyan]")
    except ImportError:
        print(f"  Reviewing chunk {i+1}/{total}: {name}")


@click.group()
def cli():
    """CodeSentinel — Agentic AI Code Review Tool"""
    pass


@cli.command()
@click.option("--file", "filepath", default=None, help="Path to a local source file to review.")
@click.option("--pr", "pr_url", default=None, help="GitHub PR URL to review (e.g. https://github.com/owner/repo/pull/42).")
@click.option("--output", "-o", default=None, help="Save Markdown report to this file path.")
@click.option("--model", default=None, help="Override the Ollama/OpenAI model name.")
@click.option("--backend", default=None, help="Override LLM backend: ollama | claude | openai.")
def review(filepath, pr_url, output, model, backend):
    """Run a multi-pass AI code review on a file or GitHub PR."""

    if not filepath and not pr_url:
        click.echo("Provide either --file or --pr.\n")
        click.echo("Examples:")
        click.echo("  python main.py review --file app.py")
        click.echo("  python main.py review --pr https://github.com/owner/repo/pull/42")
        sys.exit(1)

    if filepath and pr_url:
        click.echo("Provide only one of --file or --pr, not both.")
        sys.exit(1)

    # Override config if flags provided
    if model:
        config.OLLAMA_MODEL = model
    if backend:
        config.BACKEND = backend

    active_model = config.OLLAMA_MODEL if config.BACKEND == "ollama" else config.OPENAI_MODEL

    # ── File mode ──────────────────────────────────────────────────────────────
    if filepath:
        path = Path(filepath)
        if not path.exists():
            click.echo(f"File not found: {filepath}")
            sys.exit(1)

        click.echo(f"\n CodeSentinel")
        click.echo(f"   Backend : {config.BACKEND} / {active_model}")
        click.echo(f"   File    : {filepath}\n")

        source = path.read_text(encoding="utf-8")
        chunks = chunk_file(source, filename=path.name)

        click.echo(f" Found {len(chunks)} chunk(s) to review:\n")
        for c in chunks:
            click.echo(f"   • [{c.chunk_type}] {c.name}  (lines {c.start_line}–{c.end_line})")

        click.echo(f"\n Running multi-pass LLM review...\n")
        reviews = review_chunks(chunks, progress_cb=_progress)

        print_rich_summary(reviews)

        source_label = str(filepath)
        pr_info = None

    # ── PR mode ────────────────────────────────────────────────────────────────
    else:
        click.echo(f"\n  CodeSentinel")
        click.echo(f"   Backend : {config.BACKEND} / {active_model}")
        click.echo(f"   PR      : {pr_url}\n")

        click.echo(" Fetching PR diff from GitHub...")
        try:
            from github_client import fetch_pr_chunks
            pr_info, chunks = fetch_pr_chunks(pr_url)
        except Exception as e:
            click.echo(f" Failed to fetch PR: {e}")
            sys.exit(1)

        click.echo(f"   PR #{pr_info.pr_number}: {pr_info.title}")
        click.echo(f"   Author : @{pr_info.author}")
        click.echo(f"   Files  : {pr_info.files_changed} changed  (+{pr_info.additions} / -{pr_info.deletions})\n")

        if not chunks:
            click.echo(" No reviewable code changes found in this PR.")
            sys.exit(0)

        click.echo(f" {len(chunks)} file chunk(s) to review:\n")
        for c in chunks:
            click.echo(f"   • {c.name}")

        click.echo(f"\n Running multi-pass LLM review...\n")
        reviews = review_chunks(chunks, progress_cb=_progress)

        print_rich_summary(reviews)
        source_label = pr_url

    # ── Save report ────────────────────────────────────────────────────────────
    report_md = generate_markdown(
        reviews,
        source_label=source_label,
        pr_info=pr_info if pr_url else None,
        backend=config.BACKEND,
        model=active_model,
    )

    if output:
        out_path = Path(output)
        out_path.write_text(report_md, encoding="utf-8")
        click.echo(f" Report saved to: {out_path.resolve()}\n")
    else:
        # Auto-save alongside source file or in cwd
        auto_name = "codesentinel_report.md"
        Path(auto_name).write_text(report_md, encoding="utf-8")
        click.echo(f" Report saved to: {Path(auto_name).resolve()}\n")


@cli.command()
def models():
    """List available Ollama models."""
    import requests
    try:
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        click.echo("\n Available Ollama models:\n")
        for m in data.get("models", []):
            marker = "  active" if m["name"] == config.OLLAMA_MODEL else ""
            click.echo(f"   • {m['name']}{marker}")
        click.echo()
    except Exception as e:
        click.echo(f" Could not reach Ollama at {config.OLLAMA_BASE_URL}: {e}")


@cli.command()
def config_show():
    """Show current configuration."""
    click.echo(f"\n  CodeSentinel Configuration\n")
    click.echo(f"   LLM_BACKEND   : {config.BACKEND}")
    click.echo(f"   OLLAMA_MODEL  : {config.OLLAMA_MODEL}")
    click.echo(f"   OLLAMA_BASE_URL: {config.OLLAMA_BASE_URL}")
    click.echo(f"   OPENAI_MODEL  : {config.OPENAI_MODEL}")
    click.echo(f"   GITHUB_TOKEN  : {'set ' if config.GITHUB_TOKEN else 'not set '}")
    click.echo(f"   ANTHROPIC_KEY : {'set ' if config.ANTHROPIC_API_KEY else 'not set '}")
    click.echo(f"   MAX_CHUNK_LINES: {config.MAX_CHUNK_LINES}\n")


if __name__ == "__main__":
    cli()