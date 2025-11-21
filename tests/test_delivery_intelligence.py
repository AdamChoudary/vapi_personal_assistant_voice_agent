"""Tests for delivery intelligence endpoints."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_delivery_summary_success(client, auth_headers):
    """Summary endpoint aggregates finance, route, and defaults."""
    with (
        patch("src.services.fontis_client.FontisClient.get_delivery_stops", new_callable=AsyncMock) as mock_stops,
        patch("src.services.fontis_client.FontisClient.get_customer_finance_info", new_callable=AsyncMock) as mock_finance,
        patch("src.services.fontis_client.FontisClient.get_next_scheduled_delivery", new_callable=AsyncMock) as mock_next,
        patch("src.services.fontis_client.FontisClient.get_default_products", new_callable=AsyncMock) as mock_defaults,
    ):
        mock_stops.return_value = {
            "success": True,
            "data": {"deliveryStops": [{"deliveryId": "DELIV-1"}]},
        }
        mock_finance.return_value = {
            "success": True,
            "data": {
                "customerInfo": {
                    "currentBalance": 25.0,
                    "formattedCurrentBalance": "$25.00",
                    "pastDue": 10.0,
                    "formattedPastDue": "$10.00",
                    "hasPastDue": True,
                    "lastPayment": {"amount": 40, "date": "2025-10-01"},
                },
                "deliveryInfo": {
                    "deliveryId": "DELIV-1",
                    "deliveryName": "Main Office",
                    "routeCode": "19",
                    "routeDay": "Tuesday",
                    "schedulingArea": "North Metro",
                    "nextDeliveryDate": "2025-11-15",
                    "routeDriver": "Alex Driver",
                    "csr": "Jamie Rep",
                    "equipment": [{"type": "Cooler", "quantity": 1}],
                    "alertMessage": "Leave bottles by back door",
                },
            },
        }
        mock_next.return_value = {"success": True, "data": {"deliveryDate": "2025-11-20"}}
        mock_defaults.return_value = {
            "success": True,
            "data": [
                {"productCode": "WATER-5G", "productDescription": "5 Gallon Bottled Water", "quantity": 3, "unitPrice": 7.5}
            ],
            "meta": {"totalProducts": 1},
        }

        response = client.post(
            "/tools/delivery/summary",
            json={"customerId": "002864"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["driver"]["name"] == "Alex Driver"
    assert payload["data"]["standingOrder"]["items"][0]["code"] == "WATER-5G"
    assert payload["meta"]["nextDeliverySource"] == "nextScheduledDelivery"


@pytest.mark.asyncio
async def test_delivery_schedule_summary_counts(client, auth_headers):
    """Schedule endpoint summarises completed, skipped, and upcoming stops."""
    today = date.today()
    entries = [
        {"deliveryDate": today.isoformat(), "status": "Completed", "invoiceTotal": 45},
        {"deliveryDate": (today - timedelta(days=2)).isoformat(), "skipReason": "No Bottles Out"},
        {"deliveryDate": (today + timedelta(days=7)).isoformat(), "status": "Scheduled"},
    ]

    with (
        patch("src.services.fontis_client.FontisClient.get_delivery_stops", new_callable=AsyncMock) as mock_stops,
        patch("src.services.fontis_client.FontisClient.get_delivery_schedule", new_callable=AsyncMock) as mock_schedule,
    ):
        mock_stops.return_value = {"success": True, "data": {"deliveryStops": [{"deliveryId": "DELIV-1"}]}}
        mock_schedule.return_value = entries

        response = client.post(
            "/tools/delivery/schedule",
            json={"customerId": "002864"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["summary"]["completed"] == 1
    assert payload["summary"]["skipped"] == 1
    assert payload["summary"]["upcoming"] >= 1


@pytest.mark.asyncio
async def test_work_order_status_open_detection(client, auth_headers):
    """Work order endpoint splits open vs closed orders."""
    orders = [
        {"ticketNumber": "123", "status": "Open", "posted": False},
        {"ticketNumber": "124", "status": "Completed", "posted": True, "invoiceTotal": 30},
    ]

    with (
        patch("src.services.fontis_client.FontisClient.get_delivery_stops", new_callable=AsyncMock) as mock_stops,
        patch("src.services.fontis_client.FontisClient.get_last_delivery_orders", new_callable=AsyncMock) as mock_orders,
    ):
        mock_stops.return_value = {"success": True, "data": {"deliveryStops": [{"deliveryId": "DELIV-1"}]}}
        mock_orders.return_value = {"success": True, "data": orders}

        response = client.post(
            "/tools/delivery/work-orders",
            json={"customerId": "002864"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["open"] == 1
    assert payload["summary"]["closed"] == 1


@pytest.mark.asyncio
async def test_pricing_breakdown_totals(client, auth_headers):
    """Pricing breakdown computes subtotal using standing order pricing."""
    with (
        patch("src.services.fontis_client.FontisClient.get_delivery_stops", new_callable=AsyncMock) as mock_stops,
        patch("src.services.fontis_client.FontisClient.get_default_products", new_callable=AsyncMock) as mock_defaults,
        patch("src.services.fontis_client.FontisClient.get_products", new_callable=AsyncMock) as mock_products,
    ):
        mock_stops.return_value = {"success": True, "data": {"deliveryStops": [{"deliveryId": "DELIV-1"}]}}
        mock_defaults.return_value = {
            "success": True,
            "data": [
                {"productCode": "WATER-5G", "productDescription": "5 Gallon Bottled Water", "quantity": 2, "unitPrice": 7.5},
                {"productCode": "CUPS", "productDescription": "Cup Sleeve", "quantity": 1, "unitPrice": None},
            ],
        }
        mock_products.return_value = {
            "success": True,
            "data": {
                "records": [
                    {"code": "WATER-5G", "defaultPrice": 7.5, "description": "5 Gallon Bottled Water"},
                    {"code": "CUPS", "defaultPrice": 5.0, "description": "Cup Sleeve"},
                ]
            },
        }

        response = client.post(
            "/tools/delivery/pricing-breakdown",
            json={"customerId": "002864", "postalCode": "30066"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["subtotal"] == pytest.approx(20.0)
    assert len(payload["data"]["standingOrder"]) == 2


@pytest.mark.asyncio
async def test_order_change_status_detects_open(client, auth_headers):
    """Order change confirmation reports open tickets."""
    orders = [
        {"ticketNumber": "123", "status": "Open", "posted": False},
        {"ticketNumber": "124", "status": "Completed", "posted": True},
    ]

    with (
        patch("src.services.fontis_client.FontisClient.get_delivery_stops", new_callable=AsyncMock) as mock_stops,
        patch("src.services.fontis_client.FontisClient.search_orders", new_callable=AsyncMock) as mock_search,
    ):
        mock_stops.return_value = {"success": True, "data": {"deliveryStops": [{"deliveryId": "DELIV-1"}]}}
        mock_search.return_value = {"success": True, "data": orders}

        response = client.post(
            "/tools/delivery/order-change-status",
            json={"customerId": "002864"},
            headers=auth_headers,
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["open"] == 1
    assert payload["data"][0]["ticketNumber"] == "123"

