/**
 * Rust example for ReliAPI
 * 
 * This example demonstrates:
 * - Basic HTTP proxy usage
 * - Basic LLM proxy usage
 * - Error handling
 * - JSON serialization/deserialization
 * 
 * Requirements:
 *   Add to Cargo.toml:
 *   [dependencies]
 *   reqwest = { version = "0.11", features = ["json"] }
 *   serde = { version = "1.0", features = ["derive"] }
 *   serde_json = "1.0"
 *   tokio = { version = "1", features = ["full"] }
 * 
 * Usage:
 *   cargo run --example rust_example
 */

use reqwest::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;

// Configuration
fn get_reliapi_url() -> String {
    env::var("RELIAPI_URL").unwrap_or_else(|_| "https://reliapi.kikuai.dev".to_string())
}

fn get_api_key() -> String {
    env::var("RAPIDAPI_KEY")
        .or_else(|_| env::var("RELIAPI_API_KEY"))
        .unwrap_or_else(|_| "your-api-key".to_string())
}

// Types
#[derive(Serialize)]
struct LLMRequest {
    target: String,
    messages: Vec<HashMap<String, String>>,
    model: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<u32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    temperature: Option<f64>,
    #[serde(skip_serializing_if = "Option::is_none")]
    stream: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    idempotency_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache: Option<u32>,
}

#[derive(Serialize)]
struct HTTPRequest {
    target: String,
    method: String,
    path: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    headers: Option<HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    query: Option<HashMap<String, String>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    body: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    idempotency_key: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    cache: Option<u32>,
}

#[derive(Deserialize)]
struct ReliAPIResponse {
    data: serde_json::Value,
    meta: Meta,
}

#[derive(Deserialize)]
struct Meta {
    request_id: String,
    cache_hit: bool,
    idempotent_hit: bool,
    #[serde(default)]
    cost_usd: Option<f64>,
    duration_ms: u64,
}

// HTTP proxy example
async fn http_proxy_example(client: &Client, url: &str, api_key: &str) {
    println!("=== HTTP Proxy Example ===");

    let request = HTTPRequest {
        target: "jsonplaceholder".to_string(),
        method: "GET".to_string(),
        path: "/posts/1".to_string(),
        headers: None,
        query: None,
        body: None,
        idempotency_key: Some(format!("http-{}", chrono::Utc::now().timestamp())),
        cache: Some(300),
    };

    let response = client
        .post(&format!("{}/proxy/http", url))
        .header("X-RapidAPI-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&request)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                let data: ReliAPIResponse = resp.json().await.unwrap();
                println!("Success: Cache hit: {}, Request ID: {}", data.meta.cache_hit, data.meta.request_id);
            } else {
                let text = resp.text().await.unwrap();
                println!("Error: {} - {}", resp.status(), text);
            }
        }
        Err(e) => println!("Request error: {}", e),
    }
}

// LLM proxy example
async fn llm_proxy_example(client: &Client, url: &str, api_key: &str) {
    println!("\n=== LLM Proxy Example ===");

    let mut messages = Vec::new();
    let mut msg = HashMap::new();
    msg.insert("role".to_string(), "user".to_string());
    msg.insert("content".to_string(), "What is idempotency in API design? Explain in one sentence.".to_string());
    messages.push(msg);

    let request = LLMRequest {
        target: "openai".to_string(),
        messages,
        model: "gpt-4o-mini".to_string(),
        max_tokens: Some(100),
        temperature: None,
        stream: None,
        idempotency_key: Some(format!("rust-example-{}", chrono::Utc::now().timestamp())),
        cache: Some(3600),
    };

    let response = client
        .post(&format!("{}/proxy/llm", url))
        .header("X-RapidAPI-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&request)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                let data: ReliAPIResponse = resp.json().await.unwrap();
                
                // Extract content from nested JSON structure
                if let Some(choices) = data.data.get("choices").and_then(|c| c.as_array()) {
                    if let Some(choice) = choices.get(0) {
                        if let Some(message) = choice.get("message") {
                            if let Some(content) = message.get("content").and_then(|c| c.as_str()) {
                                println!("Response: {}", content);
                            }
                        }
                    }
                }
                
                if let Some(cost) = data.meta.cost_usd {
                    println!("Cost: ${:.6}", cost);
                }
                println!("Cache hit: {}", data.meta.cache_hit);
                println!("Request ID: {}", data.meta.request_id);
            } else {
                let text = resp.text().await.unwrap();
                println!("Error: {} - {}", resp.status(), text);
            }
        }
        Err(e) => println!("Request error: {}", e),
    }
}

// Caching example
async fn caching_example(client: &Client, url: &str, api_key: &str) {
    println!("\n=== Caching Example ===");

    let mut messages = Vec::new();
    let mut msg = HashMap::new();
    msg.insert("role".to_string(), "user".to_string());
    msg.insert("content".to_string(), "What is circuit breaker pattern?".to_string());
    messages.push(msg);

    let request = LLMRequest {
        target: "openai".to_string(),
        messages: messages.clone(),
        model: "gpt-4o-mini".to_string(),
        max_tokens: Some(100),
        temperature: None,
        stream: None,
        idempotency_key: None,
        cache: Some(3600),
    };

    // First request
    println!("First request (will call OpenAI API):");
    let resp1 = client
        .post(&format!("{}/proxy/llm", url))
        .header("X-RapidAPI-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&request)
        .send()
        .await;

    if let Ok(resp) = resp1 {
        if resp.status().is_success() {
            let data1: ReliAPIResponse = resp.json().await.unwrap();
            println!("Cache hit: {}, Cost: ${:.6}", 
                data1.meta.cache_hit, 
                data1.meta.cost_usd.unwrap_or(0.0));
        }
    }

    // Second request - should be cached
    println!("\nSecond request (same question - should be cached, FREE!):");
    let resp2 = client
        .post(&format!("{}/proxy/llm", url))
        .header("X-RapidAPI-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&request)
        .send()
        .await;

    if let Ok(resp) = resp2 {
        if resp.status().is_success() {
            let data2: ReliAPIResponse = resp.json().await.unwrap();
            println!("Cache hit: {}, Cost: ${:.6}", 
                data2.meta.cache_hit, 
                data2.meta.cost_usd.unwrap_or(0.0));
            if data2.meta.cache_hit {
                println!("✅ Second request was FREE (served from cache)!");
            }
        }
    }
}

// Error handling example
async fn error_handling_example(client: &Client, url: &str, api_key: &str) {
    println!("\n=== Error Handling Example ===");

    let mut messages = Vec::new();
    let mut msg = HashMap::new();
    msg.insert("role".to_string(), "user".to_string());
    msg.insert("content".to_string(), "Test".to_string());
    messages.push(msg);

    let request = LLMRequest {
        target: "openai".to_string(),
        messages,
        model: "gpt-4o-mini".to_string(),
        max_tokens: Some(100000), // May exceed budget cap
        temperature: None,
        stream: None,
        idempotency_key: None,
        cache: None,
    };

    let response = client
        .post(&format!("{}/proxy/llm", url))
        .header("X-RapidAPI-Key", api_key)
        .header("Content-Type", "application/json")
        .json(&request)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                println!("Success!");
            } else {
                let text = resp.text().await.unwrap();
                println!("Error: {} - {}", resp.status(), text);
            }
        }
        Err(e) => println!("Request error: {}", e),
    }
}

#[tokio::main]
async fn main() {
    println!("ReliAPI Rust Example\n");

    let url = get_reliapi_url();
    let api_key = get_api_key();
    let client = Client::new();

    http_proxy_example(&client, &url, &api_key).await;
    llm_proxy_example(&client, &url, &api_key).await;
    caching_example(&client, &url, &api_key).await;
    error_handling_example(&client, &url, &api_key).await;

    println!("\n=== Examples Completed ===");
    println!("\nBenefits of ReliAPI:");
    println!("  ✓ Automatic retries on failures");
    println!("  ✓ Caching reduces costs by 50-80%");
    println!("  ✓ Idempotency prevents duplicate charges");
    println!("  ✓ Budget caps prevent surprise bills");
    println!("  ✓ Circuit breaker prevents cascading failures");
}














