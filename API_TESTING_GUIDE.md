# API Testing Guide

Complete guide for testing all 19 Fontis AI Voice Agent APIs with examples, headers, and payloads.

---

## 🔐 Authentication

All **tool endpoints** require authentication using the `Authorization` header:

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Note:** Replace `Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg` with your actual `INTERNAL_API_KEY` from `.env`

---

## 🌐 Base URL

**Local Development:**

```
http://127.0.0.1:8000
```

**Production (Fly.io):**

```
https://your-app.fly.dev
```

---

## 📋 Table of Contents

1. [Core Endpoints](#core-endpoints) (No Auth)
2. [Customer APIs](#customer-apis) (3 endpoints)
3. [Billing APIs](#billing-apis) (6 endpoints)
4. [Delivery APIs](#delivery-apis) (6 endpoints)
5. [Contracts & Routes](#contracts--routes) (2 endpoints)
6. [Onboarding](#onboarding) (2 endpoints)
7. [Testing Tools](#testing-tools)

---

## Core Endpoints

### ✅ Health Check

**No authentication required**

```http
GET /health
```

**PowerShell:**

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/health"
```

**cURL:**

```bash
curl http://127.0.0.1:8000/health
```

**Response:**

```json
{
  "status": "healthy",
  "environment": "development",
  "version": "0.1.0",
  "timestamp": 1729636800
}
```

---

### 📚 API Documentation

**No authentication required**

```http
GET /docs
```

Open in browser: `http://127.0.0.1:8000/docs`

Interactive Swagger UI for testing all endpoints.

---

## Customer APIs

### 1️⃣ Search Customers

Search for customers by name, address, phone, or account number.

**Endpoint:** `POST /tools/customer/search`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "lookup": "Jamie Carroll",
  "offset": 0,
  "take": 25
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    lookup = "Jamie Carroll"
    offset = 0
    take = 25
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/customer/search" `
    -Method Post -Headers $headers -Body $body
```

**cURL:**

```bash
curl -X POST http://127.0.0.1:8000/tools/customer/search \
  -H "Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg" \
  -H "Content-Type: application/json" \
  -d '{"lookup": "Jamie Carroll", "offset": 0, "take": 25}'
```

**Response:**

```json
{
  "success": true,
  "message": "Found 30 customer(s)",
  "data": [
    {
      "customerId": "002864",
      "name": "Jamie Carroll",
      "address": "592 Shannon Dr, MARIETTA, GA, 30066",
      "phone": "770-595-7594",
      "email": "jcarroll@fontiswater.com",
      "totalDue": 0,
      "hasScheduledDeliveries": true
    }
  ],
  "meta": {
    "total": 30,
    "hasMore": true,
    "returned": 25
  }
}
```

---

### 2️⃣ Get Customer Details

Get detailed customer information by account number.

**Endpoint:** `POST /tools/customer/details`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864"
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = '{"customerId": "002864"}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/customer/details" `
    -Method Post -Headers $headers -Body $body
```

**cURL:**

```bash
curl -X POST http://127.0.0.1:8000/tools/customer/details \
  -H "Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg" \
  -H "Content-Type: application/json" \
  -d '{"customerId": "002864"}'
```

---

### 3️⃣ Get Finance & Delivery Info

Get combined financial and delivery information for a customer.

**Endpoint:** `POST /tools/customer/finance-info`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000"
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/customer/finance-info" `
    -Method Post -Headers $headers -Body $body
```

---

## Billing APIs

### 1️⃣ Get Account Balance

Get account balance summary (total due, past due, on hold).

**Endpoint:** `POST /tools/billing/balance`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "includeInactive": false
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = '{"customerId": "002864", "includeInactive": false}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/balance" `
    -Method Post -Headers $headers -Body $body
```

---

### 2️⃣ Get Invoice History

Get invoice and payment history for a delivery stop.

**Endpoint:** `POST /tools/billing/invoice-history`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "deliveryId": "002864000",
  "numberOfMonths": 12,
  "offset": 0,
  "take": 25,
  "descending": true
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
    numberOfMonths = 12
    descending = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/invoice-history" `
    -Method Post -Headers $headers -Body $body
```

---

### 3️⃣ Get Invoice Detail

Get detailed line items for a specific invoice.

**Endpoint:** `POST /tools/billing/invoice-detail`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "invoiceKey": "RT__7AG12BXGH",
  "invoiceDate": "2025-09-30",
  "includeSignature": false,
  "includePayments": false
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    invoiceKey = "RT__7AG12BXGH"
    invoiceDate = "2025-09-30"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/invoice-detail" `
    -Method Post -Headers $headers -Body $body
```

---

### 4️⃣ Get Payment Methods

Get stored payment methods (credit cards, ACH) for a customer.

**Endpoint:** `POST /tools/billing/payment-methods`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "includeInactive": false
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = '{"customerId": "002864"}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/payment-methods" `
    -Method Post -Headers $headers -Body $body
```

---

### 5️⃣ Get Products & Pricing

Get available products and pricing for a customer.

**Endpoint:** `POST /tools/billing/products`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000",
  "postalCode": "30066",
  "internetOnly": true,
  "categories": ["Fontis Bottled Water"],
  "defaultProducts": false,
  "offset": 0,
  "take": 25
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
    postalCode = "30066"
    internetOnly = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/products" `
    -Method Post -Headers $headers -Body $body
```

---

### 6️⃣ Add Credit Card

Add a new credit card to customer's account (vault).

**Endpoint:** `POST /tools/billing/add-credit-card`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "firstName": "Jamie",
  "lastName": "Carroll",
  "cardNumber": "4111111111111111",
  "cardExpiration": "1225",
  "cardCvv": "123",
  "address": "592 Shannon Dr",
  "city": "Marietta",
  "state": "GA",
  "postalCode": "30066",
  "email": "jcarroll@fontiswater.com",
  "setAutopay": false
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    firstName = "Jamie"
    lastName = "Carroll"
    cardNumber = "4111111111111111"
    cardExpiration = "1225"
    cardCvv = "123"
    address = "592 Shannon Dr"
    city = "Marietta"
    state = "GA"
    postalCode = "30066"
    email = "jcarroll@fontiswater.com"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/billing/add-credit-card" `
    -Method Post -Headers $headers -Body $body
```

---

## Delivery APIs

### 1️⃣ Get Delivery Stops

Get all delivery stops/locations for a customer.

**Endpoint:** `POST /tools/delivery/stops`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "offset": 0,
  "take": 25
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = '{"customerId": "002864"}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/stops" `
    -Method Post -Headers $headers -Body $body
```

---

### 2️⃣ Get Next Scheduled Delivery

Get next scheduled delivery date and details.

**Endpoint:** `POST /tools/delivery/next-scheduled`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000",
  "daysAhead": 90
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/next-scheduled" `
    -Method Post -Headers $headers -Body $body
```

---

### 3️⃣ Get Default Products

Get standing order defaults (what products are automatically delivered).

**Endpoint:** `POST /tools/delivery/default-products`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000"
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/default-products" `
    -Method Post -Headers $headers -Body $body
```

---

### 4️⃣ Get Off-Route Orders

Get last off-route delivery orders (service tickets).

**Endpoint:** `POST /tools/delivery/orders`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000",
  "numberOfOrders": 5
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
    numberOfOrders = 5
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/orders" `
    -Method Post -Headers $headers -Body $body
```

---

### 5️⃣ Search Orders

Search orders by ticket number, customer, or delivery ID.

**Endpoint:** `POST /tools/delivery/orders/search`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "ticketNumber": "2510220072",
  "customerId": "002864",
  "deliveryId": "002864000",
  "onlyOpenOrders": true,
  "webProductsOnly": false
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = '{"customerId": "002864", "onlyOpenOrders": true}'

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/orders/search" `
    -Method Post -Headers $headers -Body $body
```

---

### 6️⃣ Get Delivery Frequencies

Get available delivery frequency codes.

**Endpoint:** `GET /tools/delivery/frequencies`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
}

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/delivery/frequencies" `
    -Method Get -Headers $headers
```

**cURL:**

```bash
curl -X GET http://127.0.0.1:8000/tools/delivery/frequencies \
  -H "Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
```

---

## Contracts & Routes

### 1️⃣ Get Customer Contracts

Get service agreements and equipment contracts.

**Endpoint:** `POST /tools/contracts/get-contracts`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerId": "002864",
  "deliveryId": "002864000"
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerId = "002864"
    deliveryId = "002864000"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/contracts/get-contracts" `
    -Method Post -Headers $headers -Body $body
```

---

### 2️⃣ Get Route Stops

Get all stops on a specific route for a specific date.

**Endpoint:** `POST /tools/routes/stops`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "routeDate": "2025-10-22",
  "route": "19",
  "accountNumber": "002864"
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    routeDate = "2025-10-22"
    route = "19"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/routes/stops" `
    -Method Post -Headers $headers -Body $body
```

---

## Onboarding

### 1️⃣ Send Contract

Send JotForm onboarding contract to new customer.

**Endpoint:** `POST /tools/onboarding/send-contract`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
Content-Type: application/json
```

**Body:**

```json
{
  "customerName": "John Doe",
  "email": "john@example.com",
  "phone": "555-1234",
  "address": "123 Main St",
  "city": "Atlanta",
  "state": "GA",
  "postalCode": "30301",
  "deliveryPreference": "Tuesday",
  "sendEmail": true
}
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

$body = @{
    customerName = "John Doe"
    email = "john@example.com"
    phone = "555-1234"
    address = "123 Main St"
    city = "Atlanta"
    state = "GA"
    postalCode = "30301"
    sendEmail = $true
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/onboarding/send-contract" `
    -Method Post -Headers $headers -Body $body
```

---

### 2️⃣ Get Contract Status

Check if a customer has completed their onboarding contract.

**Endpoint:** `GET /tools/onboarding/contract-status/{submission_id}`

**Headers:**

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
```

**PowerShell:**

```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
}

$submissionId = "123456789"

Invoke-RestMethod -Uri "http://127.0.0.1:8000/tools/onboarding/contract-status/$submissionId" `
    -Method Get -Headers $headers
```

---

## Testing Tools

### 🔧 Swagger UI (Recommended)

Interactive API documentation with built-in testing:

1. Open: `http://127.0.0.1:8000/docs`
2. Click the **🔒 Authorize** button (top right)
3. Enter your API key: `Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg`
4. Click **Authorize**
5. Now you can test any endpoint by:
   - Click on the endpoint
   - Click **Try it out**
   - Fill in parameters
   - Click **Execute**

---

### 💻 PowerShell Test Script

Save this as `test-api.ps1`:

```powershell
# API Configuration
$baseUrl = "http://127.0.0.1:8000"
$apiKey = "Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"

$headers = @{
    "Authorization" = "Bearer $apiKey"
    "Content-Type" = "application/json"
}

# Test 1: Health Check
Write-Host "Testing Health Check..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get
Write-Host "✅ Health: $($health.status)" -ForegroundColor Green

# Test 2: Customer Search
Write-Host "`nTesting Customer Search..." -ForegroundColor Cyan
$body = '{"lookup": "Jamie"}'
$customers = Invoke-RestMethod -Uri "$baseUrl/tools/customer/search" `
    -Method Post -Headers $headers -Body $body
Write-Host "✅ Found: $($customers.meta.total) customers" -ForegroundColor Green

# Test 3: Customer Details
Write-Host "`nTesting Customer Details..." -ForegroundColor Cyan
$body = '{"customerId": "002864"}'
$details = Invoke-RestMethod -Uri "$baseUrl/tools/customer/details" `
    -Method Post -Headers $headers -Body $body
Write-Host "✅ Customer: $($details.data.name)" -ForegroundColor Green

# Test 4: Invoice History
Write-Host "`nTesting Invoice History..." -ForegroundColor Cyan
$body = '{"deliveryId": "002864000", "numberOfMonths": 12}'
$invoices = Invoke-RestMethod -Uri "$baseUrl/tools/billing/invoice-history" `
    -Method Post -Headers $headers -Body $body
Write-Host "✅ Invoices: $($invoices.meta.totalInvoices)" -ForegroundColor Green

Write-Host "`n🎉 All tests passed!" -ForegroundColor Green
```

Run: `.\test-api.ps1`

---

### 🐚 Bash Test Script

Save this as `test-api.sh`:

```bash
#!/bin/bash

BASE_URL="http://127.0.0.1:8000"
API_KEY="Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"

echo "Testing Health Check..."
curl -s $BASE_URL/health | jq

echo -e "\nTesting Customer Search..."
curl -s -X POST $BASE_URL/tools/customer/search \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"lookup": "Jamie"}' | jq

echo -e "\nTesting Customer Details..."
curl -s -X POST $BASE_URL/tools/customer/details \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"customerId": "002864"}' | jq

echo -e "\n✅ All tests completed!"
```

Run: `chmod +x test-api.sh && ./test-api.sh`

---

## 🚨 Common Issues

### ❌ 401 Unauthorized

**Problem:** Missing or incorrect API key

**Solution:** Check your `Authorization` header:

```http
Authorization: Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg
```

---

### ❌ 422 Validation Error

**Problem:** Missing required fields or wrong data types

**Solution:** Check the request body matches the expected schema. Use Swagger UI to see required fields.

---

### ❌ 500 Internal Server Error

**Problem:** Server error (check logs)

**Solutions:**

1. Check server logs in terminal
2. Verify `.env` configuration
3. Ensure Fontis API URL is correct: `https://fontisweb.creatordraft.com/api/v1`
4. Verify Fontis API key is valid

---

## 📚 Additional Resources

- **Swagger UI:** `http://127.0.0.1:8000/docs`
- **API Implementation:** See `API_IMPLEMENTATION_COMPLETE.md`
- **Deployment Guide:** See `DEPLOYMENT.md`
- **Client Report:** See `CLIENT_REPORT.md`

---

## 🔑 Environment Variables

Required in `.env`:

```bash
# API Authentication
FONTIS_API_KEY=fk_your_fontis_api_key_here
FONTIS_BASE_URL=https://fontisweb.creatordraft.com/api/v1
INTERNAL_API_KEY=Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg

# Optional: JotForm
JOTFORM_API_KEY=your_jotform_key
JOTFORM_FORM_ID=your_form_id

# Optional: Vapi
VAPI_API_KEY=your_vapi_key
VAPI_PUBLIC_KEY=your_vapi_public_key
```

---

**Happy Testing! 🚀**
