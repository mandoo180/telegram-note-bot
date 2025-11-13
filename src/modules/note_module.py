"""Note module for CRUD operations on notes."""

from typing import List, Optional
import logging

from models.database import Database
from models.note import Note

logger = logging.getLogger(__name__)


class NoteModule:
    """Handle note operations."""

    def __init__(self, db: Database):
        """Initialize note module.

        Args:
            db: Database instance
        """
        self.db = db

    def get_note(self, user_id: int, name: str) -> Optional[Note]:
        """Get a note by user ID and name.

        Args:
            user_id: Telegram user ID
            name: Note name

        Returns:
            Note instance or None if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM notes WHERE user_id = ? AND name = ?",
                (user_id, name)
            )
            row = cursor.fetchone()
            return Note.from_db_row(row) if row else None

    def list_notes(self, user_id: int, keyword: Optional[str] = None) -> List[Note]:
        """List notes for a user, optionally filtered by keyword/tag.

        Args:
            user_id: Telegram user ID
            keyword: Optional keyword or tag to filter by

        Returns:
            List of Note instances
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            if keyword:
                # Search in name, title, tags, and content
                cursor.execute(
                    """
                    SELECT * FROM notes
                    WHERE user_id = ?
                    AND (name LIKE ? OR title LIKE ? OR tags LIKE ? OR content LIKE ?)
                    ORDER BY updated_at DESC
                    """,
                    (user_id, f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", f"%{keyword}%")
                )
            else:
                cursor.execute(
                    "SELECT * FROM notes WHERE user_id = ? ORDER BY updated_at DESC",
                    (user_id,)
                )

            rows = cursor.fetchall()
            return [Note.from_db_row(row) for row in rows]

    def save_note(
        self,
        *,
        user_id: int,
        name: str,
        title: str,
        tags: List[str] = None,
        content: str = ''
    ) -> Note:
        """Save (create or update) a note.

        Args:
            user_id: Telegram user ID
            name: Note name
            title: Note title
            tags: List of tags
            content: Note content in markdown

        Returns:
            Saved Note instance
        """
        if tags is None:
            tags = []
        tags_str = ','.join(tags) if tags else ''

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if note exists
            existing = self.get_note(user_id, name)

            if existing:
                # Update existing note
                cursor.execute(
                    """
                    UPDATE notes
                    SET title = ?, tags = ?, content = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND name = ?
                    """,
                    (title, tags_str, content, user_id, name)
                )
                logger.info(f"Updated note '{name}' for user {user_id}")
            else:
                # Create new note
                cursor.execute(
                    """
                    INSERT INTO notes (user_id, name, title, tags, content)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (user_id, name, title, tags_str, content)
                )
                logger.info(f"Created note '{name}' for user {user_id}")

            conn.commit()

        return self.get_note(user_id, name)

    def delete_note(self, user_id: int, name: str) -> bool:
        """Delete a note.

        Args:
            user_id: Telegram user ID
            name: Note name

        Returns:
            True if deleted, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM notes WHERE user_id = ? AND name = ?",
                (user_id, name)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Deleted note '{name}' for user {user_id}")

            return deleted
