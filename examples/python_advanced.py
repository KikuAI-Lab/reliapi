#!/usr/bin/env python3
"""
Advanced Python example for ReliAPI.

This example demonstrates:
- Key pool management
- Rate limiting handling
- Client profiles
- RouteLLM headers
- Streaming
- Idempotency
"""
import httpx
import json
import os
import asyncio
import time

# Configuration
RELIAPI_URL = os.getenv("RELIAPI_URL", "http://localhost:8000")
API_KEY = os.getenv("RELIAPI_API_KEY", "sk-test")


def key_pool_example():
    """Example: Using key pool with automatic key rotation."""
    print("=== Key Pool Example ===")
    
    # Make multiple requests - ReliAPI will automatically select best key
    for i in range(5):
        response = httpx.post(
            f"{RELIAPI_URL}/proxy/llm",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": f"Request {i+1}"}],
                "model": "gpt-4o-mini",
                "max_tokens": 10,
            },
            timeout=30.0,
        )
        
        if response.status_code == 200:
            data = response.json()
            meta = data.get("meta", {})
            print(f"Request {i+1}: Success (provider: {meta.get('provider')})")
        else:
            print(f"Request {i+1}: Error {response.status_code}")
        
        time.sleep(0.5)  # Rate limiting


def rate_limiting_example():
    """Example: Handling rate limits."""
    print("\n=== Rate Limiting Example ===")
    
    # Make rapid requests to trigger rate limiting
    for i in range(10):
        response = httpx.post(
            f"{RELIAPI_URL}/proxy/llm",
            headers={
                "X-API-Key": API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "target": "openai",
                "messages": [{"role": "user", "content": f"Request {i+1}"}],
                "model": "gpt-4o-mini",
                "max_tokens": 10,
            },
            timeout=30.0,
        )
        
        if response.status_code == 200:
            print(f"Request {i+1}: Success")
        elif response.status_code == 429:
            error_data = response.json()
            error = error_data.get("error", {})
            retry_after = error.get("retry_after_s", 1.0)
            print(f"Request {i+1}: Rate limited. Retry after {retry_after}s")
            time.sleep(retry_after)
        else:
            print(f"Request {i+1}: Error {response.status_code}")


def client_profile_example():
    """Example: Using client profiles."""
    print("\n=== Client Profile Example ===")
    
    # Use X-Client header to apply client profile
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "X-Client": "cursor",  # Apply cursor_default profile
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Test"}],
            "model": "gpt-4o-mini",
            "max_tokens": 10,
        },
        timeout=30.0,
    )
    
    if response.status_code == 200:
        print("Success with client profile applied")
    else:
        print(f"Error: {response.status_code}")


def routellm_example():
    """Example: Using RouteLLM headers."""
    print("\n=== RouteLLM Example ===")
    
    response = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "X-RouteLLM-Provider": "openai",
            "X-RouteLLM-Model": "gpt-4o-mini",
            "X-RouteLLM-Correlation-ID": "req-123",
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",  # Can be overridden by header
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 10,
        },
        timeout=30.0,
    )
    
    if response.status_code == 200:
        data = response.json()
        meta = data.get("meta", {})
        print(f"Success with RouteLLM headers")
        print(f"Correlation ID: {meta.get('correlation_id')}")
    else:
        print(f"Error: {response.status_code}")


def streaming_example():
    """Example: Streaming LLM responses."""
    print("\n=== Streaming Example ===")
    
    with httpx.stream(
        "POST",
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Count from 1 to 5"}],
            "model": "gpt-4o-mini",
            "stream": True,
            "max_tokens": 50,
        },
        timeout=60.0,
    ) as response:
        if response.status_code == 200:
            print("Streaming response:")
            for line in response.iter_lines():
                if line.startswith("data: "):
                    data_str = line[6:]  # Remove "data: " prefix
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if content:
                            print(content, end="", flush=True)
                    except json.JSONDecodeError:
                        pass
            print()  # New line after stream
        else:
            print(f"Error: {response.status_code}")


def idempotency_example():
    """Example: Using idempotency keys."""
    print("\n=== Idempotency Example ===")
    
    idempotency_key = "test-idempotency-key-123"
    
    # First request
    response1 = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "X-Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Say 'First'"}],
            "model": "gpt-4o-mini",
            "max_tokens": 10,
        },
        timeout=30.0,
    )
    
    if response1.status_code == 200:
        data1 = response1.json()
        print(f"First request: {data1.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')}")
        print(f"Idempotent hit: {data1.get('meta', {}).get('idempotent_hit', False)}")
    
    # Duplicate request (should return cached result)
    response2 = httpx.post(
        f"{RELIAPI_URL}/proxy/llm",
        headers={
            "X-API-Key": API_KEY,
            "X-Idempotency-Key": idempotency_key,
            "Content-Type": "application/json",
        },
        json={
            "target": "openai",
            "messages": [{"role": "user", "content": "Say 'First'"}],
            "model": "gpt-4o-mini",
            "max_tokens": 10,
        },
        timeout=30.0,
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        print(f"Second request: {data2.get('data', {}).get('choices', [{}])[0].get('message', {}).get('content', '')}")
        print(f"Idempotent hit: {data2.get('meta', {}).get('idempotent_hit', False)}")


if __name__ == "__main__":
    print("ReliAPI Python Advanced Example\n")
    
    # Key pool example
    key_pool_example()
    
    # Rate limiting example
    rate_limiting_example()
    
    # Client profile example
    client_profile_example()
    
    # RouteLLM example
    routellm_example()
    
    # Streaming example
    streaming_example()
    
    # Idempotency example
    idempotency_example()

