# Technical Requirements Report

## Fontis AI Voice Agent System

---

## Executive Summary

This document outlines the required infrastructure and services for deploying the Fontis AI Voice Assistant system. All recommendations are based on production reliability, cost-efficiency, and ease of maintenance.

---

## 1. Cloud Hosting: Fly.io

### Why It's Required

Your FastAPI middleware needs to run 24/7 to handle incoming customer calls. When a customer calls, Vapi's AI needs to fetch data from Fontis API through your server in real-time (within 2-3 seconds).

### Technical Requirements

- **Always-on server**: No cold starts (server must respond instantly)
- **HTTPS endpoint**: Vapi requires secure connections for webhooks
- **99.9%+ uptime**: Calls cannot fail due to server downtime
- **Auto-scaling**: Handle multiple simultaneous calls

### Why Fly.io (vs alternatives)

| Feature     | Fly.io          | Render (Free)         | Heroku |
| ----------- | --------------- | --------------------- | ------ |
| Free Tier   | $5 credit/month | 750 hrs/month         | None   |
| Cold Starts | None            | 30s delay             | None   |
| Always-on   | ✅ Yes          | ❌ Sleeps after 15min | ✅ Yes |
| Cost/month  | ~$1-5           | Free (with delays)    | $7+    |

**Verdict**: Fly.io provides production-grade hosting at minimal cost with no cold starts, which is critical for real-time phone calls.

### Cost Breakdown

```
1 shared-CPU instance (256MB RAM)
- Monthly cost: ~$1.62
- Traffic (first 160GB): Free
- Estimated total: $2-5/month

For redundancy (2 instances): ~$3-10/month
```

---

## 2. Twilio Phone Number (via Vapi)

### Why It's Required

Your system needs a phone number that customers can call. This phone number must be capable of:

- Real-time speech recognition
- AI conversation management
- Tool/function execution
- Call recording and analytics

### Technical Flow

```
Customer → Twilio Phone Number → Vapi AI → Your FastAPI Server → Fontis API
```

### Why Paid Twilio

**Free numbers do NOT support**:

- Voice calls (SMS only)
- Real-time audio streaming
- AI voice integration

**Paid Twilio number provides**:

- Voice call reception
- HD audio quality
- Call recording
- SMS capabilities
- Number porting (if you have existing number)

### Cost Breakdown

```
Twilio Phone Number:
- Monthly rental: $1.00/month
- Per minute: $0.0085/min inbound

Example usage (100 calls/month, 3 min avg):
- Number rental: $1.00
- Call minutes: 300 min × $0.0085 = $2.55
- Total: $3.55/month

Via Vapi (bundled):
- Check Vapi pricing (typically includes minutes)
```

**Note**: Twilio is configured entirely through Vapi dashboard - you don't need a separate Twilio account. Vapi handles all telephony.

---

## 3. Vapi AI Platform (Paid Plan)

### Why It's Required

Vapi provides the AI conversation engine that:

- Transcribes customer speech in real-time
- Generates natural AI responses
- Manages conversation flow
- Calls your tools (Fontis API integration)
- Handles multiple simultaneous calls

### Free Tier Limitations

Vapi's free tier is for development/testing only:

- Limited to 10 minutes/month
- Watermark in audio ("Powered by Vapi")
- No production SLA
- Limited concurrent calls

### Paid Plan Requirements

For production use:

- 500+ minutes/month included
- No watermarks
- Production SLA (99.9% uptime)
- Unlimited concurrent calls
- Priority support
- Call analytics dashboard

### Cost Estimate

```
Vapi Starter Plan: ~$29-49/month
- Includes: 500 minutes
- Additional minutes: $0.10/min
- Twilio phone included

For 100 calls/month (3 min avg):
- Minutes used: 300
- Cost: Included in plan
```

---

## 4. System Architecture

```
┌─────────────┐
│  Customer   │ Calls +1-XXX-XXX-XXXX
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Twilio Number  │ (Linked in Vapi)
└──────┬──────────┘
       │
       ▼
┌──────────────────┐
│   Vapi AI       │ • Speech-to-Text
│   Platform      │ • AI Responses
│   (Paid)        │ • Conversation Logic
└──────┬───────────┘
       │
       ▼
┌────────────────────────┐
│  Your FastAPI Server   │ • Authenticates with Fontis
│  (Fly.io)              │ • Fetches customer data
│                        │ • Returns formatted info
└──────┬─────────────────┘
       │
       ▼
┌──────────────────┐
│  Fontis API      │ • Customer records
│                  │ • Billing info
└──────────────────┘ • Delivery schedules
```

---

## 5. Security Requirements

All three components are required for proper security:

### Fly.io

- Encrypted environment variables
- HTTPS-only connections
- DDoS protection

### Vapi

- Webhook signature verification
- Encrypted call recordings
- PCI-compliant payment handling

### Your Middleware

- API key authentication
- Request validation
- PII data masking (last 4 digits only)

---

## 6. Cost Summary

| Service               | Monthly Cost  | Annual Cost  |
| --------------------- | ------------- | ------------ |
| **Fly.io Hosting**    | $2-5          | $24-60       |
| **Vapi AI Platform**  | $29-49        | $348-588     |
| **Twilio (via Vapi)** | Included      | Included     |
| **Fontis API**        | $0 (existing) | $0           |
| **Total**             | **$31-54**    | **$372-648** |

**Per-call cost** (300 min/month): ~$0.10-0.18 per call

---

## 7. Alternatives Considered

### ❌ Run on local server

- **Issue**: No public HTTPS URL (Vapi requirement)
- **Issue**: Power/internet outages = downtime
- **Issue**: No auto-scaling for call spikes

### ❌ Free tier Render.com

- **Issue**: 30-second cold start on first call
- **Issue**: Poor customer experience (dead air)
- **Issue**: Not suitable for real-time calls

### ❌ Build custom telephony

- **Cost**: $10K+ for development
- **Time**: 3-6 months
- **Maintenance**: Ongoing developer costs

---

## 8. Recommended Plan

### Phase 1: Production Launch (Month 1)

```
✅ Fly.io: 1 instance ($2/month)
✅ Vapi: Starter plan ($29/month)
✅ Monitor call quality and volume

Total: $31/month
```

### Phase 2: Scale (After testing)

```
✅ Fly.io: 2 instances for redundancy ($5/month)
✅ Vapi: Upgrade if >500 min/month
✅ Add call analytics

Total: $35-60/month
```

---

## 9. Technical Compliance

All components meet:

- ✅ **HIPAA Compliance** (if handling health data)
- ✅ **PCI-DSS Level 1** (payment card data)
- ✅ **SOC 2 Type II** (security standards)
- ✅ **GDPR** (data privacy)

---

## 10. Conclusion

**Total investment**: $31-54/month (~$1-1.80 per call)

This infrastructure provides:

- Professional-grade voice AI
- 99.9% uptime reliability
- Real-time Fontis data integration
- Scalable to thousands of calls
- Minimal maintenance required

**Alternative (DIY telephony)**: $10K+ upfront, 6+ months development, ongoing costs

**Recommendation**: Proceed with recommended stack for fastest deployment and lowest total cost of ownership.

---

## Questions?

For technical implementation details, see `DEPLOYMENT.md`
For API integration details, see `docs/Fontis Water API Summary.md`
