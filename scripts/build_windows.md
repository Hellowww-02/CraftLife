# Build Windows release (P8 hybrid)

End users get **one folder** `dist/CraftLife/` with `CraftLife.exe`. They do **not** install Node or run `npm`.

## Prerequisites (developer PC only)

- Python 3.10+
- Node.js 20+ (only to compile `web/`)
- `pip install -r requirements.txt PyQt6-WebEngine pyinstaller`
- After build, `dist\CraftLife\_internal\web\dist\index.html` **and/or** `dist\CraftLife\web\dist\index.html` must exist, plus `QtWebEngineProcess.exe`.

## Command

From the repo root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

This:

1. `npm run build` → `web/dist`
2. PyInstaller `--onedir` via `CraftLife.spec` (`--add-data` equivalent: `web/dist`)
3. Copies `web/dist` beside the exe and under `_internal`
4. Output: `dist\CraftLife\CraftLife.exe`

Runtime: exe starts `api_server` on `127.0.0.1:8765` and `QWebEngineView` loads that URL (static files, **not** Vite :3000).

Fallback (dev / broken WebEngine): `CRAFTLIFE_WEB_UI=0` opens legacy PyQt pages. Do **not** delete those pages.

## Do not

- `--optimize 2` or `--strip`
- commit `.env` or `craftlife.db`
- overwrite `%APPDATA%\CraftLife\craftlife.db` on update
- `copy_qtwebengine.py` unless you were asked
- `npm audit fix --force`

## Dev (not for users)

```powershell
py api_server.py
cd web; npm run dev
py MainPyQt6.py
```
