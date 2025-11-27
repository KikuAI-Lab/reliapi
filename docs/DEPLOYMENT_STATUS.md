# ReliAPI Deployment Status & Setup Guide

## Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **Domain** | `reliapi.kikuai.dev` | Currently points to Cloudflare (172.67.173.122) |
| **Hetzner Server** | ❌ OFFLINE | IP: 91.98.122.162 - Not responding |
| **Demo** | ✅ Updated | Uses `https://reliapi.kikuai.dev` |
| **Documentation** | ✅ Updated | All links point to new domain |

---

## Required Actions

### 1. Fix Hetzner Server

The server at `91.98.122.162` is not responding. Either:

**Option A: Restart existing server**
```bash
# Login to Hetzner Console
# https://console.hetzner.cloud/
# Find server: reliapi-prod-1763115192 (ID: 113111433)
# Power on the server
```

**Option B: Create new server**
```bash
# In Hetzner Console:
# 1. Create new CPX21 server (2 vCPU, 4GB RAM)
# 2. Select Ubuntu 22.04
# 3. Add SSH key
# 4. Note the new IP address
```

### 2. Update DNS

Point `reliapi.kikuai.dev` to the Hetzner server IP:

```
Type: A
Name: reliapi
Value: <HETZNER_SERVER_IP>
TTL: 300
```

If using Cloudflare, disable proxy (orange cloud → grey) for direct connection, or keep proxy for DDoS protection.

### 3. Deploy ReliAPI

SSH to server and deploy:

```bash
# SSH to server
ssh ubuntu@<SERVER_IP>

# Clone repo
cd /opt
sudo git clone https://github.com/KikuAI-Lab/reliapi-private.git reliapi
cd reliapi/reliapi

# Copy config
cp deploy/hetzner/config.prod.yaml config.yaml
cp deploy/hetzner/env.example .env

# Edit .env with API keys
sudo nano .env
# Set:
# RELIAPI_API_KEY=<your-api-key>
# OPENAI_API_KEY=<openai-key>
# ANTHROPIC_API_KEY=<anthropic-key>
# MISTRAL_API_KEY=<mistral-key>

# Start with Docker
cd deploy/hetzner
sudo docker compose up -d

# Verify
curl http://localhost:8000/healthz
```

### 4. Setup SSL (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone -d reliapi.kikuai.dev

# Or use nginx plugin
sudo certbot --nginx -d reliapi.kikuai.dev
```

### 5. Setup Nginx

```bash
# Copy nginx config
sudo cp /opt/reliapi/reliapi/deploy/nginx-reliapi.conf /etc/nginx/sites-available/reliapi.kikuai.dev

# Enable site
sudo ln -s /etc/nginx/sites-available/reliapi.kikuai.dev /etc/nginx/sites-enabled/

# Test and reload
sudo nginx -t
sudo systemctl reload nginx
```

---

## RapidAPI Configuration

Once the server is running, configure RapidAPI with:

### Base URL
```
https://reliapi.kikuai.dev
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health check |
| `/readyz` | GET | Readiness check |
| `/proxy/llm` | POST | LLM proxy endpoint |
| `/proxy/http` | POST | HTTP proxy endpoint |
| `/metrics` | GET | Prometheus metrics |

### Health Check for RapidAPI
```
URL: https://reliapi.kikuai.dev/healthz
Method: GET
Expected Response: {"status": "healthy"}
Expected Status: 200
```

### Authentication Header
```
X-API-Key: <user's API key>
```

### Example Request (for RapidAPI testing)
```bash
curl -X POST https://reliapi.kikuai.dev/proxy/llm \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Monetization Tiers (for RapidAPI)

### Free Tier
- 20 requests/minute
- Models: gpt-4o-mini, claude-3-haiku, mistral-small only
- No streaming
- No idempotency

### Developer Tier ($29/month)
- 100 requests/minute
- All models
- Streaming enabled
- Idempotency enabled

### Pro Tier ($99/month)
- 500 requests/minute
- All models
- Streaming enabled
- Idempotency enabled
- Priority support

### Enterprise
- Custom limits
- SLA
- Dedicated support

---

## Verification Checklist

After deployment, verify:

- [ ] `curl https://reliapi.kikuai.dev/healthz` returns `{"status": "healthy"}`
- [ ] `curl https://reliapi.kikuai.dev/readyz` returns `{"status": "ready"}`
- [ ] SSL certificate valid (check with browser)
- [ ] LLM proxy works: test with OpenAI request
- [ ] HTTP proxy works: test with httpbin
- [ ] Metrics available at `/metrics`

---

## Server Information (from last deployment)

```
SERVER_ID=113111433
SERVER_IP=91.98.122.162
SERVER_NAME=reliapi-prod-1763115192
RELIAPI_API_KEY=Lnuii8yPq8WBzoJJGpWmXBlaoJ4NqDTkZJ0QNyDyrlI
```

**Note:** If creating new server, update this information.

