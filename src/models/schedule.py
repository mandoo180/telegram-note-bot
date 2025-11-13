"""Schedule model for storing and managing schedules."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Schedule:
    """Schedule data model."""

    id: Optional[int]
    user_id: int
    name: str
    title: str
    description: str
    start_datetime: datetime
    end_datetime: datetime
    reminder_minutes: Optional[int]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row) -> 'Schedule':
        """Create Schedule instance from database row.

        Args:
            row: Database row from sqlite3

        Returns:
            Schedule instance
        """
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            title=row['title'],
            description=row['description'] or '',
            start_datetime=datetime.fromisoformat(row['start_datetime']),
            end_datetime=datetime.fromisoformat(row['end_datetime']),
            reminder_minutes=row['reminder_minutes'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
