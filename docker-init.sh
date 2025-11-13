#!/bin/bash
# Docker initialization script for Telegram Note bot

set -e

echo "🤖 Telegram Note Bot - Docker Setup"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add your TELEGRAM_BOT_TOKEN"
    echo "   You can get a token from @BotFather on Telegram"
    echo ""
    read -p "Press Enter after you've updated .env with your bot token..."
else
    echo "✅ .env file already exists"
fi

# Create data directory
if [ ! -d data ]; then
    echo ""
    echo "📁 Creating data directory for database..."
    mkdir -p data
    echo "✅ data/ directory created"
fi

# Check if database exists
if [ ! -f data/telegram_note.db ]; then
    echo ""
    echo "🗄️  Initializing database..."
    docker-compose run --rm telegram-note python init_db.py
    echo "✅ Database initialized"
else
    echo ""
    echo "✅ Database already exists at data/telegram_note.db"
fi

echo ""
echo "🚀 Starting the bot..."
docker-compose up -d

echo ""
echo "✅ Bot is now running!"
echo ""
echo "📊 Useful commands:"
echo "   View logs:        docker-compose logs -f"
echo "   Stop bot:         docker-compose down"
echo "   Restart bot:      docker-compose restart"
echo "   Rebuild bot:      docker-compose up -d --build"
echo ""
echo "💾 Database location: ./data/telegram_note.db"
echo ""
