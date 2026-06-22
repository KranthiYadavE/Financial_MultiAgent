# Build all service images locally (learning / pre-push to registry)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $Root

$Tag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$Registry = if ($env:IMAGE_REGISTRY) { $env:IMAGE_REGISTRY } else { "ghcr.io/kranthiyadave/financial-multiagent" }

$services = @(
    @{ Name = "orchestrator"; Dockerfile = "services/orchestrator/Dockerfile" },
    @{ Name = "dlp-agent"; Dockerfile = "services/dlp_agent/Dockerfile" },
    @{ Name = "text-to-sql-agent"; Dockerfile = "services/text_to_sql_agent/Dockerfile" },
    @{ Name = "rag-agent"; Dockerfile = "services/rag_agent/Dockerfile" },
    @{ Name = "sql-worker"; Dockerfile = "services/workers/Dockerfile" },
    @{ Name = "mcp-server"; Dockerfile = "services/mcp_server/Dockerfile" }
)

Write-Host "Building images with tag: $Tag" -ForegroundColor Cyan

foreach ($svc in $services) {
    $image = "$Registry/$($svc.Name):$Tag"
    Write-Host "`n>>> Building $image" -ForegroundColor Green
    docker build -t $image -f $svc.Dockerfile .
}

Write-Host "`nDone. Images:" -ForegroundColor Cyan
docker images --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}" | Select-String "financial-multiagent"

Write-Host "`nPush to GHCR (after docker login ghcr.io):"
Write-Host "  `$env:IMAGE_REGISTRY='$Registry'; `$env:IMAGE_TAG='$Tag'; ./deploy/scripts/push-images.ps1"
