$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot ".env"

Write-Host ""
Write-Host "Configuration London Strategic Edge" -ForegroundColor Cyan
Write-Host "La cle reste uniquement dans ce dossier local." -ForegroundColor DarkGray

$secureKey = Read-Host "Colle ta cle LSE (saisie masquee)" -AsSecureString
$keyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($keyPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) {
        throw "La cle LSE ne peut pas etre vide."
    }
    @(
        "LSE_API_KEY=$plainKey"
        "FRONTEND_ORIGIN=http://127.0.0.1:3000"
    ) | Set-Content -LiteralPath $envPath -Encoding utf8
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($keyPointer)
    $plainKey = $null
}

Write-Host "Cle enregistree localement dans .env." -ForegroundColor Green
