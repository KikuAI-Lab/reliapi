# Streaming

ReliAPI supports Server-Sent Events (SSE) streaming for LLM responses, providing real-time text chunks with cost tracking.

---

## Supported Providers

- ✅ **OpenAI** — full streaming support
- ⏳ **Anthropic** — coming soon
- ⏳ **Mistral** — coming soon

---

## Usage

### Python Example

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

### JavaScript Example

```javascript
const response = await fetch('http://localhost:8000/proxy/llm', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    target: 'openai',
    messages: [{role: 'user', content: 'Count from 1 to 10'}],
    stream: true
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
let eventType = '';

while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  
  const lines = decoder.decode(value).split('\n');
  for (const line of lines) {
    if (line.startsWith('event: ')) {
      eventType = line.slice(7);
    } else if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      if (eventType === 'chunk') {
        process.stdout.write(data.text);
      } else if (eventType === 'done') {
        console.log(`\n\nCost: $${data.cost_usd}`);
      }
    }
  }
}
```

---

## SSE Events

### `event: meta`

Sent once at the start of the stream:

```
event: meta
data: {"provider": "openai", "model": "gpt-4", "cost_estimate_usd": 0.003}
```

### `event: chunk`

Sent for each text chunk:

```
event: chunk
data: {"text": "1", "finish_reason": null}

event: chunk
data: {"text": " 2", "finish_reason": null}
```

### `event: done`

Sent once at the end with final usage and cost:

```
event: done
data: {"finish_reason": "stop", "usage": {"prompt_tokens": 10, "completion_tokens": 20}, "cost_usd": 0.002}
```

### `event: error`

Sent if an error occurs during streaming:

```
event: error
data: {"code": "UPSTREAM_STREAM_INTERRUPTED", "message": "Stream interrupted"}
```

---

## Budget Caps

**Hard caps** are checked **before** the stream opens. If exceeded, you'll receive an `event: error` with `BUDGET_EXCEEDED` before any chunks.

**Soft caps** reduce `max_tokens` before streaming starts.

---

## Idempotency

Streaming requests support idempotency:

- **First request**: Opens upstream stream and sends to client
- **Concurrent request with same key**: Returns `409 Conflict` with `STREAM_ALREADY_IN_PROGRESS`
- **After stream completes**: Cached result available for subsequent non-stream requests

---

## Error Handling

If the upstream stream fails mid-flight:
- ReliAPI sends `event: error` with `UPSTREAM_STREAM_INTERRUPTED`
- SSE stream closes
- No automatic retry or fallback during streaming

---

## See Also

- [Idempotency](Idempotency.md) — request coalescing
- [Budget Caps](Budget-Caps.md) — cost control
- [API Reference](API-Reference.md) — endpoint details

