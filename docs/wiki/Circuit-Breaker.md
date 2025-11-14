# Circuit Breaker

ReliAPI implements a circuit breaker pattern per target, automatically detecting failures and preventing cascading failures.

---

## How It Works

The circuit breaker has three states:

1. **CLOSED** — Normal operation, requests pass through
2. **OPEN** — Circuit opened after N consecutive failures, requests rejected immediately
3. **HALF_OPEN** — Testing state after cooldown, allows one test request

---

## Configuration

```yaml
targets:
  my-api:
    circuit:
      error_threshold: 5      # Open circuit after 5 failures
      cooldown_s: 60          # Wait 60s before retry
```

---

## Behavior Example

```
Request 1-4: 500 errors → Record failures
Request 5:   500 error → Circuit OPENED
Request 6-10: Immediately rejected (circuit open)
After 60s:   Circuit HALF_OPEN → Test request
If success:  Circuit CLOSED → Normal operation
If failure:  Circuit OPEN → Wait another 60s
```

---

## Response When Circuit is Open

```json
{
  "success": false,
  "error": {
    "type": "circuit_breaker_error",
    "code": "CIRCUIT_OPEN",
    "message": "Circuit breaker is open for target 'my-api'",
    "retryable": false,
    "target": "my-api"
  }
}
```

---

## Failure Detection

The circuit breaker opens on:
- HTTP 5xx errors
- Network errors (timeout, connection refused)
- Configurable error threshold

Success resets the failure count.

---

## Monitoring

Check circuit breaker state via Prometheus:

```promql
# Circuit breaker state (0=closed, 1=open, 2=half-open)
reliapi_circuit_breaker_state{target="my-api"}

# Circuit breaker transitions
rate(reliapi_circuit_breaker_transitions_total[5m])
```

---

## Best Practices

- Set `error_threshold` based on your error tolerance (3-10 is typical)
- Set `cooldown_s` based on recovery time (30-120s is typical)
- Monitor circuit breaker state in production
- Use fallback chains for critical targets

---

## See Also

- [Architecture](Architecture.md) — system design
- [Observability](Observability.md) — metrics and monitoring
- [Usage Guides](Usage-Guides.md) — examples

