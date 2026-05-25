from __future__ import annotations

from pathlib import Path

from repo_agent_context.render import render_branches_ahead, render_issue, render_pr

FIXTURES = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_issue_markdown_golden_output() -> None:
    assert render_issue(
        {
            "number": 1,
            "title": "Bug",
            "state": "OPEN",
            "author": {"login": "alice"},
            "labels": [{"name": "bug"}],
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-02",
            "url": "https://github.com/owner/repo/issues/1",
            "body": "body",
            "comments": [],
        }
    ) == read_fixture("issue.md")


def test_pr_markdown_golden_output() -> None:
    assert render_pr(
        {
            "number": 2,
            "title": "Fix",
            "state": "OPEN",
            "isDraft": False,
            "author": {"login": "bob"},
            "labels": [],
            "baseRefName": "master",
            "headRefName": "fix",
            "mergeable": "MERGEABLE",
            "reviewDecision": None,
            "createdAt": "2026-01-01",
            "updatedAt": "2026-01-02",
            "url": "https://github.com/owner/repo/pull/2",
            "body": "",
            "files": [{"path": "src/app.py", "additions": 1, "deletions": 0}],
            "commits": [{"oid": "abcdef1234567890", "messageHeadline": "Fix bug"}],
            "statusCheckRollup": [{"name": "tests", "conclusion": "SUCCESS"}],
            "comments": [],
        }
    ) == read_fixture("pr.md")


def test_branches_ahead_markdown_golden_output() -> None:
    assert render_branches_ahead(
        {
            "repo": "owner/repo",
            "remote": "upstream",
            "baseBranch": "master",
            "branches": [
                {
                    "name": "feature",
                    "aheadBy": 1,
                    "behindBy": 0,
                    "commits": [
                        {
                            "shortOid": "abc123",
                            "subject": "Add feature",
                            "authoredAt": "2026-01-01",
                            "authorName": "Alice",
                        }
                    ],
                }
            ],
        }
    ) == read_fixture("branches_ahead.md")
