# API Tools Documentation

## Customer Management Tools

### 1. Customer Search

**Endpoint:** `POST /tools/customer/search`  
**Tool ID:** `41a59e7eacc6c58f0e215dedfc650935`  
**Fontis API:** `POST /api/v1/customers/search` (GetCustomersByName)

**Purpose:**  
Search for customers by name, address, or account number. Returns multiple matches with contact info, address, and financial summary. Essential for customer identification during calls.

**Why Created:**  
AI needs to identify customers at conversation start using fuzzy search (name/address) since customers rarely know their account number.

---

### 2. Customer Details

**Endpoint:** `POST /tools/customer/details`  
**Tool ID:** `b3846a9ea8aee18743363699e0aaa399`  
**Fontis API:** `POST /api/v1/customers/details` (GetCustomerDetails)

**Purpose:**  
Retrieve detailed customer information when account number is known. Faster than search for direct lookups.

**Why Created:**  
Customers with invoices provide account numbers. Direct lookup avoids fuzzy search overhead and provides immediate account access.

---

### 3. Finance & Delivery Info

**Endpoint:** `POST /tools/customer/finance-info`  
**Tool ID:** `68b967f63fb242cde93fbbc6e77b9752`  
**Fontis API:** `POST /api/v1/customers/{customerId}/finance-info`

**Purpose:**  
Combined snapshot of billing and delivery data. Answers "What do I owe?" and "When is my next delivery?" in single call.

**Why Created:**  
Most common customer questions require both billing and delivery context. Reduces API calls and provides complete account overview.

---

## Billing & Financial Tools

### 4. Account Balance

**Endpoint:** `POST /tools/billing/balance`  
**Tool ID:** `cce52d0c5e5f4faa1b0e9cbc8eb420e0`  
**Fontis API:** `POST /api/v1/customers/{customerId}/balances` (GetCustomerBalances)

**Purpose:**  
Summary-level balance data (total due, past due, on hold). Confirms what's owed without transaction details.

**Why Created:**  
Customers frequently ask "What's my balance?" Quick answer without full invoice history improves call efficiency.

---

### 5. Invoice History

**Endpoint:** `POST /tools/billing/invoice-history`  
**Tool ID:** `aebb0c9d5881f619f77819b48aec5b53`  
**Fontis API:** `POST /api/v1/customers/invoices` (GetCustomerInvoiceAndPaymentHistory)

**Purpose:**  
Complete invoice and payment history with pagination. Shows both invoices and payments in chronological list.

**Why Created:**  
Customers need transaction history for "When was my last payment?" and account reconciliation. Separates invoices from payments programmatically.

---

### 6. Payment Methods

**Endpoint:** `POST /tools/billing/payment-methods`  
**Tool ID:** `f9b9a1ff6729cf4f69d28d188301b32e`  
**Fontis API:** `POST /api/v1/customers/{customerId}/billing-methods`

**Purpose:**  
Retrieve stored payment methods with masked information. Shows autopay status and card expiration.

**Why Created:**  
Customers ask about "What card do you have on file?" Security-conscious design returns only masked data (last 4 digits).

---

### 7. Products Catalog

**Endpoint:** `POST /tools/billing/products`  
**Tool ID:** `2b4ad3fcd9ea0acf476734fc7368524f`  
**Fontis API:** `POST /api/v1/customers/{customerId}/products`

**Purpose:**  
Full product catalog with pricing, categories, and availability. Filtered by customer location.

**Why Created:**  
Customers ask "How much is X?" and "What products are available?" Pricing varies by location; customer-specific catalog ensures accuracy.

---

### 8. Invoice Detail

**Endpoint:** `POST /tools/billing/invoice-detail`  
**Tool ID:** `75ef81ae69cf762ba58d74c48f18d230`  
**Fontis API:** `POST /api/v1/customers/{customerId}/invoices/{invoiceKey}` (GetInvoiceDetail)

**Purpose:**  
Detailed line items for specific invoice. Shows product-level breakdown, quantities, taxes, and totals.

**Why Created:**  
Customers dispute charges or ask "What's on this invoice?" Line-item detail enables AI to explain specific charges.

---

### 9. Add Credit Card

**Endpoint:** `POST /tools/billing/add-credit-card`  
**Fontis API:** `POST /api/v1/customers/{customerId}/credit-cards` (CreditCardVaultAdd)

**Purpose:**  
Vault new credit card for recurring/one-time payments. Sets autopay and primary status.

**Why Created:**  
Customers want to add payment methods during calls. Secure vaulting enables automated billing and customer convenience.

---

## Delivery & Scheduling Tools

### 10. Delivery Stops

**Endpoint:** `POST /tools/delivery/stops`  
**Tool ID:** `a8ff151f77354ae30d328f4042b7ab15`  
**Fontis API:** `POST /api/v1/customers/{customerId}/deliveries`

**Purpose:**  
All delivery locations for customer account. Returns deliveryId required for most operations.

**Why Created:**  
Most customers have one stop; some have multiple. AI needs deliveryId to proceed with delivery-specific queries.

---

### 11. Next Scheduled Delivery

**Endpoint:** `POST /tools/delivery/next-scheduled`  
**Tool ID:** `92e47d19800cfe7724e27d11b0ec4f1a`  
**Fontis API:** `POST /api/v1/deliveries/next` (GetDeliveryDays)

**Purpose:**  
Next upcoming scheduled route delivery. Fast confirmation of "When is my next delivery?"

**Why Created:**  
Single most common customer question. Direct answer without manual route calendar lookup. Explains 20-business-day rotation naturally.

---

### 12. Default Products (Standing Order)

**Endpoint:** `POST /tools/delivery/default-products`  
**Tool ID:** `f24e6d2bc336153c076f0220b45f86b6`  
**Fontis API:** `POST /api/v1/deliveries/{deliveryId}/defaults` (GetDefaultProducts)

**Purpose:**  
Standing order products and quantities. Distinguishes SWAP (exchange empties) from STANDING ORDER (fixed quantities).

**Why Created:**  
Customers ask "What do I normally get?" AI explains delivery model (swap vs standing order) and adjusts expectations.

---

### 13. Off-Route Orders

**Endpoint:** `POST /tools/delivery/orders`  
**Tool ID:** `b4e4f83221662ac8d966ec9e5cc6cfb2`  
**Fontis API:** `POST /api/v1/customers/{customerId}/orders` (GetDeliveryOrders)

**Purpose:**  
Recent off-route/online orders (service tickets). Does NOT include regular route deliveries.

**Why Created:**  
Customers ask "Where's my online order?" Separates special requests from recurring route deliveries. Explains $25 convenience fee.

---

### 14. Delivery Frequencies

**Endpoint:** `GET /tools/delivery/frequencies`  
**Fontis API:** `GET /api/v1/deliveries/frequencies`

**Purpose:**  
Available delivery frequency codes for scheduling operations.

**Why Created:**  
Customers want to change delivery frequency. Provides valid options for rescheduling without manual lookup.

---

### 15. Orders Search

**Endpoint:** `POST /tools/delivery/orders/search`  
**Fontis API:** `POST /api/v1/orders/search`

**Purpose:**  
Search orders by ticket number, customer ID, or delivery ID. Filters by open/closed status.

**Why Created:**  
Customers ask "Where's order #12345?" Flexible search finds specific orders across system.

---

## Route Management Tools

### 16. Route Stops

**Endpoint:** `POST /tools/routes/stops`  
**Tool ID:** `b02a838764b22f83dce17e848fa63884`  
**Fontis API:** `POST /api/v1/routes/stops` (GetRouteStops)

**Purpose:**  
All customer stops for specific route and date. Shows delivery status, skip reasons, and invoice data.

**Why Created:**  
Customers ask "Why wasn't I serviced?" AI explains skip reasons empathetically. Confirms route completion for operational inquiries.

---

## Contract Management Tools

### 17. Customer Contracts

**Endpoint:** `POST /tools/contracts/get-contracts`  
**Tool ID:** `13e223880330066e44c1f2119c0c5aba`  
**Fontis API:** `POST /api/v1/customers/{customerId}/contracts` (GetCustomerContracts)

**Purpose:**  
All active and historical service agreements. Explains contract types (SA: month-to-month, Equipment: 12-month).

**Why Created:**  
Customers ask about contract terms, expiration, and cancellation fees. AI references contract type to explain commitment level.

---

## Onboarding Tools

### 18. Send Onboarding Contract

**Endpoint:** `POST /tools/onboarding/send-contract`  
**External API:** JotForm

**Purpose:**  
Generate and send pre-filled service agreement to prospective customers. Returns contract URL.

**Why Created:**  
Enables AI to onboard new customers during calls. Pre-filled forms reduce friction and improve conversion.

---

### 19. Contract Status

**Endpoint:** `GET /tools/onboarding/contract-status/{submission_id}`  
**External API:** JotForm

**Purpose:**  
Check submission status of onboarding contract (PENDING, COMPLETE, EXPIRED).

**Why Created:**  
Follow-up on pending contracts. AI informs customers about account activation progress.

---

## Design Philosophy

### Why Each Tool Exists:

1. **Customer Questions Drive Tool Design** - Each endpoint answers specific, frequently-asked customer questions
2. **Security & Privacy** - Masked sensitive data (payment methods, internal IDs) at API boundary
3. **Efficiency** - Combined endpoints (finance-info) reduce API calls for common question pairs
4. **Clarity** - Separate concerns (invoices vs payments, route vs off-route) for clear AI reasoning
5. **Operational Insight** - Route stops and skip reasons enable empathetic service recovery

### Tool Selection Strategy:

- **Fast lookup tools** (customer search, next delivery) for immediate answers
- **Detail tools** (invoice detail, default products) for drill-down questions
- **Write tools** (add credit card, send contract) for transactional operations
- **Operational tools** (route stops, contracts) for complex inquiries

All endpoints require API key authentication and return standardized `{success, message, data}` responses for consistent AI parsing.
