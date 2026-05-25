# repo-agent-context

`repo-agent-context` builds a local, file-based context snapshot from a GitHub repository's issues and pull requests so that coding agents can answer questions about project state, open work, stale pull requests, likely fixes, and good first contributions without repeatedly browsing GitHub.

The generated context is intended for local use inside a cloned repository. It includes issue bodies, issue comments, pull request metadata, pull request CI status, pull request comments, changed files, diffs, branches ahead of `master`, index files, metadata, and a generated `AGENT.md` with instructions for coding agents.

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

## Requirements

- Python 3.11 or newer
- Git
- GitHub CLI: `gh`
- An authenticated GitHub CLI session

Install and authenticate GitHub CLI:

```bash
sudo apt install gh
gh auth login
```

Check access:

```bash
gh repo view OWNER/REPO
```

## Installation for development

Create the project:

```bash
mkdir -p ~/Nextcloud/src/repo-agent-context
cd ~/Nextcloud/src/repo-agent-context
uv init --package
mkdir -p src/repo_agent_context tests
```

Install dependencies:

```bash
uv sync
```

Run the CLI during development:

```bash
uv run repo-agent-context --help
```

If `uv` warns that entry points are skipped because the project is not packaged, add this to `pyproject.toml`:

```toml
[tool.uv]
package = true
```

## Suggested `pyproject.toml`

```toml
[project]
name = "repo-agent-context"
version = "0.1.0"
description = "Build local issue and pull request context for coding agents."
readme = "README.md"
requires-python = ">=3.11"
authors = [
  { name = "Arno Waschk" }
]
dependencies = [
  "typer>=0.12.0",
  "rich>=13.0.0"
]

[project.scripts]
repo-agent-context = "repo_agent_context.cli:app"

[dependency-groups]
dev = [
  "pytest>=8.0.0",
  "ruff>=0.6.0",
  "mypy>=1.10.0"
]

[tool.uv]
package = true

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

## Basic usage

Inside a local clone with remotes like this:

```text
origin    git@github.com:YOUR_NAME/pipreqs.git
upstream  https://github.com/bndr/pipreqs.git
```

run:

```bash
repo-agent-context build
```

The tool should detect:

```text
Upstream: bndr/pipreqs
Fork: YOUR_NAME/pipreqs
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
  --upstream bndr/pipreqs \
  --fork YOUR_NAME/pipreqs \
  --out agent_context \
  --agent-file AGENT.md
```

If there is no fork:

```bash
repo-agent-context build --upstream psf/requests
```

## Repository detection

If `--upstream` and `--fork` are omitted, the tool reads Git remotes:

- `upstream` remote becomes the upstream repository.
- `origin` remote becomes the fork repository.
- If no `upstream` remote exists, `origin` is used as upstream.
- If fork and upstream resolve to the same repository, fork is treated as absent.

Supported GitHub remote formats:

```text
git@github.com:owner/repo.git
https://github.com/owner/repo.git
https://github.com/owner/repo
ssh://git@github.com/owner/repo.git
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

### `agent_context/branches_ahead.json`

Compact structured data for local remote branches that are ahead of `master`. It uses already-fetched local remote refs, so run `git fetch upstream` before building if you need fresh branch data.

### `agent_context/index/branches_ahead.md`

Markdown summary of branches ahead of `master`, including each ahead commit's short SHA, subject, author, and authored time.

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
--upstream, -u          Upstream GitHub repository, e.g. bndr/pipreqs.
--fork, -f              Fork GitHub repository, e.g. YOUR_NAME/pipreqs.
--out, -o               Output directory. Default: agent_context
--agent-file            Generated agent instruction file. Default: AGENT.md
--issue-limit           Maximum number of issues to fetch. Default: 300
--pr-limit              Maximum number of pull requests to fetch. Default: 300
--include-closed        Fetch closed issues and PRs as well.
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

## Suggested `.gitignore` behavior

By default, the tool creates `.gitignore` if missing and appends these entries if absent:

```gitignore
agent_context/
AGENT.md
```

This prevents local agent context snapshots from being accidentally committed to upstream projects.

## Possible future extensions

Useful next features:

1. Separate `--issue-state` and `--pr-state` options.
2. Label filters.
3. Date filters.
4. A relation index that detects `Fixes #123`, `Closes #123`, and `Refs #123`.
5. A stale PR report.
6. A good-first-issue ranking report.
7. Optional SQLite index.
8. Optional embedding index.
9. GitLab provider.
10. Gitea provider.

## License

Choose a license before publishing. MIT or Apache-2.0 would both be reasonable for a small developer tool.
