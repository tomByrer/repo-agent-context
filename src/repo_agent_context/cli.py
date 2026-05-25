from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.progress import track

from repo_agent_context.git import (
    GitDetectionError,
    branches_ahead_of_base,
    detect_upstream_and_fork,
)
from repo_agent_context.github import check_gh_available, check_repo_access, gh_json, run_gh
from repo_agent_context.model import ContextConfig
from repo_agent_context.render import (
    render_branches_ahead,
    render_issue,
    render_issues_index,
    render_pr,
    render_prs_index,
    render_relations,
)
from repo_agent_context.templates import render_agent_md

app = typer.Typer(no_args_is_help=True)
console = Console()
DEFAULT_AGENT_FILE = Path("AGENT.md")
DEFAULT_OUT_DIR = Path("agent_context")


def load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise typer.BadParameter(
            f"Metadata file not found: {path}\n"
            "Run `repo-agent-context build` first."
        )

    metadata: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return metadata


def update_gitignore(config: ContextConfig) -> None:
    if not config.update_gitignore:
        return

    gitignore_path = Path(".gitignore")

    wanted_entries = [
        f"{config.out_dir.as_posix().rstrip('/')}/",
        config.agent_file.as_posix(),
    ]

    if gitignore_path.exists():
        existing_text = gitignore_path.read_text(encoding="utf-8")
    else:
        existing_text = ""

    existing_lines = {
        line.strip()
        for line in existing_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    missing_entries = [
        entry
        for entry in wanted_entries
        if entry not in existing_lines
    ]

    if not missing_entries:
        return

    parts: list[str] = []

    if existing_text:
        parts.append(existing_text.rstrip())
        parts.append("")

    parts.append("# Local coding-agent context")
    parts.extend(missing_entries)
    parts.append("")

    gitignore_path.write_text("\n".join(parts), encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_issues(config: ContextConfig) -> list[dict[str, Any]]:
    state = "all" if config.include_closed else "open"

    list_fields = (
        "number,title,state,author,labels,createdAt,updatedAt,url,body"
    )
    view_fields = (
        "number,title,state,author,labels,createdAt,updatedAt,url,body,comments"
    )

    issues = gh_json(
        [
            "issue",
            "list",
            "--repo",
            config.upstream,
            "--state",
            state,
            "--limit",
            str(config.issue_limit),
            "--json",
            list_fields,
        ]
    )

    write_json(config.out_dir / "issues.json", issues)

    full_issues: list[dict[str, Any]] = []
    for issue in track(issues, description="Fetching issues"):
        number = str(issue["number"])
        full = gh_json(
            [
                "issue",
                "view",
                number,
                "--repo",
                config.upstream,
                "--comments",
                "--json",
                view_fields,
            ]
        )
        full_issues.append(full)
        write_json(config.out_dir / "issues" / f"{number}.json", full)
        write_text(config.out_dir / "issues" / f"{number}.md", render_issue(full))

    return full_issues


def build_prs(config: ContextConfig) -> list[dict[str, Any]]:
    state = "all" if config.include_closed else "open"

    list_fields = (
        "number,title,state,author,labels,createdAt,updatedAt,url,body,"
        "isDraft,mergeable,reviewDecision,headRefName,baseRefName,statusCheckRollup"
    )
    view_fields = (
        "number,title,state,author,labels,createdAt,updatedAt,url,body,"
        "comments,isDraft,mergeable,reviewDecision,headRefName,baseRefName,"
        "files,commits,statusCheckRollup"
    )

    prs = gh_json(
        [
            "pr",
            "list",
            "--repo",
            config.upstream,
            "--state",
            state,
            "--limit",
            str(config.pr_limit),
            "--json",
            list_fields,
        ]
    )

    write_json(config.out_dir / "prs.json", prs)

    full_prs: list[dict[str, Any]] = []
    for pr in track(prs, description="Fetching pull requests"):
        number = str(pr["number"])
        full = gh_json(
            [
                "pr",
                "view",
                number,
                "--repo",
                config.upstream,
                "--comments",
                "--json",
                view_fields,
            ]
        )
        full_prs.append(full)
        write_json(config.out_dir / "prs" / f"{number}.json", full)
        write_text(config.out_dir / "prs" / f"{number}.md", render_pr(full))

        diff = run_gh(["pr", "diff", number, "--repo", config.upstream])
        write_text(config.out_dir / "prs" / f"{number}.diff", diff)

    return full_prs


def build_branches(config: ContextConfig) -> dict[str, Any]:
    branches = branches_ahead_of_base(config.upstream)
    write_json(config.out_dir / "branches_ahead.json", branches)
    write_text(config.out_dir / "index" / "branches_ahead.md", render_branches_ahead(branches))
    return branches


def build_metadata(config: ContextConfig) -> None:
    metadata = {
        "upstream": config.upstream,
        "fork": config.fork,
        "out_dir": str(config.out_dir),
        "agent_file": str(config.agent_file),
        "issue_limit": config.issue_limit,
        "pr_limit": config.pr_limit,
        "include_closed": config.include_closed,
    }

    write_json(config.out_dir / "metadata.json", metadata)


def write_agent_file(config: ContextConfig) -> None:
    if config.agent_file.exists() and not config.overwrite_agent:
        console.print(
            f"[yellow]Skipping existing {config.agent_file}. "
            "Use --overwrite-agent to replace it.[/yellow]"
        )
        return

    text = render_agent_md(
        upstream=config.upstream,
        fork=config.fork,
        context_dir=str(config.out_dir),
    )
    write_text(config.agent_file, text)

def run_build(config: ContextConfig) -> None:
    console.print("[bold]Detected repository configuration:[/bold]")
    console.print(f"Upstream: [bold]{config.upstream}[/bold]")
    console.print(f"Fork: [bold]{config.fork or 'none'}[/bold]")
    console.print(f"Output directory: [bold]{config.out_dir}[/bold]")
    console.print(f"Agent file: [bold]{config.agent_file}[/bold]")
    console.print()

    console.print("[bold]Checking GitHub CLI...[/bold]")
    check_gh_available()

    console.print(f"[bold]Checking upstream repository:[/bold] {config.upstream}")
    check_repo_access(config.upstream)

    if config.fork:
        console.print(f"[bold]Checking fork repository:[/bold] {config.fork}")
        check_repo_access(config.fork)

    config.out_dir.mkdir(parents=True, exist_ok=True)

    build_metadata(config)

    issues = build_issues(config)
    prs = build_prs(config)
    branches = build_branches(config)

    write_text(config.out_dir / "index" / "issues_index.md", render_issues_index(issues))
    write_text(config.out_dir / "index" / "prs_index.md", render_prs_index(prs))
    write_text(config.out_dir / "index" / "relations.md", render_relations(issues, prs))

    write_agent_file(config)

    update_gitignore(config)

    console.print()
    console.print("[green]Done.[/green]")
    console.print(f"Context directory: [bold]{config.out_dir}[/bold]")
    console.print(f"Agent file: [bold]{config.agent_file}[/bold]")
    console.print(f"Issues fetched: [bold]{len(issues)}[/bold]")
    console.print(f"Pull requests fetched: [bold]{len(prs)}[/bold]")
    console.print(f"Branches ahead of master: [bold]{len(branches.get('branches') or [])}[/bold]")




@app.command()
def status(
    upstream: str | None = typer.Option(None, "--upstream", "-u"),
    fork: str | None = typer.Option(None, "--fork", "-f"),
) -> None:
    try:
        detected_upstream, detected_fork = detect_upstream_and_fork(upstream, fork)
    except GitDetectionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"Upstream: [bold]{detected_upstream}[/bold]")
    console.print(f"Fork: [bold]{detected_fork or 'none'}[/bold]")

@app.command()
def build(

    upstream: str | None = typer.Option(
        None,
        "--upstream",
        "-u",
        help="Upstream GitHub repository, e.g. arnowaschk/repo-agent-context. "
        "If omitted, it is detected from the git remote named 'upstream', "
        "falling back to 'origin'.",
    ),
    fork: str | None = typer.Option(
        None,
        "--fork",
        "-f",
        help="Fork GitHub repository, e.g. myname/repo-agent-context. "
        "If omitted, it is detected from the git remote named 'origin'.",
    ),

    out: Annotated[
        Path,
        typer.Option(
            "--out",
            "-o",
            help="Output directory for generated context.",
        ),
    ] = DEFAULT_OUT_DIR,
    agent_file: Annotated[
        Path,
        typer.Option(
            "--agent-file",
            help="Path of generated AGENT.md.",
        ),
    ] = DEFAULT_AGENT_FILE,
    issue_limit: int = typer.Option(
        300,
        "--issue-limit",
        help="Maximum number of issues to fetch.",
    ),
    pr_limit: int = typer.Option(
        300,
        "--pr-limit",
        help="Maximum number of pull requests to fetch.",
    ),
    include_closed: bool = typer.Option(
        False,
        "--include-closed",
        help="Fetch closed issues and PRs as well.",
    ),
    overwrite_agent: bool = typer.Option(
        False,
        "--overwrite-agent",
        help="Overwrite AGENT.md if it already exists.",
    ),
    update_gitignore_file: bool = typer.Option(
        True,
        "--update-gitignore/--no-update-gitignore",
        help="Create or update .gitignore with generated context paths.",
    ),
) -> None:
    try:
        detected_upstream, detected_fork = detect_upstream_and_fork(upstream, fork)
    except GitDetectionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    config = ContextConfig(
        upstream=detected_upstream,
        fork=detected_fork,
        out_dir=out,
        agent_file=agent_file,
        issue_limit=issue_limit,
        pr_limit=pr_limit,
        include_closed=include_closed,
        overwrite_agent=overwrite_agent,
        update_gitignore=update_gitignore_file,
    )

    run_build(config)


@app.command()
def refresh(
    out: Annotated[
        Path,
        typer.Option(
            "--out",
            "-o",
            help="Context directory containing metadata.json. Default: agent_context.",
        ),
    ] = DEFAULT_OUT_DIR,
    upstream: str | None = typer.Option(
        None,
        "--upstream",
        "-u",
        help="Upstream GitHub repository. Used only if metadata.json is missing or to override it.",
    ),
    fork: str | None = typer.Option(
        None,
        "--fork",
        "-f",
        help="Fork GitHub repository. Used only if metadata.json is missing or to override it.",
    ),
    issue_limit: int = typer.Option(
        300,
        "--issue-limit",
        help="Maximum number of issues to fetch.",
    ),
    pr_limit: int = typer.Option(
        300,
        "--pr-limit",
        help="Maximum number of pull requests to fetch.",
    ),
    overwrite_agent: bool = typer.Option(
        False,
        "--overwrite-agent",
        help="Overwrite AGENT.md during refresh.",
    ),
    update_gitignore_file: bool = typer.Option(
        True,
        "--update-gitignore/--no-update-gitignore",
        help="Create or update .gitignore with generated context paths.",
    ),
) -> None:
    metadata_path = out / "metadata.json"

    if metadata_path.exists():
        metadata = load_metadata(metadata_path)

        config = ContextConfig(
            upstream=metadata["upstream"],
            fork=metadata.get("fork"),
            out_dir=Path(metadata.get("out_dir", str(out))),
            agent_file=Path(metadata.get("agent_file", "AGENT.md")),
            issue_limit=int(metadata.get("issue_limit", issue_limit)),
            pr_limit=int(metadata.get("pr_limit", pr_limit)),
            include_closed=bool(metadata.get("include_closed", False)),
            overwrite_agent=overwrite_agent,
            update_gitignore=update_gitignore_file,
        )

    else:
        console.print(
            f"[yellow]No metadata file found at {metadata_path}. "
            "Falling back to repository auto-detection.[/yellow]"
        )

        try:
            detected_upstream, detected_fork = detect_upstream_and_fork(upstream, fork)
        except GitDetectionError as exc:
            raise typer.BadParameter(str(exc)) from exc

        config = ContextConfig(
            upstream=detected_upstream,
            fork=detected_fork,
            out_dir=out,
            agent_file=Path("AGENT.md"),
            issue_limit=300,
            pr_limit=300,
            include_closed=False,
            overwrite_agent=overwrite_agent,
            update_gitignore=update_gitignore_file,
        )

    run_build(config)


@app.callback()
def main() -> None:
    pass
