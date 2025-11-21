# Deploy to Fly.io with provided API keys
Write-Host "`n🚀 Deploying Fontis Voice Agent to Fly.io`n" -ForegroundColor Cyan

# Set environment variables from provided values
$env:FONTIS_API_KEY = "fk_XzaL3iEikKvSjPuhbk7NBbGMYoSMVeQHaN9jpq0d9vtUAn8rueZNVwluILy3"
$env:INTERNAL_API_KEY = "Igw7K6gNIBKiGh9FPbDZAhJAjFm_O3LNUWY_PBoN-mg"
$env:CORS_ORIGINS = "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"

# Check if fly is available
try {
    $flyCheck = & fly --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Fly CLI not available"
    }
} catch {
    Write-Host "❌ Fly CLI not found. Please install Fly CLI first:" -ForegroundColor Red
    Write-Host "   https://fly.io/docs/getting-started/installing-flyctl/" -ForegroundColor Yellow
    exit 1
}

# Check if logged in
Write-Host "1️⃣ Checking Fly.io authentication..." -ForegroundColor Yellow
$auth = fly auth whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Not logged in to Fly.io" -ForegroundColor Red
    Write-Host "   Run: fly auth login`n" -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Logged in to Fly.io`n" -ForegroundColor Green

# Set secrets
Write-Host "2️⃣ Setting environment variables..." -ForegroundColor Yellow

$secrets = @{
    "FONTIS_API_KEY" = $env:FONTIS_API_KEY
    "FONTIS_BASE_URL" = "https://fontisweb.creatordraft.com/api/v1"
    "INTERNAL_API_KEY" = $env:INTERNAL_API_KEY
    "CORS_ORIGINS" = $env:CORS_ORIGINS
    "APP_ENV" = "production"
    "LOG_LEVEL" = "info"
    "LOG_FORMAT" = "json"
}

foreach ($key in $secrets.Keys) {
    $value = $secrets[$key]
    Write-Host "   Setting $key..." -NoNewline
    $result = fly secrets set "$key=$value" --app fontis-voice-agent 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host " ✅" -ForegroundColor Green
    } else {
        Write-Host " ⚠️  Failed: $result" -ForegroundColor Yellow
    }
}

Write-Host "`n3️⃣ Deploying application..." -ForegroundColor Yellow
Write-Host "   This may take a few minutes...`n"

fly deploy --app fontis-voice-agent

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n" + ("=" * 60) -ForegroundColor Green
    Write-Host "✅ DEPLOYMENT SUCCESSFUL!" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Green
    Write-Host "`n🌐 Production URL: https://fontis-voice-agent.fly.dev`n" -ForegroundColor Cyan
} else {
    Write-Host "`n❌ Deployment failed" -ForegroundColor Red
    Write-Host "   Check logs: fly logs --app fontis-voice-agent`n" -ForegroundColor Yellow
    exit 1
}
