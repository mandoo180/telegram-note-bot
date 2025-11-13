# Quick Start - Deploy to AWS EC2

A simplified guide to deploy your Telegram Note bot to AWS EC2 in under 15 minutes.

## Prerequisites

✅ AWS account
✅ SSH key pair downloaded
✅ Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Step-by-Step Deployment

### 1️⃣ Launch EC2 Instance (5 minutes)

1. Go to **AWS Console** → **EC2** → **Launch Instance**
2. Configure:
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Type**: t2.micro (free tier)
   - **Key pair**: Select or create new
   - **Security Group**: Allow ports 22, 80, 443
3. Click **Launch Instance**
4. Note your **Public IP address**

### 2️⃣ Setup EC2 (5 minutes)

SSH into your instance:
```bash
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

Run the setup script:
```bash
# Download and run setup script
wget https://raw.githubusercontent.com/YOUR_REPO/main/scripts/ec2-setup.sh
chmod +x ec2-setup.sh
./ec2-setup.sh
```

Or manually:
```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install git
sudo apt-get install -y git

# Log out and back in
exit
ssh -i your-key.pem ubuntu@YOUR_EC2_IP
```

### 3️⃣ Deploy Bot (5 minutes)

Clone your repository:
```bash
git clone <your-repo-url> telegram-note
cd telegram-note
```

Configure environment:
```bash
cp .env.example .env
nano .env
```

Add your bot token:
```env
TELEGRAM_BOT_TOKEN=your_token_here
DATABASE_PATH=/app/data/telegram_note.db
WEBAPP_BASE_URL=http://YOUR_EC2_IP:8000
WEBAPP_PORT=8000
```

Deploy:
```bash
./scripts/deploy.sh
```

Or manually:
```bash
# Create data directory
mkdir -p data

# Initialize database
docker compose run --rm telegram-note python init_db.py

# Start bot
docker compose up -d

# View logs
docker compose logs -f
```

### 4️⃣ Test Your Bot

1. Open Telegram
2. Message your bot: `/start`
3. Try creating a note: `/note test`

**✅ Your bot is now live!**

## Optional: Setup HTTPS (For Web App Editor)

Telegram Web Apps require HTTPS. You have two options:

### Option A: Nginx + Let's Encrypt (Requires domain)

```bash
# Install Nginx
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Configure Nginx (replace YOUR_DOMAIN)
sudo nano /etc/nginx/sites-available/telegram-note
```

Add:
```nginx
server {
    listen 80;
    server_name bot.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable and get SSL:
```bash
sudo ln -s /etc/nginx/sites-available/telegram-note /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d bot.yourdomain.com
```

Update `.env`:
```env
WEBAPP_BASE_URL=https://bot.yourdomain.com
```

Restart bot:
```bash
docker compose restart
```

### Option B: Cloudflare Tunnel (No domain needed)

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Setup tunnel
cloudflared tunnel login
cloudflared tunnel create telegram-note
cloudflared tunnel route dns telegram-note bot

# Run tunnel
cloudflared tunnel run telegram-note
```

## Common Commands

```bash
# View logs
docker compose logs -f

# Restart bot
docker compose restart

# Stop bot
docker compose down

# Start bot
docker compose up -d

# Update bot
./scripts/update.sh

# Backup database
./scripts/backup.sh

# Check status
docker compose ps
```

## Auto-Start on Boot

Make bot start automatically when EC2 reboots:

```bash
# Run during deployment
./scripts/deploy.sh
# (Answer 'y' when asked about systemd)

# Or manually
sudo tee /etc/systemd/system/telegram-note.service > /dev/null <<EOF
[Unit]
Description=Telegram Note Bot
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=$USER
Group=$USER

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable telegram-note
sudo systemctl start telegram-note
```

## Troubleshooting

### Bot not starting?
```bash
# Check logs
docker compose logs -f

# Check if port is free
sudo lsof -i :8000

# Restart
docker compose restart
```

### Database issues?
```bash
# Check database file
ls -lh data/telegram_note.db

# Reinitialize
docker compose run --rm telegram-note python init_db.py
```

### Out of memory?
```bash
# Check memory
free -h

# Check container stats
docker stats
```

## Security Checklist

- [ ] Changed SSH port from default 22 (optional but recommended)
- [ ] Configured UFW firewall
- [ ] Using HTTPS for Web App
- [ ] `.env` file has restricted permissions (600)
- [ ] Regular database backups configured
- [ ] System updates automated

## Costs

- **EC2 t2.micro**: ~$8.50/month (Free tier: first 12 months)
- **Storage**: ~$0.80/month
- **Data transfer**: Usually < $1/month
- **Total**: ~$10/month (or FREE for first year)

## Next Steps

1. ✅ Bot is running
2. 🔒 Setup HTTPS for Web App editor
3. 💾 Configure automatic backups
4. 📊 Setup monitoring (CloudWatch)
5. 🔄 Configure CI/CD for automatic updates

## Support

For detailed documentation, see [DEPLOYMENT.md](DEPLOYMENT.md)

**Need help?**
- Check logs: `docker compose logs -f`
- Verify config: `cat .env`
- Check status: `docker compose ps`
