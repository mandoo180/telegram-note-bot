# Troubleshooting Guide

Common issues and their solutions for the Telegram Note Bot.

## Docker Permission Denied

### Problem
```bash
./scripts/deploy.sh
# Error: Got permission denied while trying to connect to the Docker daemon socket
```

### Cause
Your user is not in the `docker` group yet. This happens after Docker installation but before logging out/in.

### Solution

**Option 1: Quick Fix (No logout required)**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Activate the group changes
newgrp docker

# Verify it works
docker ps

# Now run deploy script
./scripts/deploy.sh
```

**Option 2: Log out and back in (Permanent)**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Log out
exit

# Log back in
ssh -i your-key.pem ubuntu@YOUR_EC2_IP

# Verify it works
docker ps

# Now run deploy script
./scripts/deploy.sh
```

**Option 3: Use sudo (Not recommended)**
```bash
# Run docker commands with sudo
sudo docker compose up -d

# But for the script, fix permissions properly using Option 1 or 2
```

---

## Bot Not Responding

### Problem
Bot doesn't respond to `/start` or other commands in Telegram.

### Diagnosis
```bash
# Check if container is running
docker compose ps

# Check logs
docker compose logs -f

# Check if bot token is correct
cat .env | grep TELEGRAM_BOT_TOKEN
```

### Solutions

**1. Container not running:**
```bash
docker compose up -d
docker compose logs -f
```

**2. Wrong bot token:**
```bash
# Edit .env with correct token
nano .env

# Restart bot
docker compose restart
```

**3. Network issues:**
```bash
# Check if bot can reach Telegram
docker compose exec telegram-note ping -c 3 api.telegram.org

# Check security group allows outbound traffic
```

---

## Database Issues

### Problem: Database file not found

```bash
# Error: no such file: /app/data/telegram_note.db
```

### Solution
```bash
# Initialize database
docker compose run --rm telegram-note python init_db.py

# Verify database exists
ls -lh data/telegram_note.db

# Restart bot
docker compose up -d
```

### Problem: Database corrupted

```bash
# Error: database disk image is malformed
```

### Solution
```bash
# Stop bot
docker compose down

# Backup corrupted database
cp data/telegram_note.db data/telegram_note.db.corrupted

# Try to dump and restore
sqlite3 data/telegram_note.db.corrupted ".dump" | sqlite3 data/telegram_note.db.recovered

# If successful, replace
mv data/telegram_note.db.recovered data/telegram_note.db

# If not successful, restore from backup
cp data/backups/telegram_note_LATEST.db data/telegram_note.db

# Or reinitialize (LOSES ALL DATA)
rm data/telegram_note.db
docker compose run --rm telegram-note python init_db.py

# Start bot
docker compose up -d
```

---

## Web App Not Loading

### Problem
Clicking "Edit Note" or "Edit Schedule" button shows error or blank page.

### Cause
Telegram Web Apps require HTTPS URLs.

### Solution

**1. Check WEBAPP_BASE_URL in .env:**
```bash
cat .env | grep WEBAPP_BASE_URL

# Should be HTTPS (not HTTP):
# ✅ WEBAPP_BASE_URL=https://bot.yourdomain.com
# ❌ WEBAPP_BASE_URL=http://bot.yourdomain.com
```

**2. Setup HTTPS using Nginx + Let's Encrypt:**
```bash
# Install Nginx and Certbot
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx (see DEPLOYMENT.md)
sudo nano /etc/nginx/sites-available/telegram-note

# Get SSL certificate
sudo certbot --nginx -d bot.yourdomain.com

# Update .env
nano .env
# Change to: WEBAPP_BASE_URL=https://bot.yourdomain.com

# Restart bot
docker compose restart
```

**3. Or use Cloudflare Tunnel (no domain needed):**
```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Setup tunnel (follow prompts)
cloudflared tunnel login
cloudflared tunnel create telegram-note

# Update .env with tunnel URL
nano .env

# Restart bot
docker compose restart
```

---

## Port Already in Use

### Problem
```bash
# Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

### Solution

**Find what's using port 8000:**
```bash
sudo lsof -i :8000
# or
sudo netstat -tulpn | grep :8000
```

**Kill the process:**
```bash
# If you see PID (e.g., 1234)
sudo kill -9 1234

# Or stop conflicting service
sudo systemctl stop other-service
```

**Or use a different port:**
```bash
# Edit .env
nano .env
# Change: WEBAPP_PORT=8001

# Update docker-compose.yml if needed
nano docker-compose.yml

# Restart
docker compose down
docker compose up -d
```

---

## Container Keeps Restarting

### Problem
```bash
docker compose ps
# Status: Restarting
```

### Diagnosis
```bash
# Check logs
docker compose logs -f

# Check container events
docker compose events
```

### Common Causes & Solutions

**1. Invalid bot token:**
```bash
# Fix token in .env
nano .env

# Restart
docker compose restart
```

**2. Database initialization failed:**
```bash
docker compose run --rm telegram-note python init_db.py
docker compose up -d
```

**3. Out of memory:**
```bash
# Check memory
free -h
docker stats

# If out of memory, upgrade EC2 instance or add swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**4. Python dependencies missing:**
```bash
# Rebuild image
docker compose build --no-cache
docker compose up -d
```

---

## SSL Certificate Issues

### Problem: Let's Encrypt certificate failed

```bash
# Error: Unable to get certificate
```

### Solutions

**1. Check DNS is pointing to EC2:**
```bash
# Check DNS resolution
nslookup bot.yourdomain.com

# Should return your EC2 IP
```

**2. Check port 80 is accessible:**
```bash
# Test from outside
curl http://bot.yourdomain.com

# Check firewall
sudo ufw status
```

**3. Wait for DNS propagation:**
```bash
# DNS can take up to 48 hours
# Check status:
host bot.yourdomain.com
```

**4. Use DNS challenge instead of HTTP:**
```bash
sudo certbot certonly --manual --preferred-challenges dns -d bot.yourdomain.com
```

---

## Reminders Not Working

### Problem
Scheduled reminders are not sent at the specified time.

### Diagnosis
```bash
# Check logs for reminder service
docker compose logs -f | grep -i reminder

# Check if APScheduler is running
docker compose exec telegram-note ps aux | grep apscheduler
```

### Solutions

**1. Check reminder was scheduled:**
```bash
# View database
docker compose exec telegram-note sqlite3 /app/data/telegram_note.db

# Query reminders
sqlite> SELECT * FROM reminders;
sqlite> .quit
```

**2. Check system time:**
```bash
# Check EC2 time
date

# Check timezone
timedatectl

# Set timezone if needed
sudo timedatectl set-timezone America/New_York
```

**3. Restart bot:**
```bash
docker compose restart
```

---

## Deployment Script Fails

### Problem
`./scripts/deploy.sh` or other scripts fail with various errors.

### Solutions

**1. Script not executable:**
```bash
chmod +x scripts/*.sh
./scripts/deploy.sh
```

**2. Git repository not cloned properly:**
```bash
# Ensure you're in the right directory
pwd
ls -la

# Should see: Dockerfile, docker-compose.yml, src/, etc.
```

**3. Environment file missing:**
```bash
# Create from template
cp .env.example .env

# Edit with your values
nano .env
```

**4. Docker not installed:**
```bash
# Run setup script first
./scripts/ec2-setup.sh

# Then deploy
./scripts/deploy.sh
```

---

## Out of Disk Space

### Problem
```bash
# Error: no space left on device
```

### Diagnosis
```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df
```

### Solutions

**1. Clean Docker resources:**
```bash
# Remove unused containers, images, networks
docker system prune -a

# Remove unused volumes (CAREFUL - don't remove database!)
docker volume ls
docker volume rm VOLUME_NAME
```

**2. Clean old backups:**
```bash
# Check backup size
du -sh data/backups/

# Keep only recent backups
cd data/backups/
ls -t | tail -n +8 | xargs rm -f
```

**3. Clean system logs:**
```bash
# Clean journal logs
sudo journalctl --vacuum-time=7d

# Clean apt cache
sudo apt-get clean
```

**4. Expand EBS volume:**
```bash
# In AWS Console: EC2 → Volumes → Modify Volume
# Then resize filesystem:
sudo growpart /dev/xvda 1
sudo resize2fs /dev/xvda1
```

---

## Can't SSH to EC2

### Problem
```bash
ssh -i key.pem ubuntu@EC2_IP
# Connection refused or timeout
```

### Solutions

**1. Check security group:**
- AWS Console → EC2 → Security Groups
- Ensure port 22 is allowed from your IP

**2. Check instance is running:**
- AWS Console → EC2 → Instances
- Status should be "Running"

**3. Check key permissions:**
```bash
# Key must have restricted permissions
chmod 400 your-key.pem
```

**4. Try instance connect:**
- AWS Console → EC2 → Instance → Connect
- Use "EC2 Instance Connect" option

---

## Need Help?

If your issue isn't listed here:

1. **Check logs:**
   ```bash
   docker compose logs -f
   ```

2. **Check container status:**
   ```bash
   docker compose ps
   docker stats
   ```

3. **Check system resources:**
   ```bash
   free -h
   df -h
   top
   ```

4. **Restart everything:**
   ```bash
   docker compose down
   docker compose up -d
   docker compose logs -f
   ```

5. **Check documentation:**
   - [README.md](README.md)
   - [DEPLOYMENT.md](DEPLOYMENT.md)
   - [QUICKSTART-EC2.md](QUICKSTART-EC2.md)
