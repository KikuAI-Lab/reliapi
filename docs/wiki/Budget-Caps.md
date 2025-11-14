# Budget Caps

ReliAPI enforces cost limits for LLM requests using **soft caps** (throttle) and **hard caps** (reject), preventing surprise bills and ensuring predictable costs.

---

## How It Works

### Soft Cap

When estimated cost exceeds the soft cap:
- ReliAPI **automatically reduces `max_tokens`** to fit the budget
- Request proceeds with reduced tokens
- Response includes `cost_policy_applied: "soft_cap_reduced"`

### Hard Cap

When estimated cost exceeds the hard cap:
- ReliAPI **rejects the request** before upstream call
- Returns `400 Bad Request` with `BUDGET_EXCEEDED` error
- No upstream API call is made

---

## Configuration

```yaml
targets:
  openai:
    llm:
      soft_cost_cap_usd: 0.10   # Throttle if exceeded
      hard_cost_cap_usd: 0.50    # Reject if exceeded
```

---

## Examples

### Soft Cap in Action

```python
# Request with max_tokens=2000, estimated cost: $0.12
response = httpx.post(
    "http://localhost:8000/proxy/llm",
    json={
        "target": "openai",
        "messages": [{"role": "user", "content": "Write a long story"}],
        "max_tokens": 2000  # Exceeds soft cap
    }
)

result = response.json()
# Result: ReliAPI automatically reduces max_tokens to fit $0.10 cap
print(result["meta"]["cost_policy_applied"])  # "soft_cap_reduced"
print(result["meta"]["cost_estimate_usd"])     # 0.10
```

### Hard Cap in Action

```python
# Request with estimated cost: $0.60 (exceeds hard cap)
response = httpx.post(
    "http://localhost:8000/proxy/llm",
    json={
        "target": "openai",
        "messages": [{"role": "user", "content": "Generate a novel"}],
        "max_tokens": 10000
    }
)

result = response.json()
# Result: Request rejected before upstream call
# {
#   "success": false,
#   "error": {
#     "code": "BUDGET_EXCEEDED",
#     "message": "Estimated cost $0.60 exceeds hard cap $0.50"
#   }
# }
```

---

## Response Metadata

```json
{
  "success": true,
  "data": {...},
  "meta": {
    "cost_estimate_usd": 0.10,
    "cost_usd": 0.095,
    "cost_policy_applied": "soft_cap_reduced",  // or "none", "hard_cap_rejected"
    "target": "openai"
  }
}
```

---

## Cost Estimation

ReliAPI estimates costs before making upstream calls using:
- Model pricing (per 1K tokens)
- Estimated prompt tokens (from message length)
- Requested `max_tokens`

Cost estimation is conservative — actual costs may be slightly lower.

---

## Multi-Tenant Budgets

Each tenant can have separate budget caps:

```yaml
tenants:
  - name: "client-a"
    budget_caps:
      openai:
        soft_cost_cap_usd: 10.0
        hard_cost_cap_usd: 50.0
```

---

## Monitoring

Track budget cap triggers via Prometheus:

```promql
# Hard cap rejections
sum(rate(reliapi_budget_events_total{event="hard_cap"}[5m])) by (target)

# Soft cap reductions
sum(rate(reliapi_budget_events_total{event="soft_cap"}[5m])) by (target)
```

---

## See Also

- [Observability](Observability.md) — metrics and monitoring
- [Multi-Tenant Mode](Multi-Tenant-Mode.md) — per-tenant budgets
- [API Reference](API-Reference.md) — endpoint details

