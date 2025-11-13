"""Main entry point for Telegram Note bot."""

import logging
import json
import markdown
from urllib.parse import urlencode
from telegram import Update, BotCommand, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import Config
from models import Database
from modules.note_module import NoteModule
from modules.schedule_module import ScheduleModule
from services.reminder_service import ReminderService
from webapp_server import WebAppServer
from utils.pagination import (
    PaginationHelper,
    format_note_for_list,
    format_schedule_for_list,
    format_note_button,
    format_schedule_button
)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
EDITING_NOTE = 1
EDITING_SCHEDULE = 2


class TelegramNoteBot:
    """Main bot class."""

    def __init__(self):
        """Initialize bot with database and modules."""
        Config.validate()
        self.db = Database(Config.DATABASE_PATH)
        self.note_module = NoteModule(self.db)
        self.schedule_module = ScheduleModule(self.db)
        self.reminder_service = ReminderService(self.db)
        self.webapp_server = WebAppServer(port=Config.WEBAPP_PORT)

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))

    def _render_markdown_preview(self, content: str, max_length: int = 300) -> str:
        """Render markdown content as HTML preview for Telegram."""
        content_preview = content[:max_length] + '...' if len(content) > max_length else content

        if not content_preview.strip():
            return ""

        try:
            html_preview = markdown.markdown(content_preview)
            # Clean up HTML tags that Telegram doesn't support well
            html_preview = html_preview.replace('<p>', '').replace('</p>', '\n')
            html_preview = html_preview.replace('<h1>', '\n<b>').replace('</h1>', '</b>')
            html_preview = html_preview.replace('<h2>', '\n<b>').replace('</h2>', '</b>')
            html_preview = html_preview.replace('<h3>', '\n<b>').replace('</h3>', '</b>')
            html_preview = html_preview.replace('<em>', '<i>').replace('</em>', '</i>')
            return html_preview.strip()
        except Exception as e:
            logger.warning(f"Failed to render markdown preview: {e}")
            return self._escape_html(content_preview)

    async def setup_commands(self, application: Application):
        """Set up bot commands for auto-completion."""
        commands = [
            BotCommand("start", "Start the bot and show help"),
            BotCommand("help", "Show available commands"),
            BotCommand("notes", "List all notes (optionally filter by keyword/tag)"),
            BotCommand("note", "Open or create a note"),
            BotCommand("schedules", "List all schedules (optionally filter by period)"),
            BotCommand("schedule", "Open or create a schedule"),
            BotCommand("delete", "Delete a note or schedule by name"),
        ]
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands registered for auto-completion")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Welcome to Telegram Note! 📝\n\n"
            "Available commands:\n"
            "/notes [keyword/tag] - List notes\n"
            "/note <name> - Open or create a note\n"
            "/schedules [period] - List schedules\n"
            "/schedule <name> - Open or create a schedule\n"
            "/delete <name> - Delete a note or schedule\n"
            "/help - Show this help message"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await self.start(update, context)

    async def notes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /notes command with pagination."""
        user_id = update.effective_user.id
        keyword = ' '.join(context.args) if context.args else None

        notes = self.note_module.list_notes(user_id, keyword)

        if not notes:
            await update.message.reply_text("No notes found.")
            return

        # Sort by updated_at descending (most recent first)
        notes.sort(key=lambda n: n.updated_at if n.updated_at else "", reverse=True)

        # Create pagination helper
        paginator = PaginationHelper(notes, items_per_page=10, callback_prefix="notes_page")

        # Store paginator in context for callback handlers
        context.user_data['notes_paginator'] = paginator
        context.user_data['notes_keyword'] = keyword

        # Get first page
        keyboard = paginator.get_keyboard(
            page=0,
            item_callback_prefix="view_note",
            item_formatter=format_note_button
        )

        # Build header message
        filter_msg = f" (filtered by: {keyword})" if keyword else ""
        header = f"📝 Your Notes{filter_msg}\n"
        header += f"Showing {len(notes)} note(s)\n\n"
        header += "Tap a note to view or edit it:"

        await update.message.reply_text(
            header,
            reply_markup=keyboard
        )

    async def note_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /note command - opens Web App editor."""
        if not context.args:
            await update.message.reply_text("Usage: /note <name>")
            return

        user_id = update.effective_user.id
        note_name = context.args[0]

        note = self.note_module.get_note(user_id, note_name)

        # Build URL with note data
        params = {'name': note_name}
        if note:
            params['title'] = note.title
            params['tags'] = ','.join(note.tags) if note.tags else ''
            params['content'] = note.content

        webapp_url = f"{self.webapp_server.get_url('note_editor.html', base_url=Config.WEBAPP_BASE_URL)}?{urlencode(params)}"

        # Create reply keyboard with Web App button
        # Note: Reply keyboards (not inline) are required for web_app.sendData() to work
        keyboard = [[KeyboardButton(
            text="📝 Edit Note",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )

        if note:
            # Build message with HTML formatting
            message_parts = [
                f"📝 <b>Note: {self._escape_html(note.name)}</b>\n",
                f"<b>{self._escape_html(note.title)}</b>",
                f"🏷 Tags: {', '.join(self._escape_html(t) for t in note.tags)}" if note.tags else "🏷 Tags: None",
            ]

            # Add markdown preview
            html_preview = self._render_markdown_preview(note.content)
            if html_preview:
                message_parts.append(f"\n{html_preview}")

            message_parts.append("\n<i>Tap the button below to edit this note in a rich editor</i>")
            message = '\n'.join(message_parts)
            parse_mode = 'HTML'
        else:
            message = (
                f"📝 Creating new note: {note_name}\n\n"
                f"Tap the button below to open the editor"
            )
            parse_mode = None

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    async def schedules_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedules command with pagination."""
        user_id = update.effective_user.id
        period = ' '.join(context.args) if context.args else None

        schedules = self.schedule_module.list_schedules(user_id, period)

        if not schedules:
            await update.message.reply_text("No schedules found.")
            return

        # Sort by updated_at descending (most recent first)
        schedules.sort(key=lambda s: s.updated_at if s.updated_at else "", reverse=True)

        # Create pagination helper
        paginator = PaginationHelper(schedules, items_per_page=10, callback_prefix="schedules_page")

        # Store paginator in context for callback handlers
        context.user_data['schedules_paginator'] = paginator
        context.user_data['schedules_period'] = period

        # Get first page
        keyboard = paginator.get_keyboard(
            page=0,
            item_callback_prefix="view_schedule",
            item_formatter=format_schedule_button
        )

        # Build header message
        filter_msg = f" (period: {period})" if period else ""
        header = f"📅 Your Schedules{filter_msg}\n"
        header += f"Showing {len(schedules)} schedule(s)\n\n"
        header += "Tap a schedule to view or edit it:"

        await update.message.reply_text(
            header,
            reply_markup=keyboard
        )

    async def schedule_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /schedule command - opens Web App editor."""
        if not context.args:
            await update.message.reply_text("Usage: /schedule <name>")
            return

        user_id = update.effective_user.id
        schedule_name = context.args[0]

        schedule = self.schedule_module.get_schedule(user_id, schedule_name)

        # Build URL with schedule data
        params = {'name': schedule_name}
        if schedule:
            params['title'] = schedule.title
            params['start_datetime'] = schedule.start_datetime.isoformat()
            params['end_datetime'] = schedule.end_datetime.isoformat()
            params['reminder_minutes'] = str(schedule.reminder_minutes) if schedule.reminder_minutes else '0'
            params['description'] = schedule.description

        webapp_url = f"{self.webapp_server.get_url('schedule_editor.html', base_url=Config.WEBAPP_BASE_URL)}?{urlencode(params)}"

        # Create reply keyboard with Web App button
        keyboard = [[KeyboardButton(
            text="📅 Edit Schedule",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )

        if schedule:
            # Build message with HTML formatting
            message_parts = [
                f"📅 <b>Schedule: {self._escape_html(schedule.name)}</b>\n",
                f"<b>{self._escape_html(schedule.title)}</b>",
                f"🕐 {schedule.start_datetime.strftime('%Y-%m-%d %H:%M')} - {schedule.end_datetime.strftime('%H:%M')}",
                f"⏰ Reminder: {schedule.reminder_minutes} min before" if schedule.reminder_minutes else "",
            ]

            # Add markdown preview for description
            if schedule.description:
                html_preview = self._render_markdown_preview(schedule.description)
                if html_preview:
                    message_parts.append(f"\n{html_preview}")

            message_parts.append("\n<i>Tap the button below to edit this schedule in a rich editor</i>")
            message = '\n'.join(filter(None, message_parts))
            parse_mode = 'HTML'
        else:
            message = (
                f"📅 Creating new schedule: {schedule_name}\n\n"
                f"Tap the button below to open the editor"
            )
            parse_mode = None

        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

    async def delete_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /delete command - deletes a note or schedule."""
        if not context.args:
            await update.message.reply_text(
                "Usage: /delete <name>\n\n"
                "Delete a note or schedule by name."
            )
            return

        user_id = update.effective_user.id
        name = context.args[0]

        # Try to find as a note first
        note = self.note_module.get_note(user_id, name)
        if note:
            # Delete the note
            if self.note_module.delete_note(user_id, name):
                await update.message.reply_text(
                    f"✅ Note '{name}' has been deleted successfully."
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to delete note '{name}'."
                )
            return

        # Try to find as a schedule
        schedule = self.schedule_module.get_schedule(user_id, name)
        if schedule:
            # Cancel reminder if it exists
            if schedule.reminder_minutes and schedule.id:
                self.reminder_service.cancel_reminder(schedule.id)
                logger.info(f"Cancelled reminder for schedule '{name}' (ID: {schedule.id})")

            # Delete the schedule
            if self.schedule_module.delete_schedule(user_id, name):
                await update.message.reply_text(
                    f"✅ Schedule '{name}' has been deleted successfully.\n"
                    f"{'🔕 Associated reminder has been cancelled.' if schedule.reminder_minutes else ''}"
                )
            else:
                await update.message.reply_text(
                    f"❌ Failed to delete schedule '{name}'."
                )
            return

        # Not found
        await update.message.reply_text(
            f"❌ No note or schedule found with name '{name}'.\n\n"
            f"Use /notes or /schedules to see available items."
        )

    async def handle_web_app_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data submitted from Web App (notes or schedules)."""
        user_id = update.effective_user.id

        try:
            # Parse the JSON data from the Web App
            data = json.loads(update.effective_message.web_app_data.data)

            # Determine if this is a note or schedule based on fields
            if 'start_datetime' in data:
                # This is a schedule
                await self._handle_schedule_web_app_data(update, user_id, data)
            else:
                # This is a note
                await self._handle_note_web_app_data(update, user_id, data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Web App data: {e}")
            logger.error(f"Raw data: {update.effective_message.web_app_data.data}")
            await update.effective_message.reply_text("❌ Error: Invalid data received from editor")
        except Exception as e:
            logger.error(f"Error handling Web App data: {e}", exc_info=True)
            await update.effective_message.reply_text(f"❌ Error saving: {str(e)}")

    async def _handle_note_web_app_data(self, update: Update, user_id: int, data: dict):
        """Handle note data from Web App."""
        note_name = data.get('name')
        title = data.get('title')
        tags_str = data.get('tags', '')
        content = data.get('content', '')

        logger.info(f"Received Web App data for note '{note_name}' from user {user_id}")
        logger.debug(f"Data: title={title}, tags={tags_str}, content_len={len(content)}")

        # Parse tags
        tags = [t.strip() for t in tags_str.split(',') if t.strip()]

        # Save the note
        self.note_module.save_note(
            user_id=user_id,
            name=note_name,
            title=title,
            tags=tags,
            content=content
        )

        # Build success message with HTML formatting
        message_parts = [
            "✅ <b>Note saved successfully!</b>\n",
            f"📝 <b>{self._escape_html(title)}</b>",
            f"🏷 Tags: {', '.join(self._escape_html(t) for t in tags)}" if tags else "🏷 Tags: None",
        ]

        # Add markdown preview
        html_preview = self._render_markdown_preview(content, max_length=200)
        if html_preview:
            message_parts.append(f"\n{html_preview}")

        await update.effective_message.reply_text(
            '\n'.join(message_parts),
            parse_mode='HTML'
        )

        logger.info(f"Note '{note_name}' saved successfully for user {user_id} via Web App")

    async def _handle_schedule_web_app_data(self, update: Update, user_id: int, data: dict):
        """Handle schedule data from Web App."""
        from datetime import datetime

        schedule_name = data.get('name')
        title = data.get('title')
        start_datetime_str = data.get('start_datetime')
        end_datetime_str = data.get('end_datetime')
        reminder_minutes_str = data.get('reminder_minutes', '0')
        description = data.get('description', '')

        logger.info(f"Received Web App data for schedule '{schedule_name}' from user {user_id}")

        # Parse reminder minutes
        reminder_minutes = int(reminder_minutes_str) if reminder_minutes_str else 0

        # Save the schedule (save_schedule expects datetime strings, not objects)
        self.schedule_module.save_schedule(
            user_id=user_id,
            name=schedule_name,
            title=title,
            start_datetime=start_datetime_str,
            end_datetime=end_datetime_str,
            reminder_minutes=reminder_minutes,
            description=description
        )

        # Parse datetime for display in success message
        start_datetime = datetime.fromisoformat(start_datetime_str.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(end_datetime_str.replace('Z', '+00:00'))

        # Schedule reminder if needed
        if reminder_minutes > 0:
            schedule = self.schedule_module.get_schedule(user_id, schedule_name)
            if schedule:
                self.reminder_service.schedule_reminder(schedule)

        # Build success message with HTML formatting
        message_parts = [
            "✅ <b>Schedule saved successfully!</b>\n",
            f"📅 <b>{self._escape_html(title)}</b>",
            f"🕐 {start_datetime.strftime('%Y-%m-%d %H:%M')} - {end_datetime.strftime('%H:%M')}",
            f"⏰ Reminder: {reminder_minutes} min before" if reminder_minutes else "",
        ]

        # Add markdown preview for description
        if description:
            html_preview = self._render_markdown_preview(description, max_length=200)
            if html_preview:
                message_parts.append(f"\n{html_preview}")

        await update.effective_message.reply_text(
            '\n'.join(filter(None, message_parts)),
            parse_mode='HTML'
        )

        logger.info(f"Schedule '{schedule_name}' saved successfully for user {user_id} via Web App")

    async def handle_notes_page_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pagination for notes list."""
        query = update.callback_query
        await query.answer()

        # Extract page number from callback data (format: "notes_page:0")
        page = int(query.data.split(':')[1])

        # Get paginator from context
        paginator = context.user_data.get('notes_paginator')
        keyword = context.user_data.get('notes_keyword')

        if not paginator:
            await query.edit_message_text("Session expired. Please use /notes again.")
            return

        # Generate keyboard for the requested page
        keyboard = paginator.get_keyboard(
            page=page,
            item_callback_prefix="view_note",
            item_formatter=format_note_button
        )

        # Update message with new keyboard
        filter_msg = f" (filtered by: {keyword})" if keyword else ""
        header = f"📝 Your Notes{filter_msg}\n"
        header += f"Showing {len(paginator.items)} note(s)\n\n"
        header += "Tap a note to view or edit it:"

        await query.edit_message_text(
            header,
            reply_markup=keyboard
        )

    async def handle_schedules_page_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle pagination for schedules list."""
        query = update.callback_query
        await query.answer()

        # Extract page number from callback data (format: "schedules_page:0")
        page = int(query.data.split(':')[1])

        # Get paginator from context
        paginator = context.user_data.get('schedules_paginator')
        period = context.user_data.get('schedules_period')

        if not paginator:
            await query.edit_message_text("Session expired. Please use /schedules again.")
            return

        # Generate keyboard for the requested page
        keyboard = paginator.get_keyboard(
            page=page,
            item_callback_prefix="view_schedule",
            item_formatter=format_schedule_button
        )

        # Update message with new keyboard
        filter_msg = f" (period: {period})" if period else ""
        header = f"📅 Your Schedules{filter_msg}\n"
        header += f"Showing {len(paginator.items)} schedule(s)\n\n"
        header += "Tap a schedule to view or edit it:"

        await query.edit_message_text(
            header,
            reply_markup=keyboard
        )

    async def handle_view_note_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle viewing a specific note from the list."""
        query = update.callback_query
        await query.answer()

        # Extract note name from callback data (format: "view_note:note-name")
        note_name = query.data.split(':', 1)[1]
        user_id = update.effective_user.id

        note = self.note_module.get_note(user_id, note_name)

        if not note:
            await query.edit_message_text("Note not found.")
            return

        # Build URL with note data
        params = {'name': note_name}
        if note:
            params['title'] = note.title
            params['tags'] = ','.join(note.tags) if note.tags else ''
            params['content'] = note.content

        webapp_url = f"{self.webapp_server.get_url('note_editor.html', base_url=Config.WEBAPP_BASE_URL)}?{urlencode(params)}"

        # Create reply keyboard with Web App button
        keyboard = [[KeyboardButton(
            text="📝 Edit Note",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )

        # Build message with HTML formatting
        message_parts = [
            f"📝 <b>Note: {self._escape_html(note.name)}</b>\n",
            f"<b>{self._escape_html(note.title)}</b>",
            f"🏷 Tags: {', '.join(self._escape_html(t) for t in note.tags)}" if note.tags else "🏷 Tags: None",
        ]

        # Add markdown preview
        html_preview = self._render_markdown_preview(note.content)
        if html_preview:
            message_parts.append(f"\n{html_preview}")

        message_parts.append("\n<i>Tap the button below to edit this note in a rich editor</i>")

        # Send new message (can't edit inline keyboard message to add reply keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text='\n'.join(message_parts),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def handle_view_schedule_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle viewing a specific schedule from the list."""
        query = update.callback_query
        await query.answer()

        # Extract schedule name from callback data (format: "view_schedule:schedule-name")
        schedule_name = query.data.split(':', 1)[1]
        user_id = update.effective_user.id

        schedule = self.schedule_module.get_schedule(user_id, schedule_name)

        if not schedule:
            await query.edit_message_text("Schedule not found.")
            return

        # Build URL with schedule data
        params = {
            'name': schedule_name,
            'title': schedule.title,
            'start_datetime': schedule.start_datetime.isoformat(),
            'end_datetime': schedule.end_datetime.isoformat(),
            'reminder_minutes': str(schedule.reminder_minutes) if schedule.reminder_minutes else '0',
            'description': schedule.description
        }

        webapp_url = f"{self.webapp_server.get_url('schedule_editor.html', base_url=Config.WEBAPP_BASE_URL)}?{urlencode(params)}"

        # Create reply keyboard with Web App button
        keyboard = [[KeyboardButton(
            text="📅 Edit Schedule",
            web_app=WebAppInfo(url=webapp_url)
        )]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard,
            one_time_keyboard=True,
            resize_keyboard=True
        )

        # Build message with HTML formatting
        message_parts = [
            f"📅 <b>Schedule: {self._escape_html(schedule.name)}</b>\n",
            f"<b>{self._escape_html(schedule.title)}</b>",
            f"🕐 {schedule.start_datetime.strftime('%Y-%m-%d %H:%M')} - {schedule.end_datetime.strftime('%H:%M')}",
            f"⏰ Reminder: {schedule.reminder_minutes} min before" if schedule.reminder_minutes else "",
        ]

        # Add markdown preview for description
        if schedule.description:
            html_preview = self._render_markdown_preview(schedule.description)
            if html_preview:
                message_parts.append(f"\n{html_preview}")

        message_parts.append("\n<i>Tap the button below to edit this schedule in a rich editor</i>")

        # Send new message (can't edit inline keyboard message to add reply keyboard)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text='\n'.join(filter(None, message_parts)),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    async def handle_noop_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle noop callback (page indicator button)."""
        query = update.callback_query
        await query.answer()  # Just acknowledge, no action needed

    async def debug_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug handler to see what updates we receive."""
        logger.info(f"=== DEBUG: Received update type: {type(update)}")
        logger.info(f"=== DEBUG: Update object: {update}")
        if hasattr(update, 'message') and update.message:
            logger.info(f"=== DEBUG: Message type: {type(update.message)}")
            logger.info(f"=== DEBUG: Has web_app_data: {hasattr(update.message, 'web_app_data')}")
            if hasattr(update.message, 'web_app_data') and update.message.web_app_data:
                logger.info(f"=== DEBUG: Web App Data found! {update.message.web_app_data.data[:100]}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages for editing notes and schedules."""
        # Debug log
        logger.info(f"handle_message called for user {update.effective_user.id}")

        user_id = update.effective_user.id
        text = update.message.text

        # Check if editing a note
        if 'editing_note' in context.user_data:
            note_name = context.user_data['editing_note']
            try:
                parts = [p.strip() for p in text.split('|')]
                if len(parts) < 3:
                    await update.message.reply_text(
                        "Invalid format. Use: title | tags | content"
                    )
                    return

                title = parts[0]
                tags = [t.strip() for t in parts[1].split(',')] if parts[1] else []
                content = parts[2]

                self.note_module.save_note(user_id, note_name, title, tags, content)
                await update.message.reply_text(f"✅ Note '{note_name}' saved!")
                del context.user_data['editing_note']
            except Exception as e:
                logger.error(f"Error saving note: {e}")
                await update.message.reply_text(f"❌ Error saving note: {str(e)}")

        # Check if editing a schedule
        elif 'editing_schedule' in context.user_data:
            schedule_name = context.user_data['editing_schedule']
            try:
                parts = [p.strip() for p in text.split('|')]
                if len(parts) < 5:
                    await update.message.reply_text(
                        "Invalid format. Use: title | start | end | reminder_min | description"
                    )
                    return

                title = parts[0]
                start = parts[1]
                end = parts[2]
                reminder_minutes = int(parts[3]) if parts[3] else None
                description = parts[4]

                self.schedule_module.save_schedule(
                    user_id, schedule_name, title, start, end, reminder_minutes, description
                )

                # Schedule reminder if reminder_minutes is set
                schedule = self.schedule_module.get_schedule(user_id, schedule_name)
                if schedule and schedule.reminder_minutes:
                    self.reminder_service.schedule_reminder(schedule, context.application)

                await update.message.reply_text(f"✅ Schedule '{schedule_name}' saved!")
                del context.user_data['editing_schedule']
            except Exception as e:
                logger.error(f"Error saving schedule: {e}")
                await update.message.reply_text(f"❌ Error saving schedule: {str(e)}")

    async def post_init(self, application: Application):
        """Post-initialization callback to set up commands."""
        await self.setup_commands(application)

    def run(self):
        """Run the bot."""
        # Start Web App server
        try:
            self.webapp_server.start()
        except Exception as e:
            logger.error(f"Failed to start Web App server: {e}")
            logger.warning("Bot will continue without Web App support")

        # Create application
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("notes", self.notes_command))
        application.add_handler(CommandHandler("note", self.note_command))
        application.add_handler(CommandHandler("schedules", self.schedules_command))
        application.add_handler(CommandHandler("schedule", self.schedule_command))
        application.add_handler(CommandHandler("delete", self.delete_command))

        # Callback query handlers for pagination and item selection
        application.add_handler(CallbackQueryHandler(self.handle_notes_page_callback, pattern=r'^notes_page:\d+$'))
        application.add_handler(CallbackQueryHandler(self.handle_schedules_page_callback, pattern=r'^schedules_page:\d+$'))
        application.add_handler(CallbackQueryHandler(self.handle_view_note_callback, pattern=r'^view_note:'))
        application.add_handler(CallbackQueryHandler(self.handle_view_schedule_callback, pattern=r'^view_schedule:'))
        application.add_handler(CallbackQueryHandler(self.handle_noop_callback, pattern=r'^noop$'))

        # Web App data handler - try multiple filter combinations
        application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, self.handle_web_app_data))

        # Debug: Catch all messages to see what we're receiving
        from telegram.ext import TypeHandler
        application.add_handler(TypeHandler(Update, self.debug_handler), group=99)

        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        # Start reminder service
        self.reminder_service.start(application)

        # Set up post_init callback for command registration
        application.post_init = self.post_init

        # Start the bot
        logger.info("Starting Telegram Note bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    bot = TelegramNoteBot()
    bot.run()


if __name__ == '__main__':
    main()
