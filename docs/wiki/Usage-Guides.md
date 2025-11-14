# Usage Guides

Complete guides for using ReliAPI with HTTP and LLM APIs.

## Table of Contents

- [HTTP Proxy](#http-proxy)
- [LLM Proxy](#llm-proxy)
- [Streaming (LLM Only)](#streaming-llm-only)
- [Idempotency](#idempotency)
- [Budget Control](#budget-control)
- [Fallback Chains](#fallback-chains)

---

## HTTP Proxy

ReliAPI can proxy any HTTP API, adding reliability features like retries, circuit breaker, and caching.

### Basic Request

```bash
curl -X POST https://reliapi.example.com/proxy/http \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "my-api",
    "method": "GET",
    "path": "/users/123",
    "idempotency_key": "req-123"
  }'
```

### Python Example

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://reliapi.example.com/proxy/http",
        headers={
            "X-API-Key": "your-api-key",
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
    print(result["data"])  # Response from upstream API
    print(result["meta"]["cache_hit"])  # True if cached
```

### Node.js Example

```javascript
const fetch = require('node-fetch');

const response = await fetch('https://reliapi.example.com/proxy/http', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    target: 'my-api',
    method: 'GET',
    path: '/users/123',
    idempotency_key: 'req-123'
  })
});

const result = await response.json();
console.log(result.data);  // Response from upstream API
console.log(result.meta.cache_hit);  // True if cached
```

### Response Format

```json
{
  "success": true,
  "data": {
    "status_code": 200,
    "headers": {...},
    "body": {...}
  },
  "meta": {
    "target": "my-api",
    "cache_hit": false,
    "idempotent_hit": false,
    "retries": 0,
    "duration_ms": 45,
    "request_id": "abc123"
  }
}
```

---

## LLM Proxy

ReliAPI provides a unified interface for multiple LLM providers (OpenAI, Anthropic, Mistral) with automatic retries, fallback, and cost control.

### Basic Request (Non-Streaming)

```bash
curl -X POST https://reliapi.example.com/proxy/llm \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "model": "gpt-4",
    "max_tokens": 100,
    "idempotency_key": "chat-123"
  }'
```

### Python Example

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://reliapi.example.com/proxy/llm",
        headers={
            "X-API-Key": "your-api-key",
            "Content-Type": "application/json"
        },
        json={
            "target": "openai",
            "messages": [
                {"role": "user", "content": "Hello!"}
            ],
            "model": "gpt-4",
            "max_tokens": 100,
            "idempotency_key": "chat-123"
        }
    )
    result = response.json()
    print(result["data"]["content"])  # LLM response
    print(result["meta"]["cost_usd"])  # Estimated cost
```

### Response Format

```json
{
  "success": true,
  "data": {
    "content": "Hello! How can I help you?",
    "role": "assistant",
    "finish_reason": "stop"
  },
  "meta": {
    "target": "openai",
    "provider": "openai",
    "model": "gpt-4",
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

## Streaming (LLM Only)

ReliAPI supports Server-Sent Events (SSE) for streaming LLM responses. Currently supported for OpenAI only.

### Request with Streaming

```bash
curl -X POST https://reliapi.example.com/proxy/llm \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [{"role": "user", "content": "Tell me a story"}],
    "model": "gpt-4",
    "stream": true
  }'
```

### Python Example

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "https://reliapi.example.com/proxy/llm",
        headers={
            "X-API-Key": "your-api-key",
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
                if event_type == "meta":
                    print(f"Request ID: {data['request_id']}")
                elif event_type == "chunk":
                    print(data["text"], end="", flush=True)
                elif event_type == "done":
                    print(f"\n\nCost: ${data['cost_usd']}")
                    print(f"Tokens: {data['usage']['total_tokens']}")
```

### SSE Event Format

**Meta Event:**
```
event: meta
data: {"request_id": "abc123", "target": "openai", "provider": "openai", "model": "gpt-4"}
```

**Chunk Event:**
```
event: chunk
data: {"text": "Hello", "index": 0}
```

**Done Event:**
```
event: done
data: {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}, "cost_usd": 0.003}
```

**Error Event:**
```
event: error
data: {"code": "BUDGET_EXCEEDED", "message": "Estimated cost exceeds hard cap"}
```

### Important Notes

- **Hard budget caps** are checked before opening the stream. If exceeded, you'll receive an error event immediately.
- **Soft budget caps** reduce `max_tokens` before the request, but won't interrupt a running stream.
- **Idempotency**: If a stream is already in progress for the same `idempotency_key`, you'll receive `STREAM_ALREADY_IN_PROGRESS` error.
- **Completed streams** are cached. Subsequent requests with the same `idempotency_key` return the cached result (non-streaming).

---

## Idempotency

ReliAPI ensures that identical requests are processed only once, even if submitted multiple times.

### How It Works

1. **Request Coalescing**: Multiple identical requests are automatically coalesced into a single upstream call.
2. **Result Caching**: Completed requests are cached by `idempotency_key` for a configurable TTL.
3. **Automatic Deduplication**: Subsequent requests with the same key return the cached result immediately.

### Usage

Simply include `idempotency_key` in your request:

```json
{
  "target": "my-api",
  "method": "POST",
  "path": "/orders",
  "body": {"item": "book", "quantity": 1},
  "idempotency_key": "order-12345"
}
```

### Response Metadata

Check `meta.idempotent_hit` to see if the response came from cache:

```json
{
  "meta": {
    "idempotent_hit": true,  // Response was cached
    "cache_hit": false,
    "retries": 0,
    "duration_ms": 5  // Very fast for cached responses
  }
}
```

### Best Practices

- **Use unique keys**: Generate UUIDs or use request-specific identifiers.
- **Include request body in key**: ReliAPI automatically hashes the request to detect conflicts.
- **Set appropriate TTL**: Configure `cache.ttl_s` in your target config to match your use case.

### Conflict Detection

If the same `idempotency_key` is used with a different request body, ReliAPI returns:

```json
{
  "success": false,
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "Idempotency key 'order-12345' used with different request body"
  }
}
```

---

## Budget Control

ReliAPI helps you control LLM costs with soft and hard budget caps.

### Configuration

In your `config.yaml`:

```yaml
targets:
  openai:
    llm:
      soft_cost_cap_usd: 0.10   # Reduce max_tokens if exceeded
      hard_cost_cap_usd: 0.50    # Reject request if exceeded
```

### How It Works

1. **Cost Estimation**: Before making the request, ReliAPI estimates the cost based on:
   - Provider pricing
   - Model selected
   - Prompt tokens (estimated from messages)
   - Max tokens requested

2. **Hard Cap Check**: If estimated cost > `hard_cost_cap_usd`, the request is rejected immediately:
   ```json
   {
     "success": false,
     "error": {
       "code": "BUDGET_EXCEEDED",
       "message": "Estimated cost $0.60 exceeds hard cap $0.50"
     }
   }
   ```

3. **Soft Cap Application**: If estimated cost > `soft_cost_cap_usd`, ReliAPI reduces `max_tokens` to fit within the cap:
   ```json
   {
     "meta": {
       "cost_policy_applied": "soft_cap",
       "max_tokens_reduced": 500,
       "original_max_tokens": 1000
     }
   }
   ```

### Response Metadata

```json
{
  "meta": {
    "cost_usd": 0.045,              // Actual cost
    "cost_estimate_usd": 0.050,      // Pre-request estimate
    "cost_policy_applied": "none",   // "none", "soft_cap", or "hard_cap"
    "max_tokens_reduced": null       // If soft cap was applied
  }
}
```

### Best Practices

- **Set conservative hard caps**: Prevent accidental high costs.
- **Use soft caps for flexibility**: Allow requests but limit token usage.
- **Monitor costs**: Use Prometheus metrics `reliapi_llm_cost_usd_total` to track spending.

---

## Fallback Chains

ReliAPI can automatically fallback to alternative targets if the primary target fails.

### Configuration

```yaml
targets:
  openai-primary:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai
      fallback_targets: ["openai-secondary", "anthropic-backup"]

  openai-secondary:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai

  anthropic-backup:
    base_url: https://api.anthropic.com/v1
    llm:
      provider: anthropic
```

### How It Works

1. **Primary Request**: ReliAPI attempts the request to the primary target.
2. **Failure Detection**: If the request fails (5xx, 429, network error), ReliAPI checks for fallback targets.
3. **Automatic Fallback**: ReliAPI retries the request to the next target in the chain.
4. **Metadata Tracking**: The response includes which target was actually used:

```json
{
  "meta": {
    "target": "openai-primary",
    "fallback_used": true,
    "fallback_target": "anthropic-backup"
  }
}
```

### When Fallback Triggers

- **5xx errors**: Server errors from upstream
- **429 errors**: Rate limit errors
- **Network errors**: Timeouts, connection failures
- **Circuit breaker open**: If the primary target's circuit breaker is open

### Best Practices

- **Order by priority**: List targets from most preferred to least preferred.
- **Use different providers**: Mix OpenAI, Anthropic, Mistral for maximum reliability.
- **Monitor fallback usage**: Track `meta.fallback_used` to identify problematic targets.

---

## Next Steps

- [Configuration Guide](Configuration) — Learn how to configure targets and policies
- [Reliability Features](Reliability-Features) — Deep dive into all features
- [Architecture](Architecture) — Understand how ReliAPI works internally

