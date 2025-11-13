# Self-hosted LLM reliability layer in one Docker container

**Run ReliAPI in Docker for easy deployment and isolation.**

---

## Quick Start

### 1. Pull Image

```bash
docker pull reliapi/reliapi:latest
```

### 2. Create Config

```yaml
# config.yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

### 3. Run Container

```bash
docker run -d \
  --name reliapi \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e RELIAPI_CONFIG=/app/config.yaml \
  -e OPENAI_API_KEY=your-key \
  -v $(pwd)/config.yaml:/app/config.yaml \
  reliapi/reliapi:latest
```

### 4. Verify

```bash
curl http://localhost:8000/healthz
# {"status":"healthy"}
```

---

## Docker Compose

### Full Stack (ReliAPI + Redis)

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  reliapi:
    image: reliapi/reliapi:latest
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379/0
      - RELIAPI_CONFIG=/app/config.yaml
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config.yaml:/app/config.yaml
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
```

Run:

```bash
docker-compose up -d
```

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RELIAPI_CONFIG` | Path to config file | `/app/config.yaml` |
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `LOG_LEVEL` | Logging level | `INFO` |

Provider API keys (set as needed):

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `MISTRAL_API_KEY`

---

## Volumes

### Config File

Mount config file:

```bash
-v $(pwd)/config.yaml:/app/config.yaml
```

### Redis Data (if using local Redis)

```bash
-v redis_data:/data
```

---

## Health Checks

ReliAPI provides `/healthz` endpoint:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
  interval: 30s
  timeout: 10s
  retries: 3
```

---

## Production Deployment

### 1. Use Specific Tag

```bash
docker pull reliapi/reliapi:v1.0.0
```

### 2. Resource Limits

```yaml
services:
  reliapi:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

### 3. Restart Policy

```yaml
services:
  reliapi:
    restart: unless-stopped
```

### 4. Logging

```yaml
services:
  reliapi:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## Monitoring

### Prometheus Metrics

Expose metrics endpoint:

```yaml
services:
  reliapi:
    ports:
      - "8000:8000"  # API
      - "9090:9090"  # Metrics (if using Prometheus)
```

Scrape metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'reliapi'
    static_configs:
      - targets: ['reliapi:8000']
    metrics_path: '/metrics'
```

---

## Troubleshooting

### Container Won't Start

Check logs:

```bash
docker logs reliapi
```

Common issues:

1. **Redis not accessible**: Check `REDIS_URL`
2. **Config file missing**: Check volume mount
3. **Port already in use**: Change port mapping

### Redis Connection Failed

```bash
# Test Redis connection
docker exec reliapi python3 -c "import redis; r=redis.from_url('redis://redis:6379/0'); r.ping()"
```

### Config Not Loading

```bash
# Check config file
docker exec reliapi cat /app/config.yaml
```

---

## Examples

### Development

```bash
docker run -it --rm \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  reliapi/reliapi:latest
```

### Production

```bash
docker run -d \
  --name reliapi \
  --restart unless-stopped \
  -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379/0 \
  -e RELIAPI_CONFIG=/app/config.yaml \
  -v $(pwd)/config.yaml:/app/config.yaml \
  reliapi/reliapi:latest
```

---

## Summary

ReliAPI Docker deployment provides:

- ✅ **Easy deployment**: Single container
- ✅ **Isolation**: Separate from host system
- ✅ **Portability**: Run anywhere Docker runs
- ✅ **Health checks**: Built-in monitoring
- ✅ **Resource limits**: Control CPU/memory usage

**Use Docker for easy, isolated ReliAPI deployment.**

