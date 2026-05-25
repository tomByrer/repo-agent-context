from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from repo_agent_context.model import ContextConfig


@pytest.fixture
def config_factory() -> Callable[..., ContextConfig]:
    def factory(
        *,
        provider: str = "github",
        out_dir: Path = Path("agent_context"),
        agent_file: Path = Path("AGENT.md"),
        fork: str | None = "fork/repo",
        issue_limit: int = 2,
        pr_limit: int = 2,
        base_branch: str | None = None,
        include_closed: bool = False,
        overwrite_agent: bool = False,
        update_gitignore: bool = False,
    ) -> ContextConfig:
        return ContextConfig(
            provider=provider,
            upstream="owner/repo",
            fork=fork,
            out_dir=out_dir,
            agent_file=agent_file,
            issue_limit=issue_limit,
            pr_limit=pr_limit,
            base_branch=base_branch,
            include_closed=include_closed,
            overwrite_agent=overwrite_agent,
            update_gitignore=update_gitignore,
        )

    return factory


@pytest.fixture
def issue_factory() -> Callable[..., dict[str, Any]]:
    def factory(number: int = 1, **overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
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
        data.update(overrides)
        return data

    return factory


@pytest.fixture
def pr_factory() -> Callable[..., dict[str, Any]]:
    def factory(number: int = 2, **overrides: Any) -> dict[str, Any]:
        data: dict[str, Any] = {
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
        data.update(overrides)
        return data

    return factory
