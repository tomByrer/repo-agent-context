from __future__ import annotations

from repo_agent_context.templates import render_agent_md


def test_render_agent_md_lists_context_files_and_rules() -> None:
    rendered = render_agent_md(
        upstream="owner/repo",
        fork="fork/repo",
        context_dir="agent_context",
    )

    assert "Upstream repository: `owner/repo`" in rendered
    assert "Fork repository: `fork/repo`" in rendered
    assert "`agent_context/index/branches_ahead.md`" in rendered
    assert "Use PR / MR CI summaries" in rendered
    assert "Treat generated files as a local snapshot" in rendered


def test_render_agent_md_handles_missing_fork() -> None:
    rendered = render_agent_md(
        upstream="owner/repo",
        fork=None,
        context_dir="agent_context",
    )

    assert "Fork repository: `not configured`" in rendered
