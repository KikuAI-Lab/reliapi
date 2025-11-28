# ReliAPI

Reliability layer for API calls: retries, caching, dedup, circuit breakers.

[![npm version](https://badge.fury.io/js/reliapi-sdk.svg)](https://www.npmjs.com/package/reliapi-sdk)
[![PyPI version](https://badge.fury.io/py/reliapi-sdk.svg)](https://pypi.org/project/reliapi-sdk/)
[![Docker](https://img.shields.io/docker/v/kikudoc/reliapi?label=docker)](https://hub.docker.com/r/kikudoc/reliapi)

## Features

- **Retries with Backoff** - Automatic retries with exponential backoff
- **Circuit Breaker** - Prevent cascading failures
- **Caching** - TTL cache for GET requests and LLM responses
- **Idempotency** - Request coalescing with idempotency keys
- **Rate Limiting** - Built-in rate limiting per tier
- **LLM Proxy** - Unified interface for OpenAI, Anthropic, Mistral
- **Cost Control** - Budget caps and cost estimation

## Quick Start

### Using the SDK

**JavaScript/TypeScript:**

```bash
npm install reliapi-sdk
```

```typescript
import { ReliAPI } from 'reliapi-sdk';

const client = new ReliAPI({
  baseUrl: 'https://api.reliapi.dev',
  apiKey: 'your-api-key'
});

// HTTP proxy with retries
const response = await client.proxyHttp({
  target: 'my-api',
  method: 'GET',
  path: '/users/123',
  cache: 300  // cache for 5 minutes
});

// LLM proxy with idempotency
const llmResponse = await client.proxyLlm({
  target: 'openai',
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Hello!' }],
  idempotencyKey: 'unique-key-123'
});
```

**Python:**

```bash
pip install reliapi-sdk
```

```python
from reliapi_sdk import ReliAPI

client = ReliAPI(
    base_url="https://api.reliapi.dev",
    api_key="your-api-key"
)

# HTTP proxy with retries
response = client.proxy_http(
    target="my-api",
    method="GET",
    path="/users/123",
    cache=300
)

# LLM proxy with idempotency
llm_response = client.proxy_llm(
    target="openai",
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}],
    idempotency_key="unique-key-123"
)
```

### Using the CLI

```bash
pip install reliapi-cli
```

```bash
# Check health
reli ping

# Make HTTP request
reli request --method GET --url https://api.example.com/users

# Make LLM request
reli llm --target openai --message "Hello, world!"
```

### Using the GitHub Action

```yaml
- uses: KikuAI-Lab/reliapi@v1
  with:
    api-url: 'https://api.reliapi.dev'
    api-key: ${{ secrets.RELIAPI_KEY }}
    endpoint: '/proxy/http'
    method: 'POST'
    body: '{"target": "my-api", "method": "GET", "path": "/health"}'
```

## API Endpoints

### HTTP Proxy

```
POST /proxy/http
```

Proxy any HTTP API with reliability layers.

### LLM Proxy

```
POST /proxy/llm
```

Proxy LLM requests with idempotency, caching, and cost control.

### Health Check

```
GET /healthz
```

Health check endpoint for monitoring.

## Self-Hosting

```bash
docker run -d -p 8000:8000 \
  -e REDIS_URL="redis://localhost:6379/0" \
  kikudoc/reliapi:latest
```

## Documentation

- [OpenAPI Spec](./openapi/openapi.yaml)
- [Postman Collection](./postman/collection.json)
- [Full Documentation](https://reliapi.kikuai.dev)

## License

MIT License - see [LICENSE](./LICENSE) for details.

## Support

- GitHub Issues: https://github.com/KikuAI-Lab/reliapi/issues
- Email: dev@kikuai.dev

