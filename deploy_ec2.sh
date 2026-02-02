#!/bin/bash
# AI Health Navigator - Simple EC2 Deployment Script
# Run this script on your EC2 instance after SSH'ing in

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AI Health Navigator - EC2 Setup${NC}"
echo -e "${GREEN}========================================${NC}"

# Update system
echo -e "${YELLOW}Updating system packages...${NC}"
sudo yum update -y 2>/dev/null || sudo apt-get update -y

# Install Python 3.11+ if not present
echo -e "${YELLOW}Checking Python installation...${NC}"
if ! command -v python3.11 &> /dev/null && ! command -v python3.12 &> /dev/null && ! command -v python3.13 &> /dev/null; then
    echo -e "${YELLOW}Installing Python...${NC}"
    # For Amazon Linux 2023
    sudo yum install -y python3.11 python3.11-pip 2>/dev/null || \
    # For Ubuntu
    sudo apt-get install -y python3.11 python3.11-venv python3-pip 2>/dev/null || \
    echo -e "${RED}Please install Python 3.11+ manually${NC}"
fi

# Install Git if not present
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Installing Git...${NC}"
    sudo yum install -y git 2>/dev/null || sudo apt-get install -y git
fi

# Clone or update repository
APP_DIR="/home/ec2-user/AI_Health_Navigator"
if [ -d "$APP_DIR" ]; then
    echo -e "${YELLOW}Updating existing repository...${NC}"
    cd $APP_DIR
    git pull
else
    echo -e "${YELLOW}Cloning repository...${NC}"
    cd /home/ec2-user
    git clone https://github.com/YOUR_USERNAME/AI_Health_Navigator.git
    cd $APP_DIR
fi

# Create virtual environment
echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp .env.example .env
    echo -e "${RED}IMPORTANT: Edit .env file with your API keys!${NC}"
    echo -e "${RED}  nano .env${NC}"
    echo -e "${RED}Set at minimum: ANTHROPIC_API_KEY and MONGODB_URI${NC}"
fi

# Create systemd service for Streamlit
echo -e "${YELLOW}Creating systemd service...${NC}"
sudo tee /etc/systemd/system/health-navigator.service > /dev/null << EOF
[Unit]
Description=AI Health Navigator Streamlit App
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable health-navigator

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Next steps:"
echo -e "1. ${YELLOW}Edit your .env file:${NC}"
echo -e "   nano $APP_DIR/.env"
echo -e ""
echo -e "2. ${YELLOW}Add your API keys:${NC}"
echo -e "   ANTHROPIC_API_KEY=your_key_here"
echo -e "   MONGODB_URI=mongodb://localhost:27017 or your Atlas URI"
echo -e ""
echo -e "3. ${YELLOW}Start the service:${NC}"
echo -e "   sudo systemctl start health-navigator"
echo -e ""
echo -e "4. ${YELLOW}Check status:${NC}"
echo -e "   sudo systemctl status health-navigator"
echo -e ""
echo -e "5. ${YELLOW}View logs:${NC}"
echo -e "   sudo journalctl -u health-navigator -f"
echo -e ""
echo -e "6. ${YELLOW}Access the app:${NC}"
echo -e "   http://YOUR_EC2_PUBLIC_IP:8501"
echo -e ""
echo -e "${RED}Don't forget to open port 8501 in your EC2 Security Group!${NC}"
