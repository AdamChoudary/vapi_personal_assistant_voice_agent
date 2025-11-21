"""
Tests for customer search endpoint.

Tool ID: 41a59e7eacc6c58f0e215dedfc650935
Endpoint: POST /tools/customer/search
"""

import pytest
from unittest.mock import AsyncMock, patch


class TestCustomerSearch:
    """Test suite for customer search endpoint."""
    
    def test_search_customer_success(self, client, auth_headers, sample_customer_search_response):
        """Test successful customer search."""
        with patch('src.services.fontis_client.FontisClient.search_customers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = sample_customer_search_response
            
            response = client.post(
                "/tools/customer/search",
                json={"lookup": "Jamie"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Found 1 customer(s)" in data["message"]
            assert len(data["data"]) == 1
            
            customer = data["data"][0]
            assert customer["customerId"] == "002864"
            assert customer["name"] == "Jamie Carroll"
            assert "MARIETTA" in customer["address"]
            assert customer["totalDue"] == 0
    
    def test_search_customer_with_pagination(self, client, auth_headers):
        """Test customer search with pagination parameters."""
        with patch('src.services.fontis_client.FontisClient.search_customers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "success": True,
                "message": "Customers found successfully",
                "data": {"data": [], "meta": {"total": 0, "timestamp": "2025-10-22T17:00:00Z"}},
                "meta": {"pagination": {"offset": 10, "take": 25, "orderBy": None, "searchText": "", "descending": False, "total": 0, "hasMore": False}}
            }
            
            response = client.post(
                "/tools/customer/search",
                json={"lookup": "Smith", "offset": 10, "take": 50},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            mock_search.assert_called_once()
            call_args = mock_search.call_args
            assert call_args.kwargs["offset"] == 10
            assert call_args.kwargs["take"] == 50
    
    def test_search_customer_no_results(self, client, auth_headers):
        """Test customer search with no results."""
        with patch('src.services.fontis_client.FontisClient.search_customers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "success": True,
                "message": "No customers found",
                "data": {"data": [], "meta": {"total": 0, "timestamp": "2025-10-22T17:00:00Z"}},
                "meta": {"pagination": {"offset": 0, "take": 25, "orderBy": None, "searchText": "", "descending": False, "total": 0, "hasMore": False}}
            }
            
            response = client.post(
                "/tools/customer/search",
                json={"lookup": "NonexistentCustomer"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is False
            assert "No customers found" in data["message"]
            assert len(data["data"]) == 0
    
    def test_search_customer_unauthorized(self, client):
        """Test customer search without authentication."""
        response = client.post(
                "/tools/customer/search",
            json={"lookup": "Jamie"}
        )
        
        assert response.status_code == 403  # Forbidden - no auth header
    
    def test_search_customer_invalid_api_key(self, client):
        """Test customer search with invalid API key."""
        response = client.post(
            "/tools/customer/search",
            json={"lookup": "Jamie"},
            headers={"Authorization": "Bearer invalid_key"}
        )
        
        assert response.status_code == 401  # Unauthorized
    
    def test_search_customer_missing_lookup(self, client, auth_headers):
        """Test customer search without lookup parameter."""
        response = client.post(
            "/tools/customer/search",
            json={},
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_search_customer_lookup_too_short(self, client, auth_headers):
        """Test customer search with lookup string too short."""
        response = client.post(
            "/tools/customer/search",
            json={"lookup": "A"},  # Only 1 character, min is 2
            headers=auth_headers
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_search_customer_multiple_results(self, client, auth_headers):
        """Test customer search returning multiple results."""
        with patch('src.services.fontis_client.FontisClient.search_customers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "success": True,
                "message": "Customers found successfully",
                "data": {
                    "data": [
                        {
                            "customerId": "001",
                            "name": "John Smith",
                            "address": {"street": "123 Main St", "street2": "", "city": "Atlanta", "state": "GA", "postalCode": "30301", "fullAddress": "123 Main St, Atlanta, GA, 30301"},
                            "contact": {"phoneNumber": "404-555-0001", "emailAddress": "john@example.com"},
                            "financial": {"totalDue": 50.0, "hasScheduledDeliveries": True}
                        },
                        {
                            "customerId": "002",
                            "name": "Jane Smith",
                            "address": {"street": "456 Oak Ave", "street2": "", "city": "Atlanta", "state": "GA", "postalCode": "30302", "fullAddress": "456 Oak Ave, Atlanta, GA, 30302"},
                            "contact": {"phoneNumber": "404-555-0002", "emailAddress": "jane@example.com"},
                            "financial": {"totalDue": 0.0, "hasScheduledDeliveries": False}
                        }
                    ],
                    "meta": {"total": 2, "timestamp": "2025-10-22T17:00:00Z"}
                },
                "meta": {"pagination": {"offset": 0, "take": 25, "orderBy": None, "searchText": "Smith", "descending": False, "total": 2, "hasMore": False}}
            }
            
            response = client.post(
                "/tools/customer/search",
                json={"lookup": "Smith"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["success"] is True
            assert "Found 2 customer(s)" in data["message"]
            assert len(data["data"]) == 2
            assert data["meta"]["total"] == 2
    
    def test_search_customer_api_error(self, client, auth_headers):
        """Test customer search when Fontis API returns error."""
        with patch('src.services.fontis_client.FontisClient.search_customers', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = {
                "success": False,
                "message": "API error occurred"
            }
            
            response = client.post(
                "/tools/customer/search",
                json={"lookup": "Test"},
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert "API error occurred" in data["message"]

