# How to make your LLM API idempotent with ReliAPI

**Idempotency ensures that duplicate requests return the same result, without making duplicate API calls.**

---

## Problem

When making LLM API calls, duplicate requests can happen due to:

- Network retries
- User double-clicks
- Concurrent requests
- Application crashes/restarts

Without idempotency, duplicate requests result in:
- **Duplicate costs** (same request charged twice)
- **Inconsistent results** (different responses for same input)
- **Race conditions** (concurrent requests processing same data)

---

## Solution: ReliAPI Idempotency

ReliAPI provides **first-class idempotency support**:

1. **Request coalescing**: Concurrent requests with same key execute once
2. **Result caching**: Cached results returned to all waiting requests
3. **Conflict detection**: Different request bodies with same key return error

---

## Quick Start

### 1. Add Idempotency Key

Use `Idempotency-Key` header or `idempotency_key` field:

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Idempotency-Key: chat-123" \
  -d '{
    "target": "openai",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 2. Handle Concurrent Requests

```python
import asyncio
import httpx

async def make_request(key: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/proxy/llm",
            headers={"Idempotency-Key": key},
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Hello"}]
            }
        )
        return response.json()

# Concurrent requests with same key → single LLM call
results = await asyncio.gather(
    make_request("chat-123"),
    make_request("chat-123"),
    make_request("chat-123")
)
# All three return same result, but only one LLM API call was made
```

---

## How It Works

### 1. Request Registration

When request arrives with `Idempotency-Key`:

1. ReliAPI checks if key exists
2. If exists → check if request body matches
3. If body differs → return conflict error (409)
4. If body matches → return cached result
5. If new → register key and proceed

### 2. Request Coalescing

If request is in progress:

1. ReliAPI marks key as "in progress"
2. Concurrent requests wait (up to 30s)
3. When first request completes → result cached
4. All waiting requests receive cached result

### 3. Result Caching

Results are cached with same TTL as cache config:

```yaml
targets:
  openai:
    cache:
      ttl_s: 3600  # Idempotency results cached for 1 hour
```

---

## Best Practices

### 1. Generate Stable Keys

Use deterministic key generation:

```python
import hashlib
import json

def generate_idempotency_key(user_id: str, prompt: str) -> str:
    """Generate stable idempotency key."""
    data = json.dumps({"user_id": user_id, "prompt": prompt}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:16]
```

### 2. Include Request Context

Include relevant context in key:

```python
key = f"{user_id}:{session_id}:{prompt_hash}"
```

### 3. Handle Conflicts

Different request bodies with same key return conflict:

```json
{
  "success": false,
  "error": {
    "type": "client_error",
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "Request body differs from previous request with same key"
  }
}
```

Handle by:
- Using different key for different requests
- Or retrying with correct key

### 4. Set Appropriate TTL

Match idempotency TTL to use case:

```yaml
targets:
  openai:
    cache:
      ttl_s: 3600  # 1 hour for chat sessions
```

---

## Examples

### Example 1: Chat Session

```python
def chat(user_id: str, message: str, session_id: str):
    key = f"{user_id}:{session_id}:{hashlib.md5(message.encode()).hexdigest()}"
    
    response = requests.post(
        "http://localhost:8000/proxy/llm",
        headers={"Idempotency-Key": key},
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": message}]
        }
    )
    return response.json()
```

### Example 2: Batch Processing

```python
def process_batch(items: List[str]):
    results = []
    for item in items:
        key = f"batch:{hashlib.md5(item.encode()).hexdigest()}"
        
        response = requests.post(
            "http://localhost:8000/proxy/llm",
            headers={"Idempotency-Key": key},
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": f"Process: {item}"}]
            }
        )
        results.append(response.json())
    return results
```

### Example 3: Retry Logic

```python
def make_request_with_retry(prompt: str, max_retries: int = 3):
    key = f"retry:{hashlib.md5(prompt.encode()).hexdigest()}"
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:8000/proxy/llm",
                headers={"Idempotency-Key": key},
                json={
                    "target": "openai",
                    "messages": [{"role": "user", "content": prompt}]
                }
            )
            return response.json()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
```

---

## Benefits

### 1. Cost Savings

Idempotency prevents duplicate charges:

- **Without idempotency**: 3 retries = 3x cost
- **With idempotency**: 3 retries = 1x cost

### 2. Consistency

Same request always returns same result:

- **Without idempotency**: Different responses possible
- **With idempotency**: Guaranteed same response

### 3. Performance

Concurrent requests execute once:

- **Without idempotency**: All requests execute
- **With idempotency**: Single execution, all receive result

---

## Limitations

1. **TTL-bound**: Results cached for configured TTL only
2. **Redis-dependent**: Requires Redis for idempotency storage
3. **Body-sensitive**: Different bodies with same key return conflict

---

## Summary

ReliAPI idempotency provides:

- ✅ **Request coalescing** for concurrent requests
- ✅ **Result caching** with configurable TTL
- ✅ **Conflict detection** for different request bodies
- ✅ **Cost savings** by preventing duplicate calls
- ✅ **Consistency** by returning same result

**Use idempotency keys for all LLM requests to ensure reliability and cost efficiency.**

