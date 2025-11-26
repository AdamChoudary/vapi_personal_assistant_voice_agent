"""
Admin endpoints for triggering outbound calls.
Used to manually initiate declined payment, collections, and delivery reminder calls.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import structlog

from src.services.outbound_call_service import get_outbound_service
from src.services.fontis_client import FontisClient
from src.core.deps import get_fontis_client
from src.core.security import verify_api_key

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/admin/outbound", tags=["admin", "outbound"])


@router.post("/update-status", dependencies=[Depends(verify_api_key)])
async def manual_update_status(
    row_index: int,
    status: str,
    call_id: str | None = None,
    error: str | None = None
):
    """
    Manually update Google Sheet status for a row.
    Useful for testing and fixing stuck statuses.
    """
    try:
        tracking_service = OutboundTrackingService()
        tracking_service.update_row(
            row_index=row_index,
            status=status,
            call_id=call_id,
            error=error,
            last_attempt_iso=datetime.utcnow().isoformat()
        )
        return {
            "success": True,
            "message": f"Status updated to '{status}' for row {row_index}",
            "row_index": row_index,
            "status": status
        }
    except Exception as e:
        logger.error("manual_status_update_failed", row_index=row_index, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update status: {str(e)}"
        )


class DeclinedPaymentCallRequest(BaseModel):
    """Request to initiate declined payment call."""
    customer_id: str = Field(..., description="Fontis customer ID")
    customer_phone: str = Field(..., description="Customer phone number (E.164 format)")
    customer_name: str = Field(..., description="Customer name")
    declined_amount: Optional[float] = Field(None, description="Amount that was declined")
    account_balance: Optional[float] = Field(None, description="Current account balance")
    message: Optional[str] = Field(None, description="Custom first message for the AI agent to say to the customer")


class CollectionsCallRequest(BaseModel):
    """Request to initiate collections call."""
    customer_id: str = Field(..., description="Fontis customer ID")
    customer_phone: str = Field(..., description="Customer phone number (E.164 format)")
    customer_name: str = Field(..., description="Customer name")
    past_due_amount: float = Field(..., description="Past due amount")
    days_past_due: Optional[int] = Field(None, description="Days past due")
    message: Optional[str] = Field(None, description="Custom first message for the AI agent to say to the customer")


class DeliveryReminderRequest(BaseModel):
    """Request to send delivery reminder."""
    customer_id: str = Field(..., description="Fontis customer ID")
    customer_phone: str = Field(..., description="Customer phone number (E.164 format)")
    customer_name: str = Field(..., description="Customer name")
    delivery_date: str = Field(..., description="Scheduled delivery date (YYYY-MM-DD)")
    send_sms: bool = Field(False, description="Send SMS instead of call")
    account_on_hold: bool = Field(False, description="Account is past due/on hold")
    message: Optional[str] = Field(None, description="Custom first message for the AI agent to say to the customer (only used for calls, not SMS)")


class CallResponse(BaseModel):
    """Response after initiating call."""
    success: bool
    call_id: Optional[str] = None
    message: str
    call_status: Optional[str] = None


@router.post("/declined-payment", response_model=CallResponse)
async def initiate_declined_payment_call(
    request: DeclinedPaymentCallRequest,
    _: str = Depends(verify_api_key)
):
    """
    Initiate outbound call for declined payment.
    
    Per docs: "Contact customers flagged by automated transaction report.
    Inform customer of declined payment. Advise to update payment online."
    """
    logger.info(
        "declined_payment_call_requested",
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        customer_phone=request.customer_phone
    )
    
    try:
        outbound_service = get_outbound_service()
        
        # CRITICAL: Use the exact customer_name from the request - do not modify it
        customer_name = request.customer_name.strip() if request.customer_name else ""
        logger.info(
            "processing_declined_payment",
            received_customer_name=customer_name,
            customer_id=request.customer_id
        )
        
        # Build call reason summary for agent context
        # CRITICAL: Make the declined amount VERY prominent in the summary
        call_reason_parts = []
        if request.declined_amount:
            # Make the amount very clear and prominent
            call_reason_parts.append(f"Payment of ${request.declined_amount:.2f} was declined - use this EXACT amount: ${request.declined_amount:.2f}")
        if request.account_balance:
            call_reason_parts.append(f"Current account balance is ${request.account_balance:.2f} - DO NOT use this amount, use declined_amount instead")
        call_reason_summary = ". ".join(call_reason_parts) if call_reason_parts else "Payment was declined"
        
        customer_data = {
            "customer_id": request.customer_id,
            "name": customer_name,  # Use the exact name from request
            "customer_name": customer_name,  # Also set as customer_name for metadata
            "declined_amount": request.declined_amount,
            "account_balance": request.account_balance,
            "call_reason_summary": call_reason_summary,  # Help agent understand why calling
        }
        
        # Add formatted amount display for easy reading
        if request.declined_amount:
            customer_data["call_amount_display"] = f"${request.declined_amount:.2f}"
        
        # Add custom message to metadata as context (not firstMessage)
        # This allows agent to introduce itself first, then use message naturally
        if request.message:
            customer_data["custom_message_context"] = request.message
        
        # Log metadata being prepared for agent
        logger.info(
            "declined_payment_metadata_prepared",
            customer_name=customer_name,
            declined_amount=request.declined_amount,
            call_reason_summary=call_reason_summary,
            has_custom_message=bool(request.message)
        )
        
        call_result = await outbound_service.initiate_call(
            customer_phone=request.customer_phone,
            call_type="declined_payment",
            customer_data=customer_data
        )
        
        return CallResponse(
            success=True,
            call_id=call_result.get("id"),
            message=f"Declined payment call initiated to {request.customer_name}",
            call_status=call_result.get("status")
        )
        
    except Exception as e:
        logger.error("declined_payment_call_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.post("/collections", response_model=CallResponse)
async def initiate_collections_call(
    request: CollectionsCallRequest,
    _: str = Depends(verify_api_key)
):
    """
    Initiate outbound collections call.
    
    Per docs: "Contact past due accounts with similar flow to declined payments.
    Communicate outstanding balance and payment options."
    """
    logger.info(
        "collections_call_requested",
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        past_due_amount=request.past_due_amount
    )
    
    try:
        outbound_service = get_outbound_service()
        
        # CRITICAL: Use the exact customer_name from the request - do not modify it
        customer_name = request.customer_name.strip() if request.customer_name else ""
        logger.info(
            "processing_collections",
            received_customer_name=customer_name,
            customer_id=request.customer_id
        )
        
        # Build call reason summary for agent context
        call_reason_summary = f"Account has past due balance of ${request.past_due_amount:.2f}"
        if request.days_past_due:
            call_reason_summary += f" ({request.days_past_due} days past due)"
        
        customer_data = {
            "customer_id": request.customer_id,
            "name": customer_name,  # Use the exact name from request
            "customer_name": customer_name,  # Also set as customer_name for metadata
            "past_due_amount": request.past_due_amount,
            "days_past_due": request.days_past_due,
            "call_reason_summary": call_reason_summary,  # Help agent understand why calling
        }
        
        # Add formatted amount display for easy reading
        customer_data["call_amount_display"] = f"${request.past_due_amount:.2f}"
        
        # Add custom message to metadata as context (not firstMessage)
        # This allows agent to introduce itself first, then use message naturally
        if request.message:
            customer_data["custom_message_context"] = request.message
        
        # Log metadata being prepared for agent
        logger.info(
            "collections_metadata_prepared",
            customer_name=customer_name,
            past_due_amount=request.past_due_amount,
            call_reason_summary=call_reason_summary,
            has_custom_message=bool(request.message)
        )
        
        call_result = await outbound_service.initiate_call(
            customer_phone=request.customer_phone,
            call_type="collections",
            customer_data=customer_data
        )
        
        return CallResponse(
            success=True,
            call_id=call_result.get("id"),
            message=f"Collections call initiated to {request.customer_name}",
            call_status=call_result.get("status")
        )
        
    except Exception as e:
        logger.error("collections_call_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate call: {str(e)}"
        )


@router.post("/delivery-reminder", response_model=CallResponse)
async def send_delivery_reminder(
    request: DeliveryReminderRequest,
    _: str = Depends(verify_api_key)
):
    """
    Send delivery reminder (call or SMS).
    
    Per docs: "Call or text reminder before delivery. If customer is past due or on hold:
    Inform them delivery will not occur due to account status."
    """
    logger.info(
        "delivery_reminder_requested",
        customer_id=request.customer_id,
        customer_name=request.customer_name,
        delivery_date=request.delivery_date,
        send_sms=request.send_sms
    )
    
    try:
        outbound_service = get_outbound_service()
        
        # CRITICAL: Use the exact customer_name from the request - do not modify it
        customer_name = request.customer_name.strip() if request.customer_name else ""
        logger.info(
            "processing_delivery_reminder",
            received_customer_name=customer_name,
            customer_id=request.customer_id
        )
        
        # Build call reason summary for agent context
        if request.account_on_hold:
            call_reason_summary = f"Delivery scheduled for {request.delivery_date} cannot be completed due to outstanding balance"
        else:
            call_reason_summary = f"Delivery reminder for scheduled delivery on {request.delivery_date}"
        
        customer_data = {
            "customer_id": request.customer_id,
            "name": customer_name,  # Use the exact name from request
            "customer_name": customer_name,  # Also set as customer_name for metadata
            "delivery_date": request.delivery_date,
            "account_on_hold": request.account_on_hold,
            "call_reason_summary": call_reason_summary,  # Help agent understand why calling
        }
        
        # Add formatted delivery date for easy reading
        customer_data["call_delivery_date"] = request.delivery_date
        
        # Log metadata being prepared for agent (only for calls, not SMS)
        if not request.send_sms:
            logger.info(
                "delivery_reminder_metadata_prepared",
                customer_name=customer_name,
                delivery_date=request.delivery_date,
                call_reason_summary=call_reason_summary,
                account_on_hold=request.account_on_hold,
                has_custom_message=bool(request.message)
            )
        
        if request.send_sms:
            # Send SMS reminder
            if request.account_on_hold:
                message = (
                    f"Hi {request.customer_name}, this is Fontis Water. "
                    f"Your scheduled delivery for {request.delivery_date} cannot be completed "
                    f"due to an outstanding balance on your account. Please call us at "
                    f"(678) 303-4022 or update your payment at fontisweb.com to resume service."
                )
            else:
                message = (
                    f"Hi {request.customer_name}, this is Fontis Water reminding you of your "
                    f"delivery scheduled for {request.delivery_date}. Please have your empty "
                    f"bottles ready for exchange. Questions? Call (678) 303-4022."
                )
            
            try:
                sms_result = await outbound_service.send_sms(
                    customer_phone=request.customer_phone,
                    message=message,
                    customer_data=customer_data
                )
                
                return CallResponse(
                    success=True,
                    message=f"SMS reminder sent to {request.customer_name}",
                    call_id=sms_result.get("id")
                )
            except Exception as sms_error:
                logger.error("sms_send_failed", error=str(sms_error), exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to send SMS: {str(sms_error)}"
                )
        else:
            # Make reminder call
            # Add custom message to metadata as context (not firstMessage)
            # This allows agent to introduce itself first, then use message naturally
            if request.message:
                customer_data["custom_message_context"] = request.message
            
            call_result = await outbound_service.initiate_call(
                customer_phone=request.customer_phone,
                call_type="delivery_reminder",
                customer_data=customer_data
            )
            
            return CallResponse(
                success=True,
                call_id=call_result.get("id"),
                message=f"Delivery reminder call initiated to {request.customer_name}",
                call_status=call_result.get("status")
            )
        
    except Exception as e:
        logger.error("delivery_reminder_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send reminder: {str(e)}"
        )


@router.get("/call-status/{call_id}")
async def get_call_status(
    call_id: str,
    _: str = Depends(verify_api_key)
):
    """Get status of an outbound call."""
    try:
        outbound_service = get_outbound_service()
        call_status = await outbound_service.get_call_status(call_id)
        
        return {
            "success": True,
            "call_id": call_id,
            "status": call_status.get("status"),
            "duration": call_status.get("duration"),
            "started_at": call_status.get("startedAt"),
            "ended_at": call_status.get("endedAt"),
            "cost": call_status.get("cost")
        }
    except Exception as e:
        logger.error("get_call_status_failed", call_id=call_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Call not found or error: {str(e)}"
        )

