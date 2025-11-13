"""Markdown utility functions."""

import markdown
from typing import Optional


def render_markdown(text: str) -> str:
    """Render markdown text to HTML.

    Args:
        text: Markdown text

    Returns:
        HTML string
    """
    return markdown.markdown(text)


def escape_markdown_v2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2.

    Args:
        text: Text to escape

    Returns:
        Escaped text
    """
    # Characters that need to be escaped in MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']

    for char in special_chars:
        text = text.replace(char, f'\\{char}')

    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = '...') -> str:
    """Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix
