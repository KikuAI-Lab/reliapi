/**
 * ReliAPI Overhead Benchmark
 * 
 * Measures proxy overhead by comparing total request time with upstream time.
 * 
 * Usage:
 *   export RELIAPI_URL="http://localhost:8000"
 *   export API_KEY="your-api-key"
 *   k6 run k6_overhead_benchmark.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Counter, Rate } from 'k6/metrics';

// Custom metrics for overhead measurement
const overheadP50 = new Trend('overhead_p50', true);
const overheadP95 = new Trend('overhead_p95', true);
const totalLatency = new Trend('total_latency', true);
const cacheHits = new Counter('cache_hits');
const cacheHitRate = new Rate('cache_hit_rate');

// Configuration
const BASE_URL = __ENV.RELIAPI_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-key';

export const options = {
  stages: [
    { duration: '10s', target: 10 },  // Warm up
    { duration: '30s', target: 50 },  // Main test
    { duration: '20s', target: 100 }, // Peak load
    { duration: '10s', target: 0 },   // Cool down
  ],
  thresholds: {
    'overhead_p50': ['p(50)<10'],     // P50 overhead < 10ms
    'overhead_p95': ['p(95)<30'],     // P95 overhead < 30ms
    'http_req_failed': ['rate<0.01'], // Error rate < 1%
  },
};

// Test data - simple LLM request
const llmPayload = JSON.stringify({
  target: 'openai',
  model: 'gpt-4o-mini',
  messages: [{ role: 'user', content: 'Say "hello" in one word.' }],
  max_tokens: 5,
});

// Test data - HTTP GET request
const httpTarget = 'httpbin'; // Configure this target in your config.yaml

export default function () {
  // Test 1: LLM Proxy Overhead
  const llmStart = Date.now();
  const llmRes = http.post(`${BASE_URL}/proxy/llm`, llmPayload, {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  });
  const llmTotal = Date.now() - llmStart;
  
  // Extract upstream time from response meta (if available)
  let llmUpstreamTime = 0;
  try {
    const body = JSON.parse(llmRes.body);
    if (body.meta && body.meta.duration_ms) {
      // duration_ms includes upstream time
      llmUpstreamTime = body.meta.duration_ms;
    }
    // Check cache hit
    if (body.meta && body.meta.cache_hit) {
      cacheHits.add(1);
      cacheHitRate.add(1);
    } else {
      cacheHitRate.add(0);
    }
  } catch (e) {
    // Ignore parse errors
  }
  
  // Calculate overhead (total - upstream)
  // Note: This is an approximation since duration_ms is measured server-side
  const llmOverhead = Math.max(0, llmTotal - llmUpstreamTime);
  
  overheadP50.add(llmOverhead);
  overheadP95.add(llmOverhead);
  totalLatency.add(llmTotal);
  
  check(llmRes, {
    'LLM status is 200': (r) => r.status === 200,
    'LLM overhead < 20ms': () => llmOverhead < 20,
    'LLM response has meta': (r) => {
      try {
        return JSON.parse(r.body).meta !== undefined;
      } catch {
        return false;
      }
    },
  });
  
  sleep(0.1); // Small delay between requests
  
  // Test 2: HTTP Proxy Overhead (if httpbin target configured)
  const httpStart = Date.now();
  const httpRes = http.post(`${BASE_URL}/proxy/http`, JSON.stringify({
    target: httpTarget,
    method: 'GET',
    path: '/get',
  }), {
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY,
    },
  });
  const httpTotal = Date.now() - httpStart;
  
  let httpUpstreamTime = 0;
  try {
    const body = JSON.parse(httpRes.body);
    if (body.meta && body.meta.duration_ms) {
      httpUpstreamTime = body.meta.duration_ms;
    }
  } catch (e) {
    // Ignore
  }
  
  const httpOverhead = Math.max(0, httpTotal - httpUpstreamTime);
  overheadP50.add(httpOverhead);
  overheadP95.add(httpOverhead);
  
  check(httpRes, {
    'HTTP status is 200 or 404': (r) => r.status === 200 || r.status === 404,
    'HTTP overhead < 15ms': () => httpOverhead < 15,
  });
  
  sleep(0.1);
}

export function handleSummary(data) {
  // Export results to JSON
  const results = {
    timestamp: new Date().toISOString(),
    environment: {
      base_url: BASE_URL,
      k6_version: __ENV.K6_VERSION || 'unknown',
    },
    metrics: {
      overhead_p50_ms: data.metrics.overhead_p50?.values?.['p(50)'] || 0,
      overhead_p95_ms: data.metrics.overhead_p95?.values?.['p(95)'] || 0,
      total_latency_p50_ms: data.metrics.total_latency?.values?.['p(50)'] || 0,
      total_latency_p95_ms: data.metrics.total_latency?.values?.['p(95)'] || 0,
      cache_hit_rate: data.metrics.cache_hit_rate?.values?.rate || 0,
      error_rate: data.metrics.http_req_failed?.values?.rate || 0,
      requests_total: data.metrics.http_reqs?.values?.count || 0,
    },
    thresholds_passed: Object.keys(data.metrics).every(
      (key) => !data.metrics[key].thresholds || 
               Object.values(data.metrics[key].thresholds).every((t) => t.ok)
    ),
  };
  
  return {
    'benchmark_results.json': JSON.stringify(results, null, 2),
    stdout: textSummary(data, { indent: ' ', enableColors: true }),
  };
}

function textSummary(data, opts) {
  const lines = [
    '',
    '╔══════════════════════════════════════════════════════════════════╗',
    '║                   ReliAPI Overhead Benchmark                     ║',
    '╚══════════════════════════════════════════════════════════════════╝',
    '',
    `  Overhead P50: ${(data.metrics.overhead_p50?.values?.['p(50)'] || 0).toFixed(2)}ms`,
    `  Overhead P95: ${(data.metrics.overhead_p95?.values?.['p(95)'] || 0).toFixed(2)}ms`,
    `  Total Latency P50: ${(data.metrics.total_latency?.values?.['p(50)'] || 0).toFixed(2)}ms`,
    `  Total Latency P95: ${(data.metrics.total_latency?.values?.['p(95)'] || 0).toFixed(2)}ms`,
    `  Cache Hit Rate: ${((data.metrics.cache_hit_rate?.values?.rate || 0) * 100).toFixed(1)}%`,
    `  Error Rate: ${((data.metrics.http_req_failed?.values?.rate || 0) * 100).toFixed(2)}%`,
    `  Total Requests: ${data.metrics.http_reqs?.values?.count || 0}`,
    '',
    '══════════════════════════════════════════════════════════════════',
    '',
  ];
  return lines.join('\n');
}

