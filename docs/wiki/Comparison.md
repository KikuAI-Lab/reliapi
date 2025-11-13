# Comparison

Comparison of ReliAPI with other reliability and LLM gateway tools.

---

## Overview

| Feature | ReliAPI | LiteLLM | Portkey | Helicone |
|---------|---------|---------|---------|----------|
| **Self-hosted** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No (SaaS) |
| **Open Source** | ✅ MIT | ✅ MIT | ✅ MIT | ❌ Proprietary |
| **HTTP Proxy** | ✅ Universal | ❌ LLM only | ❌ LLM only | ❌ LLM only |
| **LLM Proxy** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Idempotency** | ✅ First-class | ❌ No | ⚠️ Limited | ❌ No |
| **Budget Caps** | ✅ Hard + Soft | ⚠️ Basic | ✅ Yes | ✅ Yes |
| **Caching** | ✅ TTL cache | ✅ Yes | ✅ Yes | ✅ Yes |
| **Retries** | ✅ Configurable | ✅ Yes | ✅ Yes | ✅ Yes |
| **Circuit Breaker** | ✅ Per-target | ⚠️ Basic | ✅ Yes | ✅ Yes |
| **Fallback Chains** | ✅ Config-driven | ✅ Yes | ✅ Yes | ✅ Yes |
| **Streaming** | ❌ Not yet | ✅ Yes | ✅ Yes | ✅ Yes |
| **Observability** | ✅ Prometheus | ✅ Yes | ✅ Yes | ✅ Yes |
| **Minimal** | ✅ ~2K LOC | ❌ Large | ❌ Large | ❌ Large |
| **Docker Ready** | ✅ Yes | ✅ Yes | ✅ Yes | N/A |

---

## LiteLLM

### Where LiteLLM is Strong

- **Comprehensive LLM Support**: Supports many LLM providers
- **Streaming**: Full streaming support
- **Prompt Management**: Built-in prompt management features
- **Active Development**: Very active community and development

### Where ReliAPI is Different

- **HTTP Support**: ReliAPI supports any HTTP API, not just LLMs
- **Idempotency**: ReliAPI has first-class idempotency with coalescing
- **Minimal**: ReliAPI is much smaller (~2K LOC vs large codebase)
- **Budget Control**: ReliAPI has hard/soft caps with throttling

### When to Choose LiteLLM

- Need comprehensive LLM provider abstraction
- Need streaming support
- Need prompt management features
- Don't need HTTP proxy capabilities

### When to Choose ReliAPI

- Need HTTP + LLM proxy in one gateway
- Need first-class idempotency
- Need predictable budget control
- Prefer minimal, self-hostable solution

---

## Portkey

### Where Portkey is Strong

- **Observability**: Excellent observability dashboards
- **Budget Controls**: Good budget control features
- **Fallback Chains**: Strong fallback chain support
- **Enterprise Features**: Multi-tenant and enterprise features

### Where ReliAPI is Different

- **HTTP Support**: ReliAPI supports any HTTP API, not just LLMs
- **Idempotency**: ReliAPI has first-class idempotency with coalescing
- **Minimal**: ReliAPI is much smaller and simpler
- **Self-Hosted Focus**: ReliAPI is designed for self-hosting

### When to Choose Portkey

- Need advanced observability dashboards
- Need multi-tenant features
- Need enterprise support
- Don't need HTTP proxy capabilities

### When to Choose ReliAPI

- Need HTTP + LLM proxy in one gateway
- Need first-class idempotency
- Prefer minimal, self-hostable solution
- Don't need advanced dashboards

---

## Helicone

### Where Helicone is Strong

- **Observability**: Excellent observability and analytics
- **SaaS**: Easy setup, no self-hosting needed
- **Request Logging**: Comprehensive request/response logging
- **Analytics**: Advanced analytics and insights

### Where ReliAPI is Different

- **Self-Hosted**: ReliAPI is fully self-hostable
- **HTTP Support**: ReliAPI supports any HTTP API, not just LLMs
- **Idempotency**: ReliAPI has first-class idempotency
- **Open Source**: ReliAPI is open source (MIT)

### When to Choose Helicone

- Want SaaS observability (no self-hosting)
- Need advanced analytics
- Need request/response logging
- Don't need HTTP proxy capabilities

### When to Choose ReliAPI

- Need self-hosted solution
- Need HTTP + LLM proxy in one gateway
- Need first-class idempotency
- Prefer open source solution

---

## Key Differentiators

### ReliAPI's Unique Strengths

1. **Universal HTTP Proxy**: Works for any HTTP API, not just LLMs
2. **First-Class Idempotency**: Request coalescing with conflict detection
3. **Predictable Budget Control**: Hard/soft caps with throttling
4. **Minimal**: Small codebase (~2K LOC), easy to understand and maintain
5. **Self-Hosted Focus**: Designed for self-hosting, no external dependencies

### ReliAPI's Limitations

1. **No Streaming**: Streaming not supported yet (planned)
2. **No Dashboards**: Prometheus metrics only, no built-in dashboards
3. **No Multi-Tenant**: Single-tenant only
4. **Limited Providers**: Supports OpenAI, Anthropic, Mistral (expandable)

---

## Performance Comparison

*Note: Performance comparisons are approximate and depend on setup. These are not guarantees.*

| Metric | ReliAPI | LiteLLM | Portkey | Helicone |
|--------|---------|---------|---------|----------|
| **Overhead (p50)** | ~5ms | ~10ms | ~8ms | ~15ms |
| **Overhead (p95)** | ~15ms | ~30ms | ~25ms | ~40ms |
| **Memory (idle)** | ~50MB | ~150MB | ~120MB | N/A |
| **Memory (100 RPS)** | ~100MB | ~300MB | ~250MB | N/A |

*These are synthetic examples based on typical deployments. Actual performance depends on workload, hardware, and configuration.*

---

## Use Case Matrix

| Use Case | ReliAPI | LiteLLM | Portkey | Helicone |
|----------|---------|---------|---------|----------|
| **Self-hosted LLM proxy** | ✅ | ✅ | ✅ | ❌ |
| **HTTP API reliability** | ✅ | ❌ | ❌ | ❌ |
| **Idempotent LLM calls** | ✅ | ❌ | ⚠️ | ❌ |
| **Predictable costs** | ✅ | ⚠️ | ✅ | ✅ |
| **Minimal overhead** | ✅ | ⚠️ | ⚠️ | ⚠️ |
| **Streaming support** | ❌ | ✅ | ✅ | ✅ |
| **Observability dashboards** | ❌ | ⚠️ | ✅ | ✅ |
| **Multi-tenant** | ❌ | ⚠️ | ✅ | ✅ |

---

## Summary

ReliAPI is best for teams that need:

- **Universal HTTP + LLM proxy** in one gateway
- **First-class idempotency** with coalescing
- **Predictable budget control** with hard/soft caps
- **Minimal, self-hostable** solution
- **Simple configuration** and low overhead

Choose alternatives if you need:

- **Streaming support** (LiteLLM, Portkey)
- **Advanced dashboards** (Portkey, Helicone)
- **Multi-tenant features** (Portkey)
- **SaaS observability** (Helicone)

---

## Next Steps

- [Overview](Overview.md) — ReliAPI overview
- [Architecture](Architecture.md) — Architecture details

