# Deployment Guide - Fly.io

## Prerequisites

1. **Fly.io Account**: Sign up at https://fly.io
2. **Fly CLI Installed**:

   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"

   # Mac/Linux
   curl -L https://fly.io/install.sh | sh
   ```

3. **Vapi Account**: With paid plan and Twilio number linked
4. **Fontis API Key**: Already provided

## Step 1: Fly.io Setup

```bash
# Login to Fly.io
fly auth login

# Launch app (run in project directory)
fly launch

# When prompted:
# - App name: fontis-voice-agent (or your preferred name)
# - Region: Choose closest to your location
# - PostgreSQL: No
# - Redis: No
```

## Step 2: Set Environment Secrets

```bash
# Generate internal API key
$API_KEY = -join ((48..57) + (97..122) | Get-Random -Count 64 | % {[char]$_})

# Set all secrets
fly secrets set `
  FONTIS_API_KEY="fk_XzaL3iEikKvSjPuhbk7NBbGMYoSMVeQHaN9jpq0d9vtUAn8rueZNVwluILy3" `
  VAPI_API_KEY="your_vapi_api_key" `
  VAPI_PUBLIC_KEY="your_vapi_public_key" `
  VAPI_ASSISTANT_ID="your_assistant_id" `
  VAPI_WEBHOOK_SECRET="your_webhook_secret" `
  INTERNAL_API_KEY="$API_KEY" `
  APP_ENV="production" `
  CORS_ORIGINS='["https://vapi.ai"]'
```

## Step 3: Deploy

```bash
# Deploy to Fly.io
fly deploy

# Check status
fly status

# View logs
fly logs
```

## Step 4: Get Your URL

```bash
# Your app will be available at:
fly status
# Example: https://fontis-voice-agent.fly.dev
```

## Step 5: Configure Vapi Dashboard

1. **Go to Vapi Dashboard** → Your Assistant
2. **Set Webhook URL**: `https://fontis-voice-agent.fly.dev/webhooks/vapi`
3. **Configure Tools** - For each tool, set:
   - URL: `https://fontis-voice-agent.fly.dev/tools/customer/search` (example)
   - Method: POST
   - Headers: `Authorization: Bearer <INTERNAL_API_KEY>`

### Tools to Configure:

| Tool Name          | Endpoint                         |
| ------------------ | -------------------------------- |
| searchCustomer     | /tools/customer/search           |
| getCustomerDetails | /tools/customer/details          |
| getDeliveryStops   | /tools/customer/delivery-stops   |
| getNextDelivery    | /tools/delivery/next-scheduled   |
| getDefaultProducts | /tools/delivery/default-products |
| getAccountBalance  | /tools/billing/balance           |
| getInvoiceHistory  | /tools/billing/invoice-history   |
| getPaymentMethods  | /tools/billing/payment-methods   |
| getContracts       | /tools/contracts/list            |

## Step 6: Link Twilio in Vapi

1. **Vapi Dashboard** → Phone Numbers
2. **Connect Twilio Account**
3. **Import Your Number**
4. **Assign to Assistant**

## Monitoring

```bash
# Real-time logs
fly logs -a fontis-voice-agent

# App metrics
fly dashboard
```

## Scaling (If Needed)

```bash
# Scale to 2 instances for redundancy
fly scale count 2

# Increase memory if needed
fly scale memory 1024
```

## Troubleshooting

```bash
# Check app health
fly status

# Restart app
fly apps restart fontis-voice-agent

# SSH into container
fly ssh console
```
