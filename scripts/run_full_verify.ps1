# Full end-to-end pipeline verification (Windows PowerShell)
# Run from project root: .\scripts\run_full_verify.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

Write-Host "`n=== Financial Multi-Agent — Full Verification ===`n" -ForegroundColor Cyan

# 1. Docker check
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Docker Desktop is not running." -ForegroundColor Red
    Write-Host "  1. Open Docker Desktop from Start menu"
    Write-Host "  2. Wait until it shows 'Engine running'"
    Write-Host "  3. Re-run this script"
    exit 1
}
Write-Host "  Docker OK" -ForegroundColor Green

# 2. Env file
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "  Created .env from .env.example"
}

# 3. Start lite stack (no ELK/Kafka — faster, less RAM)
Write-Host "`n[2/5] Starting services (lite stack)..." -ForegroundColor Yellow
docker compose -f docker-compose.lite.yml up -d --build
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "  Waiting 30s for health checks..."
Start-Sleep -Seconds 30

# 4. Load data
Write-Host "`n[3/5] Loading data (Postgres + Qdrant)..." -ForegroundColor Yellow
docker compose -f docker-compose.lite.yml --profile init run --rm data-init
if ($LASTEXITCODE -ne 0) { exit 1 }

# 5. Verify
Write-Host "`n[4/5] Running verification script..." -ForegroundColor Yellow
python scripts/verify_pipeline.py
$verifyExit = $LASTEXITCODE

# 6. Smoke test
Write-Host "`n[5/5] Sample chat request..." -ForegroundColor Yellow
$body = '{"message": "Show my last 5 transactions"}'
$response = Invoke-RestMethod -Uri "http://localhost:8000/chat" -Method Post -Body $body -ContentType "application/json"
Write-Host "  Intent: $($response.intent)"
Write-Host "  Answer: $($response.answer.Substring(0, [Math]::Min(200, $response.answer.Length)))"

Write-Host "`n=== Done ===" -ForegroundColor Cyan
Write-Host "  Orchestrator: http://localhost:8000/docs"
Write-Host "  Grafana:      http://localhost:3000  (admin/admin)"
Write-Host "  Prometheus:   http://localhost:9090"
Write-Host "  Qdrant:       http://localhost:6333/dashboard"

exit $verifyExit
