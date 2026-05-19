# Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Heroku Deployment](#heroku-deployment)
4. [AWS EC2 Deployment](#aws-ec2-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Production Configuration](#production-configuration)
7. [Monitoring & Maintenance](#monitoring--maintenance)

## Prerequisites

### For All Deployments
- Python 3.11+
- MongoDB Atlas account or MongoDB server
- Git
- Virtual environment (venv)

### Platform-Specific
- **Heroku**: Heroku CLI, Heroku account
- **AWS**: AWS account, EC2 key pair
- **Docker**: Docker and Docker Compose installed

## Local Development

### 1. Setup
```bash
# Clone repository
git clone <repository-url>
cd AI_Equipment_Failure_Prediction

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Run Application
```bash
# Development mode (auto-reload)
python app_enterprise.py

# Production mode
FLASK_ENV=production python app_enterprise.py
```

### 3. Access Application
```
http://localhost:5000
```

## Heroku Deployment

### 1. Setup Heroku CLI
```bash
# Install Heroku CLI
# Windows: Download from https://devcenter.heroku.com/articles/heroku-cli
# macOS: brew install heroku/brew/heroku
# Linux: curl https://cli-assets.heroku.com/install-ubuntu.sh | sh

# Login to Heroku
heroku login
```

### 2. Create Heroku App
```bash
# Create app
heroku create your-app-name

# Add remote
heroku git:remote -a your-app-name
```

### 3. Configure Environment Variables
```bash
# Set Flask secret key
heroku config:set FLASK_SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Set MongoDB URI
heroku config:set MONGODB_URI="your-mongodb-uri"

# Set Flask environment
heroku config:set FLASK_ENV=production
FLASK_DEBUG=false

# Set email configuration
heroku config:set MAIL_SERVER=smtp.gmail.com
heroku config:set MAIL_PORT=587
heroku config:set MAIL_USE_TLS=True
heroku config:set MAIL_USERNAME=your-email@gmail.com
heroku config:set MAIL_PASSWORD=your-app-password
```

### 4. Create Procfile
```bash
# Create file
cat > Procfile << EOF
web: gunicorn -w 4 -b 0.0.0.0:\$PORT app_enterprise:app
EOF
```

### 5. Deploy
```bash
# Deploy to Heroku
git push heroku main

# View logs
heroku logs --tail

# Scale dynos (if needed)
heroku ps:scale web=2
```

### 6. Check Deployment
```bash
# Open app in browser
heroku open

# Check app status
heroku ps
heroku config
```

## AWS EC2 Deployment

### 1. Launch EC2 Instance

1. Go to AWS Console → EC2
2. Click "Launch Instance"
3. Select Ubuntu 20.04 LTS (free tier eligible)
4. Choose instance type: t2.micro
5. Configure security group:
   - Allow SSH (22) from your IP
   - Allow HTTP (80) from anywhere
   - Allow HTTPS (443) from anywhere
6. Create and download key pair
7. Launch instance

### 2. Connect to Instance
```bash
# Make key readable
chmod 400 your-key-pair.pem

# SSH into instance
ssh -i your-key-pair.pem ubuntu@your-instance-ip
```

### 3. Install Dependencies
```bash
# Update system
sudo apt update
sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install system dependencies
sudo apt install git nginx supervisor -y

# Install MongoDB (optional, if not using Atlas)
wget -qO - https://www.mongodb.org/static/pgp/server-5.0.asc | sudo apt-key add -
sudo add-apt-repository 'deb [arch=amd64 signed-by=/usr/share/keyrings/mongodb-server-5.0.gpg] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/5.0 multiverse'
sudo apt install -y mongodb-org
sudo systemctl start mongod
```

### 4. Clone and Setup Application
```bash
# Create app directory
sudo mkdir -p /var/www/equipment-prediction
sudo chown ubuntu:ubuntu /var/www/equipment-prediction

# Clone repository
cd /var/www/equipment-prediction
git clone <repository-url> .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn
```

### 5. Configure Environment
```bash
# Create .env file
nano .env

# Add your configuration:
# FLASK_ENV=production
# FLASK_SECRET_KEY=your-key
# MONGODB_URI=your-mongodb-uri
# etc.
```

### 6. Setup Nginx
```bash
# Create Nginx config
sudo nano /etc/nginx/sites-available/equipment-prediction

# Add:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

# Enable site
sudo ln -s /etc/nginx/sites-available/equipment-prediction /etc/nginx/sites-enabled/

# Test Nginx
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

### 7. Setup Supervisor
```bash
# Create supervisor config
sudo nano /etc/supervisor/conf.d/equipment-prediction.conf

# Add:
[program:equipment-prediction]
directory=/var/www/equipment-prediction
command=/var/www/equipment-prediction/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 app_enterprise:app
user=ubuntu
autostart=true
autorestart=true
stderr_logfile=/var/log/equipment-prediction.err.log
stdout_logfile=/var/log/equipment-prediction.out.log

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start equipment-prediction
```

### 8. Setup SSL (Let's Encrypt)
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get certificate
sudo certbot certonly --nginx -d your-domain.com

# Update Nginx config with SSL
# Then restart Nginx
```

## Docker Deployment

### 1. Create Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir gunicorn

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 5000

# Run application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app_enterprise:app"]
```

### 2. Create Docker Compose
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: production
      FLASK_SECRET_KEY: ${FLASK_SECRET_KEY}
      MONGODB_URI: ${MONGODB_URI}
      MAIL_SERVER: ${MAIL_SERVER}
      MAIL_USERNAME: ${MAIL_USERNAME}
      MAIL_PASSWORD: ${MAIL_PASSWORD}
    depends_on:
      - mongodb
    restart: always

  mongodb:
    image: mongo:5.0
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    restart: always

volumes:
  mongodb_data:
```

### 3. Build and Run
```bash
# Build image
docker build -t equipment-prediction .

# Run container
docker run -p 5000:5000 \
  -e FLASK_SECRET_KEY=your-key \
  -e MONGODB_URI=your-uri \
  equipment-prediction

# With Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

## Production Configuration

### Essential .env Settings

```bash
# Flask
FLASK_ENV=production
FLASK_DEBUG=false
FLASK_SECRET_KEY=<64-character-random-key>

# MongoDB
MONGODB_URI=<production-mongodb-uri>

# Email
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=<your-email>
MAIL_PASSWORD=<app-password>

# Security
PASSWORD_MIN_LENGTH=8
SESSION_TIMEOUT=3600
MAX_LOGIN_ATTEMPTS=5

# Performance
MAX_CONTENT_LENGTH=16777216
PREFERRED_URL_SCHEME=https

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/equipment-prediction.log
```

### Gunicorn Configuration

```python
# gunicorn_config.py
import multiprocessing

bind = "0.0.0.0:5000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 100
```

### Nginx Configuration

```nginx
upstream equipment_prediction {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 16M;
    
    location / {
        proxy_pass http://equipment_prediction;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
    
    # Cache static files
    location /static/ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

## Monitoring & Maintenance

### Application Monitoring

```bash
# Check application status
pm2 status

# View logs
pm2 logs equipment-prediction

# Monitor resources
htop

# Check disk space
df -h

# Check MongoDB
mongo --eval "db.adminCommand('ping')"
```

### Regular Maintenance

```bash
# Update dependencies monthly
pip list --outdated
pip install -r requirements.txt --upgrade

# Backup database
mongodump --uri="mongodb+srv://..." --out=/backups/

# Clean logs (older than 30 days)
find /var/log -name "*.log" -mtime +30 -delete

# Restart application
sudo systemctl restart equipment-prediction

# Check certificate expiration
sudo certbot renew --dry-run
```

### Health Checks

```bash
# Ping endpoint
curl http://your-domain.com/health

# Database check
curl http://your-domain.com/admin/api/health-check

# Monitor alerts
curl http://your-domain.com/dashboard/api/alerts
```

### Troubleshooting

```bash
# Check application logs
tail -f /var/log/equipment-prediction.out.log

# Check Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Check MongoDB connection
mongo --host <host> --port 27017

# Restart services
sudo systemctl restart nginx
sudo systemctl restart supervisor
```

## Performance Optimization

1. **Caching**: Implement Redis for session/data caching
2. **CDN**: Use CloudFront for static file distribution
3. **Database**: Add indexes to frequently queried fields
4. **Load Balancing**: Use load balancer for multiple instances
5. **Compression**: Enable Gzip compression in Nginx

## Security Best Practices

1. ✅ Use HTTPS only
2. ✅ Keep secret keys secure
3. ✅ Regular security updates
4. ✅ Strong password policies
5. ✅ Rate limiting enabled
6. ✅ CORS configured properly
7. ✅ Database backups scheduled
8. ✅ API key rotation
9. ✅ Audit logging enabled
10. ✅ Security headers configured

## Backup & Recovery

```bash
# Database backup (automated)
0 2 * * * /usr/local/bin/backup-mongodb.sh

# Application backup
0 3 * * * tar -czf /backups/app-$(date +%Y%m%d).tar.gz /var/www/equipment-prediction

# Restore from backup
tar -xzf /backups/app-20240115.tar.gz -C /var/www/
mongorestore --uri="mongodb+srv://..." /backups/dump/
```

---

**Last Updated:** December 2024
**Version:** 1.0
