# ReliAPI Performance Benchmarks

## Methodology

All benchmarks measure **proxy overhead** - the additional latency added by the proxy layer, not the total request time (which depends heavily on upstream API performance).

### How We Measure Overhead

```
Overhead = Total Request Time - Upstream API Time
```

Where:
- **Total Request Time**: Time from request sent to response received (through ReliAPI)
- **Upstream API Time**: Time from ReliAPI forwarding request to upstream response received

### Test Environment

- **Hardware**: AWS EC2 c5.xlarge (4 vCPU, 8 GB RAM)
- **Redis**: Local Redis 7.0 (same instance)
- **Network**: Same VPC, <1ms network latency to upstream
- **Load**: k6 with 10-100 concurrent users
- **Duration**: 60 seconds per test, 3 runs averaged

### Benchmark Results

#### P50 Overhead (Typical Request)

| Gateway | P50 Overhead | Notes |
|---------|--------------|-------|
| ReliAPI | ~5ms | Minimal processing, direct proxy |
| Portkey | ~8ms | Additional logging overhead |
| LiteLLM | ~10ms | Provider abstraction layer |
| Helicone | ~15ms | SaaS routing overhead |

#### P95 Overhead (Worst Case)

| Gateway | P95 Overhead | Notes |
|---------|--------------|-------|
| ReliAPI | ~15ms | Cache miss + idempotency check |
| Portkey | ~25ms | Dashboard logging + metrics |
| LiteLLM | ~30ms | Model routing + validation |
| Helicone | ~40ms | SaaS network + processing |

### Factors Affecting Overhead

1. **Cache Hit**: ~1-3ms (returns cached response immediately)
2. **Cache Miss**: ~10-20ms (Redis lookup + upstream call)
3. **Idempotency Check**: ~2-5ms (Redis SETNX operation)
4. **Circuit Breaker Check**: ~1ms (in-memory check)
5. **Retry**: +delay configured in retry policy

### Memory Usage

| Load | ReliAPI | LiteLLM | Portkey |
|------|---------|---------|---------|
| Idle | ~50MB | ~150MB | ~120MB |
| 100 RPS | ~100MB | ~300MB | ~250MB |
| 500 RPS | ~200MB | ~600MB | ~500MB |

### Running Your Own Benchmarks

```bash
cd reliapi-private/load_test

# Install k6
brew install k6  # macOS
# or: sudo apt-get install k6  # Linux

# Set environment
export RELIAPI_URL="http://localhost:8000"
export API_KEY="your-api-key"

# Run overhead benchmark
k6 run k6_overhead_benchmark.js

# View results
cat benchmark_results.json
```

### Benchmark Script

See `load_test/k6_overhead_benchmark.js` for the exact benchmark script used.

## Disclaimer

These benchmarks are **synthetic** and based on controlled test environments. Real-world performance depends on:

- Network latency to upstream APIs
- Redis performance and configuration
- Hardware resources (CPU, memory)
- Request complexity (message size, model)
- Cache hit rate (depends on usage patterns)

**Always run your own benchmarks** in your target environment for accurate results.

## Comparison Notes

- **Helicone**: SaaS-only, so network latency to their servers adds overhead
- **LiteLLM**: Open-source, provider abstraction adds parsing overhead
- **Portkey**: Dashboard features add logging overhead
- **ReliAPI**: Minimal design, optimized for low overhead

All tools have trade-offs. Choose based on your priorities:
- **Lowest overhead**: ReliAPI
- **Best dashboards**: Portkey, Helicone
- **Most providers**: LiteLLM
- **SaaS convenience**: Helicone

