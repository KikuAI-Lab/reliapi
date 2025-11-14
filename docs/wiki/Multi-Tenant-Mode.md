# Multi-Tenant Mode

Guide to using ReliAPI's multi-tenant features for isolating clients with separate configurations, budgets, and metrics.

## Table of Contents

- [Overview](#overview)
- [Configuration](#configuration)
- [API Usage](#api-usage)
- [Tenant Isolation](#tenant-isolation)
- [Monitoring](#monitoring)
- [Best Practices](#best-practices)

---

## Overview

Multi-tenant mode allows you to serve multiple clients from a single ReliAPI instance, with each tenant having:

- **Separate API keys** for authentication
- **Isolated cache** and idempotency namespaces
- **Independent budget caps** (soft and hard)
- **Separate fallback chains**
- **Per-tenant metrics** in Prometheus
- **Rate limiting** (optional, per tenant)

---

## Configuration

### Define Tenants

In your `config.yaml`:

```yaml
tenants:
  - name: "client-a"
    api_key: "sk-client-a-secret-key-123"
    budget_caps:
      soft_cost_cap_usd: 10.0
      hard_cost_cap_usd: 50.0
    fallback_targets:
      - "openai-secondary"
    rate_limit_rpm: 1000
    cache_ttl_override: 7200  # Optional: override default cache TTL

  - name: "client-b"
    api_key: "sk-client-b-secret-key-456"
    budget_caps:
      soft_cost_cap_usd: 5.0
      hard_cost_cap_usd: 20.0
    fallback_targets:
      - "anthropic-backup"
    rate_limit_rpm: 500

targets:
  openai-primary:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai
      model: gpt-4

  openai-secondary:
    base_url: https://api.openai.com/v1
    llm:
      provider: openai
      model: gpt-3.5-turbo

  anthropic-backup:
    base_url: https://api.anthropic.com/v1
    llm:
      provider: anthropic
      model: claude-3-opus
```

### Global API Key (Backward Compatibility)

If no tenant matches the API key, ReliAPI falls back to a global API key:

```bash
export RELIAPI_API_KEY=global-api-key
```

This allows backward compatibility with single-tenant deployments.

---

## API Usage

### Authenticate with Tenant API Key

Simply use the tenant's API key in the `X-API-Key` header:

```bash
curl -X POST https://reliapi.example.com/proxy/llm \
  -H "X-API-Key: sk-client-a-secret-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "target": "openai-primary",
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "gpt-4"
  }'
```

### Python Example

```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "https://reliapi.example.com/proxy/llm",
        headers={
            "X-API-Key": "sk-client-a-secret-key-123",  # Tenant API key
            "Content-Type": "application/json"
        },
        json={
            "target": "openai-primary",
            "messages": [{"role": "user", "content": "Hello"}],
            "model": "gpt-4"
        }
    )
    result = response.json()
    # Tenant is automatically detected from API key
```

---

## Tenant Isolation

### Cache Isolation

Each tenant has a separate cache namespace. Cache keys are prefixed with `tenant:{tenant_name}:`:

```
tenant:client-a:cache:GET:https://api.example.com/users
tenant:client-b:cache:GET:https://api.example.com/users
```

This ensures:
- ✅ Client A's cached responses are not visible to Client B
- ✅ Cache hits are isolated per tenant
- ✅ Cache TTL can be overridden per tenant

### Idempotency Isolation

Idempotency keys are also isolated per tenant:

```
tenant:client-a:idempotency:req-123
tenant:client-b:idempotency:req-123
```

This means:
- ✅ Same `idempotency_key` can be used by different tenants without conflicts
- ✅ Idempotent hits are isolated per tenant
- ✅ Request coalescing works per tenant

### Budget Caps

Each tenant has independent budget caps:

```yaml
tenants:
  - name: "client-a"
    budget_caps:
      soft_cost_cap_usd: 10.0   # Client A's soft cap
      hard_cost_cap_usd: 50.0    # Client A's hard cap

  - name: "client-b"
    budget_caps:
      soft_cost_cap_usd: 5.0     # Client B's soft cap (different!)
      hard_cost_cap_usd: 20.0    # Client B's hard cap (different!)
```

If Client A exceeds their hard cap, Client B is unaffected.

### Fallback Chains

Each tenant can have different fallback targets:

```yaml
tenants:
  - name: "client-a"
    fallback_targets: ["openai-secondary", "anthropic-backup"]

  - name: "client-b"
    fallback_targets: ["anthropic-backup"]  # Different fallback chain
```

---

## Monitoring

### Prometheus Metrics

All metrics include a `tenant` label:

```promql
# Requests per tenant
reliapi_requests_total{tenant="client-a"}

# Error rate per tenant
rate(reliapi_errors_total{tenant="client-a"}[5m])

# Cost per tenant
reliapi_llm_cost_usd_total{tenant="client-a"}

# Cache hit rate per tenant
rate(reliapi_cache_hits_total{tenant="client-a"}[5m]) /
  (rate(reliapi_cache_hits_total{tenant="client-a"}[5m]) +
   rate(reliapi_cache_misses_total{tenant="client-a"}[5m]))
```

### Structured Logging

Logs include `tenant` field:

```json
{
  "ts": "2025-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "abc123",
  "tenant": "client-a",
  "target": "openai-primary",
  "kind": "llm",
  "outcome": "success",
  "latency_ms": 1250,
  "cost_usd": 0.003
}
```

### Grafana Dashboards

Filter dashboards by tenant:

```
tenant="client-a"
```

Or compare tenants:

```
tenant=~"client-.*"
```

---

## Best Practices

### 1. Secure API Keys

- Use strong, unique API keys for each tenant
- Store keys securely (environment variables, secrets manager)
- Rotate keys periodically

### 2. Set Appropriate Budget Caps

- Start with conservative hard caps
- Monitor actual usage and adjust
- Use soft caps to allow flexibility while controlling costs

### 3. Monitor Per-Tenant Metrics

- Set up alerts for high error rates per tenant
- Track cost per tenant to identify heavy users
- Monitor cache hit rates to optimize TTL

### 4. Use Tenant-Specific Fallbacks

- Configure fallback chains based on tenant needs
- Premium tenants might have more fallback options
- Test fallback chains for each tenant

### 5. Rate Limiting

- Set `rate_limit_rpm` based on tenant tier
- Monitor rate limit hits in metrics
- Adjust limits based on actual usage patterns

### 6. Cache TTL Overrides

- Use `cache_ttl_override` for tenants with specific caching needs
- Longer TTL for stable data, shorter for dynamic data
- Monitor cache hit rates to optimize

---

## Example: SaaS Use Case

```yaml
tenants:
  # Free tier
  - name: "free-user-123"
    api_key: "sk-free-..."
    budget_caps:
      soft_cost_cap_usd: 1.0
      hard_cost_cap_usd: 5.0
    rate_limit_rpm: 100
    fallback_targets: []  # No fallback for free tier

  # Pro tier
  - name: "pro-user-456"
    api_key: "sk-pro-..."
    budget_caps:
      soft_cost_cap_usd: 50.0
      hard_cost_cap_usd: 200.0
    rate_limit_rpm: 5000
    fallback_targets: ["openai-secondary", "anthropic-backup"]

  # Enterprise tier
  - name: "enterprise-789"
    api_key: "sk-enterprise-..."
    budget_caps:
      soft_cost_cap_usd: 500.0
      hard_cost_cap_usd: 2000.0
    rate_limit_rpm: 50000
    fallback_targets: ["openai-secondary", "anthropic-backup", "mistral-backup"]
    cache_ttl_override: 86400  # 24 hours
```

---

## Next Steps

- [Configuration](Configuration) — Full configuration reference
- [Usage Guides](Usage-Guides) — How to use ReliAPI features
- [Observability](Observability) — Monitoring and metrics

