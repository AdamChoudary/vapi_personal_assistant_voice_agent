# Development environment startup script
# Starts FastAPI server, Cloudflare tunnel, and frontend dashboard
# Then updates Vapi assistant and frontend configuration

Write-Host "`n🚀 Starting Development Environment`n" -ForegroundColor Green

# Check if processes are already running
$fastapi = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*run.py*" -or $_.CommandLine -like "*uvicorn*" }
$tunnel = Get-Process cloudflared -ErrorAction SilentlyContinue

if ($fastapi) {
    Write-Host "⚠️  FastAPI already running (PID: $($fastapi.Id))" -ForegroundColor Yellow
} else {
    Write-Host "▶️  Starting FastAPI server..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python run.py; Write-Host 'FastAPI stopped' -ForegroundColor Red"
    Start-Sleep -Seconds 3
    Write-Host "✓ FastAPI started on http://localhost:8000`n" -ForegroundColor Green
}

if ($tunnel) {
    Write-Host "⚠️  Cloudflared already running (PID: $($tunnel.Id))" -ForegroundColor Yellow
    Write-Host "   Detecting tunnel URL...`n" -ForegroundColor Cyan
} else {
    Write-Host "▶️  Starting Cloudflare Tunnel..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; .\cloudflared.exe tunnel --url http://localhost:8000; Write-Host 'Tunnel stopped' -ForegroundColor Red"
    Start-Sleep -Seconds 5
}

# Get tunnel URL
Write-Host "🔍 Detecting tunnel URL..." -ForegroundColor Cyan
$metrics = Invoke-WebRequest -Uri "http://127.0.0.1:20241/metrics" -UseBasicParsing -ErrorAction SilentlyContinue

if ($metrics) {
    $tunnelUrl = ($metrics.Content | Select-String -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com').Matches.Value | Select-Object -First 1
    
    if ($tunnelUrl) {
        Write-Host "✓ Tunnel URL: $tunnelUrl`n" -ForegroundColor Green
        
        # Update frontend .env
        Write-Host "🎨 Updating frontend configuration..." -ForegroundColor Cyan
        if (Test-Path "dashboard/.env") {
            $envContent = Get-Content "dashboard/.env"
            $newContent = $envContent -replace 'VITE_API_URL=.*', "VITE_API_URL=$tunnelUrl"
            $newContent | Set-Content "dashboard/.env"
            Write-Host "✓ Frontend .env updated`n" -ForegroundColor Green
        }
        
        # Update Vapi assistant
        Write-Host "🤖 Updating Vapi assistant configuration..." -ForegroundColor Cyan
        python scripts/update_vapi_assistant.py $tunnelUrl
        
        # Start frontend
        Write-Host "`n🎨 Starting frontend dashboard..." -ForegroundColor Cyan
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\dashboard'; npm run dev"
        Write-Host "✓ Frontend starting on http://localhost:5173`n" -ForegroundColor Green
        
        Write-Host "`n" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "✅ DEVELOPMENT ENVIRONMENT READY" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "`n📋 Services:" -ForegroundColor Cyan
        Write-Host "  • Frontend:   http://localhost:5173"
        Write-Host "  • FastAPI:    http://localhost:8000"
        Write-Host "  • Public URL: $tunnelUrl"
        Write-Host "  • Health:     $tunnelUrl/health"
        Write-Host "  • API Docs:   http://localhost:8000/docs`n"
        Write-Host "📞 Test:" -ForegroundColor Cyan
        Write-Host "  • Open dashboard: http://localhost:5173"
        Write-Host "  • Call assistant: +16783034022`n"
        
    } else {
        Write-Host "❌ Could not extract tunnel URL from metrics" -ForegroundColor Red
    }
} else {
    Write-Host "❌ Cloudflared metrics not available. Is the tunnel running?" -ForegroundColor Red
    Write-Host "   Manually check: http://127.0.0.1:20241/metrics" -ForegroundColor Yellow
}


