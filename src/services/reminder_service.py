"""Reminder service for scheduling and sending notifications."""

import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

from models.database import Database
from models.schedule import Schedule

logger = logging.getLogger(__name__)


class ReminderService:
    """Handle reminder scheduling and notifications."""

    def __init__(self, db: Database):
        """Initialize reminder service.

        Args:
            db: Database instance
        """
        self.db = db
        self.scheduler = BackgroundScheduler()

    def start(self, application):
        """Start the reminder service.

        Args:
            application: Telegram bot application instance
        """
        self.application = application
        self.scheduler.start()
        logger.info("Reminder service started")

        # Load and schedule existing reminders
        self._load_pending_reminders()

    def stop(self):
        """Stop the reminder service."""
        self.scheduler.shutdown()
        logger.info("Reminder service stopped")

    def schedule_reminder(self, schedule: Schedule):
        """Schedule a reminder for a schedule.

        Args:
            schedule: Schedule instance
        """
        if not schedule.reminder_minutes:
            logger.info(f"No reminder set for schedule {schedule.name}")
            return

        # Calculate reminder time
        reminder_time = schedule.start_datetime - timedelta(minutes=schedule.reminder_minutes)

        # Don't schedule if reminder time is in the past
        if reminder_time <= datetime.now():
            logger.info(f"Reminder time for schedule {schedule.name} is in the past, skipping")
            return

        # Store reminder in database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO reminders (schedule_id, reminder_time, sent)
                VALUES (?, ?, FALSE)
                """,
                (schedule.id, reminder_time.isoformat())
            )
            conn.commit()

        # Schedule the job
        job_id = f"reminder_{schedule.id}"
        self.scheduler.add_job(
            self._send_reminder,
            trigger=DateTrigger(run_date=reminder_time),
            args=[schedule.user_id, schedule],
            id=job_id,
            replace_existing=True
        )

        logger.info(
            f"Scheduled reminder for schedule {schedule.name} "
            f"at {reminder_time.strftime('%Y-%m-%d %H:%M')}"
        )

    def _send_reminder(self, user_id: int, schedule: Schedule):
        """Send reminder notification to user (sync wrapper for async work).

        Args:
            user_id: Telegram user ID
            schedule: Schedule instance
        """
        # Use the application's job queue to run the async task
        self.application.job_queue.run_once(
            callback=self._send_reminder_async,
            when=0,  # Run immediately
            data={'user_id': user_id, 'schedule': schedule},
            name=f"send_reminder_{schedule.id}"
        )

    async def _send_reminder_async(self, context):
        """Async task to send reminder notification.

        Args:
            context: Job context containing user_id and schedule
        """
        user_id = context.job.data['user_id']
        schedule = context.job.data['schedule']

        try:
            message = (
                f"🔔 Reminder: {schedule.title}\n\n"
                f"Starts at: {schedule.start_datetime.strftime('%Y-%m-%d %H:%M')}\n"
                f"Ends at: {schedule.end_datetime.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"{schedule.description}"
            )

            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )

            # Mark reminder as sent
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE reminders
                    SET sent = TRUE, sent_at = CURRENT_TIMESTAMP
                    WHERE schedule_id = ?
                    """,
                    (schedule.id,)
                )
                conn.commit()

            logger.info(f"Sent reminder for schedule {schedule.name} to user {user_id}")

        except Exception as e:
            logger.error(f"Error sending reminder: {e}", exc_info=True)

    def _load_pending_reminders(self):
        """Load and schedule all pending reminders from database."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.*, r.reminder_time
                FROM schedules s
                JOIN reminders r ON s.id = r.schedule_id
                WHERE r.sent = FALSE AND r.reminder_time > datetime('now')
                """
            )
            rows = cursor.fetchall()

            for row in rows:
                schedule = Schedule.from_db_row(row)
                reminder_time = datetime.fromisoformat(row['reminder_time'])

                # Schedule the job
                job_id = f"reminder_{schedule.id}"
                self.scheduler.add_job(
                    self._send_reminder,
                    trigger=DateTrigger(run_date=reminder_time),
                    args=[schedule.user_id, schedule],
                    id=job_id,
                    replace_existing=True
                )

                logger.info(
                    f"Loaded pending reminder for schedule {schedule.name} "
                    f"at {reminder_time.strftime('%Y-%m-%d %H:%M')}"
                )

    def cancel_reminder(self, schedule_id: int):
        """Cancel a scheduled reminder.

        Args:
            schedule_id: Schedule ID
        """
        job_id = f"reminder_{schedule_id}"
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Cancelled reminder for schedule {schedule_id}")
        except Exception as e:
            logger.warning(f"Could not cancel reminder for schedule {schedule_id}: {e}")
