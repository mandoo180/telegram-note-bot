# Quick Server Setup

This is what you want - a clean setup with scripts in one place and data in another.

## Directory Structure

```
~/
├── scripts/
│   └── telegram-note-bot/        ← Scripts and config here
│       ├── deploy.sh
│       └── .env
│
└── data/
    └── telegram-note-bot/         ← Database here
        └── telegram_note.db       (created automatically)
```

## Setup Commands

Copy and paste these commands on your server:

```bash
# 1. Create directories
mkdir -p ~/scripts/telegram-note-bot
mkdir -p ~/data/telegram-note-bot

# 2. Download deployment script
cd ~/scripts/telegram-note-bot
curl -o deploy.sh https://raw.githubusercontent.com/mandoo180/telegram-note-bot/main/deploy.sh
chmod +x deploy.sh

# 3. Create .env file
cat > .env <<'EOF'
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Database Configuration (inside container - don't change)
DATABASE_PATH=/app/data/telegram_note.db

# Data Directory (on host machine - THIS IS IMPORTANT!)
DATA_DIR=~/data/telegram-note-bot

# Web App Configuration
WEBAPP_BASE_URL=http://YOUR_SERVER_IP:8000
WEBAPP_PORT=8000

# Timezone Configuration
TZ=Asia/Seoul
EOF

# 4. Edit .env with your actual values
nano .env
# Change:
# - TELEGRAM_BOT_TOKEN to your actual token from @BotFather
# - YOUR_SERVER_IP to your actual server IP
# - TZ to your timezone

# 5. Check configuration
./deploy.sh --config

# 6. Deploy!
./deploy.sh
```

## What Gets Created

After running `./deploy.sh`, you'll have:

```
~/scripts/telegram-note-bot/
├── deploy.sh                    ← Deployment script
└── .env                         ← Your configuration

~/data/telegram-note-bot/
└── telegram_note.db             ← Your database (created automatically)
```

## Key Points

1. **`.env` file location**: `~/scripts/telegram-note-bot/.env`
2. **Database location**: `~/data/telegram-note-bot/telegram_note.db`
3. **DATA_DIR in .env**: Must be set to `~/data/telegram-note-bot`

The script reads `DATA_DIR` from your `.env` file and creates the database there, not in the current directory!

## Common Commands

```bash
# Always run from the scripts directory
cd ~/scripts/telegram-note-bot

# Deploy/Update bot
./deploy.sh

# View logs
./deploy.sh --logs

# Check status
./deploy.sh --status

# Show configuration
./deploy.sh --config

# Backup database
cp ~/data/telegram-note-bot/telegram_note.db \
   ~/data/telegram-note-bot/backup-$(date +%Y%m%d).db
```

## Verify Setup

After deployment:

1. Check files:
```bash
ls -la ~/scripts/telegram-note-bot/
ls -la ~/data/telegram-note-bot/
```

2. Check container:
```bash
docker ps | grep telegram-note
```

3. In Telegram, send `/version` to your bot

## Troubleshooting

**Database created in wrong location?**

Check your `.env` file:
```bash
cd ~/scripts/telegram-note-bot
cat .env | grep DATA_DIR
```

It should show: `DATA_DIR=~/data/telegram-note-bot`

If it's missing or wrong:
```bash
nano .env
# Add or fix: DATA_DIR=~/data/telegram-note-bot
./deploy.sh  # Redeploy
```

For more details, see: `docs/server-setup.org`
