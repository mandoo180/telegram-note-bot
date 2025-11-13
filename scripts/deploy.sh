#!/bin/bash
# Deployment script for Telegram Note Bot on EC2
# Run this script in your project directory on the EC2 instance

set -e

echo "🚀 Telegram Note Bot - Deployment"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Please run: ./scripts/ec2-setup.sh first"
    exit 1
fi

# Check if user has docker permissions
if ! docker ps &> /dev/null; then
    echo -e "${RED}❌ Docker permission denied${NC}"
    echo ""
    echo "Your user needs to be in the 'docker' group."
    echo ""
    echo "Quick fix (run these commands):"
    echo "  sudo usermod -aG docker \$USER"
    echo "  newgrp docker"
    echo ""
    echo "Or log out and back in for group changes to take effect:"
    echo "  exit"
    echo "  ssh -i your-key.pem ubuntu@YOUR_EC2_IP"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if docker compose is available
if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Please run: ./scripts/ec2-setup.sh first"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed and accessible${NC}"
echo ""

# Setup environment file
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ .env file created${NC}"
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Please edit .env and configure:${NC}"
    echo "   - TELEGRAM_BOT_TOKEN (required)"
    echo "   - WEBAPP_BASE_URL (your HTTPS URL)"
    echo ""
    read -p "Press Enter after you've configured .env..."
else
    echo -e "${GREEN}✅ .env file exists${NC}"
fi

# Validate environment
echo ""
echo -e "${YELLOW}🔍 Validating configuration...${NC}"
source .env

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ "$TELEGRAM_BOT_TOKEN" == "your_bot_token_here" ]; then
    echo -e "${RED}❌ TELEGRAM_BOT_TOKEN not configured in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Configuration valid${NC}"

# Create data directory
echo ""
echo -e "${YELLOW}📁 Creating data directory...${NC}"
mkdir -p data
chmod 755 data
echo -e "${GREEN}✅ data/ directory ready${NC}"

# Initialize database if needed
if [ ! -f data/telegram_note.db ]; then
    echo ""
    echo -e "${YELLOW}🗄️  Initializing database...${NC}"
    docker compose run --rm telegram-note python init_db.py
    echo -e "${GREEN}✅ Database initialized${NC}"
else
    echo ""
    echo -e "${GREEN}✅ Database already exists${NC}"
fi

# Stop existing container if running
echo ""
echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker compose down 2>/dev/null || true

# Build and start
echo ""
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker compose build

echo ""
echo -e "${YELLOW}🚀 Starting bot...${NC}"
docker compose up -d

# Wait for container to start
sleep 3

# Check status
echo ""
echo -e "${YELLOW}📊 Checking container status...${NC}"
docker compose ps

# Show logs
echo ""
echo -e "${YELLOW}📜 Recent logs:${NC}"
docker compose logs --tail=20

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "📋 Management commands:"
echo "   View logs:        docker compose logs -f"
echo "   Stop bot:         docker compose down"
echo "   Restart bot:      docker compose restart"
echo "   View status:      docker compose ps"
echo "   Update & rebuild: git pull && docker compose up -d --build"
echo ""
echo "🔗 Test your bot:"
echo "   Open Telegram and message your bot: /start"
echo ""

# Offer to setup systemd service
echo ""
read -p "Do you want to setup auto-start on boot (systemd service)? (y/n): " setup_systemd
if [[ $setup_systemd == "y" || $setup_systemd == "Y" ]]; then
    echo ""
    echo -e "${YELLOW}⚙️  Setting up systemd service...${NC}"

    CURRENT_DIR=$(pwd)
    CURRENT_USER=$(whoami)

    sudo tee /etc/systemd/system/telegram-note.service > /dev/null <<EOF
[Unit]
Description=Telegram Note Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$CURRENT_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$CURRENT_USER
Group=$CURRENT_USER

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable telegram-note
    sudo systemctl start telegram-note

    echo -e "${GREEN}✅ Systemd service configured${NC}"
    echo "   Service will start automatically on boot"
    echo ""
    echo "   Service commands:"
    echo "     Status:  sudo systemctl status telegram-note"
    echo "     Start:   sudo systemctl start telegram-note"
    echo "     Stop:    sudo systemctl stop telegram-note"
    echo "     Restart: sudo systemctl restart telegram-note"
fi

echo ""
echo -e "${GREEN}🎉 All done!${NC}"
