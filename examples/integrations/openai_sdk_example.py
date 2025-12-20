"""
OpenAI SDK Replacement Example with ReliAPI

This example shows how to replace OpenAI SDK calls with ReliAPI to add reliability features
without changing your code structure. Just change the base URL!

ReliAPI provides:
- Automatic retries
- Caching (reduce costs by 50-80%)
- Idempotency (prevent duplicate charges)
- Budget caps
- Circuit breaker
- Cost tracking

Requirements:
    pip install openai

Usage:
    python openai_sdk_example.py
"""

import os
from openai import OpenAI

# Configure ReliAPI as the base URL for OpenAI
# Option 1: Using RapidAPI
RELIAPI_BASE_URL = "https://reliapi.kikuai.dev/proxy/llm"

# Option 2: Using self-hosted ReliAPI
# RELIAPI_BASE_URL = "http://localhost:8000/proxy/llm"

# Set your API keys
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "your-rapidapi-key-here")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-key-here")
# OR for self-hosted:
# RELIAPI_API_KEY = os.getenv("RELIAPI_API_KEY", "your-reliapi-key-here")


def example_basic_chat():
    """Basic chat example - just change base_url!"""
    print("=" * 60)
    print("Example 1: Basic Chat - Drop-in Replacement")
    print("=" * 60)
    
    # Create OpenAI client with ReliAPI as base URL
    # This is the ONLY change needed!
    client = OpenAI(
        base_url=RELIAPI_BASE_URL,
        api_key=OPENAI_API_KEY,  # Still use OpenAI key
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        # OR for self-hosted:
        # default_headers={"Authorization": f"Bearer {RELIAPI_API_KEY}"}
    )
    
    # Your existing code works as-is!
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "What is idempotency in API design?"}
        ]
    )
    
    print(f"Response: {response.choices[0].message.content}")
    print(f"Cost: ${response.cost_usd if hasattr(response, 'cost_usd') else 'N/A'}")
    print()


def example_with_caching():
    """Example showing caching - same request twice, second is FREE!"""
    print("=" * 60)
    print("Example 2: Caching - Second Request is FREE")
    print("=" * 60)
    
    client = OpenAI(
        base_url=RELIAPI_BASE_URL,
        api_key=OPENAI_API_KEY,
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    question = "Explain circuit breaker pattern in 2 sentences."
    messages = [{"role": "user", "content": question}]
    
    # First request - will call OpenAI API
    print("First request (will call OpenAI API):")
    response1 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(f"Response: {response1.choices[0].message.content[:100]}...")
    print()
    
    # Second request - will be served from cache (FREE!)
    print("Second request (same question - served from cache, FREE!):")
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(f"Response: {response2.choices[0].message.content[:100]}...")
    print("Note: Check ReliAPI logs/metrics to see cache hit!")
    print()


def example_with_idempotency():
    """Example showing idempotency - prevent duplicate charges."""
    print("=" * 60)
    print("Example 3: Idempotency - Prevent Duplicate Charges")
    print("=" * 60)
    
    client = OpenAI(
        base_url=RELIAPI_BASE_URL,
        api_key=OPENAI_API_KEY,
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            # Use same idempotency key for both requests
            "X-Idempotency-Key": "openai-sdk-example-789"
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    messages = [{"role": "user", "content": "What is retry logic?"}]
    
    # Simulate user clicking button twice
    print("Request 1 (user clicks button):")
    response1 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(f"Response: {response1.choices[0].message.content[:100]}...")
    print()
    
    print("Request 2 (user clicks button again - same idempotency key):")
    response2 = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    print(f"Response: {response2.choices[0].message.content[:100]}...")
    print("Note: Only ONE API call was made, even though we called create() twice!")
    print()


def example_streaming():
    """Example showing streaming with ReliAPI."""
    print("=" * 60)
    print("Example 4: Streaming Responses")
    print("=" * 60)
    
    client = OpenAI(
        base_url=RELIAPI_BASE_URL,
        api_key=OPENAI_API_KEY,
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    print("Streaming response:")
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Write a haiku about reliability."}],
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n")


def example_before_after():
    """Show the difference: before and after ReliAPI."""
    print("=" * 60)
    print("Example 5: Before vs After ReliAPI")
    print("=" * 60)
    
    print("BEFORE (direct OpenAI API):")
    print("```python")
    print("client = OpenAI(api_key='sk-...')")
    print("response = client.chat.completions.create(...)")
    print("# Problems:")
    print("# - No retry logic")
    print("# - No caching (pay for every request)")
    print("# - No idempotency (duplicate charges)")
    print("# - No budget caps")
    print("# - No cost tracking")
    print("```")
    print()
    
    print("AFTER (with ReliAPI):")
    print("```python")
    print("client = OpenAI(")
    print("    base_url='https://reliapi.kikuai.dev/proxy/llm',")
    print("    api_key='sk-...',")
    print("    default_headers={'X-RapidAPI-Key': '...'}")
    print(")")
    print("response = client.chat.completions.create(...)")
    print("# Benefits:")
    print("# ✓ Automatic retries")
    print("# ✓ Caching (save 50-80%)")
    print("# ✓ Idempotency protection")
    print("# ✓ Budget caps")
    print("# ✓ Cost tracking")
    print("```")
    print()


def example_migration_guide():
    """Show migration guide."""
    print("=" * 60)
    print("Migration Guide: OpenAI SDK → ReliAPI")
    print("=" * 60)
    print()
    print("Step 1: Install dependencies")
    print("  pip install openai")
    print()
    print("Step 2: Change base_url in your OpenAI client")
    print("  OLD: client = OpenAI(api_key='sk-...')")
    print("  NEW: client = OpenAI(")
    print("      base_url='https://reliapi.kikuai.dev/proxy/llm',")
    print("      api_key='sk-...',")
    print("      default_headers={'X-RapidAPI-Key': 'your-key'}")
    print("  )")
    print()
    print("Step 3: That's it! Your code works as-is.")
    print()
    print("Optional: Add idempotency keys")
    print("  default_headers={")
    print("      'X-RapidAPI-Key': 'your-key',")
    print("      'X-Idempotency-Key': 'unique-key-per-request'")
    print("  }")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ReliAPI + OpenAI SDK Integration Examples")
    print("=" * 60)
    print()
    
    # Run examples
    try:
        example_basic_chat()
        example_with_caching()
        example_with_idempotency()
        example_streaming()
        example_before_after()
        example_migration_guide()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        print()
        print("Key Takeaway:")
        print("  Just change base_url - that's all you need!")
        print("  Your existing OpenAI SDK code works without any other changes.")
        print()
        print("Benefits:")
        print("  ✓ Automatic retries on failures")
        print("  ✓ Caching reduces costs by 50-80%")
        print("  ✓ Idempotency prevents duplicate charges")
        print("  ✓ Budget caps prevent surprise bills")
        print("  ✓ Circuit breaker prevents cascading failures")
        print("  ✓ Real-time cost tracking")
        print()
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("  1. Set RAPIDAPI_KEY and OPENAI_API_KEY environment variables")
        print("  2. Installed dependencies: pip install openai")
        print("  3. ReliAPI is accessible at the configured base URL")














