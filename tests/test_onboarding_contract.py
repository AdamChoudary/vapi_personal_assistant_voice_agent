"""Tests for onboarding contract endpoints."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from src.api.tools.onboarding import get_jotform_client
from src.main import app


class DummyJotForm:
    """In-memory stub for JotFormClient used in tests."""

    def __init__(self) -> None:
        self.link_calls: List[Dict[str, Any]] = []
        self.email_calls: List[Dict[str, Any]] = []

    async def create_contract_link(
        self,
        customer_name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        postal_code: str,
        **additional_fields: Any,
    ) -> dict[str, Any]:
        call = {
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "address": address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            "additional_fields": additional_fields,
        }
        self.link_calls.append(call)

        prefill_payload = {
            "customerName": customer_name,
            "email": email,
            "phoneNumber": phone,
            "address": address,
            "city": city,
            "state": state,
            "postalCode": postal_code,
        }

        if "delivery_preference" in additional_fields:
            prefill_payload["deliveryPreference"] = additional_fields["delivery_preference"]
        if "company_name" in additional_fields:
            prefill_payload["companyName"] = additional_fields["company_name"]
        if "products_of_interest" in additional_fields:
            products = additional_fields["products_of_interest"]
            prefill_payload["productsOfInterest"] = "|".join(products)
        if "special_instructions" in additional_fields:
            prefill_payload["specialInstructions"] = additional_fields["special_instructions"]
        if "marketing_opt_in" in additional_fields:
            prefill_payload["marketingOptIn"] = "Yes" if additional_fields["marketing_opt_in"] else "No"

        return {
            "success": True,
            "url": "https://form.jotform.com/1234567890?prefill",
            "form_id": "1234567890",
            "customer_name": customer_name,
            "email": email,
            "prefill": prefill_payload,
        }

    async def send_contract_email(
        self,
        customer_name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        postal_code: str,
        **additional_fields: Any,
    ) -> dict[str, Any]:
        call = {
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "address": address,
            "city": city,
            "state": state,
            "postal_code": postal_code,
            **additional_fields,
        }
        self.email_calls.append(call)

        link_data = await self.create_contract_link(
            customer_name=customer_name,
            email=email,
            phone=phone,
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            **additional_fields,
        )

        return {
            "success": True,
            "message": "Contract email sent successfully",
            "email": email,
            "form_url": link_data["url"],
            "form_id": link_data["form_id"],
            "prefill": link_data["prefill"],
            "email_sent": True,
        }

    async def get_submission_status(self, submission_id: str) -> dict[str, Any]:
        return {
            "success": True,
            "submission_id": submission_id,
            "status": "PENDING",
        }

    async def close(self) -> None:
        return None


@pytest.fixture
def dummy_jotform() -> DummyJotForm:
    """Provide a dummy JotForm client and install dependency override."""
    client = DummyJotForm()
    app.dependency_overrides[get_jotform_client] = lambda: client
    yield client
    app.dependency_overrides.pop(get_jotform_client, None)


def test_send_contract_email_with_additional_fields(client, auth_headers, dummy_jotform: DummyJotForm):
    """Ensure send-contract endpoint passes optional fields and returns prefill metadata."""
    payload = {
        "customerName": "Jamie Carroll",
        "email": "jamie@example.com",
        "phone": "+17705551234",
        "address": "592 Shannon Dr",
        "city": "Marietta",
        "state": "GA",
        "postalCode": "30066",
        "deliveryPreference": "Tuesday",
        "companyName": "Fontis Fans LLC",
        "productsOfInterest": ["5-Gallon Bottles", "Water Dispenser Rental"],
        "specialInstructions": "Leave at back door",
        "marketingOptIn": True,
        "sendEmail": True,
    }

    response = client.post(
        "/tools/onboarding/send-contract",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email_sent"] is True
    assert body["data"]["sms_sent"] is False
    assert body["data"]["sms_error"] == "SMS delivery not attempted."
    assert "contract_url" in body["data"]

    # Ensure the dummy client captured the optional fields
    assert len(dummy_jotform.email_calls) == 1
    call = dummy_jotform.email_calls[0]
    assert call["company_name"] == "Fontis Fans LLC"
    assert call["delivery_preference"] == "Tuesday"
    assert call["products_of_interest"] == ["5-Gallon Bottles", "Water Dispenser Rental"]
    assert call["special_instructions"] == "Leave at back door"
    assert call["marketing_opt_in"] is True

    prefill = body["data"]["prefill"]
    assert prefill["companyName"] == "Fontis Fans LLC"
    assert prefill["deliveryPreference"] == "Tuesday"
    assert prefill["productsOfInterest"] == "5-Gallon Bottles|Water Dispenser Rental"
    assert prefill["marketingOptIn"] == "Yes"


def test_create_contract_link_without_email(client, auth_headers, dummy_jotform: DummyJotForm):
    """Ensure contract link is generated when sendEmail is false."""
    payload = {
        "customerName": "Jamie Carroll",
        "email": "jamie@example.com",
        "phone": "7705551234",
        "address": "592 Shannon Dr",
        "city": "Marietta",
        "state": "GA",
        "postalCode": "30066",
        "sendEmail": False,
        "specialInstructions": "Front office",
        "productsOfInterest": "5-Gallon Bottles, Water Dispenser Rental",
    }

    response = client.post(
        "/tools/onboarding/send-contract",
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email_sent"] is False
    assert body["data"]["sms_sent"] is False
    assert body["data"]["sms_error"] == "SMS delivery not attempted."
    assert body["data"]["prefill"]["specialInstructions"] == "Front office"
    assert body["data"]["prefill"]["productsOfInterest"] == "5-Gallon Bottles|Water Dispenser Rental"

    # Ensure only link was generated, no email invitation
    assert len(dummy_jotform.email_calls) == 0
    assert len(dummy_jotform.link_calls) == 1

