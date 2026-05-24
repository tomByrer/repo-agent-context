from __future__ import annotations


def render_agent_md(
    *,
    upstream: str,
    fork: str | None,
    context_dir: str,
) -> str:
    fork_text = fork if fork else "not configured"

    return f"""# Agent instructions

You are working with a local repository that uses this generated context.

## Repositories

- Upstream repository: `{upstream}`
- Fork repository: `{fork_text}`

## Local context files

The generated context is stored in:

- `{context_dir}/issues/*.md`
- `{context_dir}/issues/*.json`
- `{context_dir}/prs/*.md`
- `{context_dir}/prs/*.json`
- `{context_dir}/prs/*.diff`
- `{context_dir}/index/issues_index.md`
- `{context_dir}/index/prs_index.md`
- `{context_dir}/index/relations.md`
- `{context_dir}/metadata.json`

## Rules for answering questions

- Use the files in `{context_dir}` as the primary source of truth.
- Do not assume current GitHub state beyond the local snapshot unless explicitly asked to refresh it.
- When answering about an issue or PR, mention the issue or PR number.
- Distinguish clearly between:
  - confirmed facts from issue or PR text,
  - inferred root causes,
  - recommended next actions.
- Do not modify source code unless explicitly asked.
- Check `{context_dir}/index/relations.md` first when asked whether an issue and a pull request are related.
- Treat relations as detected textual references, not as proof that a pull request actually fixes an issue.
- If asked to recommend work items, prefer:
  - reproducible bugs,
  - small and localized changes,
  - issues where a regression test can be added,
  - PRs that are close to completion but missing tests or small fixes.
- Avoid broad refactoring unless the user explicitly asks for it.

## Rules for implementing fixes

When asked to implement a fix:

1. Identify the relevant issue or PR.
2. Suggest or create a branch name.
3. Find the relevant source and test files.
4. Add a failing regression test first when feasible.
5. Make the minimal implementation change.
6. Run the relevant tests.
7. Show the final diff.
8. Do not mix unrelated changes into the same patch.

## Useful questions the user may ask

- Which issues are good first contributions?
- Which PRs are almost mergeable?
- Which issues and PRs are related?
- What does PR #123 change?
- What tests are missing for PR #123?
- Which issue should I work on first?
"""

