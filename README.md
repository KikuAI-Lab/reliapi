<div align="center">

# ReliAPI

> A tiny, self-hosted reliability layer for **any HTTP API or LLM**.  
> Retries, circuit breaker, cache, idempotency, cost caps, streaming — in one Docker container.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=for-the-badge&logo=redis&logoColor=white)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-success?style=for-the-badge)](https://github.com/KikuAI-Lab/reliapi)

</div>

---

## ⭐ Highlights

- 🚀 **Universal HTTP + LLM proxy** — works with REST APIs, payment gateways, SaaS services, and LLM providers
- 🔄 **Automatic retries** with exponential backoff and jitter
- ⚡ **Circuit breaker** per target — automatic failure detection and recovery
- 💾 **Cache** (HTTP & LLM) with TTL — reduces duplicate calls and costs
- 🔑 **Idempotency with request coalescing** — duplicate requests execute once, preventing duplicate charges
- 💸 **Soft & hard budget caps** — predictable AI costs, no surprise bills
- 📡 **LLM streaming** (SSE) — Server-Sent Events for OpenAI responses
- 📊 **Prometheus metrics + JSON logs** — full observability with request tracing

---

## 🏗️ Architecture

```
Client Request
    │
    ▼
┌─────────────────────────────────┐
│   ReliAPI Gateway               │
│   POST /proxy/http or /llm      │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Idempotency Check    │  ← Coalesce duplicate requests
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Cache Check         │  ← GET/HEAD: check cache
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Budget Check        │  ← LLM: validate cost caps
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Circuit Breaker     │  ← Check if target is healthy
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Retry Logic         │  ← Execute with exponential backoff
    └──────────┬─────────────┘
               │
               ▼
    ┌──────────────────────┐
    │  Target API          │  ← HTTP or LLM provider
    └──────────┬─────────────┘
               │
               ▼
    Client Response (with meta: cache_hit, retries, cost, etc.)
```

---

## 🚀 Quick Start

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
    circuit:
      error_threshold: 5
      cooldown_s: 60
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

---

## 💡 Key Features in Action

### 🔑 Idempotency: Request Coalescing

**Problem:** Multiple identical requests → duplicate charges and inconsistent state.

**Solution:** ReliAPI coalesces concurrent requests with the same `idempotency_key` into a single upstream call.

```python
import httpx
import asyncio

async def make_request():
    response = await httpx.post(
        "http://localhost:8000/proxy/llm",
        headers={"Idempotency-Key": "chat-123"},
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Hello"}]
        }
    )
    return response.json()

# 5 concurrent requests with same idempotency_key
results = await asyncio.gather(*[make_request() for _ in range(5)])

# Result: Only 1 upstream LLM call, all 5 clients receive the same response
# meta.idempotent_hit: true for requests 2-5
```

**Response:**
```json
{
  "success": true,
  "data": {"content": "Hello! How can I help you?"},
  "meta": {
    "idempotent_hit": true,  // ← Request coalesced
    "cache_hit": false,
    "retries": 0,
    "cost_usd": 0.0001
  }
}
```

---

### ⚡ Circuit Breaker: Automatic Failure Detection

**Problem:** Unhealthy upstream services cause cascading failures and wasted retries.

**Solution:** ReliAPI opens the circuit after N consecutive failures, preventing requests until cooldown expires.

```yaml
targets:
  my-api:
    base_url: https://api.example.com
    circuit:
      error_threshold: 5      # Open circuit after 5 failures
      cooldown_s: 60          # Wait 60s before retry
```

**Behavior:**
```
Request 1-4: 500 errors → Record failures
Request 5:   500 error → Circuit OPENED
Request 6-10: Immediately rejected (circuit open)
After 60s:   Circuit HALF_OPEN → Test request
If success:  Circuit CLOSED → Normal operation
```

**Response when circuit is open:**
```json
{
  "success": false,
  "error": {
    "type": "circuit_breaker_error",
    "code": "CIRCUIT_OPEN",
    "message": "Circuit breaker is open for target 'my-api'",
    "retryable": false
  }
}
```

---

### 💸 Budget Caps: Predictable Costs

**Problem:** LLM costs can spiral out of control with unexpected token usage.

**Solution:** ReliAPI enforces soft caps (throttle) and hard caps (reject) per target.

```yaml
targets:
  openai:
    llm:
      soft_cost_cap_usd: 0.10   # Reduce max_tokens if exceeded
      hard_cost_cap_usd: 0.50    # Reject if exceeded
```

**Soft Cap Example:**
```python
# Request with max_tokens=2000, estimated cost: $0.12
response = httpx.post(
    "http://localhost:8000/proxy/llm",
    json={
        "target": "openai",
        "messages": [...],
        "max_tokens": 2000  # Exceeds soft cap
    }
)

# Result: ReliAPI automatically reduces max_tokens to fit $0.10 cap
# meta.cost_policy_applied: "soft_cap_reduced"
# meta.cost_estimate_usd: 0.10
```

**Hard Cap Example:**
```python
# Request with estimated cost: $0.60 (exceeds hard cap)
response = httpx.post(
    "http://localhost:8000/proxy/llm",
    json={
        "target": "openai",
        "messages": [...],
        "max_tokens": 10000
    }
)

# Result: Request rejected before upstream call
# {
#   "success": false,
#   "error": {
#     "code": "BUDGET_EXCEEDED",
#     "message": "Estimated cost $0.60 exceeds hard cap $0.50"
#   }
# }
```

---

### 📡 Streaming: Server-Sent Events (SSE)

**Streaming LLM responses with real-time cost tracking:**

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/proxy/llm",
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Count from 1 to 10"}],
            "stream": True
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("event: "):
                event_type = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
                
                if event_type == "meta":
                    print(f"Provider: {data['provider']}")
                    print(f"Cost estimate: ${data['cost_estimate_usd']}")
                
                elif event_type == "chunk":
                    print(data["text"], end="", flush=True)
                
                elif event_type == "done":
                    print(f"\n\nFinal cost: ${data['cost_usd']}")
                    print(f"Tokens: {data['usage']['prompt_tokens']} + {data['usage']['completion_tokens']}")
```

**SSE Events:**
```
event: meta
data: {"provider": "openai", "model": "gpt-4", "cost_estimate_usd": 0.003}

event: chunk
data: {"text": "1", "finish_reason": null}

event: chunk
data: {"text": " 2", "finish_reason": null}

event: chunk
data: {"text": " 3", "finish_reason": null}

...

event: done
data: {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 20}, "cost_usd": 0.002}
```

---

## 📊 Observability

### Prometheus Metrics

ReliAPI exposes comprehensive metrics at `/metrics`:

```promql
# Request rate by target and kind
rate(reliapi_requests_total{target="openai", kind="llm"}[5m])

# Error rate
sum(rate(reliapi_errors_total[5m])) by (target, error_code)

# P95 latency
histogram_quantile(0.95, sum(rate(reliapi_request_latency_ms_bucket[5m])) by (le, target))

# Cache hit ratio
sum(rate(reliapi_cache_hits_total[5m])) by (target) / 
  (sum(rate(reliapi_cache_hits_total[5m])) by (target) + 
   sum(rate(reliapi_cache_misses_total[5m])) by (target))

# Idempotent hit ratio
sum(rate(reliapi_idempotent_hits_total[5m])) by (target) /
  sum(rate(reliapi_requests_total[5m])) by (target)

# Budget cap triggers
sum(rate(reliapi_budget_events_total{event="hard_cap"}[5m])) by (target)

# LLM costs per target (USD/hour)
sum(rate(reliapi_llm_cost_usd_total[1h])) by (target) * 3600
```

### Structured JSON Logging

Every request is logged as a single JSON line with full context:

```json
{
  "ts": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "request_id": "req_abc123def456",
  "target": "openai",
  "kind": "llm",
  "stream": false,
  "model": "gpt-4o-mini",
  "outcome": "success",
  "error_code": null,
  "upstream_status": 200,
  "latency_ms": 1250,
  "cost_usd": 0.000012,
  "cache_hit": false,
  "idempotent_hit": false,
  "retries": 0,
  "tenant": "client-a"
}
```

**Trace a request:**
```bash
# Find all logs for a specific request
grep "req_abc123def456" /var/log/reliapi/app.log | jq

# Find all requests for a target
grep "openai" /var/log/reliapi/app.log | jq '.request_id' | sort -u
```

### Grafana Dashboards

Ready-to-use dashboards available in `deploy/grafana/`:
- **Overview**: Requests, errors, latency, cache, budget, cost
- **LLM Streaming**: Stream vs non-stream metrics, error codes, interruptions

---

## 🔄 Comparison

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| HTTP + LLM | ✅ | ❌ | ❌ | ❌ |
| **Idempotency** | ✅ **First-class** | ❌ | ⚠️ Limited | ❌ |
| Budget caps | ✅ Soft + Hard | ⚠️ Basic | ✅ | ✅ |
| Circuit breaker | ✅ | ⚠️ | ✅ | ⚠️ |
| Minimal config | ✅ | ❌ | ❌ | ❌ |
| Streaming | ✅ SSE | ✅ | ✅ | ✅ |

**Why ReliAPI?**
- **First-class idempotency** with request coalescing (prevents duplicate charges)
- **Universal proxy** for HTTP and LLM (not just LLM-only)
- **Predictable costs** with soft/hard caps (no surprise bills)
- **Minimal and self-hosted** (one container, one config)

---

## 🏢 Enterprise Features (Optional)

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

## 🚀 Production Deployment

See [Deployment Guide](https://github.com/KikuAI-Lab/reliapi/wiki/Deploy-Guide) for:
- Hetzner Cloud setup
- Docker Compose configuration
- Nginx reverse proxy
- SSL/TLS with Let's Encrypt
- Systemd service
- Monitoring setup

---

## 🗺️ Roadmap

- [ ] Streaming support for Anthropic and Mistral
- [ ] Enhanced observability (Grafana dashboards)
- [ ] Advanced multi-tenant features
- [ ] Rate limiting improvements

---

## ❌ What ReliAPI is NOT

- ❌ Not a full API gateway (no routing, load balancing)
- ❌ Not a monitoring platform (use Prometheus + Grafana)
- ❌ Not a replacement for API keys management
- ❌ Not a database or storage layer

ReliAPI focuses on **reliability** — retries, circuit breakers, caching, idempotency, and cost control.

---

## 📚 Links

- 🌐 [Live Demo](https://kikuai.dev/products/reliapi)
- 📚 [Documentation](https://github.com/KikuAI-Lab/reliapi/wiki)
- 🐛 [Issue Tracker](https://github.com/KikuAI-Lab/reliapi/issues)

---

<div align="center">

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.

Made with ❤️ by [KikuAI Lab](https://kikuai.dev)

</div>
