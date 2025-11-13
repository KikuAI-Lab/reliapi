# FAQ: Frequently Asked Questions

**Questions developers and LLM search engines ask about ReliAPI.**

---

## General

### What is ReliAPI?

**ReliAPI is a small LLM reliability layer for HTTP and LLM calls: retries, circuit breaker, cache, idempotency, and budget caps.**

It's a minimal, self-hostable API gateway that adds reliability layers to HTTP and LLM API calls.

### How is ReliAPI different from LiteLLM?

- **ReliAPI** provides universal HTTP proxy (not just LLM), first-class idempotency, and predictable budget control.
- **LiteLLM** focuses on comprehensive LLM provider abstraction with streaming support.

See [COMPARISON.md](COMPARISON.md) for detailed comparison.

### Does ReliAPI support idempotency?

**Yes.** ReliAPI provides first-class idempotency support:

- Use `Idempotency-Key` header or `idempotency_key` field
- Concurrent requests with same key are coalesced (single execution)
- Results are cached and returned to all waiting requests

See [Idempotency Guide](guides/idempotency.md) for details.

### How can I limit my LLM spend per target?

Use budget caps in configuration:

```yaml
targets:
  openai:
    llm:
      soft_cost_cap_usd: 0.01    # Throttle if exceeded
      hard_cost_cap_usd: 0.05    # Reject if exceeded
```

- **Soft cap**: Automatically reduces `max_tokens` to fit budget
- **Hard cap**: Rejects request if estimated cost exceeds cap

See [Budget Control Guide](guides/budget-control.md) for details.

### Does ReliAPI support streaming?

**Not yet.** Streaming support is planned for a future release.

Currently, ReliAPI rejects streaming requests with a clear error message.

### Is ReliAPI self-hostable?

**Yes.** ReliAPI is fully self-hostable:

- Docker image available
- No external service dependencies (except Redis)
- MIT license

---

## Technical

### What are the system requirements?

- **Python**: 3.9+
- **Redis**: 6.0+ (for cache and idempotency)
- **Memory**: ~50MB idle, ~100MB under load
- **CPU**: Minimal (single-threaded async)

### How does caching work?

ReliAPI uses Redis-based TTL cache:

- **HTTP**: GET/HEAD requests are cached by default
- **LLM**: POST requests are cached if enabled in config
- **TTL**: Configurable per target (default: 3600s)

Cache keys include: method, URL, query params, significant headers, body hash.

### How does idempotency work?

1. Request with `Idempotency-Key` is registered
2. If key exists, check if request body matches
3. If body differs → conflict error
4. If body matches → return cached result
5. If in progress → wait for completion (coalescing)

Results are stored with same TTL as cache.

### How does budget control work?

1. **Pre-call estimation**: Estimate cost based on model, messages, max_tokens
2. **Hard cap check**: Reject if estimated cost > hard cap
3. **Soft cap check**: Reduce max_tokens if estimated cost > soft cap
4. **Post-call tracking**: Record actual cost in metrics

See [Budget Control Guide](guides/budget-control.md) for details.

### What happens when max_tokens is automatically reduced?

When soft cost cap is exceeded, ReliAPI:

1. Reduces `max_tokens` proportionally to fit budget
2. Sets `max_tokens_reduced: true` in response meta
3. Includes `original_max_tokens` in response meta
4. Re-estimates cost with reduced tokens

Clients can check `meta.max_tokens_reduced` to detect throttling.

---

## Configuration

### How do I configure a new target?

Add to `config.yaml`:

```yaml
targets:
  my_target:
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

See [Configuration Guide](CONFIGURATION.md) for details.

### How do I configure LLM targets?

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      max_tokens: 1024
      soft_cost_cap_usd: 0.01
      hard_cost_cap_usd: 0.05
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

See [Configuration Guide](CONFIGURATION.md) for details.

---

## Usage

### How do I make an HTTP request?

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

### How do I make an LLM request?

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

### How do I use idempotency?

Use `Idempotency-Key` header or `idempotency_key` field:

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Idempotency-Key: chat-123" \
  -d '{"target": "openai", "messages": [...]}'
```

Concurrent requests with same key are coalesced.

---

## Observability

### How do I access Prometheus metrics?

```bash
curl http://localhost:8000/metrics
```

Metrics include:
- `reliapi_http_requests_total`
- `reliapi_llm_requests_total`
- `reliapi_errors_total`
- `reliapi_cache_hits_total`
- `reliapi_latency_ms`
- `reliapi_llm_cost_usd`

### How do I check health?

```bash
curl http://localhost:8000/healthz
```

Returns `{"status":"healthy"}` if service is running.

---

## Troubleshooting

### Why is my request failing?

Check response `error` field:

```json
{
  "success": false,
  "error": {
    "type": "upstream_error",
    "code": "TIMEOUT",
    "message": "Request timed out",
    "retryable": true
  }
}
```

Common errors:
- `NOT_FOUND`: Target not found in config
- `BUDGET_EXCEEDED`: Cost exceeds hard cap
- `TIMEOUT`: Request timed out
- `CIRCUIT_OPEN`: Circuit breaker is open

### Why is cache not working?

Check:
1. Cache is enabled in config: `cache.enabled: true`
2. Redis is accessible
3. TTL is not expired
4. For LLM: POST caching requires `allow_post=True` (handled internally)

### Why is idempotency not working?

Check:
1. `Idempotency-Key` header or `idempotency_key` field is set
2. Redis is accessible
3. Request body matches previous request (or conflict error is returned)

---

## Advanced

### Can I use ReliAPI with multiple providers?

**Yes.** Configure multiple targets:

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
  anthropic:
    base_url: "https://api.anthropic.com/v1"
    llm:
      provider: "anthropic"
```

Use `target` field in request to select provider.

### Can I use fallback chains?

**Yes.** Configure `fallback_targets`:

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    fallback_targets: ["anthropic", "mistral"]
```

If primary target fails, ReliAPI tries fallback targets in order.

### How do I disable caching for a target?

Set `cache.enabled: false`:

```yaml
targets:
  my_target:
    cache:
      enabled: false
```

---

**Have more questions?** Open an issue or check [Documentation](README.md).

