# Docker Deployment Guide

This guide shows you how to deploy the Telegram Note bot using Docker on your cloud server.

## Prerequisites

- Docker installed ([Install Docker](https://docs.docker.com/engine/install/))
- Docker Compose installed ([Install Compose](https://docs.docker.com/compose/install/))
- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- Public HTTPS URL (for Web App): ngrok, CloudFlare Tunnel, or reverse proxy

## Quick Start

### 1. Clone and Configure

```bash
# Clone repository
git clone <your-repo-url>
cd telegram-note

# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings in `.env`:**
```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
WEBAPP_BASE_URL=https://your-domain.com  # Your public HTTPS URL
WEBAPP_PORT=8000
TZ=Asia/Seoul  # YOUR TIMEZONE - CRITICAL FOR REMINDERS!
```

### 2. Set Your Timezone (IMPORTANT!)

**This is critical for reminders to work correctly.**

Find your timezone from [this list](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

Common timezones:
- `Asia/Seoul` - South Korea
- `Asia/Tokyo` - Japan
- `Asia/Shanghai` - China
- `America/New_York` - US Eastern
- `America/Los_Angeles` - US Pacific
- `America/Chicago` - US Central
- `Europe/London` - United Kingdom
- `Europe/Paris` - France/Central Europe
- `Australia/Sydney` - Australia

Edit `.env`:
```bash
TZ=Asia/Seoul  # Change to your timezone
```

### 3. Initialize Database

```bash
# Create data directory
mkdir -p data

# Initialize database
docker run --rm -v $(pwd)/data:/app/data -v $(pwd)/init_db.py:/app/init_db.py python:3.11-slim python /app/init_db.py
```

Or run locally if you have Python:
```bash
python3 init_db.py
```

### 4. Build and Start

```bash
# Build Docker image
docker-compose build

# Start container
docker-compose up -d

# Check logs
docker-compose logs -f
```

### 5. Verify Everything Works

```bash
# Check container is running
docker ps | grep telegram-note

# Check timezone is correct
docker exec telegram-note-bot date
# Should show your local time, NOT UTC

# Run diagnostic
docker exec telegram-note-bot python check_reminders.py

# View logs
docker logs -f telegram-note-bot
```

## Testing Reminders

1. **Create a test reminder** (fires in 2 minutes):
   - Open bot in Telegram
   - Send: `/schedule test-reminder`
   - Title: "Test Reminder"
   - Start time: (current time + 3 minutes)
   - End time: (current time + 4 minutes)
   - Reminder: 1 minute before
   - Save

2. **Monitor logs:**
   ```bash
   docker logs -f telegram-note-bot | grep -i reminder
   ```

3. **You should see:**
   - `Scheduled reminder for schedule test-reminder at YYYY-MM-DD HH:MM`
   - (After 2 minutes) `Sent reminder for schedule test-reminder to user XXXXX`
   - You'll receive notification in Telegram

## Troubleshooting

### Reminders Not Working

**Check timezone:**
```bash
# Inside container
docker exec telegram-note-bot date
docker exec telegram-note-bot python -c "from datetime import datetime; print(datetime.now())"

# Check SQLite time
docker exec telegram-note-bot sqlite3 /app/data/telegram_note.db "SELECT datetime('now', 'localtime')"

# All should show your local time, not UTC
```

**If timezone is wrong:**
```bash
# Edit .env and set TZ=Your/Timezone
nano .env

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker exec telegram-note-bot date
```

**Run diagnostic:**
```bash
docker exec telegram-note-bot python check_reminders.py
```

### Web App Not Accessible

**Check if web server is running:**
```bash
# From host
curl http://localhost:8000/

# Check port mapping
docker ps | grep telegram-note
```

**Verify WEBAPP_BASE_URL:**
```bash
# Check environment
docker exec telegram-note-bot env | grep WEBAPP

# Should show your public HTTPS URL
```

### Container Crashes

**View logs:**
```bash
docker logs telegram-note-bot
docker logs --tail 100 telegram-note-bot
```

**Check resources:**
```bash
docker stats telegram-note-bot
```

**Access container shell:**
```bash
docker exec -it telegram-note-bot /bin/bash

# Inside container
ps aux
df -h
python src/main.py  # Run manually to see errors
```

## Maintenance

### View Logs
```bash
# Real-time logs
docker logs -f telegram-note-bot

# Last 100 lines
docker logs --tail 100 telegram-note-bot

# Reminder logs only
docker logs -f telegram-note-bot | grep -i reminder
```

### Restart Bot
```bash
docker-compose restart
```

### Update Code
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Backup
```bash
# Backup
cp data/telegram_note.db data/telegram_note.db.backup.$(date +%Y%m%d)

# Restore
cp data/telegram_note.db.backup.20250113 data/telegram_note.db
docker-compose restart
```

### Clean Database
```bash
# Access database
docker exec -it telegram-note-bot sqlite3 /app/data/telegram_note.db

# Inside sqlite3
.tables
SELECT * FROM reminders;
DELETE FROM reminders WHERE sent = TRUE AND sent_at < datetime('now', '-30 days');
.quit
```

### Clean Up Everything
```bash
# Stop and remove container
docker-compose down

# Remove images
docker rmi telegram-note_telegram-note

# Remove volumes (WARNING: Deletes database!)
docker-compose down -v
```

## Production Deployment

### Use HTTPS with Reverse Proxy

**Option 1: Nginx with Let's Encrypt**

```nginx
server {
    listen 443 ssl http2;
    server_name bot.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Option 2: Cloudflare Tunnel**

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
chmod +x /usr/local/bin/cloudflared

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create telegram-note

# Route traffic
cloudflared tunnel route dns telegram-note bot.yourdomain.com

# Run tunnel
cloudflared tunnel --url http://localhost:8000 run telegram-note
```

**Option 3: ngrok (Development/Testing)**

```bash
# Install ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Authenticate
ngrok authtoken YOUR_TOKEN

# Run tunnel
ngrok http 8000

# Copy HTTPS URL to .env
nano .env  # Set WEBAPP_BASE_URL=https://abc123.ngrok.io
docker-compose restart
```

### Automatic Restart on Failure

The `docker-compose.yml` already includes `restart: unless-stopped`.

For systemd management:

```bash
# Create systemd service
sudo tee /etc/systemd/system/telegram-note.service > /dev/null <<EOF
[Unit]
Description=Telegram Note Bot Docker
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/path/to/telegram-note
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable telegram-note
sudo systemctl start telegram-note

# Check status
sudo systemctl status telegram-note
```

### Monitoring

**Health Check:**
```bash
# Docker built-in health check
docker inspect telegram-note-bot | grep -A 5 Health

# Manual check
docker exec telegram-note-bot python -c "import os; exit(0 if os.path.exists('/app/data/telegram_note.db') else 1)"
```

**Resource Usage:**
```bash
docker stats telegram-note-bot
```

**Set up alerts:**
```bash
# Simple monitoring script
cat > /usr/local/bin/check-telegram-bot.sh <<EOF
#!/bin/bash
if ! docker ps | grep -q telegram-note-bot; then
    echo "Bot is down! Restarting..."
    cd /path/to/telegram-note
    docker-compose up -d
    # Send alert (email, Slack, etc.)
fi
EOF

chmod +x /usr/local/bin/check-telegram-bot.sh

# Add to crontab (check every 5 minutes)
crontab -e
# Add: */5 * * * * /usr/local/bin/check-telegram-bot.sh
```

## Security Best Practices

1. **Never commit `.env` file:**
   ```bash
   # Already in .gitignore, but verify
   cat .gitignore | grep .env
   ```

2. **Restrict file permissions:**
   ```bash
   chmod 600 .env
   chmod 600 data/telegram_note.db
   ```

3. **Use secrets management in production:**
   ```bash
   # Docker secrets (Docker Swarm)
   docker secret create telegram_bot_token /path/to/token.txt
   ```

4. **Update regularly:**
   ```bash
   git pull
   docker-compose build --no-cache
   docker-compose up -d
   ```

5. **Firewall rules:**
   ```bash
   # Only allow necessary ports
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 443/tcp   # HTTPS (if using reverse proxy)
   sudo ufw enable
   ```

## Scaling

If you need high availability:

```yaml
# docker-compose.yml with multiple replicas (Docker Swarm)
version: '3.8'
services:
  telegram-note:
    image: telegram-note:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
```

## Support

- Troubleshooting: See [CLOUD_TROUBLESHOOTING.md](CLOUD_TROUBLESHOOTING.md)
- Run diagnostic: `docker exec telegram-note-bot python check_reminders.py`
- Check logs: `docker logs -f telegram-note-bot`
