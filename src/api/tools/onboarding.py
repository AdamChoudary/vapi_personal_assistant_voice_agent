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
from src.schemas.tools import SendContractTool
from src.services.jotform_client import JotFormClient
from src.core.exceptions import JotFormError

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


@router.post("/send-contract", dependencies=[Depends(verify_api_key)])
async def send_onboarding_contract(
    params: SendContractTool,
    jotform: JotFormClient = Depends(get_jotform_client)
) -> dict:
    """
    Send or generate onboarding contract link for new customers.
    
    Tool ID: TBD
    Fontis Endpoint: N/A (JotForm integration)
    Method: SendContractViaJotForm
    
    Purpose:
    Generate and optionally send pre-filled service agreement contract to prospective customers.
    Used during new customer onboarding to collect signatures and agreement terms.
    
    Behavior:
    - Generates unique, pre-filled JotForm contract link
    - Optionally emails the link to customer
    - Returns contract URL for reference
    - Link is valid indefinitely until submitted
    
    AI Usage Guidelines:
    - Use when customer expresses interest in signing up for Fontis service
    - Confirm all required information before sending (name, email, address)
    - Always inform customer they'll receive the contract via email
    - Explain next steps: "Complete the agreement form, and we'll set up your account"
    - Do not promise immediate service start (requires contract completion)
    
    Notes:
    - Contract must be completed before account creation in Fontis
    - Follow-up is handled by Fontis operations team
    - Contract includes service terms, pricing, and equipment rental agreements
    
    Args:
        params: Contract generation parameters (name, email, address, etc.)
        jotform: JotForm client dependency
    
    Returns:
        dict: Contains contract URL, form ID, and send status
    
    Raises:
        HTTPException: If contract generation or sending fails
    
    Example Response:
        {
            "success": true,
            "message": "Contract sent successfully",
            "data": {
                "contract_url": "https://form.jotform.com/xxxxx?name=John...",
                "form_id": "xxxxx",
                "email_sent": true,
                "customer_name": "John Doe",
                "email": "john@example.com"
            }
        }
    """
    try:
        # Build additional fields for JotForm
        additional_fields = {}
        if params.delivery_preference:
            additional_fields["deliveryPreference"] = params.delivery_preference
        
        # Decide whether to send email or just generate link
        if params.send_email:
            # Send contract via email
            result = await jotform.send_contract_email(
                customer_name=params.customer_name,
                email=params.email,
                phone=params.phone,
                address=params.address,
                city=params.city,
                state=params.state,
                postal_code=params.postal_code,
                **additional_fields
            )
            
            return {
                "success": True,
                "message": "Contract sent successfully via email",
                "data": {
                    "contract_url": result["form_url"],
                    "form_id": result["form_id"],
                    "email_sent": True,
                    "customer_name": params.customer_name,
                    "email": params.email
                }
            }
        else:
            # Just generate the link without sending email
            result = await jotform.create_contract_link(
                customer_name=params.customer_name,
                email=params.email,
                phone=params.phone,
                address=params.address,
                city=params.city,
                state=params.state,
                postal_code=params.postal_code,
                **additional_fields
            )
            
            return {
                "success": True,
                "message": "Contract link generated successfully",
                "data": {
                    "contract_url": result["url"],
                    "form_id": result["form_id"],
                    "email_sent": False,
                    "customer_name": params.customer_name,
                    "email": params.email
                }
            }
    
    except JotFormError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process contract: {str(e)}"
        )
    finally:
        # Always close the client after use
        await jotform.close()


@router.get("/contract-status/{submission_id}", dependencies=[Depends(verify_api_key)])
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

