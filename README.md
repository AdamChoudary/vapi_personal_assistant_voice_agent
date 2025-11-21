# Fontis AI Voice Agent

AI-powered voice agent for Fontis Water customer service and automated outbound calling.

## 🚀 Features

### Inbound Call Handling
- Customer account search and lookup
- Billing information and payment history
- Delivery scheduling and modifications
- Service area verification
- New customer onboarding
- Contract generation and tracking

### Outbound Call Automation
- Declined payment notifications
- Collections calls for past due accounts
- Delivery reminder calls
- Call status tracking

## 🏗️ Tech Stack

- **Framework:** FastAPI
- **Package Manager:** uv
- **AI Platform:** Vapi AI (GPT-4 Turbo)
- **Voice:** 11labs
- **External APIs:** Fontis Water API, JotForm

## 📋 Prerequisites

- Python 3.13+
- uv package manager
- Ngrok (for local development)
- Vapi account with phone number
- Fontis API credentials

## 🔧 Installation

```bash
# Install dependencies
uv pip install -e .

# Copy environment template
cp env.example .env

# Configure environment variables
# Edit .env with your API keys and credentials
```

## ⚙️ Configuration

Required environment variables in `.env`:

```env
# Vapi Configuration
VAPI_API_KEY=your_private_api_key
VAPI_PUBLIC_KEY=your_public_key
VAPI_ASSISTANT_ID=your_assistant_id

# Fontis API
FONTIS_API_KEY=your_fontis_api_key
FONTIS_BASE_URL=https://fontisweb.creatordraft.com/api/v1

# Security
INTERNAL_API_KEY=your_32_char_api_key

# JotForm (for contracts)
JOTFORM_API_KEY=your_jotform_key
JOTFORM_FORM_ID=your_form_id
```

## 🚀 Running Locally

### Start the Server

```bash
python run.py
```

Server will start on `http://localhost:8000`

### Start Ngrok Tunnel

```bash
ngrok http 8000
```

Update Vapi webhook URL with the ngrok URL: `https://YOUR-NGROK-URL/vapi/webhooks`

## 📞 Usage

### Inbound Calls

Customers call your Vapi phone number. The AI assistant handles:
- Account inquiries
- Billing questions
- Delivery scheduling
- New customer signup

### Outbound Calls

Trigger via admin API:

```bash
# Get your API key
python -c "from src.config import settings; print(settings.internal_api_key)"

# Trigger declined payment call
curl -X POST http://localhost:8000/admin/outbound/declined-payment \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "C12345",
    "customer_phone": "+16785551234",
    "customer_name": "John Doe",
    "declined_amount": 45.99,
    "account_balance": 89.50
  }'
```

## 📚 API Documentation

Interactive API docs available at: `http://localhost:8000/docs`

### Key Endpoints

**Public:**
- `GET /health` - Health check
- `POST /vapi/webhooks` - Vapi webhook handler

**Admin (requires Bearer token):**
- `POST /admin/outbound/declined-payment` - Trigger declined payment call
- `POST /admin/outbound/collections` - Trigger collections call
- `POST /admin/outbound/delivery-reminder` - Trigger delivery reminder
- `GET /admin/outbound/call-status/{id}` - Get call status

**Tools (called by Vapi):**
- `POST /tools/customer/search` - Search customers
- `POST /tools/billing/balance` - Get billing info
- `POST /tools/delivery/next` - Get next delivery
- `POST /tools/delivery/hold` - Hold delivery
- `POST /tools/routes/check-service` - Check service area
- `POST /tools/onboarding/create-account` - Create account

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Test health endpoint
curl http://localhost:8000/health

# Test with API docs
open http://localhost:8000/docs
```

## 📁 Project Structure

```
vapi_personal_assistant_voice_agent/
├── src/
│   ├── api/
│   │   ├── admin/          # Admin endpoints (outbound calls)
│   │   ├── tools/          # Tool endpoints (Vapi calls these)
│   │   └── vapi/           # Vapi webhooks
│   ├── core/               # Core utilities (deps, exceptions, security)
│   ├── schemas/            # Pydantic models
│   ├── services/           # Business logic
│   ├── config.py           # Configuration management
│   └── main.py             # FastAPI application
├── tests/                  # Unit tests
├── static/                 # Web interface
├── docs/                   # Project documentation
├── pyproject.toml          # Project config
├── run.py                  # Server entry point
└── README.md               # This file
```

## 🔐 Security

- Bearer token authentication for admin endpoints
- API key authentication for tool endpoints
- Webhook signature verification
- Environment-based secrets management
- HTTPS for all external communications

## 🚀 Deployment

See `DEPLOYMENT_READY.md` for production deployment guide.

### Quick Deploy Options

- **Fly.io:** `fly deploy` (see `fly.toml`)
- **Render:** Use `render.yaml`
- **Docker:** Use included `Dockerfile`

## 📊 Status

- ✅ Inbound customer service calls
- ✅ Outbound declined payment calls
- ✅ Outbound collections calls
- ✅ Outbound delivery reminders
- ✅ Real-time Fontis API integration
- ✅ Contract generation via JotForm
- ✅ Comprehensive error handling
- ✅ Structured logging

## 📖 Documentation

- `SYSTEM_READY.md` - Complete system status and verification
- `PROJECT_STATUS_FINAL.md` - Full implementation details
- `OUTBOUND_CALLS_READY.md` - Outbound call API reference
- `VAPI_DASHBOARD_SETUP.md` - Vapi configuration guide
- `DEPLOYMENT_READY.md` - Production deployment checklist

## 🤝 Support

For issues or questions:
1. Check API docs: `http://localhost:8000/docs`
2. Review logs: Server terminal output
3. Check ngrok: `http://localhost:4040`
4. Vapi dashboard: https://dashboard.vapi.ai

## 📄 License

See `LICENSE` file.

## 🏆 Project Status

**Status:** Production Ready ✅  
**Version:** 0.1.0  
**Last Updated:** October 24, 2025

All features implemented and tested according to project requirements.
