# RapidAPI Quick Start Guide

## Error: "API should have at least 1 endpoint before making it PUBLIC"

**Solution:** Add at least one endpoint in RapidAPI Dashboard.

---

## Fastest Way: Add Main Endpoint

### Step 1: Go to RapidAPI Dashboard
1. Login to [RapidAPI Dashboard](https://rapidapi.com/developer/dashboard)
2. Select your ReliAPI
3. Click **"Endpoints"** tab
4. Click **"Add Endpoint"**

### Step 2: Add POST /proxy/llm

**Endpoint Configuration:**
- **Path:** `/proxy/llm`
- **Method:** `POST`
- **Name:** `Proxy LLM Request`
- **Description:** `Proxy LLM requests to OpenAI, Anthropic, or Mistral with reliability features`

**Request Body Schema:**
```json
{
  "target": "string (required): openai | anthropic | mistral",
  "model": "string (required): Model name",
  "messages": "array (required): Array of {role, content}",
  "stream": "boolean (optional): Enable streaming",
  "max_tokens": "number (optional): Max tokens",
  "temperature": "number (optional): 0.0-2.0"
}
```

**Headers:**
- `X-API-Key` (required): User's API key
- `Content-Type`: `application/json`
- `X-Idempotency-Key` (optional): For idempotent requests

**Response:**
- Status: `200 OK`
- Body: JSON with `success`, `data`, `meta` fields

---

## Alternative: Import OpenAPI Spec

If RapidAPI supports OpenAPI import:

1. Go to **Settings** → **Import**
2. Enter URL: `https://reliapi.kikuai.dev/openapi.json`
3. Click **Import**

This will automatically add all endpoints.

---

## Minimum Required Endpoints

To make API public, add at least:

1. ✅ **POST /proxy/llm** (main endpoint)
2. ✅ **GET /healthz** (for RapidAPI health checks)

---

## Test After Adding

```bash
# Test the endpoint
curl -X POST https://reliapi.kikuai.dev/proxy/llm \
  -H "X-API-Key: test-key-1234567890" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "model": "gpt-4o-mini",
    "messages": [{"role": "user", "content": "Hi"}]
  }'
```

Expected response:
```json
{
  "success": true,
  "data": {
    "content": "...",
    "usage": {...}
  }
}
```

---

## Full Endpoint List

See `RAPIDAPI_ENDPOINTS.md` for complete endpoint documentation.

**Main endpoints:**
- `POST /proxy/llm` - LLM proxy (required)
- `POST /proxy/http` - HTTP proxy (optional)
- `GET /healthz` - Health check (required for monitoring)
- `GET /readyz` - Readiness check (optional)

---

## Troubleshooting

**If endpoints don't appear:**
1. Check that API is running: `curl https://reliapi.kikuai.dev/healthz`
2. Verify OpenAPI spec: `curl https://reliapi.kikuai.dev/openapi.json`
3. Check RapidAPI logs for import errors

**If test requests fail:**
1. Verify API key format (minimum 20 characters)
2. Check rate limits (Free tier: 20 req/min)
3. Verify target provider API keys are set on server

