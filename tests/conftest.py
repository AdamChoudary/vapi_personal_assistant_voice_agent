"""
Pytest configuration and fixtures for test suite.
"""

import os
import pytest

# Set test environment variables before importing the app
os.environ["INTERNAL_API_KEY"] = "test_api_key_for_testing_with_32_characters_minimum"
os.environ["FONTIS_API_KEY"] = "fk_test_fontis_key_32chars_minimum_for_tests"
os.environ["FONTIS_API_URL"] = "https://api.fontiswater.com"
os.environ["VAPI_PUBLIC_KEY"] = "test_vapi_key"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient
from src.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for protected endpoints."""
    return {"Authorization": "Bearer test_api_key_for_testing_with_32_characters_minimum"}


@pytest.fixture
def sample_customer_search_response():
    """Sample customer search response from Fontis API."""
    return {
        "success": True,
        "message": "Customers found successfully",
        "data": {
            "data": [
                {
                    "customerId": "002864",
                    "name": "Jamie Carroll",
                    "address": {
                        "street": "592 Shannon Dr",
                        "street2": "",
                        "city": "MARIETTA",
                        "state": "GA",
                        "postalCode": "30066",
                        "fullAddress": "592 Shannon Dr, MARIETTA, GA, 30066"
                    },
                    "contact": {
                        "phoneNumber": "770-595-7594",
                        "emailAddress": "jcarroll@fontiswater.com"
                    },
                    "financial": {
                        "totalDue": 0,
                        "hasScheduledDeliveries": False
                    }
                }
            ],
            "meta": {
                "total": 1,
                "timestamp": "2025-10-22T16:59:41.089086Z"
            }
        },
        "meta": {
            "pagination": {
                "offset": 0,
                "take": 25,
                "orderBy": None,
                "searchText": "Jamie",
                "descending": False,
                "total": 1,
                "hasMore": False
            }
        }
    }


@pytest.fixture
def sample_customer_details_response():
    """Sample customer details response from Fontis API."""
    return {
        "success": True,
        "message": "Customer details retrieved successfully",
        "data": {
            "customerId": "002864",
            "name": "Jamie Carroll",
            "address": {
                "street": "592 Shannon Dr",
                "street2": "",
                "city": "MARIETTA",
                "state": "GA",
                "postalCode": "30066",
                "fullAddress": "592 Shannon Dr, MARIETTA, GA, 30066"
            },
            "contact": {
                "phoneNumber": "770-595-7594",
                "emailAddress": "jcarroll@fontiswater.com"
            },
            "financial": {
                "totalDue": 0,
                "hasScheduledDeliveries": False
            }
        }
    }


@pytest.fixture
def sample_invoice_history_response():
    """Sample invoice history response from Fontis API."""
    return {
        "success": True,
        "message": "Invoice history retrieved successfully",
        "data": {
            "data": [
                {
                    "paginationId": "IRT__7AG12BXGH",
                    "type": 0,
                    "invoiceNumber": "2061604",
                    "invoiceKey": "RT__7AG12BXGH",
                    "date": "2025-09-30T00:00:00-04:00",
                    "amount": 45.50,
                    "tax": 2.50,
                    "customerId": "002864",
                    "deliveryName": "Jamie Carroll",
                    "deliveryId": "002864000",
                    "viewPdf": True,
                    "posted": True,
                    "formattedAmount": "$45.50",
                    "isPayment": False,
                    "isInvoice": True
                }
            ],
            "meta": {
                "total": 1,
                "timestamp": "2025-10-22T17:00:00.000000Z"
            }
        },
        "meta": {
            "pagination": {
                "offset": 0,
                "take": 25,
                "orderBy": None,
                "searchText": "",
                "descending": True,
                "total": 1,
                "hasMore": False
            }
        }
    }

