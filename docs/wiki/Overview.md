# Overview

## What is ReliAPI?

ReliAPI is a small reliability layer for **any HTTP API** — REST services, internal microservices, and LLM calls. It provides retries, circuit breaker, cache, idempotency, and predictable cost controls in a single, self-hostable gateway.

**ReliAPI is not limited to LLM calls.**

It can sit in front of *any* HTTP-based API — payment services, SaaS APIs, internal microservices — and apply the same retry, circuit breaker, cache, idempotency, and error handling policies in a uniform way.

---

## When You Need ReliAPI

Use ReliAPI when you need:

### Reliability

- **Retries**: Automatic retries with exponential backoff for transient failures
- **Circuit Breaker**: Per-target failure detection and automatic cooldown
- **Fallback Chains**: Automatic failover to backup targets when primary fails

### Predictability

- **Unified Errors**: Normalized error format (no raw stacktraces)
- **Budget Caps**: Hard cap (reject) and soft cap (throttle) for LLM costs
- **Cost Estimation**: Pre-call cost estimation with policy application

### Performance

- **Caching**: TTL cache for GET/HEAD and LLM requests
- **Idempotency**: Request coalescing for concurrent identical requests
- **Low Overhead**: Minimal latency addition (< 10ms typical)

### Observability

- **Prometheus Metrics**: Request counts, latency, errors, cache hits, costs
- **Structured Logging**: JSON logs with request IDs
- **Health Endpoints**: `/healthz` for monitoring

---

## When You Don't Need ReliAPI

You probably don't need ReliAPI if:

- **Simple direct calls**: You're making simple HTTP calls without retry/cache needs
- **No SLA requirements**: You don't need guaranteed retries or circuit breaker behavior
- **No budget concerns**: LLM costs are not a concern and you don't need cost caps
- **Single provider**: You're only using one LLM provider and don't need abstraction
- **No idempotency needs**: You don't need request coalescing or duplicate prevention

---

## Typical Deployment

ReliAPI is typically deployed:

### In Front of External APIs

- **LLM Providers**: OpenAI, Anthropic, Mistral
- **Payment Services**: Stripe, PayPal, payment gateways
- **SaaS APIs**: External REST APIs with rate limits

### In Front of Internal Microservices

- **Service Mesh**: Reliability layer for internal HTTP services
- **API Gateway**: Single point for retry, cache, and error handling

### As a Sidecar

- **Container Sidecar**: Deployed alongside application containers
- **Kubernetes**: As a sidecar container in pods

---

## Architecture Overview

```
Client → ReliAPI → Target (HTTP/LLM)
         ↓
    [Retry] → [Circuit Breaker] → [Cache] → [Idempotency] → [Upstream]
         ↓
    [Normalize] → [Response Envelope]
```

ReliAPI sits between your application and upstream APIs, applying reliability layers uniformly.

---

## Key Concepts

### Targets

A **target** is an upstream API endpoint configured in `config.yaml`. Each target has:

- `base_url`: Upstream API base URL
- `timeout_ms`: Request timeout
- `circuit`: Circuit breaker configuration
- `cache`: Cache configuration
- `auth`: Authentication configuration
- `llm`: LLM-specific configuration (if applicable)

### Reliability Layers

1. **Retries**: Automatic retries with exponential backoff
2. **Circuit Breaker**: Per-target failure detection
3. **Cache**: TTL cache for GET/HEAD and LLM requests
4. **Idempotency**: Request coalescing for duplicate requests
5. **Budget Caps**: Cost control for LLM requests

### Response Format

All responses follow a unified format:

```json
{
  "success": true,
  "data": {...},
  "meta": {
    "target": "openai",
    "cache_hit": false,
    "idempotent_hit": false,
    "retries": 0,
    "duration_ms": 150,
    "cost_usd": 0.001
  }
}
```

---

## Next Steps

- [Architecture](Architecture.md) — Detailed architecture overview
- [Configuration](Configuration.md) — Configuration guide
- [Reliability Features](Reliability-Features.md) — Detailed feature explanations
- [Comparison](Comparison.md) — Comparison with other tools

