# Configuration

ReliAPI uses a single YAML configuration file (`config.yaml`) to define targets and their reliability policies.

---

## Configuration Structure

```yaml
targets:
  target_name:
    base_url: "https://api.example.com"
    timeout_ms: 10000
    circuit:
      error_threshold: 5
      cooldown_s: 60
    cache:
      ttl_s: 300
      enabled: true
    auth:
      type: bearer_env
      env_var: API_KEY
    retry_matrix:
      "429": { attempts: 3, backoff: "exp-jitter", base_s: 1.0 }
      "5xx": { attempts: 2, backoff: "exp-jitter", base_s: 1.0 }
      "net": { attempts: 2, backoff: "exp-jitter", base_s: 1.0 }
```

---

## Target Configuration

### Required Fields

- **`base_url`**: Upstream API base URL (e.g., `"https://api.example.com"`)

### Optional Fields

- **`timeout_ms`**: Request timeout in milliseconds (default: `20000`)
- **`circuit`**: Circuit breaker configuration
- **`cache`**: Cache configuration
- **`auth`**: Authentication configuration
- **`retry_matrix`**: Retry policy configuration
- **`fallback_targets`**: List of fallback target names
- **`llm`**: LLM-specific configuration (for LLM targets)

---

## HTTP-Only Target Example

```yaml
targets:
  my_api:
    base_url: "https://api.example.com"
    timeout_ms: 10000
    
    circuit:
      error_threshold: 5      # Open circuit after 5 failures
      cooldown_s: 60          # Stay open for 60 seconds
    
    cache:
      ttl_s: 300              # Cache for 5 minutes
      enabled: true
    
    auth:
      type: bearer_env
      env_var: API_KEY        # Read from environment variable
    
    retry_matrix:
      "429":                  # Rate limit errors
        attempts: 3
        backoff: "exp-jitter"
        base_s: 1.0
        max_s: 60.0
      "5xx":                  # Server errors
        attempts: 2
        backoff: "exp-jitter"
        base_s: 1.0
      "net":                  # Network errors
        attempts: 2
        backoff: "exp-jitter"
        base_s: 1.0
```

---

## LLM Target Example

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    timeout_ms: 20000
    
    circuit:
      error_threshold: 5
      cooldown_s: 60
    
    llm:
      provider: "openai"                    # Explicit provider
      default_model: "gpt-4o-mini"          # Default model
      max_tokens: 1024                      # Max tokens limit
      temperature: 0.7                      # Temperature limit
      
      # Budget control
      soft_cost_cap_usd: 0.01              # Throttle if exceeded
      hard_cost_cap_usd: 0.05              # Reject if exceeded
    
    cache:
      ttl_s: 3600                          # Cache for 1 hour
      enabled: true
    
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
    
    fallback_targets: ["anthropic", "mistral"]  # Fallback chain
    
    retry_matrix:
      "429":
        attempts: 3
        backoff: "exp-jitter"
        base_s: 1.0
        max_s: 60.0
      "5xx":
        attempts: 2
        backoff: "exp-jitter"
        base_s: 1.0
      "net":
        attempts: 2
        backoff: "exp-jitter"
        base_s: 1.0
```

---

## Field Reference

### `timeout_ms`

Request timeout in milliseconds.

- **Default**: `20000` (20 seconds)
- **Example**: `timeout_ms: 10000`

### `circuit`

Circuit breaker configuration.

- **`error_threshold`**: Number of consecutive failures before opening circuit (default: `5`)
- **`cooldown_s`**: Seconds to keep circuit open (default: `60`)

### `cache`

Cache configuration.

- **`ttl_s`**: Time-to-live in seconds (default: `3600`)
- **`enabled`**: Enable/disable caching (default: `true`)

### `auth`

Authentication configuration.

- **`type`**: Auth type (`bearer_env`, `bearer_static`)
- **`env_var`**: Environment variable name (for `bearer_env`)
- **`token`**: Static token (for `bearer_static`)

### `retry_matrix`

Retry policy per error class.

- **`"429"`**: Rate limit errors
- **`"5xx"`**: Server errors (500-599)
- **`"net"`**: Network errors (timeout, connection)

Each error class supports:

- **`attempts`**: Number of retry attempts (default: `3`)
- **`backoff`**: Backoff strategy (`exp-jitter`, `linear`)
- **`base_s`**: Base delay in seconds (default: `1.0`)
- **`max_s`**: Maximum delay in seconds (default: `60.0`)

### `llm`

LLM-specific configuration (only for LLM targets).

- **`provider`**: Provider name (`openai`, `anthropic`, `mistral`)
- **`default_model`**: Default model name
- **`max_tokens`**: Maximum tokens limit
- **`temperature`**: Temperature limit
- **`soft_cost_cap_usd`**: Soft cost cap (throttle if exceeded)
- **`hard_cost_cap_usd`**: Hard cost cap (reject if exceeded)

### `fallback_targets`

List of fallback target names to try if primary target fails.

- **Example**: `fallback_targets: ["anthropic", "mistral"]`

---

## Environment Variables

ReliAPI reads configuration from environment variables:

- **`RELIAPI_CONFIG`**: Path to config file (default: `config.yaml`)
- **`REDIS_URL`**: Redis connection URL (default: `redis://localhost:6379/0`)
- **`LOG_LEVEL`**: Logging level (default: `INFO`)

Provider API keys (set as needed):

- **`OPENAI_API_KEY`**: OpenAI API key
- **`ANTHROPIC_API_KEY`**: Anthropic API key
- **`MISTRAL_API_KEY`**: Mistral API key

---

## Best Practices

### Keep Config Minimal

- Don't create YAML hell with excessive nesting
- Use sensible defaults
- Only override what you need

### Use Environment Variables

- Store API keys in environment variables
- Use `env_var` in auth config
- Don't commit secrets to config files

### Organize by Use Case

```yaml
targets:
  # Production LLM providers
  openai_prod:
    ...
  anthropic_prod:
    ...
  
  # Development/test providers
  openai_dev:
    ...
  
  # External APIs
  stripe:
    ...
  payment_gateway:
    ...
```

### Test Configuration

- Validate config before deploying
- Use health endpoints to verify targets
- Monitor metrics to ensure config works

---

## Configuration Examples

See `examples/config.http.yaml` and `examples/config.llm.yaml` for complete examples.

---

## Next Steps

- [Reliability Features](Reliability-Features.md) — Detailed feature explanations
- [Architecture](Architecture.md) — Architecture overview

