#!/bin/bash
# Update script for Telegram Note Bot
# Pulls latest code and rebuilds the container

set -e

echo "🔄 Telegram Note Bot - Update"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if git repository
if [ ! -d .git ]; then
    echo -e "${RED}❌ Not a git repository${NC}"
    echo "This script is for updating from git. For manual updates, use:"
    echo "  docker compose down"
    echo "  docker compose up -d --build"
    exit 1
fi

# Backup database first
echo -e "${YELLOW}💾 Creating database backup...${NC}"
if [ -f scripts/backup.sh ]; then
    ./scripts/backup.sh
else
    # Inline backup
    mkdir -p data/backups
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    cp data/telegram_note.db "data/backups/telegram_note_${TIMESTAMP}.db"
    echo -e "${GREEN}✅ Backup created${NC}"
fi

echo ""
echo -e "${YELLOW}📥 Pulling latest changes from git...${NC}"

# Stash local changes if any
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}⚠️  Local changes detected, stashing...${NC}"
    git stash
    STASHED=true
else
    STASHED=false
fi

# Pull latest changes
git pull

if [ "$STASHED" = true ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Your local changes were stashed${NC}"
    echo "   To restore them: git stash pop"
fi

echo -e "${GREEN}✅ Code updated${NC}"

# Stop bot
echo ""
echo -e "${YELLOW}🛑 Stopping bot...${NC}"
docker compose down

# Rebuild
echo ""
echo -e "${YELLOW}🔨 Rebuilding Docker image...${NC}"
docker compose build --no-cache

# Start bot
echo ""
echo -e "${YELLOW}🚀 Starting bot...${NC}"
docker compose up -d

# Wait for container to start
sleep 3

# Check status
echo ""
echo -e "${YELLOW}📊 Checking status...${NC}"
docker compose ps

# Show recent logs
echo ""
echo -e "${YELLOW}📜 Recent logs:${NC}"
docker compose logs --tail=30

echo ""
echo -e "${GREEN}✅ Update complete!${NC}"
echo ""
echo "📋 Commands:"
echo "   View logs:   docker compose logs -f"
echo "   Restart:     docker compose restart"
echo "   Status:      docker compose ps"
echo ""
