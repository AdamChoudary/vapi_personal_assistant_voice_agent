"""
HTTP client for Vapi AI platform integration.

This module provides a client for Vapi's outbound call capabilities,
enabling:
- Programmatic phone call initiation
- SMS sending (if supported by Vapi)
- Call metadata injection

Design decisions:
- Similar structure to FontisClient for consistency
- Error handling with custom VapiError exception
- Async operations for non-blocking I/O
"""

from typing import Any

import httpx

from src.config import settings
from src.core.exceptions import ErrorCode, VapiError


class VapiClient:
    """
    Async HTTP client for Vapi AI platform.
    
    Provides methods for:
    - Creating outbound phone calls
    - Sending SMS messages (if supported)
    - Managing call metadata
    
    Usage:
        client = VapiClient()
        try:
            call = await client.create_phone_call(
                phone_number="+1234567890",
                assistant_id="asst_xyz",
                customer_data={"account": "12345"}
            )
        finally:
            await client.close()
    
    Configuration:
        Requires VAPI_API_KEY environment variable
    """
    
    def __init__(self):
        """
        Initialize Vapi API client.
        
        Raises:
            VapiError: If API key is not configured
        """
        self.base_url = settings.vapi_base_url
        self.api_key = settings.vapi_api_key
        
        # Validate API key is configured
        if not self.api_key:
            raise VapiError(
                "Vapi API key not configured - set VAPI_API_KEY environment variable",
                error_code=ErrorCode.ASSISTANT_NOT_CONFIGURED
            )
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # Create async client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0
        )
    
    async def create_phone_call(
        self,
        phone_number: str,
        assistant_id: str,
        customer_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Initiate an outbound phone call via Vapi.
        
        Use cases:
        - Collections calls for past due accounts
        - Declined payment notifications
        - Delivery reminders
        - Proactive customer outreach
        
        Args:
            phone_number: E.164 format (e.g., "+12345678900")
            assistant_id: Vapi assistant ID to use for the call
            customer_data: Optional metadata to pass to assistant (e.g., account info)
        
        Returns:
            Call response with:
            - call_id: Unique call identifier
            - status: Call status
            - Other Vapi response data
        
        Raises:
            VapiError: If call creation fails
        
        Example:
            # Collections call for past due account
            call = await client.create_phone_call(
                phone_number="+12345678900",
                assistant_id="asst_collections_xyz",
                customer_data={
                    "account_number": "12345",
                    "past_due_amount": 150.00,
                    "days_overdue": 30
                }
            )
        
        Notes:
            - Vapi assistant must be configured in Vapi dashboard
            - Phone number must include country code
            - Metadata is accessible to assistant during call
        """
        try:
            payload = {
                "phoneNumber": phone_number,
                "assistantId": assistant_id,
            }
            
            # Include customer metadata if provided
            # This data is accessible to the assistant during the call
            if customer_data:
                payload["metadata"] = customer_data
            
            response = await self.client.post(
                "/calls",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            raise VapiError(
                f"Failed to create Vapi call: {str(e)}",
                error_code=ErrorCode.VAPI_CALL_FAILED
            )
    
    async def send_sms(
        self,
        phone_number: str,
        message: str
    ) -> dict[str, Any]:
        """
        Send SMS message via Vapi (if supported).
        
        Note: This is a placeholder implementation. Check Vapi documentation
        for current SMS capabilities and API structure.
        
        Use cases:
        - Delivery reminders (text instead of call)
        - Payment confirmations
        - Quick notifications
        
        Args:
            phone_number: Recipient phone (E.164 format)
            message: SMS text content
        
        Returns:
            SMS response from Vapi
        
        Raises:
            VapiError: If SMS sending fails or is not supported
        
        Example:
            response = await client.send_sms(
                phone_number="+12345678900",
                message="Your Fontis water delivery is scheduled for tomorrow."
            )
        """
        try:
            payload = {
                "phoneNumber": phone_number,
                "message": message
            }
            
            response = await self.client.post(
                "/sms",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPError as e:
            raise VapiError(
                f"Failed to send SMS: {str(e)}",
                error_code=ErrorCode.VAPI_CALL_FAILED
            )
    
    async def close(self) -> None:
        """
        Close the HTTP client and release resources.
        
        Should be called when the client is no longer needed.
        """
        await self.client.aclose()
