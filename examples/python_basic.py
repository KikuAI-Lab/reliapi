#!/usr/bin/env python3
"""
Basic Python example for ReliAPI.

This example demonstrates:
- Basic HTTP proxy usage
- Basic LLM proxy usage
- Error handling
- Response parsing
"""
import httpx
import json
import os

# Configuration
RELIAPI_URL = os.getenv("RELIAPI_URL", "http://localhost:8000")
API_KEY = os.getenv("RELIAPI_API_KEY", "sk-test")

def http_proxy_example():
    """Example: HTTP proxy request."""
    print("=== HTTP Proxy Example ===")
    
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/http",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "target": "httpbin",
            "method": "GET",
            "path": "/get",
        },
        timeout=30.0,
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {json.dumps(data, indent=2)}")
        print(f"Cache hit: {data.get('meta', {}).get('cache_hit', False)}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def llm_proxy_example():
    """Example: LLM proxy request."""
    print("\n=== LLM Proxy Example ===")
    
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [
                {"role": "user", "content": "Say 'Hello, ReliAPI!' only."}
            ],
            "model": "gpt-4o-mini",
            "max_tokens": 20,
        },
        timeout=60.0,
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {json.dumps(data, indent=2)}")
        print(f"Content: {data.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')}")
        print(f"Cost: ${data.get('meta', {}).get('cost_usd', 0)}")
    else:
        print(f"Error: {response.status_code} - {response.text}")


def error_handling_example():
    """Example: Error handling."""
    print("\n=== Error Handling Example ===")
    
    try:
        response = httpx.post(
            f"{RELIAPI_URL}/proxy/llm",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": "Test"}],
                "max_tokens": 10000,  # May exceed budget cap
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
    
    # Error handling example
    error_handling_example()

