"""Schedule module for CRUD operations on schedules."""

from typing import List, Optional
from datetime import datetime
import logging

from models.database import Database
from models.schedule import Schedule

logger = logging.getLogger(__name__)


class ScheduleModule:
    """Handle schedule operations."""

    def __init__(self, db: Database):
        """Initialize schedule module.

        Args:
            db: Database instance
        """
        self.db = db

    def get_schedule(self, user_id: int, name: str) -> Optional[Schedule]:
        """Get a schedule by user ID and name.

        Args:
            user_id: Telegram user ID
            name: Schedule name

        Returns:
            Schedule instance or None if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM schedules WHERE user_id = ? AND name = ?",
                (user_id, name)
            )
            row = cursor.fetchone()
            return Schedule.from_db_row(row) if row else None

    def list_schedules(self, user_id: int, period: Optional[str] = None) -> List[Schedule]:
        """List schedules for a user, optionally filtered by period.

        Args:
            user_id: Telegram user ID
            period: Optional period filter (e.g., 'today', 'week', 'month')

        Returns:
            List of Schedule instances
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # For now, implement basic filtering
            # TODO: Enhance period filtering (today, week, month)
            if period:
                # Simple keyword search for now
                cursor.execute(
                    """
                    SELECT * FROM schedules
                    WHERE user_id = ?
                    AND (name LIKE ? OR title LIKE ? OR description LIKE ?)
                    ORDER BY start_datetime ASC
                    """,
                    (user_id, f"%{period}%", f"%{period}%", f"%{period}%")
                )
            else:
                cursor.execute(
                    "SELECT * FROM schedules WHERE user_id = ? ORDER BY start_datetime ASC",
                    (user_id,)
                )

            rows = cursor.fetchall()
            return [Schedule.from_db_row(row) for row in rows]

    def save_schedule(
        self,
        *,
        user_id: int,
        name: str,
        title: str,
        start_datetime: str,
        end_datetime: str,
        reminder_minutes: Optional[int] = None,
        description: str = ''
    ) -> Schedule:
        """Save (create or update) a schedule.

        Args:
            user_id: Telegram user ID
            name: Schedule name
            title: Schedule title
            start_datetime: Start datetime string (ISO format)
            end_datetime: End datetime string (ISO format)
            reminder_minutes: Minutes before event to send reminder
            description: Schedule description

        Returns:
            Saved Schedule instance
        """
        # Parse datetime strings
        start_dt = datetime.fromisoformat(start_datetime.replace(' ', 'T'))
        end_dt = datetime.fromisoformat(end_datetime.replace(' ', 'T'))

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if schedule exists
            existing = self.get_schedule(user_id, name)

            if existing:
                # Update existing schedule
                cursor.execute(
                    """
                    UPDATE schedules
                    SET title = ?, description = ?, start_datetime = ?,
                        end_datetime = ?, reminder_minutes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND name = ?
                    """,
                    (title, description, start_dt.isoformat(), end_dt.isoformat(),
                     reminder_minutes, user_id, name)
                )
                logger.info(f"Updated schedule '{name}' for user {user_id}")
            else:
                # Create new schedule
                cursor.execute(
                    """
                    INSERT INTO schedules
                    (user_id, name, title, description, start_datetime, end_datetime, reminder_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, name, title, description, start_dt.isoformat(),
                     end_dt.isoformat(), reminder_minutes)
                )
                logger.info(f"Created schedule '{name}' for user {user_id}")

            conn.commit()

        return self.get_schedule(user_id, name)

    def delete_schedule(self, user_id: int, name: str) -> bool:
        """Delete a schedule.

        Args:
            user_id: Telegram user ID
            name: Schedule name

        Returns:
            True if deleted, False if not found
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM schedules WHERE user_id = ? AND name = ?",
                (user_id, name)
            )
            conn.commit()
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Deleted schedule '{name}' for user {user_id}")

            return deleted

    def get_upcoming_schedules(self, user_id: int, limit: int = 10) -> List[Schedule]:
        """Get upcoming schedules for a user.

        Args:
            user_id: Telegram user ID
            limit: Maximum number of schedules to return

        Returns:
            List of upcoming Schedule instances
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM schedules
                WHERE user_id = ? AND start_datetime >= datetime('now')
                ORDER BY start_datetime ASC
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = cursor.fetchall()
            return [Schedule.from_db_row(row) for row in rows]
