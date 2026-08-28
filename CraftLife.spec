# PyInstaller spec — onedir Windows release with web/dist embedded.
# Generated for P8; run: pyinstaller --noconfirm CraftLife.spec
# Do not use --optimize 2 / --strip (google.generativeai docstring crash).
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None
ROOT = Path(SPECPATH).resolve()
WEB_DIST = ROOT / "web" / "dist"
ICONS = ROOT / "icons"

datas = []
if WEB_DIST.is_dir():
    datas.append((str(WEB_DIST), "web/dist"))
if ICONS.is_dir():
    datas.append((str(ICONS), "icons"))

binaries = []
hiddenimports = [
    "api_server",
    "life_api",
    "studio_api",
    "web_shell",
    "cloud_api",
    "cloud_service",
    "cloud_config",
    "sync_service",
    "database",
    "food_data",
    "holidays",
    "translations",
    "learning_helper",
    "mathtools",
    "music_downloader",
    "updater",
    "applog",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
]
for pkg in (
    "PyQt6",
    "google.generativeai",
    "google.genai",
    "supabase",
):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        try:
            hiddenimports += collect_submodules(pkg)
        except Exception:
            pass

a = Analysis(
    [str(ROOT / "MainPyQt6.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="CraftLife",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICONS / "craftlife.ico") if (ICONS / "craftlife.ico").is_file() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CraftLife",
)
