#!/bin/bash
# Backup script for Telegram Note Bot database

set -e

echo "💾 Database Backup"
echo "=================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if data directory exists
if [ ! -d data ]; then
    echo -e "${RED}❌ data/ directory not found${NC}"
    exit 1
fi

# Check if database exists
if [ ! -f data/telegram_note.db ]; then
    echo -e "${RED}❌ Database file not found at data/telegram_note.db${NC}"
    exit 1
fi

# Create backups directory
mkdir -p data/backups

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="data/backups/telegram_note_${TIMESTAMP}.db"

# Create backup
echo -e "${YELLOW}📦 Creating backup...${NC}"
cp data/telegram_note.db "$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✅ Backup created successfully${NC}"
    echo "   File: $BACKUP_FILE"
    echo "   Size: $BACKUP_SIZE"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Show existing backups
echo ""
echo "📚 Existing backups:"
ls -lh data/backups/

# Calculate total backup size
TOTAL_SIZE=$(du -sh data/backups/ | cut -f1)
echo ""
echo "Total backup size: $TOTAL_SIZE"

# Offer to clean old backups
echo ""
BACKUP_COUNT=$(ls data/backups/ | wc -l)
if [ "$BACKUP_COUNT" -gt 7 ]; then
    echo -e "${YELLOW}⚠️  You have $BACKUP_COUNT backups${NC}"
    read -p "Do you want to keep only the 7 most recent backups? (y/n): " cleanup
    if [[ $cleanup == "y" || $cleanup == "Y" ]]; then
        echo -e "${YELLOW}🧹 Cleaning old backups...${NC}"
        cd data/backups
        ls -t | tail -n +8 | xargs rm -f
        cd ../..
        echo -e "${GREEN}✅ Old backups removed${NC}"
        echo ""
        echo "📚 Remaining backups:"
        ls -lh data/backups/
    fi
fi

echo ""
echo -e "${GREEN}✅ Backup complete!${NC}"
