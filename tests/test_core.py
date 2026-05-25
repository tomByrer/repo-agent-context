from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from repo_agent_context.cli import update_gitignore
from repo_agent_context.git import github_repo_from_url
from repo_agent_context.model import ContextConfig
from repo_agent_context.render import render_issue, render_pr, render_relations


def test_github_repo_from_ssh_url() -> None:
    assert github_repo_from_url("git@github.com:UPSTREAM_OWNER/oss_repo.git") == "UPSTREAM_OWNER/oss_repo"


def test_github_repo_from_https_url_with_git_suffix() -> None:
    assert github_repo_from_url("https://github.com/UPSTREAM_OWNER/oss_repo.git") == "UPSTREAM_OWNER/oss_repo"


def test_github_repo_from_https_url_without_git_suffix() -> None:
    assert github_repo_from_url("https://github.com/UPSTREAM_OWNER/oss_repo") == "UPSTREAM_OWNER/oss_repo"


def test_github_repo_from_ssh_protocol_url() -> None:
    assert github_repo_from_url("ssh://git@github.com/UPSTREAM_OWNER/oss_repo.git") == "UPSTREAM_OWNER/oss_repo"


def test_github_repo_from_gitlab_https_url() -> None:
    assert github_repo_from_url("https://gitlab.com/UPSTREAM_OWNER/oss_repo.git") == "UPSTREAM_OWNER/oss_repo"


def test_github_repo_from_gitlab_ssh_url() -> None:
    assert github_repo_from_url("git@gitlab.com:UPSTREAM_OWNER/oss_repo.git") == "UPSTREAM_OWNER/oss_repo"


def test_render_issue_contains_core_fields() -> None:
    issue = {
        "number": 1,
        "title": "Example bug",
        "state": "OPEN",
        "author": {"login": "alice"},
        "labels": [{"name": "bug"}],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": "https://github.com/owner/repo/issues/1",
        "body": "Bug body",
        "comments": [],
    }

    rendered = render_issue(issue)

    assert "# Issue #1: Example bug" in rendered
    assert "- State: OPEN" in rendered
    assert "- Author: alice" in rendered
    assert "- Labels: bug" in rendered
    assert "Bug body" in rendered


def test_render_issue_without_comments_mentions_no_comments() -> None:
    issue = {
        "number": 1,
        "title": "Example bug",
        "state": "OPEN",
        "author": {"login": "alice"},
        "labels": [],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": "https://github.com/owner/repo/issues/1",
        "body": "",
        "comments": [],
    }

    rendered = render_issue(issue)

    assert "_No comments._" in rendered


def test_render_pr_contains_core_fields_and_changed_files() -> None:
    pr = {
        "number": 2,
        "title": "Example PR",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "bob"},
        "labels": [{"name": "bugfix"}],
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": "https://github.com/owner/repo/pull/2",
        "body": "PR body",
        "comments": [],
        "files": [
            {
                "path": "src/example.py",
                "additions": 10,
                "deletions": 2,
            }
        ],
        "commits": [
            {
                "oid": "abcdef1234567890",
                "messageHeadline": "Fix example bug",
            }
        ],
        "baseRefName": "main",
        "headRefName": "fix/example",
        "mergeable": "MERGEABLE",
        "reviewDecision": None,
    }

    rendered = render_pr(pr)

    assert "# Pull Request #2: Example PR" in rendered
    assert "- Draft: False" in rendered
    assert "- Author: bob" in rendered
    assert "- Labels: bugfix" in rendered
    assert "- Base: main" in rendered
    assert "- Head: fix/example" in rendered
    assert "`src/example.py` (+10/-2)" in rendered
    assert "`abcdef123456` Fix example bug" in rendered


def test_render_relations_detects_pr_body_referencing_issue() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "Fixes #10",
            "comments": [],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "PR #20 references Issue #10 (body)" in rendered


def test_render_relations_detects_pr_comment_referencing_issue() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "",
            "comments": [
                {
                    "body": "This probably relates to #10.",
                    "author": {"login": "alice"},
                }
            ],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "PR #20 references Issue #10 (comment)" in rendered


def test_render_relations_detects_issue_referencing_pr() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "This is probably fixed by #20.",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "",
            "comments": [],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "Issue #10 references PR #20 (body)" in rendered


def test_render_relations_marks_unknown_reference_as_unverified() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "Fixes #9999",
            "comments": [],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "PR #20 references Issue #9999 (body/unverified)" in rendered


def test_update_gitignore_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    config = ContextConfig(
        provider="github",
        upstream="owner/repo",
        fork="user/repo",
        out_dir=Path("agent_context"),
        agent_file=Path("AGENT.md"),
        issue_limit=300,
        pr_limit=300,
        base_branch=None,
        include_closed=False,
        overwrite_agent=False,
        update_gitignore=True,
    )
    update_gitignore(config)

    text = Path(".gitignore").read_text(encoding="utf-8")

    assert "agent_context/" in text
    assert "AGENT.md" in text


def test_update_gitignore_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_factory: Callable[..., ContextConfig],
) -> None:
    monkeypatch.chdir(tmp_path)

    config = config_factory(issue_limit=300, pr_limit=300, update_gitignore=True)

    update_gitignore(config)
    first = Path(".gitignore").read_text(encoding="utf-8")

    update_gitignore(config)
    second = Path(".gitignore").read_text(encoding="utf-8")

    assert first == second
    assert first.count("agent_context/") == 1
    assert first.count("AGENT.md") == 1


def test_update_gitignore_preserves_existing_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_factory: Callable[..., ContextConfig],
) -> None:
    monkeypatch.chdir(tmp_path)

    Path(".gitignore").write_text("__pycache__/\n.venv/\n", encoding="utf-8")

    config = config_factory(issue_limit=300, pr_limit=300, update_gitignore=True)
    update_gitignore(config)

    text = Path(".gitignore").read_text(encoding="utf-8")

    assert "__pycache__/" in text
    assert ".venv/" in text
    assert "agent_context/" in text
    assert "AGENT.md" in text


def test_update_gitignore_can_be_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config_factory: Callable[..., ContextConfig],
) -> None:
    monkeypatch.chdir(tmp_path)

    config = config_factory(issue_limit=300, pr_limit=300, update_gitignore=False)
    update_gitignore(config)

    assert not Path(".gitignore").exists()
