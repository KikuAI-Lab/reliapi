"""Health check endpoints.

This module provides health check endpoints for load balancers and monitoring.
The actual health endpoints are defined in reliapi.app.main, this module
is provided for api-template compatibility.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint for load balancers and monitoring."""
    return HealthResponse(status="ok", version="1.0.7")


@router.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    """Kubernetes-style health check endpoint."""
    return HealthResponse(status="ok", version="1.0.7")

