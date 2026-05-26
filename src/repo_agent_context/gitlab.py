from __future__ import annotations

import json
import subprocess
import time
from typing import Any


class GitLabCliError(RuntimeError):
    pass


_TRANSIENT_ERROR_HINTS = (
    "connection reset by peer",
    "connection refused",
    "unexpected eof",
    "broken pipe",
    "temporary failure in name resolution",
    "could not resolve host",
    "tls handshake timeout",
    "i/o timeout",
    "timed out",
    "timeout",
    "remote disconnected",
)


def _is_transient_error(stderr: str) -> bool:
    lowered = stderr.lower()
    return any(hint in lowered for hint in _TRANSIENT_ERROR_HINTS)


def _format_glab_error(command: list[str], result: subprocess.CompletedProcess[str]) -> str:
    return (
        "GitLab CLI command failed:\n"
        f"Command: {' '.join(command)}\n"
        f"Exit code: {result.returncode}\n"
        f"Stderr:\n{result.stderr.strip()}"
    )


def run_glab(args: list[str]) -> str:
    command = ["glab", *args]
    max_attempts = 5

    for attempt in range(1, max_attempts + 1):
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode == 0:
            return result.stdout

        error = GitLabCliError(_format_glab_error(command, result))
        if attempt < max_attempts and _is_transient_error(result.stderr):
            time.sleep(5.0 * attempt)
            continue

        raise error

    raise GitLabCliError(f"GitLab CLI command failed unexpectedly: {' '.join(command)}")


def glab_json(args: list[str]) -> Any:
    output = run_glab(args)
    return json.loads(output)


def check_glab_available() -> None:
    run_glab(["--version"])


def check_repo_access(repo: str) -> None:
    run_glab(["repo", "view", repo, "--output", "json"])
