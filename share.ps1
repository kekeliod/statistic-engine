# Starts the app and opens a PUBLIC link you can send to someone else.
#
#   powershell -ExecutionPolicy Bypass -File share.ps1
#
# The link works only while this window is open and your computer is awake.
# Close the window (or Ctrl+C) to take the link down.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$port = 8000
$backend = $null

function Cleanup {
  if ($backend -and -not $backend.HasExited) {
    Write-Host "`nStopping the app..." -ForegroundColor Yellow
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  }
}

function Stop-Existing {
  # free port 8000 in case a previous run didn't shut down cleanly
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*uvicorn*$port*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}

try {
  # --- 1. make sure everything is built ---
  if (-not (Test-Path "$root\backend\.venv")) {
    Write-Host "First run: one-time setup (this can take a few minutes)..." -ForegroundColor Yellow
    & powershell -ExecutionPolicy Bypass -File "$root\setup.ps1"
  }
  Write-Host "Building the latest version of the website..." -ForegroundColor Cyan
  Set-Location "$root\frontend"
  if (-not (Test-Path "node_modules")) { npm install }
  npm run build
  Set-Location $root

  # --- 2. start the server in the background ---
  Stop-Existing
  Write-Host "Starting the app on port $port..." -ForegroundColor Cyan
  $backend = Start-Process -FilePath "$root\backend\.venv\Scripts\python.exe" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$port") `
    -WorkingDirectory "$root\backend" -PassThru -WindowStyle Hidden

  $ready = $false
  for ($i = 0; $i -lt 40; $i++) {
    try { Invoke-RestMethod "http://127.0.0.1:$port/api/health" -TimeoutSec 2 | Out-Null; $ready = $true; break }
    catch { Start-Sleep -Seconds 1 }
  }
  if (-not $ready) { throw "The app did not start. Run  run-local.ps1  to see the error." }
  Write-Host "App is up." -ForegroundColor Green

  # --- 3. get the tunnel tool (cloudflared) ---
  $cfLocal = Join-Path $root "cloudflared.exe"
  $cfCmd = $null

  # look in: this folder, PATH, and the standard install locations
  $candidates = @(
    $cfLocal,
    "$env:ProgramFiles\cloudflared\cloudflared.exe",
    "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe"
  )
  foreach ($c in $candidates) { if ($c -and (Test-Path $c)) { $cfCmd = $c; break } }
  if (-not $cfCmd) {
    $onPath = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($onPath) { $cfCmd = $onPath.Source }
  }

  # not found anywhere -> download a single self-contained copy into this folder
  if (-not $cfCmd) {
    Write-Host "Downloading the link tool (cloudflared, ~50 MB) - one time only..." -ForegroundColor Yellow
    try {
      $url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      Invoke-WebRequest -Uri $url -OutFile $cfLocal -UseBasicParsing
      if ((Get-Item $cfLocal).Length -gt 1MB) { $cfCmd = $cfLocal }
    } catch {
      Write-Host "  Download failed: $($_.Exception.Message)" -ForegroundColor DarkYellow
      Remove-Item $cfLocal -ErrorAction SilentlyContinue
    }
  }

  Write-Host ""
  Write-Host "============================================================" -ForegroundColor Green
  Write-Host " Creating your public link - watch for the https:// address" -ForegroundColor Green
  Write-Host " below. Copy it and send it to whoever should try the app." -ForegroundColor Green
  Write-Host " Keep this window open the whole time they are using it." -ForegroundColor Green
  Write-Host "============================================================" -ForegroundColor Green
  Write-Host ""

  if ($cfCmd) {
    # Cloudflare quick tunnel - no account needed, no interstitial page, reliable.
    # Prints a https://<random>.trycloudflare.com URL. That is the link to share.
    & $cfCmd tunnel --no-autoupdate --url "http://localhost:$port"
  } else {
    # Last resort: uses Windows' built-in ssh. Prints a https://<random>.lhr.life URL.
    # Visitors may see a one-time "continue to this tunnel" page - that is normal.
    Write-Host "(Using the no-download fallback. If ssh asks to continue connecting, type: yes)" -ForegroundColor DarkGray
    & ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -R 80:localhost:$port nokey@localhost.run
  }
}
finally {
  Cleanup
}
