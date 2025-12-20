/**
 * Basic JavaScript example for ReliAPI.
 * 
 * This example demonstrates:
 * - Basic HTTP proxy usage
 * - Basic LLM proxy usage
 * - Error handling
 * - Response parsing
 */

const RELIAPI_URL = process.env.RELIAPI_URL || 'https://reliapi.kikuai.dev';
const API_KEY = process.env.RAPIDAPI_KEY || process.env.RELIAPI_API_KEY || 'your-api-key';

/**
 * HTTP proxy example
 */
async function httpProxyExample() {
  console.log('=== HTTP Proxy Example ===');
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/http`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target: 'httpbin',
        method: 'GET',
        path: '/get',
      }),
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('Success:', JSON.stringify(data, null, 2));
      console.log('Cache hit:', data.meta?.cache_hit || false);
    } else {
      console.error('Error:', response.status, await response.text());
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * LLM proxy example
 */
async function llmProxyExample() {
  console.log('\n=== LLM Proxy Example ===');
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target: 'openai',
        messages: [
          { role: 'user', content: "Say 'Hello, ReliAPI!' only." }
        ],
        model: 'gpt-4o-mini',
        max_tokens: 20,
      }),
    });
    
    if (response.ok) {
      const data = await response.json();
      console.log('Success:', JSON.stringify(data, null, 2));
      console.log('Content:', data.data?.choices?.[0]?.message?.content || '');
      console.log('Cost: $' + (data.meta?.cost_usd || 0));
    } else {
      const errorData = await response.json();
      console.error('Error:', response.status, errorData);
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

/**
 * Error handling example
 */
async function errorHandlingExample() {
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
        max_tokens: 10000, // May exceed budget cap
      }),
    });
    
    if (response.ok) {
      console.log('Success!');
    } else {
      const errorData = await response.json();
      const error = errorData.error || {};
      
      console.log('Error Type:', error.type);
      console.log('Error Code:', error.code);
      console.log('Message:', error.message);
      console.log('Retryable:', error.retryable);
      
      // Handle rate limit errors
      if (error.code === 'RATE_LIMIT_RELIAPI') {
        const retryAfter = error.retry_after_s || 1.0;
        console.log(`Rate limited. Retry after ${retryAfter}s`);
        // Wait and retry
        await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
        // Retry request...
      }
    }
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      console.error('Network error:', error);
    } else {
      console.error('Unexpected error:', error);
    }
  }
}

/**
 * Streaming example
 */
async function streamingExample() {
  console.log('\n=== Streaming Example ===');
  
  try {
    const response = await fetch(`${RELIAPI_URL}/proxy/llm`, {
      method: 'POST',
      headers: {
        'X-RapidAPI-Key': API_KEY,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target: 'openai',
        messages: [{ role: 'user', content: 'Count from 1 to 5' }],
        model: 'gpt-4o-mini',
        stream: true,
        max_tokens: 50,
      }),
    });
    
    if (response.ok) {
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      console.log('Streaming response:');
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
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
      console.error('Error:', response.status, await response.text());
    }
  } catch (error) {
    console.error('Request error:', error);
  }
}

// Run examples
(async () => {
  console.log('ReliAPI JavaScript Basic Example\n');
  
  await httpProxyExample();
  await llmProxyExample();
  await errorHandlingExample();
  await streamingExample();
})();

