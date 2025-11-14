# Idempotency

ReliAPI provides first-class idempotency with request coalescing — duplicate requests execute once, preventing duplicate charges and ensuring consistency.

---

## How It Works

When multiple requests arrive with the same `idempotency_key`, ReliAPI:

1. **First request**: Executes normally and stores the result
2. **Concurrent requests**: Wait for the first request to complete
3. **Subsequent requests**: Return cached result instantly

All requests receive the same response, but only one upstream call is made.

---

## Request Coalescing Example

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
```

**Response for requests 2-5:**
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

## Usage

### HTTP Header

```python
headers = {
    "Idempotency-Key": "unique-key-123"
}
```

### Request Body

```python
json = {
    "target": "my-api",
    "method": "POST",
    "path": "/charges",
    "idempotency_key": "charge-123",  // ← In request body
    "body": {"amount": 1000}
}
```

---

## Behavior

- **Same key + same request**: Returns cached result (`idempotent_hit: true`)
- **Same key + different request**: Returns `409 Conflict` with `IDEMPOTENCY_KEY_CONFLICT`
- **TTL**: Results cached for 1 hour (configurable)
- **Cache namespace**: Isolated per tenant in multi-tenant mode

---

## Configuration

```yaml
targets:
  my-api:
    idempotency:
      ttl_s: 3600  # Cache results for 1 hour
```

---

## Use Cases

- **Payment processing**: Prevent duplicate charges on retries
- **LLM calls**: Avoid duplicate API costs for identical prompts
- **Webhook processing**: Ensure idempotent webhook handling
- **Concurrent requests**: Coalesce duplicate requests from multiple clients

---

## See Also

- [API Reference](API-Reference.md) — endpoint details
- [Usage Guides](Usage-Guides.md) — more examples
- [Multi-Tenant Mode](Multi-Tenant-Mode.md) — tenant isolation

