# Reliability Features

Detailed explanation of ReliAPI's reliability features and how they work for both HTTP and LLM targets.

---

## Retries

### How It Works

ReliAPI automatically retries failed requests based on error class:

- **429 (Rate Limit)**: Retries with exponential backoff, respecting `Retry-After` header
- **5xx (Server Error)**: Retries server errors (transient failures)
- **Network Errors**: Retries timeouts and connection errors

### Configuration

```yaml
retry_matrix:
  "429":
    attempts: 3
    backoff: "exp-jitter"
    base_s: 1.0
    max_s: 60.0
  "5xx":
    attempts: 2
    backoff: "exp-jitter"
    base_s: 1.0
  "net":
    attempts: 2
    backoff: "exp-jitter"
    base_s: 1.0
```

### Backoff Strategies

- **`exp-jitter`**: Exponential backoff with jitter (recommended)
- **`linear`**: Linear backoff

### Behavior

- **HTTP Targets**: Retries apply to all HTTP methods
- **LLM Targets**: Retries apply to LLM API calls
- **Non-Retryable**: 4xx errors (except 429) are not retried

---

## Circuit Breaker

### How It Works

Circuit breaker prevents cascading failures by opening circuit after threshold failures:

1. **Closed**: Normal operation, requests pass through
2. **Open**: Circuit opens after N consecutive failures, requests fail fast
3. **Half-Open**: After cooldown, allows test requests
4. **Closed**: If test succeeds, circuit closes

### Configuration

```yaml
circuit:
  error_threshold: 5      # Open after 5 failures
  cooldown_s: 60          # Stay open for 60 seconds
```

### Behavior

- **Per-Target**: Each target has its own circuit breaker
- **HTTP Targets**: Opens on HTTP errors (5xx, timeouts)
- **LLM Targets**: Opens on LLM API errors
- **Fast Fail**: When open, requests fail immediately without upstream call

---

## Cache

### How It Works

ReliAPI caches responses to reduce upstream calls:

- **HTTP**: GET/HEAD requests cached by default
- **LLM**: POST requests cached if enabled
- **TTL-Based**: Responses cached for configured TTL
- **Redis-Backed**: Uses Redis for storage

### Configuration

```yaml
cache:
  ttl_s: 300              # Cache for 5 minutes
  enabled: true
```

### Cache Keys

Cache keys include:

- Method (GET, POST, etc.)
- URL/path
- Query parameters (sorted)
- Significant headers (Accept, Content-Type)
- Body hash (for POST requests)

### Behavior

- **HTTP Targets**: GET/HEAD cached automatically
- **LLM Targets**: POST cached if `cache.enabled: true`
- **Cache Hit**: Returns cached response instantly
- **Cache Miss**: Makes upstream request and caches result

---

## Idempotency

### How It Works

Idempotency ensures duplicate requests return same result:

1. **Request Registration**: Request with `Idempotency-Key` is registered
2. **Conflict Detection**: If key exists, check if request body matches
3. **Coalescing**: Concurrent requests with same key execute once
4. **Result Caching**: Results cached for configured TTL

### Usage

Use `Idempotency-Key` header or `idempotency_key` field:

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Idempotency-Key: chat-123" \
  -d '{"target": "openai", "messages": [...]}'
```

### Behavior

- **HTTP Targets**: Works for POST/PUT/PATCH requests
- **LLM Targets**: Works for all LLM requests
- **Coalescing**: Concurrent requests with same key execute once
- **Conflict**: Different request bodies with same key return error
- **TTL**: Results cached for same TTL as cache config

### Response Meta

```json
{
  "meta": {
    "idempotent_hit": true,    # True if result from idempotency cache
    "cache_hit": false
  }
}
```

---

## Budget Caps (LLM Only)

### How It Works

Budget caps prevent unexpected LLM costs:

1. **Cost Estimation**: Pre-call cost estimation based on model, messages, max_tokens
2. **Hard Cap Check**: Rejects requests exceeding hard cap
3. **Soft Cap Check**: Throttles by reducing `max_tokens` if soft cap exceeded
4. **Cost Tracking**: Records actual cost in metrics

### Configuration

```yaml
llm:
  soft_cost_cap_usd: 0.01    # Throttle if exceeded
  hard_cost_cap_usd: 0.05    # Reject if exceeded
```

### Behavior

- **Hard Cap**: Rejects request if estimated cost > hard cap
- **Soft Cap**: Reduces `max_tokens` if estimated cost > soft cap
- **Cost Estimation**: Uses approximate pricing tables
- **Cost Tracking**: Records actual cost in `meta.cost_usd`

### Response Meta

```json
{
  "meta": {
    "cost_estimate_usd": 0.012,
    "cost_usd": 0.011,
    "cost_policy_applied": "soft_cap_throttled",
    "max_tokens_reduced": true,
    "original_max_tokens": 2000
  }
}
```

---

## Error Normalization

### How It Works

All errors are normalized to unified format:

```json
{
  "success": false,
  "error": {
    "type": "upstream_error",
    "code": "TIMEOUT",
    "message": "Request timed out",
    "retryable": true,
    "target": "openai",
    "status_code": 504
  },
  "meta": {
    "target": "openai",
    "retries": 2,
    "duration_ms": 20000
  }
}
```

### Error Types

- **`client_error`**: Client errors (4xx, invalid request)
- **`upstream_error`**: Upstream errors (5xx, timeout)
- **`budget_error`**: Budget errors (cost cap exceeded)
- **`internal_error`**: Internal errors (configuration, adapter)

### Behavior

- **No Raw Stacktraces**: Errors never expose internal stacktraces
- **Retryable Flag**: Indicates if error is retryable
- **Consistent Format**: All errors follow same structure

---

## Fallback Chains

### How It Works

Fallback chains provide automatic failover:

1. **Primary Target**: Try primary target first
2. **Failure Detection**: If primary fails, try fallback targets
3. **Sequential Fallback**: Try fallbacks in order
4. **Success**: Return first successful response

### Configuration

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    fallback_targets: ["anthropic", "mistral"]
```

### Behavior

- **HTTP Targets**: Fallback to backup HTTP APIs
- **LLM Targets**: Fallback to backup LLM providers
- **Sequential**: Tries fallbacks in order
- **Metadata**: Includes `fallback_used` and `fallback_target` in meta

---

## Summary

All reliability features work uniformly for HTTP and LLM targets:

- **Retries**: Automatic retries with exponential backoff
- **Circuit Breaker**: Per-target failure detection
- **Cache**: TTL cache for GET/HEAD and LLM responses
- **Idempotency**: Request coalescing for duplicate requests
- **Budget Caps**: Cost control for LLM requests (LLM only)
- **Error Normalization**: Unified error format
- **Fallback Chains**: Automatic failover to backup targets

---

## Next Steps

- [Configuration](Configuration.md) — Configuration guide
- [Comparison](Comparison.md) — Comparison with other tools

