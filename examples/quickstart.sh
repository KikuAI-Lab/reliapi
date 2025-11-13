#!/bin/bash
# Quick start example: HTTP proxy

RELIAPI_URL="${RELIAPI_URL:-http://localhost:8000}"
API_KEY="${API_KEY:-test-key}"

echo "=== ReliAPI HTTP Proxy Example ==="
echo ""

# Example 1: Simple GET request
echo "1. GET request:"
curl -X POST "$RELIAPI_URL/proxy/http" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "target": "test_http",
    "method": "GET",
    "path": "/get",
    "query": {"test": "value"}
  }' | python3 -m json.tool

echo ""
echo ""

# Example 2: GET with idempotency
echo "2. GET with idempotency:"
IDEMPOTENCY_KEY="test-$(date +%s)"
curl -X POST "$RELIAPI_URL/proxy/http" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -H "Idempotency-Key: $IDEMPOTENCY_KEY" \
  -d '{
    "target": "test_http",
    "method": "GET",
    "path": "/get"
  }' | python3 -m json.tool

echo ""
echo ""

# Example 3: LLM request
echo "3. LLM request:"
curl -X POST "$RELIAPI_URL/proxy/llm" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [
      {"role": "user", "content": "Say hello in one word"}
    ],
    "model": "gpt-4o-mini",
    "idempotency_key": "chat-123"
  }' | python3 -m json.tool

echo ""
echo "=== Done ==="

