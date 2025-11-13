# Telegram Note

A Telegram bot that enables users to save notes, schedule personal events, and receive notification reminders.

## Features

- **Notes Management**: Create, edit, and search notes with tags in markdown format
- **Schedule Management**: Create and manage schedules with customizable reminders
- **Smart Reminders**: Get notified minutes, hours, or days before scheduled events
- **Simple Interface**: Easy-to-use slash commands for all operations

## Installation

### Prerequisites

- Python 3.8 or higher (for local development)
- Docker and Docker Compose (for Docker deployment)
- A Telegram Bot Token (get one from [@BotFather](https://t.me/botfather))

### Option 1: Docker Deployment (Recommended)

Docker provides an isolated environment and easier deployment. The database is automatically persisted in a local directory.

1. Clone the repository:
```bash
git clone <repository-url>
cd telegram-note
```

2. Configure the bot:
```bash
cp .env.example .env
```

3. Edit `.env` and add your Telegram Bot Token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_PATH=/app/data/telegram_note.db
WEBAPP_BASE_URL=http://localhost:8000
```

4. Create data directory for database persistence:
```bash
mkdir -p data
```

5. Initialize the database:
```bash
docker-compose run --rm telegram-note python init_db.py
```

6. Start the bot:
```bash
docker-compose up -d
```

7. View logs:
```bash
docker-compose logs -f
```

**Docker Management Commands:**
```bash
# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# Backup database
cp data/telegram_note.db data/telegram_note.db.backup

# Restore database
cp data/telegram_note.db.backup data/telegram_note.db
docker-compose restart
```

**Note**: The database file is stored in `./data/telegram_note.db` and is excluded from version control.

### Option 2: Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd telegram-note
```

2. Create and activate a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Initialize the database:
```bash
python init_db.py
```

This will create a `telegram_note.db` file with the necessary tables (notes, schedules, reminders).

5. Configure the bot:
```bash
cp .env.example .env
```

6. Edit `.env` and add your Telegram Bot Token:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

7. **(Optional but Recommended)** Set up ngrok for Web App support:

The bot includes a rich Web App editor for notes. To use it locally, you need to expose your local server via HTTPS:

```bash
# Install ngrok from https://ngrok.com/
# Then run:
ngrok http 8000
```

Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`) and update your `.env`:
```
WEBAPP_BASE_URL=https://abc123.ngrok-free.app
```

**Note**: Without ngrok, the bot will still work, but you'll need to use the text-based note editing instead of the rich Web App editor.

8. Run the bot:
```bash
python src/main.py
```

## Usage

### Available Commands

The bot supports command auto-completion! Simply type `/` in the Telegram chat to see all available commands with descriptions.

- `/start` or `/help` - Show help message
- `/notes [keyword/tag]` - List all notes (optionally filtered by keyword or tag)
- `/note <name>` - Open or create a note
- `/schedules [period]` - List all schedules (optionally filtered by period)
- `/schedule <name>` - Open or create a schedule

**Note**: Commands are automatically registered with Telegram when the bot starts, enabling auto-completion as you type.

### Managing Notes

#### Using the Web App Editor (Recommended)

1. Create or open a note:
```
/note my-first-note
```

2. Click the **"📝 Edit Note"** button to open the rich Web App editor

3. The editor provides:
   - **Title field**: Enter your note title
   - **Tags field**: Add comma-separated tags (e.g., `personal, ideas, work`)
   - **Content area**: Write in Markdown with live preview
   - **Preview panel**: See how your note will look
   - **Save button**: Saves the note and closes the editor
   - **Cancel button**: Closes without saving

The editor supports Markdown formatting:
- `**bold**` for **bold text**
- `*italic*` for *italic text*
- `` `code` `` for `inline code`
- `# Heading` for headings
- And more!

#### Text-Based Editing (Fallback)

If Web App is not configured, you can still edit notes via text messages:

Send a message in this format:
```
title | tags | content
```

Example:
```
My First Note | personal,ideas | This is my note content in **markdown** format!
```

### Managing Schedules

1. Create or open a schedule:
```
/schedule team-meeting
```

2. Send a message with schedule details in this format:
```
title | start_datetime | end_datetime | reminder_minutes | description
```

Example:
```
Team Sync | 2025-11-15 14:00 | 2025-11-15 15:00 | 30 | Weekly team synchronization meeting
```

The schedule will be saved with:
- Title: "Team Sync"
- Start: November 15, 2025 at 14:00
- End: November 15, 2025 at 15:00
- Reminder: 30 minutes before (13:30)
- Description: "Weekly team synchronization meeting"

### Searching Notes

Search notes by keyword or tag:
```
/notes personal
```

This will show all notes that contain "personal" in their name, title, tags, or content.

## Project Structure

```
telegram-note/
├── src/
│   ├── models/          # Database models and schema
│   │   ├── database.py  # SQLite database manager
│   │   ├── note.py      # Note data model
│   │   └── schedule.py  # Schedule data model
│   ├── modules/         # Business logic modules
│   │   ├── note_module.py      # Note CRUD operations
│   │   └── schedule_module.py  # Schedule CRUD operations
│   ├── services/        # Background services
│   │   └── reminder_service.py # Reminder scheduling with APScheduler
│   ├── utils/           # Utility functions
│   │   ├── datetime_utils.py   # DateTime parsing
│   │   └── markdown_utils.py   # Markdown utilities
│   ├── config.py        # Configuration management
│   └── main.py          # Main bot entry point
├── init_db.py           # Database initialization script
├── .env.example         # Example environment variables
├── .gitignore          # Git ignore rules
├── requirements.txt    # Python dependencies
├── CLAUDE.md          # Claude Code guidance
└── README.md          # This file
```

## Technical Details

### Database Schema

The bot uses SQLite with three main tables:

- **notes**: Stores user notes with title, tags, and markdown content
- **schedules**: Stores user schedules with datetime and reminder settings
- **reminders**: Tracks scheduled reminders and their delivery status

### Dependencies

- `python-telegram-bot` - Telegram Bot API wrapper
- `APScheduler` - Background job scheduling for reminders
- `python-dotenv` - Environment variable management
- `markdown` - Markdown parsing support

### Database Management

The database is automatically initialized when you run `python init_db.py`. To inspect or manage the database directly:

```bash
# Open database shell
sqlite3 telegram_note.db

# View all tables
.tables

# View table schema
.schema notes

# Query notes
SELECT * FROM notes;

# Exit
.quit
```

To reset the database, simply delete the file and re-run the initialization:
```bash
rm telegram_note.db
python init_db.py
```

## Production Deployment

### Deploy to AWS EC2

See our deployment guides:

- **[Quick Start Guide](QUICKSTART-EC2.md)** - Deploy in under 15 minutes
- **[Detailed Deployment Guide](DEPLOYMENT.md)** - Comprehensive EC2 deployment documentation

**Quick Deploy:**
```bash
# 1. Launch EC2 Ubuntu instance
# 2. SSH into instance
ssh -i key.pem ubuntu@YOUR_EC2_IP

# 3. Run setup script
git clone <your-repo-url> telegram-note
cd telegram-note
./scripts/ec2-setup.sh

# 4. Deploy bot
./scripts/deploy.sh
```

## Development

For development guidance and architecture details, see [CLAUDE.md](CLAUDE.md).

## License

MIT License
