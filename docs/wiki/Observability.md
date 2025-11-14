# Observability

ReliAPI provides comprehensive observability through Prometheus metrics, structured JSON logging, and ready-to-use Grafana dashboards.

---

## Prometheus Metrics

All metrics are exposed at `/metrics` endpoint.

### Request Metrics

```promql
# Request rate by target and kind
rate(reliapi_requests_total{target="openai", kind="llm"}[5m])

# Error rate
sum(rate(reliapi_errors_total[5m])) by (target, error_code)

# P95 latency
histogram_quantile(0.95, sum(rate(reliapi_request_latency_ms_bucket[5m])) by (le, target))
```

### Cache & Idempotency

```promql
# Cache hit ratio
sum(rate(reliapi_cache_hits_total[5m])) by (target) / 
  (sum(rate(reliapi_cache_hits_total[5m])) by (target) + 
   sum(rate(reliapi_cache_misses_total[5m])) by (target))

# Idempotent hit ratio
sum(rate(reliapi_idempotent_hits_total[5m])) by (target) /
  sum(rate(reliapi_requests_total[5m])) by (target)
```

### Budget & Costs

```promql
# Budget cap triggers
sum(rate(reliapi_budget_events_total{event="hard_cap"}[5m])) by (target)

# LLM costs per target (USD/hour)
sum(rate(reliapi_llm_cost_usd_total[1h])) by (target) * 3600
```

### Circuit Breaker

```promql
# Circuit breaker state (0=closed, 1=open, 2=half-open)
reliapi_circuit_breaker_state{target="my-api"}

# Circuit breaker transitions
rate(reliapi_circuit_breaker_transitions_total[5m])
```

---

## Structured JSON Logging

Every request is logged as a single JSON line with full context:

```json
{
  "ts": "2025-01-15T10:30:45.123Z",
  "level": "INFO",
  "request_id": "req_abc123def456",
  "target": "openai",
  "kind": "llm",
  "stream": false,
  "model": "gpt-4o-mini",
  "outcome": "success",
  "error_code": null,
  "upstream_status": 200,
  "latency_ms": 1250,
  "cost_usd": 0.000012,
  "cache_hit": false,
  "idempotent_hit": false,
  "retries": 0,
  "tenant": "client-a"
}
```

### Log Fields

- `ts` — ISO timestamp
- `level` — Log level (INFO, ERROR)
- `request_id` — Unique request identifier (UUID4)
- `target` — Target name
- `kind` — "http" or "llm"
- `stream` — Whether streaming (LLM only)
- `outcome` — "success" or "error"
- `error_code` — Error code if applicable
- `upstream_status` — Upstream HTTP status
- `latency_ms` — Request latency
- `cost_usd` — Cost in USD (LLM only)
- `cache_hit` — Whether from cache
- `idempotent_hit` — Whether from idempotency cache
- `tenant` — Tenant name (multi-tenant mode)

---

## Request Tracing

### Find All Logs for a Request

```bash
grep "req_abc123def456" /var/log/reliapi/app.log | jq
```

### Find All Requests for a Target

```bash
grep "openai" /var/log/reliapi/app.log | jq '.request_id' | sort -u
```

### Find Errors for a Target

```bash
grep "openai" /var/log/reliapi/app.log | jq 'select(.outcome == "error")'
```

---

## Grafana Dashboards

Ready-to-use Grafana dashboards are available in `deploy/grafana/`:

### Overview Dashboard

- Request rate and error rate
- P95/P99 latency
- Cache hit ratio
- Idempotent hit ratio
- Budget cap triggers
- LLM costs per target

### LLM Streaming Dashboard

- Stream vs non-stream requests
- Streaming error codes
- `UPSTREAM_STREAM_INTERRUPTED` count
- Streaming latency

### Import Dashboards

1. Copy JSON from `deploy/grafana/reliapi_overview.json`
2. Import in Grafana: **Dashboards → Import**
3. Select Prometheus data source
4. Adjust time ranges and refresh intervals

---

## Best Practices

- **Request IDs**: Always include `request_id` in error reports
- **Log aggregation**: Use ELK, Loki, or similar for log aggregation
- **Alerting**: Set up alerts for error rate, latency, and budget cap triggers
- **Dashboards**: Customize Grafana dashboards for your use case

---

## See Also

- [Architecture](Architecture.md) — system design
- [Deployment](Deploy-Guide.md) — production setup
- [Multi-Tenant Mode](Multi-Tenant-Mode.md) — per-tenant metrics

