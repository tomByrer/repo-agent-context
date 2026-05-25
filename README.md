# repo-agent-context

Local GitHub issue and PR context snapshots for coding agents and local LLMs.

`repo-agent-context` builds a local, file-based context snapshot from a GitHub repository's issues and pull requests so that coding agents can answer questions about project state, open work, stale pull requests, likely fixes, and good first contributions without repeatedly browsing GitHub.

The generated context is intended for local use inside a cloned repository. It includes issue bodies, issue comments, pull request metadata, pull request CI status, pull request comments, changed files, diffs, branches ahead of the upstream default branch, index files, metadata, and a generated `AGENT.md` with instructions for coding agents.

It is intentionally plain Markdown and JSON. There is no hosted service, vector database, background daemon, or agent framework dependency.

The JSON files are written compactly to keep token usage low for downstream agents.

## How It Works

1. Detect the upstream and fork repositories, plus the branch base for branch-ahead context.
2. Fetch issues, pull requests, CI status, comments, diffs, and local branch data.
3. Write compact Markdown and JSON files into `agent_context/` together with a generated `AGENT.md`.

## Use case

Typical questions after generating the context:

- Which issues are good first contributions?
- Which pull requests are almost mergeable?
- Which pull requests appear to address existing issues?
- What does PR #123 change?
- Which tests are missing for PR #123?
- Which issue should I work on first?
- Which PRs look stale but salvageable?

The tool is especially useful when maintaining or contributing to existing open-source projects.

## What This Is

- A CLI that exports GitHub issue and pull request context into local files.
- A way to give coding agents and local LLMs compact project state without repeated browsing.
- A source of Markdown and JSON that humans can inspect and edit workflows around.

## What This Is Not

- It is not an agent.
- It is not an MCP server.
- It is not an embedding or vector database.
- It does not replace GitHub as the source of truth.

## Why Local Files

Local files are easy for terminal agents and local LLM workflows to inspect. They also keep repository context close to the clone, avoid repeated GitHub API lookups during analysis, and make it clear what snapshot the agent is using.

## Known Limitations

- Relation detection is heuristic and based on textual references.
- Branch-ahead data depends on local remote refs. Run `git fetch upstream` before building if you need fresh data.
- Generated files are snapshots, not live GitHub state.

## Requirements

- Python 3.10 or newer
- Git
- GitHub CLI: `gh`
- An authenticated GitHub CLI session

Install GitHub CLI from https://cli.github.com/ or with your platform package manager
(Homebrew on macOS, winget on Windows, apt/dnf/pacman on Linux), then authenticate with:

```bash
gh auth login
```

Check access:

```bash
gh repo view OWNER/REPO
```

## Installation

Install as a CLI tool:

```bash
uv tool install repo-agent-context
```

or:

```bash
pipx install repo-agent-context
```

or:

```bash
pip install repo-agent-context
```

## Installation for Development

Clone the project and install dependencies:

```bash
git clone https://github.com/arnowaschk/repo-agent-context.git
cd repo-agent-context
uv sync
```

Run the CLI during development:

```bash
uv run repo-agent-context --help
```

Run the complete tox matrix where interpreters are available:

```bash
uv run tox
```

## Basic usage

Inside a local clone with remotes like this:

```text
origin    git@github.com:YOUR_NAME/oss_repo.git
upstream  https://github.com/UPSTREAM_OWNER/oss_repo.git
```

run:

```bash
repo-agent-context build
```

The tool should detect:

```text
Upstream: UPSTREAM_OWNER/oss_repo
Fork: YOUR_NAME/oss_repo
Output directory: agent_context
Agent file: AGENT.md
```

By default it writes:

```text
agent_context/
AGENT.md
```

and updates or creates `.gitignore` with:

```gitignore
agent_context/
AGENT.md
```

## Explicit usage

You can also pass the repositories explicitly:

```bash
repo-agent-context build \
  --upstream UPSTREAM_OWNER/oss_repo \
  --fork YOUR_NAME/oss_repo \
  --out agent_context \
  --agent-file AGENT.md
```

If there is no fork:

```bash
repo-agent-context build --upstream UPSTREAM_OWNER/oss_repo
```

## Repository detection

If `--upstream` and `--fork` are omitted, the tool reads Git remotes:

- `upstream` remote becomes the upstream repository.
- `origin` remote becomes the fork repository.
- If no `upstream` remote exists, `origin` is used as upstream.
- If fork and upstream resolve to the same repository, fork is treated as absent.

Supported GitHub remote formats:

```text
git@github.com:owner/oss_repo.git
https://github.com/owner/oss_repo.git
https://github.com/owner/oss_repo
ssh://git@github.com/owner/oss_repo.git
```

You can verify detection without fetching data:

```bash
repo-agent-context status
```

## Generated files

Example output:

```text
agent_context/
  metadata.json
  issues.json
  prs.json
  branches_ahead.json
  issues/
    123.json
    123.md
  prs/
    456.json
    456.md
    456.diff
  index/
    issues_index.md
    prs_index.md
    branches_ahead.md
    relations.md
AGENT.md
```

### `agent_context/issues/*.md`

Contains rendered issue text:

- issue number
- title
- state
- author
- labels
- creation and update dates
- URL
- body
- comments

### `agent_context/prs/*.md`

Contains rendered pull request text:

- PR number
- title
- state
- draft status
- author
- labels
- base branch
- head branch
- mergeability
- review decision
- CI status summary and checks needing attention
- changed files
- commits
- comments

### `agent_context/prs/*.diff`

Contains the pull request diff as returned by:

```bash
gh pr diff PR_NUMBER --repo OWNER/REPO
```

### `agent_context/index/issues_index.md`

Compact issue index sorted by update time.

### `agent_context/index/prs_index.md`

Compact pull request index sorted by update time.

Example:

```markdown
- #456: Fix parser crash [state: OPEN] [draft: False] [review: APPROVED] [mergeable: MERGEABLE] [ci: failure: 1, success: 4] [updated: 2026-05-25T08:30:00Z]
```

### `agent_context/branches_ahead.json`

Compact structured data for local remote branches that are ahead of the upstream default branch. The default is detected from local remote refs. Use `--base-branch BRANCH` to override it. The data uses already-fetched local remote refs, so run `git fetch upstream` before building if you need fresh branch data.

### `agent_context/index/branches_ahead.md`

Markdown summary of branches ahead of the selected base branch, including each ahead commit's short SHA, subject, author, and authored time.

### `agent_context/index/relations.md`

Contains detected textual relations between issues and pull requests.

Examples:

- PR #456 references Issue #123 via `Fixes #123`
- Issue #123 references PR #456 in a comment
- Issue #200 references Issue #123

The relation index is based on textual references and should be treated as a triage aid, not as proof that a PR correctly fixes an issue.

### `agent_context/metadata.json`

Contains the repository configuration used to build the snapshot.

### `AGENT.md`

Generated instructions for a coding agent. It tells the agent where the local context is stored, how to answer questions, and what rules to follow before modifying code.

## Privacy And Generated Data

The generated context can contain issue bodies, PR comments, diffs, branch names, CI status, and other repository metadata. For private repositories, treat `agent_context/` and `AGENT.md` as local working files unless you intentionally want to publish that snapshot.

By default, the tool updates `.gitignore` with:

```gitignore
agent_context/
AGENT.md
```

This reduces the risk of committing local context snapshots by accident.

## Recommended workflow

In a target repository:

```bash
git fetch upstream
repo-agent-context build
```

Then ask a coding agent questions such as:

```text
Use AGENT.md and agent_context/.
Which five open issues are best suited for a first contribution?
Rank them by reproducibility, patch size, testability, and risk.
Do not modify code.
```

For a pull request:

```text
Analyze PR #123 using agent_context/prs/123.md and agent_context/prs/123.diff.
What does it change, what risks do you see, and which tests are missing?
Do not modify code.
```

For issue triage:

```text
Use agent_context/issues/*.md and agent_context/prs/*.md.
Find issues related to dependency resolution, import parsing, or requirements.txt output.
Group them by likely affected source file.
```

## CLI options

```text
repo-agent-context build [OPTIONS]
```

Common options:

```text
--upstream, -u          Upstream GitHub repository, e.g. UPSTREAM_OWNER/oss_repo.
--fork, -f              Fork GitHub repository, e.g. YOUR_NAME/oss_repo.
--out, -o               Output directory. Default: agent_context
--agent-file            Generated agent instruction file. Default: AGENT.md
--issue-limit           Maximum number of issues to fetch. Default: 300
--pr-limit              Maximum number of pull requests to fetch. Default: 300
--include-closed        Fetch closed issues and PRs as well.
--base-branch           Base branch for branch-ahead context. Default: detect upstream default.
--overwrite-agent       Overwrite AGENT.md if it already exists.
--no-update-gitignore   Do not create or update .gitignore.
```

Detection-only command:

```bash
repo-agent-context status
```

## Development checks

Run tests:

```bash
uv run pytest -q
```

Run tests with required 100% statement coverage:

```bash
uv run coverage run -m pytest -q
uv run coverage report
```

Run the tox matrix:

```bash
uv run tox
```

Run linting:

```bash
uv run ruff check .
```

Run type checking:

```bash
uv run mypy src
```

## Design principles

- Keep generated context as plain files.
- Prefer Markdown for agent-readable context.
- Keep JSON files for structured follow-up processing.
- Do not modify project source code.
- Do not commit generated context unless explicitly intended.
- Make repository detection automatic but overridable.
- Keep the first version GitHub-only.
- Structure the code so that GitLab or Gitea providers can be added later.
- Treat 100% statement coverage as a guardrail, not as proof of correctness. Output stability and behavior-focused tests matter more than coverage alone.

## Suggested `.gitignore` behavior

By default, the tool creates `.gitignore` if missing and appends these entries if absent:

```gitignore
agent_context/
AGENT.md
```

This prevents local agent context snapshots from being accidentally committed to upstream projects.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## Support

If this tool saves you maintainer time, optional support via Buy Me a Coffee is appreciated
but not expected:
https://buymeacoffee.com/arnwas

## License

MIT. See [LICENSE](LICENSE).
