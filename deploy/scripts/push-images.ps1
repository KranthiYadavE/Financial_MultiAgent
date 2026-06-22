# Push built images to GitHub Container Registry (GHCR)
# Prerequisites:
#   1. docker login ghcr.io -u YOUR_GITHUB_USERNAME
#   2. Run deploy/scripts/build-images.ps1 first

$ErrorActionPreference = "Stop"
$Tag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "latest" }
$Registry = if ($env:IMAGE_REGISTRY) { $env:IMAGE_REGISTRY } else { "ghcr.io/kranthiyadave/financial-multiagent" }

$names = @("orchestrator", "dlp-agent", "text-to-sql-agent", "rag-agent", "sql-worker", "mcp-server")

foreach ($name in $names) {
    $image = "$Registry/${name}:$Tag"
    Write-Host "Pushing $image" -ForegroundColor Green
    docker push $image
}

Write-Host "`nPushed to $Registry" -ForegroundColor Cyan
