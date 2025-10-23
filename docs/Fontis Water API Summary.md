## Fontis Water API Index Summary

A complete reference of all Fontis customer, delivery, billing, and contract endpoints used by the Fontis AI Assistant.

### **Customer Search**  
**ID:** `41a59e7eacc6c58f0e215dedfc650935`  
**Route:** `/api/v1/customers/search`  
**Method:** `GetCustomersByName`
**Purpose:** Search for customers by address, name, account number. Search by phone or email as backup option.  
**Use Case:** First step in every conversation — used to identify the correct customer.  
**Notes:**  
- Always confirm **two identifiers** (address + name + account number).  
- Returns contact info, address, total due, and delivery summary.  
- Does **not** return delivery stop or route info.  


### **Get Customer Details**  
**ID:** `b3846a9ea8aee18743363699e0aaa399`  
**Route:** `/api/v1/customers/details`  
**Method:** `GetCustomerDetails`
**Purpose:** Retrieve a specific customer’s details using their **account number (customerId)**.  
**Use Case:** Used when customer knows their account number — retrieves the same data as Customer Search.  
**Notes:**  
- Use this endpoint **instead of** Customer Search when the account number is known.  
- Returns address, contact info, and balance summary.  


### **Get Customer Delivery Stops**  
**ID:** `a8ff151f77354ae30d328f4042b7ab15`  
**Route:** `/api/v1/customers/deliverystops`  
**Method:** `GetAllDeliveryStops`
**Purpose:** Retrieve all delivery stops (delivery IDs) tied to a customer account.  
**Use Case:** Called after customer verification to obtain the required `deliveryId`.  
**Notes:**  
- **deliveryId** is required for nearly all delivery and invoice endpoints.  
- Most customers have one stop; multiple stops are **edge cases** (campus/multi-building).  
- Includes route, delivery day, and next delivery date.  


### **Customer Finance and Delivery Info**  
**ID:** `68b967f63fb242cde93fbbc6e77b9752`  
**Route:** `/api/v1/customers/financedeliveryinfo`  
**Method:** `GetCustomerFinanceInfo`
**Purpose:** Provide a combined snapshot of billing and delivery data for a specific stop.  
**Use Case:** Used when summarizing a customer’s account — “current balance,” “last payment,” “next delivery,” or “equipment on site.”  
**Notes:**  
- Requires `customerId` and `deliveryId`.  
- Includes last payment date, current balance, and delivery route/day.  


### **Invoices and Payment History**  
**ID:** `aebb0c9d5881f619f77819b48aec5b53`  
**Route:** `/api/v1/customers/invoices`  
**Method:** `GetCustomerInvoiceAndPaymentHistory`
**Purpose:** Retrieve all invoices and payments by delivery stop.  
**Use Case:** Used when a customer asks “What do I owe?” or “When was my last payment?”  
**Notes:**  
- Requires `customerId` and `deliveryId`.  
- Returns both invoices (`isInvoice=true`) and payments (`isPayment=true`).  
- For detailed line items, use **Invoice Detail**.  
- Accounts typically show multiple invoices per month (delivery + equipment).  


### **Invoice Detail**  
**ID:** `75ef81ae69cf762ba58d74c48f18d230`  
**Route:** `/api/v1/customers/invoicedetail`  
**Method:** `GetInvoiceDetail`
**Purpose:** Retrieve detailed invoice line items for a specific invoice.  
**Use Case:** Used when customers ask for a breakdown of what an invoice includes.  
**Notes:**  
- Requires `customerId`, `invoiceKey`, and `invoiceDate`.  
- Do not use with “Payment” invoiceKeys — returns no data.  
- Never offer to email a PDF; refer to Customer Service if requested.  


### **Retrieve Last Off-Route Delivery Orders**  
**ID:** `b4e4f83221662ac8d966ec9e5cc6cfb2`  
**Route:** `/api/v1/customers/lastdeliveryorders`  
**Method:** `GetDeliveryOrders`
**Purpose:** Retrieve off-route deliveries and customer-placed online orders.  
**Use Case:** Used when verifying service requests or online orders outside normal routes.  
**Notes:**  
- These are **service tickets**, not regular route deliveries.  
- Does **not** reflect recurring route deliveries or standing orders.
- Does **not** reflect a customer's complete delivery history.


### **Next Scheduled Delivery**  
**ID:** `92e47d19800cfe7724e27d11b0ec4f1a`  
**Route:** `/api/v1/customers/nextscheduleddelivery`  
**Method:** `GetDeliveryDays`
**Purpose:** Retrieve the next upcoming scheduled delivery for a given stop.  
**Use Case:** Answering “When is my next delivery?”  
**Notes:**  
- Requires `customerId` and `deliveryId`.  
- Returns next delivery date, route code, and ticket info.  


### **Delivery Schedule (Date Range)**  
**ID:** `248fa66e8012d7f62a7ca15199a7e67e`  
**Route:** `/api/v1/customers/deliveryschedule`  
**Method:** `GetDeliveryDays`
**Purpose:** Retrieve upcoming and past scheduled deliveries for a customer over a date range.  
**Use Case:** Used to confirm last or upcoming deliveries.  
**Notes:**  
- Requires `customerId`, `deliveryId`, `from`, and `to` dates.  
- Shows **regular route deliveries only**, not off-route.  


### **Get Delivery Default Products**  
**ID:** `f24e6d2bc336153c076f0220b45f86b6`  
**Route:** `/api/v1/customers/defaultproducts` 
**Method:** `GetDefaultProducts` 
**Purpose:** Retrieve a stop’s standing order defaults (what products and quantities are automatically delivered each time).  
**Use Case:** Used to explain or adjust default deliveries.  
**Notes:**  
- If quantity = 0 → customer is on standard **swap model** (exchange empties for full bottles).  
- If quantity > 0 → **standing order** customer (fixed amount every delivery).  


### **Get Fontis Products and Pricing**  
**ID:** `2b4ad3fcd9ea0acf476734fc7368524f`  
**Route:** `/api/v1/customers/products`  
**Method:** `GetProductListPaginated`
**Purpose:** Retrieve full catalog and pricing available to a customer.  
**Use Case:** Used to answer “How much is a case of water?” or to show web catalog prices.  
**Notes:**  
- Returns only active, available products unless otherwise specified.  
- Supports filters for category, availability, and internet-only products.  


### **Get Customer Contracts and Agreements**  
**ID:** `13e223880330066e44c1f2119c0c5aba`  
**Route:** `/api/v1/customers/contracts`  
**Method:** `GetCustomerContracts`
**Purpose:** Retrieve all active or historical service and equipment agreements for a customer.  
**Use Case:** Used to confirm start/end dates, renewal terms, and cancellation policy.  
**Notes:**  
- All customers have a contract:  
  - Water-only = month-to-month.  
  - Equipment rental = 12-month, auto-renewing with $100 or remaining balance early termination fee.  
- Documents may include signed PDFs (not to be sent by AI).  


### **Get Customer Billing Methods**  
**ID:** `f9b9a1ff6729cf4f69d28d188301b32e`  
**Route:** `/api/v1/customers/billingmethods`  
**Method:** `GetCustomerBilling`
**Purpose:** Retrieve stored payment methods (credit cards, ACH) and autopay status.  
**Use Case:** Used when a customer asks about their payment method or autopay setup.  
**Notes:**  
- Returns masked card/ACH info (e.g., `VISA-3758`).  
- `Primary` = default method; `Autopay` = auto billing enabled.  
- Never display or expose Vault IDs or internal tokens.  


### **Get Account Balances**  
**ID:** `cce52d0c5e5f4faa1b0e9cbc8eb420e0`  
**Route:** `/api/v1/customers/accountbalances`  
**Method:** `GetCustomerBalances`
**Purpose:** Retrieve total due, past due, and on-hold balances for a customer.  
**Use Case:** Used when confirming what’s owed or summarizing account status.  
**Notes:**  
- Data is summary-level (matches top-line “Total Due”).  
- Combine with **Invoices** for detailed transactions.  


### **Get Route Stops**  
**ID:** `b02a838764b22f83dce17e848fa63884`  
**Route:** `/api/v1/routes/stops`  
**Method:** `GetRouteStops`
**Purpose:** Retrieve all customer stops for a specific route and date, including invoice and skip data.  
**Use Case:** Used internally to confirm route completion or skipped deliveries.  
**Notes:**  
- `invoiceTotal > 0` → delivery completed.  
- `skipReason` present → delivery skipped.  
- Most common skip: "No Bottles Out."  
- Requires `routeDate` and `route`.  
- Must filter by `accountNumber` or `deliveryId` to isolate a single customer.  


---

## Endpoints in Development

The following endpoints are currently in development and not yet available for production use.


### **Customer Management**

#### **Create or Update Customer**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreateCustomer`  
**Purpose:** Create a new customer or update an existing customer's contact information.  
**Use Case:** Used for creating new accounts or updating address, phone, email, or contact preferences.  
**Notes:**  
- Pass existing `customerId` to update; omit to create new.  
- Can send welcome email on creation.  
- Includes delivery stop creation options.  
- **Status:** IN DEVELOPMENT  

#### **Get Available Contact Methods**  
**ID:** TBD  
**Route:** TBD  
**Method:** `GetAllContactViaData`  
**Purpose:** Retrieve available contact method options (Phone, Email, SMS).  
**Use Case:** Used to display valid contact preference options when updating customer profiles.  
**Notes:**  
- Returns system-configured contact options.  
- Update ContactVia1-3 fields in CustomerData to change preferences.  
- **Status:** IN DEVELOPMENT  


### **Delivery Management**

#### **Create New Delivery Order**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreateDeliveryLocationWithOrder`  
**Purpose:** Create a delivery order for an existing customer and delivery location.  
**Use Case:** Used when customer wants to place an off-route order or schedule additional delivery.  
**Notes:**  
- Requires existing `customerId` and `deliveryId`.  
- Applies standard pricing and product rules.  
- Returns order confirmation with ticket number.  
- May fail if account is on hold.  
- **Status:** IN DEVELOPMENT  

#### **Get Delivery Order Details**  
**ID:** TBD  
**Route:** TBD  
**Method:** `GetOrder`  
**Purpose:** Retrieve complete delivery order details including all line items, products, and equipment.  
**Use Case:** Used to view full details of a specific delivery order or ticket.  
**Notes:**  
- Returns complete `DeliveryOrderData` structure.  
- Includes product line items and equipment details.  
- Can filter by ticket number, customerId, or deliveryId.  
- Set `onlyOpenOrders=true` to see only unposted orders.  
- **Status:** IN DEVELOPMENT  

#### **Retrieve Delivery Frequency Codes**  
**ID:** TBD  
**Route:** TBD  
**Method:** `GetDeliveryFrequency`  
**Purpose:** Get valid delivery frequency codes for scheduling.  
**Use Case:** Used when customer wants to change delivery frequency or pause service.  
**Notes:**  
- Returns system-configured frequency options.  
- Required for rescheduling operations.  
- **Status:** IN DEVELOPMENT  

#### **Update or Skip Scheduled Delivery**  
**ID:** TBD  
**Route:** TBD  
**Method:** `UpdateExact`  
**Purpose:** Update delivery details or skip a scheduled delivery.  
**Use Case:** Used when customer needs to skip or reschedule a specific delivery.  
**Notes:**  
- Set `skip=true` to skip the delivery.  
- Requires `calendarId`, `routeId`, and `deliveryDate`.  
- Can include note explaining skip reason.  
- **Status:** IN DEVELOPMENT  


### **Payment and Billing**

#### **Add Credit Card Payment Method**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreditCardVaultAdd`  
**Purpose:** Add and vault a new credit card for recurring or one-time payments.  
**Use Case:** Used when customer wants to add a payment method to their account.  
**Notes:**  
- Stores card securely in payment vault.  
- Can set as autopay method during addition.  
- Requires billing address for verification.  
- **Status:** IN DEVELOPMENT  

#### **Charge Credit Card (Vaulted)**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreditCardVaultChargeToDeliveryOrder`  
**Purpose:** Charge a previously vaulted credit card for a delivery order.  
**Use Case:** Used to process payment for a delivery using stored payment method.  
**Notes:**  
- Requires `vaultId` or `vaultPayId`.  
- Can apply coupons and calculate delivery fees.  
- Creates payment record and optionally sends email.  
- **Status:** IN DEVELOPMENT  

#### **Charge Credit Card (One-Time)**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreditCardNonVaultChargeToDeliveryOrder`  
**Purpose:** Process one-time credit card payment without storing card details.  
**Use Case:** Used for one-time payments when customer doesn't want card saved.  
**Notes:**  
- Does not vault the card.  
- Tied to specific delivery order.  
- Creates payment record immediately.  
- **Status:** IN DEVELOPMENT  

#### **Remove Credit Card**  
**ID:** TBD  
**Route:** TBD  
**Method:** `CreditCardVaultRemove`  
**Purpose:** Remove a vaulted credit card from customer account.  
**Use Case:** Used when customer wants to delete a stored payment method.  
**Notes:**  
- Requires `vaultId` and `vaultPayId`.  
- Cannot remove if it's the only autopay method on active contract.  
- **Status:** IN DEVELOPMENT  

#### **Add ACH Payment Method**  
**ID:** TBD  
**Route:** TBD  
**Method:** `ACHVaultAdd`  
**Purpose:** Add and vault a bank account for ACH payments or autopay.  
**Use Case:** Used when customer wants to set up bank account for direct debit.  
**Notes:**  
- Stores bank account securely in vault.  
- Can enable autopay during setup.  
- Requires routing and account numbers.  
- **Status:** IN DEVELOPMENT  

#### **Charge ACH (Vaulted)**  
**ID:** TBD  
**Route:** TBD  
**Method:** `ACHVaultChargeToDeliveryOrder`  
**Purpose:** Charge a previously vaulted ACH account for a delivery order.  
**Use Case:** Used to process ACH payment for delivery using stored bank account.  
**Notes:**  
- Requires vaulted bank account.  
- Can apply coupons and fees.  
- Creates payment record with optional email confirmation.  
- **Status:** IN DEVELOPMENT  

#### **Charge ACH (One-Time)**  
**ID:** TBD  
**Route:** TBD  
**Method:** `ACHChargeToDeliveryOrder`  
**Purpose:** Process one-time ACH payment without storing bank account.  
**Use Case:** Used for one-time ACH payments when customer doesn't want account saved.  
**Notes:**  
- Does not vault bank account.  
- Tied to specific delivery order.  
- Processes immediately.  
- **Status:** IN DEVELOPMENT  

#### **Charge ACH (General - Not Tied to Delivery)**  
**ID:** TBD  
**Route:** TBD  
**Method:** `ACHCharge`  
**Purpose:** Process general ACH charge not associated with a specific delivery.  
**Use Case:** Used for account balance payments or service fees.  
**Notes:**  
- Not tied to delivery order.  
- Can specify custom amount and invoice number.  
- One-time transaction.  
- **Status:** IN DEVELOPMENT  

#### **Remove ACH Payment Method**  
**ID:** TBD  
**Route:** TBD  
**Method:** `ACHVaultRemove`  
**Purpose:** Remove a vaulted ACH account from customer profile.  
**Use Case:** Used when customer wants to delete stored bank account.  
**Notes:**  
- Removes all ACH vault data for customer.  
- Cannot remove if it's the only autopay method on active contract.  
- **Status:** IN DEVELOPMENT  


---

## Summary of Required Field Dependencies
| Task | Required Fields | Core Endpoint |
|------|------------------|----------------|
| Identify Customer | name, phone, address | Customer Search |
| Confirm Account Info | customerId | Customer Details |
| Retrieve Delivery ID | customerId | Get Customer Delivery Stops |
| Get Balance | customerId | Account Balances |
| View Invoices | customerId, deliveryId | Invoices and Payment History |
| View Invoice Detail | customerId, invoiceKey, invoiceDate | Invoice Detail |
| Check Next Delivery | customerId, deliveryId | Next Scheduled Delivery |
| Confirm Route | routeDate, route | Get Route Stops |


## AI Usage Rules Summary
- Always **confirm customer identity** with at least 2 identifiers from service address, name, and account number.  
- Never share internal IDs (VaultId, Document GUIDs, etc.).  
- Default to **single-stop customers** unless multiple stops are confirmed.  
- Use **Next Scheduled Delivery** for future deliveries, **Route Stops** for past delivery verification.  
- Do not offer to email PDFs or documents.  
- Be empathetic with skip reasons — “No Bottles Out” can happen, however, we send reminders before regular route day to prevent this.  
- Summarize clearly; avoid quoting internal codes or raw field names.  