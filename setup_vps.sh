#!/bin/bash

# Automated VPS Setup Script for Amul Telegram Bot
# Run this script on a fresh Ubuntu/Debian VPS

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   Amul Telegram Bot - VPS Setup Script              ║"
echo "║   Automated Installation                             ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo -e "${RED}Cannot detect OS${NC}"
    exit 1
fi

echo -e "${YELLOW}Detected OS: $OS $VERSION${NC}"
echo ""

# Ask for deployment method
echo "Choose deployment method:"
echo "  1) Docker (Recommended - Easy to manage)"
echo "  2) Manual (Systemd services)"
echo ""
read -p "Enter choice (1 or 2): " DEPLOY_METHOD

if [ "$DEPLOY_METHOD" != "1" ] && [ "$DEPLOY_METHOD" != "2" ]; then
    echo -e "${RED}Invalid choice${NC}"
    exit 1
fi

# Ask for bot token
echo ""
echo -e "${YELLOW}Enter your Telegram Bot Token:${NC}"
read -p "Token: " BOT_TOKEN

if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}Bot token is required${NC}"
    exit 1
fi

# Update system
echo ""
echo -e "${GREEN}[1/7] Updating system...${NC}"
apt update && apt upgrade -y

# Install common dependencies
echo ""
echo -e "${GREEN}[2/7] Installing common dependencies...${NC}"
apt install -y git curl wget nano software-properties-common

if [ "$DEPLOY_METHOD" == "1" ]; then
    # Docker installation
    echo ""
    echo -e "${GREEN}[3/7] Installing Docker...${NC}"
    
    # Remove old versions
    apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
    
    # Install Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
    
    # Install Docker Compose
    echo ""
    echo -e "${GREEN}[4/7] Installing Docker Compose...${NC}"
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    
    # Verify installation
    docker --version
    docker-compose --version
    
else
    # Manual installation
    echo ""
    echo -e "${GREEN}[3/7] Installing Python 3.11...${NC}"
    add-apt-repository -y ppa:deadsnakes/ppa
    apt update
    apt install -y python3.11 python3.11-venv python3-pip
    
    echo ""
    echo -e "${GREEN}[4/7] Installing Redis...${NC}"
    apt install -y redis-server
    systemctl enable redis-server
    systemctl start redis-server
    
    echo ""
    echo -e "${GREEN}[4.5/7] Installing Chrome/ChromeDriver...${NC}"
    apt install -y chromium-browser chromium-chromedriver
fi

# Create project directory
echo ""
echo -e "${GREEN}[5/7] Setting up project directory...${NC}"
PROJECT_DIR="/opt/amul-bot"
mkdir -p $PROJECT_DIR
cd $PROJECT_DIR

# Check if project files exist
if [ ! -f "bot.py" ]; then
    echo ""
    echo -e "${YELLOW}Project files not found in $PROJECT_DIR${NC}"
    echo "Please upload your project files to $PROJECT_DIR first"
    echo ""
    echo "You can do this by:"
    echo "  1. Using SCP: scp -r amul-bot/* root@vps-ip:/opt/amul-bot/"
    echo "  2. Using Git: git clone <repo-url> /opt/amul-bot"
    echo ""
    echo "After uploading files, run this script again."
    exit 1
fi

# Create .env file
echo ""
echo -e "${GREEN}[6/7] Creating configuration...${NC}"

cat > .env << EOF
# Telegram Configuration
TELEGRAM_BOT_TOKEN=$BOT_TOKEN

# Redis Configuration
REDIS_HOST=${DEPLOY_METHOD == "1" && echo "redis" || echo "localhost"}
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false
REDIS_KEY_PREFIX=amul:

# Default Settings
PINCODE=110001
DEFAULT_STORE=delhi

# Background Checker Settings
CHECK_INTERVAL=300
NOTIFICATION_COOLDOWN_HOURS=24

# Performance Settings
MAX_WORKERS=8
REQUEST_TIMEOUT=10

# Chrome/Selenium Settings
CHROME_BINARY=/usr/bin/chromium-browser
CHROMEDRIVER_PATH=/usr/bin/chromedriver
CHROME_NO_SANDBOX=true
CHROME_DISABLE_GPU=true

# Logging
LOG_LEVEL=INFO

# Advanced
FORCE_NOTIFY=false
EOF

echo "✓ Configuration file created"

if [ "$DEPLOY_METHOD" == "1" ]; then
    # Docker deployment
    echo ""
    echo -e "${GREEN}[7/7] Starting Docker services...${NC}"
    docker-compose down 2>/dev/null || true
    docker-compose up -d
    
    echo ""
    echo -e "${GREEN}Waiting for services to start...${NC}"
    sleep 5
    
    # Check status
    if docker-compose ps | grep -q "Up"; then
        echo ""
        echo -e "${GREEN}✓ Services started successfully!${NC}"
        echo ""
        docker-compose ps
    else
        echo -e "${RED}✗ Some services failed to start${NC}"
        docker-compose logs
        exit 1
    fi
    
else
    # Manual deployment
    echo ""
    echo -e "${GREEN}[7/7] Setting up services...${NC}"
    
    # Create virtual environment
    python3.11 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    
    # Create systemd services
    cat > /etc/systemd/system/amul-bot.service << EOF
[Unit]
Description=Amul Telegram Bot
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    cat > /etc/systemd/system/amul-checker.service << EOF
[Unit]
Description=Amul Notification Checker
After=network.target redis-server.service

[Service]
Type=simple
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/notification_checker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # Start services
    systemctl daemon-reload
    systemctl enable amul-bot amul-checker
    systemctl start amul-bot amul-checker
    
    echo ""
    echo -e "${GREEN}Waiting for services to start...${NC}"
    sleep 3
    
    # Check status
    if systemctl is-active --quiet amul-bot && systemctl is-active --quiet amul-checker; then
        echo ""
        echo -e "${GREEN}✓ Services started successfully!${NC}"
        echo ""
        systemctl status amul-bot --no-pager -l
        echo ""
        systemctl status amul-checker --no-pager -l
    else
        echo -e "${RED}✗ Some services failed to start${NC}"
        echo ""
        echo "Bot status:"
        systemctl status amul-bot --no-pager -l
        echo ""
        echo "Checker status:"
        systemctl status amul-checker --no-pager -l
        exit 1
    fi
fi

# Setup firewall (optional)
echo ""
read -p "Do you want to setup firewall (UFW)? (y/n): " SETUP_FIREWALL

if [ "$SETUP_FIREWALL" == "y" ]; then
    echo ""
    echo -e "${GREEN}Setting up firewall...${NC}"
    apt install -y ufw
    ufw --force enable
    ufw allow 22/tcp  # SSH
    ufw status
fi

# Final instructions
echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════╗"
echo "║   Installation Complete! 🎉                          ║"
echo "╚═══════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo "Your Amul Telegram Bot is now running!"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Open Telegram and search for your bot"
echo "  2. Send /start to begin"
echo "  3. Enter your pincode and select products"
echo ""

if [ "$DEPLOY_METHOD" == "1" ]; then
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  View logs:     docker-compose logs -f"
    echo "  Stop bot:      docker-compose stop"
    echo "  Start bot:     docker-compose start"
    echo "  Restart:       docker-compose restart"
    echo "  Update:        git pull && docker-compose restart"
else
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo "  View bot logs:     journalctl -u amul-bot -f"
    echo "  View checker logs: journalctl -u amul-checker -f"
    echo "  Restart bot:       systemctl restart amul-bot"
    echo "  Restart checker:   systemctl restart amul-checker"
    echo "  Stop services:     systemctl stop amul-bot amul-checker"
fi

echo ""
echo -e "${GREEN}Configuration file: $PROJECT_DIR/.env${NC}"
echo ""
echo "Happy tracking! 🥛"
echo ""
