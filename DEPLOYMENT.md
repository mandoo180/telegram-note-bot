# Deployment Guide - AWS EC2 (Ubuntu)

This guide walks you through deploying the Telegram Note bot to an AWS EC2 instance running Ubuntu.

## Prerequisites

- AWS account
- SSH key pair for EC2 access
- Domain name (optional, but recommended for Web App HTTPS)
- Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Step 1: Launch EC2 Instance

1. **Login to AWS Console** → EC2 → Launch Instance

2. **Configure Instance:**
   - **Name**: `telegram-note-bot`
   - **AMI**: Ubuntu Server 22.04 LTS (free tier eligible)
   - **Instance Type**: `t2.micro` (1GB RAM, sufficient for this bot)
   - **Key Pair**: Create new or select existing SSH key pair
   - **Network Settings**:
     - Allow SSH (port 22) from your IP
     - Allow HTTP (port 80) from anywhere (0.0.0.0/0)
     - Allow HTTPS (port 443) from anywhere (0.0.0.0/0)
     - Allow Custom TCP (port 8000) from anywhere (for testing only)
   - **Storage**: 8GB (free tier eligible)

3. **Launch Instance** and note the public IP address

## Step 2: Connect to EC2 Instance

```bash
# SSH into your instance (replace with your key and IP)
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP

# Example:
ssh -i ~/.ssh/telegram-bot.pem ubuntu@54.123.45.67
```

## Step 3: Install Docker on EC2

```bash
# Update package list
sudo apt-get update

# Install required packages
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up the repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add current user to docker group (to run docker without sudo)
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
exit
```

**Log back in:**
```bash
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

**Verify Docker installation:**
```bash
docker --version
docker compose version
```

## Step 4: Deploy Application

### Option A: Deploy from Git (Recommended)

```bash
# Install git
sudo apt-get install -y git

# Clone your repository
git clone <your-repository-url> telegram-note
cd telegram-note

# Setup environment
cp .env.example .env
nano .env  # Edit with your bot token
```

### Option B: Deploy via SCP

**On your local machine:**
```bash
# Create a deployment package (exclude unnecessary files)
tar -czf telegram-note.tar.gz \
  --exclude='venv' \
  --exclude='*.db' \
  --exclude='data' \
  --exclude='*.log' \
  --exclude='.git' \
  --exclude='__pycache__' \
  .

# Copy to EC2
scp -i /path/to/your-key.pem telegram-note.tar.gz ubuntu@YOUR_EC2_PUBLIC_IP:~/

# SSH to EC2 and extract
ssh -i /path/to/your-key.pem ubuntu@YOUR_EC2_PUBLIC_IP
mkdir telegram-note
tar -xzf telegram-note.tar.gz -C telegram-note
cd telegram-note

# Setup environment
cp .env.example .env
nano .env  # Edit with your bot token
```

**Edit .env file:**
```bash
nano .env
```

Add your configuration:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_PATH=/app/data/telegram_note.db
WEBAPP_BASE_URL=https://your-domain.com  # See Step 5 for HTTPS setup
WEBAPP_PORT=8000
```

## Step 5: Setup HTTPS for Web App (Required for Telegram Web Apps)

Telegram Web Apps **require HTTPS**. You have two options:

### Option A: Use Nginx + Let's Encrypt (Recommended for Production)

**1. Install Nginx:**
```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

**2. Configure domain DNS:**
- Point your domain (e.g., `bot.yourdomain.com`) to your EC2 public IP

**3. Create Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/telegram-note
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name bot.yourdomain.com;  # Replace with your domain

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**4. Enable site and get SSL certificate:**
```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/telegram-note /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Get SSL certificate (follow prompts)
sudo certbot --nginx -d bot.yourdomain.com
```

**5. Update .env with HTTPS URL:**
```bash
nano .env
# Change WEBAPP_BASE_URL to: https://bot.yourdomain.com
```

### Option B: Use Cloudflare Tunnel (No domain required)

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create telegram-note

# Configure tunnel
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add configuration:
```yaml
tunnel: <tunnel-id>
credentials-file: /home/ubuntu/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: telegram-note.your-subdomain.cfargotunnel.com
    service: http://localhost:8000
  - service: http_status:404
```

**Run tunnel:**
```bash
cloudflared tunnel run telegram-note
```

## Step 6: Start the Bot

```bash
# Create data directory
mkdir -p data

# Initialize database
docker compose run --rm telegram-note python init_db.py

# Start the bot
docker compose up -d

# View logs
docker compose logs -f
```

## Step 7: Setup Auto-Start on Boot

Create a systemd service to automatically start the bot when EC2 reboots:

```bash
sudo nano /etc/systemd/system/telegram-note.service
```

Add this content:
```ini
[Unit]
Description=Telegram Note Bot
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/ubuntu/telegram-note
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=ubuntu
Group=ubuntu

[Install]
WantedBy=multi-user.target
```

**Enable and start the service:**
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable telegram-note

# Start service now
sudo systemctl start telegram-note

# Check status
sudo systemctl status telegram-note
```

## Step 8: Verify Deployment

1. **Check bot is running:**
```bash
docker compose ps
docker compose logs -f
```

2. **Test the bot:**
   - Open Telegram
   - Message your bot: `/start`
   - Try creating a note: `/note test`

3. **Check Web App:**
   - Visit your HTTPS URL in a browser
   - Should see the Web App editor

## Management Commands

```bash
# View logs
docker compose logs -f

# Restart bot
docker compose restart

# Stop bot
docker compose down

# Start bot
docker compose up -d

# Rebuild after code changes
docker compose up -d --build

# Update from git
git pull
docker compose up -d --build

# Backup database
cp data/telegram_note.db data/backup-$(date +%Y%m%d).db

# View database
docker compose exec telegram-note sqlite3 /app/data/telegram_note.db
```

## Monitoring and Maintenance

### Check Disk Space
```bash
df -h
```

### Check Memory Usage
```bash
free -h
docker stats
```

### View System Logs
```bash
# System log
sudo journalctl -u telegram-note -f

# Docker logs
docker compose logs -f --tail=100
```

### Rotate Logs
```bash
# Docker handles log rotation automatically
# To view log size:
docker compose logs --timestamps | wc -l
```

### Update Bot
```bash
# Pull latest code
git pull

# Rebuild and restart
docker compose up -d --build

# Or manually backup, pull, and restart
cp data/telegram_note.db data/backup.db
git pull
docker compose down
docker compose up -d --build
```

## Security Best Practices

1. **Firewall Rules:**
```bash
# Install UFW
sudo apt-get install -y ufw

# Allow SSH
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS (for Web App)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw --force enable

# Check status
sudo ufw status
```

2. **Secure .env file:**
```bash
chmod 600 .env
```

3. **Regular backups:**
```bash
# Setup daily backup cron job
crontab -e

# Add this line (runs daily at 2 AM)
0 2 * * * cp /home/ubuntu/telegram-note/data/telegram_note.db /home/ubuntu/telegram-note/data/backup-$(date +\%Y\%m\%d).db
```

4. **Keep system updated:**
```bash
sudo apt-get update && sudo apt-get upgrade -y
```

## Troubleshooting

### Bot not responding
```bash
# Check if container is running
docker compose ps

# Check logs
docker compose logs -f

# Restart bot
docker compose restart
```

### Database issues
```bash
# Check if database file exists
ls -lh data/telegram_note.db

# Check permissions
ls -la data/

# Reinitialize if needed
docker compose run --rm telegram-note python init_db.py
```

### Web App not loading
```bash
# Check Nginx status (if using Nginx)
sudo systemctl status nginx
sudo nginx -t

# Check SSL certificate
sudo certbot certificates

# Check bot logs
docker compose logs -f | grep -i webapp
```

### Port already in use
```bash
# Find what's using port 8000
sudo lsof -i :8000

# Kill the process (replace PID)
sudo kill -9 <PID>
```

## Cost Estimation

- **EC2 t2.micro**: ~$8.50/month (free tier: 750 hours/month for 12 months)
- **EBS Storage 8GB**: ~$0.80/month
- **Data Transfer**: Usually negligible for a bot
- **Domain (optional)**: ~$12/year
- **Total**: ~$10/month (or free for first year with free tier)

## Next Steps

1. **Monitor bot performance** using AWS CloudWatch
2. **Set up CloudWatch alarms** for high CPU/memory usage
3. **Configure automatic backups** to S3
4. **Set up CI/CD pipeline** for automated deployments
5. **Add monitoring dashboard** (Grafana + Prometheus)

## Support

If you encounter issues:
1. Check the logs: `docker compose logs -f`
2. Verify environment variables: `cat .env`
3. Check container status: `docker compose ps`
4. Review AWS security groups
5. Verify domain DNS settings (if using custom domain)
