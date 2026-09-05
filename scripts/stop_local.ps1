$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$runDirectory = Join-Path $projectRoot ".local-run"
$pidFile = Join-Path $runDirectory "pids.json"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "Aucun terminal local enregistre n'est en cours." -ForegroundColor Yellow
    exit 0
}

$savedProcesses = Get-Content -LiteralPath $pidFile -Raw | ConvertFrom-Json
foreach ($processId in @($savedProcesses.backend, $savedProcesses.frontend)) {
    if (-not $processId) { continue }
    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($process) {
        Stop-Process -Id $processId -Force
    }
}

Remove-Item -LiteralPath $pidFile -Force
Write-Host "Market Terminal arrete." -ForegroundColor Green
