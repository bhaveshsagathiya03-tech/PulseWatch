$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
Write-Host "`nPulseWatch — Windows startup" -ForegroundColor Cyan

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Host "Docker CLI was not found. Install Docker Desktop for Windows first." -ForegroundColor Red
  exit 1
}
docker compose version *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker Compose v2 is unavailable. Update Docker Desktop." -ForegroundColor Red
  exit 1
}
if (-not (Test-Path ".env")) {
  if (-not (Test-Path ".env.example")) { throw ".env.example is missing from the extracted project." }
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example. Review SESSION_SECRET before exposing this service." -ForegroundColor Yellow
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
  Write-Host "Docker Desktop is not running. Start it, wait for the engine to become ready, then run this script again." -ForegroundColor Red
  exit 1
}
Write-Host "Validating Compose configuration…" -ForegroundColor DarkCyan
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw "docker compose config failed. Check docker-compose.yml and .env." }
Write-Host "Building and starting PulseWatch services…" -ForegroundColor DarkCyan
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw "Docker Compose could not start PulseWatch. Review the output above." }
Write-Host "Waiting for API health check…" -ForegroundColor DarkCyan
$ready = $false
for ($i = 0; $i -lt 45; $i++) {
  try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/health/ready" -TimeoutSec 2
    if ($response.status -eq "ready") { $ready = $true; break }
  } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
  Write-Host "Containers started, but API readiness was not confirmed. Inspect logs with: docker compose logs --tail=100" -ForegroundColor Yellow
} else {
  Write-Host "PulseWatch API is ready." -ForegroundColor Green
}
Write-Host "`nFrontend : http://localhost:3000" -ForegroundColor Green
Write-Host "Backend  : http://localhost:8000" -ForegroundColor Green
Write-Host "API docs : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Health   : http://localhost:8000/health/live" -ForegroundColor Green
Write-Host "`nStop the stack with stop-windows.bat or docker compose down." -ForegroundColor Gray
