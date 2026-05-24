from repo_agent_context.render import render_relations


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

