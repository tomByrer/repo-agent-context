# Contributing

Thanks for considering a contribution.

## Development Setup

```bash
git clone https://github.com/arnowaschk/repo-agent-context.git
cd repo-agent-context
uv sync
```

## Checks

Run the full local check set:

```bash
uv run tox
```

Or run checks individually:

```bash
uv run pytest -q
uv run coverage run -m pytest -q
uv run coverage report
uv run ruff check .
uv run mypy src
```

## Contribution Guidelines

- Keep generated context as plain Markdown and JSON.
- Keep code changes small and behavior-focused.
- Do not commit generated `agent_context/` snapshots unless a test fixture explicitly needs one.
- Add or update tests for behavior changes.
- Preserve 100% statement coverage, but prefer meaningful assertions over coverage-only tests.
- Avoid broad refactors in the same pull request as behavior changes.

## Release Checklist

Before publishing a release:

```bash
uv run pytest -q
uv run coverage run -m pytest -q
uv run coverage report
uv run ruff check .
uv run mypy src
uv run tox
uv build
```

Also inspect `README.md` and `SOCIAL_MEDIA.md` for stale examples, links, and version-specific wording.
