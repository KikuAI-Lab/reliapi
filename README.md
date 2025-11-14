<div align="center">

# ReliAPI

**Self-hosted reliability layer for HTTP and LLM APIs**

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)](https://github.com/KikuAI-Lab/reliapi)

</div>

---

## What is ReliAPI?

ReliAPI is a minimal, self-hosted reliability layer that adds retries, circuit breakers, caching, idempotency, and budget caps to any HTTP API and any LLM provider.

- **First-class idempotency** — duplicate requests execute once via request coalescing
- **Predictable costs** — soft/hard budget caps prevent surprise bills
- **Works with any API** — universal proxy for REST services, payment gateways, SaaS APIs, and LLM providers

One Docker container, one config file, one unified API. All reliability features work consistently across HTTP and LLM targets, with comprehensive observability through Prometheus metrics and structured JSON logging.

---

## Why ReliAPI is Different

- **True idempotency** — request coalescing prevents duplicate execution and charges
- **Predictable cost policies** — soft caps (throttle) and hard caps (reject) for LLM costs
- **Universal proxy** — works for both HTTP APIs and LLM providers with the same reliability features

---

## Key Features

| Feature | Description |
|---------|-------------|
| 🔄 **Retries** | Exponential backoff with jitter |
| ⚡ **Circuit Breaker** | Automatic failure detection |
| 💾 **Cache** | TTL-based caching for GET/HEAD and LLM responses |
| 🔑 **Idempotency** | Request coalescing prevents duplicate execution |
| 💰 **Budget Caps** | Soft (throttle) and hard (reject) cost limits |
| 📡 **Streaming** | Server-Sent Events (SSE) for LLM responses (OpenAI) |
| 📊 **Observability** | Prometheus metrics and structured JSON logging |

---

## Quick Start

### Docker (Recommended)

```bash
docker run -d \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e OPENAI_API_KEY=sk-... \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/kikuai-lab/reliapi:latest
```

### Python

```bash
pip install -r requirements.txt
export REDIS_URL=redis://localhost:6379/0
export RELIAPI_CONFIG_PATH=config.yaml
uvicorn reliapi.app.main:app --host 0.0.0.0 --port 8000
```

### Configuration

Create `config.yaml`:

```yaml
targets:
  openai:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai
      default_model: gpt-4o-mini
      soft_cost_cap_usd: 0.10
      hard_cost_cap_usd: 0.50
    cache:
      enabled: true
      ttl_s: 3600
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

---

## Examples

### HTTP Proxy

```python
import httpx

response = httpx.post(
    "http://localhost:8000/proxy/http",
    headers={
        "X-API-Key": "your-key",
        "Content-Type": "application/json"
    },
    json={
        "target": "my-api",
        "method": "GET",
        "path": "/users/123",
        "idempotency_key": "req-123"
    }
)
result = response.json()
print(result["data"])  # Response from upstream
print(result["meta"]["cache_hit"])  # True if cached
```

### LLM Proxy (Non-Streaming)

```python
import httpx

response = httpx.post(
    "http://localhost:8000/proxy/llm",
    headers={
        "X-API-Key": "your-key",
        "Content-Type": "application/json"
    },
    json={
        "target": "openai",
        "messages": [{"role": "user", "content": "Hello!"}],
        "model": "gpt-4",
        "max_tokens": 100,
        "idempotency_key": "chat-123"
    }
)
result = response.json()
print(result["data"]["content"])  # LLM response
print(result["meta"]["cost_usd"])  # Estimated cost
```

### LLM Proxy (Streaming)

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/proxy/llm",
        headers={
            "X-API-Key": "your-key",
            "Content-Type": "application/json"
        },
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Tell me a story"}],
            "model": "gpt-4",
            "stream": True
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                if event_type == "chunk":
                    print(data["text"], end="", flush=True)
                elif event_type == "done":
                    print(f"\n\nCost: ${data['cost_usd']}")
```

---

## Response Format

All responses follow a consistent envelope format:

```json
{
  "success": true,
  "data": {
    // Response from upstream API
  },
  "meta": {
    "target": "openai",
    "cache_hit": false,
    "idempotent_hit": false,
    "retries": 0,
    "duration_ms": 1250,
    "cost_usd": 0.003,
    "request_id": "abc123"
  }
}
```

---

## Observability

### Prometheus Metrics

```promql
# Request rate
rate(reliapi_requests_total[5m])

# Error rate
rate(reliapi_errors_total[5m])

# P95 latency
histogram_quantile(0.95, reliapi_request_latency_ms_bucket)

# Cache hit rate
rate(reliapi_cache_hits_total[5m]) / 
  (rate(reliapi_cache_hits_total[5m]) + rate(reliapi_cache_misses_total[5m]))

# LLM costs
reliapi_llm_cost_usd_total
```

### Structured Logging

JSON logs with `request_id` for tracing:

```json
{
  "ts": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "abc123",
  "target": "openai",
  "kind": "llm",
  "stream": "false",
  "outcome": "success",
  "latency_ms": 1250,
  "cost_usd": 0.003
}
```

---

## Enterprise Features (Optional)

### Multi-Tenant Mode

Isolate clients with separate configs, budgets, and metrics:

```yaml
tenants:
  - name: "client-a"
    api_key: "sk-client-a-123"
    budget_caps:
      openai:
        soft_cost_cap_usd: 10.0
        hard_cost_cap_usd: 50.0
    fallback_targets:
      openai: ["openai-secondary"]
    rate_limit_rpm: 1000
```

Each tenant has isolated cache, idempotency, and metrics. Multi-tenant support is optional and modular.

---

## Comparison

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| HTTP + LLM | ✅ | ❌ | ❌ | ❌ |
| Idempotency | ✅ | ❌ | ⚠️ | ❌ |
| Budget caps | ✅ | ⚠️ | ✅ | ✅ |
| Minimal config | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Streaming | ✅ | ✅ | ✅ | ✅ |

---

## Production Deployment

See [Deployment Guide](https://github.com/KikuAI-Lab/reliapi/wiki/Deploy-Guide) for:
- Hetzner Cloud setup
- Docker Compose configuration
- Nginx reverse proxy
- SSL/TLS with Let's Encrypt
- Systemd service
- Monitoring setup

---

## Roadmap

- [ ] Streaming support for Anthropic and Mistral
- [ ] Enhanced observability (Grafana dashboards)
- [ ] Advanced multi-tenant features
- [ ] Rate limiting improvements

---

## What ReliAPI is NOT

- ❌ Not a full API gateway (no routing, load balancing)
- ❌ Not a monitoring platform (use Prometheus + Grafana)
- ❌ Not a replacement for API keys management
- ❌ Not a database or storage layer

ReliAPI focuses on **reliability** — retries, circuit breakers, caching, idempotency, and cost control.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Links

- 🌐 [Live Demo](https://kikuai.dev/products/reliapi)
- 📚 [Documentation](https://github.com/KikuAI-Lab/reliapi/wiki)
- 🐛 [Issue Tracker](https://github.com/KikuAI-Lab/reliapi/issues)

---

<div align="center">

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.

Made with ❤️ by [KikuAI Lab](https://kikuai.dev)

</div>
