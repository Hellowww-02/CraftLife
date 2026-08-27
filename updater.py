"""CraftLife — auto-updater (Supabase atau GitHub Releases).

Alur operator (publish rilis):
  SUMBER = "supabase":
    1. Build versi baru (PyInstaller --onedir).
    2. Zip ISI folder dist/CraftLife -> craftlife-X.Y.Z.zip (tanpa .env & craftlife.db).
    3. Upload zip ke bucket 'app-updates' + insert ke public.app_releases.
  SUMBER = "github"  (REKOMENDASI — egress GRATIS, tidak masuk kuota Supabase):
    1. Build + zip seperti di atas.
    2. Buat GitHub Release dengan tag = versi (mis. v1.2.0), lampirkan zip.
    3. Selesai. App membaca https://api.github.com/repos/<repo>/releases/latest.

Alur client:
  check_for_update()  -> info bila versi lebih baru (dengan backoff anti-loop), else None.
  download_release()  -> zip terverifikasi sha256 (bila tersedia).
  apply_downloaded()  -> ekstrak staging + updater batch (Windows), app lalu keluar.

PENTING anti-loop (penghemat cached egress):
  - Versi yang sama TIDAK di-download berulang: ada backoff (default 24 jam) +
    catatan status di _update_state.json di folder aplikasi.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

APP_VERSION = "1.2.0"
CHANNEL = "stable"
USER_AGENT = "CraftLifeDesktop-Updater/1.0"

# "supabase" = download dari Storage Supabase (masuk kuota cached egress).
# "github"   = download dari GitHub Releases (egress gratis, TIDAK masuk kuota).
UPDATE_SOURCE = "supabase"
GITHUB_REPO = "Hellowww-02/CraftLife"

# Jangan tanya/unduh versi yang sama berulang dalam rentang ini (detik).
RETRY_BACKOFF_SECONDS = 24 * 3600


def parse_version(value: str):
    parts = re.findall(r"\d+", str(value or ""))
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts[:4])


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS LOKAL — anti-loop & hemat egress
# ══════════════════════════════════════════════════════════════════════════════
_STATE_FILE = app_root() / "_update_state.json"


def _load_state() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _mark_attempt(version: str) -> None:
    state = _load_state()
    state.setdefault("attempts", {})[str(version)] = datetime.now(timezone.utc).isoformat()
    _save_state(state)


def _api_base():
    """(url, publishable_key) dari .env; None bila belum dikonfigurasi."""
    try:
        from cloud_config import load_cloud_config
        cfg = load_cloud_config()
        if cfg.url and cfg.publishable_key:
            return cfg.url.rstrip("/"), cfg.publishable_key
    except Exception:
        pass
    return None


def _rpc(name: str, payload: dict, timeout: int = 10):
    base = _api_base()
    if not base:
        raise RuntimeError("updater_not_configured")
    url, key = base
    import requests
    resp = requests.post(
        f"{url}/rest/v1/rpc/{name}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"updater http {resp.status_code}")
    return resp.json()


def _fetch_from_github(timeout: int = 10) -> dict | None:
    import requests
    resp = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    if resp.status_code != 200:
        return None
    rel = resp.json()
    version = (rel.get("tag_name") or "").lstrip("vV")
    if not version:
        return None
    assets = rel.get("assets") or []
    zip_asset = next((a for a in assets if (a.get("name") or "").lower().endswith(".zip")), None)
    return {
        "version": version,
        "notes": (rel.get("body") or "")[:4000],
        "storage_path": zip_asset.get("name") if zip_asset else "",
        "download_url": zip_asset.get("browser_download_url") if zip_asset else None,
        "sha256": "",
        "size_bytes": zip_asset.get("size") if zip_asset else 0,
    }


def _fetch_from_supabase(timeout: int = 10) -> dict | None:
    data = _rpc("latest_app_release", {"p_channel": CHANNEL}, timeout)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict) or not data.get("version"):
        return None
    base = _api_base()
    if base:
        data["download_url"] = (
            f"{base[0]}/storage/v1/object/public/app-updates/{data.get('storage_path') or ''}"
        )
    return data


def check_for_update(timeout: int = 10):
    """Return release dict bila ada versi lebih baru (dengan backoff anti-loop);
    selain itu None (diam saat offline / sudah dicoba baru-baru ini)."""
    try:
        info = _fetch_from_github(timeout) if UPDATE_SOURCE == "github" else _fetch_from_supabase(timeout)
    except Exception:
        return None
    if not info or not info.get("version"):
        return None
    version = str(info.get("version"))
    if not is_newer(version, APP_VERSION):
        return None
    # Anti-loop: versi yang sama jangan ditawarkan berulang dalam backoff.
    attempts = _load_state().get("attempts", {})
    last = attempts.get(version)
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            age = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if age < RETRY_BACKOFF_SECONDS:
                return None
        except Exception:
            pass
    return info


def download_release(info: dict, progress_cb=None) -> Path:
    """Unduh zip update ke temp & verifikasi sha256 (bila disediakan)."""
    import requests
    url = info.get("download_url")
    if not url:
        raise RuntimeError("updater_no_url")
    _mark_attempt(info.get("version", ""))
    dest = Path(tempfile.gettempdir()) / f"craftlife_update_{info.get('version', 'v')}.zip"
    expected = (info.get("sha256") or "").strip().lower()
    h = hashlib.sha256()
    done = 0
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": USER_AGENT}) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length") or info.get("size_bytes") or 0)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if not chunk:
                    continue
                fh.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress_cb and total:
                    try:
                        progress_cb(done, total)
                    except Exception:
                        pass
    if expected:
        actual = h.hexdigest()
        if actual != expected:
            dest.unlink(missing_ok=True)
            raise RuntimeError("updater_checksum")
    return dest


def _flatten_staging(staging: Path) -> None:
    entries = [p for p in staging.iterdir() if p.name != "__MACOSX"]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(staging / item.name))
        try:
            inner.rmdir()
        except OSError:
            pass


def _staging_dir() -> Path:
    return app_root() / "_update_staging"


def apply_downloaded(zip_path: Path, version: str) -> None:
    """Ekstrak paket baru, siapkan staging, lalu (Windows) jalankan updater batch."""
    staging = _staging_dir()
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(staging)
    _flatten_staging(staging)
    try:
        zip_path.unlink(missing_ok=True)
    except OSError:
        pass

    if os.name == "nt":
        bat = _write_updater_bat(staging)
        _launch_detached(f'cmd /c "{bat}"')
    else:
        root = app_root()
        protected = {".env", "craftlife.db", "craftlife.db-wal", "craftlife.db-shm", "_update_state.json"}
        for item in staging.iterdir():
            dst = root / item.name
            if dst.name in protected:
                continue
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)
        shutil.rmtree(staging, ignore_errors=True)


def _write_updater_bat(staging: Path) -> Path:
    root = app_root()
    bat = Path(tempfile.gettempdir()) / f"craftlife_update_{int(time.time())}.bat"
    if is_frozen():
        relaunch = f'start "" "{Path(sys.executable)}"'
    else:
        script = Path(sys.argv[0]).resolve() if (sys.argv and sys.argv[0]) else (root / "MainPyQt6.py")
        relaunch = f'start "" "{sys.executable}" "{script}"'
    pid = os.getpid()
    content = (
        "@echo off\r\n"
        "setlocal EnableDelayedExpansion\r\n"
        f"set PID={pid}\r\n"
        f"set SRC={staging}\r\n"
        f"set DST={root}\r\n"
        "set MAXWAIT=30\r\n"
        "set /a N=0\r\n"
        ":waitloop\r\n"
        "tasklist /FI \"PID eq %PID%\" /NH 2>nul | findstr /C:\"%PID%\" >nul\r\n"
        "if not errorlevel 1 (\r\n"
        "  ping 127.0.0.1 -n 2 >nul\r\n"
        "  set /a N+=1\r\n"
        "  if !N! LSS %MAXWAIT% goto waitloop\r\n"
        ")\r\n"
        "robocopy \"%SRC%\" \"%DST%\" /E /XF .env craftlife.db craftlife.db-wal craftlife.db-shm "
        "_update_state.json /XD backups logs learning_audio _update_staging /NFL /NDL /NJH /NJS /NP >nul\r\n"
        "if errorlevel 8 exit /b 1\r\n"
        "rd /s /q \"%SRC%\"\r\n"
        f"cd /d \"%DST%\"\r\n"
        f"{relaunch}\r\n"
        "endlocal\r\n"
        "exit /b 0\r\n"
    )
    bat.write_text(content, encoding="ascii", errors="ignore")
    return bat


def _launch_detached(command: str) -> None:
    flags = 0
    if os.name == "nt":
        flags = (getattr(subprocess, "DETACHED_PROCESS", 0)
                 | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    subprocess.Popen(command, shell=True, creationflags=flags, close_fds=True)
