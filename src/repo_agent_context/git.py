from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass


class GitDetectionError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitRemotes:
    origin: str | None
    upstream: str | None


def run_git(args: list[str]) -> str:
    command = ["git", *args]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        raise GitDetectionError(
            "Git command failed:\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {result.returncode}\n"
            f"Stderr:\n{result.stderr.strip()}"
        )

    return result.stdout


def get_remote_url(remote_name: str) -> str | None:
    result = subprocess.run(
        ["git", "remote", "get-url", remote_name],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        return None

    url = result.stdout.strip()
    return url or None


def github_repo_from_url(url: str) -> str | None:
    """
    Convert common GitHub remote URLs to 'owner/repo'.

    Supported examples:
    - git@github.com:owner/repo.git
    - https://github.com/owner/repo.git
    - https://github.com/owner/repo
    - ssh://git@github.com/owner/repo.git
    """
    patterns = [
        r"^git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$",
        r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
        r"^ssh://git@github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$",
    ]

    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            owner = match.group("owner")
            repo = match.group("repo")
            return f"{owner}/{repo}"

    return None


def detect_github_remotes() -> GitRemotes:
    origin_url = get_remote_url("origin")
    upstream_url = get_remote_url("upstream")

    origin = github_repo_from_url(origin_url) if origin_url else None
    upstream = github_repo_from_url(upstream_url) if upstream_url else None

    return GitRemotes(origin=origin, upstream=upstream)


def detect_upstream_and_fork(
    explicit_upstream: str | None,
    explicit_fork: str | None,
) -> tuple[str, str | None]:
    remotes = detect_github_remotes()

    upstream = explicit_upstream or remotes.upstream or remotes.origin
    fork = explicit_fork or remotes.origin

    if upstream is None:
        raise GitDetectionError(
            "Could not determine upstream repository.\n"
            "Pass --upstream owner/repo explicitly or run this command inside a GitHub clone."
        )

    if fork == upstream:
        fork = None

    return upstream, fork
