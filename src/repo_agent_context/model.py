from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextConfig:
    provider: str
    upstream: str
    fork: str | None
    out_dir: Path
    agent_file: Path
    issue_limit: int
    pr_limit: int
    base_branch: str | None
    include_closed: bool
    overwrite_agent: bool
    update_gitignore: bool
