"""Pagination utilities for listing items."""

from typing import List, Callable, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime


class PaginationHelper:
    """Helper class for paginating lists with inline keyboards."""

    def __init__(
        self,
        items: List[Any],
        items_per_page: int = 10,
        callback_prefix: str = "page"
    ):
        """Initialize pagination helper.

        Args:
            items: List of items to paginate
            items_per_page: Number of items per page
            callback_prefix: Prefix for callback data
        """
        self.items = items
        self.items_per_page = items_per_page
        self.callback_prefix = callback_prefix
        self.total_pages = max(1, (len(items) + items_per_page - 1) // items_per_page)

    def get_page(self, page: int = 0) -> List[Any]:
        """Get items for a specific page.

        Args:
            page: Page number (0-indexed)

        Returns:
            List of items for the page
        """
        start = page * self.items_per_page
        end = start + self.items_per_page
        return self.items[start:end]

    def get_keyboard(
        self,
        page: int,
        item_callback_prefix: str,
        item_formatter: Callable[[Any], tuple[str, str]]
    ) -> InlineKeyboardMarkup:
        """Generate inline keyboard for a page.

        Args:
            page: Current page number (0-indexed)
            item_callback_prefix: Prefix for item callback data
            item_formatter: Function that formats item to (button_text, callback_data)

        Returns:
            InlineKeyboardMarkup with items and navigation
        """
        keyboard = []

        # Add item buttons (one per row)
        page_items = self.get_page(page)
        for item in page_items:
            button_text, callback_data = item_formatter(item)
            keyboard.append([InlineKeyboardButton(
                text=button_text,
                callback_data=f"{item_callback_prefix}:{callback_data}"
            )])

        # Add navigation buttons
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(
                text="⬅️ Previous",
                callback_data=f"{self.callback_prefix}:{page - 1}"
            ))

        # Add page indicator
        if self.total_pages > 1:
            nav_buttons.append(InlineKeyboardButton(
                text=f"· {page + 1}/{self.total_pages} ·",
                callback_data="noop"
            ))

        if page < self.total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"{self.callback_prefix}:{page + 1}"
            ))

        if nav_buttons:
            keyboard.append(nav_buttons)

        return InlineKeyboardMarkup(keyboard)


def format_note_for_list(note) -> str:
    """Format a note as a card for list display.

    Args:
        note: Note object

    Returns:
        Formatted string
    """
    # Format date
    if note.updated_at:
        date_str = note.updated_at.strftime('%b %d, %H:%M')
    else:
        date_str = "Unknown"

    # Truncate content preview
    content_preview = note.content[:50].replace('\n', ' ') if note.content else "No content"
    if len(note.content) > 50:
        content_preview += "..."

    # Tags
    tags_str = f"🏷 {', '.join(note.tags)}" if note.tags else ""

    return f"📝 *{note.title}*\n{content_preview}\n{tags_str}\n🕐 {date_str}"


def format_schedule_for_list(schedule) -> str:
    """Format a schedule as a card for list display.

    Args:
        schedule: Schedule object

    Returns:
        Formatted string
    """
    # Format dates
    start_str = schedule.start_datetime.strftime('%b %d, %H:%M')
    end_str = schedule.end_datetime.strftime('%H:%M')

    # Reminder indicator
    reminder_str = ""
    if schedule.reminder_minutes:
        reminder_str = f" 🔔 {schedule.reminder_minutes}m"

    # Description preview
    desc_preview = schedule.description[:50].replace('\n', ' ') if schedule.description else ""
    if len(schedule.description) > 50:
        desc_preview += "..."

    return f"📅 *{schedule.title}*\n{desc_preview}\n🕐 {start_str} - {end_str}{reminder_str}"


def format_note_button(note) -> tuple[str, str]:
    """Format note for inline keyboard button.

    Args:
        note: Note object

    Returns:
        Tuple of (button_text, callback_data)
    """
    # Button text with ID/name shown first
    button_text = f"📝 [{note.name}] {note.title}"
    if len(button_text) > 60:
        # Prioritize showing the name/ID
        max_title_len = 60 - len(f"📝 [{note.name}] ") - 3
        truncated_title = note.title[:max_title_len] + "..." if len(note.title) > max_title_len else note.title
        button_text = f"📝 [{note.name}] {truncated_title}"

    # Callback data
    callback_data = note.name

    return button_text, callback_data


def format_schedule_button(schedule) -> tuple[str, str]:
    """Format schedule for inline keyboard button.

    Args:
        schedule: Schedule object

    Returns:
        Tuple of (button_text, callback_data)
    """
    # Button text with ID/name shown first, then date
    start_str = schedule.start_datetime.strftime('%m/%d %H:%M')
    button_text = f"📅 [{schedule.name}] {schedule.title} - {start_str}"
    if len(button_text) > 60:
        # Prioritize showing the name/ID
        max_title_len = 60 - len(f"📅 [{schedule.name}] ") - len(f" - {start_str}") - 3
        truncated_title = schedule.title[:max_title_len] + "..." if len(schedule.title) > max_title_len else schedule.title
        button_text = f"📅 [{schedule.name}] {truncated_title} - {start_str}"

    # Callback data
    callback_data = schedule.name

    return button_text, callback_data
