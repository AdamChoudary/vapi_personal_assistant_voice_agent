"""
Custom exceptions for Fontis AI Voice Agent.

This module defines a hierarchical exception system with:
- Machine-readable error codes for API responses
- Retryable flag for transient vs permanent failures
- Structured error data for logging and debugging

Design pattern: Base exception → Specific exceptions
- FontisAPIError: Base for all Fontis API errors
- VapiError: Base for all Vapi platform errors
- Specific exceptions inherit from base with predefined error codes
"""

from enum import Enum
from typing import Any


class ErrorCode(str, Enum):
    """
    Standardized error codes for API responses.
    
    Used for:
    - Consistent error handling across the application
    - Help clients identify specific error conditions
    - Machine-readable error identification
    
    Naming convention: <DOMAIN>_<NUMBER>
    - AUTH_xxx: Authentication errors (1xxx range)
    - CUST_xxx: Customer-related errors (2xxx range)
    - DEL_xxx: Delivery errors (3xxx range)
    - API_xxx: General API errors (4xxx range)
    - VAPI_xxx: Vapi platform errors (5xxx range)
    """
    
    # Authentication errors (1xxx)
    AUTHENTICATION_FAILED = "AUTH_001"
    INVALID_API_KEY = "AUTH_002"
    UNAUTHORIZED = "AUTH_003"
    
    # Customer errors (2xxx)
    CUSTOMER_NOT_FOUND = "CUST_001"
    MULTIPLE_CUSTOMERS_FOUND = "CUST_002"
    INVALID_CUSTOMER_DATA = "CUST_003"
    
    # Delivery errors (3xxx)
    DELIVERY_STOP_NOT_FOUND = "DEL_001"
    NO_SCHEDULED_DELIVERY = "DEL_002"
    DELIVERY_MODIFICATION_FAILED = "DEL_003"
    
    # API errors (4xxx)
    EXTERNAL_API_ERROR = "API_001"
    REQUEST_TIMEOUT = "API_002"
    RATE_LIMIT_EXCEEDED = "API_003"
    INVALID_RESPONSE = "API_004"
    CONNECTION_ERROR = "API_005"
    
    # Vapi errors (5xxx)
    VAPI_CALL_FAILED = "VAPI_001"
    WEBHOOK_VERIFICATION_FAILED = "VAPI_002"
    ASSISTANT_NOT_CONFIGURED = "VAPI_003"
    
    # JotForm errors (6xxx)
    JOTFORM_NOT_CONFIGURED = "JOTFORM_001"
    JOTFORM_GENERATION_FAILED = "JOTFORM_002"
    JOTFORM_EMAIL_FAILED = "JOTFORM_003"
    JOTFORM_STATUS_CHECK_FAILED = "JOTFORM_004"


class FontisAPIError(Exception):
    """
    Base exception for all Fontis API-related errors.
    
    This exception stores comprehensive error context for:
    - HTTP error responses to clients
    - Structured logging
    - Retry decision making
    
    Attributes:
        message: Human-readable error description
        status_code: HTTP status code (if applicable)
        error_code: Machine-readable error identifier
        details: Additional context (dict, can include API response)
        retryable: Whether the operation can be retried
    
    Usage:
        try:
            result = await fontis_client.search_customers("test")
        except FontisAPIError as e:
            logger.error("API call failed", 
                        error_code=e.error_code,
                        retryable=e.retryable)
            if e.retryable:
                # Implement retry logic
                pass
    """
    
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_code: ErrorCode = ErrorCode.EXTERNAL_API_ERROR,
        details: Any = None,
        retryable: bool = False
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        self.retryable = retryable
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convert exception to dictionary for API responses.
        
        Returns:
            dict: Structured error data suitable for JSON responses
        """
        return {
            "error": self.error_code.value,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
            "retryable": self.retryable
        }
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.error_code.value}: {self.message}"


class CustomerNotFoundError(FontisAPIError):
    """
    Raised when a customer cannot be found in the Fontis system.
    
    This is typically a non-retryable error as customer data
    won't exist on retry. Common causes:
    - Invalid account number
    - Customer not in system
    - Search returned no results
    
    HTTP Status: 404 Not Found
    """
    
    def __init__(self, message: str = "Customer not found", details: Any = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code=ErrorCode.CUSTOMER_NOT_FOUND,
            details=details,
            retryable=False
        )


class DeliveryStopNotFoundError(FontisAPIError):
    """
    Raised when a delivery stop cannot be found.
    
    This typically means:
    - Customer has no active delivery locations
    - Invalid deliveryId provided
    - Delivery stop was deactivated
    
    HTTP Status: 404 Not Found
    """
    
    def __init__(self, message: str = "Delivery stop not found", details: Any = None):
        super().__init__(
            message=message,
            status_code=404,
            error_code=ErrorCode.DELIVERY_STOP_NOT_FOUND,
            details=details,
            retryable=False
        )


class AuthenticationError(FontisAPIError):
    """
    Raised when Fontis API authentication fails.
    
    Common causes:
    - Invalid API key
    - Expired credentials
    - Missing Authorization header
    
    Non-retryable as credentials won't change on retry.
    
    HTTP Status: 401 Unauthorized
    """
    
    def __init__(self, message: str = "Authentication failed", details: Any = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code=ErrorCode.AUTHENTICATION_FAILED,
            details=details,
            retryable=False
        )


class RateLimitError(FontisAPIError):
    """
    Raised when API rate limit is exceeded.
    
    This is a retryable error - should implement exponential backoff.
    The retry_after value (if provided) indicates when to retry.
    
    HTTP Status: 429 Too Many Requests
    
    Usage:
        try:
            result = await fontis_client.search_customers("test")
        except RateLimitError as e:
            retry_after = e.details.get("retry_after", 60)
            await asyncio.sleep(retry_after)
            # Retry the request
    """
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(
            message=message,
            status_code=429,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            details={"retry_after": retry_after},
            retryable=True
        )


class RequestTimeoutError(FontisAPIError):
    """
    Raised when API request times out.
    
    This is retryable as timeouts are often transient.
    Common causes:
    - Network latency
    - Overloaded API server
    - Large response payload
    
    HTTP Status: 504 Gateway Timeout
    """
    
    def __init__(self, message: str = "Request timeout", timeout: int | None = None):
        super().__init__(
            message=message,
            status_code=504,
            error_code=ErrorCode.REQUEST_TIMEOUT,
            details={"timeout_seconds": timeout},
            retryable=True
        )


class VapiError(Exception):
    """
    Base exception for Vapi AI platform errors.
    
    Used for:
    - Outbound call failures
    - Webhook processing errors
    - Assistant configuration issues
    
    Attributes:
        message: Error description
        error_code: Machine-readable error identifier
    """
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.VAPI_CALL_FAILED):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": self.error_code.value,
            "message": self.message
        }


class JotFormError(Exception):
    """
    Base exception for JotForm API errors.
    
    Used for:
    - Contract generation failures
    - Email sending errors
    - Form submission tracking issues
    
    Attributes:
        message: Error description
        error_code: Machine-readable error identifier
    """
    
    def __init__(self, message: str, error_code: ErrorCode = ErrorCode.JOTFORM_GENERATION_FAILED):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "error": self.error_code.value,
            "message": self.message
        }
