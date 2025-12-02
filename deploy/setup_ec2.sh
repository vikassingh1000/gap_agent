#!/bin/bash
# =============================================================================
# EC2 Deployment Script for Gap Assessment Application
# Run this script on a fresh Ubuntu 22.04 EC2 instance
# Recommended: t3.medium (2 vCPU, 4GB RAM)
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Gap Assessment - EC2 Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"

# =============================================================================
# CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
APP_DIR="/opt/gap-assessment"
REPO_URL="https://github.com/YOUR_USERNAME/Gap_Assesment.git"  # UPDATE THIS
DOMAIN_OR_IP=""  # Leave empty to use EC2 public IP, or set your domain

# API Keys - UPDATE THESE or use environment variables
GEMINI_API_KEY="${GEMINI_API_KEY:-your_gemini_api_key_here}"
PINECONE_API_KEY="${PINECONE_API_KEY:-your_pinecone_api_key_here}"
BROWSER_USE_API_KEY="${BROWSER_USE_API_KEY:-your_browser_use_api_key_here}"

# =============================================================================
# STEP 1: System Update & Dependencies
# =============================================================================
echo -e "\n${YELLOW}[1/8] Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "\n${YELLOW}[2/8] Installing required packages...${NC}"
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    nodejs \
    npm \
    nginx \
    git \
    curl \
    build-essential \
    libffi-dev \
    libssl-dev

# Install Node.js 18+ (LTS)
echo -e "\n${YELLOW}Installing Node.js 18 LTS...${NC}"
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# =============================================================================
# STEP 2: Clone Repository
# =============================================================================
echo -e "\n${YELLOW}[3/8] Setting up application directory...${NC}"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# If repo URL is set, clone it
if [ "$REPO_URL" != "https://github.com/YOUR_USERNAME/Gap_Assesment.git" ]; then
    echo "Cloning repository..."
    git clone $REPO_URL $APP_DIR
else
    echo -e "${RED}NOTE: Update REPO_URL in this script or manually copy files to $APP_DIR${NC}"
    echo "For now, creating directory structure..."
    mkdir -p $APP_DIR
fi

cd $APP_DIR

# =============================================================================
# STEP 3: Python Environment Setup
# =============================================================================
echo -e "\n${YELLOW}[4/8] Setting up Python virtual environment...${NC}"
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip wheel setuptools

# Install Python dependencies
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "${RED}requirements.txt not found. Please copy your project files to $APP_DIR${NC}"
fi

# Install Playwright browsers (for web scraping)
echo "Installing Playwright browsers..."
playwright install chromium
playwright install-deps chromium

# =============================================================================
# STEP 4: Frontend Build
# =============================================================================
echo -e "\n${YELLOW}[5/8] Building frontend...${NC}"
if [ -d "frontend" ]; then
    cd frontend
    npm install
    npm run build
    cd ..
else
    echo -e "${RED}frontend directory not found. Skipping frontend build.${NC}"
fi

# =============================================================================
# STEP 5: Configuration Files
# =============================================================================
echo -e "\n${YELLOW}[6/8] Creating configuration files...${NC}"

# Create config directory if it doesn't exist
mkdir -p config

# Create agent config
cat > config/agent_config.json << 'EOF'
{
    "gemini_model": "gemini-2.0-flash-exp",
    "embedding_model": "all-mpnet-base-v2",
    "max_search_results": 10,
    "temperature": 0.3,
    "extraction_interval_hours": 24
}
EOF

# Create environment file for API keys
cat > .env << EOF
GEMINI_API_KEY=${GEMINI_API_KEY}
PINECONE_API_KEY=${PINECONE_API_KEY}
BROWSER_USE_API_KEY=${BROWSER_USE_API_KEY}
EOF

chmod 600 .env

# =============================================================================
# STEP 6: Systemd Service for FastAPI
# =============================================================================
echo -e "\n${YELLOW}[7/8] Creating systemd service...${NC}"

sudo tee /etc/systemd/system/gap-assessment.service > /dev/null << EOF
[Unit]
Description=Gap Assessment FastAPI Application
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/uvicorn api.gap_assessment_api:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=gap-assessment

# Security hardening
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable gap-assessment
sudo systemctl start gap-assessment

# =============================================================================
# STEP 7: Nginx Configuration
# =============================================================================
echo -e "\n${YELLOW}[8/8] Configuring Nginx...${NC}"

# Get EC2 public IP if domain not set
if [ -z "$DOMAIN_OR_IP" ]; then
    DOMAIN_OR_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "localhost")
fi

sudo tee /etc/nginx/sites-available/gap-assessment > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_OR_IP;

    # Frontend - React static files
    location / {
        root $APP_DIR/frontend/dist;
        index index.html;
        try_files \$uri \$uri/ /index.html;
    }

    # API proxy
    location /api/ {
        rewrite ^/api/(.*) /\$1 break;
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;

        # Increase timeout for long-running LLM requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Direct API access (without /api prefix)
    location ~ ^/(health|assess|status|logs)(.*)$ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
EOF

# Enable site and remove default
sudo ln -sf /etc/nginx/sites-available/gap-assessment /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx

# =============================================================================
# FINAL OUTPUT
# =============================================================================
echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Application URL: ${GREEN}http://$DOMAIN_OR_IP${NC}"
echo -e "API Health Check: ${GREEN}http://$DOMAIN_OR_IP/health${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Check API status:    sudo systemctl status gap-assessment"
echo "  View API logs:       sudo journalctl -u gap-assessment -f"
echo "  Restart API:         sudo systemctl restart gap-assessment"
echo "  Check Nginx status:  sudo systemctl status nginx"
echo "  View Nginx logs:     sudo tail -f /var/log/nginx/error.log"
echo ""
echo -e "${RED}IMPORTANT:${NC}"
echo "  1. Update API keys in $APP_DIR/.env"
echo "  2. Update CORS origins in api/gap_assessment_api.py for your domain"
echo "  3. Consider setting up SSL with: sudo certbot --nginx"
echo ""