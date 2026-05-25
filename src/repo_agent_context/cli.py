from __future__ import annotations

import json
from collections.abc import Callable
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
SUPPORT_URL = "https://buymeacoffee.com/arnwas"
ISSUE_LIST_FIELDS = "number,title,state,author,labels,createdAt,updatedAt,url,body"
ISSUE_VIEW_FIELDS = "number,title,state,author,labels,createdAt,updatedAt,url,body,comments"
PR_LIST_FIELDS = (
    "number,title,state,author,labels,createdAt,updatedAt,url,body,"
    "isDraft,mergeable,reviewDecision,headRefName,baseRefName,statusCheckRollup"
)
PR_VIEW_FIELDS = (
    "number,title,state,author,labels,createdAt,updatedAt,url,body,"
    "comments,isDraft,mergeable,reviewDecision,headRefName,baseRefName,"
    "files,commits,statusCheckRollup"
)


def print_support() -> None:
    console.print()
    console.print("If repo-agent-context saves you maintainer time, support is appreciated:")
    console.print(f"Buy Me a Coffee: [bold]{SUPPORT_URL}[/bold]")


def load_metadata(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise typer.BadParameter(
            f"Metadata file not found: {path}\nRun `repo-agent-context build` first."
        )

    try:
        metadata: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Metadata file is not valid JSON: {path}") from exc

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

    missing_entries = [entry for entry in wanted_entries if entry not in existing_lines]

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
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_context_items(
    *,
    config: ContextConfig,
    list_args: list[str],
    item_kind: str,
    item_dir: Path,
    list_filename: str,
    view_args_factory: Callable[[str], list[str]],
    render_item: Callable[[dict[str, Any]], str],
    extra_writer: Callable[[str, dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = gh_json(list_args)
    write_json(config.out_dir / list_filename, items)

    full_items: list[dict[str, Any]] = []
    for item in track(items, description=f"Fetching {item_kind}"):
        number_value = item.get("number")
        if number_value is None:
            raise typer.BadParameter(f"{item_kind.capitalize()} entry is missing a number: {item!r}")

        number = str(number_value)
        full: dict[str, Any] = gh_json(view_args_factory(number))
        full_items.append(full)
        write_json(item_dir / f"{number}.json", full)
        write_text(item_dir / f"{number}.md", render_item(full))

        if extra_writer is not None:
            extra_writer(number, full)

    return full_items


def build_issues(config: ContextConfig) -> list[dict[str, Any]]:
    state = "all" if config.include_closed else "open"
    return build_context_items(
        config=config,
        list_args=[
            "issue",
            "list",
            "--repo",
            config.upstream,
            "--state",
            state,
            "--limit",
            str(config.issue_limit),
            "--json",
            ISSUE_LIST_FIELDS,
        ],
        item_kind="issues",
        item_dir=config.out_dir / "issues",
        list_filename="issues.json",
        view_args_factory=lambda number: [
            "issue",
            "view",
            number,
            "--repo",
            config.upstream,
            "--comments",
            "--json",
            ISSUE_VIEW_FIELDS,
        ],
        render_item=render_issue,
    )


def build_prs(config: ContextConfig) -> list[dict[str, Any]]:
    state = "all" if config.include_closed else "open"
    item_dir = config.out_dir / "prs"

    def write_diff(number: str, _: dict[str, Any]) -> None:
        diff = run_gh(["pr", "diff", number, "--repo", config.upstream])
        write_text(item_dir / f"{number}.diff", diff)

    return build_context_items(
        config=config,
        list_args=[
            "pr",
            "list",
            "--repo",
            config.upstream,
            "--state",
            state,
            "--limit",
            str(config.pr_limit),
            "--json",
            PR_LIST_FIELDS,
        ],
        item_kind="pull requests",
        item_dir=item_dir,
        list_filename="prs.json",
        view_args_factory=lambda number: [
            "pr",
            "view",
            number,
            "--repo",
            config.upstream,
            "--comments",
            "--json",
            PR_VIEW_FIELDS,
        ],
        render_item=render_pr,
        extra_writer=write_diff,
    )


def build_branches(config: ContextConfig) -> dict[str, Any]:
    branches = branches_ahead_of_base(config.upstream, config.base_branch)
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
        "base_branch": config.base_branch,
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
    console.print(f"Branch-ahead base: [bold]{config.base_branch or 'auto'}[/bold]")
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
    console.print(
        f"Branches ahead of {branches.get('baseBranch')}: "
        f"[bold]{len(branches.get('branches') or [])}[/bold]"
    )
    print_support()


@app.command()
def status(
    upstream: Annotated[str | None, typer.Option("--upstream", "-u")] = None,
    fork: Annotated[str | None, typer.Option("--fork", "-f")] = None,
) -> None:
    try:
        detected_upstream, detected_fork = detect_upstream_and_fork(upstream, fork)
    except GitDetectionError as exc:
        raise typer.BadParameter(str(exc)) from exc

    console.print(f"Upstream: [bold]{detected_upstream}[/bold]")
    console.print(f"Fork: [bold]{detected_fork or 'none'}[/bold]")
    print_support()


@app.command()
def build(
    upstream: Annotated[
        str | None,
        typer.Option(
            "--upstream",
            "-u",
            help="Upstream GitHub repository, e.g. arnowaschk/repo-agent-context. "
            "If omitted, it is detected from the git remote named 'upstream', "
            "falling back to 'origin'.",
        ),
    ] = None,
    fork: Annotated[
        str | None,
        typer.Option(
            "--fork",
            "-f",
            help="Fork GitHub repository, e.g. myname/repo-agent-context. "
            "If omitted, it is detected from the git remote named 'origin'.",
        ),
    ] = None,
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
    issue_limit: Annotated[
        int, typer.Option("--issue-limit", help="Maximum number of issues to fetch.")
    ] = 300,
    pr_limit: Annotated[
        int, typer.Option("--pr-limit", help="Maximum number of pull requests to fetch.")
    ] = 300,
    include_closed: Annotated[
        bool,
        typer.Option("--include-closed", help="Fetch closed issues and PRs as well."),
    ] = False,
    overwrite_agent: Annotated[
        bool,
        typer.Option("--overwrite-agent", help="Overwrite AGENT.md if it already exists."),
    ] = False,
    update_gitignore_file: Annotated[
        bool,
        typer.Option(
            "--update-gitignore/--no-update-gitignore",
            help="Create or update .gitignore with generated context paths.",
        ),
    ] = True,
    base_branch: Annotated[
        str | None,
        typer.Option(
            "--base-branch",
            help="Base branch for branch-ahead context. If omitted, detect the upstream default.",
        ),
    ] = None,
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
        base_branch=base_branch,
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
    upstream: Annotated[
        str | None,
        typer.Option(
            "--upstream",
            "-u",
            help=(
                "Upstream GitHub repository. Used only if metadata.json is missing "
                "or to override it."
            ),
        ),
    ] = None,
    fork: Annotated[
        str | None,
        typer.Option(
            "--fork",
            "-f",
            help="Fork GitHub repository. Used only if metadata.json is missing or to override it.",
        ),
    ] = None,
    issue_limit: Annotated[
        int, typer.Option("--issue-limit", help="Maximum number of issues to fetch.")
    ] = 300,
    pr_limit: Annotated[
        int, typer.Option("--pr-limit", help="Maximum number of pull requests to fetch.")
    ] = 300,
    overwrite_agent: Annotated[
        bool,
        typer.Option("--overwrite-agent", help="Overwrite AGENT.md during refresh."),
    ] = False,
    update_gitignore_file: Annotated[
        bool,
        typer.Option(
            "--update-gitignore/--no-update-gitignore",
            help="Create or update .gitignore with generated context paths.",
        ),
    ] = True,
    base_branch: Annotated[
        str | None,
        typer.Option(
            "--base-branch",
            help="Override the branch-ahead base branch from metadata or auto-detection.",
        ),
    ] = None,
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
            base_branch=base_branch or metadata.get("base_branch"),
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
            base_branch=base_branch,
            include_closed=False,
            overwrite_agent=overwrite_agent,
            update_gitignore=update_gitignore_file,
        )

    run_build(config)


@app.callback()
def main() -> None:
    pass
