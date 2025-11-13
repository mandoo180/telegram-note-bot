"""Datetime utility functions."""

from datetime import datetime
from typing import Optional


def parse_datetime(datetime_str: str) -> datetime:
    """Parse datetime string to datetime object.

    Supports multiple formats:
    - ISO format: 2025-11-15T14:00:00
    - Space separated: 2025-11-15 14:00
    - With seconds: 2025-11-15 14:00:00

    Args:
        datetime_str: Datetime string to parse

    Returns:
        datetime object

    Raises:
        ValueError: If datetime string is invalid
    """
    # Try different formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M',
    ]

    for fmt in formats:
        try:
            return datetime.strptime(datetime_str, fmt)
        except ValueError:
            continue

    # If none worked, raise error
    raise ValueError(
        f"Invalid datetime format: {datetime_str}. "
        f"Expected format: YYYY-MM-DD HH:MM"
    )


def format_datetime(dt: datetime, include_seconds: bool = False) -> str:
    """Format datetime object to string.

    Args:
        dt: datetime object to format
        include_seconds: Whether to include seconds in output

    Returns:
        Formatted datetime string
    """
    if include_seconds:
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt.strftime('%Y-%m-%d %H:%M')


def parse_period(period: str) -> tuple[Optional[datetime], Optional[datetime]]:
    """Parse period string to start and end datetime.

    Supports: 'today', 'tomorrow', 'week', 'month'

    Args:
        period: Period string

    Returns:
        Tuple of (start_datetime, end_datetime)
    """
    from datetime import timedelta

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if period.lower() == 'today':
        return today, today + timedelta(days=1)
    elif period.lower() == 'tomorrow':
        tomorrow = today + timedelta(days=1)
        return tomorrow, tomorrow + timedelta(days=1)
    elif period.lower() == 'week':
        return today, today + timedelta(days=7)
    elif period.lower() == 'month':
        return today, today + timedelta(days=30)
    else:
        return None, None
