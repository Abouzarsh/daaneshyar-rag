$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==> Creating Python environment" -ForegroundColor Cyan
if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
}

& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -e ".\backend[dev]"

Write-Host "==> Installing web dependencies" -ForegroundColor Cyan
Push-Location frontend
npm ci
Pop-Location

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run: ollama pull qwen3:4b"
Write-Host "Run: ollama pull embeddinggemma"
Write-Host "Then: .\scripts\run-dev.ps1"
