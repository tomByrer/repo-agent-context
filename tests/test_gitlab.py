from __future__ import annotations

import subprocess

import pytest

import repo_agent_context.gitlab as gitlab
from repo_agent_context.gitlab import GitLabCliError


def completed(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(["glab"], returncode, stdout, stderr)


def test_run_glab_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gitlab.subprocess, "run", lambda *args, **kwargs: completed("ok"))

    assert gitlab.run_glab(["--version"]) == "ok"


def test_run_glab_raises_detailed_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        gitlab.subprocess,
        "run",
        lambda *args, **kwargs: completed(stderr="auth failed\n", returncode=1),
    )

    with pytest.raises(GitLabCliError) as exc_info:
        gitlab.run_glab(["repo", "view"])

    message = str(exc_info.value)
    assert "Command: glab repo view" in message
    assert "Exit code: 1" in message
    assert "auth failed" in message


def test_glab_json_parses_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gitlab, "run_glab", lambda args: '{"name":"repo"}')

    assert gitlab.glab_json(["repo", "view"]) == {"name": "repo"}


def test_check_helpers_delegate_to_run_glab(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(gitlab, "run_glab", lambda args: calls.append(args) or "")

    gitlab.check_glab_available()
    gitlab.check_repo_access("owner/repo")

    assert calls == [
        ["--version"],
        ["repo", "view", "owner/repo", "--output", "json"],
    ]
