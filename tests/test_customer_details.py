"""
Tests for customer details endpoint.

Tool ID: b3846a9ea8aee18743363699e0aaa399
Endpoint: POST /tools/customer/details
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestCustomerDetails:
    """Test suite for customer details endpoint."""
    
    def test_get_customer_details_success(self, client, auth_headers, sample_customer_details_response):
        """Test successful customer details retrieval."""
        with patch('src.services.fontis_client.FontisClient.get_customer_details', new_callable=AsyncMock) as mock_details:
            mock_details.return_value = sample_customer_details_response
            
            response = client.post(
                "/tools/customer/details",
                json={"customerId": "002864"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "successfully" in data["message"]
            
            customer = data["data"]
            assert customer["customerId"] == "002864"
            assert customer["name"] == "Jamie Carroll"
            assert customer["phone"] == "770-595-7594"
            assert customer["totalDue"] == 0
    
    def test_get_customer_details_not_found(self, client, auth_headers):
        """Test customer details when customer not found."""
        with patch('src.services.fontis_client.FontisClient.get_customer_details', new_callable=AsyncMock) as mock_details:
            mock_details.return_value = {
                "success": False,
                "message": "Customer not found"
            }
            
            response = client.post(
                "/tools/customer/details",
                json={"customerId": "999999"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "not found" in data["message"]
    
    def test_get_customer_details_unauthorized(self, client):
        """Test customer details without authentication."""
        response = client.post(
            "/tools/customer/details",
            json={"customerId": "002864"}
        )
        
        assert response.status_code == 403  # Forbidden
    
    def test_get_customer_details_missing_customer_id(self, client, auth_headers):
        """Test customer details without customer ID."""
        response = client.post(
            "/tools/customer/details",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_get_customer_details_with_address_breakdown(self, client, auth_headers, sample_customer_details_response):
        """Test that address details are properly formatted."""
        with patch('src.services.fontis_client.FontisClient.get_customer_details', new_callable=AsyncMock) as mock_details:
            mock_details.return_value = sample_customer_details_response
            
            response = client.post(
                "/tools/customer/details",
                json={"customerId": "002864"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "addressDetails" in data["data"]
            addr = data["data"]["addressDetails"]
            assert addr["street"] == "592 Shannon Dr"
            assert addr["city"] == "MARIETTA"
            assert addr["state"] == "GA"
            assert addr["postalCode"] == "30066"

