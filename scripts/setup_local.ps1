$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$frontendRoot = Join-Path $projectRoot "frontend"
$envPath = Join-Path $projectRoot ".env"
$venvRoot = Join-Path $projectRoot ".venv"
$pythonPath = Join-Path $venvRoot "Scripts\python.exe"
$runDirectory = Join-Path $projectRoot ".local-run"
$logDirectory = Join-Path $projectRoot "logs"
$pidFile = Join-Path $runDirectory "pids.json"

function Test-HttpEndpoint([string]$url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    }
    catch {
        return $false
    }
}

function Find-PythonLauncher {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { return @($py.Source, "-3") }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) { return @($python.Source) }
    throw "Python 3.11 ou plus recent est requis. Installe-le depuis https://www.python.org/downloads/"
}

function Find-PackageManager {
    $pnpm = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
    if ($pnpm) { return $pnpm.Source }
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($npm) { return $npm.Source }
    throw "Node.js 20 ou plus recent est requis. Installe la version LTS depuis https://nodejs.org/"
}

function Wait-ForTerminal {
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ((Test-HttpEndpoint "http://127.0.0.1:8000/api/health") -and
            (Test-HttpEndpoint "http://127.0.0.1:3000")) {
            return $true
        }
        Start-Sleep -Seconds 1
    }
    return $false
}

Set-Location -LiteralPath $projectRoot
Write-Host ""
Write-Host "Flavio Market Terminal - installation locale" -ForegroundColor Cyan
Write-Host "Toutes les donnees passeront par ton PC sur 127.0.0.1." -ForegroundColor DarkGray

if (-not (Test-Path -LiteralPath $envPath) -or
    -not (Select-String -LiteralPath $envPath -Pattern '^LSE_API_KEY=.+$' -Quiet)) {
    & (Join-Path $PSScriptRoot "configure_key.ps1")
}

if (Test-Path -LiteralPath $pidFile) {
    & (Join-Path $PSScriptRoot "stop_local.ps1")
}

if ((Test-HttpEndpoint "http://127.0.0.1:8000/api/health") -or
    (Test-HttpEndpoint "http://127.0.0.1:3000")) {
    throw "Le port 3000 ou 8000 est deja utilise. Ferme l'autre application puis relance DEMARRER_LOCAL.bat."
}

$pythonLauncher = Find-PythonLauncher
$packageManager = Find-PackageManager

if (-not (Test-Path -LiteralPath $pythonPath)) {
    Write-Host "Creation de l'environnement Python..."
    $launcherArgs = @()
    if ($pythonLauncher.Count -gt 1) { $launcherArgs += $pythonLauncher[1] }
    $launcherArgs += @("-m", "venv", $venvRoot)
    & $pythonLauncher[0] @launcherArgs
}

Write-Host "Installation et verification du serveur..."
& $pythonPath -m pip install --disable-pip-version-check -r (Join-Path $projectRoot "requirements.txt")

Write-Host "Installation et verification de l'interface..."
Push-Location -LiteralPath $frontendRoot
try {
    if ([IO.Path]::GetFileName($packageManager) -ieq "pnpm.cmd") {
        & $packageManager install --frozen-lockfile
    }
    else {
        & $packageManager install
    }
}
finally {
    Pop-Location
}

New-Item -ItemType Directory -Path $runDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

$backendProcess = Start-Process -FilePath $pythonPath `
    -ArgumentList @("-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000") `
    -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logDirectory "backend.out.log") `
    -RedirectStandardError (Join-Path $logDirectory "backend.error.log")

$frontendProcess = Start-Process -FilePath $packageManager `
    -ArgumentList @("run", "dev", "--", "--hostname", "127.0.0.1", "--port", "3000") `
    -WorkingDirectory $frontendRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logDirectory "frontend.out.log") `
    -RedirectStandardError (Join-Path $logDirectory "frontend.error.log")

@{
    backend = $backendProcess.Id
    frontend = $frontendProcess.Id
} | ConvertTo-Json | Set-Content -LiteralPath $pidFile -Encoding utf8

Write-Host "Demarrage du terminal..."
if (-not (Wait-ForTerminal)) {
    & (Join-Path $PSScriptRoot "stop_local.ps1")
    throw "Le terminal n'a pas repondu dans le delai prevu. Consulte le dossier logs."
}

Start-Process "http://127.0.0.1:3000"
Write-Host ""
Write-Host "Terminal ouvert : http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "Pour l'arreter, lance ARRETER_LOCAL.bat." -ForegroundColor DarkGray
