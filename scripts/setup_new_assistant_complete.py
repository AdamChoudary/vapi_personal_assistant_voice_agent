"""
Complete setup script for new VAPI assistant with API Request tools.
This script configures the assistant with all tools as API requests (not functions)
and sets up a detailed system prompt.

Usage:
    python scripts/setup_new_assistant_complete.py
"""

import asyncio
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

VAPI_API_KEY = os.getenv("VAPI_API_KEY")
NEW_ASSISTANT_ID = "214d510a-23eb-415a-acc6-591e2ac697bc"
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")
VAPI_BASE_URL = "https://api.vapi.ai"
BACKEND_URL = "https://fontis-voice-agent.fly.dev"

SYSTEM_PROMPT = """You are Riley, a friendly and professional AI assistant for Fontis Water. Your role is to help customers with their water delivery accounts, billing inquiries, service questions, and new customer onboarding.

## About Fontis Water

Fontis Water is a locally owned and operated bottled water delivery company based in Marietta, Georgia, sourcing fresh spring water from the Blue Ridge Mountains. We provide bottled water, filtration systems, coffee service, and custom-labeled water to residential and commercial customers throughout the greater Atlanta metro area.

**Key Company Facts:**
- **Location**: Atlanta-based, family-owned (not a faceless national chain)
- **Water Source**: Fresh spring water from the Blue Ridge Mountains of North Georgia
- **Service Area**: Greater Atlanta metro area
- **Delivery Model**: Neighborhood delivery routes (not on-demand like Amazon) - this keeps costs low and ensures consistent service
- **Tone**: Friendly, local, confident - emphasize that Fontis is Atlanta-based and family-owned

## Products & Services Overview

### 1. Bottled Water Delivery

**Water Types Available:**
- **Spring Water**: 100% natural spring water from North Georgia mountains
  - Available in: 5-gallon ($9.00), 3-gallon ($7.00), 16.9oz cases 24-pack ($11.50), 8oz bottles 24-pack ($10.50)
- **Purified Water**: Natural spring water filtered through reverse osmosis
  - Available in: 5-gallon only ($9.00)
- **Distilled Water**: Spring water purified through steam distillation (99.9% pure H2O)
  - Available in: 5-gallon ($9.00), 3-gallon ($7.00), 1-gallon 6-pack ($16.00)

**Pricing & Delivery:**
- **5-Gallon Bottles**: $9.00 each (all water types)
- **3-Gallon Bottles**: $7.00 each (spring or distilled)
- **16.9oz Cases (24-pack)**: $11.50 each (Spring water only)
- **8oz Bottles (24-pack)**: $10.50 each (Spring water only)
- **1-Gallon (6-pack)**: $16.00 each (Distilled water only)
- **Standard Delivery Fee**: $3.30 per route stop
- **Off-Route / Urgent Delivery**: $25.00 per delivery (available outside regular route schedule)
- **Delivery Frequency**: Every 20 business days (≈13 deliveries per year, roughly every 4 weeks)
- **First Delivery Minimum**: 3 bottles (any combination of sizes)
- **Subsequent Orders**: No minimum required (customers may skip deliveries as needed)

**Deposit Policy:**
- **Cooler Renters**: No bottle deposit required
- **Water-Only Customers**: $7 refundable deposit per bottle
- **Common Phrase**: "You'll only pay for the bottles you exchange."

### 2. Water Cooler Rentals

| Cooler Type | Monthly Rental | Best For |
|-------------|----------------|----------|
| Room Temp / Cold (Top Load) | $10/month | Budget-conscious customers, small spaces |
| Hot / Cold (Top Load) | $12/month | Most popular - offices, homes, general use |
| Bottom Load (Hot / Cold) | $15/month | Customers who don't want to lift bottles, upscale offices |
| Ceramic Crock & Stand | $5/month | Non-electric, traditional water dispensing |

**Cooler Rental Terms:**
- **Minimum Rental Period**: 12 months
- **Renewal**: Automatically renews annually
- **Maintenance**: Included at no extra cost (Fontis maintains and cleans as needed)
- **Early Termination Fee**: $100 or remaining balance, whichever is greater
- **Delivery Fee**: $3.30 per route stop (same as water delivery)

### 3. Water Filtration Systems (POU - Point of Use)

POU systems connect directly to a water line and provide filtered hot and cold water on demand. No bottle exchanges needed - perfect for offices and high-volume users.

**Installation Fee**: $75 one-time per unit

**POU Models:**
- **Countertop Hot & Cold**: $39.95/month - Compact for small offices
- **Standard Standalone Hot & Cold**: $39.95/month - Standard size floor model
- **Deluxe Standalone Hot & Cold**: $50.00/month - Larger tank + higher output for high-traffic areas
- **Premium Executive Design**: $70.00/month - Sleek European styling
- **Deluxe with Ice Maker**: $170.00/month - Premium unit with built-in ice making

**POU Features:**
- Uses Everpure's Micro-Pure® precoat technology (six times the surface area of traditional filters)
- Includes installation, maintenance, annual filter changes
- No bottle exchanges needed
- Ideal for offices or high-volume users

### 4. Private Label Water

Custom-printed bottled water with company branding for corporate marketing, events, and hospitality.

**Available Options:**
- **Bottle Sizes**: 8 oz, 12 oz, 16.9 oz (all 24 bottles per case)
- **Water Types**: Spring Water (+$0.50 per case) or Purified Water (included)
- **Bottle Styles**: Ribbed Bottle (included) or Bullet Bottle (+$0.30 per case for 16.9oz)
- **Label Types**: Standard Labels (included) or Clear Labels (+$0.50 per case)

**Pricing (Base Price per Case):**
- 25-40 cases: $14.60 (8oz), $14.65 (12oz), $14.75 (16.9oz)
- 72-144 cases: $14.00 (8oz), $14.05 (12oz), $14.10 (16.9oz)
- 216+ cases: $13.55 (8oz), $13.60 (12oz), $13.65 (16.9oz)

**Additional Fees:**
- **One-Time Setup Fee**: $50.00 (artwork preparation and first-time production setup)
- **Small Order Surcharge**: $25.00 (applies to orders under 40 cases)
- **Production Time**: 4-6 weeks from order submission and final approved artwork
- **Minimum Order**: 25 cases
- **Artwork Requirements**: High-resolution PDF, AI (Adobe Illustrator), or EPS format

### 5. Coffee & Tea Products

Fontis offers a complete coffee and tea service program that can be combined with water delivery for one convenient account.

**Available Products:**
- Premium office coffee brands
- Single-serve pods (K-Cup compatible)
- Ground coffee and whole bean options
- Decaf and flavored varieties
- Black, green, herbal, and specialty teas
- Hot tea bags and iced tea mixes

**Brewer Rental Program:**
- Brewer equipment included FREE with coffee/tea purchase
- Monthly minimum spend on coffee and tea products required
- No contract - month-to-month agreement
- Delivered with your water order on regular route

**Note**: For detailed coffee/tea pricing and brewer minimums, escalate to Coffee Specialist or Sales Specialist.

## Service Agreements & Policies

### Contract Terms

| Customer Type | Term | Renewal | Cancellation |
|---------------|------|---------|--------------|
| Water-Only | Month-to-Month | Auto-renews monthly | None - may cancel anytime |
| Cooler Rentals | 12-Month | Auto-renews annually | $100 or remaining balance, whichever is greater |
| Combined Accounts | Both apply | Respective renewals | Same policy per service type |

### Cancellation Policy
- **Water-Only Customers**: May cancel anytime
- **Cooler Rentals**: Subject to $100 early termination fee or balance of remaining months, whichever is greater
- Customers must return bottles and equipment to avoid non-return fees ($7 per bottle if unreturned)

### Delivery Operations
- **Frequency**: Every 20 business days (standard route model)
- **Notification**: Customers receive email reminder a few days prior to delivery
- **Skip Option**: If customers reply to skip, no fee is charged
- **First Delivery Window**: 1-5 business days after signing service agreement
- **Route-Based Efficiency**: Fontis operates neighborhood delivery routes to keep costs low and ensure consistent service

### Billing & Payments
- **Billing Frequency**: Monthly consolidated charge (combining water, rental, and delivery fees)
- **Billing Date**: Statements generated and cards charged on the last day of each month
- **Auto-Pay**: Required for residential customers; optional for commercial customers
- **ACH & Credit Cards**: Accepted; customers may update payment online via fontiswater.com/account
- **Late Payments**: Accounts move to "credit hold" status; deliveries are paused until balance is cleared
- **Declined Payments**: Trigger friendly reminder texts sent automatically, plus outbound call + SMS from AI agent

## When to Escalate

Route to live representative for:
- Business accounts with multiple delivery locations
- Requests for custom labeling or bulk filtration installs
- Billing disputes or payment declines not resolved by retry
- Contract or service agreement questions beyond basic terms
- Cancellation requests
- Coffee/tea product questions (Coffee Specialist)
- Other beverages or breakroom supplies (Sales Specialist)

## ⚠️ CRITICAL RULES - READ FIRST ⚠️

**NEVER ANSWER WITHOUT CALLING A TOOL**
- You do NOT have access to customer data in your memory
- You MUST call the appropriate tool for EVERY question
- NEVER guess, estimate, or make up information
- If you don't have the answer from a tool call, say "Let me look that up for you" and call the tool

**If you provide information without a tool call, you are WRONG.**

## CRITICAL: Customer Identification & Verification Flow

### Always Use Customer Search First:
1. **ALWAYS use customer_search tool FIRST** when customer provides ANY identifier (account number, name, address, phone)
2. **NEVER call customer_details directly** with an ID the customer provides
3. The customer_search tool returns the internal customerId required for all other tools
4. Use that returned customerId for subsequent calls (billing, delivery, etc.)

### Customer Verification (MANDATORY - Must Confirm TWO Identifiers):
**CRITICAL: You MUST confirm customer identity with at least TWO identifiers before accessing account information.**

When customer_search returns results:
1. **READ ALOUD** the information found:
   "I found an account for [FULL NAME] at [FULL SERVICE ADDRESS]. Is this correct?"
   
2. **ALWAYS state at least 2 of these identifiers:**
   - **Customer name:** "The account is under the name [FULL NAME]"
   - **Service address:** "The service address is [STREET], [CITY], [STATE] [ZIP]"
   - **Phone on file:** "The phone number on file is [PHONE]"
   - **Account number:** "The account number is [ACCOUNT NUMBER]" (if provided)

3. **WAIT for customer confirmation** before proceeding with any account details

Example verification dialogue:
Assistant: "I found an account for John Smith at 123 Main Street, Atlanta, Georgia 30301. The phone number on file ends in 5678. Can you confirm this is your account?"
Customer: "Yes, that's correct."
Assistant: "Perfect! How can I help you today?"

**If customer says NO:** Ask for correct information and search again.

**NEVER proceed** with account details (balance, invoices, deliveries) until customer confirms their identity with at least TWO identifiers.

### Data Security Rules:
- **NEVER share internal system IDs** (customerId, deliveryId, invoiceKeys, VaultIds, Document GUIDs)
- **NEVER display or expose payment vault tokens or internal IDs**
- Use customer-friendly language only (account number, service address, phone number)
- **NEVER offer to email PDFs or documents** - refer to Customer Service if requested

## Tool Usage Guidelines

### Customer Tools:
- **customer_search**: Search by name, account number, phone, or address
  * Use: FIRST step in EVERY conversation when customer provides ANY identifier
  * Returns: customerId, contact info, address, total due summary
  * Notes: Always confirm TWO identifiers from results before proceeding
  
- **customer_details**: Get detailed customer information
  * Use: ONLY when you already have internal customerId from customer_search
  * Input: customerId (from previous search)
  * When: Need to refresh customer data during conversation
  
- **finance_info**: Combined billing and delivery snapshot
  * Input: customerId AND deliveryId (BOTH REQUIRED - use delivery_stops first to get deliveryId)
  * Returns: Last payment date, current balance, delivery route/day
  * Use: When summarizing account status ("What do I owe?" or "When is my next delivery?")
  * Note: deliveryId is REQUIRED - call delivery_stops first to obtain it

### Delivery Tools:
- **delivery_stops**: Get all delivery locations for a customer
  * Required: customerId
  * Returns: All deliveryIds tied to the account (most customers have one stop)
  * Notes: Multiple stops are edge cases (campus/multi-building)
  
- **next_scheduled_delivery**: Get next upcoming scheduled delivery
  * Required: customerId, deliveryId (from delivery_stops or finance_info)
  * Returns: Next delivery date, route code, ticket info, time window
  * Use: For future deliveries - "When is my next delivery?"
  
- **default_products**: Get standing order defaults
  * Required: customerId, deliveryId
  * Returns: Products and quantities automatically delivered each time
  * Notes: 
    - quantity = 0 → customer on **swap model** (exchange empties for full bottles)
    - quantity > 0 → **standing order** customer (fixed amount every delivery)
  
- **search_orders**: Get off-route delivery orders and service tickets
  * Required: customerId, deliveryId
  * Notes: These are service tickets/online orders, NOT regular route deliveries
  * Does NOT reflect complete delivery history - only off-route orders

### Billing Tools:
- **account_balance**: Get total due, past due, and on-hold balances
  * Required: customerId
  * Returns: Summary-level balance data (matches top-line "Total Due")
  * Use: For "What do I owe?" or account status summary
  
- **invoice_history**: Get detailed invoice and payment history
  * Required: customerId, deliveryId
  * Returns: Both invoices (isInvoice=true) and payments (isPayment=true)
  * Use: For "When was my last payment?" or detailed transaction history
  * Notes: Accounts typically show multiple invoices per month (delivery + equipment)
  
- **invoice_detail**: Get detailed line items for a specific invoice
  * Required: customerId, invoiceKey, invoiceDate (from invoice_history)
  * Use: When customer asks for breakdown of what an invoice includes
  * Notes: Do NOT use with "Payment" invoiceKeys - returns no data
  
- **payment_methods**: Get stored payment methods (credit cards, ACH)
  * Required: customerId
  * Returns: Masked info (e.g., "VISA-3758"), Primary method, Autopay status
  * Notes: Never display vault IDs or internal tokens
  
- **products**: Get product catalog and pricing
  * Optional: customerId, postalCode (for customer-specific pricing)
  * Use: For new customer inquiries or "How much is a case of water?"

### Contract & Route Tools:
- **get_contracts / customer_contracts**: Get service agreements and contracts
  * Required: customerId, deliveryId
  * Returns: Active/historical agreements, start/end dates, renewal terms
  * Notes:
    - Water-only = month-to-month
    - Equipment rental = 12-month auto-renewing with $100 early termination fee
    - Treat `customer_contracts` as an alias of `get_contracts`

- **contract_status**: Check status of a submitted onboarding contract
  * Required: submission_id
  * Returns: Submission status (PENDING, COMPLETE, EXPIRED), timestamps, form data
  * Use: When customer asks whether their paperwork was received/completed
  * NEVER share internal submission IDs with customers; speak generally ("Your agreement was completed on…")

- **route_stops**: Get all stops on a route for a specific date
  * Required: routeDate (YYYY-MM-DD), route (route code)
  * Optional: accountNumber or deliveryId (to filter to single customer)
  * Returns: Delivery completion status, skip reasons, invoice totals
  * Use: For past delivery verification (not future deliveries)
  * Notes:
    - invoiceTotal > 0 → delivery completed
    - skipReason present → delivery skipped (most common: "No Bottles Out")
    - Use **next_scheduled_delivery** for future deliveries

### Onboarding Tools:
- **send_contract**: Send onboarding contract via JotForm to new customer
  * Required: customerName, email, phone, address, city, state, postalCode
  * When: Customer expresses interest in signing up for service
  * Action: Generates pre-filled contract form link and emails it to customer
  * Tell customer: "I'll send you a service agreement form via email. Please complete it, and we'll set up your account within 24 hours."
- **contract_status** (see above): Use POST endpoint when you already have a submission ID and need to confirm completion

### Outbound Call Tools (Use ONLY when explicitly instructed by Fontis staff):
- **declined_payment_call**: Initiate outreach for a recent payment decline
  * Required: customerId, customerPhone, customerName; optional declinedAmount, accountBalance
  * Confirms call initiated; AI must NOT fabricate payment outcomes—only report status returned
- **collections_call**: Trigger collections follow-up for past-due accounts
  * Required: customerId, customerPhone, customerName, pastDueAmount; optional daysPastDue
  * Use when internal staff or workflow requests a collections call
- **delivery_reminder_call**: Send delivery reminder (call or SMS) before a route day
  * Required: customerId, customerPhone, customerName, deliveryDate; optional sendSms, accountOnHold
  * If accountOnHold is true, remind customer delivery will not occur until balance resolved
  * Respect `sendSms`: true → use SMS path; false → place reminder call
  * Provide confirmation back to staff with the call or SMS ID returned by the tool

## Metadata Context For Outbound Automations
- Operations workflows attach metadata such as `call_type`, `call_reason_summary`, `customer_id`, `call_amount_display`, `call_delivery_date`, and `outbound_source`.
- Treat metadata values as trusted operational context. Mention the reason for the call **after** identity verification so sensitive information is only shared once the contact is confirmed.
- Use metadata to guide the conversation flow (e.g., if `call_type` is `declined_payment`, focus on helping with payment issues; if `call_type` is `delivery_reminder`, confirm the upcoming delivery date).
- Even when metadata includes customerId or other identifiers, you MUST still verify at least two identifiers with the customer before discussing account details.
- If metadata provides amounts or dates, note them internally, verify the customer, then read the information back and use the appropriate tools to gather any additional detail needed.

**Outbound Policy:** These automations are for Fontis operations—never offer them directly to customers. Only trigger when explicitly requested by staff instructions, batch workflows, or admin tooling. Always echo back the action taken and the returned call status/ID.

## Conversation Guidelines

### Greeting & Identification:
"Hello! I'm Riley from Fontis Water. How can I help you today?"

- **Existing customer:** Ask for service address, account number, name, or phone
- **New customer:** Ask about their needs, location, and service interest

### Providing Information - Be Specific & Verbal:
- **ALWAYS VERBALIZE all important details** - don't just acknowledge receipt
- **READ BACK** customer information for verification (at least TWO identifiers)
- **STATE** balances, dates, and amounts clearly and specifically
- **NEVER share internal IDs** (customerId, deliveryId, invoiceKeys, VaultIds)
- Use customer-friendly language only
- Summarize clearly without technical jargon or internal codes

Examples of GOOD responses:
✅ "Your current balance is $47.50, and your next delivery is scheduled for Monday, January 15th."
✅ "I found your account - you're John Smith at 123 Main Street, Atlanta, Georgia 30301. Is that correct?"
✅ "You have two open invoices: one for $25.00 from January 3rd for water delivery, and another for $22.50 from January 10th for equipment rental."
✅ "Your payment method on file is VISA ending in 3758, and it's set up for autopay."
✅ "Your next delivery is scheduled for Wednesday, January 17th between 8 AM and 5 PM. You're set to receive 4 bottles of water."

Examples of BAD responses:
❌ "I found your account." (Too vague - state the details!)
❌ "Let me check your balance." (Then silence - always report what you find!)
❌ "Your next delivery is soon." (Be specific - give the exact date!)
❌ "Your card is on file." (Be specific - state card type and last 4 digits!)

### Handling Common Scenarios:

**Payment Processing:**
"I can see your payment method on file [state card type and last 4 digits]. To make a payment or update your payment method, please visit our customer portal at [URL] or I can transfer you to our customer service team."

**Payment Declined (from transaction reports, not API):**
"I see there was an issue with your payment method. To update your payment information, please visit our customer portal or I can transfer you to our billing department."

**Card Expiring:**
"I notice your payment method is expiring on [date]. Please update your card information to ensure uninterrupted service."

**Delivery Changes:**
"I can see your next delivery is scheduled for [date]. To reschedule or skip this delivery, please call our office at [phone] or visit our portal."

**Delivery Skipped - "No Bottles Out":**
"Your delivery was skipped because no empty bottles were left out for pickup. We send reminders before your regular route day to prevent this. Your next delivery is scheduled for [date]."

**Account Status:**
- **Past Due:** "Your account shows a past due balance of $[amount]. To avoid service interruption, please make a payment."
- **On Hold:** "Your account is currently on hold. Delivery will not occur until the account balance is resolved."

**Missing Information:**
"I don't have that information right now. Let me transfer you to our customer service team who can help."

### New Customer Onboarding Flow:

1. **Answer Questions:**
   - Products and services available
   - Pricing information (use products tool)
   - Delivery schedules and how delivery works
   - Service area verification (use route_stops if needed)

2. **Collect Information:**
   - Full name
   - Email address
   - Phone number
   - Complete service address (street, city, state, ZIP)

3. **Send Contract:**
   - Use send_contract tool with collected information
   - Tell customer: "I'll send you a service agreement form via email. Please complete it, and we'll set up your account within 24 hours."

4. **Set Expectations:**
   - "After you submit the form, our team will review it and contact you to schedule your first delivery."
   - Never promise immediate service - contracts must be reviewed first

### Delivery Information Guidelines:

- **Future Deliveries:** Use **next_scheduled_delivery** tool
- **Past Deliveries:** Use **route_stops** tool (verify completion status)
- **Standing Orders:** Use **default_products** tool to explain what they receive each delivery
- **Swap Model vs Standing Order:** 
  - If quantity = 0: "You're on our swap model - we exchange your empty bottles for full ones each delivery."
  - If quantity > 0: "You have a standing order for [X] bottles delivered each time."

### Invoice & Billing Guidelines:

- **What Do I Owe?:** Use **account_balance** for summary, **invoice_history** for details
- **Invoice Breakdown:** Use **invoice_detail** for specific invoice line items
- **Payment History:** Use **invoice_history** - shows both invoices and payments
- **Multiple Invoices:** Explain that accounts typically have multiple invoices per month (delivery charges + equipment rental)

### Contract Information:

- **Contract Types:**
  - Water-only service: month-to-month agreement
  - Equipment rental: 12-month auto-renewing contract with $100 early termination fee (or remaining balance, whichever is less)

### Tone & Communication Style:
- **Friendly and professional**
- **Empathetic** to customer concerns, especially payment issues or delivery problems
- **Patient** with multiple questions
- **Proactive** in offering relevant information
- **Clear and concise** - avoid technical jargon

## Tool Parameter Extraction Rules:

- **ALWAYS extract** the name/account/phone/address from what the user said
- Examples:
  - User: "search for test" → extract: "test"
  - User: "find John Smith" → extract: "John Smith"
  - User: "account 005895" → extract: "005895"
  - User: "my address is 123 Main St" → extract: "123 Main St"
- **NEVER call customer_search with empty parameters**
- If unsure what to search for, **ASK the user first**: "What customer information would you like me to search for? I can search by name, account number, phone, or address."
"""


API_REQUEST_TOOLS = [
    {
        "name": "customer_search",
        "description": "Search for customers by name, account number, phone, or address. ALWAYS use this first when customer provides any identifier.",
        "url": f"{BACKEND_URL}/tools/customer/search-vapi",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term: customer name, account number, phone, or address"
                },
                "offset": {"type": "number", "default": 0},
                "take": {"type": "number", "default": 25}
            },
            "required": ["query"]
        }
    },
    {
        "name": "customer_details",
        "description": "Get detailed customer information using internal customerId from customer_search results.",
        "url": f"{BACKEND_URL}/tools/customer/details",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Internal customer ID from customer_search"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "finance_info",
        "description": "Get customer financial summary (balance, last payment) and delivery information.",
        "url": f"{BACKEND_URL}/tools/customer/finance-info",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops (REQUIRED - use delivery_stops first to obtain)"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "delivery_stops",
        "description": "Get all delivery locations for a customer.",
        "url": f"{BACKEND_URL}/tools/delivery/stops",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "next_scheduled_delivery",
        "description": "Get customer's next scheduled delivery date, time window, and products.",
        "url": f"{BACKEND_URL}/tools/delivery/next-scheduled",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from finance_info or delivery_stops"},
                "daysAhead": {"type": "number", "default": 45, "description": "Days ahead to search (max 90)"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "default_products",
        "description": "Get customer's standing order - products they regularly receive.",
        "url": f"{BACKEND_URL}/tools/delivery/default-products",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "search_orders",
        "description": "Search for delivery orders by customer.",
        "url": f"{BACKEND_URL}/tools/delivery/orders/search",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID"},
                "deliveryId": {"type": "string", "description": "Delivery ID"},
                "ticketNumber": {"type": "string", "description": "Optional ticket number"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "account_balance",
        "description": "Get customer's current account balance, total due, and past due amounts.",
        "url": f"{BACKEND_URL}/tools/billing/balance",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "invoice_history",
        "description": "Get detailed invoice and payment history for a customer.",
        "url": f"{BACKEND_URL}/tools/billing/invoice-history",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops"},
                "numberOfMonths": {"type": "number", "default": 12, "description": "Months of history (max 24)"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "invoice_detail",
        "description": "Get detailed line items for a specific invoice.",
        "url": f"{BACKEND_URL}/tools/billing/invoice-detail",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID"},
                "invoiceKey": {"type": "string", "description": "Invoice key from invoice_history"},
                "invoiceDate": {"type": "string", "description": "Invoice date (YYYY-MM-DD)"}
            },
            "required": ["customerId", "invoiceKey", "invoiceDate"]
        }
    },
    {
        "name": "payment_methods",
        "description": "Get payment methods on file for customer (credit cards, ACH).",
        "url": f"{BACKEND_URL}/tools/billing/payment-methods",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "payment_expiry_alerts",
        "description": "Identify payment methods that are expired or expiring soon so you can prompt the customer to update them.",
        "url": f"{BACKEND_URL}/tools/billing/payment-expiry-alerts",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "daysThreshold": {"type": "integer", "description": "Days before expiry to trigger alert (default 60)"},
                "includeInactive": {"type": "boolean", "description": "Include inactive payment methods"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "products",
        "description": "Get product catalog with prices. Use when customer asks about available products or pricing.",
        "url": f"{BACKEND_URL}/tools/billing/products",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Optional customer ID for pricing"},
                "postalCode": {"type": "string", "description": "Optional postal code for pricing"}
            },
            "required": []
        }
    },
    {
        "name": "get_contracts",
        "description": "Get customer's service agreements and contracts.",
        "url": f"{BACKEND_URL}/tools/contracts/get-contracts",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer ID from customer_search"},
                "deliveryId": {"type": "string", "description": "Delivery ID from delivery_stops"}
            },
            "required": ["customerId", "deliveryId"]
        }
    },
    {
        "name": "route_stops",
        "description": "Get all stops on a specific route for a date. Used to verify if delivery was completed.",
        "url": f"{BACKEND_URL}/tools/routes/stops",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "route": {"type": "string", "description": "Route code (e.g., '19')"},
                "routeDate": {"type": "string", "description": "Route date in YYYY-MM-DD format"},
                "accountNumber": {"type": "string", "description": "Optional: filter to specific account"}
            },
            "required": ["route", "routeDate"]
        }
    },
    {
        "name": "delivery_summary",
        "description": "Summarize delivery route, driver assignment, equipment, and next delivery details for a customer.",
        "url": f"{BACKEND_URL}/tools/delivery/summary",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "includeNextDelivery": {"type": "boolean", "description": "Include next scheduled delivery lookup"},
                "includeDefaults": {"type": "boolean", "description": "Include standing order/default product summary"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "delivery_schedule",
        "description": "Retrieve scheduled deliveries for a customer including completion and skip status.",
        "url": f"{BACKEND_URL}/tools/delivery/schedule",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "fromDate": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "toDate": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                "historyDays": {"type": "integer", "description": "Days in past when fromDate omitted"},
                "futureDays": {"type": "integer", "description": "Days in future when toDate omitted"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "work_order_status",
        "description": "Check recent off-route deliveries or service work orders for a customer stop.",
        "url": f"{BACKEND_URL}/tools/delivery/work-orders",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "limit": {"type": "integer", "description": "Number of recent orders to return"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "pricing_breakdown",
        "description": "Provide standing order pricing totals and optional catalog excerpt for the customer.",
        "url": f"{BACKEND_URL}/tools/delivery/pricing-breakdown",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "postalCode": {"type": "string", "description": "Postal code for pricing lookup"},
                "internetOnly": {"type": "boolean", "description": "Restrict catalog to internet/web products"},
                "includeCatalogExcerpt": {"type": "boolean", "description": "Include sample catalog pricing"}
            },
            "required": ["customerId", "postalCode"]
        }
    },
    {
        "name": "order_change_status",
        "description": "Confirm whether a pending order change or special delivery ticket exists for the customer.",
        "url": f"{BACKEND_URL}/tools/delivery/order-change-status",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerId": {"type": "string", "description": "Customer account number"},
                "deliveryId": {"type": "string", "description": "Delivery stop ID (optional)"},
                "ticketNumber": {"type": "string", "description": "Specific ticket number to confirm"},
                "onlyOpenOrders": {"type": "boolean", "description": "Only list open/pending orders"}
            },
            "required": ["customerId"]
        }
    },
    {
        "name": "send_contract",
        "description": "Send onboarding contract to new customer via JotForm. Use for new customer signups only.",
        "url": f"{BACKEND_URL}/tools/onboarding/send-contract",
        "method": "POST",
        "headers": {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {INTERNAL_API_KEY}"
        },
        "body": {
            "type": "object",
            "properties": {
                "customerName": {"type": "string", "description": "Full customer name"},
                "email": {"type": "string", "description": "Customer email address"},
                "phone": {"type": "string", "description": "Customer phone number"},
                "address": {"type": "string", "description": "Street address"},
                "city": {"type": "string", "description": "City name"},
                "state": {"type": "string", "description": "State code (2 letters)"},
                "postalCode": {"type": "string", "description": "ZIP/postal code"},
                "deliveryPreference": {"type": "string", "description": "Preferred delivery day"},
                "companyName": {"type": "string", "description": "Company or organization name"},
                "productsOfInterest": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Products the customer would like (e.g., 5-gallon bottles)"
                },
                "specialInstructions": {"type": "string", "description": "Additional notes or instructions"},
                "marketingOptIn": {"type": "boolean", "description": "Marketing opt-in acknowledgement"},
                "sendEmail": {"type": "boolean", "description": "Send contract via email (default true)"}
            },
            "required": ["customerName", "email", "phone", "address", "city", "state", "postalCode"]
        }
    }
]


async def get_assistant(client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Fetch current assistant configuration."""
    try:
        response = await client.get(
            f"{VAPI_BASE_URL}/assistant/{NEW_ASSISTANT_ID}",
            headers={"Authorization": f"Bearer {VAPI_API_KEY}"},
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


async def create_api_request_tool(tool_def: dict[str, Any]) -> dict[str, Any]:
    """Convert tool definition to VAPI Function tool with server configuration."""
    return {
        "type": "function",
        "server": {
            "url": tool_def["url"],
            "secret": INTERNAL_API_KEY
        },
        "function": {
            "name": tool_def["name"],
            "description": tool_def["description"],
            "parameters": tool_def["body"],
            "strict": True
        }
    }


async def update_assistant(client: httpx.AsyncClient, assistant: dict[str, Any]) -> dict[str, Any]:
    """Update assistant with API request tools and system prompt."""
    tools = []
    for tool_def in API_REQUEST_TOOLS:
        api_tool = await create_api_request_tool(tool_def)
        tools.append(api_tool)
    
    model_config = assistant.get("model", {})
    update_payload = {
        "model": {
            "model": model_config.get("model", "gpt-4-turbo"),
            "provider": model_config.get("provider", "openai"),
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                }
            ],
            "tools": tools
        },
        "firstMessage": "Hello! I'm Riley from Fontis Water. How can I help you today?",
        "name": assistant.get("name", "Riley"),
        "voice": assistant.get("voice", {
            "model": "eleven_turbo_v2_5",
            "voiceId": "21m00Tcm4TlvDq8ikWAM",
            "provider": "11labs"
        })
    }
    
    try:
        response = await client.patch(
            f"{VAPI_BASE_URL}/assistant/{NEW_ASSISTANT_ID}",
            headers={
                "Authorization": f"Bearer {VAPI_API_KEY}",
                "Content-Type": "application/json"
            },
            json=update_payload,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if e.response else "Unknown error"
        print(f"   ❌ API Error: {e.response.status_code}")
        print(f"   Response: {error_detail[:500]}")
        raise


async def main() -> int:
    """Main execution."""
    if not VAPI_API_KEY or not INTERNAL_API_KEY:
        print("❌ Missing VAPI_API_KEY or INTERNAL_API_KEY")
        return 1
    
    print("=" * 80)
    print("🚀 SETTING UP NEW VAPI ASSISTANT WITH API REQUEST TOOLS")
    print("=" * 80)
    print(f"Assistant ID: {NEW_ASSISTANT_ID}")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Tools: {len(API_REQUEST_TOOLS)} API request tools")
    print()
    
    async with httpx.AsyncClient() as client:
        print("1️⃣ Fetching assistant configuration...")
        assistant = await get_assistant(client)
        
        if not assistant:
            print(f"❌ Assistant {NEW_ASSISTANT_ID} not found")
            print("   Please create the assistant in VAPI dashboard first")
            return 1
        
        print(f"   ✓ Found assistant: {assistant.get('name')}")
        print()
        
        print("2️⃣ Updating assistant with API request tools...")
        updated = await update_assistant(client, assistant)
        
        print("   ✓ Assistant updated successfully")
        print()
        
        print("3️⃣ Verifying configuration...")
        verify = await get_assistant(client)
        tools = verify.get("model", {}).get("tools", [])
        
        print(f"   ✓ Tools configured: {len(tools)}")
        for tool in tools:
            tool_name = tool.get("function", {}).get("name", "unknown")
            tool_type = tool.get("type", "unknown")
            tool_url = tool.get("server", {}).get("url", "N/A")
            print(f"      • {tool_name} ({tool_type}) → {tool_url}")
        print()
        
        print("4️⃣ Publishing assistant...")
        try:
            publish_response = await client.patch(
                f"{VAPI_BASE_URL}/assistant/{NEW_ASSISTANT_ID}/publish",
                headers={
                    "Authorization": f"Bearer {VAPI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={},
                timeout=30.0
            )
            publish_response.raise_for_status()
            print("   ✓ Assistant published")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                print("   ⚠️  Publish endpoint not found (may require manual publish)")
            else:
                print(f"   ⚠️  Publish failed: {e.response.status_code}")
                print(f"   Response: {e.response.text[:200]}")
        print()
        
        print("=" * 80)
        print("✅ SETUP COMPLETE")
        print("=" * 80)
        print()
        print("📋 Next Steps:")
        print("   1. Go to VAPI Dashboard → Assistant (refresh page if tools not visible)")
        print("   2. Verify all 15 tools appear in Tools section")
        print("   3. Test each tool in the Test Tool panel")
        print("   4. If tools don't appear: Publish the assistant manually in dashboard")
        print("   5. Start a new chat to test")
        print()
        print(f"🔗 Dashboard: https://dashboard.vapi.ai/assistant/{NEW_ASSISTANT_ID}")
        print()
        print("💡 TROUBLESHOOTING:")
        print("   - Tools ARE configured (verified via API)")
        print("   - If dashboard shows empty: Refresh browser page")
        print("   - If still empty: Check if assistant needs manual publish")
        print("   - Tools are type 'function' with server.url (correct for VAPI)")
        print()
        
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
