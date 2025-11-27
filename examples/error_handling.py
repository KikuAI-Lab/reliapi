#!/usr/bin/env python3
"""
Error handling examples for ReliAPI.

This example demonstrates:
- Handling different error types
- Retry logic
- Rate limit handling
- Budget cap errors
- Network errors
"""
import httpx
import json
import os
import time

# Configuration
RELIAPI_URL = os.getenv("RELIAPI_URL", "http://localhost:8000")
API_KEY = os.getenv("RELIAPI_API_KEY", "sk-test")


def handle_rate_limit_error(response):
    """Handle rate limit errors with retry."""
    error_data = response.json()
    error = error_data.get("error", {})
    
    print(f"Rate limit error: {error.get('message')}")
    print(f"Source: {error.get('source')}")  # 'reliapi' or 'upstream'
    print(f"Retry after: {error.get('retry_after_s')}s")
    
    # Wait and retry
    retry_after = error.get("retry_after_s", 1.0)
    print(f"Waiting {retry_after}s before retry...")
    time.sleep(retry_after)
    
    return True  # Should retry


def handle_budget_error(response):
    """Handle budget cap errors."""
    error_data = response.json()
    error = error_data.get("error", {})
    
    print(f"Budget error: {error.get('message')}")
    print(f"Cost estimate: ${error.get('details', {}).get('cost_estimate_usd', 0)}")
    print(f"Hard cap: ${error.get('details', {}).get('hard_cost_cap_usd', 0)}")
    
    # Don't retry - budget cap is a hard limit
    return False  # Should not retry


def handle_upstream_error(response):
    """Handle upstream errors."""
    error_data = response.json()
    error = error_data.get("error", {})
    
    print(f"Upstream error: {error.get('message')}")
    print(f"Status code: {error.get('status_code')}")
    print(f"Retryable: {error.get('retryable')}")
    
    # Retry if retryable
    if error.get("retryable", False):
        print("Retrying after exponential backoff...")
        time.sleep(2)  # Simplified - use exponential backoff in production
        return True
    
    return False


def handle_network_error(exception):
    """Handle network errors."""
    print(f"Network error: {exception}")
    print("Retrying after delay...")
    time.sleep(1)
    return True  # Should retry


def make_request_with_retry(max_retries=3):
    """Make request with automatic retry logic."""
    for attempt in range(max_retries):
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
                    "model": "gpt-4o-mini",
                    "max_tokens": 10,
                },
                timeout=30.0,
            )
            
            if response.status_code == 200:
                return response.json()
            
            # Handle different error types
            error_data = response.json()
            error = error_data.get("error", {})
            error_type = error.get("type")
            error_code = error.get("code")
            
            if error_code == "RATE_LIMIT_RELIAPI" or error_code == "RATE_LIMIT_UPSTREAM":
                if handle_rate_limit_error(response):
                    continue  # Retry
                else:
                    break  # Don't retry
            
            elif error_code == "BUDGET_EXCEEDED":
                handle_budget_error(response)
                break  # Don't retry
            
            elif error_type == "upstream_error":
                if handle_upstream_error(response):
                    continue  # Retry
                else:
                    break  # Don't retry
            
            else:
                print(f"Unknown error: {error_code}")
                break
        
        except httpx.TimeoutException as e:
            if handle_network_error(e):
                continue  # Retry
            else:
                break
        
        except httpx.RequestError as e:
            if handle_network_error(e):
                continue  # Retry
            else:
                break
        
        except Exception as e:
            print(f"Unexpected error: {e}")
            break
    
    return None


def example_all_error_types():
    """Example: Handling all error types."""
    print("=== Error Handling Examples ===\n")
    
    # Example 1: Rate limit error
    print("1. Rate Limit Error:")
    print("   When rate limit is exceeded, ReliAPI returns 429 with retry_after_s")
    print("   Response includes source ('reliapi' or 'upstream') and retry_after_s\n")
    
    # Example 2: Budget cap error
    print("2. Budget Cap Error:")
    print("   When cost estimate exceeds hard cap, request is rejected")
    print("   Response includes cost_estimate_usd and hard_cost_cap_usd\n")
    
    # Example 3: Upstream error
    print("3. Upstream Error:")
    print("   When upstream API returns 5xx, ReliAPI normalizes the error")
    print("   Response includes retryable flag and normalized status code\n")
    
    # Example 4: Network error
    print("4. Network Error:")
    print("   When network fails, ReliAPI retries with exponential backoff")
    print("   Maximum retries configured in retry policy\n")
    
    # Make request with retry
    print("Making request with retry logic...")
    result = make_request_with_retry()
    
    if result:
        print("Success!")
    else:
        print("Failed after retries")


if __name__ == "__main__":
    example_all_error_types()

