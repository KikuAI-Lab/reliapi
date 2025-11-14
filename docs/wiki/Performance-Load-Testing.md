# Performance & Load Testing

Guide to testing ReliAPI performance and load capacity using k6 and other tools.

## Table of Contents

- [Quick Start](#quick-start)
- [k6 Test Scenarios](#k6-test-scenarios)
- [Performance Benchmarks](#performance-benchmarks)
- [Load Testing Recommendations](#load-testing-recommendations)
- [Interpreting Results](#interpreting-results)

---

## Quick Start

### Install k6

```bash
# macOS
brew install k6

# Linux
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D53
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Windows
choco install k6
```

### Basic Test

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },   // Ramp up to 10 users
    { duration: '1m', target: 10 },   // Stay at 10 users
    { duration: '30s', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
  },
};

export default function () {
  const response = http.post('https://reliapi.example.com/proxy/http', JSON.stringify({
    target: 'my-api',
    method: 'GET',
    path: '/test',
  }), {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
}
```

Run:

```bash
k6 run test.js --env API_KEY=your-api-key
```

---

## k6 Test Scenarios

### HTTP Proxy Load Test

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 100 },
    { duration: '1m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<300', 'p(99)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const payload = JSON.stringify({
    target: 'my-api',
    method: 'GET',
    path: `/users/${Math.floor(Math.random() * 1000)}`,
    idempotency_key: `req-${__VU}-${__ITER}`,
  });

  const response = http.post('https://reliapi.example.com/proxy/http', payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has cache hit': (r) => {
      const body = JSON.parse(r.body);
      return body.meta && typeof body.meta.cache_hit === 'boolean';
    },
  });

  sleep(1);
}
```

### LLM Proxy Load Test

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 5 },
    { duration: '2m', target: 10 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<5000'],  // LLM requests are slower
    http_req_failed: ['rate<0.05'],
  },
};

export default function () {
  const payload = JSON.stringify({
    target: 'openai',
    messages: [
      { role: 'user', content: 'Say hello in one sentence.' }
    ],
    model: 'gpt-3.5-turbo',
    max_tokens: 50,
    idempotency_key: `chat-${__VU}-${__ITER}`,
  });

  const response = http.post('https://reliapi.example.com/proxy/llm', payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
    timeout: '30s',
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'has cost estimate': (r) => {
      const body = JSON.parse(r.body);
      return body.meta && typeof body.meta.cost_usd === 'number';
    },
  });

  sleep(5);  // Wait between requests
}
```

### Cache Hit Rate Test

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '2m',
};

let cacheHits = 0;
let totalRequests = 0;

export default function () {
  // Use same idempotency key to test caching
  const payload = JSON.stringify({
    target: 'my-api',
    method: 'GET',
    path: '/cached-endpoint',
    idempotency_key: 'cache-test-key',
  });

  const response = http.post('https://reliapi.example.com/proxy/http', payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
  });

  totalRequests++;
  const body = JSON.parse(response.body);
  if (body.meta && body.meta.cache_hit) {
    cacheHits++;
  }

  check(response, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(0.5);
}

export function handleSummary(data) {
  const hitRate = (cacheHits / totalRequests * 100).toFixed(2);
  return {
    'stdout': `\nCache Hit Rate: ${hitRate}% (${cacheHits}/${totalRequests})\n`,
  };
}
```

### Idempotency Coalescing Test

```javascript
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 50,
  duration: '30s',
};

export default function () {
  // All VUs use the same idempotency key
  const payload = JSON.stringify({
    target: 'my-api',
    method: 'POST',
    path: '/orders',
    body: { item: 'test' },
    idempotency_key: 'coalesce-test',
  });

  const response = http.post('https://reliapi.example.com/proxy/http', payload, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': __ENV.API_KEY,
    },
  });

  check(response, {
    'status is 200': (r) => r.status === 200,
    'idempotent hit': (r) => {
      const body = JSON.parse(r.body);
      return body.meta && body.meta.idempotent_hit === true;
    },
  });
}
```

---

## Performance Benchmarks

### Expected Performance

**HTTP Proxy:**
- P50 latency: < 50ms (cached)
- P95 latency: < 200ms (cached), < 500ms (uncached)
- P99 latency: < 500ms (cached), < 1000ms (uncached)
- Throughput: 1000+ req/s (single instance)

**LLM Proxy:**
- P50 latency: < 2000ms (depends on provider)
- P95 latency: < 5000ms
- P99 latency: < 10000ms
- Throughput: 10-50 req/s (limited by LLM providers)

### Factors Affecting Performance

1. **Cache Hit Rate**: Higher cache hit rate = lower latency
2. **Network Latency**: Distance to upstream API
3. **Upstream API Speed**: LLM providers vary significantly
4. **Redis Performance**: Cache and idempotency depend on Redis
5. **Concurrent Requests**: Circuit breaker and retries add overhead

---

## Load Testing Recommendations

### Test Scenarios

1. **Baseline Test**: Single user, measure baseline latency
2. **Ramp-up Test**: Gradually increase load to find breaking point
3. **Sustained Load**: Maintain high load for extended period
4. **Spike Test**: Sudden increase in load
5. **Stress Test**: Push beyond expected capacity

### Key Metrics to Monitor

- **Request Rate**: Requests per second
- **Latency**: P50, P95, P99 percentiles
- **Error Rate**: Percentage of failed requests
- **Cache Hit Rate**: Percentage of cached responses
- **Idempotent Hit Rate**: Percentage of idempotent hits
- **Upstream Errors**: 5xx, 429 errors from upstream
- **Circuit Breaker State**: How often circuit breakers open

### Resource Monitoring

Monitor server resources during tests:

```bash
# CPU and Memory
htop

# Network
iftop

# Docker stats
docker stats

# Redis stats
docker exec -it reliapi-redis redis-cli INFO stats
```

---

## Interpreting Results

### Good Results

- ✅ P95 latency < 500ms for HTTP, < 5000ms for LLM
- ✅ Error rate < 1%
- ✅ Cache hit rate > 50% (for cacheable endpoints)
- ✅ No circuit breaker openings
- ✅ Stable memory usage

### Warning Signs

- ⚠️ P95 latency > 1000ms
- ⚠️ Error rate > 5%
- ⚠️ Circuit breakers opening frequently
- ⚠️ Memory usage growing continuously
- ⚠️ Redis connection errors

### Optimization Tips

1. **Increase Cache TTL**: If cache hit rate is low
2. **Tune Circuit Breaker**: Adjust failure threshold and recovery timeout
3. **Scale Horizontally**: Add more ReliAPI instances behind load balancer
4. **Optimize Redis**: Use Redis Cluster for high availability
5. **Reduce Retries**: Lower `max_attempts` if upstream is consistently slow

---

## Next Steps

- [Deploy Guide](Deploy-Guide) — Production deployment
- [Configuration](Configuration) — Tune performance settings
- [Developer Guide](Developer-Guide) — Contribute improvements

