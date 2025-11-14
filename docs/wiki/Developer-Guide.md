# Developer Guide

Guide for contributing to ReliAPI: coding style, architecture, and development workflow.

## Table of Contents

- [Getting Started](#getting-started)
- [Coding Style](#coding-style)
- [Architecture Overview](#architecture-overview)
- [Adding Adapters](#adding-adapters)
- [Cost Estimator](#cost-estimator)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

---

## Getting Started

### Clone Repository

```bash
git clone https://github.com/KikuAI-Lab/reliapi.git
cd reliapi
```

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black mypy
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=reliapi --cov-report=html

# Run specific test file
pytest tests/test_cache.py
```

### Run Locally

```bash
# Start Redis
docker run -d -p 6379:6379 redis:7-alpine

# Set environment variables
export REDIS_URL=redis://localhost:6379/0
export RELIAPI_CONFIG_PATH=config.yaml
export OPENAI_API_KEY=sk-...

# Run ReliAPI
uvicorn reliapi.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## Coding Style

### Python Style Guide

ReliAPI follows PEP 8 with some modifications:

- **Line length**: 100 characters (not 79)
- **Type hints**: Required for all function signatures
- **Docstrings**: Google style for public APIs
- **Imports**: Grouped (stdlib, third-party, local)

### Code Formatting

```bash
# Format code
black reliapi/

# Check types
mypy reliapi/

# Lint
flake8 reliapi/
```

### Example Function

```python
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def process_request(
    target_name: str,
    payload: Dict[str, Any],
    tenant: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Process a request to the specified target.
    
    Args:
        target_name: Name of the target from config
        payload: Request payload
        tenant: Optional tenant identifier for multi-tenant isolation
        
    Returns:
        Processed response dictionary
        
    Raises:
        ValueError: If target_name is invalid
    """
    if not target_name:
        raise ValueError("target_name is required")
    
    logger.info(f"Processing request for target: {target_name}")
    # ... implementation
    return {"success": True}
```

### Error Handling

- Use custom error classes from `reliapi.core.errors`
- Always log errors with context
- Return structured error responses

```python
from reliapi.core.errors import ErrorCode

try:
    result = await upstream_call()
except httpx.HTTPStatusError as e:
    logger.warning(
        f"Upstream error: {e.response.status_code}",
        extra={"target": target_name, "status": e.response.status_code}
    )
    return ErrorResponse(
        error=ErrorResponseData(
            code=ErrorCode.from_http_status(e.response.status_code).value,
            message=f"Upstream error: {e.response.status_code}",
            retryable=e.response.status_code >= 500,
        )
    )
```

---

## Architecture Overview

### Core Components

1. **API Layer** (`reliapi/app/main.py`): FastAPI endpoints
2. **Service Layer** (`reliapi/app/services.py`): Business logic
3. **Core Components** (`reliapi/core/`):
   - `cache.py`: Redis-based caching
   - `idempotency.py`: Idempotency management
   - `circuit_breaker.py`: Circuit breaker pattern
   - `retry.py`: Retry logic
   - `http_client.py`: HTTP client wrapper
4. **Adapters** (`reliapi/adapters/`):
   - `llm/`: LLM provider adapters
   - `http_generic/`: Generic HTTP adapter

### Request Flow

```
Client Request
    ↓
FastAPI Endpoint (main.py)
    ↓
Service Handler (services.py)
    ↓
Cache Check → Idempotency Check
    ↓
Circuit Breaker Check
    ↓
Adapter (llm/openai.py or http_generic/service.py)
    ↓
Upstream API
    ↓
Response Processing
    ↓
Cache Store → Idempotency Store
    ↓
Client Response
```

---

## Adding Adapters

### LLM Adapter

Create a new file in `reliapi/adapters/llm/`:

```python
from typing import Dict, Any, Optional, AsyncIterator
from reliapi.adapters.llm.base import LLMAdapter

class MyLLMAdapter(LLMAdapter):
    """Adapter for MyLLM provider."""
    
    def supports_streaming(self) -> bool:
        return False  # or True if provider supports streaming
    
    def prepare_request(
        self,
        messages: list,
        model: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """Prepare request payload for MyLLM API."""
        payload = {
            "messages": messages,
            "model": model,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if stream:
            payload["stream"] = True
        return payload
    
    async def chat(
        self,
        client: Any,
        payload: Dict[str, Any],
        base_url: str,
        api_key: Optional[str],
    ) -> Dict[str, Any]:
        """Make chat completion request."""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = await client.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response.json()
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse MyLLM response to standard format."""
        choices = response.get("choices", [])
        if not choices:
            raise ValueError("No choices in response")
        
        return {
            "content": choices[0]["message"]["content"],
            "role": "assistant",
            "finish_reason": choices[0].get("finish_reason", "stop"),
        }
    
    def get_usage(self, response: Dict[str, Any]) -> Dict[str, int]:
        """Extract token usage from response."""
        usage = response.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }
    
    def get_cost_usd(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> Optional[float]:
        """Calculate cost in USD."""
        # Implement pricing logic
        pricing = {
            "my-model": {"prompt": 0.001, "completion": 0.002},
        }
        if model not in pricing:
            return None
        
        cost = (
            prompt_tokens / 1000 * pricing[model]["prompt"] +
            completion_tokens / 1000 * pricing[model]["completion"]
        )
        return cost
    
    async def stream_chat(
        self,
        client: Any,
        payload: Dict[str, Any],
        base_url: str,
        api_key: Optional[str],
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream chat completion (if supported)."""
        if not self.supports_streaming():
            raise NotImplementedError("Streaming not supported")
        # Implement streaming logic
        raise NotImplementedError("Streaming not yet implemented")
```

Register in `reliapi/adapters/llm/factory.py`:

```python
from reliapi.adapters.llm.my_llm import MyLLMAdapter

def create_adapter(provider: str) -> LLMAdapter:
    if provider == "myllm":
        return MyLLMAdapter()
    # ... existing adapters
```

---

## Cost Estimator

### Adding Pricing Data

Update `reliapi/core/cost_estimator.py`:

```python
# Pricing data (per 1K tokens)
PRICING = {
    "myllm": {
        "my-model-v1": {
            "prompt": 0.001,      # $0.001 per 1K prompt tokens
            "completion": 0.002,  # $0.002 per 1K completion tokens
        },
    },
}
```

### Estimation Logic

```python
@staticmethod
def estimate_from_messages(
    provider: str,
    model: str,
    messages: list,
    max_tokens: Optional[int] = None,
) -> Optional[float]:
    """Estimate cost from messages and max_tokens."""
    if provider not in PRICING or model not in PRICING[provider]:
        return None
    
    # Estimate prompt tokens (rough: 4 chars per token)
    prompt_text = " ".join(m.get("content", "") for m in messages)
    estimated_prompt_tokens = len(prompt_text) // 4
    
    # Use max_tokens or default
    estimated_completion_tokens = max_tokens or 1000
    
    pricing = PRICING[provider][model]
    cost = (
        estimated_prompt_tokens / 1000 * pricing["prompt"] +
        estimated_completion_tokens / 1000 * pricing["completion"]
    )
    return cost
```

---

## Testing

### Unit Tests

Create test file in `reliapi/tests/`:

```python
import pytest
from reliapi.adapters.llm.my_llm import MyLLMAdapter

@pytest.fixture
def adapter():
    return MyLLMAdapter()

@pytest.mark.asyncio
async def test_prepare_request(adapter):
    payload = adapter.prepare_request(
        messages=[{"role": "user", "content": "Hello"}],
        model="my-model-v1",
        max_tokens=100,
    )
    assert payload["model"] == "my-model-v1"
    assert payload["max_tokens"] == 100

def test_get_cost_usd(adapter):
    cost = adapter.get_cost_usd("my-model-v1", 1000, 500)
    assert cost == 0.002  # (1000 * 0.001 + 500 * 0.002) / 1000
```

### Integration Tests

Test with real API (use test API keys):

```python
@pytest.mark.asyncio
async def test_real_api_call(adapter):
    import httpx
    client = httpx.AsyncClient()
    
    payload = adapter.prepare_request(
        messages=[{"role": "user", "content": "Test"}],
        model="my-model-v1",
    )
    
    response = await adapter.chat(
        client,
        payload,
        base_url="https://api.myllm.com/v1",
        api_key=os.getenv("MYLLM_API_KEY"),
    )
    
    assert "content" in adapter.parse_response(response)
    await client.aclose()
```

---

## Pull Request Process

### Before Submitting

1. ✅ Run tests: `pytest`
2. ✅ Format code: `black reliapi/`
3. ✅ Check types: `mypy reliapi/`
4. ✅ Update documentation if needed
5. ✅ Add tests for new features

### PR Checklist

- [ ] Code follows style guide
- [ ] Tests pass
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Changelog updated (if applicable)

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: Add MyLLM adapter support
fix: Correct cost estimation for GPT-4
docs: Update deployment guide
test: Add unit tests for cache isolation
```

---

## Next Steps

- [Architecture](Architecture) — Deep dive into architecture
- [Configuration](Configuration) — Configuration reference
- [Usage Guides](Usage-Guides) — User documentation

