"""Tests for RouteLLM integration."""
import pytest
from unittest.mock import MagicMock

from reliapi.integrations.routellm import (
    RouteLLMDecision,
    extract_routellm_decision,
    apply_routellm_overrides,
    get_provider_from_target,
    RouteLLMMetrics,
    ROUTELLM_PROVIDER_HEADER,
    ROUTELLM_MODEL_HEADER,
    ROUTELLM_DECISION_ID_HEADER,
    ROUTELLM_ROUTE_NAME_HEADER,
    ROUTELLM_REASON_HEADER,
)


class TestRouteLLMDecision:
    """Tests for RouteLLMDecision dataclass."""
    
    def test_default_values(self):
        """Test default values are None."""
        decision = RouteLLMDecision()
        assert decision.provider is None
        assert decision.model is None
        assert decision.decision_id is None
        assert decision.route_name is None
        assert decision.reason is None
    
    def test_has_override_false(self):
        """Test has_override returns False when no overrides."""
        decision = RouteLLMDecision()
        assert not decision.has_override
    
    def test_has_override_with_provider(self):
        """Test has_override returns True with provider."""
        decision = RouteLLMDecision(provider="openai")
        assert decision.has_override
    
    def test_has_override_with_model(self):
        """Test has_override returns True with model."""
        decision = RouteLLMDecision(model="gpt-4o")
        assert decision.has_override
    
    def test_has_override_with_both(self):
        """Test has_override returns True with both provider and model."""
        decision = RouteLLMDecision(provider="openai", model="gpt-4o")
        assert decision.has_override
    
    def test_to_response_headers_empty(self):
        """Test response headers generation with no data."""
        decision = RouteLLMDecision()
        headers = decision.to_response_headers()
        assert headers == {}
    
    def test_to_response_headers_full(self):
        """Test response headers generation with all data."""
        decision = RouteLLMDecision(
            provider="openai",
            model="gpt-4o",
            decision_id="dec-123",
        )
        headers = decision.to_response_headers()
        
        assert "X-ReliAPI-Provider" in headers
        assert headers["X-ReliAPI-Provider"] == "openai"
        assert "X-ReliAPI-Model" in headers
        assert headers["X-ReliAPI-Model"] == "gpt-4o"
        assert "X-ReliAPI-Decision-ID" in headers
        assert headers["X-ReliAPI-Decision-ID"] == "dec-123"
    
    def test_to_log_context(self):
        """Test log context generation."""
        decision = RouteLLMDecision(
            provider="anthropic",
            model="claude-3-opus",
            decision_id="dec-456",
            route_name="premium_route",
            reason="High complexity query",
        )
        context = decision.to_log_context()
        
        assert context["routellm_provider"] == "anthropic"
        assert context["routellm_model"] == "claude-3-opus"
        assert context["routellm_decision_id"] == "dec-456"
        assert context["routellm_route_name"] == "premium_route"
        assert context["routellm_reason"] == "High complexity query"
    
    def test_to_log_context_excludes_none(self):
        """Test log context excludes None values."""
        decision = RouteLLMDecision(provider="openai")
        context = decision.to_log_context()
        
        assert "routellm_provider" in context
        assert "routellm_model" not in context
        assert "routellm_decision_id" not in context


class TestExtractRouteLLMDecision:
    """Tests for extract_routellm_decision function."""
    
    def test_no_headers(self):
        """Test extraction with no RouteLLM headers."""
        headers = {"Content-Type": "application/json"}
        result = extract_routellm_decision(headers)
        assert result is None
    
    def test_provider_only(self):
        """Test extraction with provider header only."""
        headers = {ROUTELLM_PROVIDER_HEADER: "openai"}
        result = extract_routellm_decision(headers)
        
        assert result is not None
        assert result.provider == "openai"
        assert result.model is None
    
    def test_model_only(self):
        """Test extraction with model header only."""
        headers = {ROUTELLM_MODEL_HEADER: "gpt-4o"}
        result = extract_routellm_decision(headers)
        
        assert result is not None
        assert result.model == "gpt-4o"
        assert result.provider is None
    
    def test_all_headers(self):
        """Test extraction with all RouteLLM headers."""
        headers = {
            ROUTELLM_PROVIDER_HEADER: "anthropic",
            ROUTELLM_MODEL_HEADER: "claude-3-opus",
            ROUTELLM_DECISION_ID_HEADER: "dec-789",
            ROUTELLM_ROUTE_NAME_HEADER: "complex_queries",
            ROUTELLM_REASON_HEADER: "Query complexity > 0.8",
        }
        result = extract_routellm_decision(headers)
        
        assert result is not None
        assert result.provider == "anthropic"
        assert result.model == "claude-3-opus"
        assert result.decision_id == "dec-789"
        assert result.route_name == "complex_queries"
        assert result.reason == "Query complexity > 0.8"
    
    def test_case_insensitive_headers(self):
        """Test extraction handles case-insensitive headers."""
        headers = {
            "x-routellm-provider": "openai",
            "x-routellm-model": "gpt-4o",
        }
        result = extract_routellm_decision(headers)
        
        assert result is not None
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
    
    def test_decision_id_only(self):
        """Test extraction with decision ID only (for correlation)."""
        headers = {ROUTELLM_DECISION_ID_HEADER: "dec-correlation-only"}
        result = extract_routellm_decision(headers)
        
        assert result is not None
        assert result.decision_id == "dec-correlation-only"
        assert not result.has_override  # No provider/model override


class TestApplyRouteLLMOverrides:
    """Tests for apply_routellm_overrides function."""
    
    @pytest.fixture
    def targets(self):
        """Sample targets configuration."""
        return {
            "openai": {
                "base_url": "https://api.openai.com",
                "llm": {"provider": "openai"},
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com",
                "llm": {"provider": "anthropic"},
            },
            "mistral": {
                "base_url": "https://api.mistral.ai",
                "llm": {"provider": "mistral"},
            },
        }
    
    def test_no_decision(self, targets):
        """Test no overrides when decision is None."""
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, None
        )
        assert target == "openai"
        assert model == "gpt-4o"
    
    def test_no_override_in_decision(self, targets):
        """Test no overrides when decision has no provider/model."""
        decision = RouteLLMDecision(decision_id="dec-123")
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        assert target == "openai"
        assert model == "gpt-4o"
    
    def test_provider_override(self, targets):
        """Test provider override."""
        decision = RouteLLMDecision(provider="anthropic")
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        assert target == "anthropic"
        assert model == "gpt-4o"
    
    def test_model_override(self, targets):
        """Test model override."""
        decision = RouteLLMDecision(model="gpt-4-turbo")
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        assert target == "openai"  # Target unchanged
        assert model == "gpt-4-turbo"  # Model changed
    
    def test_both_overrides(self, targets):
        """Test both provider and model override."""
        decision = RouteLLMDecision(
            provider="anthropic",
            model="claude-3-sonnet",
        )
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        assert target == "anthropic"
        assert model == "claude-3-sonnet"
    
    def test_provider_not_found(self, targets):
        """Test provider override when provider not in targets."""
        decision = RouteLLMDecision(provider="unknown_provider")
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        # Should fall back to direct target name match
        assert target == "openai"  # Unchanged since not found
        assert model == "gpt-4o"
    
    def test_direct_target_name_match(self, targets):
        """Test direct target name match when provider lookup fails."""
        decision = RouteLLMDecision(provider="mistral")
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        assert target == "mistral"  # Direct match in targets


class TestGetProviderFromTarget:
    """Tests for get_provider_from_target function."""
    
    def test_provider_exists(self):
        """Test getting provider from target config."""
        targets = {
            "my_openai": {
                "llm": {"provider": "openai"},
            },
        }
        provider = get_provider_from_target("my_openai", targets)
        assert provider == "openai"
    
    def test_target_not_found(self):
        """Test when target not in config."""
        targets = {}
        provider = get_provider_from_target("nonexistent", targets)
        assert provider is None
    
    def test_no_llm_config(self):
        """Test when target has no LLM config."""
        targets = {
            "http_target": {
                "base_url": "https://api.example.com",
            },
        }
        provider = get_provider_from_target("http_target", targets)
        assert provider is None


class TestRouteLLMMetrics:
    """Tests for RouteLLMMetrics class."""
    
    def test_record_decision_none(self):
        """Test recording None decision."""
        metrics = RouteLLMMetrics()
        metrics.record_decision(None)  # Should not raise
        assert metrics.get_stats()["decisions_total"] == {}
    
    def test_record_decision_with_route_name(self):
        """Test recording decision with route name."""
        metrics = RouteLLMMetrics()
        decision = RouteLLMDecision(route_name="premium_route")
        metrics.record_decision(decision)
        
        stats = metrics.get_stats()
        assert stats["decisions_total"]["premium_route"] == 1
    
    def test_record_decision_unknown_route(self):
        """Test recording decision without route name."""
        metrics = RouteLLMMetrics()
        decision = RouteLLMDecision()
        metrics.record_decision(decision)
        
        stats = metrics.get_stats()
        assert stats["decisions_total"]["unknown"] == 1
    
    def test_record_multiple_decisions(self):
        """Test recording multiple decisions."""
        metrics = RouteLLMMetrics()
        
        metrics.record_decision(RouteLLMDecision(route_name="route_a"))
        metrics.record_decision(RouteLLMDecision(route_name="route_a"))
        metrics.record_decision(RouteLLMDecision(route_name="route_b"))
        
        stats = metrics.get_stats()
        assert stats["decisions_total"]["route_a"] == 2
        assert stats["decisions_total"]["route_b"] == 1
    
    def test_record_overrides(self):
        """Test recording override statistics."""
        metrics = RouteLLMMetrics()
        
        decision = RouteLLMDecision(provider="openai", model="gpt-4o")
        metrics.record_decision(decision)
        
        stats = metrics.get_stats()
        assert "openai:gpt-4o" in stats["overrides_applied"]
        assert stats["overrides_applied"]["openai:gpt-4o"] == 1
    
    def test_no_override_recorded_without_has_override(self):
        """Test overrides not recorded when no override present."""
        metrics = RouteLLMMetrics()
        decision = RouteLLMDecision(decision_id="dec-123")  # No override
        metrics.record_decision(decision)
        
        stats = metrics.get_stats()
        assert stats["overrides_applied"] == {}


class TestIntegration:
    """Integration tests for RouteLLM functionality."""
    
    def test_full_routing_flow(self):
        """Test full routing flow from headers to overrides."""
        headers = {
            "X-RouteLLM-Provider": "anthropic",
            "X-RouteLLM-Model": "claude-3-opus",
            "X-RouteLLM-Decision-ID": "dec-integration-test",
            "X-RouteLLM-Route-Name": "premium_queries",
            "X-RouteLLM-Reason": "User requested premium model",
        }
        
        targets = {
            "openai": {"llm": {"provider": "openai"}},
            "anthropic": {"llm": {"provider": "anthropic"}},
        }
        
        # Extract decision
        decision = extract_routellm_decision(headers)
        assert decision is not None
        assert decision.has_override
        
        # Apply overrides
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        
        assert target == "anthropic"
        assert model == "claude-3-opus"
        
        # Check response headers
        response_headers = decision.to_response_headers()
        assert "X-ReliAPI-Provider" in response_headers
        assert "X-ReliAPI-Model" in response_headers
        assert "X-ReliAPI-Decision-ID" in response_headers
    
    def test_correlation_only_flow(self):
        """Test flow with decision ID only (correlation without override)."""
        headers = {
            "X-RouteLLM-Decision-ID": "dec-correlation",
        }
        
        targets = {
            "openai": {"llm": {"provider": "openai"}},
        }
        
        decision = extract_routellm_decision(headers)
        assert decision is not None
        assert not decision.has_override
        
        # No overrides should be applied
        target, model = apply_routellm_overrides(
            "openai", "gpt-4o", targets, decision
        )
        
        assert target == "openai"
        assert model == "gpt-4o"
        
        # But correlation ID should be in response
        response_headers = decision.to_response_headers()
        assert "X-ReliAPI-Decision-ID" in response_headers
        assert response_headers["X-ReliAPI-Decision-ID"] == "dec-correlation"


