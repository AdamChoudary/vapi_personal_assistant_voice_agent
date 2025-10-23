"""
FastAPI dependencies for dependency injection.

This module provides reusable dependencies for:
- HTTP client management with connection pooling
- Webhook signature verification
- Request context and authentication

Design decisions:
- Singleton pattern for HTTP clients (connection pooling)
- AsyncGenerator for proper resource cleanup
- HMAC-based webhook verification for security
"""

import hashlib
import hmac
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Header, HTTPException, Request, status

from src.config import settings
from src.services.fontis_client import FontisClient

# ===== HTTP Client Management =====

# Global client instance for connection pooling
# Why global? httpx.AsyncClient maintains a connection pool.
# Creating one client per request would defeat connection pooling.
_fontis_client: FontisClient | None = None


async def get_fontis_client() -> AsyncGenerator[FontisClient, None]:
    """
    Dependency that provides a Fontis API client with connection pooling.
    
    Uses singleton pattern to reuse the same httpx.AsyncClient across
    requests, enabling:
    - Connection pooling (faster subsequent requests)
    - Reduced overhead (no client creation per request)
    - Shared timeout and retry configuration
    
    Yields:
        FontisClient: Configured Fontis API client instance
    
    Usage in endpoint:
        @router.post("/search")
        async def search(
            params: SearchParams,
            client: FontisClient = Depends(get_fontis_client)
        ):
            return await client.search_customers(params.term)
    
    Note: The client is NOT closed after each request. It's reused
    across all requests for the lifetime of the application.
    Call close_fontis_client() in the app shutdown hook.
    """
    global _fontis_client
    
    # Lazy initialization on first use
    if _fontis_client is None:
        _fontis_client = FontisClient()
    
    try:
        yield _fontis_client
    finally:
        # Don't close the client here - reuse across requests
        pass


async def close_fontis_client() -> None:
    """
    Cleanup function to close the Fontis client on application shutdown.
    
    Should be called in the FastAPI lifespan shutdown hook to:
    - Close all open HTTP connections
    - Release system resources
    - Ensure graceful shutdown
    
    Usage in main.py:
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield  # App is running
            await close_fontis_client()  # Cleanup on shutdown
    """
    global _fontis_client
    if _fontis_client is not None:
        await _fontis_client.close()
        _fontis_client = None


# ===== Webhook Security =====


async def verify_vapi_webhook(
    request: Request,
    x_vapi_signature: Annotated[str | None, Header()] = None
) -> None:
    """
    Verify Vapi webhook requests using HMAC-SHA256 signature.
    
    Security implementation:
    1. Vapi signs webhook payloads with a secret key
    2. Signature is sent in X-Vapi-Signature header
    3. We compute expected signature and compare
    4. Uses timing-safe comparison to prevent timing attacks
    
    Args:
        request: FastAPI request object (for raw body access)
        x_vapi_signature: Signature header from Vapi (format: sha256=<hex>)
    
    Raises:
        HTTPException: 
            - 401 if signature missing or invalid
            - 500 if webhook secret not configured in production
    
    Configuration:
        Set VAPI_WEBHOOK_SECRET environment variable with the secret
        provided by Vapi in your dashboard settings.
    
    Development Mode:
        If webhook secret is not configured in development mode,
        verification is skipped to allow easier local testing.
    
    Security Notes:
        - Always enable in production
        - Protects against replay attacks and unauthorized webhooks
        - Uses HMAC (Hash-based Message Authentication Code)
        - Timing-safe comparison prevents timing attacks
    """
    # Always require webhook secret for security
    if not settings.vapi_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured - cannot verify webhook"
        )
    
    # Check if signature header is provided
    if not x_vapi_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Vapi-Signature header"
        )
    
    # Get raw request body for signature verification
    # Important: Use raw body, not parsed JSON
    body = await request.body()
    
    # Compute expected signature using HMAC-SHA256
    # HMAC ensures message integrity and authenticity
    expected_signature = hmac.new(
        key=settings.vapi_webhook_secret.encode("utf-8"),
        msg=body,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Parse signature from header (format: "sha256=<hex_digest>")
    try:
        algorithm, provided_signature = x_vapi_signature.split("=", 1)
        if algorithm.lower() != "sha256":
            raise ValueError(f"Unsupported signature algorithm: {algorithm}")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid signature format: {str(e)}"
        )
    
    # Timing-safe comparison to prevent timing attacks
    # Why? Prevents attackers from guessing the signature byte-by-byte
    # by measuring response times
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )


# ===== Type Aliases for Cleaner Endpoint Signatures =====

# These type aliases make endpoint signatures more readable:
#
# Instead of:
#   async def endpoint(client: Annotated[FontisClient, Depends(get_fontis_client)])
#
# Use:
#   async def endpoint(client: FontisClientDep)
#
FontisClientDep = Annotated[FontisClient, Depends(get_fontis_client)]
