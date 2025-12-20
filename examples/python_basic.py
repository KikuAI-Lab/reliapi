#!/usr/bin/env python3
"""
Basic Python example for ReliAPI.

This example demonstrates:
- Basic HTTP proxy usage
- Basic LLM proxy usage
- Error handling
- Response parsing
- Caching and idempotency

Requirements:
    pip install httpx

Usage:
    python python_basic.py
"""
import httpx
import json
import os
import uuid

# Configuration
RELIAPI_URL = os.getenv("RELIAPI_URL", "https://reliapi.kikuai.dev")
API_KEY = os.getenv("RAPIDAPI_KEY", os.getenv("RELIAPI_API_KEY", "your-api-key"))

def http_proxy_example():
    """Example: HTTP proxy request with caching and idempotency."""
    print("=== HTTP Proxy Example ===")
    
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/http",
        headers={
            "X-RapidAPI-Key": API_KEY if "rapidapi" in RELIAPI_URL.lower() else None,
            "Authorization": f"Bearer {API_KEY}" if "rapidapi" not in RELIAPI_URL.lower() else None,
            "Content-Type": "application/json",
        },
        json={
            "target": "jsonplaceholder",
            "method": "GET",
            "path": "/posts/1",
            "cache": 300,  # Cache for 5 minutes
            "idempotency_key": f"http-{uuid.uuid4()}",
        },
        timeout=30.0,
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {json.dumps(data.get('data', {}), indent=2)[:200]}...")
        print(f"Cache hit: {data.get('meta', {}).get('cache_hit', False)}")
        print(f"Request ID: {data.get('meta', {}).get('request_id', 'N/A')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def llm_proxy_example():
    """Example: LLM proxy request with caching and idempotency."""
    print("\n=== LLM Proxy Example ===")
    
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-RapidAPI-Key": API_KEY if "rapidapi" in RELIAPI_URL.lower() else None,
            "Authorization": f"Bearer {API_KEY}" if "rapidapi" not in RELIAPI_URL.lower() else None,
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [
                {"role": "user", "content": "What is idempotency in API design? Explain in one sentence."}
            ],
            "model": "gpt-4o-mini",
            "max_tokens": 100,
            "idempotency_key": f"llm-{uuid.uuid4()}",
            "cache": 3600,  # Cache for 1 hour
        },
        timeout=60.0,
    )
    
    if response.status_code == 200:
        data = response.json()
        content = data.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"Response: {content}")
        print(f"Cost: ${data.get('meta', {}).get('cost_usd', 0)}")
        print(f"Cache hit: {data.get('meta', {}).get('cache_hit', False)}")
        print(f"Request ID: {data.get('meta', {}).get('request_id', 'N/A')}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def caching_example():
    """Example: Caching - same request twice, second is FREE!"""
    print("\n=== Caching Example ===")
    
    request_data = {
        "target": "openai",
        "messages": [
            {"role": "user", "content": "What is circuit breaker pattern?"}
        ],
        "model": "gpt-4o-mini",
        "cache": 3600,  # Cache for 1 hour
    }
    
    headers = {
        "X-RapidAPI-Key": API_KEY if "rapidapi" in RELIAPI_URL.lower() else None,
        "Authorization": f"Bearer {API_KEY}" if "rapidapi" not in RELIAPI_URL.lower() else None,
        "Content-Type": "application/json",
    }
    headers = {k: v for k, v in headers.items() if v is not None}
    
    # First request - will call OpenAI API
    print("First request (will call OpenAI API):")
    response1 = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers=headers,
        json=request_data,
        timeout=60.0,
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        content1 = data1.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"Response: {content1[:100]}...")
        print(f"Cache hit: {data1.get('meta', {}).get('cache_hit', False)}")
        print(f"Cost: ${data1.get('meta', {}).get('cost_usd', 0)}")
    
    # Second request - will be served from cache (FREE!)
    print("\nSecond request (same question - served from cache, FREE!):")
    response2 = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers=headers,
        json=request_data,
        timeout=60.0,
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        content2 = data2.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"Response: {content2[:100]}...")
        print(f"Cache hit: {data2.get('meta', {}).get('cache_hit', False)}")
        print(f"Cost: ${data2.get('meta', {}).get('cost_usd', 0)}")
        if data2.get('meta', {}).get('cache_hit'):
            print("✅ Second request was FREE (served from cache)!")


def error_handling_example():
    """Example: Error handling."""
    print("\n=== Error Handling Example ===")
    
    try:
        response = httpx.post(
            f"{RELIAPI_URL}/proxy/llm",
            headers={
                "X-RapidAPI-Key": API_KEY if "rapidapi" in RELIAPI_URL.lower() else None,
                "Authorization": f"Bearer {API_KEY}" if "rapidapi" not in RELIAPI_URL.lower() else None,
                "Content-Type": "application/json",
            },
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 100000,  # May exceed budget cap
            },
            timeout=60.0,
        )
        
        if response.status_code == 200:
            print("Success!")
        else:
            error_data = response.json()
            error = error_data.get("error", {})
            print(f"Error Type: {error.get('type')}")
            print(f"Error Code: {error.get('code')}")
            print(f"Message: {error.get('message')}")
            print(f"Retryable: {error.get('retryable')}")
            
            # Handle rate limit errors
            if error.get("code") == "RATE_LIMIT_RELIAPI":
                retry_after = error.get("retry_after_s", 1.0)
                print(f"Rate limited. Retry after {retry_after}s")
    
    except httpx.TimeoutException:
        print("Request timed out")
    except httpx.RequestError as e:
        print(f"Request error: {e}")


if __name__ == "__main__":
    print("ReliAPI Python Basic Example\n")
    
    # HTTP proxy example
    http_proxy_example()
    
    # LLM proxy example
    llm_proxy_example()
    
    # Caching example
    caching_example()
    
    # Error handling example
    error_handling_example()
    
    print("\n=== Examples Completed ===")
    print("\nBenefits of ReliAPI:")
    print("  ✓ Automatic retries on failures")
    print("  ✓ Caching reduces costs by 50-80%")
    print("  ✓ Idempotency prevents duplicate charges")
    print("  ✓ Budget caps prevent surprise bills")
    print("  ✓ Circuit breaker prevents cascading failures")

