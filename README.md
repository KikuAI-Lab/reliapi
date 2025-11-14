# ReliAPI

ReliAPI is a self-hosted reliability layer for HTTP and LLM APIs — adding retries, circuit breaker, cache, idempotency, and budget caps to any upstream API.

**Key benefits:**
- Works with **any HTTP** and **any LLM provider** — universal proxy for REST APIs, payment gateways, SaaS services, and LLM providers
- **Idempotent by design** via request coalescing — duplicate requests execute once, preventing duplicate charges and ensuring consistency
- **Predictable AI costs** via soft/hard budget caps — no surprise bills, automatic token throttling when soft caps are exceeded

ReliAPI provides a minimal, self-hostable gateway that sits between your application and external APIs. Unlike LLM-only gateways, ReliAPI handles both HTTP and LLM requests uniformly. Unlike feature-heavy SaaS platforms, ReliAPI stays minimal and fully self-hosted. One Docker container, one config file, one unified API — that's it. All reliability features (retries, circuit breaker, cache, idempotency, budget control) work consistently across HTTP and LLM targets, with comprehensive observability through Prometheus metrics and structured JSON logging.

---

## Key Features

- ✅ **Retries** with exponential backoff and jitter
- ✅ **Circuit breakers** for automatic failure detection
- ✅ **Caching** for GET/HEAD requests and LLM responses
- ✅ **First-class idempotency** with request coalescing
- ✅ **Predictable budget caps** (soft/hard cost limits)
- ✅ **Streaming** — Server-Sent Events (SSE) streaming for LLM responses (OpenAI)
- ✅ **Unified metrics** (Prometheus)

---

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

Create `config.yaml`:

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    timeout_ms: 20000
    circuit:
      error_threshold: 5
      cooldown_s: 60
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      max_tokens: 1024
      soft_cost_cap_usd: 0.01
      hard_cost_cap_usd: 0.05
    cache:
      ttl_s: 3600
      enabled: true
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

### Run

```bash
RELIAPI_CONFIG=config.yaml REDIS_URL=redis://localhost:6379/0 python -m uvicorn reliapi.app.main:app --host 0.0.0.0 --port 8000
```

---

## Examples

### HTTP Proxy

#### GET Request

```bash
curl -X POST http://localhost:8000/proxy/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "target": "my_api",
    "method": "GET",
    "path": "/users/123",
    "query": {"include": "profile"},
    "idempotency_key": "req-123"
  }'
```

#### POST Request

```bash
curl -X POST http://localhost:8000/proxy/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "target": "payments",
    "method": "POST",
    "path": "/charges",
    "body": {"amount": 1000, "currency": "usd"},
    "idempotency_key": "charge-123"
  }'
```

#### PUT Request with Cache

```bash
curl -X POST http://localhost:8000/proxy/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "target": "my_api",
    "method": "PUT",
    "path": "/users/123",
    "body": {"name": "John"},
    "cache": 300
  }'
```

### LLM Proxy

#### Non-Streaming

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

#### Streaming (Server-Sent Events)

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [{"role": "user", "content": "Count from 1 to 3"}],
    "model": "gpt-4o-mini",
    "stream": true
  }'
```

**Response:** Server-Sent Events (SSE) stream with `event: meta`, `event: chunk`, and `event: done` events.

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
- **Fallback Chains**: Simple sequential fallback for LLM proxy (HTTP proxy fallback planned)
- **Works for all HTTP APIs**, not just LLM providers

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
| Streaming | ✅ SSE (OpenAI) | ✅ | ✅ | ✅ |
| Minimal | ✅ | ❌ | ❌ | ❌ |

---

## Documentation

- **[Wiki](https://github.com/KikuAI-Lab/reliapi/wiki)** — Complete documentation and guides
  - [Overview](https://github.com/KikuAI-Lab/reliapi/wiki/Overview)
  - [Architecture](https://github.com/KikuAI-Lab/reliapi/wiki/Architecture)
  - [Configuration](https://github.com/KikuAI-Lab/reliapi/wiki/Configuration)
  - [Reliability Features](https://github.com/KikuAI-Lab/reliapi/wiki/Reliability-Features)
  - [Comparison](https://github.com/KikuAI-Lab/reliapi/wiki/Comparison)
  - [FAQ](https://github.com/KikuAI-Lab/reliapi/wiki/FAQ)
- [Demo](https://kikuai-lab.github.io/reliapi/) — [Interactive playground](https://kikuai-lab.github.io/reliapi/)

---

## Guides

All guides are available in the [Wiki](https://github.com/KikuAI-Lab/reliapi/wiki):

- [How to make your LLM API idempotent with ReliAPI](https://github.com/KikuAI-Lab/reliapi/wiki/guides/idempotency)
- [How to keep AI costs predictable using budget caps](https://github.com/KikuAI-Lab/reliapi/wiki/guides/budget-control)
- [Self-hosted LLM reliability layer in one Docker container](https://github.com/KikuAI-Lab/reliapi/wiki/guides/docker)

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.
