from __future__ import annotations

import subprocess

import pytest

import repo_agent_context.github as github
from repo_agent_context.github import GitHubCliError


def completed(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["gh"], returncode, stdout, stderr)


def test_run_gh_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(github.subprocess, "run", lambda *args, **kwargs: completed("ok"))

    assert github.run_gh(["--version"]) == "ok"


def test_run_gh_raises_detailed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        github.subprocess,
        "run",
        lambda *args, **kwargs: completed(stderr="auth failed\n", returncode=1),
    )

    with pytest.raises(GitHubCliError) as exc_info:
        github.run_gh(["repo", "view"])

    message = str(exc_info.value)
    assert "Command: gh repo view" in message
    assert "Exit code: 1" in message
    assert "auth failed" in message


def test_gh_json_parses_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(github, "run_gh", lambda args: '{"name":"repo"}')

    assert github.gh_json(["repo", "view"]) == {"name": "repo"}


def test_check_helpers_delegate_to_run_gh(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(github, "run_gh", lambda args: calls.append(args) or "")

    github.check_gh_available()
    github.check_repo_access("owner/repo")

    assert calls == [
        ["--version"],
        ["repo", "view", "owner/repo", "--json", "nameWithOwner"],
    ]
