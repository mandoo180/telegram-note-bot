#!/bin/bash
# EC2 Ubuntu Setup Script for Telegram Note Bot
# Run this script on your EC2 instance after SSH'ing in

set -e

echo "🚀 Telegram Note Bot - EC2 Setup"
echo "================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Update system
echo -e "${YELLOW}📦 Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
echo ""
echo -e "${YELLOW}🐳 Installing Docker...${NC}"
if command -v docker &> /dev/null; then
    echo -e "${GREEN}✅ Docker already installed${NC}"
else
    # Install prerequisites
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker $USER

    echo -e "${GREEN}✅ Docker installed successfully${NC}"
    echo -e "${YELLOW}⚠️  You need to log out and back in for group changes to take effect${NC}"
fi

# Install git
echo ""
echo -e "${YELLOW}📚 Installing git...${NC}"
if command -v git &> /dev/null; then
    echo -e "${GREEN}✅ Git already installed${NC}"
else
    sudo apt-get install -y git
    echo -e "${GREEN}✅ Git installed${NC}"
fi

# Install Nginx (optional, for HTTPS)
echo ""
read -p "Do you want to install Nginx for HTTPS support? (y/n): " install_nginx
if [[ $install_nginx == "y" || $install_nginx == "Y" ]]; then
    echo -e "${YELLOW}🌐 Installing Nginx and Certbot...${NC}"
    sudo apt-get install -y nginx certbot python3-certbot-nginx
    echo -e "${GREEN}✅ Nginx and Certbot installed${NC}"

    # Create Nginx config template
    echo ""
    echo -e "${YELLOW}📝 Creating Nginx configuration template...${NC}"
    sudo tee /etc/nginx/sites-available/telegram-note > /dev/null <<EOF
server {
    listen 80;
    server_name YOUR_DOMAIN_HERE;  # Replace with your domain

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_cache_bypass \$http_upgrade;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    echo -e "${GREEN}✅ Nginx config created at /etc/nginx/sites-available/telegram-note${NC}"
    echo -e "${YELLOW}⚠️  Remember to:${NC}"
    echo "   1. Edit the config and replace YOUR_DOMAIN_HERE with your actual domain"
    echo "   2. Point your domain DNS to this server's IP"
    echo "   3. Enable the site: sudo ln -s /etc/nginx/sites-available/telegram-note /etc/nginx/sites-enabled/"
    echo "   4. Test config: sudo nginx -t"
    echo "   5. Reload Nginx: sudo systemctl reload nginx"
    echo "   6. Get SSL cert: sudo certbot --nginx -d your-domain.com"
fi

# Setup firewall
echo ""
read -p "Do you want to setup UFW firewall? (y/n): " setup_firewall
if [[ $setup_firewall == "y" || $setup_firewall == "Y" ]]; then
    echo -e "${YELLOW}🔥 Setting up firewall...${NC}"
    sudo apt-get install -y ufw

    # Allow SSH first (important!)
    sudo ufw allow 22/tcp
    echo -e "${GREEN}✅ Allowed SSH (port 22)${NC}"

    # Allow HTTP/HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp
    echo -e "${GREEN}✅ Allowed HTTP/HTTPS (ports 80, 443)${NC}"

    # Enable firewall
    sudo ufw --force enable
    echo -e "${GREEN}✅ Firewall enabled${NC}"

    # Show status
    sudo ufw status
fi

echo ""
echo -e "${GREEN}✅ EC2 setup complete!${NC}"
echo ""
echo "📋 Next steps:"
echo "   1. Log out and back in (if Docker was just installed)"
echo "   2. Clone your repository: git clone <repo-url>"
echo "   3. cd into project directory"
echo "   4. Run: ./scripts/deploy.sh"
echo ""
