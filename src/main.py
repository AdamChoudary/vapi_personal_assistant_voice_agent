"""
FastAPI application entry point for Fontis AI Voice Agent.

This module:
- Configures the FastAPI application with middleware and routers
- Sets up structured logging with structlog
- Implements global exception handlers for consistent error responses
- Manages application lifecycle (startup/shutdown hooks)
- Configures CORS and security settings

Design decisions:
- Structured logging (JSON in prod, console in dev) for observability
- Global exception handlers for consistent error format
- Request timing middleware for performance monitoring
- Lifespan manager for resource cleanup
- Router registration with clear organization
"""

import time
from contextlib import asynccontextmanager

import httpx
import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from src.api.vapi import webhooks_handler as vapi_webhooks
from src.api.tools import billing, contracts, customer, delivery, onboarding, routes
from src.config import settings
from src.core.deps import close_fontis_client
from src.core.exceptions import FontisAPIError, JotFormError, VapiError

# ===== Structured Logging Configuration =====

# Configure structlog for structured logging
# Why structlog? Produces machine-readable logs (JSON) for log aggregation
# systems like ELK, Datadog, CloudWatch while still being human-readable
# in development.
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 8601 timestamps
        structlog.stdlib.add_log_level,  # Add log level to output
        structlog.processors.StackInfoRenderer(),  # Stack traces when needed
        structlog.processors.format_exc_info,  # Format exceptions
        # JSON for production (machine-readable), Console for dev (human-readable)
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer(),
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle manager for FastAPI application.
    
    This context manager handles:
    
    Startup phase:
    - Log application start with configuration
    - Initialize connections and resources
    - Validate configuration
    
    Shutdown phase:
    - Close HTTP clients (connection pooling cleanup)
    - Release system resources
    - Ensure graceful shutdown
    
    Why use lifespan instead of @app.on_event?
    - on_event is deprecated in FastAPI 0.109+
    - lifespan provides better control flow
    - Supports async context managers properly
    """
    # ===== Startup =====
    logger.info(
        "application_starting",
        service="Fontis AI Voice Agent",
        version="0.1.0",
        environment=settings.app_env,
        log_level=settings.log_level,
        fontis_base_url=settings.fontis_base_url,
        cors_origins=settings.cors_origins
    )
    
    yield  # Application is running
    
    # ===== Shutdown =====
    logger.info("application_shutting_down")
    await close_fontis_client()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Fontis AI Voice Agent",
    description="FastAPI middleware for Vapi-Fontis Water API integration",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ===== Middleware Configuration =====

# CORS middleware for Vapi webhooks
# Why CORS? Vapi makes cross-origin requests to our webhooks
# Security: Use specific origins in production, not wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,  # From config, not hardcoded
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only needed methods
    allow_headers=["*"],
    max_age=600,  # Cache preflight requests for 10 minutes
)


# Request logging and timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all incoming requests with timing information.
    
    Logs:
    - Request start: method, path, client IP
    - Request end: status code, processing time
    
    Adds X-Process-Time header to response for debugging.
    
    Why middleware? Captures ALL requests including errors,
    unlike endpoint-level logging.
    """
    start_time = time.time()
    
    # Log request start
    logger.info(
        "request_started",
        method=request.method,
        path=request.url.path,
        client_ip=request.client.host if request.client else "unknown",
        user_agent=request.headers.get("user-agent", "unknown")
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log request completion
    logger.info(
        "request_completed",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        process_time_ms=round(process_time * 1000, 2)
    )
    
    # Add timing header for debugging
    response.headers["X-Process-Time"] = str(round(process_time, 3))
    return response


# ===== Global Exception Handlers =====


@app.exception_handler(FontisAPIError)
async def fontis_api_error_handler(request: Request, exc: FontisAPIError):
    """
    Handle Fontis API errors with structured responses.
    
    Converts FontisAPIError exceptions into consistent JSON responses.
    
    Response format:
    {
        "error": "CUST_001",
        "message": "Customer not found",
        "status_code": 404,
        "details": {...},
        "retryable": false
    }
    
    Why centralized error handling?
    - Consistent error format for clients
    - Reduces duplication in endpoints
    - Easier to add error tracking (Sentry, etc.)
    """
    logger.error(
        "fontis_api_error",
        error_code=exc.error_code.value,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        retryable=exc.retryable,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=exc.status_code or status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_dict()
    )


@app.exception_handler(VapiError)
async def vapi_error_handler(request: Request, exc: VapiError):
    """
    Handle Vapi-specific errors.
    
    Used for outbound call failures and webhook processing errors.
    """
    logger.error(
        "vapi_error",
        error_code=exc.error_code.value,
        message=exc.message,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_dict()
    )


@app.exception_handler(JotFormError)
async def jotform_error_handler(request: Request, exc: JotFormError):
    """
    Handle JotForm-specific errors.
    
    Used for contract generation and sending failures.
    """
    logger.error(
        "jotform_error",
        error_code=exc.error_code.value,
        message=exc.message,
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=exc.to_dict()
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors with clear messages.
    
    Converts Pydantic validation errors into user-friendly responses.
    
    Common causes:
    - Missing required fields
    - Wrong field types
    - Invalid field values
    
    Response includes detailed validation errors for debugging.
    """
    logger.warning(
        "validation_error",
        errors=exc.errors(),
        body=str(exc.body)[:500],  # Truncate to avoid logging sensitive data
        path=request.url.path
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid request data",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected exceptions.
    
    Prevents internal errors from leaking implementation details.
    Logs full exception for debugging while returning safe response.
    
    Why needed? Unhandled exceptions would show stack traces to users,
    potentially exposing internal implementation details.
    """
    logger.exception(
        "unexpected_error",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path
    )
    
    # Return generic error to client (don't leak internals)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
            # Include error ID in production for support reference
            "reference_id": f"err_{int(time.time())}"
        }
    )


# ===== Router Registration =====

# Include all API routers
# Order matters for path matching (more specific routes first)
app.include_router(vapi_webhooks.router)  # Vapi webhook handler (handles /vapi/webhooks)
app.include_router(customer.router)
app.include_router(delivery.router)
app.include_router(billing.router)
app.include_router(contracts.router)
app.include_router(onboarding.router)
app.include_router(routes.router)

# Admin routes
from src.api.admin import outbound_calls
app.include_router(outbound_calls.router)

# Mount static files for voice test interface
app.mount("/static", StaticFiles(directory="static"), name="static")

# ===== Core Endpoints =====


@app.get("/")
async def root():
    """
    Root endpoint with service information.
    
    Provides:
    - API version and status
    - Available endpoints (service discovery)
    - Environment information
    - Documentation links (if enabled)
    
    Useful for:
    - Service discovery
    - Health monitoring dashboards
    - API exploration
    """
    return {
        "service": "Fontis AI Voice Agent",
        "version": "0.1.0",
        "status": "operational",
        "environment": settings.app_env,
        "documentation": "/docs" if not settings.is_production else None,
        "endpoints": {
            "health": "/health",
            "webhooks": {
                "vapi": "/vapi/webhooks"
            },
            "tools": {
                "customer": "/tools/customer",
                "delivery": "/tools/delivery",
                "billing": "/tools/billing",
                "contracts": "/tools/contracts",
                "onboarding": "/tools/onboarding",
                "routes": "/tools/routes"
            }
        }
    }


@app.get("/health")
async def health():
    """
    Health check endpoint for load balancers and monitoring.
    
    Used by:
    - Kubernetes liveness/readiness probes
    - Load balancers (AWS ALB, nginx)
    - Uptime monitoring services
    - CI/CD health checks
    
    Returns:
        200 OK if service is healthy
        Includes environment and version for debugging
    
    Note: This is a simple health check. In production,
    consider checking:
    - Database connectivity
    - External API availability
    - Resource usage (CPU, memory)
    """
    return {
        "status": "healthy",
        "environment": settings.app_env,
        "version": "0.1.0",
        "timestamp": int(time.time())
    }


@app.get("/api/config")
async def get_vapi_config():
    """
    Return Vapi configuration for browser-side SDK initialization.
    
    Public endpoint (no auth required) that exposes only public keys
    and configuration needed by the Vapi Web SDK in the browser.
    
    Why separate endpoint? Don't expose private keys to browser.
    """
    return {
        "publicKey": settings.vapi_public_key,
        "assistantId": settings.vapi_assistant_id,
    }


@app.get("/api/tunnel/status")
async def get_tunnel_status():
    """
    Check tunnel status (cloudflared or ngrok) and return public URL.
    
    Acts as a proxy to avoid CORS issues when checking from the browser dashboard.
    Tries cloudflared first (port 20241), then falls back to ngrok (port 4040).
    """
    # Try cloudflared first (preferred)
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://127.0.0.1:20241/metrics")
            if response.status_code == 200:
                text = response.text
                # Extract cloudflare tunnel URL from metrics
                import re
                match = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', text)
                if match:
                    return {
                        "active": True,
                        "url": match.group(0),
                        "status": "connected",
                        "type": "cloudflared"
                    }
    except Exception:
        pass
    
    # Fallback to ngrok
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get("http://127.0.0.1:4040/api/tunnels")
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                https_tunnel = next((t for t in tunnels if t.get("proto") == "https"), None)
                
                if https_tunnel:
                    return {
                        "active": True,
                        "url": https_tunnel.get("public_url"),
                        "status": "connected",
                        "type": "ngrok"
                    }
    except Exception:
        pass
    
    logger.warning("tunnel_check_failed", message="Neither cloudflared nor ngrok detected")
    return {
        "active": False,
        "url": None,
        "status": "not_running",
        "type": None
    }


