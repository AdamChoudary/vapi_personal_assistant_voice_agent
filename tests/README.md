# Test Suite - Fontis AI Voice Agent

Professional test suite for the Fontis AI Voice Agent API.

## Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run all tests (environment variables auto-configured)
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_customer_search.py

# Run tests matching pattern
pytest -k "search"

# Run with coverage report
pytest --cov=src --cov-report=html
```

**Latest Test Results**: ✅ **21/21 tests passing** (1.08s)

## Environment Configuration

Test environment variables are automatically set in `conftest.py`:

- No manual environment setup required
- Tests run in isolated environment
- Mock Fontis API responses (no real API calls)

## Test Structure

```
tests/
├── __init__.py               # Test package init
├── conftest.py               # Shared fixtures and configuration
├── test_customer_search.py   # Customer search endpoint tests
├── test_customer_details.py  # Customer details endpoint tests
└── test_invoice_history.py   # Invoice history endpoint tests
```

## Test Coverage

### Customer Search (test_customer_search.py) - 10 tests

- ✅ Successful search with results
- ✅ Search with pagination parameters
- ✅ Search with no results
- ✅ Authentication failure (no header)
- ✅ Invalid API key handling
- ✅ Missing lookup parameter
- ✅ Lookup string too short (<2 chars)
- ✅ Multiple results handling
- ✅ API error response handling

### Customer Details (test_customer_details.py) - 5 tests

- ✅ Successful details retrieval
- ✅ Customer not found
- ✅ Authentication failure (no header)
- ✅ Missing customer ID parameter
- ✅ Address details formatting

### Invoice History (test_invoice_history.py) - 6 tests

- ✅ Successful history retrieval
- ✅ Custom parameters (months, pagination)
- ✅ Invoice/payment separation logic
- ✅ Authentication failure (no header)
- ✅ Missing delivery ID parameter
- ✅ Pagination metadata inclusion
- ✅ API error response handling

## Test Fixtures

Defined in `conftest.py`:

- `client`: FastAPI test client
- `auth_headers`: Authentication headers
- `sample_customer_search_response`: Sample search response
- `sample_customer_details_response`: Sample details response
- `sample_invoice_history_response`: Sample invoice response

## Writing New Tests

Follow this pattern:

```python
def test_feature_name(self, client, auth_headers):
    """Test description."""
    with patch('src.services.fontis_client.FontisClient.method_name', new_callable=AsyncMock) as mock:
        mock.return_value = {expected_response}

        response = client.post(
            "/endpoint/path",
            json={params},
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

## CI/CD Integration

Add to your CI pipeline:

```yaml
- name: Run tests
  run: |
    pip install pytest pytest-asyncio httpx-mock
    pytest --cov=src --cov-report=xml
```

## Notes

- All tests use mocked Fontis API calls (no real API calls)
- Tests focus on endpoint behavior and error handling
- Integration tests would require test API credentials
- Tests run quickly (<1 second per test)
