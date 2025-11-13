# How to keep AI costs predictable using budget caps

**Budget caps prevent unexpected LLM costs by rejecting or throttling expensive requests.**

---

## Problem

LLM API costs can be unpredictable:

- **Long responses**: High `max_tokens` = high cost
- **Expensive models**: GPT-4 costs 10x more than GPT-4o-mini
- **Unexpected usage**: Bugs or attacks can cause cost spikes
- **No visibility**: Costs accumulate without warning

---

## Solution: ReliAPI Budget Caps

ReliAPI provides **two types of budget caps**:

1. **Hard cap**: Rejects requests exceeding budget
2. **Soft cap**: Throttles requests by reducing `max_tokens`

---

## Quick Start

### 1. Configure Budget Caps

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      soft_cost_cap_usd: 0.01    # Throttle if exceeded
      hard_cost_cap_usd: 0.05    # Reject if exceeded
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

### 2. Make Request

```bash
curl -X POST http://localhost:8000/proxy/llm \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 2000
  }'
```

### 3. Check Response

If soft cap exceeded, response includes:

```json
{
  "success": true,
  "data": {...},
  "meta": {
    "cost_estimate_usd": 0.012,
    "cost_policy_applied": "soft_cap_throttled",
    "max_tokens_reduced": true,
    "original_max_tokens": 2000
  }
}
```

---

## How It Works

### 1. Pre-Call Cost Estimation

ReliAPI estimates cost before making request:

```python
cost_estimate = estimate_cost(
    provider="openai",
    model="gpt-4o-mini",
    messages=[...],
    max_tokens=2000
)
# Returns: 0.012 USD
```

### 2. Hard Cap Check

If estimated cost > hard cap:

```json
{
  "success": false,
  "error": {
    "type": "budget_error",
    "code": "BUDGET_EXCEEDED",
    "message": "Estimated cost $0.012 exceeds hard cap $0.05",
    "details": {
      "cost_estimate_usd": 0.012,
      "hard_cost_cap_usd": 0.05,
      "model": "gpt-4o-mini",
      "max_tokens": 2000
    }
  }
}
```

### 3. Soft Cap Check

If estimated cost > soft cap:

1. Calculate reduction factor: `soft_cap / estimated_cost`
2. Reduce `max_tokens`: `max_tokens * reduction_factor * 0.9`
3. Re-estimate cost with reduced tokens
4. Proceed with reduced `max_tokens`

Response includes:

```json
{
  "meta": {
    "cost_policy_applied": "soft_cap_throttled",
    "max_tokens_reduced": true,
    "original_max_tokens": 2000
  }
}
```

---

## Best Practices

### 1. Set Realistic Caps

Match caps to use case:

```yaml
# Development
soft_cost_cap_usd: 0.01
hard_cost_cap_usd: 0.05

# Production
soft_cost_cap_usd: 0.10
hard_cost_cap_usd: 0.50
```

### 2. Monitor Cost Metrics

Use Prometheus metrics:

```bash
curl http://localhost:8000/metrics | grep reliapi_llm_cost_usd
```

### 3. Handle Throttling

Check `max_tokens_reduced` in response:

```python
response = requests.post(...)
meta = response.json()["meta"]

if meta.get("max_tokens_reduced"):
    print(f"Warning: max_tokens reduced from {meta['original_max_tokens']} to fit budget")
    # Adjust client expectations
```

### 4. Use Different Caps Per Model

```yaml
targets:
  openai_cheap:
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      soft_cost_cap_usd: 0.01
      hard_cost_cap_usd: 0.05
  
  openai_expensive:
    llm:
      provider: "openai"
      default_model: "gpt-4"
      soft_cost_cap_usd: 0.10
      hard_cost_cap_usd: 0.50
```

---

## Examples

### Example 1: Basic Budget Control

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      soft_cost_cap_usd: 0.01
      hard_cost_cap_usd: 0.05
```

### Example 2: Per-Model Caps

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
      # Model-specific caps via request
```

Handle in application:

```python
def make_request(model: str, max_tokens: int):
    # Select target based on model
    target = "openai_cheap" if model == "gpt-4o-mini" else "openai_expensive"
    
    response = requests.post(
        "http://localhost:8000/proxy/llm",
        json={
            "target": target,
            "model": model,
            "max_tokens": max_tokens,
            "messages": [...]
        }
    )
    return response.json()
```

### Example 3: Monitoring Costs

```python
import requests
from prometheus_client.parser import text_string_to_metric_families

def get_cost_metrics():
    response = requests.get("http://localhost:8000/metrics")
    metrics = text_string_to_metric_families(response.text)
    
    for metric in metrics:
        if metric.name == "reliapi_llm_cost_usd":
            for sample in metric.samples:
                print(f"{sample.labels}: {sample.value} USD")
```

---

## Cost Estimation

ReliAPI uses approximate pricing:

| Provider | Model | Input ($/1M tokens) | Output ($/1M tokens) |
|----------|-------|---------------------|---------------------|
| OpenAI | gpt-4o-mini | 0.15 | 0.60 |
| OpenAI | gpt-4 | 30.00 | 60.00 |
| Anthropic | claude-3-haiku | 0.25 | 1.25 |
| Anthropic | claude-3-opus | 15.00 | 75.00 |

*Prices are approximate and may vary. Check provider pricing for exact rates.*

---

## Limitations

1. **Estimation accuracy**: Costs are estimated, not exact
2. **Model-specific**: Pricing varies by model
3. **Token counting**: Approximate token counts used
4. **No per-user caps**: Caps are per-target, not per-user

---

## Benefits

### 1. Cost Predictability

- **Hard cap**: Prevents unexpected costs
- **Soft cap**: Throttles expensive requests
- **Visibility**: Cost estimates in response

### 2. Protection

- **Bug protection**: Prevents cost spikes from bugs
- **Attack protection**: Limits damage from abuse
- **Budget compliance**: Ensures costs stay within budget

### 3. Flexibility

- **Configurable**: Set caps per target
- **Transparent**: Clients see when throttling occurs
- **Adjustable**: Change caps without code changes

---

## Summary

ReliAPI budget caps provide:

- ✅ **Hard cap**: Reject expensive requests
- ✅ **Soft cap**: Throttle by reducing `max_tokens`
- ✅ **Cost estimation**: Pre-call cost estimates
- ✅ **Transparency**: Clients see when throttling occurs
- ✅ **Protection**: Prevent unexpected cost spikes

**Use budget caps to keep AI costs predictable and within budget.**

