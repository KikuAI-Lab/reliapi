# RapidAPI Endpoints Configuration

This document contains all endpoints that need to be added to RapidAPI before making the API public.

## Base URL
```
https://reliapi.kikuai.dev
```

## Authentication
All endpoints (except health checks) require:
```
Header: X-API-Key
Value: <user's API key>
```

---

## Required Endpoints for RapidAPI

### 1. POST /proxy/llm
**Main LLM Proxy Endpoint** - This is the primary endpoint users will use.

**Description:**
Proxy LLM requests to OpenAI, Anthropic, or Mistral with reliability features: retries, circuit breaker, cache, idempotency, and budget caps.

**Request Body:**
```json
{
  "target": "openai",
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": false,
  "max_tokens": 1000,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "content": "Hello! How can I assist you?",
    "role": "assistant",
    "usage": {
      "prompt_tokens": 9,
      "completion_tokens": 9,
      "total_tokens": 18
    }
  },
  "meta": {
    "target": "openai",
    "model": "gpt-4o-mini",
    "cache_hit": false,
    "duration_ms": 1328
  }
}
```

**Parameters:**
- `target` (required): Provider name - `"openai"`, `"anthropic"`, or `"mistral"`
- `model` (required): Model name (e.g., `"gpt-4o-mini"`, `"claude-3-haiku-20240307"`)
- `messages` (required): Array of message objects with `role` and `content`
- `stream` (optional): Boolean, enable SSE streaming
- `max_tokens` (optional): Maximum tokens to generate
- `temperature` (optional): Sampling temperature (0.0-2.0)
- `X-Idempotency-Key` (optional header): For idempotent requests

---

### 2. POST /proxy/http
**HTTP Proxy Endpoint** - For proxying any HTTP API.

**Description:**
Universal HTTP proxy endpoint for any HTTP API. Supports retries, circuit breaker, cache, and idempotency.

**Request Body:**
```json
{
  "target": "api.example.com",
  "method": "GET",
  "path": "/users/123",
  "headers": {
    "Authorization": "Bearer token"
  },
  "body": null
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status_code": 200,
    "headers": {},
    "body": {}
  },
  "meta": {
    "target": "api.example.com",
    "cache_hit": false,
    "duration_ms": 245
  }
}
```

**Parameters:**
- `target` (required): Target API hostname
- `method` (required): HTTP method - `"GET"`, `"POST"`, `"PUT"`, `"DELETE"`, etc.
- `path` (required): API path (e.g., `"/users/123"`)
- `headers` (optional): Request headers object
- `body` (optional): Request body (for POST/PUT)

---

### 3. GET /healthz
**Health Check** - For RapidAPI monitoring.

**Description:**
Health check endpoint. Returns service health status.

**Response:**
```json
{
  "status": "healthy"
}
```

**Status Code:** 200

**No authentication required** - This is a public endpoint.

---

### 4. GET /readyz
**Readiness Check** - For RapidAPI monitoring.

**Description:**
Readiness check endpoint. Returns service readiness status.

**Response:**
```json
{
  "status": "ready"
}
```

**Status Code:** 200

**No authentication required** - This is a public endpoint.

---

## Optional Endpoints (for monitoring)

### 5. GET /metrics
**Prometheus Metrics** - For monitoring and observability.

**Description:**
Returns Prometheus-formatted metrics.

**Response:** Plain text (Prometheus format)

**Authentication:** Optional (can be public or protected)

---

### 6. GET /rapidapi/status
**RapidAPI Status** - Special endpoint for RapidAPI.

**Description:**
Returns API status information for RapidAPI dashboard.

**Response:**
```json
{
  "status": "operational",
  "version": "1.0.0"
}
```

---

## How to Add Endpoints in RapidAPI

1. **Go to RapidAPI Dashboard**
   - Navigate to your API
   - Click on "Endpoints" tab

2. **Add Each Endpoint:**
   - Click "Add Endpoint"
   - Enter the path (e.g., `/proxy/llm`)
   - Select HTTP method (GET/POST)
   - Add description
   - Configure parameters (if needed)

3. **Minimum Required:**
   - ✅ `POST /proxy/llm` (main endpoint)
   - ✅ `GET /healthz` (for health checks)

4. **Recommended:**
   - ✅ `POST /proxy/http` (for HTTP proxying)
   - ✅ `GET /readyz` (for readiness checks)

---

## Test Endpoints Before Adding

### Test LLM Proxy:
```bash
curl -X POST https://reliapi.kikuai.dev/proxy/llm \
  -H "X-API-Key: test-key-1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### Test Health Check:
```bash
curl https://reliapi.kikuai.dev/healthz
```

### Test HTTP Proxy:
```bash
curl -X POST https://reliapi.kikuai.dev/proxy/http \
  -H "X-API-Key: test-key-1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "httpbin.org",
    "method": "GET",
    "path": "/get"
  }'
```

---

## OpenAPI Specification

Full OpenAPI spec is available at:
```
https://reliapi.kikuai.dev/openapi.json
```

You can import this directly into RapidAPI if they support OpenAPI import.

---

## Notes

- All endpoints support CORS
- Rate limiting is applied per API key
- Free tier has restrictions (see monetization tiers)
- Streaming is supported via SSE (Server-Sent Events)
- Idempotency requires `X-Idempotency-Key` header

