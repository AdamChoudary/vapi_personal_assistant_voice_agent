# Project cleanup script
# Removes temporary files, cache, and debug artifacts

Write-Host "`n🧹 Cleaning Project...`n" -ForegroundColor Cyan

# Remove Python cache
Write-Host "Removing Python cache..." -ForegroundColor Yellow
Get-ChildItem -Recurse -Filter "__pycache__" -ErrorAction SilentlyContinue | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" -ErrorAction SilentlyContinue | Remove-Item -Force
Write-Host "✅ Python cache cleaned" -ForegroundColor Green

# Remove temporary files
Write-Host "`nRemoving temporary files..." -ForegroundColor Yellow
Remove-Item -Force -ErrorAction SilentlyContinue *.log, *.tmp, *.temp, .DS_Store
Write-Host "✅ Temporary files removed" -ForegroundColor Green

# Remove debug files
Write-Host "`nRemoving debug files..." -ForegroundColor Yellow
Remove-Item -Force -ErrorAction SilentlyContinue vapi_config_debug.json
Write-Host "✅ Debug files removed" -ForegroundColor Green

Write-Host "`n✅ Cleanup complete!`n" -ForegroundColor Green
Write-Host "Project is clean and ready for deployment." -ForegroundColor Cyan





