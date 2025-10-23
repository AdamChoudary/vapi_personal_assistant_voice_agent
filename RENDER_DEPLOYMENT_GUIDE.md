# 🚀 Render.com Deployment Guide - Fontis Voice Agent

## ✅ Prerequisites
- [x] GitHub account
- [x] Your code pushed to GitHub repository
- [ ] Render.com account (free, no credit card)

---

## 📋 **Step-by-Step Deployment**

### **Step 1: Push Code to GitHub** (If not already done)

```bash
# If you haven't initialized git yet:
git init
git add .
git commit -m "Initial commit - Fontis Voice Agent"

# Create a new GitHub repository at https://github.com/new
# Then push:
git remote add origin https://github.com/YOUR_USERNAME/fontis-voice-agent.git
git branch -M main
git push -u origin main
```

---

### **Step 2: Sign Up for Render.com**

1. Go to: **https://render.com/**
2. Click **"Get Started for Free"**
3. Sign up with:
   - GitHub (recommended - easier deployment)
   - Google
   - Email

**✅ No credit card required!**

---

### **Step 3: Create New Web Service**

1. After login, click **"New +"** (top right)
2. Select **"Web Service"**
3. Click **"Connect a repository"** or **"Build and deploy from a Git repository"**
4. If using GitHub:
   - Click **"Connect GitHub"**
   - Authorize Render
   - Select your repository: `fontis-voice-agent`
5. If repository not listed, click **"Configure account"** to grant access

---

### **Step 4: Configure Service Settings**

Fill in these settings:

| Field | Value |
|-------|-------|
| **Name** | `fontis-voice-agent` |
| **Region** | `Oregon (US West)` or `Ohio (US East 2)` |
| **Branch** | `main` |
| **Root Directory** | (leave blank) |
| **Runtime** | `Docker` |
| **Instance Type** | `Free` |

---

### **Step 5: Add Environment Variables**

Click **"Advanced"** → Scroll to **"Environment Variables"** → Click **"Add Environment Variable"**

**Add these 15 variables** (copy-paste each):

```
Key: INTERNAL_API_KEY
Value: Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg

Key: FONTIS_API_KEY
Value: fk_XzaL3iEikKvSjPuhbk7NBbGMYoSMVeQHaN9jpq0d9vtUAn8rueZNVwluILy3

Key: FONTIS_BASE_URL
Value: https://fontisweb.creatordraft.com/api/v1

Key: FONTIS_TIMEOUT
Value: 30

Key: FONTIS_MAX_RETRIES
Value: 3

Key: VAPI_API_KEY
Value: 4caf7bf1-2ca7-40e3-bc9b-0906d09f7a9f

Key: VAPI_PUBLIC_KEY
Value: 1e53bbe2-a4b1-460c-bbb4-42d99b9ed154

Key: VAPI_ASSISTANT_ID
Value: 224e4c8f-e968-4248-9d1c-20408126c6a5

Key: VAPI_PHONE_NUMBER
Value: +16783034022

Key: VAPI_PHONE_NUMBER_ID
Value: 172cea7f-07fc-47b8-bbba-5fc8eb179cd6

Key: VAPI_BASE_URL
Value: https://api.vapi.ai

Key: VAPI_WEBHOOK_SECRET
Value: YOUR_WEBHOOK_SECRET_FROM_VAPI_DASHBOARD

Key: JOTFORM_API_KEY
Value: YOUR_JOTFORM_API_KEY

Key: JOTFORM_BASE_URL
Value: https://api.jotform.com

Key: JOTFORM_FORM_ID
Value: YOUR_JOTFORM_FORM_ID

Key: APP_ENV
Value: production

Key: LOG_FORMAT
Value: json

Key: LOG_LEVEL
Value: info

Key: CORS_ORIGINS
Value: https://fontis-voice-agent.onrender.com

Key: API_RATE_LIMIT
Value: 100
```

**⚠️ Replace placeholders:**
- `YOUR_WEBHOOK_SECRET_FROM_VAPI_DASHBOARD`
- `YOUR_JOTFORM_API_KEY`
- `YOUR_JOTFORM_FORM_ID`

---

### **Step 6: Deploy**

1. Scroll to bottom
2. Click **"Create Web Service"**
3. Wait 5-10 minutes for:
   - Build (Docker image)
   - Deploy (Start container)
   - Health check (Verify `/health` endpoint)

**Watch the logs** on the deployment page to monitor progress.

---

### **Step 7: Get Your Production URL**

Once deployed successfully:

1. Look for: **"Your service is live 🎉"**
2. Your URL: `https://fontis-voice-agent.onrender.com`
3. Test it:
   ```bash
   curl https://fontis-voice-agent.onrender.com/health
   ```

Expected response:
```json
{
  "status": "healthy",
  "environment": "production",
  "version": "0.1.0",
  "timestamp": 1234567890
}
```

---

## 🔧 **Step 8: Update Vapi Dashboard**

Now update your Vapi configuration with the production URL:

### **8.1: Update Server URL**
```
Vapi Dashboard → Assistant → Settings → Server URL:
https://fontis-voice-agent.onrender.com/vapi/webhooks
```

### **8.2: Update All 19 Function URLs**

Replace `https://your-app-name.fly.dev` with `https://fontis-voice-agent.onrender.com`:

**Customer Functions:**
- `https://fontis-voice-agent.onrender.com/tools/customer/search`
- `https://fontis-voice-agent.onrender.com/tools/customer/details`
- `https://fontis-voice-agent.onrender.com/tools/customer/finance-info`

**Delivery Functions:**
- `https://fontis-voice-agent.onrender.com/tools/delivery/stops`
- `https://fontis-voice-agent.onrender.com/tools/delivery/next-scheduled`
- `https://fontis-voice-agent.onrender.com/tools/delivery/default-products`
- `https://fontis-voice-agent.onrender.com/tools/delivery/orders`
- `https://fontis-voice-agent.onrender.com/tools/delivery/frequencies`
- `https://fontis-voice-agent.onrender.com/tools/delivery/orders/search`

**Billing Functions:**
- `https://fontis-voice-agent.onrender.com/tools/billing/balance`
- `https://fontis-voice-agent.onrender.com/tools/billing/invoice-history`
- `https://fontis-voice-agent.onrender.com/tools/billing/invoice-detail`
- `https://fontis-voice-agent.onrender.com/tools/billing/payment-methods`
- `https://fontis-voice-agent.onrender.com/tools/billing/products`

**Contract Functions:**
- `https://fontis-voice-agent.onrender.com/tools/contracts/get-contracts`

**Route Functions:**
- `https://fontis-voice-agent.onrender.com/tools/routes/stops`

**Onboarding Functions:**
- `https://fontis-voice-agent.onrender.com/tools/onboarding/send-contract`
- `https://fontis-voice-agent.onrender.com/tools/onboarding/contract-status`

### **8.3: Update System Prompt**
```
Vapi Dashboard → Model → System Prompt:
[Copy entire content from vapi_system_prompt.md]
```

### **8.4: Update First Message**
```
Vapi Dashboard → Voice → First Message:
"Hi there! Thanks for calling Fontis Water. This call is being recorded for quality assurance. This is Mia — how can I help you today?"
```

---

## 🧪 **Step 9: Test Your Deployment**

### **Test 1: Health Check**
```bash
curl https://fontis-voice-agent.onrender.com/health
```

### **Test 2: Tool Endpoint (with auth)**
```powershell
$headers = @{
    "Authorization" = "Bearer Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
    "Content-Type" = "application/json"
}

Invoke-RestMethod `
  -Uri "https://fontis-voice-agent.onrender.com/tools/customer/search" `
  -Method POST `
  -Headers $headers `
  -Body '{"lookup":"Adam"}'
```

### **Test 3: Make a Real Call**
Call your Vapi number: **+1 (678) 303-4022**

---

## ⚡ **Step 10: Prevent Cold Starts (Keep Service Warm)**

Render's free tier spins down after **15 minutes of inactivity**.

**Solution:** Use UptimeRobot to ping your service every 5 minutes.

### **Setup UptimeRobot:**

1. Go to: **https://uptimerobot.com/**
2. Sign up (free, no credit card)
3. Click **"Add New Monitor"**
4. Configure:
   ```
   Monitor Type: HTTP(s)
   Friendly Name: Fontis Voice Agent
   URL: https://fontis-voice-agent.onrender.com/health
   Monitoring Interval: 5 minutes
   ```
5. Click **"Create Monitor"**

**✅ Your service will now stay warm 24/7!**

---

## 📊 **Monitoring & Logs**

### **View Logs:**
1. Render Dashboard → Your service → **"Logs"** tab
2. Real-time streaming logs
3. Filter by severity

### **View Metrics:**
1. Render Dashboard → Your service → **"Metrics"** tab
2. CPU, Memory, Request count

### **Health Status:**
1. Render Dashboard → Your service
2. Look for green **"Live"** status

---

## 🔄 **Updating Your App**

### **Option 1: Auto-Deploy (Recommended)**
```bash
# Just push to GitHub:
git add .
git commit -m "Update: Fixed bug"
git push

# Render automatically redeploys!
```

### **Option 2: Manual Deploy**
1. Render Dashboard → Your service
2. Click **"Manual Deploy"** → **"Deploy latest commit"**

---

## 🚨 **Troubleshooting**

### **Issue: Build fails**
- Check **"Logs"** tab for error messages
- Common fix: Update `pyproject.toml` dependencies
- Verify `Dockerfile` syntax

### **Issue: Service shows "Unhealthy"**
- Check logs: `curl https://fontis-voice-agent.onrender.com/health`
- Verify environment variables are set
- Check if port 10000 is used in Dockerfile

### **Issue: 401 Unauthorized on tool calls**
- Verify `INTERNAL_API_KEY` matches in Render and Vapi
- Check Authorization header format: `Bearer YOUR_KEY`

### **Issue: Service is slow (cold start)**
- First request after 15min idle takes ~30 seconds
- Solution: Use UptimeRobot keep-alive (see Step 10)

---

## 💰 **Render Free Tier Limits**

| Resource | Limit | Your Usage |
|----------|-------|------------|
| **Web Services** | 1 free | ✅ Within limit |
| **Build Hours** | 500/month | ✅ ~5 hours/month |
| **Bandwidth** | 100GB/month | ✅ ~1-5GB/month |
| **Build Minutes** | Unlimited | ✅ No limit |
| **Spin Down** | After 15min idle | ⚠️ Use keep-alive |

**Your app will stay within free tier!** 🎉

---

## ✅ **Deployment Checklist**

- [ ] Code pushed to GitHub
- [ ] Render account created (no credit card)
- [ ] Web service created
- [ ] All 15+ environment variables added
- [ ] Service deployed successfully
- [ ] Health endpoint returns 200 OK
- [ ] Vapi dashboard updated (server URL + 19 functions)
- [ ] System prompt pasted into Vapi
- [ ] First message updated in Vapi
- [ ] UptimeRobot keep-alive configured
- [ ] Test call to +1 (678) 303-4022 successful

---

## 🎉 **You're Live!**

Your Fontis Voice Agent is now deployed on Render.com!

**Production URL:** `https://fontis-voice-agent.onrender.com`

**Next Steps:**
1. Monitor first few calls
2. Check logs for any errors
3. Adjust system prompt if needed
4. Share Vapi number with team

**Questions?** Check Render docs: https://render.com/docs

---

**Deployed successfully?** 🚀 You're ready to handle customer calls!

