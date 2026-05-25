from __future__ import annotations

from pathlib import Path

from repo_agent_context.cli import SUPPORT_URL


def test_social_media_posts_include_support_link_and_offline_examples() -> None:
    text = Path("SOCIAL_MEDIA.md").read_text(encoding="utf-8")

    assert SUPPORT_URL in text

