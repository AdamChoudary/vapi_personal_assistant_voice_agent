# Deploy to Fly.io Script
# Deploys the latest changes to production

Write-Host "`n🚀 Deploying Fontis Voice Agent to Fly.io`n" -ForegroundColor Cyan

# Check if logged in
Write-Host "1️⃣ Checking Fly.io authentication..." -ForegroundColor Yellow
$auth = fly auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Not logged in to Fly.io" -ForegroundColor Red
    Write-Host "   Run: fly auth login`n" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Logged in to Fly.io`n" -ForegroundColor Green

# Set environment variables (secrets)
Write-Host "2️⃣ Setting environment variables..." -ForegroundColor Yellow

$envVars = @{
    "FONTIS_API_KEY" = $env:FONTIS_API_KEY
    "FONTIS_BASE_URL" = "https://fontisweb.creatordraft.com/api/v1"
    "INTERNAL_API_KEY" = $env:INTERNAL_API_KEY
    "VAPI_API_KEY" = $env:VAPI_API_KEY
    "VAPI_PUBLIC_KEY" = $env:VAPI_PUBLIC_KEY
    "VAPI_ASSISTANT_ID" = $env:VAPI_ASSISTANT_ID
    "VAPI_PHONE_NUMBER" = $env:VAPI_PHONE_NUMBER
    "JOTFORM_API_KEY" = "d0b3c98a0557e5c58f4886be6862de32"
    "JOTFORM_FORM_ID" = "253003490094450"
    "JOTFORM_BASE_URL" = "https://api.jotform.com"
    "APP_ENV" = "production"
    "LOG_LEVEL" = "info"
    "LOG_FORMAT" = "json"
}

foreach ($key in $envVars.Keys) {
    $value = $envVars[$key]
    if ($value) {
        Write-Host "   Setting $key..." -NoNewline
        fly secrets set "$key=$value" --app fontis-voice-agent 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
        } else {
            Write-Host " ⚠️" -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ⚠️  $key not set in local environment" -ForegroundColor Yellow
    }
}

Write-Host "`n3️⃣ Deploying application..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes...`n"

fly deploy --app fontis-voice-agent

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n" + ("=" * 60) -ForegroundColor Green
    Write-Host "✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Green
    
    Write-Host "`n📋 Application Info:" -ForegroundColor Cyan
    fly status --app fontis-voice-agent
    
    Write-Host "`n🌐 Your production URL:" -ForegroundColor Cyan
    $appInfo = fly info --app fontis-voice-agent 2>&1
    $url = ($appInfo | Select-String -Pattern "https://.*\.fly\.dev").Matches.Value
    if ($url) {
        Write-Host "   $url" -ForegroundColor Green
        Write-Host "`n📝 Next Steps:" -ForegroundColor Yellow
        Write-Host "   1. Update VAPI with production URL:"
        Write-Host "      python scripts/sync_all_tools_to_vapi.py $url"
        Write-Host "`n   2. Test production:"
        Write-Host "      curl $url/health"
        Write-Host "`n   3. Test voice call: +1 (678) 303-4022`n"
    }
} else {
    Write-Host "`n❌ Deployment failed" -ForegroundColor Red
    Write-Host "   Check logs: fly logs --app fontis-voice-agent`n"
    exit 1
}

Write-Host ("=" * 60) + "`n"








