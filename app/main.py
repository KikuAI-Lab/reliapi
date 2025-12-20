"""ReliAPI FastAPI application - minimal reliability layer."""
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from typing import Dict, List, Optional
import hashlib

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from reliapi.app.schemas import HTTPProxyRequest, LLMProxyRequest
from reliapi.app.services import handle_http_proxy, handle_llm_proxy, handle_llm_stream_generator
from reliapi.config.loader import ConfigLoader
from reliapi.core.cache import Cache
from reliapi.core.errors import ErrorCode
from reliapi.core.idempotency import IdempotencyManager
from reliapi.core.client_profile import ClientProfileManager, ClientProfile
from reliapi.core.key_pool import KeyPoolManager, ProviderKey
from reliapi.core.rate_limiter import RateLimiter
from reliapi.core.rate_scheduler import RateScheduler
from reliapi.core.free_tier_restrictions import FreeTierRestrictions
from reliapi.core.security import SecurityManager
from reliapi.integrations.rapidapi import RapidAPIClient, SubscriptionTier
from reliapi.integrations.rapidapi_tenant import RapidAPITenantManager
from reliapi.integrations.routellm import (
    RouteLLMDecision,
    extract_routellm_decision,
    apply_routellm_overrides,
    routellm_metrics,
)
from reliapi.metrics.prometheus import (
    rapidapi_webhook_events_total,
    rapidapi_tier_cache_total,
    rapidapi_tier_distribution,
    routellm_decisions_total,
    routellm_overrides_total,
    free_tier_abuse_attempts_total,
)

# Configure structured JSON logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(message)s",  # JSON logs are already formatted
)
logger = logging.getLogger(__name__)

# Global state
config_loader: ConfigLoader = None
targets: Dict[str, Dict] = {}
cache: Cache = None
idempotency: IdempotencyManager = None
rate_limiter: RateLimiter = None
key_pool_manager: KeyPoolManager = None
rate_scheduler: RateScheduler = None
client_profile_manager: ClientProfileManager = None
rapidapi_client: RapidAPIClient = None
rapidapi_tenant_manager: RapidAPITenantManager = None


def verify_api_key(request: Request) -> tuple[Optional[str], Optional[str], str]:
    """Verify API key from header and resolve tenant and tier.
    
    Priority for tier detection:
    1. RapidAPI headers (X-RapidAPI-User, X-RapidAPI-Subscription)
    2. Redis cache (from previous RapidAPI detection)
    3. Config-based tenants
    4. Test key prefixes (sk-free, sk-dev, sk-pro)
    5. Default: 'free'
    
    Returns:
        Tuple of (api_key, tenant_name, tier). 
        tenant_name is None if multi-tenant not enabled or tenant not found.
        tier is 'free', 'developer', 'pro', or 'enterprise'.
    """
    api_key = request.headers.get("X-API-Key")
    
    # Get headers dict for RapidAPI detection
    headers_dict = dict(request.headers)
    
    # Helper to determine tier with RapidAPI priority
    def get_tier(api_key: str, headers: Dict[str, str]) -> str:
        # 1. Check RapidAPI headers first
        if rapidapi_client:
            result = rapidapi_client.get_tier_from_headers(headers)
            if result:
                user_id, tier_enum = result
                rapidapi_tier_cache_total.labels(operation="hit").inc()
                return tier_enum.value
        
        # 2. Use rate_limiter with RapidAPI client for cache lookup
        if rate_limiter and api_key:
            tier = rate_limiter.get_account_tier(api_key, headers, rapidapi_client)
            return tier
        
        return "free"
    
    # Multi-tenant mode: check tenants config
    if config_loader and hasattr(config_loader, 'config') and config_loader.config.tenants:
        tenants = config_loader.config.tenants
        # Find tenant by API key
        for tenant_name, tenant_config in tenants.items():
            if tenant_config.api_key == api_key:
                # Store tenant in request state for later use
                request.state.tenant = tenant_name
                tier = get_tier(api_key, headers_dict)
                request.state.tier = tier
                return api_key, tenant_name, tier
        
        # Tenant not found - check if global API key is set (backward compatibility)
        required_key = os.getenv("RELIAPI_API_KEY")
        if required_key and api_key == required_key:
            request.state.tenant = None  # No tenant, use default
            tier = get_tier(api_key, headers_dict)
            request.state.tier = tier
            return api_key, None, tier
        
        # No matching tenant and no global key match - allow with free tier
        tier = get_tier(api_key, headers_dict)
        request.state.tier = tier
        request.state.tenant = None
        return api_key, None, tier
    
    # Single-tenant mode: use global API key
    if not api_key:
        # Check if RapidAPI headers are present (RapidAPI handles auth)
        if rapidapi_client:
            result = rapidapi_client.get_tier_from_headers(headers_dict)
            if result:
                # RapidAPI user - create virtual API key from user ID
                user_id, tier_enum = result
                virtual_api_key = f"rapidapi:{user_id}"
                
                # Auto-create tenant for RapidAPI user
                if rapidapi_tenant_manager:
                    tenant_name = rapidapi_tenant_manager.ensure_tenant_exists(user_id, tier_enum)
                    request.state.tenant = tenant_name
                else:
                    request.state.tenant = None
                
                request.state.tier = tier_enum.value
                rapidapi_tier_cache_total.labels(operation="hit").inc()
                return virtual_api_key, request.state.tenant, tier_enum.value
        
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {
                    "type": "client_error",
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Missing X-API-Key header",
                    "retryable": False,
                    "target": None,
                    "status_code": 401,
                },
            },
        )
    
    # Determine tier
    tier = get_tier(api_key, headers_dict)
    
    # For testing: allow keys starting with sk-free/sk-dev/sk-pro to pass
    if api_key and (api_key.startswith("sk-free") or api_key.startswith("sk-dev") or api_key.startswith("sk-pro")):
        request.state.tenant = None
        request.state.tier = tier
        return api_key, None, tier
    
    # Check against required key
    required_key = os.getenv("RELIAPI_API_KEY")
    if not required_key:
        # No auth required if env var not set
        request.state.tenant = None
        request.state.tier = tier
        return api_key, None, tier
    
    if api_key != required_key:
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error": {
                    "type": "client_error",
                    "code": ErrorCode.UNAUTHORIZED.value,
                    "message": "Invalid API key",
                    "retryable": False,
                    "target": None,
                    "status_code": 401,
                },
            },
        )
    
    request.state.tenant = None  # No tenant in single-tenant mode
    request.state.tier = tier
    return api_key, None, tier


def detect_client_profile(request: Request, tenant: Optional[str] = None) -> Optional[str]:
    """Detect client profile using priority: X-Client header > tenant.profile > default.
    
    Args:
        request: FastAPI request
        tenant: Tenant name (if known)
        
    Returns:
        Profile name or None
    """
    # Priority 1: X-Client header
    client_header = request.headers.get("X-Client")
    if client_header and client_profile_manager and client_profile_manager.has_profile(client_header):
        return client_header
    
    # Priority 2: tenant.profile
    if tenant and config_loader:
        tenant_config = config_loader.get_tenant(tenant)
        if tenant_config and tenant_config.get("profile"):
            profile_name = tenant_config.get("profile")
            if client_profile_manager and client_profile_manager.has_profile(profile_name):
                return profile_name
    
    # Priority 3: default
    return "default"


def _init_client_profile_manager(config_loader: ConfigLoader) -> ClientProfileManager:
    """Initialize ClientProfileManager from configuration."""
    profiles_config = config_loader.get_client_profiles()
    if not profiles_config:
        return ClientProfileManager()
    
    profiles: Dict[str, ClientProfile] = {}
    
    for profile_name, profile_config in profiles_config.items():
        profile = ClientProfile(
            max_parallel_requests=profile_config.get("max_parallel_requests", 10),
            max_qps_per_tenant=profile_config.get("max_qps_per_tenant"),
            max_qps_per_provider_key=profile_config.get("max_qps_per_provider_key"),
            burst_size=profile_config.get("burst_size", 5),
            default_timeout_s=profile_config.get("default_timeout_s"),
        )
        profiles[profile_name] = profile
        logger.info(f"Initialized client profile: {profile_name}")
    
    return ClientProfileManager(profiles)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


def _validate_startup_config(config_loader: ConfigLoader, strict: bool = True) -> List[str]:
    """Validate configuration at startup.
    
    Args:
        config_loader: Configuration loader
        strict: If True, fail on missing required env vars
        
    Returns:
        List of validation warnings (non-fatal issues)
        
    Raises:
        ConfigValidationError: If configuration is invalid
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    # 1. Validate required environment variables
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        warnings.append("REDIS_URL not set - Redis features will be disabled")
    
    # RapidAPI API key is optional but recommended
    rapidapi_key = os.getenv("RAPIDAPI_API_KEY")
    if not rapidapi_key:
        warnings.append("RAPIDAPI_API_KEY not set - RapidAPI tier detection may be limited")
    
    # 2. Validate key pool configuration
    pools_config = config_loader.get_provider_key_pools()
    if pools_config:
        seen_key_ids: Dict[str, str] = {}  # key_id -> provider (for uniqueness check)
        
        for provider, pool_config in pools_config.items():
            keys_config = pool_config.get("keys", [])
            
            if not keys_config:
                warnings.append(f"Key pool for provider '{provider}' has no keys configured")
                continue
            
            for key_config in keys_config:
                key_id = key_config.get("id")
                api_key_str = key_config.get("api_key", "")
                qps_limit = key_config.get("qps_limit")
                rate_limit = key_config.get("rate_limit", {})
                
                # Check key ID is present
                if not key_id:
                    errors.append(f"Key in provider '{provider}' is missing 'id' field")
                    continue
                
                # Check key ID uniqueness (within provider)
                full_key_id = f"{provider}:{key_id}"
                if full_key_id in seen_key_ids:
                    errors.append(f"Duplicate key ID '{key_id}' in provider '{provider}'")
                else:
                    seen_key_ids[full_key_id] = provider
                
                # Check API key is present
                if not api_key_str:
                    errors.append(f"Key '{key_id}' in provider '{provider}' is missing 'api_key' field")
                    continue
                
                # Check env var exists if using env:VAR_NAME format
                if api_key_str.startswith("env:"):
                    env_var = api_key_str[4:]
                    if strict and not os.getenv(env_var):
                        errors.append(f"Environment variable '{env_var}' not set for key '{key_id}' in provider '{provider}'")
                
                # Check QPS limit is positive
                effective_qps = rate_limit.get("max_qps") or qps_limit
                if effective_qps is not None and effective_qps <= 0:
                    errors.append(f"Key '{key_id}' in provider '{provider}' has invalid QPS limit: {effective_qps} (must be > 0)")
    
    # 3. Validate client profiles configuration
    profiles_config = config_loader.get_client_profiles()
    if profiles_config:
        for profile_name, profile_config in profiles_config.items():
            max_parallel = profile_config.get("max_parallel_requests")
            if max_parallel is not None and max_parallel <= 0:
                errors.append(f"Client profile '{profile_name}' has invalid max_parallel_requests: {max_parallel} (must be > 0)")
            
            timeout = profile_config.get("default_timeout_s")
            if timeout is not None and timeout <= 0:
                errors.append(f"Client profile '{profile_name}' has invalid default_timeout_s: {timeout} (must be > 0)")
            
            max_qps_tenant = profile_config.get("max_qps_per_tenant")
            if max_qps_tenant is not None and max_qps_tenant <= 0:
                errors.append(f"Client profile '{profile_name}' has invalid max_qps_per_tenant: {max_qps_tenant} (must be > 0)")
            
            max_qps_key = profile_config.get("max_qps_per_provider_key")
            if max_qps_key is not None and max_qps_key <= 0:
                errors.append(f"Client profile '{profile_name}' has invalid max_qps_per_provider_key: {max_qps_key} (must be > 0)")
    
    # Log warnings
    for warning in warnings:
        logger.warning(f"Configuration warning: {warning}")
    
    # Fail fast on errors
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ConfigValidationError(f"Configuration validation failed with {len(errors)} error(s): {'; '.join(errors)}")
    
    return warnings


def _init_key_pool_manager(config_loader: ConfigLoader) -> Optional[KeyPoolManager]:
    """Initialize KeyPoolManager from configuration."""
    pools_config = config_loader.get_provider_key_pools()
    if not pools_config:
        return None
    
    pools: Dict[str, List[ProviderKey]] = {}
    
    for provider, pool_config in pools_config.items():
        keys = []
        for key_config in pool_config.get("keys", []):
            key_id = key_config.get("id")
            api_key_str = key_config.get("api_key", "")
            qps_limit = key_config.get("qps_limit")
            
            if not key_id:
                continue  # Already validated, skip
            
            # Resolve API key from env if needed
            if api_key_str.startswith("env:"):
                env_var = api_key_str[4:]
                api_key = os.getenv(env_var)
                if not api_key:
                    # Already validated in strict mode, skip silently
                    logger.debug(f"Skipping key {key_id}: env var {env_var} not set")
                    continue
            else:
                api_key = api_key_str
            
            # Get rate limit config if present
            rate_limit_config = key_config.get("rate_limit", {})
            if rate_limit_config:
                # Use rate_limit.max_qps if present, otherwise fallback to qps_limit
                qps_limit = rate_limit_config.get("max_qps") or qps_limit
                if qps_limit:
                    qps_limit = int(qps_limit)
            
            key = ProviderKey(
                id=key_id,
                provider=provider,
                key=api_key,
                qps_limit=qps_limit,
            )
            keys.append(key)
        
        if keys:
            pools[provider] = keys
            logger.info(f"Initialized key pool for {provider} with {len(keys)} keys")
    
    if pools:
        return KeyPoolManager(pools)
    return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global config_loader, targets, cache, idempotency, rate_limiter, key_pool_manager, rate_scheduler, client_profile_manager, rapidapi_client, rapidapi_tenant_manager
    
    # Startup
    config_path = os.getenv("RELIAPI_CONFIG_PATH", os.getenv("RELIAPI_CONFIG", "config.yaml"))
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    logger.info(f"Loading configuration from {config_path}")
    config_loader = ConfigLoader(config_path)
    config_loader.load()
    targets = config_loader.get_targets()
    
    # Validate configuration (fail fast on invalid config)
    # Set strict=False for development to allow missing env vars with warnings
    strict_validation = os.getenv("RELIAPI_STRICT_CONFIG", "true").lower() == "true"
    try:
        validation_warnings = _validate_startup_config(config_loader, strict=strict_validation)
        if validation_warnings:
            logger.info(f"Configuration loaded with {len(validation_warnings)} warning(s)")
    except ConfigValidationError as e:
        logger.critical(f"Configuration validation failed: {e}")
        raise
    
    logger.info(f"Initializing Redis connection: {redis_url}")
    cache = Cache(redis_url, key_prefix="reliapi")
    idempotency = IdempotencyManager(redis_url, key_prefix="reliapi")
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(redis_url, key_prefix="reliapi")
    
    # Initialize RapidAPI client
    rapidapi_client = RapidAPIClient(
        redis_url=redis_url,
        key_prefix="reliapi",
    )
    logger.info("RapidAPI client initialized")
    
    # Initialize RapidAPI tenant manager
    if cache and cache.client:
        rapidapi_tenant_manager = RapidAPITenantManager(
            redis_client=cache.client,
            key_prefix="reliapi",
        )
        logger.info("RapidAPI tenant manager initialized")
    
    # Initialize key pool manager
    key_pool_manager = _init_key_pool_manager(config_loader)
    if key_pool_manager:
        logger.info("Key pool manager initialized")
    else:
        logger.info("No key pools configured, using targets.auth")
    
    # Initialize rate scheduler with memory management
    rate_scheduler = RateScheduler(
        max_buckets=1000,
        bucket_ttl_seconds=3600,  # 1 hour TTL
        cleanup_interval_seconds=300,  # 5 minute cleanup interval
    )
    await rate_scheduler.start_cleanup_task()
    logger.info("Rate scheduler initialized with memory management")
    
    # Initialize client profile manager
    client_profile_manager = _init_client_profile_manager(config_loader)
    logger.info("Client profile manager initialized")
    
    logger.info(f"ReliAPI started with {len(targets)} targets")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ReliAPI...")
    if rate_scheduler:
        await rate_scheduler.stop_cleanup_task()
    if rapidapi_client:
        await rapidapi_client.close()


app = FastAPI(
    title="ReliAPI",
    version="1.0.7",
    description="ReliAPI is a small LLM reliability layer for HTTP and LLM calls: retries, circuit breaker, cache, idempotency, and budget caps. Idempotent LLM proxy with predictable AI costs. Self-hosted AI gateway focused on reliability, not features.",
    lifespan=lifespan,
)

# CORS middleware with production security
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
is_production = os.getenv("ENVIRONMENT", "").lower() == "production"

if cors_origins_env == "*":
    if is_production:
        # In production, warn if CORS_ORIGINS is "*" (security risk)
        logger.warning(
            "SECURITY WARNING: CORS_ORIGINS is set to '*' in production. "
            "This allows requests from any origin. Consider restricting to specific origins."
        )
    cors_origins = ["*"]
else:
    cors_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    # Validate origins (basic security check)
    validated_origins = []
    for origin in cors_origins:
        if not origin:
            continue
        # Basic validation: must start with http:// or https://
        if origin != "*" and not (origin.startswith("http://") or origin.startswith("https://")):
            logger.warning(f"Invalid CORS origin format (skipping): {origin}")
            continue
        # In production, don't allow wildcard subdomains without explicit configuration
        if is_production and origin == "*":
            logger.warning("Wildcard CORS origin '*' not recommended in production")
        validated_origins.append(origin)
    cors_origins = validated_origins

# Log CORS configuration
if is_production:
    logger.info(f"CORS configured for production with {len(cors_origins)} allowed origin(s)")
    if len(cors_origins) > 10:
        logger.warning(f"Large number of CORS origins ({len(cors_origins)}), consider consolidating")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    import traceback
    error_details = traceback.format_exc()
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}\n{error_details}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "type": "internal_error",
                "code": "INTERNAL_ERROR",
                "message": f"Internal server error: {str(exc)}",
                "retryable": True,
                "target": None,
                "status_code": 500,
            },
            "meta": {
                "target": None,
                "cache_hit": False,
                "retries": 0,
                "duration_ms": 0,
                "request_id": request.headers.get("X-Request-ID", "unknown"),
                "trace_id": request.headers.get("X-Trace-ID"),
            },
        },
    )


@app.get("/healthz")
async def healthz(http_request: Request):
    """Health check endpoint with optional rate limiting."""
    # Optional rate limiting for healthz (20 req/min per IP)
    if rate_limiter:
        client_ip = http_request.client.host if http_request.client else "unknown"
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=20, prefix="healthz")
        if not allowed:
            # For healthz, return 429 but don't log as warning (expected for monitoring)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded for healthz endpoint.",
                },
            )
    return {"status": "healthy"}


@app.get("/readyz")
async def readyz(http_request: Request):
    """Readiness check endpoint with optional rate limiting."""
    # Optional rate limiting for readyz (20 req/min per IP)
    if rate_limiter:
        client_ip = http_request.client.host if http_request.client else "unknown"
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=20, prefix="readyz")
        if not allowed:
            # For readyz, return 429 but don't log as warning (expected for monitoring)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded for readyz endpoint.",
                },
            )
    return {"status": "ready"}


@app.get("/livez")
async def livez(http_request: Request):
    """Liveness check endpoint with optional rate limiting."""
    # Optional rate limiting for livez (20 req/min per IP)
    if rate_limiter:
        client_ip = http_request.client.host if http_request.client else "unknown"
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=20, prefix="livez")
        if not allowed:
            # For livez, return 429 but don't log as warning (expected for monitoring)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded for livez endpoint.",
                },
            )
    return {"status": "alive"}


@app.get("/metrics")
async def metrics(http_request: Request):
    """Prometheus metrics endpoint with rate limiting."""
    # Rate limiting for metrics endpoint (10 req/min per IP)
    if rate_limiter:
        client_ip = http_request.client.host if http_request.client else "unknown"
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=10, prefix="metrics")
        if not allowed:
            logger.warning(f"Rate limit exceeded for /metrics endpoint: IP={client_ip}")
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded for metrics endpoint (10 req/min per IP).",
                },
            )
    
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/proxy/http", summary="Proxy HTTP request", description="Universal HTTP proxy endpoint for any HTTP API. Supports retries, circuit breaker, cache, and idempotency. Use this endpoint to add reliability layers to any HTTP API call.")
async def proxy_http(
    request: HTTPProxyRequest,
    http_request: Request,
):
    """Universal HTTP proxy endpoint for any HTTP API."""
    # Verify API key if required and resolve tenant and tier
    api_key, tenant, tier = verify_api_key(http_request)
    
    # Security: Validate API key format (BYO-key security)
    if api_key:
        is_valid, error_msg = SecurityManager.validate_api_key_format(api_key)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "type": "client_error",
                    "code": "INVALID_API_KEY_FORMAT",
                    "message": error_msg or "Invalid API key format",
                },
            )
    
    # Rate limiting and abuse protection for Free tier
    if rate_limiter and tier == "free":
        # Set current tier for abuse detection
        rate_limiter._current_tier = tier
        
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("User-Agent", "")
        
        # Check IP rate limit (20 req/min)
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=20)
        if not allowed:
            free_tier_abuse_attempts_total.labels(abuse_type="rate_limit_bypass", tier=tier).inc()
            logger.warning(f"Free tier abuse attempt: IP rate limit exceeded for tier={tier}, IP={client_ip}")
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded. Free tier: 20 requests/minute per IP.",
                },
            )
        
        # Check account burst limit (500 req/min)
        account_id = hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else "unknown"
        allowed, error = rate_limiter.check_account_burst_limit(account_id, limit_per_minute=500)
        if not allowed:
            free_tier_abuse_attempts_total.labels(abuse_type="burst_limit", tier=tier).inc()
            logger.warning(f"Free tier abuse attempt: burst limit exceeded for tier={tier}, account_id={account_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "abuse_error",
                    "code": error,
                    "message": "Burst limit exceeded. Free tier abuse detected.",
                },
            )
        
        # Check fingerprint limit
        allowed, error = rate_limiter.check_fingerprint_limit(client_ip, user_agent, api_key or "", limit_per_minute=20)
        if not allowed:
            free_tier_abuse_attempts_total.labels(abuse_type="fingerprint_mismatch", tier=tier).inc()
            logger.warning(f"Free tier abuse attempt: fingerprint mismatch for tier={tier}, account_id={account_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded based on fingerprint.",
                },
            )
        
        # Check anomaly detector
        allowed, error = rate_limiter.check_anomaly_detector(account_id)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "anomaly_error",
                    "code": error,
                    "message": "Anomalous activity detected. Request throttled.",
                },
            )
    
    # Generate request ID (UUID4 for better uniqueness)
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    
    # Detect client profile
    client_profile_name = detect_client_profile(http_request, tenant=tenant)
    
    result = await handle_http_proxy(
        target_name=request.target,
        method=request.method,
        path=request.path,
        headers=request.headers,
        query=request.query,
        body=request.body,
        idempotency_key=request.idempotency_key,
        cache_ttl=request.cache,
        targets=targets,
        cache=cache,
        idempotency=idempotency,
        key_pool_manager=key_pool_manager,
        rate_scheduler=rate_scheduler,
        client_profile_name=client_profile_name,
        client_profile_manager=client_profile_manager,
        request_id=request_id,
        tenant=tenant,
        tier=tier,
    )
    
    # Record usage for RapidAPI tracking
    if rapidapi_client and api_key:
        await rapidapi_client.record_usage(
            api_key=api_key,
            endpoint="/proxy/http",
            latency_ms=result.meta.duration_ms,
            status="success" if result.success else "error",
        )
        rapidapi_tier_distribution.labels(tier=tier).inc()
    
    status_code = 200 if result.success else (result.error.status_code or 500)
    return JSONResponse(
        content=result.model_dump(),
        status_code=status_code,
        headers={
            "X-Request-ID": request_id,
            "X-Cache-Hit": str(result.meta.cache_hit).lower(),
            "X-Retries": str(result.meta.retries),
            "X-Duration-MS": str(result.meta.duration_ms),
        },
    )


@app.post("/proxy/llm", summary="Proxy LLM request", description="LLM proxy endpoint with idempotency, budget caps, and caching. Make idempotent LLM API calls with predictable costs. Supports OpenAI, Anthropic, and Mistral providers. Set stream=true for Server-Sent Events (SSE) streaming.")
async def proxy_llm(
    request: LLMProxyRequest,
    http_request: Request,
):
    """LLM proxy endpoint with idempotency and budget control."""
    # Verify API key if required and resolve tenant and tier
    api_key, tenant, tier = verify_api_key(http_request)
    
    # Security: Validate API key format (BYO-key security)
    if api_key:
        is_valid, error_msg = SecurityManager.validate_api_key_format(api_key)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail={
                    "type": "client_error",
                    "code": "INVALID_API_KEY_FORMAT",
                    "message": error_msg or "Invalid API key format",
                },
            )
    
    # Free tier: Block SSE streaming
    if tier == "free" and request.stream:
        allowed, error = FreeTierRestrictions.is_feature_allowed("streaming", tier)
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail={
                    "type": "feature_error",
                    "code": error,
                    "message": "SSE streaming not available for Free tier.",
                },
            )
    
    # Rate limiting and abuse protection for Free tier
    if rate_limiter and tier == "free":
        # Set current tier for abuse detection
        rate_limiter._current_tier = tier
        
        client_ip = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("User-Agent", "")
        accept_language = http_request.headers.get("Accept-Language", "")
        account_id = hashlib.sha256(api_key.encode()).hexdigest()[:16] if api_key else "unknown"
        
        # Check auto-ban first (>5 bypass attempts)
        should_ban, ban_reason = rate_limiter.check_auto_ban(account_id, client_ip, max_attempts=5)
        if should_ban:
            free_tier_abuse_attempts_total.labels(abuse_type="auto_ban", tier=tier).inc()
            logger.warning(f"Free tier abuse: account/IP banned for tier={tier}, account_id={account_id}, reason={ban_reason}")
            raise HTTPException(
                status_code=403,
                detail={
                    "type": "abuse_error",
                    "code": "ACCOUNT_BANNED",
                    "message": f"Account/IP banned: {ban_reason}",
                },
            )
        
        # Check IP rate limit (20 req/min)
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=20)
        if not allowed:
            rate_limiter.abuse_detector.record_limit_bypass_attempt(account_id, client_ip)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "rate_limit_error",
                    "code": error,
                    "message": "Rate limit exceeded. Free tier: 20 requests/minute per IP.",
                },
            )
        
        # Check burst protection (≤300 req/10min)
        allowed, error = rate_limiter.check_burst_protection(account_id, limit_per_10min=300)
        if not allowed:
            rate_limiter.abuse_detector.record_limit_bypass_attempt(account_id, client_ip)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "abuse_error",
                    "code": error,
                    "message": "Burst limit exceeded. Free tier: maximum 300 requests per 10 minutes.",
                },
            )
        
        # Check account burst limit (500 req/min)
        allowed, error = rate_limiter.check_account_burst_limit(account_id, limit_per_minute=500)
        if not allowed:
            rate_limiter.abuse_detector.record_limit_bypass_attempt(account_id, client_ip)
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "abuse_error",
                    "code": error,
                    "message": "Burst limit exceeded. Free tier abuse detected.",
                },
            )
        
        # Check usage anomaly (3x average)
        allowed, error = rate_limiter.check_usage_anomaly(account_id, multiplier=3.0)
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "anomaly_error",
                    "code": error,
                    "message": "Usage anomaly detected. Request throttled.",
                },
            )
        
        # Check fingerprint-based identity
        allowed, error = rate_limiter.check_fingerprint(
            account_id, client_ip, user_agent, accept_language
        )
        if not allowed:
            if error == "FINGERPRINT_MISMATCH_BANNED":
                raise HTTPException(
                    status_code=403,
                    detail={
                        "type": "abuse_error",
                        "code": error,
                        "message": "Account banned due to multiple fingerprint mismatches.",
                    },
                )
            raise HTTPException(
                status_code=429,
                detail={
                    "type": "abuse_error",
                    "code": error,
                    "message": "Fingerprint mismatch detected. Request throttled.",
                },
            )
        
        # Validate Free tier restrictions
        if request.model:
            allowed, error = FreeTierRestrictions.is_model_allowed(
                request.target, 
                request.model, 
                tier
            )
            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "type": "feature_error",
                        "code": error,
                        "message": f"Model {request.model} not allowed for Free tier. Allowed: gpt-4o-mini, claude-3-haiku, mistral-small",
                    },
                )
        
        # Check idempotency restriction
        if request.idempotency_key:
            allowed, error = FreeTierRestrictions.is_feature_allowed("idempotency", tier)
            if not allowed:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "type": "feature_error",
                        "code": error,
                        "message": "Idempotency not available for Free tier.",
                    },
                )
    
    # Generate request ID (UUID4 for better uniqueness)
    request_id = f"req_{uuid.uuid4().hex[:16]}"
    
    # Extract RouteLLM routing decision from headers
    routellm_decision = extract_routellm_decision(dict(http_request.headers))
    
    # Apply RouteLLM overrides to target and model
    resolved_target = request.target
    resolved_model = request.model
    if routellm_decision and routellm_decision.has_override:
        resolved_target, resolved_model = apply_routellm_overrides(
            request.target,
            request.model,
            targets,
            routellm_decision,
        )
        
        # Record metrics for RouteLLM routing
        routellm_decisions_total.labels(
            route_name=routellm_decision.route_name or "unknown",
            provider=routellm_decision.provider or "default",
            model=routellm_decision.model or "default",
        ).inc()
        
        if routellm_decision.provider and routellm_decision.model:
            routellm_overrides_total.labels(override_type="both").inc()
        elif routellm_decision.provider:
            routellm_overrides_total.labels(override_type="provider").inc()
        elif routellm_decision.model:
            routellm_overrides_total.labels(override_type="model").inc()
        
        routellm_metrics.record_decision(routellm_decision)
    
    # Handle streaming requests
    if request.stream:
        generator = handle_llm_stream_generator(
            target_name=resolved_target,
            messages=request.messages,
            model=resolved_model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop=request.stop,
            idempotency_key=request.idempotency_key,
            cache_ttl=request.cache,
            targets=targets,
            cache=cache,
            idempotency=idempotency,
            request_id=request_id,
            tenant=tenant,
            tier=tier,
        )
        
        # Build response headers including RouteLLM correlation
        response_headers = {
            "X-Request-ID": request_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if routellm_decision:
            response_headers.update(routellm_decision.to_response_headers())
        
        return StreamingResponse(
            generator,
            media_type="text/event-stream",
            headers=response_headers,
        )
    
    # Detect client profile
    client_profile_name = detect_client_profile(http_request, tenant=tenant)
    
    # Handle non-streaming requests (existing behavior)
    result = await handle_llm_proxy(
        target_name=resolved_target,
        messages=request.messages,
        model=resolved_model,
        max_tokens=request.max_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        stop=request.stop,
        stream=False,
        idempotency_key=request.idempotency_key,
        cache_ttl=request.cache,
        targets=targets,
        cache=cache,
        idempotency=idempotency,
        request_id=request_id,
        tenant=tenant,
        tier=tier,
        key_pool_manager=key_pool_manager,
        rate_scheduler=rate_scheduler,
        client_profile_name=client_profile_name,
        client_profile_manager=client_profile_manager,
    )
    
    # Record usage for RapidAPI tracking
    if rapidapi_client and api_key:
        cost_usd = result.data.usage.estimated_cost_usd if result.success and result.data and result.data.usage else 0.0
        await rapidapi_client.record_usage(
            api_key=api_key,
            endpoint="/proxy/llm",
            latency_ms=result.meta.duration_ms,
            status="success" if result.success else "error",
            cost_usd=cost_usd,
        )
        rapidapi_tier_distribution.labels(tier=tier).inc()
    
    # Add RouteLLM correlation to response meta
    if routellm_decision:
        result.meta.routellm_decision_id = routellm_decision.decision_id
        result.meta.routellm_route_name = routellm_decision.route_name
        result.meta.routellm_provider_override = routellm_decision.provider
        result.meta.routellm_model_override = routellm_decision.model
    
    # Build response headers including RouteLLM correlation
    response_headers = {
        "X-Request-ID": request_id,
        "X-Cache-Hit": str(result.meta.cache_hit).lower(),
        "X-Retries": str(result.meta.retries),
        "X-Duration-MS": str(result.meta.duration_ms),
    }
    if routellm_decision:
        response_headers.update(routellm_decision.to_response_headers())
    
    status_code = 200 if result.success else (result.error.status_code or 500)
    return JSONResponse(
        content=result.model_dump(),
        status_code=status_code,
        headers=response_headers,
    )


# === RapidAPI Webhook Endpoint ===

@app.post(
    "/webhooks/rapidapi",
    summary="RapidAPI Webhook",
    description="Webhook endpoint for RapidAPI events (subscription changes, usage alerts).",
    include_in_schema=False,  # Hidden from public docs
)
async def rapidapi_webhook(request: Request):
    """
    Handle RapidAPI webhook events.
    
    Supported events:
    - subscription.created: New subscription created
    - subscription.updated: Subscription tier changed
    - subscription.cancelled: Subscription cancelled
    - usage.alert: Usage threshold reached
    """
    if not rapidapi_client:
        raise HTTPException(status_code=503, detail="RapidAPI integration not configured")
    
    # Rate limiting for webhook endpoint (IP-based, 10 req/min)
    if rate_limiter:
        client_ip = request.client.host if request.client else "unknown"
        webhook_rate_key = f"webhook_ip:{client_ip}"
        
        # Check rate limit (10 requests per minute)
        allowed, error = rate_limiter.check_ip_rate_limit(client_ip, limit_per_minute=10, prefix="webhook")
        if not allowed:
            logger.warning(f"Webhook rate limit exceeded for IP: {client_ip}")
            rapidapi_webhook_events_total.labels(event_type="unknown", status="rate_limited").inc()
            raise HTTPException(
                status_code=429,
                detail="Webhook rate limit exceeded (10 requests/minute)",
            )
    
    # Request size limit (10KB)
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 10240:
        logger.warning(f"Webhook payload too large: {content_length} bytes")
        rapidapi_webhook_events_total.labels(event_type="unknown", status="payload_too_large").inc()
        raise HTTPException(
            status_code=413,
            detail="Webhook payload too large (max 10KB)",
        )
    
    # Get raw body for signature verification
    body = await request.body()
    
    # Verify webhook signature
    signature = request.headers.get("X-RapidAPI-Signature", "")
    if not rapidapi_client.verify_webhook_signature(body, signature):
        logger.warning("Invalid RapidAPI webhook signature")
        rapidapi_webhook_events_total.labels(event_type="unknown", status="invalid_signature").inc()
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook payload
    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        rapidapi_webhook_events_total.labels(event_type="unknown", status="invalid_json").inc()
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    event_type = payload.get("type", "unknown")
    event_data = payload.get("data", {})
    event_id = payload.get("id") or payload.get("event_id") or ""
    
    logger.info(f"Received RapidAPI webhook: {event_type}, event_id={event_id}")
    
    # Idempotency check: generate key from event_type + event_id
    # This prevents duplicate processing of the same webhook event
    if idempotency and event_id:
        webhook_idempotency_key = f"webhook:rapidapi:{event_type}:{event_id}"
        
        # Check if this webhook has already been processed
        existing_result = idempotency.get_result(webhook_idempotency_key)
        if existing_result:
            logger.info(f"Duplicate webhook detected: {event_type}, event_id={event_id}")
            rapidapi_webhook_events_total.labels(event_type=event_type, status="duplicate").inc()
            return JSONResponse(
                content={
                    "status": "ok",
                    "event_type": event_type,
                    "duplicate": True,
                    "message": "Event already processed",
                },
                status_code=200,
            )
        
        # Mark as in progress to prevent concurrent processing
        idempotency.mark_in_progress(webhook_idempotency_key, ttl_s=60)
    else:
        webhook_idempotency_key = None
    
    try:
        if event_type == "subscription.created":
            # New subscription - cache tier info and create tenant
            api_key = event_data.get("api_key")
            tier = event_data.get("tier", "free")
            user_id = event_data.get("user_id")
            
            if api_key:
                tier_enum = SubscriptionTier(tier) if tier in [t.value for t in SubscriptionTier] else SubscriptionTier.FREE
                await rapidapi_client._cache_tier(api_key, tier_enum, user_id)
                rapidapi_tier_cache_total.labels(operation="set").inc()
                rapidapi_tier_distribution.labels(tier=tier).inc()
                
                # Create tenant for RapidAPI user
                if rapidapi_tenant_manager and user_id:
                    rapidapi_tenant_manager.create_tenant(
                        user_id,
                        tier_enum,
                        metadata={"api_key_hash": rapidapi_client._hash_api_key(api_key)},
                    )
                
                logger.info(f"Cached new subscription: tier={tier}, user_id={user_id}")
            
            rapidapi_webhook_events_total.labels(event_type="subscription.created", status="success").inc()
        
        elif event_type == "subscription.updated":
            # Subscription tier changed - invalidate cache, update tier, and migrate tenant
            api_key = event_data.get("api_key")
            new_tier = event_data.get("tier", "free")
            user_id = event_data.get("user_id")
            
            if api_key:
                # Invalidate old cache
                await rapidapi_client.invalidate_tier_cache(api_key)
                rapidapi_tier_cache_total.labels(operation="invalidate").inc()
                
                # Cache new tier
                tier_enum = SubscriptionTier(new_tier) if new_tier in [t.value for t in SubscriptionTier] else SubscriptionTier.FREE
                await rapidapi_client._cache_tier(api_key, tier_enum, user_id)
                rapidapi_tier_cache_total.labels(operation="set").inc()
                rapidapi_tier_distribution.labels(tier=new_tier).inc()
                
                # Update tenant tier (migration)
                if rapidapi_tenant_manager and user_id:
                    rapidapi_tenant_manager.update_tenant_tier(
                        user_id,
                        tier_enum,
                        metadata={"api_key_hash": rapidapi_client._hash_api_key(api_key)},
                    )
                
                logger.info(f"Updated subscription: new_tier={new_tier}, user_id={user_id}")
            
            rapidapi_webhook_events_total.labels(event_type="subscription.updated", status="success").inc()
        
        elif event_type == "subscription.cancelled":
            # Subscription cancelled - invalidate cache and cleanup tenant
            api_key = event_data.get("api_key")
            user_id = event_data.get("user_id")
            
            if api_key:
                await rapidapi_client.invalidate_tier_cache(api_key)
                rapidapi_tier_cache_total.labels(operation="invalidate").inc()
                
                # Cleanup tenant (delete tenant and associated data)
                if rapidapi_tenant_manager and user_id:
                    rapidapi_tenant_manager.delete_tenant(user_id)
                
                logger.info(f"Subscription cancelled: user_id={user_id}")
            
            rapidapi_webhook_events_total.labels(event_type="subscription.cancelled", status="success").inc()
        
        elif event_type == "usage.alert":
            # Usage alert - log and potentially throttle
            api_key = event_data.get("api_key")
            usage_percent = event_data.get("usage_percent", 0)
            threshold = event_data.get("threshold", "unknown")
            
            logger.warning(f"Usage alert: api_key_hash={rapidapi_client._hash_api_key(api_key) if api_key else 'unknown'}, usage={usage_percent}%, threshold={threshold}")
            rapidapi_webhook_events_total.labels(event_type="usage.alert", status="success").inc()
        
        else:
            logger.info(f"Unknown webhook event type: {event_type}")
            rapidapi_webhook_events_total.labels(event_type=event_type, status="unknown_type").inc()
        
        # Store idempotency result for successful processing
        if idempotency and webhook_idempotency_key:
            idempotency.store_result(
                webhook_idempotency_key,
                {"status": "processed", "event_type": event_type, "event_id": event_id},
                ttl_s=86400,  # 24 hours
            )
            idempotency.clear_in_progress(webhook_idempotency_key)
        
        return JSONResponse(
            content={"status": "ok", "event_type": event_type},
            status_code=200,
        )
    
    except Exception as e:
        logger.error(f"Error processing webhook {event_type}: {e}")
        rapidapi_webhook_events_total.labels(event_type=event_type, status="error").inc()
        
        # Clear in-progress marker on error
        if idempotency and webhook_idempotency_key:
            idempotency.clear_in_progress(webhook_idempotency_key)
        
        raise HTTPException(status_code=500, detail=f"Webhook processing error: {str(e)}")


@app.get(
    "/rapidapi/status",
    summary="RapidAPI Integration Status",
    description="Check the status of RapidAPI integration.",
)
async def rapidapi_status(request: Request):
    """Get RapidAPI integration status."""
    # Verify API key
    api_key, tenant, tier = verify_api_key(request)
    
    if not rapidapi_client:
        return JSONResponse(
            content={
                "status": "not_configured",
                "message": "RapidAPI integration not configured",
            },
            status_code=200,
        )
    
    # Get usage stats for the current API key
    usage_stats = await rapidapi_client.get_usage_stats(api_key) if api_key else {}
    
    return JSONResponse(
        content={
            "status": "configured",
            "tier": tier,
            "usage": usage_stats,
            "redis_connected": rapidapi_client.redis_enabled,
            "api_configured": bool(rapidapi_client.api_key),
        },
        status_code=200,
    )


# =============================================================================
# Business Routes (Paddle, Onboarding, Analytics, Calculators, Dashboard)
# =============================================================================

# Import and register business routes
try:
    from reliapi.app.routes import paddle, onboarding, analytics, calculators, dashboard
    
    app.include_router(paddle.router)
    app.include_router(onboarding.router)
    app.include_router(analytics.router)
    app.include_router(calculators.router)
    app.include_router(dashboard.router)
    
    logger.info("Business routes registered: paddle, onboarding, analytics, calculators, dashboard")
except ImportError as e:
    logger.warning(f"Business routes not available: {e}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)

