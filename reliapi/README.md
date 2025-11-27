<div align="center">

# ReliAPI

> **Stability Engine for HTTP and LLM APIs**  
> Transform chaotic API calls into stable, reliable requests with automatic retries, circuit breakers, caching, and cost control.

[![Live Demo](https://img.shields.io/badge/Demo-Live%20Site-blue?style=for-the-badge)](https://kikuai-lab.github.io/reliapi/)
[![Documentation](https://img.shields.io/badge/Docs-Wiki-green?style=for-the-badge)](https://github.com/KikuAI-Lab/reliapi/wiki)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

**One Docker container. One config file. One unified API.**

</div>

---

## What is ReliAPI?

ReliAPI is a **minimal, self-hosted reliability layer** that sits between your application and external APIs. It adds automatic retries, circuit breakers, caching, idempotency, and cost controls to **any HTTP API or LLM provider**.

**Works with:**
- 🔗 **Any HTTP API** — REST services, payment gateways, SaaS APIs, internal microservices
- 🤖 **Any LLM Provider** — OpenAI, Anthropic, Mistral, and more

Unlike LLM-only gateways (LiteLLM, Portkey), ReliAPI handles **both HTTP and LLM requests** with the same reliability features. Unlike feature-heavy platforms, ReliAPI stays **minimal and focused on reliability**.

---

## Why ReliAPI?

| Problem | ReliAPI Solution |
|---------|------------------|
| 🔴 **Provider outages** | Automatic failover to backup services |
| 💸 **Surprise LLM bills** | Hard/soft budget caps prevent cost overruns |
| ⚡ **Rate limit errors** | Smart retries with exponential backoff |
| 🔄 **Duplicate requests** | First-class idempotency prevents duplicate charges |
| 📊 **No observability** | Prometheus metrics and structured logging |

**Key Benefits:**
- 🔑 **First-class idempotency** — Request coalescing prevents duplicate execution
- 💰 **Predictable costs** — Budget caps prevent surprise LLM bills
- 🚀 **Universal proxy** — Same reliability features for HTTP and LLM APIs
- 📦 **Self-hosted** — No SaaS lock-in, full control over your data

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

### Example Usage

**HTTP Proxy:**
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
```

**LLM Proxy:**
```python
response = httpx.post(
    "http://localhost:8000/proxy/llm",
    headers={"Idempotency-Key": "chat-123"},
    json={
        "target": "openai",
        "messages": [{"role": "user", "content": "Hello!"}],
        "model": "gpt-4o-mini"
    }
)
```

See [Examples](examples/) for more code samples.

---

## Key Features

| Feature | HTTP APIs | LLM APIs |
|---------|-----------|----------|
| 🔄 **Retries** | ✅ | ✅ |
| ⚡ **Circuit Breaker** | ✅ | ✅ |
| 💾 **Cache** | ✅ | ✅ |
| 🔑 **Idempotency** | ✅ | ✅ |
| 💰 **Budget Caps** | ❌ | ✅ |
| 📡 **Streaming** | ❌ | ✅ (OpenAI) |
| 🔀 **Fallback Chains** | ❌ | ✅ |

**Detailed feature documentation:** [Wiki → Reliability Features](https://github.com/KikuAI-Lab/reliapi/wiki/Reliability-Features)

---

## Performance

ReliAPI adds minimal overhead while providing significant reliability improvements:

- **Error Rate**: 20% → 1% (with ReliAPI)
- **Cost Variance**: ±30% → ±2% (predictable budgets)
- **Cache Hit Rate**: 15% → 68% (reduced API calls)
- **P95 Latency**: 450ms (faster than LiteLLM, Portkey, Helicone)

[See live demo →](https://kikuai-lab.github.io/reliapi/)

---

## Documentation

📖 **Full Documentation:** [Wiki Home](https://github.com/KikuAI-Lab/reliapi/wiki)

**Quick Links:**
- [Overview](https://github.com/KikuAI-Lab/reliapi/wiki/Overview) — What is ReliAPI and when to use it
- [Architecture](https://github.com/KikuAI-Lab/reliapi/wiki/Architecture) — How ReliAPI works internally
- [Configuration](https://github.com/KikuAI-Lab/reliapi/wiki/Configuration) — Configuring targets and policies
- [Reliability Features](https://github.com/KikuAI-Lab/reliapi/wiki/Reliability-Features) — Detailed feature explanations
- [Stability Shield](https://github.com/KikuAI-Lab/reliapi/wiki/Stability-Shield) — Anti-rate-limit layer with key pools
- [Comparison](https://github.com/KikuAI-Lab/reliapi/wiki/Comparison) — Comparison with other tools
- [FAQ](https://github.com/KikuAI-Lab/reliapi/wiki/FAQ) — Frequently asked questions

**Guides:**
- [How to make your LLM API idempotent](https://github.com/KikuAI-Lab/reliapi/wiki/Idempotency)
- [How to keep AI costs predictable using budget caps](https://github.com/KikuAI-Lab/reliapi/wiki/Budget-Caps)
- [Self-hosted LLM reliability layer in one Docker container](https://github.com/KikuAI-Lab/reliapi/wiki/Deploy-Guide)

---

## Comparison

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| HTTP + LLM | ✅ | ❌ | ❌ | ❌ |
| Idempotency | ✅ First-class | ❌ | ⚠️ | ❌ |
| Budget caps | ✅ | ⚠️ | ✅ | ✅ |
| Minimal | ✅ | ❌ | ❌ | ❌ |

[Detailed comparison →](https://github.com/KikuAI-Lab/reliapi/wiki/Comparison)

---

## Examples

- [Python Examples](examples/python_basic.py) — Basic usage, error handling
- [JavaScript Examples](examples/javascript_basic.js) — Browser and Node.js
- [cURL Examples](examples/curl_examples.sh) — Command-line testing
- [Configuration Examples](config.example.yaml) — Full config samples

---

## Requirements

- **Python**: 3.12+
- **Redis**: 7+ (for cache, idempotency, circuit breaker state)
- **Docker**: Optional (for containerized deployment)

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Links

- 🌐 **[Live Demo](https://kikuai-lab.github.io/reliapi/)** — Interactive demo and examples
- 📚 **[Documentation](https://github.com/KikuAI-Lab/reliapi/wiki)** — Complete wiki documentation
- 🐛 **[Issue Tracker](https://github.com/KikuAI-Lab/reliapi/issues)** — Report bugs or request features
- 🏢 **[KikuAI Lab](https://github.com/KikuAI-Lab)** — More projects

---

<div align="center">

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.

Made with ❤️ by [KikuAI Lab](https://github.com/KikuAI-Lab)

</div>

