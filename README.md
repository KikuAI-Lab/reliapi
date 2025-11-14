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

## What is ReliAPI?

ReliAPI sits between your application and external APIs, adding reliability features that prevent failures and control costs. Works with **any HTTP API** (REST, payment gateways, SaaS) and **any LLM provider** (OpenAI, Anthropic, Mistral).

**One Docker container. One config file. One unified API.**

---

## Why ReliAPI?

- 🔑 **First-class idempotency** — duplicate requests execute once via request coalescing (prevents duplicate charges)
- 💸 **Predictable costs** — soft/hard budget caps prevent surprise LLM bills
- 🚀 **Universal proxy** — same reliability features for HTTP and LLM APIs
- 📦 **Minimal & self-hosted** — no SaaS lock-in, full control over your data

Unlike LLM-only gateways (LiteLLM, Portkey), ReliAPI handles both HTTP and LLM requests. Unlike feature-heavy platforms, ReliAPI stays minimal and focused on reliability.

---

## Key Features

- 🔄 **Retries** — exponential backoff with jitter
- ⚡ **Circuit breaker** — automatic failure detection per target
- 💾 **Cache** — TTL-based caching for GET/HEAD and LLM responses
- 🔑 **Idempotency** — request coalescing prevents duplicate execution
- 💰 **Budget caps** — soft (throttle) and hard (reject) cost limits
- 📡 **Streaming** — Server-Sent Events (SSE) for LLM responses
- 📊 **Observability** — Prometheus metrics and structured JSON logging

[**See all features →**](https://github.com/KikuAI-Lab/reliapi/wiki)

---

## Quick Start

### Docker

```bash
docker run -d \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -e OPENAI_API_KEY=sk-... \
  -v $(pwd)/config.yaml:/app/config.yaml \
  ghcr.io/kikuai-lab/reliapi:latest
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
    headers={"Idempotency-Key": "req-123"},
    json={
        "target": "my-api",
        "method": "GET",
        "path": "/users/123"
    }
)
result = response.json()
print(result["data"])  # Response from upstream
print(result["meta"]["cache_hit"])  # True if cached
```

### LLM Proxy

```python
import httpx

response = httpx.post(
    "http://localhost:8000/proxy/llm",
    headers={"Idempotency-Key": "chat-123"},
    json={
        "target": "openai",
        "messages": [{"role": "user", "content": "Hello!"}],
        "model": "gpt-4o-mini"
    }
)
result = response.json()
print(result["data"]["content"])  # LLM response
print(result["meta"]["cost_usd"])  # Estimated cost
```

[**More examples →**](https://github.com/KikuAI-Lab/reliapi/wiki/Usage-Guides)

---

## Capabilities

| Feature | HTTP APIs | LLM APIs |
|---------|-----------|----------|
| Retries | ✅ | ✅ |
| Circuit breaker | ✅ | ✅ |
| Cache | ✅ | ✅ |
| Idempotency | ✅ | ✅ |
| Budget caps | ❌ | ✅ |
| Streaming | ❌ | ✅ (OpenAI) |
| Fallback chains | ❌ | ✅ |

---

## Documentation

- 📖 [**Full Documentation**](https://github.com/KikuAI-Lab/reliapi/wiki) — complete guides and examples
- 🔑 [**Idempotency**](https://github.com/KikuAI-Lab/reliapi/wiki/Idempotency) — request coalescing deep-dive
- 💰 [**Budget Caps**](https://github.com/KikuAI-Lab/reliapi/wiki/Budget-Caps) — cost control examples
- 📡 [**Streaming**](https://github.com/KikuAI-Lab/reliapi/wiki/Streaming) — SSE events and examples
- ⚡ [**Circuit Breaker**](https://github.com/KikuAI-Lab/reliapi/wiki/Circuit-Breaker) — failure detection
- 📊 [**Observability**](https://github.com/KikuAI-Lab/reliapi/wiki/Observability) — metrics, logs, Grafana
- 🏗️ [**Architecture**](https://github.com/KikuAI-Lab/reliapi/wiki/Architecture) — system design
- 🚀 [**Deployment**](https://github.com/KikuAI-Lab/reliapi/wiki/Deploy-Guide) — production setup
- 🏢 [**Multi-Tenant**](https://github.com/KikuAI-Lab/reliapi/wiki/Multi-Tenant-Mode) — enterprise features
- 📚 [**API Reference**](https://github.com/KikuAI-Lab/reliapi/wiki/API-Reference) — endpoint details

---

## Comparison

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| HTTP + LLM | ✅ | ❌ | ❌ | ❌ |
| Idempotency | ✅ First-class | ❌ | ⚠️ | ❌ |
| Budget caps | ✅ | ⚠️ | ✅ | ✅ |
| Minimal | ✅ | ❌ | ❌ | ❌ |

[**Detailed comparison →**](https://github.com/KikuAI-Lab/reliapi/wiki/Comparison)

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
