package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"time"
)

// Configuration
var (
	reliapiURL = getEnv("RELIAPI_URL", "https://reliapi.kikuai.dev")
	apiKey     = getEnv("RAPIDAPI_KEY", getEnv("RELIAPI_API_KEY", "your-api-key"))
)

// Types
type LLMRequest struct {
	Target         string                   `json:"target"`
	Messages       []map[string]interface{} `json:"messages"`
	Model          string                   `json:"model"`
	MaxTokens      *int                     `json:"max_tokens,omitempty"`
	Temperature    *float64                 `json:"temperature,omitempty"`
	Stream         *bool                    `json:"stream,omitempty"`
	IdempotencyKey *string                  `json:"idempotency_key,omitempty"`
	Cache          *int                     `json:"cache,omitempty"`
}

type HTTPRequest struct {
	Target         string            `json:"target"`
	Method         string            `json:"method"`
	Path           string            `json:"path"`
	Headers        map[string]string  `json:"headers,omitempty"`
	Query          map[string]interface{} `json:"query,omitempty"`
	Body           *string           `json:"body,omitempty"`
	IdempotencyKey *string           `json:"idempotency_key,omitempty"`
	Cache          *int              `json:"cache,omitempty"`
}

type ReliAPIResponse struct {
	Data interface{} `json:"data"`
	Meta struct {
		RequestID     string  `json:"request_id"`
		CacheHit      bool    `json:"cache_hit"`
		IdempotentHit bool    `json:"idempotent_hit"`
		CostUSD       *float64 `json:"cost_usd,omitempty"`
		DurationMs    int     `json:"duration_ms"`
	} `json:"meta"`
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

// HTTP proxy example
func httpProxyExample() {
	fmt.Println("=== HTTP Proxy Example ===")

	reqBody := HTTPRequest{
		Target: "jsonplaceholder",
		Method: "GET",
		Path:   "/posts/1",
		Cache:  intPtr(300),
	}

	jsonData, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", reliapiURL+"/proxy/http", bytes.NewBuffer(jsonData))
	req.Header.Set("X-RapidAPI-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var data ReliAPIResponse
		json.NewDecoder(resp.Body).Decode(&data)
		fmt.Printf("Success: Cache hit: %v, Request ID: %s\n", data.Meta.CacheHit, data.Meta.RequestID)
	} else {
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("Error: %d - %s\n", resp.StatusCode, string(body))
	}
}

// LLM proxy example
func llmProxyExample() {
	fmt.Println("\n=== LLM Proxy Example ===")

	maxTokens := 100
	cache := 3600
	idempotencyKey := fmt.Sprintf("go-example-%d", time.Now().Unix())

	reqBody := LLMRequest{
		Target: "openai",
		Messages: []map[string]interface{}{
			{"role": "user", "content": "What is idempotency in API design? Explain in one sentence."},
		},
		Model:          "gpt-4o-mini",
		MaxTokens:      &maxTokens,
		IdempotencyKey: &idempotencyKey,
		Cache:          &cache,
	}

	jsonData, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", reliapiURL+"/proxy/llm", bytes.NewBuffer(jsonData))
	req.Header.Set("X-RapidAPI-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		var data ReliAPIResponse
		json.NewDecoder(resp.Body).Decode(&data)
		
		// Extract content from nested structure
		if dataMap, ok := data.Data.(map[string]interface{}); ok {
			if choices, ok := dataMap["choices"].([]interface{}); ok && len(choices) > 0 {
				if choice, ok := choices[0].(map[string]interface{}); ok {
					if message, ok := choice["message"].(map[string]interface{}); ok {
						if content, ok := message["content"].(string); ok {
							fmt.Printf("Response: %s\n", content)
						}
					}
				}
			}
		}
		
		if data.Meta.CostUSD != nil {
			fmt.Printf("Cost: $%.6f\n", *data.Meta.CostUSD)
		}
		fmt.Printf("Cache hit: %v\n", data.Meta.CacheHit)
		fmt.Printf("Request ID: %s\n", data.Meta.RequestID)
	} else {
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("Error: %d - %s\n", resp.StatusCode, string(body))
	}
}

// Caching example
func cachingExample() {
	fmt.Println("\n=== Caching Example ===")

	cache := 3600
	reqBody := LLMRequest{
		Target: "openai",
		Messages: []map[string]interface{}{
			{"role": "user", "content": "What is circuit breaker pattern?"},
		},
		Model: "gpt-4o-mini",
		Cache: &cache,
	}

	jsonData, _ := json.Marshal(reqBody)

	// First request
	fmt.Println("First request (will call OpenAI API):")
	req1, _ := http.NewRequest("POST", reliapiURL+"/proxy/llm", bytes.NewBuffer(jsonData))
	req1.Header.Set("X-RapidAPI-Key", apiKey)
	req1.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 60 * time.Second}
	resp1, _ := client.Do(req1)
	if resp1.StatusCode == 200 {
		var data1 ReliAPIResponse
		json.NewDecoder(resp1.Body).Decode(&data1)
		fmt.Printf("Cache hit: %v, Cost: $%.6f\n", data1.Meta.CacheHit, *data1.Meta.CostUSD)
	}
	resp1.Body.Close()

	// Second request - should be cached
	fmt.Println("\nSecond request (same question - should be cached, FREE!):")
	req2, _ := http.NewRequest("POST", reliapiURL+"/proxy/llm", bytes.NewBuffer(jsonData))
	req2.Header.Set("X-RapidAPI-Key", apiKey)
	req2.Header.Set("Content-Type", "application/json")

	resp2, _ := client.Do(req2)
	if resp2.StatusCode == 200 {
		var data2 ReliAPIResponse
		json.NewDecoder(resp2.Body).Decode(&data2)
		fmt.Printf("Cache hit: %v, Cost: $%.6f\n", data2.Meta.CacheHit, *data2.Meta.CostUSD)
		if data2.Meta.CacheHit {
			fmt.Println("✅ Second request was FREE (served from cache)!")
		}
	}
	resp2.Body.Close()
}

// Error handling example
func errorHandlingExample() {
	fmt.Println("\n=== Error Handling Example ===")

	maxTokens := 100000 // May exceed budget cap
	reqBody := LLMRequest{
		Target: "openai",
		Messages: []map[string]interface{}{
			{"role": "user", "content": "Test"},
		},
		MaxTokens: &maxTokens,
	}

	jsonData, _ := json.Marshal(reqBody)
	req, _ := http.NewRequest("POST", reliapiURL+"/proxy/llm", bytes.NewBuffer(jsonData))
	req.Header.Set("X-RapidAPI-Key", apiKey)
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{Timeout: 60 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Printf("Request error: %v\n", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode == 200 {
		fmt.Println("Success!")
	} else {
		body, _ := io.ReadAll(resp.Body)
		fmt.Printf("Error: %d - %s\n", resp.StatusCode, string(body))
	}
}

func intPtr(i int) *int {
	return &i
}

func main() {
	fmt.Println("ReliAPI Go Example\n")

	httpProxyExample()
	llmProxyExample()
	cachingExample()
	errorHandlingExample()

	fmt.Println("\n=== Examples Completed ===")
	fmt.Println("\nBenefits of ReliAPI:")
	fmt.Println("  ✓ Automatic retries on failures")
	fmt.Println("  ✓ Caching reduces costs by 50-80%")
	fmt.Println("  ✓ Idempotency prevents duplicate charges")
	fmt.Println("  ✓ Budget caps prevent surprise bills")
	fmt.Println("  ✓ Circuit breaker prevents cascading failures")
}














