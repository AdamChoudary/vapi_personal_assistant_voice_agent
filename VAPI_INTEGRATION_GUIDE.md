# Vapi Integration Guide - Hybrid Approach

## Overview

This guide explains how the **Fontis Water AI Assistant** integrates with Vapi using a **hybrid architecture**:

- **90% Custom** → Your FastAPI middleware handles all business logic
- **10% Vapi Dashboard** → Configuration and voice settings only

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────┐
│         Customer (Inbound/Outbound Call)        │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│              TWILIO (Telephony)                 │
│  - Phone number routing                         │
│  - Call recording                               │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│             VAPI AI PLATFORM                    │
│  ┌───────────────────────────────────────────┐  │
│  │  VAPI DASHBOARD (Configuration Only)      │  │
│  │  • System prompt text                     │  │
│  │  • Voice settings (ElevenLabs)            │  │
│  │  • Call routing settings                  │  │
│  │  • Function definitions (19 tools)        │  │
│  │  • Analytics dashboard                    │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  VAPI AI ENGINE (Automatic)              │  │
│  │  • Speech-to-text (Deepgram)             │  │
│  │  • LLM processing (GPT-4o)               │  │
│  │  • Text-to-speech (ElevenLabs)           │  │
│  │  • Conversation management               │  │
│  └───────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────┘
                    │
                    │ Webhooks + Function Calls
                    ▼
┌─────────────────────────────────────────────────┐
│      YOUR CUSTOM MIDDLEWARE (FastAPI)           │
│  Endpoint: /vapi/webhooks                       │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  Function Call Router                     │  │
│  │  • Receives tool call from Vapi          │  │
│  │  • Validates parameters                   │  │
│  │  • Routes to internal tool               │  │
│  │  • Manages call context (state)          │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  19 Production Tools                      │  │
│  │  • Customer search/details                │  │
│  │  • Delivery scheduling                    │  │
│  │  • Billing & invoices                     │  │
│  │  • Payment methods (PII masked)           │  │
│  │  • Products & pricing                     │  │
│  │  • Contracts & agreements                 │  │
│  │  • JotForm onboarding                     │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  ┌───────────────────────────────────────────┐  │
│  │  Security & Business Logic                │  │
│  │  • API key authentication                 │  │
│  │  • PII masking                            │  │
│  │  • Error handling                         │  │
│  │  • Retry logic                            │  │
│  │  • Structured logging                     │  │
│  └───────────────────────────────────────────┘  │
└───────────────────┬─────────────────────────────┘
                    │
                    │ REST API Calls
                    ▼
┌─────────────────────────────────────────────────┐
│          FONTIS WATER API                       │
│  - Customer data                                │
│  - Invoices & payments                          │
│  - Delivery schedules                           │
│  - Products & pricing                           │
│  - Contracts & equipment                        │
└─────────────────────────────────────────────────┘
```

---

## File Structure

```
vapi_personal_assistant_voice_agent/
│
├── vapi_system_prompt.md          # System prompt (copy/paste to Vapi dashboard)
├── vapi_assistant_config.json     # Assistant config (import to Vapi dashboard)
├── VAPI_INTEGRATION_GUIDE.md      # This file
│
├── src/
│   ├── main.py                     # FastAPI app with Vapi webhook router
│   │
│   ├── api/
│   │   ├── vapi/
│   │   │   ├── __init__.py
│   │   │   └── webhooks_handler.py # Vapi webhook & function call handler
│   │   │
│   │   └── tools/                  # 19 production tool endpoints
│   │       ├── customer.py
│   │       ├── delivery.py
│   │       ├── billing.py
│   │       ├── contracts.py
│   │       ├── routes.py
│   │       └── onboarding.py
│   │
│   ├── schemas/
│   │   ├── vapi.py                 # Vapi webhook schemas
│   │   └── tools.py                # Tool parameter schemas
│   │
│   └── services/
│       ├── fontis_client.py        # Fontis API client
│       ├── vapi_client.py          # Vapi API client (outbound calls)
│       └── jotform_client.py       # JotForm integration
│
└── .env                            # Environment variables
```

---

## Setup Instructions

### Step 1: Deploy Your Middleware to Fly.io

```bash
# 1. Login to Fly.io
fly auth login

# 2. Launch your app
fly launch --no-deploy

# 3. Set secrets
fly secrets set \
  INTERNAL_API_KEY="your-secure-32char-api-key" \
  FONTIS_API_KEY="your-fontis-api-key" \
  VAPI_PUBLIC_KEY="your-vapi-public-key" \
  VAPI_WEBHOOK_SECRET="your-webhook-secret" \
  JOTFORM_API_KEY="your-jotform-api-key"

# 4. Deploy
fly deploy

# 5. Get your URL
fly info
# Example: https://fontis-ai-assistant.fly.dev
```

### Step 2: Configure Vapi Dashboard

#### 2.1 Create New Assistant

1. Go to [Vapi Dashboard](https://dashboard.vapi.ai)
2. Click **"Create Assistant"**
3. Name it: `Fontis Water AI Assistant`

#### 2.2 Import Configuration

**Option A: Manual Setup**

1. Open `vapi_assistant_config.json`
2. Copy each section into the corresponding Vapi dashboard field

**Option B: API Import** (Recommended)

```bash
# Use Vapi API to import configuration
curl -X POST https://api.vapi.ai/assistant \
  -H "Authorization: Bearer YOUR_VAPI_API_KEY" \
  -H "Content-Type: application/json" \
  -d @vapi_assistant_config.json
```

#### 2.3 Update Webhook URLs

In `vapi_assistant_config.json`, replace all instances of:

```
https://your-app-name.fly.dev
```

With your actual Fly.io URL:

```
https://fontis-ai-assistant.fly.dev
```

Then update in Vapi dashboard:

- **Server URL**: `https://fontis-ai-assistant.fly.dev/vapi/webhooks`
- **Server URL Secret**: Your `VAPI_WEBHOOK_SECRET` from `.env`

#### 2.4 Configure All 19 Functions

Each function in `vapi_assistant_config.json` needs:

- **URL**: Update to your Fly.io URL
- **Headers**:
  ```json
  {
    "Authorization": "Bearer YOUR_INTERNAL_API_KEY",
    "Content-Type": "application/json"
  }
  ```

Replace `YOUR_INTERNAL_API_KEY` with the value from `.env`.

#### 2.5 Copy System Prompt

1. Open `vapi_system_prompt.md`
2. Copy the **ENTIRE CONTENT**
3. In Vapi dashboard → **Model** → **System Prompt**
4. Paste the content

#### 2.6 Voice Settings

In Vapi dashboard → **Voice**:

- **Provider**: ElevenLabs
- **Voice ID**: `21m00Tcm4TlvDq8ikWAM` (Rachel - professional, friendly)
- **Stability**: `0.5`
- **Similarity Boost**: `0.75`
- **Model**: `eleven_turbo_v2` (low latency)
- **Optimize Streaming Latency**: `3`

#### 2.7 Model Settings

In Vapi dashboard → **Model**:

- **Provider**: OpenAI
- **Model**: `gpt-4o`
- **Temperature**: `0.7`
- **Max Tokens**: `300`
- **Emotion Recognition**: Enabled

#### 2.8 Call Settings

In Vapi dashboard → **Call Settings**:

- **First Message**: `"Thank you for calling Fontis Water. May I have your service address to pull up your account?"`
- **End Call Message**: `"Thank you for calling Fontis Water. Have a great day!"`
- **Silence Timeout**: `30 seconds`
- **Response Delay**: `0.8 seconds`
- **Interruptions**: Enabled
- **Words to Interrupt**: `2`
- **Max Call Duration**: `600 seconds` (10 minutes)
- **Recording**: Enabled

### Step 3: Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com)
2. Buy a phone number (if you don't have one)
3. Configure the number:
   - **Voice & Fax** → **A Call Comes In**
   - **Webhook**: Use Vapi's Twilio webhook URL (found in Vapi dashboard)
   - **HTTP POST**

### Step 4: Test the Integration

#### 4.1 Test Inbound Call

1. Call your Twilio number
2. You should hear: "Thank you for calling Fontis Water..."
3. Provide a customer name or address
4. The AI should call `customer_search` via your middleware

#### 4.2 Monitor Logs

**On Fly.io:**

```bash
fly logs
```

**On Vapi Dashboard:**

- Go to **Calls** → View real-time call logs
- Check **Transcripts** for conversation history
- Review **Function Calls** to see tool executions

#### 4.3 Verify Webhook Connectivity

```bash
# Test webhook endpoint
curl -X POST https://fontis-ai-assistant.fly.dev/vapi/webhooks \
  -H "Authorization: Bearer YOUR_INTERNAL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "call-start",
    "callId": "test-123",
    "timestamp": "2025-10-23T10:00:00Z"
  }'

# Expected response:
# {"success": true, "message": "Call started"}
```

---

## How Function Calls Work

### Call Flow Example: "What do I owe?"

```
1. Customer speaks: "What do I owe?"
   ↓
2. Vapi (Deepgram) transcribes to text
   ↓
3. Vapi (GPT-4o) processes:
   - Identifies intent: Check account balance
   - Determines customer verification is needed first
   ↓
4. Vapi asks: "May I have your service address?"
   ↓
5. Customer: "3929 Canton Road"
   ↓
6. Vapi decides to call function: customer_search
   ↓
7. Vapi sends webhook to YOUR MIDDLEWARE:
   POST /vapi/webhooks
   {
     "type": "function-call",
     "functionName": "customer_search",
     "parameters": {
       "lookup": "3929 Canton Road"
     },
     "callId": "abc-123"
   }
   ↓
8. YOUR MIDDLEWARE (webhooks_handler.py):
   - Routes to customer_search_handler()
   - Calls FontisClient.search_customers()
   - Returns formatted response to Vapi
   ↓
9. Vapi receives result:
   {
     "success": true,
     "result": {
       "data": {
         "customerId": "002864",
         "name": "Jamie Carroll",
         "deliveryId": "002864000"
       }
     }
   }
   ↓
10. Vapi (GPT-4o) processes result:
    - Stores customerId + deliveryId in context
    - Now calls account_balance function
    ↓
11. Vapi sends another webhook:
    POST /vapi/webhooks
    {
      "type": "function-call",
      "functionName": "account_balance",
      "parameters": {
        "customerId": "002864"
      },
      "callId": "abc-123"
    }
    ↓
12. YOUR MIDDLEWARE:
    - Routes to account_balance_handler()
    - Calls FontisClient.get_account_balances()
    - Returns balance data
    ↓
13. Vapi receives balance:
    {
      "success": true,
      "result": {
        "data": {
          "totalDueBalance": 171.60,
          "pastDueBalance": 0
        }
      }
    }
    ↓
14. Vapi (GPT-4o) formulates response:
    "Your current balance is $171.60 with no past due amount."
    ↓
15. Vapi (ElevenLabs) speaks response to customer
    ↓
16. Call continues or ends
```

---

## Call Context Management

Your middleware stores context for each call session to avoid asking for the same information multiple times.

**Example:**

```python
# In webhooks_handler.py

# After customer_search, store IDs
if function_name == "customer_search":
    store_call_context(call_id, "customerId", "002864")
    store_call_context(call_id, "deliveryId", "002864000")
    store_call_context(call_id, "customerName", "Jamie Carroll")

# Later, when calling invoice_history:
customer_id = get_call_context(call_id, "customerId")
delivery_id = get_call_context(call_id, "deliveryId")

# Auto-populate parameters if missing
if not parameters.get("customerId"):
    parameters["customerId"] = customer_id
```

**⚠️ Production Note:**
Current implementation uses in-memory storage. For production scale, replace with **Redis**:

```python
# Replace in-memory dict with Redis
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def store_call_context(call_id: str, key: str, value: Any):
    redis_client.hset(f"call:{call_id}", key, value)
    redis_client.expire(f"call:{call_id}", 3600)  # 1 hour TTL

def get_call_context(call_id: str, key: str, default=None):
    return redis_client.hget(f"call:{call_id}", key) or default
```

---

## Updating the System Prompt

### When to Update in Vapi Dashboard vs Code

**✅ Update in Vapi Dashboard when:**

- Changing conversation tone or phrasing
- Adding/removing example dialogues
- Adjusting AI personality
- Updating business policies (hours, pricing, etc)
- Quick iterations and A/B testing

**✅ Update in Code when:**

- Adding new tools/functions
- Changing tool parameters
- Modifying business logic
- Security or PII handling changes
- Error handling improvements

### How to Update Prompt in Vapi Dashboard

1. Go to Vapi Dashboard → **Assistants** → **Fontis Water AI Assistant**
2. Click **Model** tab
3. Edit **System Prompt** field
4. Click **Save**
5. Changes are **immediate** (no deployment needed)

### Version Control Best Practice

Keep `vapi_system_prompt.md` in sync:

```bash
# After editing in Vapi dashboard:
# 1. Copy the prompt text
# 2. Paste into vapi_system_prompt.md
# 3. Commit to Git

git add vapi_system_prompt.md
git commit -m "feat: Update system prompt - adjusted collections call tone"
git push
```

---

## Monitoring & Analytics

### Vapi Dashboard Analytics

Built-in metrics (free):

- **Call Volume**: Inbound/outbound call counts
- **Call Duration**: Average and total talk time
- **Success Rate**: Completed vs dropped calls
- **Function Call Stats**: Which tools are used most
- **Transcript Search**: Search all call transcripts
- **Cost Tracking**: Vapi usage costs per call

### Your Middleware Logs (Fly.io)

Structured logs for debugging:

```bash
# Real-time logs
fly logs

# Filter by call ID
fly logs --search "call_id=abc-123"

# Filter by function name
fly logs --search "function_name=customer_search"

# Filter by errors
fly logs --search "level=error"
```

### Custom Analytics (Optional)

Send logs to external services:

**Option 1: Datadog**

```python
# In src/main.py
import datadog

datadog.initialize(api_key=settings.datadog_api_key)

@app.middleware("http")
async def log_to_datadog(request: Request, call_next):
    response = await call_next(request)
    datadog.statsd.increment('fontis.api.requests')
    return response
```

**Option 2: CloudWatch (AWS)**
**Option 3: Sentry (Error Tracking)**

---

## Security Considerations

### 1. API Key Authentication

All tool endpoints require authentication:

```python
# In src/api/tools/customer.py

@router.post("/search", dependencies=[Depends(verify_api_key)])
async def search_customers(...):
    ...
```

**How it works:**

- Vapi sends `Authorization: Bearer YOUR_INTERNAL_API_KEY` header
- `verify_api_key()` dependency validates the key
- Unauthorized requests return `401 Unauthorized`

### 2. PII Masking

Your middleware masks sensitive data before sending to Vapi:

```python
# Example: Payment methods
{
    "description": "VISA-3758",  # ✅ Masked (last 4 digits only)
    "isPrimary": true,
    "isAutopay": false
}

# NOT sent to Vapi:
# - VaultId
# - PayId
# - Full card number
```

### 3. Webhook Verification

Vapi signs webhooks with HMAC-SHA256:

```python
# In src/core/deps.py

async def verify_vapi_webhook(request: Request):
    """Verify Vapi webhook signature."""
    signature = request.headers.get("X-Vapi-Signature")
    expected = hmac.new(
        settings.vapi_webhook_secret.encode(),
        await request.body(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid signature")
```

### 4. Rate Limiting

Protect your endpoints from abuse:

```python
# Already implemented in src/main.py

from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@app.post("/vapi/webhooks")
@limiter.limit("100/minute")
async def handle_vapi_webhook(...):
    ...
```

---

## Troubleshooting

### Issue: Vapi can't reach my middleware

**Symptoms:**

- Function calls timeout
- Logs show no incoming requests
- Vapi shows "Function call failed"

**Solutions:**

1. Verify Fly.io URL is correct in Vapi dashboard
2. Check Fly.io app is running: `fly status`
3. Test webhook manually:
   ```bash
   curl -X POST https://your-app.fly.dev/vapi/webhooks \
     -H "Authorization: Bearer YOUR_INTERNAL_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"type": "call-start", "callId": "test"}'
   ```
4. Check firewall rules (Fly.io apps are public by default)

### Issue: "401 Unauthorized" errors

**Symptoms:**

- Tool calls fail with authentication errors
- Logs show `invalid_api_key`

**Solutions:**

1. Verify `INTERNAL_API_KEY` matches in:
   - `.env` file
   - Fly.io secrets: `fly secrets list`
   - Vapi function headers in dashboard
2. Ensure API key is at least 32 characters
3. Check for extra spaces or quotes in `.env`

### Issue: Functions return wrong data

**Symptoms:**

- AI says "I couldn't find that information"
- Response data is empty or malformed

**Solutions:**

1. Check Fontis API status
2. Verify `FONTIS_API_KEY` is correct
3. Test Fontis endpoints directly:
   ```bash
   curl -X POST https://fontisweb.creatordraft.com/api/v1/customers/search \
     -H "X-API-Key: YOUR_FONTIS_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"lookup": "Adam"}'
   ```
4. Check middleware logs: `fly logs --search "fontis_api_error"`

### Issue: Call context not persisting

**Symptoms:**

- AI asks for address multiple times
- Customer must re-authenticate repeatedly

**Solutions:**

1. Check `call_contexts` dict in `webhooks_handler.py`
2. Verify `call_id` is consistent across function calls
3. Implement Redis for production (see "Call Context Management" section)

### Issue: Slow response times

**Symptoms:**

- Long pauses during calls
- Customer complains about delays

**Solutions:**

1. Optimize Fontis API calls (use caching for frequently accessed data)
2. Reduce `response_delay_seconds` in Vapi dashboard (0.5-0.8s recommended)
3. Use `eleven_turbo_v2` voice model (not `eleven_multilingual`)
4. Check Fly.io region latency: `fly regions list`
5. Consider upgrading Fly.io machine specs

---

## Cost Optimization

### Vapi Costs (Per Call)

- **Speech-to-Text (Deepgram Nova 2)**: ~$0.0043/min
- **LLM (GPT-4o)**: ~$0.015/call (avg 300 tokens)
- **Text-to-Speech (ElevenLabs Turbo)**: ~$0.18/1000 chars
- **Vapi Platform Fee**: ~$0.05/min

**Average call cost**: ~$0.30-0.50 for 3-5 minute call

### Optimization Tips

1. **Shorten system prompt** (fewer tokens = lower cost)
2. **Use GPT-4o-mini** for simple queries (5x cheaper)
3. **Cache frequently accessed data** (reduce Fontis API calls)
4. **Set max_duration** to prevent runaway calls
5. **Use silence timeout** to detect call abandonment

---

## Next Steps

1. ✅ Complete this guide setup
2. ✅ Test all 19 functions with real calls
3. ✅ Monitor for 1 week, collect feedback
4. ⚠️ Implement Redis for call context (production)
5. ⚠️ Add analytics dashboard (optional)
6. ⚠️ Set up alerting (Sentry/PagerDuty)
7. ⚠️ A/B test different system prompts
8. ⚠️ Train client staff on monitoring

---

## Support & Resources

- **Vapi Documentation**: https://docs.vapi.ai
- **Fly.io Docs**: https://fly.io/docs
- **Your Middleware Docs**: See `API_TOOLS_DOCUMENTATION.md`
- **API Testing Guide**: See `API_TESTING_GUIDE.md`

**Questions?** Check project logs or contact the development team.
