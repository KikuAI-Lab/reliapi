/**
 * TypeScript/Node.js example for ReliAPI
 * 
 * This example demonstrates:
 * - Basic HTTP proxy usage
 * - Basic LLM proxy usage with TypeScript types
 * - Error handling
 * - Streaming support
 * - Idempotency and caching
 * 
 * Requirements:
 *   npm install node-fetch @types/node-fetch
 * 
 * Usage:
 *   npx ts-node typescript_example.ts
 *   OR
 *   tsc typescript_example.ts && node typescript_example.js
 */

import fetch from 'node-fetch';

// Configuration
const RELIAPI_URL = process.env.RELIAPI_URL || 'https://reliapi.kikuai.dev';
const API_KEY = process.env.RAPIDAPI_KEY || process.env.RELIAPI_API_KEY || 'your-api-key';

// Types
interface ReliAPILLMRequest {
  target: 'openai' | 'anthropic' | 'mistral';
  messages: Array<{ role: string; content: string }>;
  model: string;
  max_tokens?: number;
  temperature?: number;
  stream?: boolean;
  idempotency_key?: string;
  cache?: number;
}

interface ReliAPIHTTPRequest {
  target: string;
  method: string;
  path: string;
  headers?: Record<string, string>;
  query?: Record<string, any>;
  body?: string;
  idempotency_key?: string;
  cache?: number;
}

interface ReliAPIResponse<T = any> {
  data: T;
  meta: {
    request_id: string;
    cache_hit: boolean;
    idempotent_hit: boolean;
    cost_usd?: number;
    duration_ms: number;
  };
}

/**
 * HTTP proxy example
 */
async function httpProxyExample(): Promise<void> {
  console.log('=== HTTP Proxy Example ===');
  
  const request: ReliAPIHTTPRequest = {
    target: 'jsonplaceholder',
    method: 'GET',
    path: '/posts/1',
    cache: 300, // Cache for 5 minutes
    idempotency_key: `http-${Date.now()}`
  };
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/http`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (response.ok) {
      const data: ReliAPIResponse = await response.json();
      console.log('Success:', JSON.stringify(data.data, null, 2));
      console.log('Cache hit:', data.meta.cache_hit);
      console.log('Request ID:', data.meta.request_id);
    } else {
      const errorText = await response.text();
      console.error('Error:', response.status, errorText);
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * LLM proxy example
 */
async function llmProxyExample(): Promise<void> {
  console.log('\n=== LLM Proxy Example ===');
  
  const request: ReliAPILLMRequest = {
    target: 'openai',
    messages: [
      { role: 'user', content: 'What is idempotency in API design? Explain in one sentence.' }
    ],
    model: 'gpt-4o-mini',
    max_tokens: 100,
    idempotency_key: `llm-${Date.now()}`,
    cache: 3600, // Cache for 1 hour
  };
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (response.ok) {
      const data: ReliAPIResponse = await response.json();
      const content = (data.data as any).choices?.[0]?.message?.content || '';
      console.log('Response:', content);
      console.log('Cost: $' + (data.meta.cost_usd || 0));
      console.log('Cache hit:', data.meta.cache_hit);
      console.log('Request ID:', data.meta.request_id);
    } else {
      const errorData = await response.json();
      console.error('Error:', response.status, errorData);
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * Streaming example
 */
async function streamingExample(): Promise<void> {
  console.log('\n=== Streaming Example ===');
  
  const request: ReliAPILLMRequest = {
    target: 'openai',
    messages: [
      { role: 'user', content: 'Write a haiku about reliability.' }
    ],
    model: 'gpt-4o-mini',
    stream: true,
    max_tokens: 100,
  };
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify(request),
    });
    
    if (response.ok && response.body) {
      console.log('Streaming response:');
      const reader = response.body;
      let buffer = '';
      
      for await (const chunk of reader) {
        buffer += chunk.toString();
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6);
            if (dataStr === '[DONE]') {
              console.log('\n');
              return;
            }
            
            try {
              const data = JSON.parse(dataStr);
              const content = data.choices?.[0]?.delta?.content || '';
              if (content) {
                process.stdout.write(content);
              }
            } catch (e) {
              // Ignore parse errors
            }
          }
        }
      }
      console.log('\n');
    } else {
      const errorText = await response.text();
      console.error('Error:', response.status, errorText);
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * Caching example - same request twice
 */
async function cachingExample(): Promise<void> {
  console.log('\n=== Caching Example ===');
  
  const request: ReliAPILLMRequest = {
    target: 'openai',
    messages: [
      { role: 'user', content: 'What is circuit breaker pattern?' }
    ],
    model: 'gpt-4o-mini',
    cache: 3600,
  };
  
  try {
    // First request
    console.log('First request (will call OpenAI API):');
    const response1 = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (response1.ok) {
      const data1: ReliAPIResponse = await response1.json();
      console.log('Response:', (data1.data as any).choices?.[0]?.message?.content?.substring(0, 100) + '...');
      console.log('Cache hit:', data1.meta.cache_hit);
      console.log('Cost: $' + (data1.meta.cost_usd || 0));
    }
    
    // Second request - should be cached
    console.log('\nSecond request (same question - should be cached, FREE!):');
    const response2 = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });
    
    if (response2.ok) {
      const data2: ReliAPIResponse = await response2.json();
      console.log('Response:', (data2.data as any).choices?.[0]?.message?.content?.substring(0, 100) + '...');
      console.log('Cache hit:', data2.meta.cache_hit);
      console.log('Cost: $' + (data2.meta.cost_usd || 0));
      if (data2.meta.cache_hit) {
        console.log('✅ Second request was FREE (served from cache)!');
      }
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * Error handling example
 */
async function errorHandlingExample(): Promise<void> {
  console.log('\n=== Error Handling Example ===');
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target: 'openai',
        messages: [{ role: 'user', content: 'Test' }],
        max_tokens: 100000, // May exceed budget cap
      }),
    });
    
    if (response.ok) {
      console.log('Success!');
    } else {
      const errorData = await response.json();
      const error = (errorData as any).error || {};
      
      console.log('Error Type:', error.type);
      console.log('Error Code:', error.code);
      console.log('Message:', error.message);
      console.log('Retryable:', error.retryable);
      
      // Handle rate limit errors
      if (error.code === 'RATE_LIMIT_RELIAPI') {
        const retryAfter = error.retry_after_s || 1.0;
        console.log(`Rate limited. Retry after ${retryAfter}s`);
      }
    }
  } catch (error) {
    if (error instanceof Error) {
      console.error('Error:', error.message);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

// Run examples
(async () => {
  console.log('ReliAPI TypeScript Example\n');
  
  await httpProxyExample();
  await llmProxyExample();
  await streamingExample();
  await cachingExample();
  await errorHandlingExample();
  
  console.log('\n=== Examples Completed ===');
  console.log('\nBenefits of ReliAPI:');
  console.log('  ✓ Automatic retries on failures');
  console.log('  ✓ Caching reduces costs by 50-80%');
  console.log('  ✓ Idempotency prevents duplicate charges');
  console.log('  ✓ Budget caps prevent surprise bills');
  console.log('  ✓ Circuit breaker prevents cascading failures');
})();














