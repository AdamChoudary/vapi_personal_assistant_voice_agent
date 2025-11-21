"""
HTTP client for JotForm API integration.

This module provides a client for JotForm's contract generation capabilities,
enabling:
- Pre-filled contract submission generation
- Customer onboarding form links
- Contract status tracking

Design decisions:
- Similar structure to FontisClient and VapiClient for consistency
- Error handling with custom JotFormError exception
- Async operations for non-blocking I/O
- Supports email notifications and pre-filled data
"""

from typing import Any
from urllib.parse import urlencode

import httpx

from src.config import settings
from src.core.exceptions import ErrorCode, JotFormError

DEFAULT_PREFILL_MAP: dict[str, str] = {
    "customer_name": "customerName",
    "email": "email",
    "phone": "phoneNumber",
    "address": "address",
    "city": "city",
    "state": "state",
    "postal_code": "postalCode",
    "delivery_preference": "deliveryPreference",
    "company_name": "companyName",
    "products_of_interest": "productsOfInterest",
    "special_instructions": "specialInstructions",
    "marketing_opt_in": "marketingOptIn",
}


class JotFormClient:
    """
    Async HTTP client for JotForm API.
    
    Provides methods for:
    - Generating pre-filled contract submission links
    - Sending contracts via email
    - Tracking submission status
    
    Usage:
        client = JotFormClient()
        try:
            link = await client.create_contract_submission(
                customer_name="John Doe",
                email="john@example.com",
                address="123 Main St",
                phone="+12345678900"
            )
        finally:
            await client.close()
    
    Configuration:
        Requires JOTFORM_API_KEY and JOTFORM_FORM_ID environment variables
    """
    
    def __init__(self):
        """
        Initialize JotForm API client.
        
        Raises:
            JotFormError: If API key or form ID is not configured
        """
        self.base_url = settings.jotform_base_url
        self.api_key = settings.jotform_api_key
        self.form_id = settings.jotform_form_id
        self.prefill_map = {**DEFAULT_PREFILL_MAP, **settings.jotform_prefill_map}
        
        # Validate configuration
        if not self.api_key:
            raise JotFormError(
                "JotForm API key not configured - set JOTFORM_API_KEY environment variable",
                error_code=ErrorCode.JOTFORM_NOT_CONFIGURED
            )
        
        if not self.form_id:
            raise JotFormError(
                "JotForm form ID not configured - set JOTFORM_FORM_ID environment variable",
                error_code=ErrorCode.JOTFORM_NOT_CONFIGURED
            )
        
        # Create async client with API key authentication
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            params={"apiKey": self.api_key},
            timeout=30.0
        )
    
    async def create_contract_link(
        self,
        customer_name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        postal_code: str,
        **additional_fields: Any
    ) -> dict[str, Any]:
        """
        Generate a pre-filled JotForm contract submission link.
        
        Use cases:
        - New customer onboarding
        - Contract renewal
        - Service agreement updates
        
        Args:
            customer_name: Full customer name
            email: Customer email address
            phone: Phone number (E.164 format recommended)
            address: Street address
            city: City name
            state: State/Province code
            postal_code: ZIP/Postal code
            **additional_fields: Any additional form fields to pre-fill
        
        Returns:
            Dictionary containing:
            - url: Pre-filled form URL
            - form_id: JotForm form ID
            - expires_at: Link expiration (if applicable)
        
        Raises:
            JotFormError: If link generation fails
        
        Example:
            result = await client.create_contract_link(
                customer_name="Jamie Carroll",
                email="jcarroll@fontiswater.com",
                phone="770-595-7594",
                address="592 Shannon Dr",
                city="Marietta",
                state="GA",
                postal_code="30066",
                delivery_preference="Tuesday"
            )
            # Returns: {
            #   "url": "https://form.jotform.com/xxxxx?name=Jamie...",
            #   "form_id": "xxxxx"
            # }
        
        Notes:
            - Link is unique per customer
            - Pre-filled data reduces customer friction
            - Customer can modify pre-filled data before submitting
        """
        try:
            prefill_payload = self._build_prefill_payload(
                customer_name=customer_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                **additional_fields,
            )
            
            form_url = f"https://form.jotform.com/{self.form_id}"
            query_params = urlencode(prefill_payload, doseq=True, safe="|,:")
            prefilled_url = f"{form_url}?{query_params}"
            
            return {
                "success": True,
                "url": prefilled_url,
                "form_id": self.form_id,
                "customer_name": customer_name,
                "email": email,
                "prefill": prefill_payload,
            }
            
        except Exception as e:
            raise JotFormError(
                f"Failed to create JotForm contract link: {str(e)}",
                error_code=ErrorCode.JOTFORM_GENERATION_FAILED
            )
    
    async def send_contract_email(
        self,
        customer_name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        postal_code: str,
        **additional_fields: Any
    ) -> dict[str, Any]:
        """
        Send a contract form link via email directly from JotForm.
        
        Use cases:
        - Automated onboarding emails
        - Follow-up contract requests
        - Bulk contract distribution
        
        Args:
            customer_name: Full customer name
            email: Customer email address
            phone: Phone number
            address: Street address
            city: City name
            state: State/Province code
            postal_code: ZIP/Postal code
            **additional_fields: Additional form fields to pre-fill
        
        Returns:
            Dictionary containing:
            - success: True if email sent
            - submission_id: Unique submission identifier
            - email: Recipient email
        
        Raises:
            JotFormError: If email sending fails
        
        Example:
            result = await client.send_contract_email(
                customer_name="Jamie Carroll",
                email="jcarroll@fontiswater.com",
                phone="770-595-7594",
                address="592 Shannon Dr",
                city="Marietta",
                state="GA",
                postal_code="30066"
            )
        
        Notes:
            - JotForm sends email with form link
            - Email is tracked in JotForm dashboard
            - Can customize email template in JotForm settings
        """
        try:
            # First, create the pre-filled link
            link_data = await self.create_contract_link(
                customer_name=customer_name,
                email=email,
                phone=phone,
                address=address,
                city=city,
                state=state,
                postal_code=postal_code,
                **additional_fields
            )
            
            # JotForm API endpoint for sending forms
            # Note: This uses JotForm's email invitation feature
            email_sent = False
            try:
                response = await self.client.post(
                    f"/form/{self.form_id}/invitations",
                    data={
                        "email": email,
                        "name": customer_name,
                        "message": f"Hello {customer_name}, please complete your Fontis Water service agreement.",
                        "prefill": link_data["url"],
                    },
                )
                response.raise_for_status()
                result = response.json()
                email_sent = True
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 404:
                    # JotForm standard plans do not support email invitations; fall back to link-only flow.
                    return {
                        "success": True,
                        "message": "Contract link generated (JotForm email invitations unavailable for this account).",
                        "email": email,
                        "form_url": link_data["url"],
                        "form_id": self.form_id,
                        "prefill": link_data.get("prefill", {}),
                        "email_sent": False,
                    }
                raise
            
            return {
                "success": True,
                "message": "Contract email sent successfully",
                "email": email,
                "form_url": link_data["url"],
                "form_id": self.form_id,
                "prefill": link_data.get("prefill", {}),
                "email_sent": email_sent,
            }
            
        except httpx.HTTPError as e:
            raise JotFormError(
                f"Failed to send contract email: {str(e)}",
                error_code=ErrorCode.JOTFORM_EMAIL_FAILED
            )
    
    async def get_submission_status(self, submission_id: str) -> dict[str, Any]:
        """
        Check the status of a contract submission.
        
        Use cases:
        - Verify contract completion
        - Track pending contracts
        - Follow up on incomplete submissions
        
        Args:
            submission_id: JotForm submission ID
        
        Returns:
            Dictionary containing:
            - status: "PENDING", "COMPLETE", or "EXPIRED"
            - created_at: Submission creation timestamp
            - answers: Form field responses (if complete)
        
        Raises:
            JotFormError: If status check fails
        
        Example:
            status = await client.get_submission_status("123456789")
            if status["status"] == "COMPLETE":
                print("Contract signed!")
        """
        try:
            response = await self.client.get(f"/submission/{submission_id}")
            response.raise_for_status()
            data = response.json()
            
            # Extract relevant data from JotForm response
            content = data.get("content", {})
            
            return {
                "success": True,
                "submission_id": submission_id,
                "status": content.get("status", "UNKNOWN"),
                "created_at": content.get("created_at"),
                "updated_at": content.get("updated_at"),
                "answers": content.get("answers", {})
            }
            
        except httpx.HTTPError as e:
            raise JotFormError(
                f"Failed to get submission status: {str(e)}",
                error_code=ErrorCode.JOTFORM_STATUS_CHECK_FAILED
            )
    
    async def close(self) -> None:
        """
        Close the HTTP client and release resources.
        
        Should be called when the client is no longer needed.
        """
        await self.client.aclose()

    def _build_prefill_payload(self, **fields: Any) -> dict[str, str]:
        """
        Map canonical onboarding fields to the configured JotForm parameter keys.
        """
        payload: dict[str, str] = {}
        for canonical_key, value in fields.items():
            serialized = self._serialize_prefill_value(value)
            if serialized is None:
                continue
            mapped_key = self.prefill_map.get(canonical_key, canonical_key)
            payload[mapped_key] = serialized
        return payload

    @staticmethod
    def _serialize_prefill_value(value: Any) -> str | None:
        """Normalize values for URL encoding."""
        if value is None:
            return None
        if isinstance(value, bool):
            return "Yes" if value else "No"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, (list, tuple, set)):
            cleaned = [str(item).strip() for item in value if str(item).strip()]
            return "|".join(cleaned) if cleaned else None
        if isinstance(value, dict):
            return None
        text = str(value).strip()
        return text or None

