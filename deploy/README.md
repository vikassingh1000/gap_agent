# EC2 Deployment Guide

## Prerequisites

1. **EC2 Instance**: Ubuntu 22.04, `t3.medium` or larger
2. **Security Group**: Allow inbound ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
3. **API Keys**: Gemini, Pinecone, Browser-use

## Quick Deploy

### Option 1: Using the Script

```bash
# SSH into your EC2 instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Download and run setup script
curl -O https://raw.githubusercontent.com/YOUR_REPO/deploy/setup_ec2.sh
chmod +x setup_ec2.sh

# Edit the script to add your API keys and repo URL
nano setup_ec2.sh

# Run the script
./setup_ec2.sh
```

### Option 2: Manual Upload

```bash
# From your local machine, upload the project
scp -i your-key.pem -r ./Gap_Assesment-main ubuntu@your-ec2-ip:/opt/gap-assessment

# SSH in and run the setup
ssh -i your-key.pem ubuntu@your-ec2-ip
cd /opt/gap-assessment/deploy
chmod +x setup_ec2.sh
./setup_ec2.sh
```

## Post-Deployment

### 1. Update API Keys

```bash
nano /opt/gap-assessment/.env
```

Add your keys:
```
GEMINI_API_KEY=your_actual_key
PINECONE_API_KEY=your_actual_key
BROWSER_USE_API_KEY=your_actual_key
```

Then restart:
```bash
sudo systemctl restart gap-assessment
```

### 2. Update CORS (if using custom domain)

```bash
python3 /opt/gap-assessment/deploy/update_cors.py your-domain.com
sudo systemctl restart gap-assessment
```

### 3. Enable HTTPS (Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Useful Commands

| Command | Description |
|---------|-------------|
| `sudo systemctl status gap-assessment` | Check API status |
| `sudo systemctl restart gap-assessment` | Restart API |
| `sudo journalctl -u gap-assessment -f` | View API logs |
| `sudo systemctl status nginx` | Check Nginx status |
| `sudo tail -f /var/log/nginx/error.log` | View Nginx errors |

## Architecture

```
Internet
    │
    ▼
┌─────────────────────┐
│     Nginx (:80)     │
│  - Serves React SPA │
│  - Proxies /api/*   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Uvicorn (:8000)    │
│  FastAPI Backend    │
└──────────┬──────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
Gemini  Pinecone  Browser-use
```

## Troubleshooting

### API not responding
```bash
# Check if service is running
sudo systemctl status gap-assessment

# Check logs for errors
sudo journalctl -u gap-assessment -n 50

# Check if port 8000 is listening
sudo ss -tlnp | grep 8000
```

### Frontend not loading
```bash
# Check if build exists
ls -la /opt/gap-assessment/frontend/dist

# Check nginx config
sudo nginx -t

# Check nginx logs
sudo tail -f /var/log/nginx/error.log
```

### CORS errors
```bash
# Update CORS with your domain
python3 /opt/gap-assessment/deploy/update_cors.py your-domain.com
sudo systemctl restart gap-assessment
```