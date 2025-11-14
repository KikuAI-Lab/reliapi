# Contributing to ReliAPI

Thank you for your interest in contributing to ReliAPI!

---

## Code of Conduct

- Be respectful and inclusive
- Focus on what is best for the project
- Show empathy towards other contributors

---

## How to Contribute

### Reporting Bugs

1. Check if bug already exists in issues
2. Create new issue with:
   - Clear description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment (OS, Python version, etc.)

### Suggesting Features

1. Check if feature already exists in issues
2. Create new issue with:
   - Use case description
   - Proposed solution
   - Alternatives considered

### Submitting Pull Requests

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes following code style
4. Add tests if applicable
5. Update documentation if needed
6. Commit with clear messages
7. Push to your fork
8. Create Pull Request

---

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/KikuAI-Lab/reliapi.git
cd reliapi
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Create a `config.yaml` file (see `config.example.yaml` for reference):

```yaml
targets:
  openai:
    base_url: "https://api.openai.com/v1"
    timeout_ms: 20000
    llm:
      provider: "openai"
      default_model: "gpt-4o-mini"
    auth:
      type: bearer_env
      env_var: OPENAI_API_KEY
```

Set environment variables:

```bash
export RELIAPI_CONFIG_PATH=config.yaml
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=sk-...  # Your API key
```

### 5. Run Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=reliapi --cov-report=html

# Run specific test file
pytest tests/test_cache.py
```

### 6. Run Locally (Development Mode)

**Option A: Direct Python**

```bash
uvicorn reliapi.app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Option B: Docker Compose**

1. Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  reliapi:
    build: .
    ports:
      - "8000:8000"
    environment:
      - RELIAPI_CONFIG_PATH=/app/config.yaml
      - REDIS_URL=redis://redis:6379/0
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    volumes:
      - ./config.yaml:/app/config.yaml:ro
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

2. Run:

```bash
docker compose up
```

3. Verify:

```bash
curl http://localhost:8000/healthz
```

### 7. Development Workflow

1. Make code changes
2. Run tests: `pytest tests/`
3. Test manually: `curl http://localhost:8000/proxy/llm ...`
4. Check logs: Application logs to stdout/stderr
5. Commit with clear messages

### 8. Testing with Real APIs

For integration testing, you can use mock targets or real API keys:

```yaml
targets:
  # Mock target for testing
  test_api:
    base_url: "https://httpbin.org"
    timeout_ms: 5000
    cache:
      enabled: true
      ttl_s: 60
```

Test with:

```bash
curl -X POST http://localhost:8000/proxy/http \
  -H "Content-Type: application/json" \
  -d '{"target": "test_api", "method": "GET", "path": "/get"}'
```

---

## Code Style

- Follow PEP 8 for Python code
- Use type hints where applicable
- Keep functions small and focused
- Add docstrings for public APIs

---

## Testing

- Write tests for new features
- Ensure all tests pass before submitting PR
- Aim for >80% code coverage

---

## Documentation

- Update README.md if adding features
- Add examples for new functionality
- Update API docs if changing endpoints

---

## Questions?

Open an issue or discussion for questions.

---

Thank you for contributing to ReliAPI!

