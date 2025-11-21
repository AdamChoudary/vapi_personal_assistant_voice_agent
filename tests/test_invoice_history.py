"""
Tests for invoice history endpoint.

Tool ID: aebb0c9d5881f619f77819b48aec5b53
Endpoint: POST /tools/billing/invoice-history
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestInvoiceHistory:
    """Test suite for invoice history endpoint."""
    
    def test_get_invoice_history_success(self, client, auth_headers, sample_invoice_history_response):
        """Test successful invoice history retrieval."""
        with patch('src.services.fontis_client.FontisClient.get_invoice_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = sample_invoice_history_response
            
            response = client.post(
                "/tools/billing/invoice-history",
                json={"deliveryId": "002864000"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Retrieved 1 records" in data["message"]
            assert "invoices" in data["data"]
            assert "payments" in data["data"]
            assert data["data"]["totalInvoices"] == 1
            assert data["data"]["totalPayments"] == 0
    
    def test_get_invoice_history_with_parameters(self, client, auth_headers, sample_invoice_history_response):
        """Test invoice history with custom parameters."""
        with patch('src.services.fontis_client.FontisClient.get_invoice_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = sample_invoice_history_response
            
            response = client.post(
                "/tools/billing/invoice-history",
                json={
                    "deliveryId": "002864000",
                    "numberOfMonths": 6,
                    "offset": 0,
                    "take": 50,
                    "descending": True
                },
                headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_history.assert_called_once()
            call_args = mock_history.call_args
            assert call_args.kwargs["number_of_months"] == 6
            assert call_args.kwargs["take"] == 50
    
    def test_get_invoice_history_separates_invoices_and_payments(self, client, auth_headers):
        """Test that invoices and payments are properly separated."""
        with patch('src.services.fontis_client.FontisClient.get_invoice_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = {
                "success": True,
                "message": "Success",
                "data": {
                    "data": [
                        {
                            "paginationId": "INV001",
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
                        },
                        {
                            "paginationId": "PAY001",
                            "type": 1,
                            "invoiceNumber": "PMT-001",
                            "invoiceKey": "PMT__001",
                            "date": "2025-10-01T00:00:00-04:00",
                            "amount": 45.50,
                            "tax": 0,
                            "customerId": "002864",
                            "deliveryName": "Jamie Carroll",
                            "deliveryId": "002864000",
                            "viewPdf": False,
                            "posted": True,
                            "formattedAmount": "$45.50",
                            "isPayment": True,
                            "isInvoice": False
                        }
                    ],
                    "meta": {"total": 2, "timestamp": "2025-10-22T17:00:00Z"}
                },
                "meta": {"pagination": {"offset": 0, "take": 25, "orderBy": None, "searchText": "", "descending": True, "total": 2, "hasMore": False}}
            }
            
            response = client.post(
                "/tools/billing/invoice-history",
                json={"deliveryId": "002864000"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["data"]["totalInvoices"] == 1
            assert data["data"]["totalPayments"] == 1
            assert len(data["data"]["invoices"]) == 1
            assert len(data["data"]["payments"]) == 1
    
    def test_get_invoice_history_unauthorized(self, client):
        """Test invoice history without authentication."""
        response = client.post(
            "/tools/billing/invoice-history",
            json={"deliveryId": "002864000"}
        )
        
        assert response.status_code == 403  # Forbidden
    
    def test_get_invoice_history_missing_delivery_id(self, client, auth_headers):
        """Test invoice history without delivery ID."""
        response = client.post(
            "/tools/billing/invoice-history",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_invoice_history_pagination_metadata(self, client, auth_headers, sample_invoice_history_response):
        """Test that pagination metadata is included."""
        with patch('src.services.fontis_client.FontisClient.get_invoice_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = sample_invoice_history_response
            
            response = client.post(
                "/tools/billing/invoice-history",
                json={"deliveryId": "002864000"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "meta" in data
            assert "total" in data["meta"]
            assert "hasMore" in data["meta"]
            assert "returned" in data["meta"]
    
    def test_get_invoice_history_api_error(self, client, auth_headers):
        """Test invoice history when Fontis API returns error."""
        with patch('src.services.fontis_client.FontisClient.get_invoice_history', new_callable=AsyncMock) as mock_history:
            mock_history.return_value = {
                "success": False,
                "message": "Failed to retrieve invoice history"
            }
            
            response = client.post(
                "/tools/billing/invoice-history",
                json={"deliveryId": "002864000"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "Failed to retrieve" in data["message"]

