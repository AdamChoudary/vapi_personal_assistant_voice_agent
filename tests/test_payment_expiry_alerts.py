"""Tests for payment expiry alerts endpoint."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_payment_expiry_alerts_categories(client, auth_headers):
    """Expired and expiring soon methods are detected correctly."""
    today = date.today()
    expired_month = (today - timedelta(days=40)).strftime("%m%y")
    soon_month = (today + timedelta(days=15)).strftime("%m%y")
    active_month = (today + timedelta(days=120)).strftime("%m%y")

    methods = [
        {"Description": "VISA-1111", "CardExpiration": expired_month, "Autopay": True, "Primary": True},
        {"Description": "MC-2222", "CardExpiration": soon_month, "Autopay": False, "Primary": False},
        {"Description": "ACH-3333", "CardExpiration": active_month, "Autopay": False, "Primary": False},
        {"Description": "VENMO", "Autopay": False, "Primary": False},  # No expiration
    ]

    with patch("src.services.fontis_client.FontisClient.get_billing_methods", new_callable=AsyncMock) as mock_methods:
        mock_methods.return_value = {"success": True, "data": methods}

        response = client.post(
            "/tools/billing/payment-expiry-alerts",
            json={"customerId": "002864", "daysThreshold": 30},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    summary = payload["summary"]
    assert summary["expired"] == 1
    assert summary["expiringSoon"] == 1
    assert summary["active"] == 1
    assert summary["unknown"] == 1

    statuses = [item["status"] for item in payload["data"]]
    assert "expired" in statuses
    assert "expiring_soon" in statuses
    assert "active" in statuses
    assert "no_expiration" in statuses


@pytest.mark.asyncio
async def test_payment_expiry_alerts_handles_empty_methods(client, auth_headers):
    """Gracefully handle no payment methods."""
    with patch("src.services.fontis_client.FontisClient.get_billing_methods", new_callable=AsyncMock) as mock_methods:
        mock_methods.return_value = {"success": True, "data": []}

        response = client.post(
            "/tools/billing/payment-expiry-alerts",
            json={"customerId": "002864"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 0
    assert "No payment methods were found" in payload["message"]

