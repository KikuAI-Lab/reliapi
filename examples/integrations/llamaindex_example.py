"""
LlamaIndex Integration Example with ReliAPI

This example shows how to use ReliAPI as a reliability layer for LlamaIndex applications.
ReliAPI provides automatic retries, caching, idempotency, and budget controls for LLM API calls.

Requirements:
    pip install llama-index-openai reliapi-sdk

Usage:
    python llamaindex_example.py
"""

import os
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

# Configure ReliAPI as the base URL for OpenAI
# Option 1: Using RapidAPI
RELIAPI_BASE_URL = "https://reliapi.kikuai.dev/proxy/llm"

# Option 2: Using self-hosted ReliAPI
# RELIAPI_BASE_URL = "http://localhost:8000/proxy/llm"

# Set your API keys
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "your-rapidapi-key-here")
# OR for self-hosted:
# RELIAPI_API_KEY = os.getenv("RELIAPI_API_KEY", "your-reliapi-key-here")


def example_basic_query():
    """Basic query example with ReliAPI and LlamaIndex."""
    print("=" * 60)
    print("Example 1: Basic Query with ReliAPI + LlamaIndex")
    print("=" * 60)
    
    # Create LlamaIndex LLM with ReliAPI as base URL
    llm = OpenAI(
        api_base=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        temperature=0.7,
        # Add RapidAPI key as header if using RapidAPI
        api_key=RAPIDAPI_KEY if RAPIDAPI_KEY != "your-rapidapi-key-here" else "dummy-key",
        # Custom headers for ReliAPI
        additional_kwargs={
            "headers": {
                "X-RapidAPI-Key": RAPIDAPI_KEY
            } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
            # OR for self-hosted:
            # "headers": {"Authorization": f"Bearer {RELIAPI_API_KEY}"}
        }
    )
    
    # Set as default LLM
    Settings.llm = llm
    
    # Make a query
    response = llm.complete("What is the circuit breaker pattern?")
    print(f"Response: {response.text}")
    print()


def example_with_caching():
    """Example showing how ReliAPI caching reduces costs."""
    print("=" * 60)
    print("Example 2: Caching - Same Query Twice (Second is FREE)")
    print("=" * 60)
    
    llm = OpenAI(
        api_base=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        api_key=RAPIDAPI_KEY if RAPIDAPI_KEY != "your-rapidapi-key-here" else "dummy-key",
        additional_kwargs={
            "headers": {
                "X-RapidAPI-Key": RAPIDAPI_KEY
            } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        }
    )
    
    query = "Explain idempotency in API design."
    
    # First query - will call OpenAI API
    print("First query (will call OpenAI API):")
    response1 = llm.complete(query)
    print(f"Response: {response1.text[:100]}...")
    print()
    
    # Second query - will be served from cache (FREE!)
    print("Second query (same question - served from cache, FREE!):")
    response2 = llm.complete(query)
    print(f"Response: {response2.text[:100]}...")
    print("Note: Check ReliAPI logs/metrics to see cache hit!")
    print()


def example_rag_pipeline():
    """Example showing RAG pipeline with ReliAPI."""
    print("=" * 60)
    print("Example 3: RAG Pipeline with ReliAPI")
    print("=" * 60)
    
    from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Document
    
    llm = OpenAI(
        api_base=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        api_key=RAPIDAPI_KEY if RAPIDAPI_KEY != "your-rapidapi-key-here" else "dummy-key",
        additional_kwargs={
            "headers": {
                "X-RapidAPI-Key": RAPIDAPI_KEY
            } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        }
    )
    
    Settings.llm = llm
    
    # Create a simple document
    documents = [Document(text="ReliAPI is a reliability layer for HTTP and LLM APIs. "
                              "It provides caching, retry logic, idempotency, and circuit breaker functionality.")]
    
    # Create index
    index = VectorStoreIndex.from_documents(documents)
    
    # Create query engine
    query_engine = index.as_query_engine()
    
    # Query
    response = query_engine.query("What does ReliAPI provide?")
    print(f"Response: {response}")
    print()


def example_streaming():
    """Example showing streaming with ReliAPI."""
    print("=" * 60)
    print("Example 4: Streaming Responses")
    print("=" * 60)
    
    llm = OpenAI(
        api_base=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        api_key=RAPIDAPI_KEY if RAPIDAPI_KEY != "your-rapidapi-key-here" else "dummy-key",
        additional_kwargs={
            "headers": {
                "X-RapidAPI-Key": RAPIDAPI_KEY
            } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        }
    )
    
    print("Streaming response:")
    response_stream = llm.stream_complete("Write a haiku about reliability.")
    for token in response_stream:
        print(token.delta, end="", flush=True)
    print("\n")


def example_with_idempotency():
    """Example showing idempotency protection."""
    print("=" * 60)
    print("Example 5: Idempotency - Prevent Duplicate Charges")
    print("=" * 60)
    
    llm = OpenAI(
        api_base=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        api_key=RAPIDAPI_KEY if RAPIDAPI_KEY != "your-rapidapi-key-here" else "dummy-key",
        additional_kwargs={
            "headers": {
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                # Use same idempotency key for both requests
                "X-Idempotency-Key": "llamaindex-example-456"
            } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        }
    )
    
    query = "What is retry logic?"
    
    # Simulate duplicate request
    print("Request 1:")
    response1 = llm.complete(query)
    print(f"Response: {response1.text[:100]}...")
    print()
    
    print("Request 2 (same idempotency key):")
    response2 = llm.complete(query)
    print(f"Response: {response2.text[:100]}...")
    print("Note: Only ONE API call was made!")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ReliAPI + LlamaIndex Integration Examples")
    print("=" * 60)
    print()
    
    # Run examples
    try:
        example_basic_query()
        example_with_caching()
        example_rag_pipeline()
        example_streaming()
        example_with_idempotency()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        print()
        print("Benefits of using ReliAPI with LlamaIndex:")
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
        print("  1. Set RAPIDAPI_KEY environment variable (for RapidAPI)")
        print("  2. Installed dependencies: pip install llama-index-openai")
        print("  3. ReliAPI is accessible at the configured base URL")














