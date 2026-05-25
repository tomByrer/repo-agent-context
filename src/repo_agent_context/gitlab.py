from __future__ import annotations

import json
import subprocess
from typing import Any


class GitLabCliError(RuntimeError):
    pass


def run_glab(args: list[str]) -> str:
    command = ["glab", *args]
    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if result.returncode != 0:
        raise GitLabCliError(
            "GitLab CLI command failed:\n"
            f"Command: {' '.join(command)}\n"
            f"Exit code: {result.returncode}\n"
            f"Stderr:\n{result.stderr.strip()}"
        )

    return result.stdout


def glab_json(args: list[str]) -> Any:
    output = run_glab(args)
    return json.loads(output)


def check_glab_available() -> None:
    run_glab(["--version"])


def check_repo_access(repo: str) -> None:
    run_glab(["repo", "view", repo, "--output", "json"])
