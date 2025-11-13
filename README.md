# ReliAPI

**ReliAPI is a small reliability layer for *any* HTTP API — REST services, internal microservices, and LLM calls.**

**Retries, circuit breaker, cache, idempotency, and predictable cost controls for LLM workloads.**

**Self-hosted gateway focused on stability and simplicity, not feature bloat.**

---

## What is ReliAPI?

ReliAPI is a minimal, self-hostable API gateway that adds reliability layers to HTTP and LLM API calls.

**ReliAPI is not limited to LLM calls.**

It can sit in front of *any* HTTP-based API — payment services, SaaS APIs, internal microservices — and apply the same retry, circuit breaker, cache, idempotency, and error handling policies in a uniform way.

It provides:

- **Retries** with exponential backoff
- **Circuit breaker** per target
- **TTL cache** for GET/HEAD and LLM requests
- **Idempotency** with request coalescing
- **Budget caps** for predictable LLM costs
- **Unified error format** (no raw stacktraces)
- **Prometheus metrics** for observability

ReliAPI is designed to be **simple, predictable, and stable** — not a feature-rich platform.

---

## Quick Start

### Docker (Recommended)

```bash
docker run -d \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  reliapi/reliapi:latest
```

### Python

```bash
pip install reliapi
reliapi --config config.yaml --redis-url redis://localhost:6379/0
```

---

## Examples

### HTTP Proxy

```bash
curl -X POST http://localhost:8000/proxy/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "target": "my_api",
    "method": "GET",
    "path": "/users/123",
    "idempotency_key": "req-123"
  }'
```

### LLM Proxy

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "gpt-4o-mini",
    "idempotency_key": "chat-123"
  }'
```

### Idempotency

ReliAPI supports idempotency via `Idempotency-Key` header or `idempotency_key` field:

```bash
# First request
curl -X POST http://localhost:8000/proxy/llm \
  -H "Idempotency-Key: chat-123" \
  -d '{"target": "openai", "messages": [...]}'

# Second request with same key returns cached result (no LLM call)
curl -X POST http://localhost:8000/proxy/llm \
  -H "Idempotency-Key: chat-123" \
  -d '{"target": "openai", "messages": [...]}'
```

---

## Configuration

See `examples/config.yaml` for full configuration examples.

### Minimal HTTP Target

```yaml
targets:
  my_api:
    base_url: "https://api.example.com"
    timeout_ms: 10000
    circuit:
      error_threshold: 5
      cooldown_s: 60
    cache:
      ttl_s: 300
      enabled: true
    auth:
      type: bearer_env
      env_var: API_KEY
```

### LLM Target with Budget Caps

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    timeout_ms: 20000
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      max_tokens: 1024
      soft_cost_cap_usd: 0.01    # Throttle if exceeded
      hard_cost_cap_usd: 0.05    # Reject if exceeded
    cache:
      ttl_s: 3600
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

---

## Features

### Reliability

- **Retries**: Configurable retry matrix per error class (429, 5xx, network)
- **Circuit Breaker**: Per-target failure threshold and cooldown
- **Fallback Chains**: Automatic failover to backup targets

### Predictability

- **Unified Errors**: Normalized error format (no raw stacktraces)
- **Budget Caps**: Hard cap (reject) and soft cap (throttle) for LLM costs
- **Cost Estimation**: Pre-call cost estimation with policy application

### Performance

- **Caching**: TTL cache for GET/HEAD and LLM requests
- **Idempotency**: Request coalescing for concurrent identical requests
- **Low Overhead**: Minimal latency addition (< 10ms typical)

### Observability

- **Prometheus Metrics**: Request counts, latency, errors, cache hits, costs
- **Structured Logging**: JSON logs with request IDs
- **Health Endpoint**: `/healthz` for monitoring

---

## Comparison

See [COMPARISON.md](docs/COMPARISON.md) for detailed comparison with LiteLLM, Portkey, and Helicone.

**TL;DR:**

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| Self-hosted | ✅ | ✅ | ✅ | ❌ |
| Idempotency | ✅ First-class | ❌ | ⚠️ Limited | ❌ |
| Budget Caps | ✅ | ⚠️ Basic | ✅ | ✅ |
| HTTP Proxy | ✅ | ❌ | ❌ | ❌ |
| Minimal | ✅ | ❌ | ❌ | ❌ |

---

## Documentation

- [Getting Started](docs/GETTING_STARTED.md)
- [Configuration Guide](docs/CONFIGURATION.md)
- [API Reference](docs/API.md)
- [FAQ](docs/FAQ.md)
- [Comparison](docs/COMPARISON.md)

---

## Guides

- [How to make your LLM API idempotent with ReliAPI](docs/guides/idempotency.md)
- [How to keep AI costs predictable using budget caps](docs/guides/budget-control.md)
- [Self-hosted LLM reliability layer in one Docker container](docs/guides/docker.md)

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.

