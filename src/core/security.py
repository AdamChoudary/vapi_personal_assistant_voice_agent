"""
Security utilities for API authentication and authorization.
"""

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import settings

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> None:
    """
    Verify API key for tool endpoints.
    
    In production, tool endpoints should only be called by Vapi servers.
    Uses a shared secret API key to prevent unauthorized access.
    
    Args:
        credentials: Bearer token from Authorization header
        
    Raises:
        HTTPException: 500 if key not configured, 401 if invalid
    """
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal API key not configured"
        )
    
    if credentials.credentials != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"}
        )

