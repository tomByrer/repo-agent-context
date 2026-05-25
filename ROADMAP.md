# Roadmap

Possible future extensions:

1. Separate issue and pull request state options.
2. Label filters.
3. Date filters.
4. Stale PR reporting.
5. Good-first-issue ranking.
6. GitLab provider.
7. Gitea provider.

The current project intentionally starts with local Markdown and JSON files. New features should preserve that basic property unless there is a strong reason not to.

## Large Repository Support

Possible future options for very large repositories:

1. Optional RAG or embedding index over generated Markdown and JSON.
2. Optional SQLite or DuckDB metadata index.
3. Incremental refresh instead of full rebuilds.
4. Context size budgets for agent-specific summaries.
5. Configurable pruning for old comments, closed issues, and large diffs.

These should remain optional so the default workflow stays simple, local, and file-based.
