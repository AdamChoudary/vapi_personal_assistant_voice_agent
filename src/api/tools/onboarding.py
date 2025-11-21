"""
Onboarding tool endpoints for Vapi AI Assistant.

This module provides API endpoints for customer onboarding:
- Contract generation and sending via JotForm
- Pre-filled form links for new customers
- Contract submission tracking

All endpoints require API key authentication (internal_api_key).
"""

from fastapi import APIRouter, Depends, HTTPException

from src.core.security import verify_api_key
from src.schemas.tools import SendContractTool, ContractStatusTool
from src.services.jotform_client import JotFormClient
from src.core.exceptions import JotFormError
from src.services.twilio_service import TwilioService

router = APIRouter(prefix="/tools/onboarding", tags=["tools-onboarding"])


async def get_jotform_client() -> JotFormClient:
    """
    Dependency to get JotForm client instance.
    
    Returns:
        JotFormClient: Initialized JotForm API client
    
    Raises:
        HTTPException: If JotForm is not configured
    """
    try:
        client = JotFormClient()
        return client
    except JotFormError as e:
        raise HTTPException(status_code=503, detail=str(e))


async def execute_send_contract(params: SendContractTool, jotform: JotFormClient) -> dict:
    """
    Shared implementation for sending or generating JotForm contracts.
    """
    additional_fields = {
        "delivery_preference": params.delivery_preference,
        "company_name": params.company_name,
        "products_of_interest": params.products_of_interest,
        "special_instructions": params.special_instructions,
        "marketing_opt_in": params.marketing_opt_in,
    }
    additional_fields = {
        key: value for key, value in additional_fields.items() if value not in (None, "", [])
    }

    sms_sent = False

    if params.send_email:
        result = await jotform.send_contract_email(
            customer_name=params.customer_name,
            email=params.email,
            phone=params.phone,
            address=params.address,
            city=params.city,
            state=params.state,
            postal_code=params.postal_code,
            **additional_fields,
        )

        sms_error: str | None = None

        contract_data = {
            "success": True,
            "message": "Contract sent successfully via email" if result.get("email_sent") else result.get("message", "Contract link generated"),
            "data": {
                "contract_url": result["form_url"],
                "form_id": result["form_id"],
                "email_sent": result.get("email_sent", False),
                "customer_name": params.customer_name,
                "email": params.email,
                "prefill": result.get("prefill", {}),
                "sms_sent": sms_sent,
            },
        }

        if not result.get("email_sent", False):
            twilio = TwilioService()
            if twilio.enabled:
                sms_body = (
                    f"Hi {params.customer_name}, here is your Fontis Water agreement: {result['form_url']}"
                )
                sms_sent, sms_error = twilio.send_sms(params.phone, sms_body)
                contract_data["data"]["sms_sent"] = sms_sent
                if sms_error:
                    contract_data["data"]["sms_error"] = sms_error
                if sms_sent:
                    contract_data["message"] = "Contract link shared via SMS (JotForm email invitations unavailable)."
                elif sms_error:
                    contract_data["message"] = "Contract link generated, but SMS delivery failed."
            else:
                sms_error = "Twilio is not configured."
                contract_data["data"]["sms_error"] = sms_error

        if not sms_sent and sms_error is None:
            contract_data["data"]["sms_error"] = "SMS delivery not attempted."

        return contract_data

    result = await jotform.create_contract_link(
        customer_name=params.customer_name,
        email=params.email,
        phone=params.phone,
        address=params.address,
        city=params.city,
        state=params.state,
        postal_code=params.postal_code,
        **additional_fields,
    )

    return {
        "success": True,
        "message": "Contract link generated successfully",
        "data": {
            "contract_url": result["url"],
            "form_id": result["form_id"],
            "email_sent": False,
            "sms_sent": False,
            "sms_error": "SMS delivery not attempted.",
            "customer_name": params.customer_name,
            "email": params.email,
            "prefill": result.get("prefill", {}),
        },
    }


@router.post("/send-contract", dependencies=[Depends(verify_api_key)])
async def send_onboarding_contract(
    params: SendContractTool,
    jotform: JotFormClient = Depends(get_jotform_client),
) -> dict:
    """
    Send or generate onboarding contract link for new customers.
    """
    try:
        return await execute_send_contract(params, jotform)
    except JotFormError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process contract: {str(e)}",
        )
    finally:
        await jotform.close()


@router.get("/contract-status/{submission_id}")
async def get_contract_status(
    submission_id: str,
    jotform: JotFormClient = Depends(get_jotform_client)
) -> dict:
    """
    Check the status of a submitted contract.
    
    Purpose:
    Track whether a customer has completed their onboarding contract.
    Used for follow-up and account activation workflows.
    
    Behavior:
    - Returns submission status (PENDING, COMPLETE, EXPIRED)
    - Includes submission timestamp
    - Shows form answers if completed
    
    AI Usage Guidelines:
    - Use when customer asks about contract status
    - Internal use only - don't expose submission IDs to customers
    - If COMPLETE, inform customer their account is being processed
    - If PENDING, remind customer to complete the form
    
    Args:
        submission_id: JotForm submission ID
        jotform: JotForm client dependency
    
    Returns:
        dict: Submission status and details
    
    Raises:
        HTTPException: If status check fails
    
    Example Response:
        {
            "success": true,
            "data": {
                "submission_id": "123456789",
                "status": "COMPLETE",
                "created_at": "2025-10-22T10:00:00Z",
                "updated_at": "2025-10-22T10:15:00Z"
            }
        }
    """
    try:
        result = await jotform.get_submission_status(submission_id)
        
        return {
            "success": True,
            "data": result
        }
    
    except JotFormError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check contract status: {str(e)}"
        )
    finally:
        await jotform.close()


@router.post("/contract-status", dependencies=[Depends(verify_api_key)])
async def get_contract_status_post(
    params: ContractStatusTool,
    jotform: JotFormClient = Depends(get_jotform_client)
) -> dict:
    """POST variant for Vapi tool integration to check contract status."""
    try:
        result = await jotform.get_submission_status(params.submission_id)
        return {
            "success": True,
            "data": result
        }
    except JotFormError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check contract status: {str(e)}"
        )
    finally:
        await jotform.close()

