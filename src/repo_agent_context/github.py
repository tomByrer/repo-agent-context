from __future__ import annotations

import json
import subprocess
from typing import Any


class GitHubCliError(RuntimeError):
    pass


def run_gh(args: list[str]) -> str:
    command = ["gh", *args]
    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        raise GitHubCliError(
            "GitHub CLI command failed:\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {result.returncode}\n"
            f"Stderr:\n{result.stderr.strip()}"
        )

    return result.stdout


def gh_json(args: list[str]) -> Any:
    output = run_gh(args)
    return json.loads(output)


def check_gh_available() -> None:
    run_gh(["--version"])


def check_repo_access(repo: str) -> None:
    run_gh(["repo", "view", repo, "--json", "nameWithOwner"])
