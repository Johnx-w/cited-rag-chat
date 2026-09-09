$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location (Join-Path $root "python")
$python = Join-Path $PWD ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
  throw "python\\.venv is missing. Create it with: py -3.13 -m venv python\\.venv"
}
& $python -m uvicorn app.server:app --host 127.0.0.1 --port 8000
