# Fontis AI Voice Agent

Production-ready FastAPI middleware connecting Vapi AI with Fontis Water API for automated customer service calls.

## Features

- ✅ **19 Production APIs**: 17 Fontis APIs + JotForm onboarding integration
- ✅ **Complete Coverage**: Customer search, billing, delivery, contracts, routes, onboarding
- ✅ **Secure Authentication**: API key protection on all endpoints
- ✅ **Webhook Verification**: HMAC signature validation
- ✅ **Production Ready**: Docker + Fly.io deployment
- ✅ **Error Handling**: Retry logic, structured logging
- ✅ **Type Safe**: Full Pydantic validation

## Quick Start (Development)

```bash
# Install dependencies
pip install -e .

# Configure environment
cp env.example .env
# Edit .env with your credentials

# Run development server
python run.py
```

Server available at: `http://localhost:8000`

## Production Deployment

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for complete Fly.io setup guide.

```bash
# Quick deploy
fly launch
fly secrets set FONTIS_API_KEY=xxx INTERNAL_API_KEY=xxx JOTFORM_API_KEY=xxx JOTFORM_FORM_ID=xxx
fly deploy
```

## Project Structure

```
src/
├── main.py              # FastAPI app with middleware
├── config.py            # Environment configuration
├── api/
│   ├── webhooks.py      # Vapi webhook handlers
│   └── tools/           # Tool endpoints (19 production APIs)
│       ├── customer.py  # Customer search, details, finance
│       ├── billing.py   # Invoices, payments, products
│       ├── delivery.py  # Schedules, orders, frequencies
│       ├── contracts.py # Service agreements
│       ├── routes.py    # Route stops
│       └── onboarding.py # JotForm integration
├── services/
│   ├── fontis_client.py # Fontis API integration (17 endpoints)
│   ├── vapi_client.py   # Vapi outbound calls
│   └── jotform_client.py # JotForm contract generation
├── core/
│   ├── deps.py          # FastAPI dependencies
│   ├── security.py      # Authentication
│   └── exceptions.py    # Custom exceptions
└── schemas/             # Pydantic models
```

## API Endpoints

### Core

- `GET /` - Service information
- `GET /health` - Health check for monitoring
- `GET /docs` - OpenAPI documentation (dev only)

### Webhooks

- `POST /webhooks/vapi` - Receive call events from Vapi

### Tools (All require authentication)

**Customer APIs** (3 endpoints)
- `POST /tools/customer/search` - Search customers
- `POST /tools/customer/details` - Get customer details
- `POST /tools/customer/finance-info` - Combined finance & delivery info

**Billing APIs** (6 endpoints)
- `POST /tools/billing/balance` - Account balances
- `POST /tools/billing/invoice-history` - Invoices and payments
- `POST /tools/billing/invoice-detail` - Detailed invoice line items
- `POST /tools/billing/payment-methods` - Payment methods on file
- `POST /tools/billing/products` - Product catalog & pricing
- `POST /tools/billing/add-credit-card` - Add payment method

**Delivery APIs** (6 endpoints)
- `POST /tools/delivery/stops` - Delivery locations
- `POST /tools/delivery/next-scheduled` - Next delivery date
- `POST /tools/delivery/default-products` - Standing orders
- `POST /tools/delivery/orders` - Off-route delivery orders
- `POST /tools/delivery/orders/search` - Search orders by ticket/customer
- `GET /tools/delivery/frequencies` - Delivery frequency codes

**Contracts & Routes** (2 endpoints)
- `POST /tools/contracts/get-contracts` - Customer contracts
- `POST /tools/routes/stops` - Route stops for specific date

**Onboarding** (2 endpoints)
- `POST /tools/onboarding/send-contract` - Send JotForm contract
- `GET /tools/onboarding/contract-status/{id}` - Check submission status

## Configuration

Required environment variables:

```bash
# Fontis API (Required)
FONTIS_API_KEY=fk_your_key_here
FONTIS_BASE_URL=https://api.fontiswater.com/api/v1

# Internal Security (Required)
INTERNAL_API_KEY=your_32_char_minimum_api_key

# JotForm (Required for onboarding)
JOTFORM_API_KEY=your_jotform_api_key
JOTFORM_FORM_ID=your_form_id

# Vapi AI (Optional for outbound calls)
VAPI_API_KEY=your_vapi_secret_key
VAPI_PUBLIC_KEY=your_vapi_public_key
VAPI_WEBHOOK_SECRET=your_webhook_secret

# Application
APP_ENV=development
LOG_LEVEL=info
CORS_ORIGINS=http://localhost:8000
```

See `env.example` for complete configuration template.

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[CLIENT_REPORT.md](CLIENT_REPORT.md)** - Technical requirements explanation
- **[docs/](docs/)** - API reference and requirements

## Security

- ✅ API key authentication on all tool endpoints
- ✅ Webhook signature verification (HMAC-SHA256)
- ✅ CORS restricted to Vapi servers only
- ✅ Environment-based secrets management
- ✅ PII data masking (payment methods)
- ✅ Production/development environment separation

## Technology Stack

- **Framework**: FastAPI 0.115+ (Python 3.11+)
- **HTTP Client**: httpx (async, connection pooling)
- **Validation**: Pydantic 2.9+
- **Logging**: structlog (JSON structured logs)
- **Retry Logic**: tenacity
- **Deployment**: Docker + Fly.io
- **AI Platform**: Vapi + Twilio
