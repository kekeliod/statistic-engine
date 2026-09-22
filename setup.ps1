# One-time setup. Run this once (double-click won't work - right-click > Run with
# PowerShell, or in a terminal:  powershell -ExecutionPolicy Bypass -File setup.ps1)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "== Backend: Python virtual environment + dependencies ==" -ForegroundColor Cyan
Set-Location "$root\backend"
if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "== Frontend: npm install + production build ==" -ForegroundColor Cyan
Set-Location "$root\frontend"
if (-not (Test-Path "node_modules")) { npm install }
npm run build

Set-Location $root
Write-Host ""
Write-Host "Setup complete. Next:" -ForegroundColor Green
Write-Host "  - To use it on this computer only:   powershell -ExecutionPolicy Bypass -File run-local.ps1"
Write-Host "  - To get a link to share:            powershell -ExecutionPolicy Bypass -File share.ps1"
