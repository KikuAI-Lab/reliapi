#!/bin/bash
# cURL examples for ReliAPI

RELIAPI_URL="${RELIAPI_URL:-http://localhost:8000}"
API_KEY="${RELIAPI_API_KEY:-sk-test}"

echo "=== ReliAPI cURL Examples ===\n"

# Example 1: HTTP Proxy
echo "1. HTTP Proxy Request:"
curl -X POST "${RELIAPI_URL}/proxy/http" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "httpbin",
    "method": "GET",
    "path": "/get"
  }'
echo "\n"

# Example 2: LLM Proxy (Basic)
echo "2. LLM Proxy Request (Basic):"
curl -X POST "${RELIAPI_URL}/proxy/llm" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Say '\''Hello'\'' only."}
    ],
    "model": "gpt-4o-mini",
    "max_tokens": 10
  }'
echo "\n"

# Example 3: LLM Proxy with Client Profile
echo "3. LLM Proxy with Client Profile:"
curl -X POST "${RELIAPI_URL}/proxy/llm" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Client: cursor" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Test"}
    ],
    "model": "gpt-4o-mini",
    "max_tokens": 10
  }'
echo "\n"

# Example 4: LLM Proxy with RouteLLM Headers
echo "4. LLM Proxy with RouteLLM Headers:"
curl -X POST "${RELIAPI_URL}/proxy/llm" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-RouteLLM-Provider: openai" \
  -H "X-RouteLLM-Model: gpt-4o-mini" \
  -H "X-RouteLLM-Correlation-ID: req-123" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Test"}
    ],
    "max_tokens": 10
  }'
echo "\n"

# Example 5: LLM Proxy with Idempotency Key
echo "5. LLM Proxy with Idempotency Key:"
curl -X POST "${RELIAPI_URL}/proxy/llm" \
  -H "X-API-Key: ${API_KEY}" \
  -H "X-Idempotency-Key: test-idempotency-123" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Say '\''Test'\'' only."}
    ],
    "model": "gpt-4o-mini",
    "max_tokens": 10
  }'
echo "\n"

# Example 6: LLM Proxy Streaming
echo "6. LLM Proxy Streaming:"
curl -X POST "${RELIAPI_URL}/proxy/llm" \
  -H "X-API-Key: ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5"}
    ],
    "model": "gpt-4o-mini",
    "stream": true,
    "max_tokens": 50
  }' \
  --no-buffer
echo "\n"

# Example 7: Health Check
echo "7. Health Check:"
curl -X GET "${RELIAPI_URL}/healthz"
echo "\n"

# Example 8: Metrics
echo "8. Metrics:"
curl -X GET "${RELIAPI_URL}/metrics" | head -20
echo "\n"

echo "=== Examples Complete ==="

