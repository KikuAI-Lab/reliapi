# ReliAPI Wiki

Welcome to the ReliAPI Wiki — your guide to building reliable HTTP and LLM API integrations.

## Quick Links

- [Overview](Overview) — What is ReliAPI and when to use it
- [Architecture](Architecture) — How ReliAPI works internally
- [Configuration](Configuration) — Configuring targets and policies
- [Reliability Features](Reliability-Features) — Detailed feature explanations
- [Usage Guides](Usage-Guides) — HTTP, LLM, Streaming, Idempotency, Budgets, Fallback
- [Multi-Tenant Mode](Multi-Tenant-Mode) — Multi-tenant isolation and configuration
- [Deploy Guide](Deploy-Guide) — Production deployment on Hetzner
- [Performance & Load Testing](Performance-Load-Testing) — k6 testing and benchmarks
- [Developer Guide](Developer-Guide) — Contributing to ReliAPI
- [Comparison](Comparison) — Comparison with other tools

## Getting Started

ReliAPI is a small reliability layer for **ANY HTTP API and ANY LLM API** — REST services, internal microservices, payment gateways, SaaS APIs, and LLM providers.

**Quick start:**

```bash
docker run -d \
  -p 8000:8000 \
  -e REDIS_URL=redis://localhost:6379/0 \
  -v $(pwd)/config.yaml:/app/config.yaml \
  reliapi/reliapi:latest
```

## Documentation

- [How to make your LLM API idempotent](guides/idempotency)
- [How to keep AI costs predictable using budget caps](guides/budget-control)
- [Self-hosted LLM reliability layer in one Docker container](guides/docker)

## Examples

- [HTTP Proxy Example](examples/http-proxy)
- [LLM Proxy Example](examples/llm-proxy)
- [Configuration Examples](examples/configuration)

---

**ReliAPI** — Reliability layer for HTTP and LLM calls. Simple, predictable, stable.

