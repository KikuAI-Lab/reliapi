# Architecture

## High-Level Overview

ReliAPI is a minimal reliability layer that sits between clients and upstream APIs (HTTP or LLM providers).

```
┌─────────┐
│ Client  │
└────┬────┘
     │ HTTP Request
     ↓
┌─────────────────────────────────────────┐
│           ReliAPI Gateway               │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Request Routing                │  │
│  │   (HTTP / LLM)                   │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Idempotency Check               │  │
│  │   (coalesce concurrent requests) │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Cache Check                    │  │
│  │   (GET/HEAD, LLM responses)     │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Circuit Breaker               │  │
│  │   (per-target failure detection)│  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Budget Control (LLM only)       │  │
│  │   (cost estimation, caps)        │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Retry Logic                    │  │
│  │   (exponential backoff)         │  │
│  └───────────┬──────────────────────┘  │
└──────────────┼──────────────────────────┘
               │ Upstream Request
               ↓
         ┌──────────┐
         │  Target  │
         │  (HTTP/  │
         │   LLM)   │
         └────┬─────┘
              │ Response
              ↓
┌─────────────────────────────────────────┐
│           ReliAPI Gateway               │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │   Response Normalization         │  │
│  │   (unified error format)        │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Cache Store                    │  │
│  │   (if cacheable)                 │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Idempotency Store              │  │
│  │   (if idempotency_key present)   │  │
│  └───────────┬──────────────────────┘  │
│              ↓                          │
│  ┌──────────────────────────────────┐  │
│  │   Metrics Export                 │  │
│  │   (Prometheus)                   │  │
│  └───────────┬──────────────────────┘  │
└──────────────┼──────────────────────────┘
               │ Response Envelope
               ↓
         ┌─────────┐
         │ Client  │
         └─────────┘
```

---

## Components

### HTTP Proxy Path

For generic HTTP API requests (`POST /proxy/http`):

1. **Request Parsing**: Extract target, method, path, headers, query, body
2. **Target Resolution**: Load target config from `config.yaml`
3. **Idempotency Check**: Check if request with same `idempotency_key` exists
4. **Cache Check**: For GET/HEAD, check cache
5. **Circuit Breaker**: Check if target circuit is open
6. **HTTP Client**: Create HTTP client with retry logic
7. **Upstream Request**: Make request to upstream API
8. **Response Normalization**: Convert to unified response format
9. **Cache Store**: Store response if cacheable
10. **Idempotency Store**: Store result if `idempotency_key` present
11. **Metrics**: Export Prometheus metrics

### LLM Proxy Path

For LLM API requests (`POST /proxy/llm`):

1. **Request Parsing**: Extract target, messages, model, parameters
2. **Target Resolution**: Load target config with LLM settings
3. **Streaming Rejection**: Reject streaming requests (not supported yet)
4. **Budget Control**: Estimate cost, check hard/soft caps
5. **Idempotency Check**: Check if request with same `idempotency_key` exists
6. **Cache Check**: Check cache for LLM response
7. **Circuit Breaker**: Check if target circuit is open
8. **Adapter Selection**: Select provider adapter (OpenAI, Anthropic, Mistral)
9. **Request Preparation**: Convert generic request to provider-specific format
10. **Upstream Request**: Make request to LLM provider
11. **Response Parsing**: Parse provider response to normalized format
12. **Cost Calculation**: Calculate actual cost
13. **Response Normalization**: Convert to unified response format
14. **Cache Store**: Store response if cacheable
15. **Idempotency Store**: Store result if `idempotency_key` present
16. **Metrics**: Export Prometheus metrics

---

## Core Components

### Retry Logic

- **Error Classification**: 429 (rate limit), 5xx (server error), network errors
- **Backoff Strategy**: Exponential backoff with jitter
- **Configurable**: Per-target retry matrix in `config.yaml`

### Circuit Breaker

- **Per-Target**: Each target has its own circuit breaker
- **Failure Threshold**: Opens after N consecutive failures
- **Cooldown Period**: Stays open for configured duration
- **Half-Open State**: Allows test requests after cooldown

### Cache

- **HTTP**: GET/HEAD requests cached by default
- **LLM**: POST requests cached if enabled
- **TTL-Based**: Configurable TTL per target
- **Redis-Backed**: Uses Redis for storage

### Idempotency

- **Key-Based**: Uses `Idempotency-Key` header or `idempotency_key` field
- **Coalescing**: Concurrent requests with same key execute once
- **Conflict Detection**: Different request bodies with same key return error
- **TTL-Bound**: Results cached for configured TTL

### Budget Control (LLM Only)

- **Cost Estimation**: Pre-call cost estimation based on model, messages, max_tokens
- **Hard Cap**: Rejects requests exceeding hard cap
- **Soft Cap**: Throttles by reducing `max_tokens` if soft cap exceeded
- **Cost Tracking**: Records actual cost in metrics

### Cost Estimator

- **Provider-Specific**: Pricing tables per provider/model
- **Token-Based**: Estimates based on input/output tokens
- **Approximate**: Uses approximate token counts (not exact)

---

## Request Flow

### HTTP Request Flow

```
1. Client → POST /proxy/http
2. Parse request (target, method, path, ...)
3. Load target config
4. Check idempotency (if key present)
5. Check cache (if GET/HEAD)
6. Check circuit breaker
7. Create HTTP client
8. Make upstream request (with retries)
9. Normalize response
10. Store cache (if cacheable)
11. Store idempotency result (if key present)
12. Export metrics
13. Return response envelope
```

### LLM Request Flow

```
1. Client → POST /proxy/llm
2. Parse request (target, messages, model, ...)
3. Load target config (with LLM settings)
4. Reject streaming (if requested)
5. Estimate cost
6. Check hard cap (reject if exceeded)
7. Check soft cap (throttle if exceeded)
8. Check idempotency (if key present)
9. Check cache
10. Check circuit breaker
11. Select adapter (OpenAI/Anthropic/Mistral)
12. Prepare provider-specific request
13. Make upstream request (with retries)
14. Parse provider response
15. Calculate actual cost
16. Normalize response
17. Store cache (if cacheable)
18. Store idempotency result (if key present)
19. Export metrics
20. Return response envelope
```

---

## Data Storage

### Redis

ReliAPI uses Redis for:

- **Cache**: TTL-based cache storage
- **Idempotency**: Idempotency key storage and result caching
- **Circuit Breaker**: Failure state storage (optional, can be in-memory)

### Configuration

- **YAML File**: `config.yaml` with target definitions
- **Environment Variables**: API keys, Redis URL, config path

---

## Metrics & Observability

### Prometheus Metrics

- `reliapi_http_requests_total`: HTTP request counts
- `reliapi_llm_requests_total`: LLM request counts
- `reliapi_errors_total`: Error counts by type
- `reliapi_cache_hits_total`: Cache hit counts
- `reliapi_latency_ms`: Request latency histogram
- `reliapi_llm_cost_usd`: LLM cost histogram

### Logging

- **Structured JSON**: All logs in JSON format
- **Request IDs**: Every request has unique ID
- **Trace IDs**: Optional trace ID for distributed tracing

### Health Endpoints

- `/healthz`: Basic health check
- `/readyz`: Readiness check (Redis, targets)
- `/livez`: Liveness check
- `/metrics`: Prometheus metrics endpoint

---

## Deployment Architecture

### Single Instance

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   ReliAPI (Port 8000)   │
└──────┬──────────────────┘
       │
┌──────▼──────┐
│   Redis     │
└─────────────┘
```

### Docker Compose

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
┌──────▼──────────────────┐
│   Docker Compose        │
│                        │
│  ┌──────────────┐      │
│  │   ReliAPI    │      │
│  └──────┬───────┘      │
│         │              │
│  ┌──────▼──────┐      │
│  │   Redis     │      │
│  └─────────────┘      │
└───────────────────────┘
```

---

## Next Steps

- [Configuration](Configuration.md) — Configuration guide
- [Reliability Features](Reliability-Features.md) — Detailed feature explanations

