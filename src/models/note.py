"""Note model for storing and managing notes."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class Note:
    """Note data model."""

    id: Optional[int]
    user_id: int
    name: str
    title: str
    tags: List[str]
    content: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row) -> 'Note':
        """Create Note instance from database row.

        Args:
            row: Database row from sqlite3

        Returns:
            Note instance
        """
        tags = row['tags'].split(',') if row['tags'] else []
        return cls(
            id=row['id'],
            user_id=row['user_id'],
            name=row['name'],
            title=row['title'],
            tags=tags,
            content=row['content'] or '',
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    def tags_to_string(self) -> str:
        """Convert tags list to comma-separated string.

        Returns:
            Comma-separated tags
        """
        return ','.join(self.tags) if self.tags else ''
