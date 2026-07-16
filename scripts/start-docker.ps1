param(
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$dockerPath = (Get-Command docker -ErrorAction SilentlyContinue).Source

if (-not $dockerPath) {
    $dockerPath = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
    if (-not (Test-Path $dockerPath)) {
        throw "Docker CLI was not found. Install Docker Desktop and restart PowerShell."
    }
}

try {
    & $dockerPath info | Out-Null
} catch {
    throw "Docker Engine is not running. Start Docker Desktop and make sure WSL 2 is installed."
}

Push-Location $projectRoot
try {
    if ($Rebuild) {
        # 先构建；构建失败时保留当前正在运行的工作台，避免无谓停服。
        & $dockerPath compose build
        if ($LASTEXITCODE -ne 0) {
            throw "Docker Compose failed to build the quant backend. Existing services were left unchanged."
        }
        & $dockerPath compose up -d --no-build --force-recreate --remove-orphans
    } else {
        & $dockerPath compose up -d
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed to start the quant services."
    }
} finally {
    Pop-Location
}

Write-Host "Workbench:       http://127.0.0.1:8765/templates/workbench.html"
Write-Host "Quant dashboard: http://127.0.0.1:8765/templates/quant-dashboard.html"
Write-Host "API health:      http://127.0.0.1:8765/api/health"
