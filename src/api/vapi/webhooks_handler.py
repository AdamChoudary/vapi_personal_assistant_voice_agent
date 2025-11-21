"""
Vapi webhook handler for function/tool calls.

This handler receives function call requests from Vapi and routes them
to the appropriate internal tool endpoints. It provides:
- Function call routing
- Call context management
- Error handling and retry logic
- Response formatting for Vapi
"""

from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request, Request as FastAPIRequest
import structlog

from src.core.deps import get_fontis_client
from src.services.fontis_client import FontisClient
from src.services.outbound_call_service import get_outbound_service
from src.core.exceptions import FontisAPIError
from src.schemas.vapi import VapiFunctionCall, VapiWebhookEvent
from src.services.outbound_tracking_service import OutboundTrackingService
from src.services.twilio_service import TwilioService

# Import all tool handlers
from src.api.tools import customer, delivery, billing, contracts, routes, onboarding

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/vapi", tags=["vapi"])

# In-memory call context store (replace with Redis in production)
call_contexts: dict[str, dict[str, Any]] = {}


@router.get("/webhooks/test")
async def test_webhook_endpoint():
    """Test endpoint to verify webhook URL is accessible."""
    return {
        "status": "ok",
        "message": "Webhook endpoint is accessible",
        "endpoint": "/vapi/webhooks",
        "timestamp": datetime.utcnow().isoformat()
    }
def store_call_context(call_id: str, key: str, value: Any) -> None:
    """Store context data for a call session."""
    if call_id not in call_contexts:
        call_contexts[call_id] = {}
    call_contexts[call_id][key] = value


def get_call_context(call_id: str, key: str, default: Any = None) -> Any:
    """Retrieve context data for a call session."""
    return call_contexts.get(call_id, {}).get(key, default)


def clear_call_context(call_id: str) -> None:
    """Clear context data after call ends."""
    if call_id in call_contexts:
        del call_contexts[call_id]


@router.post("/webhooks")
async def handle_vapi_webhook(
    request: FastAPIRequest,
    background_tasks: BackgroundTasks,
    fontis: FontisClient = Depends(get_fontis_client)
):
    """
    Handle incoming webhooks from Vapi.
    
    Vapi sends various webhook events:
    - function-call: AI wants to call a tool
    - call-start: New call initiated
    - call-end: Call completed
    - transcript: Real-time transcription
    - hang: Call disconnected
    """
    # Parse request body - handle both structured and raw JSON
    try:
        body = await request.json()
        logger.info("webhook_raw_received", body_type=type(body).__name__, body_keys=list(body.keys()) if isinstance(body, dict) else "not_dict")
    except Exception as parse_err:
        logger.error("webhook_parse_error", error=str(parse_err))
        return {"success": False, "error": "Failed to parse request body"}
    
    # Try to parse as VapiWebhookEvent, but handle gracefully if it fails
    try:
        event = VapiWebhookEvent(**body)
    except Exception as event_parse_err:
        logger.warning("webhook_event_parse_failed", error=str(event_parse_err), body=body)
        # Create a fallback event object from raw body
        class FallbackEvent:
            def __init__(self, data):
                self.type = data.get("type", "unknown")
                self.call_id = data.get("callId") or data.get("call_id")
                self.timestamp = data.get("timestamp")
                self.call = data.get("call") or {}
                self.metadata = data.get("metadata") or {}
                self.function_name = data.get("functionName") or data.get("function_name")
                self.parameters = data.get("parameters") or {}
                self.transcript = data.get("transcript")
        event = FallbackEvent(body)
    
    event_type = event.type
    
    logger.info(
        "vapi_webhook_received",
        event_type=event_type,
        call_id=event.call_id if hasattr(event, 'call_id') else None
    )
    
    # Route based on event type
    if event_type == "function-call":
        return await handle_function_call(event, fontis)
    
    elif event_type == "call-start":
        # Initialize call context and store metadata for later use
        call_payload = event.call or {}
        call_id = event.call_id if hasattr(event, 'call_id') else call_payload.get("id")
        
        if call_id:
            # Store metadata from call-start event so we can use it in call-end
            metadata = call_payload.get("metadata") or {}
            if hasattr(event, 'metadata') and event.metadata:
                if isinstance(event.metadata, dict):
                    metadata.update(event.metadata)
            
            store_call_context(call_id, "started_at", event.timestamp)
            if metadata:
                store_call_context(call_id, "metadata", metadata)
            
            logger.info(
                "call_started",
                call_id=call_id,
                has_metadata=bool(metadata),
                metadata_keys=list(metadata.keys()) if metadata else []
            )
        return {"success": True, "message": "Call started"}
    
    elif event_type == "call-end":
        call_payload = event.call or {}
        
        # CRITICAL: Extract metadata from ALL possible locations
        # Vapi might put metadata in different places depending on how the call was initiated
        metadata = {}
        
        # Location 1: Inside call object
        if call_payload.get("metadata"):
            metadata.update(call_payload.get("metadata", {}))
        
        # Location 2: At event level (if Vapi sends it there)
        if hasattr(event, 'metadata') and event.metadata:
            if isinstance(event.metadata, dict):
                metadata.update(event.metadata)
        
        # Location 3: Check if metadata is in the raw event dict
        event_dict = event.model_dump() if hasattr(event, 'model_dump') else {}
        if event_dict.get("metadata"):
            if isinstance(event_dict["metadata"], dict):
                metadata.update(event_dict["metadata"])
        
        # Location 4: Check call context (stored when call started)
        call_id = event.call_id if hasattr(event, "call_id") else call_payload.get("id")
        if call_id and call_id in call_contexts:
            context_metadata = call_contexts[call_id].get("metadata")
            if context_metadata and isinstance(context_metadata, dict):
                metadata.update(context_metadata)
        
        timestamp = event.timestamp

        logger.info(
            "call_end_received",
            call_id=call_id,
            call_status=call_payload.get("status"),
            hang_reason=call_payload.get("hangReason"),
            has_metadata=bool(metadata),
            metadata_keys=list(metadata.keys()) if metadata else [],
            call_payload_keys=list(call_payload.keys()) if call_payload else [],
            event_keys=list(event_dict.keys()) if event_dict else []
        )

        background_tasks.add_task(
            process_call_end_event,
            call_id,
            call_payload,
            metadata,
            timestamp,
        )
        if call_id:
            background_tasks.add_task(clear_call_context, call_id)
        return {"success": True, "message": "Call ended"}
    
    elif event_type in ["transcript", "speech-update"]:
        # Log transcript for debugging
        logger.debug(
            "transcript_received",
            call_id=event.call_id if hasattr(event, 'call_id') else None,
            transcript=event.transcript if hasattr(event, 'transcript') else None
        )
        return {"success": True}
    
    elif event_type == "hang":
        # Call disconnected
        if hasattr(event, 'call_id'):
            background_tasks.add_task(clear_call_context, event.call_id)
            logger.info("call_hung_up", call_id=event.call_id)
        return {"success": True, "message": "Call hung up"}
    
    else:
        # Unknown event type
        logger.warning("unknown_webhook_event", event_type=event_type)
        return {"success": True, "message": "Event received"}


async def handle_function_call(
    event: VapiWebhookEvent,
    fontis: FontisClient
) -> dict[str, Any]:
    """
    Handle function/tool call requests from Vapi.
    
    Routes the function call to the appropriate internal tool endpoint
    and returns a formatted response for Vapi to speak.
    """
    function_name = event.function_name
    parameters = event.parameters or {}
    call_id = event.call_id
    
    logger.info(
        "function_call_received",
        function_name=function_name,
        call_id=call_id,
        parameters=parameters
    )
    
    try:
        # Route to appropriate handler
        result = await route_function_call(
            function_name=function_name,
            parameters=parameters,
            call_id=call_id,
            fontis=fontis
        )
        
        # Store important context (customerId, deliveryId)
        if function_name in ["customer_search", "customer_details"]:
            if result.get("success") and result.get("data"):
                data = result["data"]
                if isinstance(data, dict):
                    # Store customer info for subsequent calls
                    if "customerId" in data:
                        store_call_context(call_id, "customerId", data["customerId"])
                    if "deliveryId" in data:
                        store_call_context(call_id, "deliveryId", data["deliveryId"])
                    if "name" in data:
                        store_call_context(call_id, "customerName", data["name"])
        
        logger.info(
            "function_call_success",
            function_name=function_name,
            call_id=call_id
        )
        
        # Return the result directly - VAPI expects the tool result, not wrapped
        return result
        
    except FontisAPIError as e:
        logger.error(
            "function_call_error",
            function_name=function_name,
            call_id=call_id,
            error=str(e)
        )
        # Return error in format VAPI expects
        return {
            "success": False,
            "message": "I'm having trouble accessing that information right now. Let me try again or connect you with someone who can help.",
            "error": str(e)
        }
    
    except Exception as e:
        logger.error(
            "function_call_unexpected_error",
            function_name=function_name,
            call_id=call_id,
            error=str(e),
            exc_info=True
        )
        # Return error in format VAPI expects
        return {
            "success": False,
            "message": "I encountered an unexpected issue. Let me connect you with a representative who can assist you.",
            "error": str(e)
        }


async def route_function_call(
    function_name: str,
    parameters: dict[str, Any],
    call_id: str,
    fontis: FontisClient
) -> dict[str, Any]:
    """
    Route function call to appropriate internal tool endpoint.
    
    This acts as a dispatcher, matching Vapi function names to your
    internal FastAPI tool endpoints.
    """
    
    # Customer tools
    if function_name == "customer_search":
        from src.schemas.tools import CustomerSearchTool
        params = CustomerSearchTool(**parameters)
        return await customer_search_handler(params, fontis)
    
    elif function_name == "customer_details":
        from src.schemas.tools import CustomerDetailsTool
        params = CustomerDetailsTool(**parameters)
        return await customer_details_handler(params, fontis)
    
    elif function_name == "finance_info":
        from src.schemas.tools import FinanceDeliveryInfoTool
        params = FinanceDeliveryInfoTool(**parameters)
        return await finance_info_handler(params, fontis)
    
    # Delivery tools
    elif function_name == "delivery_stops":
        from src.schemas.tools import DeliveryStopsTool
        params = DeliveryStopsTool(**parameters)
        return await delivery_stops_handler(params, fontis)
    
    elif function_name == "next_delivery":
        from src.schemas.tools import NextScheduledDeliveryTool
        params = NextScheduledDeliveryTool(**parameters)
        return await next_delivery_handler(params, fontis)
    
    elif function_name == "default_products":
        from src.schemas.tools import DefaultProductsTool
        params = DefaultProductsTool(**parameters)
        return await default_products_handler(params, fontis)
    
    elif function_name == "delivery_summary":
        from src.schemas.tools import DeliverySummaryTool
        from src.api.tools.delivery import get_delivery_summary
        params = DeliverySummaryTool(**parameters)
        return await get_delivery_summary(params, fontis)
    
    elif function_name == "delivery_schedule":
        from src.schemas.tools import DeliveryScheduleTool
        from src.api.tools.delivery import get_delivery_schedule
        params = DeliveryScheduleTool(**parameters)
        return await get_delivery_schedule(params, fontis)
    
    elif function_name == "work_order_status":
        from src.schemas.tools import WorkOrderStatusTool
        from src.api.tools.delivery import get_work_order_status
        params = WorkOrderStatusTool(**parameters)
        return await get_work_order_status(params, fontis)
    
    elif function_name == "pricing_breakdown":
        from src.schemas.tools import PricingBreakdownTool
        from src.api.tools.delivery import get_pricing_breakdown
        params = PricingBreakdownTool(**parameters)
        return await get_pricing_breakdown(params, fontis)
    
    elif function_name == "order_change_status":
        from src.schemas.tools import OrderChangeStatusTool
        from src.api.tools.delivery import get_order_change_status
        params = OrderChangeStatusTool(**parameters)
        return await get_order_change_status(params, fontis)
    
    elif function_name == "orders_search":
        from src.schemas.tools import OrdersSearchTool
        params = OrdersSearchTool(**parameters)
        return await orders_search_handler(params, fontis)
    
    # Billing tools
    elif function_name == "account_balance":
        from src.schemas.tools import AccountBalanceTool
        params = AccountBalanceTool(**parameters)
        return await account_balance_handler(params, fontis)
    
    elif function_name == "invoice_history":
        from src.schemas.tools import InvoiceHistoryTool
        params = InvoiceHistoryTool(**parameters)
        return await invoice_history_handler(params, fontis)
    
    elif function_name == "invoice_detail":
        from src.schemas.tools import InvoiceDetailTool
        params = InvoiceDetailTool(**parameters)
        return await invoice_detail_handler(params, fontis)
    
    elif function_name == "payment_methods":
        from src.schemas.tools import BillingMethodsTool
        params = BillingMethodsTool(**parameters)
        return await payment_methods_handler(params, fontis)
    
    elif function_name == "payment_expiry_alerts":
        from src.schemas.tools import PaymentExpiryAlertTool
        from src.api.tools.billing import get_payment_expiry_alerts
        params = PaymentExpiryAlertTool(**parameters)
        return await get_payment_expiry_alerts(params, fontis)
    
    elif function_name == "products_catalog" or function_name == "products":
        from src.schemas.tools import ProductsTool
        params = ProductsTool(**parameters)
        return await products_catalog_handler(params, fontis)
    
    # Contract tools
    elif function_name == "customer_contracts":
        from src.schemas.tools import ContractsTool
        params = ContractsTool(**parameters)
        return await customer_contracts_handler(params, fontis)
    
    # Route tools
    elif function_name == "route_stops":
        from src.schemas.tools import RouteStopsTool
        params = RouteStopsTool(**parameters)
        return await route_stops_handler(params, fontis)
    
    # Onboarding tools (JotForm)
    elif function_name == "send_contract":
        from src.schemas.tools import SendContractTool
        params = SendContractTool(**parameters)
        return await send_contract_handler(params)
    
    elif function_name == "contract_status":
        from src.schemas.tools import ContractStatusTool
        params = ContractStatusTool(**parameters)
        return await contract_status_handler(params)

    # Outbound call tools
    elif function_name == "declined_payment_call":
        from src.schemas.tools import DeclinedPaymentCallTool
        params = DeclinedPaymentCallTool(**parameters)
        return await declined_payment_call_handler(params)

    elif function_name == "collections_call":
        from src.schemas.tools import CollectionsCallTool
        params = CollectionsCallTool(**parameters)
        return await collections_call_handler(params)

    elif function_name == "delivery_reminder_call":
        from src.schemas.tools import DeliveryReminderCallTool
        params = DeliveryReminderCallTool(**parameters)
        return await delivery_reminder_call_handler(params)
    
    else:
        raise ValueError(f"Unknown function: {function_name}")


# Individual tool handlers (simplified wrappers around your existing tools)


def process_call_end_event(
    call_id: str | None,
    call_payload: dict[str, Any],
    metadata: dict[str, Any],
    timestamp: str | None,
) -> None:
    """
    Update Google Sheet status and optionally trigger SMS fallback when a call ends.
    """
    logger = structlog.get_logger(__name__)

    try:
        # CRITICAL: Log EVERYTHING for debugging
        logger.info(
            "processing_call_end_START",
            call_id=call_id,
            call_payload_keys=list(call_payload.keys()) if call_payload else [],
            call_payload_full=str(call_payload)[:500],  # Log first 500 chars of payload
            metadata_keys=list(metadata.keys()) if metadata else [],
            metadata_full=str(metadata)[:500],  # Log first 500 chars of metadata
            call_status=call_payload.get("status"),
            hang_reason=call_payload.get("hangReason"),
            timestamp=timestamp,
        )

        row_index_value = metadata.get("sheet_row_index")
        if not row_index_value:
            logger.warning(
                "call_end_missing_row_index",
                call_id=call_id,
                metadata=metadata,
                call_payload_keys=list(call_payload.keys()),
                metadata_keys=list(metadata.keys())
            )
            # Still try to send SMS if we have customer phone, even without row_index
            customer_phone = metadata.get("customer_phone") or call_payload.get("customer", {}).get("number")
            if customer_phone:
                customer_phone = normalize_phone_for_sms(customer_phone)
                logger.info(
                    "attempting_sms_without_sheet_index",
                    customer_phone=customer_phone,
                    call_id=call_id,
                    metadata_keys=list(metadata.keys())
                )
                twilio = TwilioService()
                if twilio.enabled:
                    # Determine if call was completed (we don't have full status info, so assume no-answer)
                    sms_body = build_sms_body(metadata, is_completed=False)
                    sms_sent, sms_error = twilio.send_sms(customer_phone, sms_body)
                    logger.info(
                        "sms_sent_without_sheet",
                        sms_sent=sms_sent,
                        sms_error=sms_error,
                        customer_phone=customer_phone,
                        call_id=call_id,
                        sms_body_preview=sms_body[:100] if sms_body else None
                    )
                else:
                    logger.warning(
                        "twilio_not_enabled_no_sheet",
                        customer_phone=customer_phone,
                        call_id=call_id,
                        twilio_enabled=twilio.enabled
                    )
            else:
                logger.warning(
                    "no_phone_for_sms_no_sheet",
                    metadata_keys=list(metadata.keys()),
                    call_payload_customer=call_payload.get("customer"),
                    call_id=call_id
                )
            return

        # CRITICAL: Convert row_index to int, handle string conversion
        try:
            row_index = int(str(row_index_value).strip())
        except (ValueError, TypeError) as row_err:
            logger.error(
                "invalid_row_index",
                row_index_value=row_index_value,
                error=str(row_err),
                call_id=call_id
            )
            # Still try SMS even if row_index is invalid
            customer_phone = metadata.get("customer_phone") or call_payload.get("customer", {}).get("number")
            if customer_phone:
                twilio = TwilioService()
                if twilio.enabled:
                    sms_body = build_sms_body(metadata)
                    sms_sent, sms_error = twilio.send_sms(customer_phone, sms_body)
                    logger.info("sms_attempted_invalid_row", sms_sent=sms_sent, sms_error=sms_error)
            return

        call_status = (call_payload.get("status") or "").lower()
        hang_reason = (call_payload.get("hangReason") or "").lower()
        
        # Also check for status in different formats
        if not call_status:
            call_status = (call_payload.get("callStatus") or "").lower()
        if not hang_reason:
            hang_reason = (call_payload.get("endReason") or "").lower()

        completed_statuses = {"completed", "success", "answered", "ended", "finished"}
        no_answer_statuses = {
            "no_answer", "not_answered", "busy", "failed", "cancelled", "timeout",
            "voicemail", "no-answer", "no_answer", "declined", "rejected",
            "unanswered", "missed", "unavailable"
        }

        is_completed = call_status in completed_statuses
        is_no_answer = call_status in no_answer_statuses or hang_reason in no_answer_statuses

        # Check if call was actually answered (duration > 0 might indicate answered)
        call_duration = call_payload.get("duration") or call_payload.get("callDuration") or 0
        if call_duration and call_duration > 5:  # If call lasted more than 5 seconds, likely answered
            is_completed = True
            is_no_answer = False

        # Default fallbacks if status unavailable
        if not call_status and hang_reason:
            is_no_answer = True
        elif not call_status and not hang_reason:
            # If no status info, assume no answer if duration is very short
            if call_duration and call_duration < 10:
                is_no_answer = True
            else:
                is_completed = True

        logger.info(
            "call_status_determined",
            call_id=call_id,
            call_status=call_status,
            hang_reason=hang_reason,
            call_duration=call_duration,
            is_completed=is_completed,
            is_no_answer=is_no_answer,
        )

        if not (is_completed or is_no_answer):
            logger.warning(
                "call_end_unclassified_status",
                call_id=call_id,
                status=call_status,
                hang_reason=hang_reason,
                call_duration=call_duration,
            )
            # Default to no_answer if we can't classify
            is_no_answer = True

        sms_sent = False
        sms_error: str | None = None
        error_text = hang_reason or call_status or ""
        last_attempt_iso = timestamp or datetime.utcnow().isoformat()

        # Determine sheet status
        if is_completed:
            sheet_status = "Contacted"
        else:
            sheet_status = "No Answer"
        
        # CRITICAL: Send SMS for ALL calls by default (both answered and no-answer)
        twilio = TwilioService()
        customer_phone = metadata.get("customer_phone") or call_payload.get("customer", {}).get("number")
        
        if customer_phone:
            # Normalize phone number to E.164 format for Twilio
            customer_phone = normalize_phone_for_sms(customer_phone)
            
            if twilio.enabled:
                try:
                    logger.info(
                        "attempting_sms_send_for_all_calls",
                        customer_phone=customer_phone,
                        call_id=call_id,
                        call_type=metadata.get("call_type"),
                        call_status="completed" if is_completed else "no_answer"
                    )
                    sms_body = build_sms_body(metadata, is_completed=is_completed)
                    sms_sent, sms_error = twilio.send_sms(customer_phone, sms_body)
                    if sms_sent:
                        if is_completed:
                            sheet_status = "Contacted - SMS Sent"
                        else:
                            sheet_status = "No Answer - SMS Sent"
                        logger.info(
                            "sms_sent_successfully",
                            customer_phone=customer_phone,
                            call_id=call_id,
                            call_status="completed" if is_completed else "no_answer",
                            sms_body=sms_body[:100]  # Log first 100 chars
                        )
                    else:
                        error_text = (sms_error or "") or error_text
                        logger.warning(
                            "sms_send_failed",
                            customer_phone=customer_phone,
                            error=sms_error,
                            call_id=call_id,
                            call_status="completed" if is_completed else "no_answer"
                        )
                except Exception as sms_exc:  # noqa: BLE001
                    logger.error(
                        "sms_send_exception",
                        customer_phone=customer_phone,
                        error=str(sms_exc),
                        call_id=call_id,
                        exc_info=True
                    )
                    sms_error = str(sms_exc)
            else:
                logger.warning(
                    "twilio_not_enabled",
                    customer_phone=customer_phone,
                    call_id=call_id,
                    twilio_enabled=twilio.enabled
                )
        else:
            logger.warning(
                "no_customer_phone_for_sms",
                metadata_keys=list(metadata.keys()),
                call_payload_customer=call_payload.get("customer"),
                call_id=call_id
            )

        # Update Google Sheet - CRITICAL: This must work
        try:
            logger.info("attempting_google_sheet_update", row_index=row_index, status=sheet_status)
            tracking_service = OutboundTrackingService()
            tracking_service.update_row(
                row_index=row_index,
                status=sheet_status,
                call_id=call_id,
                error=error_text,
                last_attempt_iso=last_attempt_iso,
            )
            logger.info(
                "google_sheet_updated_SUCCESS",
                row_index=row_index,
                status=sheet_status,
                call_id=call_id,
                sms_sent=sms_sent
            )
        except Exception as sheet_exc:  # noqa: BLE001
            logger.error(
                "google_sheet_update_FAILED",
                row_index=row_index,
                status=sheet_status,
                error=str(sheet_exc),
                error_type=type(sheet_exc).__name__,
                exc_info=True
            )
            # Don't fail completely if sheet update fails - SMS might have been sent
            # But log it clearly so we can fix it

        logger.info(
            "call_end_processed",
            call_id=call_id,
            sheet_status=sheet_status,
            sms_sent=sms_sent,
            sms_error=sms_error,
            row_index=row_index,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "call_end_processing_failed",
            call_id=call_id,
            error=str(exc),
            metadata=metadata,
            call_payload=call_payload,
            exc_info=True,
        )


def normalize_phone_for_sms(phone: str) -> str:
    """Normalize phone number to E.164 format for Twilio SMS."""
    if not phone:
        return phone
    
    # Remove all non-digit characters except +
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    
    # If it doesn't start with +, assume US number and add +1
    if not cleaned.startswith("+"):
        # Remove leading 1 if present
        if cleaned.startswith("1") and len(cleaned) == 11:
            cleaned = cleaned[1:]
        cleaned = f"+1{cleaned}"
    
    return cleaned


def build_sms_body(metadata: dict[str, Any], is_completed: bool = False) -> str:
    """
    Build SMS message body based on call outcome and metadata.
    
    Args:
        metadata: Call metadata with customer info, call type, etc.
        is_completed: True if call was answered/completed, False if no answer
    """
    customer_name = metadata.get("customer_name") or "there"
    sms_reason = metadata.get("sms_reason") or "we have an important update regarding your Fontis Water account"
    call_type_label = metadata.get("call_type_label") or "account"
    call_type = metadata.get("call_type", "")

    # Different messages based on call outcome
    if is_completed:
        # Call was answered - send follow-up SMS with key info
        if call_type == "declined_payment":
            declined_amount = metadata.get("declined_amount") or metadata.get("call_amount_display", "")
            if declined_amount:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    f"Just a reminder: your payment of ${declined_amount} did not go through. "
                    "You can update your payment information at fontiswater.com or call us at (678) 303-4022. "
                    "Thank you!"
                )
            else:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    "Just a reminder: your recent payment did not go through. "
                    "You can update your payment information at fontiswater.com or call us at (678) 303-4022. "
                    "Thank you!"
                )
        elif call_type == "collections":
            past_due = metadata.get("past_due_amount") or metadata.get("call_amount_display", "")
            if past_due:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    f"Just a reminder: your account has a past due balance of ${past_due}. "
                    "You can make a payment at fontiswater.com or call us at (678) 303-4022. "
                    "Thank you!"
                )
            else:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    "Just a reminder: your account has a past due balance. "
                    "You can make a payment at fontiswater.com or call us at (678) 303-4022. "
                    "Thank you!"
                )
        elif call_type == "delivery_reminder":
            delivery_date = metadata.get("delivery_date") or metadata.get("call_delivery_date", "")
            if delivery_date:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    f"Just a reminder: your next delivery is scheduled for {delivery_date}. "
                    "Please have your empty bottles ready. If you need to reschedule, call us at (678) 303-4022. "
                    "Thank you!"
                )
            else:
                message = (
                    f"Hi {customer_name}, thank you for speaking with us today. "
                    "Just a reminder: you have an upcoming delivery scheduled. "
                    "Please have your empty bottles ready. If you need to reschedule, call us at (678) 303-4022. "
                    "Thank you!"
                )
        else:
            # Generic follow-up for answered calls
            message = (
                f"Hi {customer_name}, thank you for speaking with us today about {sms_reason}. "
                "If you have any questions, please call us at (678) 303-4022. Thank you!"
            )
    else:
        # Call was not answered - send initial message
        if "delivery" in (call_type_label or "").lower() or call_type == "delivery_reminder":
            delivery_date = metadata.get("delivery_date") or metadata.get("call_delivery_date", "")
            if delivery_date:
                message = (
                    f"Hi {customer_name}, Fontis Water here. We tried calling about your delivery scheduled for {delivery_date}. "
                    "Please have your empty bottles ready. If you need to reschedule, call us at (678) 303-4022. "
                    "Thank you!"
                )
            else:
                message = (
                    f"Hi {customer_name}, Fontis Water here. We tried calling about your upcoming delivery. "
                    "Please have your empty bottles ready. If you need to reschedule, call us at (678) 303-4022. "
                    "Thank you!"
                )
        else:
            message = (
                f"Hi {customer_name}, this is Fontis Water. We tried calling about {sms_reason}. "
                "Please contact our team at (678) 303-4022 at your earliest convenience so we can help you. "
                "Thank you!"
            )

    return message


>>>>>>> 7f5d6f0 (Sure! Pl)
async def customer_search_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_search function call."""
    response = await fontis.search_customers(
        lookup=params.lookup,
        offset=params.offset,
        take=params.take
    )
    return response


async def customer_details_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_details function call."""
    response = await fontis.get_customer_details(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def finance_info_handler(params, fontis: FontisClient) -> dict:
    """Handle finance_info function call."""
    # If delivery_id not provided, get customer's primary delivery
    delivery_id = params.delivery_id
    if not delivery_id:
        # Get customer details to find their delivery IDs
        customer = await fontis.get_customer_details(
            customer_id=params.customer_id,
            include_inactive=False
        )
        if customer.get("success") and customer.get("data"):
            # Try to get first delivery ID from customer data
            deliveries = customer["data"].get("deliveries", [])
            if deliveries:
                delivery_id = deliveries[0].get("deliveryId")
    
    if not delivery_id:
        return {
            "success": False,
            "message": "Unable to find delivery information for this customer. They may not have any active deliveries set up.",
            "error": "No delivery ID available"
        }
    
    response = await fontis.get_customer_finance_info(
        customer_id=params.customer_id,
        delivery_id=delivery_id
    )
    return response


async def delivery_stops_handler(params, fontis: FontisClient) -> dict:
    """Handle delivery_stops function call."""
    response = await fontis.get_delivery_stops(
        customer_id=params.customer_id,
        offset=params.offset,
        take=params.take
    )
    return response


async def next_delivery_handler(params, fontis: FontisClient) -> dict:
    """Handle next_delivery function call."""
    response = await fontis.get_next_scheduled_delivery(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        days_ahead=params.days_ahead
    )
    return response


async def default_products_handler(params, fontis: FontisClient) -> dict:
    """Handle default_products function call."""
    response = await fontis.get_default_products(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id
    )
    return response


async def orders_search_handler(params, fontis: FontisClient) -> dict:
    """Handle orders_search function call."""
    response = await fontis.search_orders(
        ticket_number=params.ticket_number,
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        only_open_orders=params.only_open_orders,
        web_products_only=params.web_products_only
    )
    return response


async def account_balance_handler(params, fontis: FontisClient) -> dict:
    """Handle account_balance function call."""
    response = await fontis.get_account_balances(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def invoice_history_handler(params, fontis: FontisClient) -> dict:
    """Handle invoice_history function call."""
    response = await fontis.get_invoice_history(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        number_of_months=params.number_of_months,
        offset=params.offset,
        take=params.take,
        descending=params.descending
    )
    return response


async def invoice_detail_handler(params, fontis: FontisClient) -> dict:
    """Handle invoice_detail function call."""
    response = await fontis.get_invoice_detail(
        customer_id=params.customer_id,
        invoice_key=params.invoice_key,
        invoice_date=params.invoice_date,
        include_signature=params.include_signature,
        include_payments=params.include_payments
    )
    return response


async def payment_methods_handler(params, fontis: FontisClient) -> dict:
    """Handle payment_methods function call."""
    response = await fontis.get_billing_methods(
        customer_id=params.customer_id,
        include_inactive=params.include_inactive
    )
    return response


async def products_catalog_handler(params, fontis: FontisClient) -> dict:
    """Handle products_catalog function call."""
    response = await fontis.get_products(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id,
        postal_code=params.postal_code,
        internet_only=params.internet_only,
        categories=params.categories,
        default_products=params.default_products,
        offset=params.offset,
        take=params.take
    )
    return response


async def customer_contracts_handler(params, fontis: FontisClient) -> dict:
    """Handle customer_contracts function call."""
    response = await fontis.get_customer_contracts(
        customer_id=params.customer_id,
        delivery_id=params.delivery_id
    )
    return response


async def route_stops_handler(params, fontis: FontisClient) -> dict:
    """Handle route_stops function call."""
    response = await fontis.get_route_stops(
        route=params.route,
        route_date=params.route_date,
        account_number=params.account_number
    )
    return response


async def send_contract_handler(params) -> dict:
    """Handle send_contract function call (JotForm integration)."""
    from src.api.tools.onboarding import execute_send_contract
    from src.services.jotform_client import JotFormClient
    from src.core.exceptions import JotFormError

    jotform = JotFormClient()
    try:
        result = await execute_send_contract(params, jotform)
        return result["data"]
    except JotFormError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    finally:
        await jotform.close()


async def contract_status_handler(params) -> dict:
    """Handle contract_status function call (JotForm integration)."""
    from src.services.jotform_client import JotFormClient
    from src.core.exceptions import JotFormError

    jotform = JotFormClient()
    try:
        result = await jotform.get_submission_status(
            submission_id=params.submission_id
        )
        return result
    except JotFormError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    finally:
        await jotform.close()


async def declined_payment_call_handler(params) -> dict[str, Any]:
    """Handle declined payment outbound call."""

    outbound_service = get_outbound_service()
    customer_data = {
        "customer_id": params.customer_id,
        "name": params.customer_name,
        "declined_amount": params.declined_amount,
        "account_balance": params.account_balance
    }

    call_result = await outbound_service.initiate_call(
        customer_phone=params.customer_phone,
        call_type="declined_payment",
        customer_data=customer_data
    )

    return {
        "success": True,
        "callId": call_result.get("id"),
        "status": call_result.get("status"),
        "message": f"Declined payment call initiated to {params.customer_name}"
    }


async def collections_call_handler(params) -> dict[str, Any]:
    """Handle collections outbound call."""

    outbound_service = get_outbound_service()
    customer_data = {
        "customer_id": params.customer_id,
        "name": params.customer_name,
        "past_due_amount": params.past_due_amount,
        "days_past_due": params.days_past_due
    }

    call_result = await outbound_service.initiate_call(
        customer_phone=params.customer_phone,
        call_type="collections",
        customer_data=customer_data
    )

    return {
        "success": True,
        "callId": call_result.get("id"),
        "status": call_result.get("status"),
        "message": f"Collections call initiated to {params.customer_name}"
    }


async def delivery_reminder_call_handler(params) -> dict[str, Any]:
    """Handle delivery reminder outbound call or SMS."""

    outbound_service = get_outbound_service()
    customer_data = {
        "customer_id": params.customer_id,
        "name": params.customer_name,
        "delivery_date": params.delivery_date,
        "account_on_hold": params.account_on_hold
    }

    if params.send_sms:
        if params.account_on_hold:
            message = (
                f"Hi {params.customer_name}, this is Fontis Water. "
                f"Your scheduled delivery for {params.delivery_date} cannot be completed "
                f"due to an outstanding balance on your account. Please call us at "
                f"(678) 303-4022 or update your payment at fontisweb.com to resume service."
            )
        else:
            message = (
                f"Hi {params.customer_name}, this is Fontis Water reminding you of your "
                f"delivery scheduled for {params.delivery_date}. Please have your empty "
                f"bottles ready for exchange. Questions? Call (678) 303-4022."
            )

        sms_result = await outbound_service.send_sms(
            customer_phone=params.customer_phone,
            message=message,
            customer_data=customer_data
        )

        return {
            "success": True,
            "message": f"SMS reminder sent to {params.customer_name}",
            "callId": sms_result.get("id")
        }

    call_result = await outbound_service.initiate_call(
        customer_phone=params.customer_phone,
        call_type="delivery_reminder",
        customer_data=customer_data
    )

    return {
        "success": True,
        "callId": call_result.get("id"),
        "status": call_result.get("status"),
        "message": f"Delivery reminder call initiated to {params.customer_name}"
    }

