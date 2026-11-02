@echo off
REM ============================================================
REM  Start CraftLife with LAN access (phone companion mode)
REM
REM  Double-click ONCE before using the CraftLife Android app
REM  from a phone on the same WiFi. The local server becomes
REM  reachable from the LAN. Keep this window open while using
REM  the phone app. NOTE: everyone on the same WiFi can reach
REM  the server in this mode - home WiFi only, never public WiFi.
REM ============================================================
cd /d "%~dp0"
set CRAFTLIFE_API_HOST=0.0.0.0
echo.
echo === CraftLife (phone mode) ===
echo Type this into the phone app (Settings - Server):
ipconfig | findstr /i "IPv4"
echo   ...as  http://YOUR-IP:8765
echo.
if exist "%~dp0CraftLife.exe" (
  echo Starting CraftLife desktop, server open for the phone...
  start "" "%~dp0CraftLife.exe"
  pause
) else (
  echo CraftLife.exe not found - starting server only (source mode).
  python api_server.py
)
