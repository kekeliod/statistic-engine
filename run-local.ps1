# Runs the whole app (API + website) as one server on this computer.
# Open the URL it prints in your browser. Ctrl+C to stop.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

if (-not (Test-Path "$root\backend\.venv")) {
  Write-Host "First run: doing one-time setup..." -ForegroundColor Yellow
  & powershell -ExecutionPolicy Bypass -File "$root\setup.ps1"
}
if (-not (Test-Path "$root\frontend\dist")) {
  Set-Location "$root\frontend"; npm run build; Set-Location $root
}

Set-Location "$root\backend"
Write-Host ""
Write-Host "App running at  http://localhost:8000" -ForegroundColor Green
Write-Host "(Press Ctrl+C to stop)"
Write-Host ""
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
