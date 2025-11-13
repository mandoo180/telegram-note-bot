# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Telegram Note is a Telegram bot that enables users to save notes, schedule personal events, and receive notification reminders. The bot uses slash commands for user interaction and supports markdown formatting for notes.

## Development Commands

### Local Development (without Docker)

```bash
# Setup virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database (first time setup)
python init_db.py

# Run the bot
python src/main.py

# Run with environment variables
export TELEGRAM_BOT_TOKEN="your_token_here"
python src/main.py

# Or use .env file
cp .env.example .env
# Edit .env with your token, then run:
python src/main.py
```

### Docker Deployment

```bash
# 1. Setup environment file
cp .env.example .env
# Edit .env with your Telegram bot token and other settings

# 2. Create data directory for database persistence
mkdir -p data

# 3. Initialize database (first time only)
docker-compose run --rm telegram-note python init_db.py

# 4. Start the bot
docker-compose up -d

# 5. View logs
docker-compose logs -f

# 6. Stop the bot
docker-compose down

# 7. Rebuild after code changes
docker-compose up -d --build

# 8. Backup database
cp data/telegram_note.db data/telegram_note.db.backup

# 9. Restore database
cp data/telegram_note.db.backup data/telegram_note.db
docker-compose restart
```

**Important Docker Notes:**
- The database is stored in `./data/telegram_note.db` (persisted via Docker volume)
- The database file is **NOT** in version control (excluded in `.gitignore`)
- Web App files in `./webapp/` are mounted for hot-reload during development
- Port 8000 is exposed for the Web App server (configure with `WEBAPP_PORT` in `.env`)
```

### Database Commands

```bash
# Initialize/create database
python init_db.py

# Open SQLite database shell
sqlite3 telegram_note.db

# Inspect database (within sqlite3 shell)
.tables                    # List all tables
.schema notes              # View notes table schema
.schema schedules          # View schedules table schema
.schema reminders          # View reminders table schema
SELECT * FROM notes;       # Query all notes
SELECT * FROM schedules;   # Query all schedules
.quit                      # Exit sqlite3 shell

# Reset database (delete and reinitialize)
rm telegram_note.db
python init_db.py

# Backup database
cp telegram_note.db telegram_note.db.backup

# Restore database from backup
cp telegram_note.db.backup telegram_note.db
```

## Core Features

### Slash Commands
- `/notes <keyword/tag>`: List notes filtered by keyword or tag
- `/note <name>`: Open existing note or create new note in markdown mode
- `/schedules <period>`: List schedules for a given period
- `/schedule <name>`: Open or create a schedule

### Note Management
Notes include:
- Title (editable)
- Tags (editable, multiple tags supported)
- Content in markdown format

### Schedule Management
Schedules include:
- Start and end datetime
- Title
- Description
- Reminder notifications (configurable: n minutes/hours/days before event)

## Development Setup

### Technology Stack

1. **Telegram Bot Framework**: python-telegram-bot v21.0
2. **Database**: SQLite (telegram_note.db)
3. **Markdown Parsing**: markdown package for rendering
4. **Reminder System**: APScheduler (Advanced Python Scheduler) for background job scheduling
5. **Configuration**: python-dotenv for environment variable management

### Project Structure

- `src/models/` - Database models (Database, Note, Schedule)
- `src/modules/` - Business logic (NoteModule, ScheduleModule)
- `src/services/` - Background services (ReminderService with APScheduler)
- `src/utils/` - Utility functions (datetime, markdown helpers)
- `src/webapp_server.py` - HTTP server for hosting Telegram Web App
- `src/config.py` - Configuration management
- `src/main.py` - Main bot entry point with command handlers
- `webapp/note_editor.html` - Rich Web App editor for notes
- `init_db.py` - Database initialization script

## Architecture Considerations

- **Bot Handler** (src/main.py:1): Process incoming slash commands and route to appropriate handlers. Commands are automatically registered with Telegram's Bot API for auto-completion support.
- **Note Module** (src/modules/note_module.py:1): CRUD operations for notes with tag and keyword search functionality
- **Schedule Module** (src/modules/schedule_module.py:1): CRUD operations for schedules with datetime handling
- **Reminder Service** (src/services/reminder_service.py:1): Background job/scheduler to trigger notifications at specified times using APScheduler
- **Storage Layer** (src/models/database.py:1): SQLite database with three tables
- **Markdown Processor** (src/utils/markdown_utils.py:1): Handle markdown formatting for note content display and editing

### Command Auto-Completion

The bot automatically registers all commands with Telegram using the `setMyCommands` API. This enables:
- Command suggestions when users type `/` in the chat
- Command descriptions visible in the auto-complete menu
- Better user experience without needing to memorize commands

Commands are registered in the `setup_commands()` method and called during bot initialization via the `post_init` callback.

### Telegram Web App Integration

The bot includes a rich Web App editor for notes (webapp/note_editor.html:1):
- **HTML/CSS/JS interface**: Full-featured note editor with live Markdown preview
- **Web Server** (src/webapp_server.py:1): Simple HTTP server serving the Web App files
- **HTTPS Requirement**: Telegram Web Apps require HTTPS URLs. For local development, use ngrok or similar tunneling service
- **Data Flow**:
  1. Bot sends `WebAppInfo` with URL to editor
  2. User edits note in the Web App
  3. Web App sends data back via `Telegram.WebApp.sendData()`
  4. Bot receives data in `handle_web_app_data()` handler
  5. Note is saved to database

**Configuration**:
- `WEBAPP_BASE_URL`: Public HTTPS URL (e.g., ngrok URL for development)
- `WEBAPP_PORT`: Local port for the web server (default: 8000)

**Fallback**: Text-based editing still works if Web App is not configured.

## Database Schema

### Notes Table
- `id` - Primary key
- `user_id` - Telegram user ID
- `name` - Unique note name (per user)
- `title` - Note title
- `tags` - Comma-separated tags
- `content` - Markdown content
- `created_at`, `updated_at` - Timestamps

### Schedules Table
- `id` - Primary key
- `user_id` - Telegram user ID
- `name` - Unique schedule name (per user)
- `title` - Schedule title
- `description` - Schedule description
- `start_datetime` - Start time (ISO format)
- `end_datetime` - End time (ISO format)
- `reminder_minutes` - Minutes before event to send reminder
- `created_at`, `updated_at` - Timestamps

### Reminders Table
- `id` - Primary key
- `schedule_id` - Foreign key to schedules
- `reminder_time` - When to send reminder
- `sent` - Boolean flag
- `sent_at` - When reminder was sent
