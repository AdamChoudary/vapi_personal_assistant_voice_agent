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
from src.services.twilio_service import TwilioService

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
        self.twilio_service = TwilioService()
    
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
        
        # Get customer name for use in greeting
        # CRITICAL: Prioritize "customer_name" field if present, then fall back to "name"
        # This ensures we use the explicit customer_name field first
        customer_name = customer_data.get("customer_name") or customer_data.get("name")
        
        # CRITICAL: Validate and clean the name
        if customer_name:
            customer_name = str(customer_name).strip()
            if not customer_name:
                customer_name = None
        
        # Build assistant configuration with call context
        assistant_config: dict[str, Any] = {
            "assistantId": settings.vapi_assistant_id,
            "phoneNumberId": phone_id,
            "customer": {
                "number": customer_phone,
                "name": customer_name,
                "extension": customer_data.get("extension")
            }
        }
        
        # Note: serverUrl (webhook URL) must be configured in Vapi dashboard/assistant settings,
        # not in the call payload. Vapi API rejects serverUrl in the call request.
        # Ensure webhook URL is set in Vapi dashboard: https://fontis-voice-agent.fly.dev/vapi/webhooks
        
        # Add call type to metadata for webhook routing
        metadata: dict[str, str] = {
            "call_type": call_type,
            "customer_id": str(customer_data.get("customer_id") or ""),
            "delivery_id": str(customer_data.get("delivery_id") or ""),
            "initiated_at": datetime.utcnow().isoformat(),
        }
        
        # CRITICAL: Ensure customer_name is explicitly set in metadata
        if customer_name:
            metadata["customer_name"] = str(customer_name)
        
        # Add other customer_data fields to metadata
        for key, value in customer_data.items():
            if value in (None, ""):
                continue
            # Skip 'name' since we've already set it as 'customer_name'
            if key == "name":
                continue
            
            # Format amounts properly - ensure 2 decimal places for currency
            if key in ("declined_amount", "account_balance", "past_due_amount") and isinstance(value, (int, float)):
                # Format as string with 2 decimals: 50 -> "50.00", 50.5 -> "50.50"
                metadata[key] = f"{float(value):.2f}"
            elif key == "account_on_hold" and isinstance(value, bool):
                # Convert boolean to string for metadata
                metadata[key] = "true" if value else "false"
            else:
                metadata[key] = str(value)
        
        # CRITICAL: Ensure call_reason_summary is always readable
        # This helps the agent understand why it's calling
        if "call_reason_summary" not in metadata and call_type == "declined_payment":
            if metadata.get("declined_amount"):
                metadata["call_reason_summary"] = f"Payment of ${metadata['declined_amount']} was declined"
        elif "call_reason_summary" not in metadata and call_type == "collections":
            if metadata.get("past_due_amount"):
                metadata["call_reason_summary"] = f"Account has past due balance of ${metadata['past_due_amount']}"
        elif "call_reason_summary" not in metadata and call_type == "delivery_reminder":
            if metadata.get("delivery_date"):
                metadata["call_reason_summary"] = f"Delivery reminder for scheduled delivery on {metadata['delivery_date']}"
        
        # CRITICAL: Set metadata in assistantOverrides so it's accessible to the assistant
        # Vapi requires metadata to be in assistantOverrides for the assistant to access it
        if "assistantOverrides" not in assistant_config:
            assistant_config["assistantOverrides"] = {}
        assistant_config["assistantOverrides"]["metadata"] = metadata
        # Also set at top level for webhook processing
        assistant_config["metadata"] = metadata
        
        # CRITICAL: Log the exact metadata being sent to Vapi
        logger.info(
            "metadata_being_sent_to_vapi",
            metadata=metadata,
            call_type=call_type,
            customer_id=customer_data.get("customer_id")
        )
        
        # CRITICAL: Log the customer name being used
        logger.info(
            "setting_customer_name",
            customer_name=customer_name,
            customer_id=customer_data.get("customer_id"),
            call_type=call_type
        )
        
        # CRITICAL: Set dynamic firstMessage with customer name if not already set in overrides
        # This ensures the assistant has the name directly in the first message
        if customer_name:
            # Only set firstMessage if not already provided in overrides
            if not assistant_overrides or not assistant_overrides.get("assistantOverrides", {}).get("firstMessage"):
                if "assistantOverrides" not in assistant_config:
                    assistant_config["assistantOverrides"] = {}
                # Set a natural greeting with the customer name - USE THE EXACT NAME
                first_message = f"Hi {customer_name}! This is Riley calling from Fontis Water. How are you doing today?"
                assistant_config["assistantOverrides"]["firstMessage"] = first_message
                logger.info(
                    "first_message_set",
                    first_message=first_message,
                    customer_name=customer_name
                )
        
        # Apply overrides if provided
        if assistant_overrides:
            overrides = dict(assistant_overrides)  # shallow copy to avoid mutation
            override_metadata = overrides.pop("metadata", None)
            if override_metadata:
                # Update top-level metadata
                assistant_config["metadata"].update({k: str(v) for k, v in override_metadata.items() if v not in (None, "")})
                # CRITICAL: Also update assistantOverrides.metadata so assistant can access it
                if "assistantOverrides" not in assistant_config:
                    assistant_config["assistantOverrides"] = {}
                if "metadata" not in assistant_config["assistantOverrides"]:
                    assistant_config["assistantOverrides"]["metadata"] = {}
                assistant_config["assistantOverrides"]["metadata"].update({k: str(v) for k, v in override_metadata.items() if v not in (None, "")})
            
            # If assistantOverrides has firstMessage, use it (allows dynamic greeting with name)
            assistant_overrides_dict = overrides.pop("assistantOverrides", {})
            if assistant_overrides_dict:
                # Merge with existing assistantOverrides
                if "assistantOverrides" not in assistant_config:
                    assistant_config["assistantOverrides"] = {}
                # CRITICAL: If override has metadata, merge it (don't overwrite)
                if "metadata" in assistant_overrides_dict:
                    if "metadata" not in assistant_config["assistantOverrides"]:
                        assistant_config["assistantOverrides"]["metadata"] = {}
                    assistant_config["assistantOverrides"]["metadata"].update({k: str(v) for k, v in assistant_overrides_dict["metadata"].items() if v not in (None, "")})
                # CRITICAL: If override has firstMessage, log it to verify the name
                if "firstMessage" in assistant_overrides_dict:
                    logger.info(
                        "override_first_message",
                        first_message=assistant_overrides_dict["firstMessage"],
                        customer_name=customer_name
                    )
                # Update other fields (but preserve metadata we just merged)
                other_overrides = {k: v for k, v in assistant_overrides_dict.items() if k != "metadata"}
                assistant_config["assistantOverrides"].update(other_overrides)
            
            assistant_config.update(overrides)
        
        # CRITICAL: Final verification - log what's being sent to Vapi
        final_metadata_name = assistant_config["metadata"].get("customer_name")
        final_customer_name = assistant_config["customer"].get("name")
        final_first_message = assistant_config.get("assistantOverrides", {}).get("firstMessage")
        
        logger.info(
            "final_assistant_config",
            customer_name_in_metadata=final_metadata_name,
            customer_name_in_customer=final_customer_name,
            first_message=final_first_message,
            original_customer_name_from_data=customer_name
        )
        
        # CRITICAL: Verify consistency - all should have the same name
        if customer_name and (final_metadata_name != customer_name or final_customer_name != customer_name):
            logger.error(
                "customer_name_mismatch",
                expected=customer_name,
                metadata_name=final_metadata_name,
                customer_name=final_customer_name,
                first_message=final_first_message
            )
        
        # CRITICAL: Log the exact JSON payload being sent to Vapi
        # Log both top-level metadata and assistantOverrides.metadata
        assistant_overrides_meta = assistant_config.get("assistantOverrides", {}).get("metadata", {})
        logger.info(
            "sending_to_vapi",
            payload_metadata=assistant_config.get("metadata", {}),
            assistant_overrides_metadata=assistant_overrides_meta,
            declined_amount_in_metadata=assistant_config.get("metadata", {}).get("declined_amount"),
            declined_amount_in_overrides=assistant_overrides_meta.get("declined_amount"),
            call_amount_display=assistant_config.get("metadata", {}).get("call_amount_display"),
            call_type=call_type,
            customer_id=customer_data.get("customer_id")
        )
        
        # CRITICAL: Send SMS BEFORE initiating the call
        # This ensures SMS arrives first, then the call comes
        logger.info(
            "sending_sms_before_call",
            call_type=call_type,
            customer_phone=customer_phone,
            customer_id=customer_data.get("customer_id")
        )
        
        if self.twilio_service.enabled:
            try:
                # Build SMS body from metadata
                sms_body = self._build_sms_body_from_metadata(metadata)
                
                logger.info(
                    "sms_before_call_prepared",
                    customer_phone=customer_phone,
                    sms_body_length=len(sms_body),
                    sms_body_preview=sms_body[:150]
                )
                
                sms_sent, sms_error = self.twilio_service.send_sms(customer_phone, sms_body)
                
                if sms_sent:
                    logger.info(
                        "sms_sent_before_call_SUCCESS",
                        customer_phone=customer_phone,
                        call_type=call_type
                    )
                else:
                    logger.error(
                        "sms_failed_before_call",
                        customer_phone=customer_phone,
                        error=sms_error,
                        call_type=call_type
                    )
            except Exception as sms_exc:  # noqa: BLE001
                logger.error(
                    "sms_exception_before_call",
                    customer_phone=customer_phone,
                    error=str(sms_exc),
                    exc_info=True
                )
                # Continue with call even if SMS fails
        else:
            logger.warning(
                "twilio_not_enabled_before_call",
                customer_phone=customer_phone,
                call_type=call_type,
                twilio_account_sid=bool(settings.twilio_account_sid),
                twilio_auth_token=bool(settings.twilio_auth_token),
                twilio_from_number=bool(settings.twilio_from_number)
            )
        
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
    
    def _build_sms_body_from_metadata(self, metadata: Dict[str, Any]) -> str:
        """
        Build SMS message body from metadata.
        Explicitly states the call type/reason at the beginning.
        """
        customer_name = metadata.get("customer_name") or "there"
        call_type = metadata.get("call_type", "")
        
        # For declined payment - EXPLICITLY STATE IT'S ABOUT DECLINED PAYMENT
        if call_type == "declined_payment":
            declined_amount = metadata.get("call_amount_display") or metadata.get("declined_amount", "")
            if declined_amount:
                # Clean amount if needed
                amount_clean = declined_amount.replace("$", "").replace(",", "").strip()
                try:
                    amount_float = float(amount_clean)
                    amount_formatted = f"${amount_float:.2f}"
                except (ValueError, TypeError):
                    amount_formatted = declined_amount if declined_amount.startswith("$") else f"${declined_amount}"
                
                return (
                    f"Fontis Water - Declined Payment Alert: Hi {customer_name}, your payment of {amount_formatted} did not go through. "
                    "Please update your payment method at fontiswater.com or call us at (678) 303-4022. Thank you!"
                )
            else:
                return (
                    f"Fontis Water - Declined Payment Alert: Hi {customer_name}, your recent payment did not go through. "
                    "Please update your payment method at fontiswater.com or call us at (678) 303-4022. Thank you!"
                )
        
        # For collections - EXPLICITLY STATE IT'S ABOUT DUE PAYMENT
        elif call_type == "collections":
            past_due = metadata.get("call_amount_display") or metadata.get("past_due_amount", "")
            if past_due:
                amount_clean = past_due.replace("$", "").replace(",", "").strip()
                try:
                    amount_float = float(amount_clean)
                    amount_formatted = f"${amount_float:.2f}"
                except (ValueError, TypeError):
                    amount_formatted = past_due if past_due.startswith("$") else f"${past_due}"
                
                return (
                    f"Fontis Water - Past Due Payment: Hi {customer_name}, your account has a past due balance of {amount_formatted}. "
                    "Please make a payment at fontiswater.com or call us at (678) 303-4022. Thank you!"
                )
            else:
                return (
                    f"Fontis Water - Past Due Payment: Hi {customer_name}, your account has a past due balance. "
                    "Please make a payment at fontiswater.com or call us at (678) 303-4022. Thank you!"
                )
        
        # For delivery reminder - EXPLICITLY STATE IT'S ABOUT DELIVERY REMINDER
        elif call_type == "delivery_reminder":
            delivery_date = metadata.get("call_delivery_date") or metadata.get("delivery_date", "")
            if delivery_date:
                try:
                    date_obj = datetime.strptime(delivery_date, "%Y-%m-%d")
                    formatted_date = date_obj.strftime("%B %d")
                except:
                    formatted_date = delivery_date
                
                return (
                    f"Fontis Water - Delivery Reminder: Hi {customer_name}, your next delivery is scheduled for {formatted_date}. "
                    "Please have your empty bottles ready for pickup. To reschedule, call us at (678) 303-4022. Thank you!"
                )
            else:
                return (
                    f"Fontis Water - Delivery Reminder: Hi {customer_name}, you have an upcoming delivery scheduled. "
                    "Please have your empty bottles ready for pickup. To reschedule, call us at (678) 303-4022. Thank you!"
                )
        
        # Fallback
        return (
            f"Fontis Water: Hi {customer_name}, we have an important update regarding your account. "
            "Please call us at (678) 303-4022 if you have any questions. Thank you!"
        )
    
    async def send_sms(
        self,
        customer_phone: str,
        message: str,
        customer_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send SMS notification via Twilio.
        
        Args:
            customer_phone: Customer phone number (E.164 format)
            message: SMS message content
            customer_data: Optional customer context
        
        Returns:
            SMS send status with success flag and message ID/error
        """
        logger.info("sending_sms", phone=customer_phone, message_length=len(message))
        
        # Use Twilio for SMS (Vapi doesn't have native SMS support)
        success, error = self.twilio_service.send_sms(customer_phone, message)
        
        if not success:
            error_msg = error or "Failed to send SMS"
            logger.error("sms_send_failed", phone=customer_phone, error=error_msg)
            raise VapiError(
                message=f"Failed to send SMS: {error_msg}",
                error_code=ErrorCode.VAPI_CALL_FAILED
            )
        
        # Return a consistent response format
        return {
            "id": f"sms_{customer_phone}_{datetime.utcnow().isoformat()}",
            "status": "sent",
            "phone": customer_phone,
            "message": "SMS sent successfully"
        }


# Singleton instance
_outbound_service: Optional[OutboundCallService] = None


def get_outbound_service() -> OutboundCallService:
    """Get or create outbound call service singleton."""
    global _outbound_service
    if _outbound_service is None:
        _outbound_service = OutboundCallService()
    return _outbound_service

