# P8: Build CraftLife Windows onedir (React dist + PyInstaller).
# Run from repo root. End users do not need Node.
# ASCII-only so Windows PowerShell 5.1 can parse this file.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)

if (-not (Test-Path ".\web\package.json")) {
  throw "web/package.json missing"
}

Write-Host "==> npm build web UI"
if (Test-Path ".\translations.py") {
  python scripts\export_i18n.py
  New-Item -ItemType Directory -Force -Path ".\web\public\i18n" | Out-Null
  if (Test-Path ".\web\src\i18n\messages.json") {
    Copy-Item ".\web\src\i18n\messages.json" ".\web\public\i18n\messages.json" -Force
  }
}
Push-Location .\web
if (-not (Test-Path ".\node_modules")) {
  npm install
}
npm run build
Pop-Location

if (-not (Test-Path ".\web\dist\index.html")) {
  throw "web/dist/index.html not produced. Build the UI before packing the exe."
}

Write-Host "==> PyInstaller CraftLife.spec plus web/dist datas"
python -m pip install --upgrade pyinstaller
python -m pip install "PyQt6-WebEngine>=6.4.0"

python -c "from pathlib import Path; import PyQt6; p=list(Path(PyQt6.__file__).parent.rglob('QtWebEngineProcess.exe')); print(p[0] if p else ''); raise SystemExit(0 if p else 1)"
if ($LASTEXITCODE -ne 0) {
  throw "PyQt6-WebEngine missing QtWebEngineProcess.exe"
}

python -m PyInstaller --noconfirm --clean CraftLife.spec

$distRoot = Join-Path ".\dist" "CraftLife"
if (-not (Test-Path $distRoot)) {
  throw "dist\CraftLife missing after PyInstaller"
}

New-Item -ItemType Directory -Force -Path (Join-Path $distRoot "web") | Out-Null
Copy-Item -Recurse -Force ".\web\dist" (Join-Path $distRoot "web\dist")
$internal = Join-Path $distRoot "_internal"
if (Test-Path $internal) {
  New-Item -ItemType Directory -Force -Path (Join-Path $internal "web") | Out-Null
  Copy-Item -Recurse -Force ".\web\dist" (Join-Path $internal "web\dist")
}

$idxA = Join-Path $distRoot "web\dist\index.html"
$idxB = Join-Path $internal "web\dist\index.html"
if (-not ((Test-Path $idxA) -or (Test-Path $idxB))) {
  throw "P8 failed: web/dist/index.html not in dist\CraftLife"
}
if (Test-Path $idxA) { Write-Host "web/dist index -> $idxA" } else { Write-Host "web/dist index -> $idxB" }

$proc = Get-ChildItem -Path $distRoot -Recurse -Filter QtWebEngineProcess.exe -ErrorAction SilentlyContinue | Select-Object -First 1
if ($proc) {
  Write-Host "QtWebEngineProcess.exe -> $($proc.FullName)"
} else {
  Write-Warning "QtWebEngineProcess.exe NOT in dist. pip install PyQt6-WebEngine, then rebuild."
}

Write-Host "Done. Run dist\CraftLife\CraftLife.exe (no Node). Fallback: CRAFTLIFE_WEB_UI=0"
Write-Host "Do not copy .env into git. Do not run copy_qtwebengine.py unless asked."
