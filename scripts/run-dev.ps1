$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "Virtual environment not found. Run .\scripts\setup.ps1 first."
}

$BackendCommand = "Set-Location '$ProjectRoot\backend'; & '$Python' -m uvicorn app.main:app --reload --port 8000"
$Backend = Start-Process powershell -PassThru -ArgumentList "-NoExit", "-Command", $BackendCommand

try {
    Set-Location (Join-Path $ProjectRoot "frontend")
    npm run dev
}
finally {
    if (-not $Backend.HasExited) {
        Stop-Process -Id $Backend.Id
    }
}
