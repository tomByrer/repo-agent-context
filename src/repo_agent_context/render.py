from __future__ import annotations

import re
from typing import Any


ISSUE_REFERENCE_RE = re.compile(
    r"(?i)\b("
    r"fix(?:e[sd])?|"
    r"close[sd]?|"
    r"resolve[sd]?|"
    r"ref(?:s|erence[sd]?)?|"
    r"relate[sd]?"
    r")?\s*#(?P<number>\d+)"
)


def extract_references_from_text(text: str) -> set[int]:
    references: set[int] = set()

    for match in ISSUE_REFERENCE_RE.finditer(text or ""):
        references.add(int(match.group("number")))

    return references


def extract_references_from_comments(comments: list[dict[str, Any]]) -> set[int]:
    references: set[int] = set()

    for comment in comments:
        references.update(extract_references_from_text(comment.get("body") or ""))

    return references


def render_relations(
    issues: list[dict[str, Any]],
    prs: list[dict[str, Any]],
) -> str:
    issue_numbers = {int(issue["number"]) for issue in issues}
    pr_numbers = {int(pr["number"]) for pr in prs}

    lines: list[str] = [
        "# Relations",
        "",
        "This file lists detected references between issues and pull requests.",
        "",
        "Detection is based on textual references such as `#123`, `Fixes #123`, "
        "`Closes #123`, `Resolves #123`, `Refs #123`, and similar forms.",
        "",
    ]

    pr_issue_relations: list[tuple[int, int, str]] = []
    pr_pr_relations: list[tuple[int, int, str]] = []
    issue_issue_relations: list[tuple[int, int, str]] = []
    issue_pr_relations: list[tuple[int, int, str]] = []

    for pr in prs:
        pr_number = int(pr["number"])

        body_refs = extract_references_from_text(pr.get("body") or "")
        comment_refs = extract_references_from_comments(pr.get("comments") or [])

        for ref in sorted(body_refs):
            if ref == pr_number:
                continue
            if ref in issue_numbers:
                pr_issue_relations.append((pr_number, ref, "body"))
            elif ref in pr_numbers:
                pr_pr_relations.append((pr_number, ref, "body"))
            else:
                pr_issue_relations.append((pr_number, ref, "body/unverified"))

        for ref in sorted(comment_refs):
            if ref == pr_number:
                continue
            if ref in issue_numbers:
                pr_issue_relations.append((pr_number, ref, "comment"))
            elif ref in pr_numbers:
                pr_pr_relations.append((pr_number, ref, "comment"))
            else:
                pr_issue_relations.append((pr_number, ref, "comment/unverified"))

    for issue in issues:
        issue_number = int(issue["number"])

        body_refs = extract_references_from_text(issue.get("body") or "")
        comment_refs = extract_references_from_comments(issue.get("comments") or [])

        for ref in sorted(body_refs):
            if ref == issue_number:
                continue
            if ref in pr_numbers:
                issue_pr_relations.append((issue_number, ref, "body"))
            elif ref in issue_numbers:
                issue_issue_relations.append((issue_number, ref, "body"))
            else:
                issue_issue_relations.append((issue_number, ref, "body/unverified"))

        for ref in sorted(comment_refs):
            if ref == issue_number:
                continue
            if ref in pr_numbers:
                issue_pr_relations.append((issue_number, ref, "comment"))
            elif ref in issue_numbers:
                issue_issue_relations.append((issue_number, ref, "comment"))
            else:
                issue_issue_relations.append((issue_number, ref, "comment/unverified"))

    def unique_relations(
        relations: list[tuple[int, int, str]],
    ) -> list[tuple[int, int, str]]:
        seen: set[tuple[int, int, str]] = set()
        result: list[tuple[int, int, str]] = []

        for relation in relations:
            if relation not in seen:
                seen.add(relation)
                result.append(relation)

        return sorted(result)

    lines.extend(["## Pull requests referencing issues", ""])

    for pr_number, issue_number, source in unique_relations(pr_issue_relations):
        lines.append(f"- PR #{pr_number} references Issue #{issue_number} ({source})")

    if not pr_issue_relations:
        lines.append("_No PR-to-issue references detected._")

    lines.extend(["", "## Issues referencing pull requests", ""])

    for issue_number, pr_number, source in unique_relations(issue_pr_relations):
        lines.append(f"- Issue #{issue_number} references PR #{pr_number} ({source})")

    if not issue_pr_relations:
        lines.append("_No issue-to-PR references detected._")

    lines.extend(["", "## Issues referencing issues", ""])

    for source_issue, target_issue, source in unique_relations(issue_issue_relations):
        lines.append(f"- Issue #{source_issue} references Issue #{target_issue} ({source})")

    if not issue_issue_relations:
        lines.append("_No issue-to-issue references detected._")

    lines.extend(["", "## Pull requests referencing pull requests", ""])

    for source_pr, target_pr, source in unique_relations(pr_pr_relations):
        lines.append(f"- PR #{source_pr} references PR #{target_pr} ({source})")

    if not pr_pr_relations:
        lines.append("_No PR-to-PR references detected._")

    lines.append("")
    return "\n".join(lines)


def author_login(item: dict[str, Any]) -> str:
    author = item.get("author") or {}
    return author.get("login") or "unknown"


def label_names(item: dict[str, Any]) -> str:
    labels = item.get("labels") or []
    names = [label.get("name", "") for label in labels]
    return ", ".join(name for name in names if name)


def render_comments(comments: list[dict[str, Any]]) -> str:
    if not comments:
        return "_No comments._\n"

    parts: list[str] = []
    for comment in comments:
        author = author_login(comment)
        created = comment.get("createdAt", "")
        body = comment.get("body") or ""
        parts.append(f"### Comment by {author} at {created}\n\n{body}\n")

    return "\n".join(parts)


def render_issue(issue: dict[str, Any]) -> str:
    body = issue.get("body") or ""
    comments = issue.get("comments") or []

    return f"""# Issue #{issue["number"]}: {issue["title"]}

- State: {issue.get("state")}
- Author: {author_login(issue)}
- Labels: {label_names(issue)}
- Created: {issue.get("createdAt")}
- Updated: {issue.get("updatedAt")}
- URL: {issue.get("url")}

## Body

{body}

## Comments

{render_comments(comments)}
"""


def render_pr(pr: dict[str, Any]) -> str:
    body = pr.get("body") or ""
    files = pr.get("files") or []
    comments = pr.get("comments") or []
    commits = pr.get("commits") or []

    file_lines = []
    for changed_file in files:
        path = changed_file.get("path", "")
        additions = changed_file.get("additions", 0)
        deletions = changed_file.get("deletions", 0)
        file_lines.append(f"- `{path}` (+{additions}/-{deletions})")

    commit_lines = []
    for commit in commits:
        message = commit.get("messageHeadline") or commit.get("message") or ""
        oid = commit.get("oid", "")[:12]
        commit_lines.append(f"- `{oid}` {message}")

    return f"""# Pull Request #{pr["number"]}: {pr["title"]}

- State: {pr.get("state")}
- Draft: {pr.get("isDraft")}
- Author: {author_login(pr)}
- Labels: {label_names(pr)}
- Base: {pr.get("baseRefName")}
- Head: {pr.get("headRefName")}
- Mergeable: {pr.get("mergeable")}
- Review decision: {pr.get("reviewDecision")}
- Created: {pr.get("createdAt")}
- Updated: {pr.get("updatedAt")}
- URL: {pr.get("url")}

## Body

{body}

## Changed files

{chr(10).join(file_lines) if file_lines else "_No files listed._"}

## Commits

{chr(10).join(commit_lines) if commit_lines else "_No commits listed._"}

## Comments

{render_comments(comments)}
"""


def render_issues_index(issues: list[dict[str, Any]]) -> str:
    lines = ["# Issues Index", ""]

    for issue in sorted(issues, key=lambda item: item.get("updatedAt", ""), reverse=True):
        lines.append(
            f"- #{issue['number']}: {issue['title']} "
            f"[state: {issue.get('state')}] "
            f"[labels: {label_names(issue)}] "
            f"[updated: {issue.get('updatedAt')}]"
        )

    return "\n".join(lines) + "\n"


def render_prs_index(prs: list[dict[str, Any]]) -> str:
    lines = ["# Pull Requests Index", ""]

    for pr in sorted(prs, key=lambda item: item.get("updatedAt", ""), reverse=True):
        lines.append(
            f"- #{pr['number']}: {pr['title']} "
            f"[state: {pr.get('state')}] "
            f"[draft: {pr.get('isDraft')}] "
            f"[review: {pr.get('reviewDecision')}] "
            f"[mergeable: {pr.get('mergeable')}] "
            f"[updated: {pr.get('updatedAt')}]"
        )

    return "\n".join(lines) + "\n"

