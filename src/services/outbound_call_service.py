"""
Outbound call service for Vapi AI.
Manages outbound calls for declined payments, collections, and delivery reminders.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import structlog
import httpx

from src.config import settings
from src.core.exceptions import VapiError, ErrorCode

logger = structlog.get_logger(__name__)


class OutboundCallService:
    """Service for managing outbound calls via Vapi."""
    
    def __init__(self):
        self.base_url = "https://api.vapi.ai"
        self.headers = {
            "Authorization": f"Bearer {settings.vapi_api_key}",
            "Content-Type": "application/json"
        }
        self._phone_number_id: Optional[str] = None
    
    async def _get_phone_number_id(self) -> str:
        """Get Vapi phone number ID (cached)."""
        if self._phone_number_id:
            return self._phone_number_id
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/phone-number",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise VapiError(
                    message="Failed to get phone number",
                    error_code=ErrorCode.VAPI_CALL_FAILED
                )
            
            phones = response.json()
            if not phones:
                raise VapiError(
                    message="No phone number found in Vapi account",
                    error_code=ErrorCode.VAPI_CALL_FAILED
                )
            
            self._phone_number_id = phones[0]["id"]
            logger.info("phone_number_cached", phone_id=self._phone_number_id)
            return self._phone_number_id
    
    async def initiate_call(
        self,
        customer_phone: str,
        call_type: str,
        customer_data: Dict[str, Any],
        assistant_overrides: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initiate an outbound call.
        
        Args:
            customer_phone: Customer phone number (E.164)
            call_type: Type of call (declined_payment, collections, delivery_reminder)
            customer_data: Customer information for context
            assistant_overrides: Optional assistant configuration overrides
        
        Returns:
            Call details including call_id
        """
        phone_id = await self._get_phone_number_id()
        
        # Build assistant configuration with call context
        assistant_config = {
            "assistantId": settings.vapi_assistant_id,
            "phoneNumberId": phone_id,
            "customer": {
                "number": customer_phone,
                "name": customer_data.get("name"),
                "extension": customer_data.get("extension")
            }
        }
        
        # Add call type to metadata for webhook routing
        assistant_config["metadata"] = {
            "call_type": call_type,
            "customer_id": customer_data.get("customer_id"),
            "delivery_id": customer_data.get("delivery_id"),
            "initiated_at": datetime.utcnow().isoformat()
        }
        
        # Apply overrides if provided
        if assistant_overrides:
            assistant_config.update(assistant_overrides)
        
        logger.info(
            "initiating_outbound_call",
            call_type=call_type,
            customer_phone=customer_phone,
            customer_id=customer_data.get("customer_id")
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/call/phone",
                headers=self.headers,
                json=assistant_config
            )
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                logger.error(
                    "outbound_call_failed",
                    status=response.status_code,
                    error=error_text,
                    call_type=call_type
                )
                raise VapiError(
                    message=f"Failed to initiate call: {error_text}",
                    error_code=ErrorCode.VAPI_CALL_FAILED
                )
            
            call_data = response.json()
            call_id = call_data.get("id")
            
            logger.info(
                "outbound_call_initiated",
                call_id=call_id,
                call_type=call_type,
                status=call_data.get("status")
            )
            
            return call_data
    
    async def get_call_status(self, call_id: str) -> Dict[str, Any]:
        """Get call status and details."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/call/{call_id}",
                headers=self.headers
            )
            
            if response.status_code != 200:
                raise VapiError(
                    message="Failed to get call status",
                    error_code=ErrorCode.VAPI_CALL_FAILED
                )
            
            return response.json()
    
    async def send_sms(
        self,
        customer_phone: str,
        message: str,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS notification via Vapi.
        
        Args:
            customer_phone: Customer phone number
            message: SMS message content
            customer_data: Optional customer context
        
        Returns:
            SMS send status
        """
        phone_id = await self._get_phone_number_id()
        
        payload = {
            "phoneNumberId": phone_id,
            "customer": {"number": customer_phone},
            "message": message
        }
        
        if customer_data:
            payload["metadata"] = {
                "customer_id": customer_data.get("customer_id"),
                "type": "notification"
            }
        
        logger.info("sending_sms", phone=customer_phone, message_length=len(message))
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/sms",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code not in [200, 201]:
                logger.error("sms_send_failed", status=response.status_code)
                raise VapiError(
                    message="Failed to send SMS",
                    error_code=ErrorCode.VAPI_CALL_FAILED
                )
            
            return response.json()


# Singleton instance
_outbound_service: Optional[OutboundCallService] = None


def get_outbound_service() -> OutboundCallService:
    """Get or create outbound call service singleton."""
    global _outbound_service
    if _outbound_service is None:
        _outbound_service = OutboundCallService()
    return _outbound_service

