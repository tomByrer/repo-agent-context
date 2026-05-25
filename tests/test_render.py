from repo_agent_context.render import (
    render_branches_ahead,
    render_pr,
    render_prs_index,
    render_relations,
)


def test_render_relations_detects_pr_referencing_issue() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "Fixes #10",
            "comments": [],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "PR #20 references Issue #10" in rendered


def test_render_relations_detects_comment_reference() -> None:
    issues = [
        {
            "number": 10,
            "title": "Bug",
            "body": "",
            "comments": [],
        }
    ]

    prs = [
        {
            "number": 20,
            "title": "Fix bug",
            "body": "",
            "comments": [
                {
                    "body": "This probably relates to #10.",
                    "author": {"login": "alice"},
                }
            ],
        }
    ]

    rendered = render_relations(issues, prs)

    assert "PR #20 references Issue #10" in rendered
    assert "(comment)" in rendered


def test_render_pr_includes_ci_checks_requiring_attention() -> None:
    pr = {
        "number": 20,
        "title": "Fix bug",
        "state": "OPEN",
        "isDraft": False,
        "author": {"login": "alice"},
        "labels": [],
        "baseRefName": "master",
        "headRefName": "fix-bug",
        "mergeable": "MERGEABLE",
        "reviewDecision": None,
        "createdAt": "2026-01-01T00:00:00Z",
        "updatedAt": "2026-01-02T00:00:00Z",
        "url": "https://github.com/example/repo/pull/20",
        "body": "",
        "files": [],
        "commits": [],
        "comments": [],
        "statusCheckRollup": [
            {"name": "tests", "conclusion": "FAILURE", "detailsUrl": "https://ci.example/tests"},
            {"name": "lint", "conclusion": "SUCCESS"},
        ],
    }

    rendered = render_pr(pr)

    assert "## CI status" in rendered
    assert "failure: 1" in rendered
    assert "success: 1" in rendered
    assert "tests [failure]" in rendered
    assert "lint [success]" not in rendered


def test_render_prs_index_includes_ci_summary() -> None:
    rendered = render_prs_index(
        [
            {
                "number": 20,
                "title": "Fix bug",
                "state": "OPEN",
                "isDraft": False,
                "reviewDecision": None,
                "mergeable": "MERGEABLE",
                "updatedAt": "2026-01-02T00:00:00Z",
                "statusCheckRollup": [{"name": "tests", "conclusion": "FAILURE"}],
            }
        ]
    )

    assert "[ci: failure: 1]" in rendered


def test_render_branches_ahead_lists_commits() -> None:
    rendered = render_branches_ahead(
        {
            "repo": "example/repo",
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
                            "authoredAt": "2026-01-01T00:00:00+00:00",
                            "authorName": "Alice",
                        }
                    ],
                }
            ],
        }
    )

    assert "## feature [ahead: 1] [behind: 0]" in rendered
    assert "`abc123` Add feature" in rendered
