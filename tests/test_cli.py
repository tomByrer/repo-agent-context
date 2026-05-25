from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import typer

import repo_agent_context.cli as cli
from repo_agent_context.git import GitDetectionError
from repo_agent_context.model import ContextConfig


def config(tmp_path: Path, *, fork: str | None = "fork/repo") -> ContextConfig:
    return ContextConfig(
        upstream="owner/repo",
        fork=fork,
        out_dir=tmp_path / "agent_context",
        agent_file=tmp_path / "AGENT.md",
        issue_limit=2,
        pr_limit=2,
        include_closed=False,
        overwrite_agent=False,
        update_gitignore=False,
    )


def issue(number: int = 1) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"Issue {number}",
        "state": "OPEN",
        "author": {"login": "alice"},
        "labels": [],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": f"https://github.com/owner/repo/issues/{number}",
        "body": "",
        "comments": [],
    }


def pr(number: int = 2) -> dict[str, Any]:
    return {
        "number": number,
        "title": f"PR {number}",
        "state": "OPEN",
        "author": {"login": "bob"},
        "labels": [],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": f"https://github.com/owner/repo/pull/{number}",
        "body": "",
        "comments": [],
        "isDraft": False,
        "mergeable": "MERGEABLE",
        "reviewDecision": None,
        "headRefName": "feature",
        "baseRefName": "master",
        "files": [],
        "commits": [],
        "statusCheckRollup": [],
    }


def test_load_metadata_reads_json_and_raises_for_missing(tmp_path: Path) -> None:
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text('{"upstream":"owner/repo"}', encoding="utf-8")

    assert cli.load_metadata(metadata_path) == {"upstream": "owner/repo"}

    with pytest.raises(typer.BadParameter):
        cli.load_metadata(tmp_path / "missing.json")


def test_write_json_and_text_create_parent_directories(tmp_path: Path) -> None:
    cli.write_json(tmp_path / "nested" / "data.json", {"snowman": "ok"})
    cli.write_text(tmp_path / "nested" / "text.md", "hello")

    assert json.loads((tmp_path / "nested" / "data.json").read_text(encoding="utf-8")) == {
        "snowman": "ok"
    }
    assert (tmp_path / "nested" / "text.md").read_text(encoding="utf-8") == "hello"


def test_build_issues_fetches_list_and_full_items(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_gh_json(args: list[str]) -> Any:
        calls.append(args)
        if args[:2] == ["issue", "list"]:
            return [{"number": 1, "title": "Issue 1"}]
        return issue(1)

    monkeypatch.setattr(cli, "gh_json", fake_gh_json)
    monkeypatch.setattr(cli, "track", lambda items, description: items)

    result = cli.build_issues(config(tmp_path))

    assert result == [issue(1)]
    assert json.loads((tmp_path / "agent_context" / "issues.json").read_text()) == [
        {"number": 1, "title": "Issue 1"}
    ]
    assert (tmp_path / "agent_context" / "issues" / "1.md").exists()
    assert "--state" in calls[0]
    assert "open" in calls[0]


def test_build_issues_can_include_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []
    cfg = config(tmp_path)
    cfg = ContextConfig(**{**cfg.__dict__, "include_closed": True})

    monkeypatch.setattr(cli, "gh_json", lambda args: calls.append(args) or [])

    assert cli.build_issues(cfg) == []
    assert "all" in calls[0]


def test_build_prs_fetches_status_rollup_and_diff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_gh_json(args: list[str]) -> Any:
        calls.append(args)
        if args[:2] == ["pr", "list"]:
            return [{"number": 2, "title": "PR 2", "statusCheckRollup": []}]
        return pr(2)

    monkeypatch.setattr(cli, "gh_json", fake_gh_json)
    monkeypatch.setattr(cli, "run_gh", lambda args: "diff text")
    monkeypatch.setattr(cli, "track", lambda items, description: items)

    result = cli.build_prs(config(tmp_path))

    assert result == [pr(2)]
    assert "statusCheckRollup" in calls[0][-1]
    assert "statusCheckRollup" in calls[1][-1]
    assert (tmp_path / "agent_context" / "prs" / "2.diff").read_text() == "diff text"


def test_build_branches_writes_json_and_markdown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = {"repo": "owner/repo", "remote": "upstream", "baseBranch": "master", "branches": []}
    monkeypatch.setattr(cli, "branches_ahead_of_base", lambda repo: data)

    assert cli.build_branches(config(tmp_path)) == data
    assert (tmp_path / "agent_context" / "branches_ahead.json").exists()
    assert (tmp_path / "agent_context" / "index" / "branches_ahead.md").exists()


def test_build_metadata_writes_config(tmp_path: Path) -> None:
    cfg = config(tmp_path)

    cli.build_metadata(cfg)

    metadata = json.loads((tmp_path / "agent_context" / "metadata.json").read_text())
    assert metadata["upstream"] == "owner/repo"
    assert metadata["fork"] == "fork/repo"
    assert metadata["issue_limit"] == 2


def test_write_agent_file_skips_existing_unless_overwrite(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    cfg.agent_file.write_text("existing", encoding="utf-8")

    cli.write_agent_file(cfg)
    assert cfg.agent_file.read_text(encoding="utf-8") == "existing"

    overwrite_cfg = ContextConfig(**{**cfg.__dict__, "overwrite_agent": True})
    cli.write_agent_file(overwrite_cfg)
    assert "Upstream repository: `owner/repo`" in cfg.agent_file.read_text(encoding="utf-8")


def test_run_build_orchestrates_all_steps_with_fork(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    cfg = config(tmp_path)

    monkeypatch.setattr(cli, "check_gh_available", lambda: calls.append("gh"))
    monkeypatch.setattr(cli, "check_repo_access", lambda repo: calls.append(f"repo:{repo}"))
    monkeypatch.setattr(cli, "build_metadata", lambda config: calls.append("metadata"))
    monkeypatch.setattr(cli, "build_issues", lambda config: [issue(1)])
    monkeypatch.setattr(cli, "build_prs", lambda config: [pr(2)])
    monkeypatch.setattr(
        cli,
        "build_branches",
        lambda config: {"branches": [{"name": "feature"}]},
    )
    monkeypatch.setattr(cli, "write_text", lambda path, text: calls.append(path.name))
    monkeypatch.setattr(cli, "write_agent_file", lambda config: calls.append("agent"))
    monkeypatch.setattr(cli, "update_gitignore", lambda config: calls.append("gitignore"))

    cli.run_build(cfg)

    assert calls[:4] == ["gh", "repo:owner/repo", "repo:fork/repo", "metadata"]
    assert "issues_index.md" in calls
    assert "prs_index.md" in calls
    assert "relations.md" in calls
    assert calls[-2:] == ["agent", "gitignore"]


def test_run_build_skips_fork_check_when_no_fork(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    checked: list[str] = []
    cfg = config(tmp_path, fork=None)

    monkeypatch.setattr(cli, "check_gh_available", lambda: None)
    monkeypatch.setattr(cli, "check_repo_access", lambda repo: checked.append(repo))
    monkeypatch.setattr(cli, "build_metadata", lambda config: None)
    monkeypatch.setattr(cli, "build_issues", lambda config: [])
    monkeypatch.setattr(cli, "build_prs", lambda config: [])
    monkeypatch.setattr(cli, "build_branches", lambda config: {"branches": []})
    monkeypatch.setattr(cli, "write_text", lambda path, text: None)
    monkeypatch.setattr(cli, "write_agent_file", lambda config: None)
    monkeypatch.setattr(cli, "update_gitignore", lambda config: None)

    cli.run_build(cfg)

    assert checked == ["owner/repo"]


def test_status_prints_detected_repos(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: ("owner/repo", None),
    )
    monkeypatch.setattr(cli.console, "print", lambda text="": lines.append(str(text)))

    cli.status(None, None)

    assert any("owner/repo" in line for line in lines)
    assert any("none" in line for line in lines)


def test_status_wraps_detection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: (_ for _ in ()).throw(GitDetectionError("bad remote")),
    )

    with pytest.raises(typer.BadParameter):
        cli.status(None, None)


def test_build_command_creates_config_and_runs_build(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[ContextConfig] = []
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: ("owner/repo", "fork/repo"),
    )
    monkeypatch.setattr(cli, "run_build", lambda cfg: seen.append(cfg))

    cli.build(
        upstream=None,
        fork=None,
        out=tmp_path / "ctx",
        agent_file=tmp_path / "AGENT.md",
        issue_limit=4,
        pr_limit=5,
        include_closed=True,
        overwrite_agent=True,
        update_gitignore_file=True,
    )

    assert seen[0].out_dir == tmp_path / "ctx"
    assert seen[0].issue_limit == 4
    assert seen[0].include_closed is True


def test_build_command_wraps_detection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: (_ for _ in ()).throw(GitDetectionError("bad remote")),
    )

    with pytest.raises(typer.BadParameter):
        cli.build()


def test_refresh_uses_existing_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "agent_context"
    out.mkdir()
    (out / "metadata.json").write_text(
        json.dumps(
            {
                "upstream": "owner/repo",
                "fork": None,
                "out_dir": str(out),
                "agent_file": str(tmp_path / "CUSTOM.md"),
                "issue_limit": 7,
                "pr_limit": 8,
                "include_closed": True,
            }
        ),
        encoding="utf-8",
    )
    seen: list[ContextConfig] = []
    monkeypatch.setattr(cli, "run_build", lambda cfg: seen.append(cfg))

    cli.refresh(out=out, overwrite_agent=True, update_gitignore_file=False)

    assert seen[0].upstream == "owner/repo"
    assert seen[0].agent_file == tmp_path / "CUSTOM.md"
    assert seen[0].issue_limit == 7
    assert seen[0].overwrite_agent is True
    assert seen[0].update_gitignore is False


def test_refresh_falls_back_to_detection_without_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[ContextConfig] = []
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: ("owner/repo", "fork/repo"),
    )
    monkeypatch.setattr(cli, "run_build", lambda cfg: seen.append(cfg))

    cli.refresh(out=tmp_path / "missing")

    assert seen[0].upstream == "owner/repo"
    assert seen[0].fork == "fork/repo"
    assert seen[0].out_dir == tmp_path / "missing"
    assert seen[0].agent_file == Path("AGENT.md")


def test_refresh_wraps_detection_errors_without_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli,
        "detect_upstream_and_fork",
        lambda upstream, fork: (_ for _ in ()).throw(GitDetectionError("bad remote")),
    )

    with pytest.raises(typer.BadParameter):
        cli.refresh(out=tmp_path / "missing")


def test_main_callback_is_noop() -> None:
    assert cli.main() is None
