from __future__ import annotations

from repo_agent_context.render import render_branches_ahead, render_issue, render_pr


def test_issue_markdown_golden_output() -> None:
    assert (
        render_issue(
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
        )
        == """# Issue #1: Bug

- State: OPEN
- Author: alice
- Labels: bug
- Created: 2026-01-01
- Updated: 2026-01-02
- URL: https://github.com/owner/repo/issues/1

## Body

body

## Comments

_No comments._

"""
    )


def test_pr_markdown_golden_output() -> None:
    assert (
        render_pr(
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
        )
        == """# Pull Request #2: Fix

- State: OPEN
- Draft: False
- Author: bob
- Labels: 
- Base: master
- Head: fix
- Mergeable: MERGEABLE
- Review decision: None
- Created: 2026-01-01
- Updated: 2026-01-02
- URL: https://github.com/owner/repo/pull/2

## Body



## Changed files

- `src/app.py` (+1/-0)

## Commits

- `abcdef123456` Fix bug

## CI status

Summary: success: 1
No failing or pending checks.

## Comments

_No comments._

"""
    )


def test_branches_ahead_markdown_golden_output() -> None:
    assert (
        render_branches_ahead(
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
        )
        == """# Branches Ahead Of master

- Repository: owner/repo
- Remote: upstream
- Base branch: master
- Base branch source: unknown

## feature [ahead: 1] [behind: 0]

- `abc123` Add feature [2026-01-01, Alice]
"""
    )
