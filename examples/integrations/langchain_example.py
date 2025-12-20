"""
LangChain Integration Example with ReliAPI

This example shows how to use ReliAPI as a reliability layer for LangChain applications.
ReliAPI provides automatic retries, caching, idempotency, and budget controls for LLM API calls.

Requirements:
    pip install langchain-openai reliapi-sdk

Usage:
    python langchain_example.py
"""

import os
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Configure ReliAPI as the base URL for OpenAI
# Option 1: Using RapidAPI
RELIAPI_BASE_URL = "https://reliapi.kikuai.dev/proxy/llm"

# Option 2: Using self-hosted ReliAPI
# RELIAPI_BASE_URL = "http://localhost:8000/proxy/llm"

# Set your API keys
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "your-rapidapi-key-here")
# OR for self-hosted:
# RELIAPI_API_KEY = os.getenv("RELIAPI_API_KEY", "your-reliapi-key-here")


def example_basic_chat():
    """Basic chat example with ReliAPI and LangChain."""
    print("=" * 60)
    print("Example 1: Basic Chat with ReliAPI + LangChain")
    print("=" * 60)
    
    # Create LangChain LLM with ReliAPI as base URL
    llm = ChatOpenAI(
        base_url=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        temperature=0.7,
        # Add RapidAPI key as header if using RapidAPI
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
        # OR for self-hosted:
        # default_headers={"Authorization": f"Bearer {RELIAPI_API_KEY}"}
    )
    
    # Make a chat request
    messages = [
        SystemMessage(content="You are a helpful assistant."),
        HumanMessage(content="What is idempotency in API design?")
    ]
    
    response = llm.invoke(messages)
    print(f"Response: {response.content}")
    print(f"Response metadata: {response.response_metadata}")
    print()


def example_with_caching():
    """Example showing how ReliAPI caching reduces costs."""
    print("=" * 60)
    print("Example 2: Caching - Same Request Twice (Second is FREE)")
    print("=" * 60)
    
    llm = ChatOpenAI(
        base_url=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    question = "Explain circuit breaker pattern in 2 sentences."
    messages = [HumanMessage(content=question)]
    
    # First request - will call OpenAI API
    print("First request (will call OpenAI API):")
    response1 = llm.invoke(messages)
    print(f"Response: {response1.content[:100]}...")
    print()
    
    # Second request - will be served from cache (FREE!)
    print("Second request (same question - served from cache, FREE!):")
    response2 = llm.invoke(messages)
    print(f"Response: {response2.content[:100]}...")
    print("Note: Check ReliAPI logs/metrics to see cache hit!")
    print()


def example_with_idempotency():
    """Example showing idempotency protection."""
    print("=" * 60)
    print("Example 3: Idempotency - Prevent Duplicate Charges")
    print("=" * 60)
    
    llm = ChatOpenAI(
        base_url=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            # Use same idempotency key for both requests
            "X-Idempotency-Key": "langchain-example-123"
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    messages = [HumanMessage(content="What is retry logic?")]
    
    # Simulate user clicking button twice
    print("Request 1 (user clicks button):")
    response1 = llm.invoke(messages)
    print(f"Response: {response1.content[:100]}...")
    print()
    
    print("Request 2 (user clicks button again - same idempotency key):")
    response2 = llm.invoke(messages)
    print(f"Response: {response2.content[:100]}...")
    print("Note: Only ONE API call was made, even though we called invoke() twice!")
    print()


def example_streaming():
    """Example showing streaming with ReliAPI."""
    print("=" * 60)
    print("Example 4: Streaming Responses")
    print("=" * 60)
    
    llm = ChatOpenAI(
        base_url=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        streaming=True,
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    messages = [HumanMessage(content="Write a haiku about reliability.")]
    
    print("Streaming response:")
    for chunk in llm.stream(messages):
        if chunk.content:
            print(chunk.content, end="", flush=True)
    print("\n")


def example_chain():
    """Example showing LangChain chain with ReliAPI."""
    print("=" * 60)
    print("Example 5: LangChain Chain with ReliAPI")
    print("=" * 60)
    
    from langchain.chains import LLMChain
    from langchain.prompts import ChatPromptTemplate
    
    llm = ChatOpenAI(
        base_url=RELIAPI_BASE_URL,
        model="gpt-4o-mini",
        default_headers={
            "X-RapidAPI-Key": RAPIDAPI_KEY
        } if RAPIDAPI_KEY != "your-rapidapi-key-here" else {}
    )
    
    prompt = ChatPromptTemplate.from_template(
        "Translate the following {language} text to English: {text}"
    )
    
    chain = LLMChain(llm=llm, prompt=prompt)
    
    result = chain.run(language="Spanish", text="Hola, ¿cómo estás?")
    print(f"Translation: {result}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("ReliAPI + LangChain Integration Examples")
    print("=" * 60)
    print()
    
    # Run examples
    try:
        example_basic_chat()
        example_with_caching()
        example_with_idempotency()
        example_streaming()
        example_chain()
        
        print("=" * 60)
        print("All examples completed!")
        print("=" * 60)
        print()
        print("Benefits of using ReliAPI with LangChain:")
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
        print("  2. Installed dependencies: pip install langchain-openai")
        print("  3. ReliAPI is accessible at the configured base URL")














