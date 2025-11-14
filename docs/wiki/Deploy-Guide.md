# Deployment Guide

Complete guide for deploying ReliAPI in production on Hetzner Cloud with Docker, Nginx, and systemd.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Server Setup](#server-setup)
- [Docker Installation](#docker-installation)
- [ReliAPI Deployment](#reliapi-deployment)
- [Nginx Configuration](#nginx-configuration)
- [Systemd Service](#systemd-service)
- [SSL/TLS Setup](#ssltls-setup)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Hetzner Cloud server (Ubuntu 22.04+ recommended)
- Domain name pointing to server IP
- SSH access to server
- Basic knowledge of Linux, Docker, and Nginx

---

## Server Setup

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Create User (Optional)

```bash
sudo adduser reliapi
sudo usermod -aG sudo reliapi
```

---

## Docker Installation

### Install Docker

```bash
# Remove old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

### Verify Installation

```bash
docker --version
docker compose version
```

---

## ReliAPI Deployment

### 1. Create Directory Structure

```bash
sudo mkdir -p /opt/reliapi/{config,logs}
cd /opt/reliapi
```

### 2. Create Configuration File

```bash
sudo nano config/config.yaml
```

Example configuration:

```yaml
targets:
  openai:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai
      model: gpt-4
      soft_cost_cap_usd: 0.10
      hard_cost_cap_usd: 0.50
    cache:
      enabled: true
      ttl_s: 3600
    retry:
      max_attempts: 3
      backoff_ms: 1000
    circuit_breaker:
      failure_threshold: 5
      recovery_timeout_s: 60
```

### 3. Create Environment File

```bash
sudo nano .env
```

```bash
REDIS_URL=redis://redis:6379/0
RELIAPI_CONFIG_PATH=/app/config.yaml
RELIAPI_API_KEY=your-secure-api-key-here
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
CORS_ORIGINS=https://yourdomain.com
LOG_LEVEL=INFO
```

### 4. Create Docker Compose File

```bash
sudo nano docker-compose.yml
```

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    container_name: reliapi-redis
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3

  reliapi:
    image: reliapi/reliapi:latest
    container_name: reliapi
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    env_file:
      - .env
    volumes:
      - ./config:/app/config:ro
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

### 5. Start Services

```bash
docker compose up -d
```

### 6. Verify Deployment

```bash
# Check logs
docker compose logs -f reliapi

# Check health
curl http://localhost:8000/healthz
```

---

## Nginx Configuration

### 1. Install Nginx

```bash
sudo apt install -y nginx
```

### 2. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/reliapi
```

```nginx
server {
    listen 80;
    server_name reliapi.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name reliapi.yourdomain.com;

    # SSL certificates (will be added by Certbot)
    ssl_certificate /etc/letsencrypt/live/reliapi.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/reliapi.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Proxy settings
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (optional: make it public)
    location /healthz {
        proxy_pass http://127.0.0.1:8000/healthz;
        access_log off;
    }
}
```

### 3. Enable Site

```bash
sudo ln -s /etc/nginx/sites-available/reliapi /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## SSL/TLS Setup

### Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### Obtain Certificate

```bash
sudo certbot --nginx -d reliapi.yourdomain.com
```

### Auto-Renewal

Certbot automatically sets up a systemd timer. Verify:

```bash
sudo systemctl status certbot.timer
```

---

## Systemd Service

### Create Service File

```bash
sudo nano /etc/systemd/system/reliapi.service
```

```ini
[Unit]
Description=ReliAPI Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/reliapi
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Enable and Start

```bash
sudo systemctl daemon-reload
sudo systemctl enable reliapi
sudo systemctl start reliapi
```

### Check Status

```bash
sudo systemctl status reliapi
```

---

## Monitoring

### Health Checks

```bash
# Local health check
curl http://localhost:8000/healthz

# Public health check
curl https://reliapi.yourdomain.com/healthz
```

### Logs

```bash
# Docker logs
docker compose logs -f reliapi

# Systemd logs
sudo journalctl -u reliapi -f
```

### Prometheus Metrics

ReliAPI exposes metrics at `/metrics`:

```bash
curl http://localhost:8000/metrics
```

### Uptime Monitoring

Set up monitoring (e.g., Uptime Kuma) to check:
- `https://reliapi.yourdomain.com/healthz` every 60 seconds
- TLS certificate expiry (warn at 21/7/3 days)

---

## Troubleshooting

### Service Won't Start

```bash
# Check Docker
docker ps -a
docker compose logs

# Check systemd
sudo systemctl status reliapi
sudo journalctl -u reliapi -n 50
```

### Nginx 502 Bad Gateway

```bash
# Check if ReliAPI is running
docker ps | grep reliapi

# Check ReliAPI logs
docker compose logs reliapi

# Test connection
curl http://127.0.0.1:8000/healthz
```

### SSL Certificate Issues

```bash
# Test certificate
sudo certbot certificates

# Renew manually
sudo certbot renew --dry-run
```

### Redis Connection Issues

```bash
# Check Redis
docker compose logs redis
docker exec -it reliapi-redis redis-cli ping
```

---

## Next Steps

- [Configuration Guide](Configuration) — Configure targets and policies
- [Performance & Load Testing](Performance-Load-Testing) — Test your deployment
- [Developer Guide](Developer-Guide) — Contribute to ReliAPI

