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
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# v1.6.3 "Quality of Life" — commit phase A01–A14 (satu rilis):
#   A01–A03 lirik · A03.5 unduhan · A04–A08 Learning · A09–A12 Love Space · A13 Home · A14 rilis.
#   A08 (selesai 2026-09-15): sitasi sumber + grounding di jawaban AI, Audio Overview dua host
#   dengan suara mengikuti bahasa transkrip + pemutar MP3 interaktif (Range/seek), dan migrasi
#   dependency AI `google.generativeai` → `google.genai` (SDK lama end-of-support).
#   A09 (selesai 2026-09-16): Love Space → tab Plans — catatan acara yang dulu mustahil diisi,
#   edit acara, Special Day dengan pengulangan tahunan + pengingat H-n, hitung mundur, dan
#   hari istimewa otomatis dari profil. Migrasi SQLite otomatis (6 kolom relationship_events);
#   Supabase opsional lewat 20260916000000_phase_a09_love_special_days.sql.
#   A10 (selesai 2026-09-16): Love Space → tab Memories & Bucket List — kenangan kini bisa
#   diedit, diberi emoji pilihan, tag, bintang favorit, dan ditautkan ke foto galeri; bucket list
#   punya progres nyata, kategori, target tanggal (badge H-n/terlewat), catatan, prioritas, filter,
#   dan tombol "Simpan jadi kenangan" saat tercapai (idempoten). Migrasi SQLite otomatis (9 kolom
#   baru: 5 memories + 4 bucket_items, plus 2 indeks); Supabase opsional lewat
#   20260916010000_phase_a10_love_memories_bucket.sql.
#   A11 (selesai 2026-09-16): Love Space → tab connection/cycle/gallery diprofesionalkan.
#   Connection: riwayat jawaban (cari/filter kategori/favorit/jawab ulang), prompt favorit,
#   grafik tren mood 30/90 hari + skor koneksi, streak check-in. Cycle: riwayat siklus yang bisa
#   diedit + catatan + tombol "Jadikan pengingat" H-3/H-1 (idempoten), prediksi ovulasi/jendela
#   subur + badge keyakinan dari 3 siklus terakhir. Gallery: sampul album, jumlah & tanggal album,
#   aksi massal (pindah album/hapus/visibilitas) lewat satu endpoint, lightbox bernavigasi
#   keyboard (← → / Esc / zoom). Perbaikan bug: sync cloud penghapusan foto massal dulu no-op
#   karena `cloud_id` dibaca setelah baris dihapus. Migrasi SQLite otomatis (menstrual_cycles.updated_at,
#   love_albums.cover_photo_id + 2 indeks); Supabase opsional lewat
#   20260916020000_phase_a11_love_cycle_gallery_alignment.sql.
#   Paket baru yang WAJIB ada di mesin user: google-genai>=1.0.0, edge-tts>=6.1.0, gTTS>=2.5.0.
#   A12 (selesai 2026-09-16): Love Space → tab `overview` menjadi dashboard pasangan
#   (hero "bersama N hari / M tahun" dari tanggal jadian, kartu Hari istimewa berikutnya
#   + hitung mundur + tombol "Buat pengingat", cincin skor kedekatan + rincian check-in,
#   grid 6 statistik, aksi cepat) dan Special Day kini benar-benar berujung pada pengingat:
#   mesin `get_next_reminder_datetime` mengenal `repeat_type='yearly'` (29 Feb → 28 Feb),
#   ada endpoint idempoten `POST /api/love/events/<id>/create-reminder` (acara ATAU ulang
#   tahun/hari jadi dari profil), opsi **Tahunan** + input batas akhir di halaman Reminders
#   dengan badge "Tahunan · tiap {tanggal}", dan chip satu baris di Beranda. Migrasi SQLite
#   otomatis: `reminders.repeat_until` (kolom ini selama ini dirujuk kode tetapi belum pernah
#   ada), `reminders.source_ref` + indeks. Perbaikan bug dari uji A12: database BARU gagal
#   `init_db()` (indeks `love_albums` dibuat sebelum tabelnya — warisan A11), update reminder
#   yang tidak mengirim `repeat` menghapus pengulangan tahunan secara diam-diam, dan
#   `repeat_until`/`reminder_datetime` yang tidak valid membuat proses pengingat gagal.
#   A13 (selesai 2026-09-16): Home → Year Wrapped. Laporan ekonomi di dialog Wrapped tidak lagi
#   memakai "Rp" hardcoded: seluruh angka (pemasukan, pengeluaran, selisih bersih) lewat
#   `formatMoney(v, user.currency)` dari `web/src/utils/currency.ts` (satu-satunya formatter resmi),
#   ditambah chip mata uang aktif + catatan kurs kecil dari `/api/catalog/currency`. Seluruh teks
#   dialog kini i18n id+en (dulu hardcoded Indonesia). Polish laporan: kartu **Selisih bersih**
#   berwarna dinamis, **rasio tabungan**, rincian **per tipe** (habits/dailies/quests/sport dari
#   `by_type`), top habit dengan ikon + bar relatif, **pemilih tahun** (`GET /api/year-wrapped?year=`,
#   baru juga mengembalikan `years[]` dari `db.get_wrapped_years`), tombol **Salin ringkasan**
#   (clipboard) + **Unduh .txt**, confetti `canvas-confetti`, dan pemisahan **empty-state** dari
#   **error** (dulu keduanya tampil "belum ada aktivitas"). Di halaman Reminders, badge
#   **Tahunan · tiap {tanggal}** kini bisa diklik untuk langsung membuka dialog edit reminder itu.
#   Tidak ada migrasi (hanya membaca tabel yang sudah ada).
#   A15 (selesai 2026-09-16): perbaikan rail kiri halaman Learning. Ikon notebook kini benar-benar
#   tersimpan (`learning_notebooks.icon`/`description`/`updated_at`, ALTER otomatis di init_db),
#   `POST /api/learning/notebooks` meneruskan `icon`/`description`, dan `…/<id>/rename` menerima
#   `title`/`icon`/`description` secara parsial (mengganti ikon tidak mengosongkan judul). Rail kiri
#   menggambar satu avatar per notebook (emoji pilihan user, fallback inisial judul) dengan lebar
#   mengikuti token `--rail-w` (72/220 px), judul `truncate`, tombol **+ Notebook** ikut melebar, daftar
#   panjang bisa digulir. Dialog Ganti nama juga bisa mengganti emoji (pemilih `NB_EMOJI` dipakai bersama).
#   i18n: key baru `learning_icon_label` → total 4.325.
# v1.6.4 (dalam pengerjaan) — commit phase C01–C09:
#   C01 (selesai 2026-09-22): Learning shell baru ala NotebookLM — 3 panel sejajar
#   (Sumber ‖ Chat ‖ Studio) dengan divider seret + collapse (pengganti tombol preset
#   Sempit/Sedang/Lebar), preferensi v2 + migrasi otomatis, mobile tab tetap.
#   i18n: +5 key → total 4.330.
#   C02 (selesai 2026-09-22): multi-upload (input multiple + drag-and-drop + antrean
#   berurutan) 23 tipe berkas — dokumen terstruktur (xlsx/xls/pptx/csv/epub/rtf),
#   gambar via vision AI + audio via transkrip Gemini (butuh API key, else penanda);
#   berkas asli disimpan di learning_sources/<uid>/ + bisa diunduh/diekstrak-ulang;
#   migrasi SQLite otomatis (5 kolom + indeks); hapus sumber hanya menyentuh berkas
#   kelolaan app. i18n: +23 key → total 4.353.
#   C02-revisi (2026-09-22, hybrid): berkas asli pdf/gambar dilampirkan ke Gemini
#   saat chat/generate (maks 3, ≤20 MB); PDF scan lolos upload + warning; impor gagal
#   bersihkan yatim. i18n: +1 key → total 4.354.
#   C03 (selesai 2026-09-22): sumber URL di Web UI (website fetch+bersih, YouTube
#   transkrip API ganda + judul oEmbed, deteksi otomatis server-side); panduan 1–2
#   kalimat per sumber (AI backfill malas + kolom summary). i18n: +6 → total 4.360.
#   C04 (selesai 2026-09-22): saran chat kontekstual dari judul sumber + simpan
#   jawaban AI jadi catatan (lihat/salin/hapus per notebook). Field `savedNotes`.
#   i18n: +12 key → total 4.372.
#   C05 (selesai 2026-09-22): 4 output Studio baru (Briefing Doc, Data Table,
#   Infografik, Slide Deck) + ekspor CSV/HTML + warning AFC terminal dihilangkan
#   (disable eksplisit). i18n: +20 key → total 4.392.
#   Revisi C05 (2026-09-22): rumus LaTeX chat AI dirender KaTeX.
#   C06 (selesai 2026-09-22): database self-care — respons camelCase (ukuran tampil),
#   jadwal auto-clean mandiri, auto-clean perdana, rincian per tabel, checkpoint/
#   VACUUM manual + periodik. i18n: +10 key → total 4.402.
#   C07 (selesai 2026-09-23): auto-updater berfungsi — flatten staging multi-level
#   (dist/CraftLife/), abort bila exe absen + _update_apply.log, checksum digest
#   GitHub, check verbose (beda 'terbaru' vs 'gagal cek'), unduh latar untuk web.
#   i18n: +6 key → total 4.408.
#   C08 (selesai 2026-09-23): tanggal sinkron (today ticking, rollover ringan,
#   sync halaman) + streak habits benar (fail_streak nyata, mapping murni) +
#   indikator done. i18n: +1 key → total 4.409.
#   C09 (selesai 2026-09-23): finalisasi & rilis v1.6.4 — bump versi, sinkron
#   i18n 4 arah (4.409), README REVISI, RELEASE_NOTES, rekap fase, verifikasi
#   penuh + smoke hidup, satu commit + tag v1.6.4.
# v1.6.5 (selesai 2026-09-23): food database update — dedupe 850→774 (0
# duplikat), 9 koreksi gizi, 33 item baru (ciki/kerupuk/minuman), migrasi DB
# lama idempoten (sinkron kanonik + gabung duplikat semantik, log aman).
APP_VERSION = "1.6.5"
CHANNEL = "stable"
USER_AGENT = "CraftLifeDesktop-Updater/1.0"

# "supabase" = download dari Storage Supabase (masuk kuota cached egress).
# "github"   = download dari GitHub Releases (egress gratis, TIDAK masuk kuota).
UPDATE_SOURCE = "github"
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


def _clean_tag(tag: str) -> str:
    """C07 §10: bersihkan tag rilis ('v1.6.4' -> '1.6.4'; toleran 'v.1.6.3')."""
    return re.sub(r"^[vV\s.]+", "", str(tag or "")).strip()


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
    version = _clean_tag(rel.get("tag_name"))
    if not version:
        return None
    assets = rel.get("assets") or []
    zip_asset = next((a for a in assets if (a.get("name") or "").lower().endswith(".zip")), None)
    # C07 §10: GitHub menyertakan digest "sha256:..." per aset — pakai untuk verifikasi.
    sha256 = ""
    digest = str((zip_asset or {}).get("digest") or "")
    if digest.lower().startswith("sha256:"):
        sha256 = digest.split(":", 1)[1].strip().lower()
    return {
        "version": version,
        "notes": (rel.get("body") or "")[:4000],
        "storage_path": zip_asset.get("name") if zip_asset else "",
        "download_url": zip_asset.get("browser_download_url") if zip_asset else None,
        "sha256": sha256,
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


def _check_inner(timeout: int = 10):
    """Inti pemeriksaan update — melempar Exception agar pemanggil bisa
    membedakan 'tidak ada update' dari 'gagal memeriksa' (C07 §10)."""
    info = _fetch_from_github(timeout) if UPDATE_SOURCE == "github" else _fetch_from_supabase(timeout)
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


def check_for_update(timeout: int = 10):
    """Return release dict bila ada versi lebih baru (dengan backoff anti-loop);
    selain itu None (diam saat offline / sudah dicoba baru-baru ini)."""
    try:
        return _check_inner(timeout)
    except Exception:
        return None


def check_update_status(timeout: int = 10) -> dict:
    """Varian verbose untuk Web UI: {"update": info|None, "error": str|None}.

    Error jaringan/timeout dikembalikan sebagai pesan jelas agar UI tidak
    mengklaim 'sudah terbaru' saat sebenarnya gagal memeriksa (C07).
    """
    try:
        return {"update": _check_inner(timeout), "error": None}
    except Exception as e:
        msg = str(e) or "update_check_failed"
        low = msg.lower()
        if "timed out" in low or "timeout" in low:
            msg = "timeout: %s" % msg
        elif ("urlopen" in low or "nodename nor servname" in low
                or "getaddrinfo" in low or "connection" in low
                or "max retries" in low or "name resolution" in low):
            msg = "network_unreachable: %s" % msg
        elif low == "updater_not_configured":
            msg = "network_unavailable: %s" % msg
        return {"update": None, "error": msg}


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
    """C07 §10: naikkan isi paket berlapis (maks 4 level).

    Mengenali tata letak rilis resmi (isi dist/CraftLife di root zip, yang bisa
    ikut terzip sebagai folder 'dist/CraftLife/') + unwrap legacy satu-folder.
    Berhenti segera bila CraftLife.exe sudah di root staging.
    """
    for _ in range(4):
        try:
            entries = [p for p in staging.iterdir()
                       if p.name != "__MACOSX" and not p.name.startswith(".")]
        except OSError:
            return
        if any(p.is_file() and p.name.lower() == "craftlife.exe" for p in entries):
            return
        nested = staging / "dist" / "CraftLife"
        if nested.is_dir():
            for item in nested.iterdir():
                shutil.move(str(item), str(staging / item.name))
            shutil.rmtree(staging / "dist", ignore_errors=True)
            continue
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            inner = dirs[0]
            for item in inner.iterdir():
                shutil.move(str(item), str(staging / item.name))
            try:
                inner.rmdir()
            except OSError:
                pass
            continue
        return


def _staging_dir() -> Path:
    return app_root() / "_update_staging"


def _apply_log_path() -> Path:
    return app_root() / "_update_apply.log"


def _apply_log(msg: str) -> None:
    """C07 §10: catat jejak apply agar kegagalan update bisa didiagnosis."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(_apply_log_path(), "a", encoding="utf-8") as fh:
            fh.write(f"[{ts} UTC] {msg}\n")
    except OSError:
        pass


def apply_downloaded(zip_path: Path, version: str) -> None:
    """Ekstrak paket baru, siapkan staging, lalu (Windows) jalankan updater batch.

    C07 §10: ABORT dengan error jelas bila CraftLife.exe tidak ada setelah
    staging di-flatten (tata letak zip salah) — JANGAN timpa instalasi.
    Seluruh langkah dicatat di _update_apply.log (folder aplikasi).
    """
    staging = _staging_dir()
    _apply_log(f"apply start version={version} zip={zip_path}")
    try:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(staging)
        try:
            names = sorted(p.name for p in staging.iterdir())
        except OSError:
            names = []
        _apply_log(f"extracted entries: {names}")
        _flatten_staging(staging)
        exe = staging / "CraftLife.exe"
        if not exe.exists():
            try:
                names = sorted(p.name for p in staging.iterdir())
            except OSError:
                names = []
            _apply_log(f"ABORT updater_no_exe: CraftLife.exe tidak ada di staging {names}")
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError(
                "updater_no_exe: paket update tidak berisi CraftLife.exe "
                "(tata letak zip salah — harusnya isi dist/CraftLife di root)")
        _apply_log("exe check OK: CraftLife.exe ada di staging")
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass

        if os.name == "nt":
            bat = _write_updater_bat(staging, version)
            _apply_log(f"updater batch ditulis: {bat}")
            _launch_detached(f'cmd /c "{bat}"')
            _apply_log("updater batch diluncurkan (detached)")
        else:
            root = app_root()
            protected = {".env", "craftlife.db", "craftlife.db-wal", "craftlife.db-shm",
                         "_update_state.json", "_update_apply.log"}
            for item in staging.iterdir():
                dst = root / item.name
                if dst.name in protected:
                    continue
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)
            shutil.rmtree(staging, ignore_errors=True)
            _apply_log("apply selesai (posix copy)")
    except Exception as e:
        _apply_log(f"apply FAILED: {e}")
        raise


def _write_updater_bat(staging: Path, version: str = "") -> Path:
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
        "set LOG=%DST%\\_update_apply.log\r\n"
        f"echo [%date% %time%] CraftLife updater start {version} >> \"%LOG%\" 2>&1\r\n"
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
        "_update_state.json /XD backups logs learning_audio _update_staging /NFL /NDL /NJH /NJS /NP >> \"%LOG%\" 2>&1\r\n"
        "if errorlevel 8 exit /b 1\r\n"
        "echo [%date% %time%] robocopy exit=%errorlevel% >> \"%LOG%\" 2>&1\r\n"
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


# ══════════════════════════════════════════════════════════════════════════════
#  UNDUH LATAR — untuk polling progres Web UI (C07)
# ══════════════════════════════════════════════════════════════════════════════
_dl_lock = threading.Lock()
_dl_state = {"state": "idle", "done": 0, "total": 0,
             "version": "", "zip": "", "error": ""}


def download_status() -> dict:
    """Salinan status unduh saat ini (aman-thread)."""
    with _dl_lock:
        return dict(_dl_state)


def reset_download() -> dict:
    """Kembalikan status ke idle (dipanggil setelah apply/dismiss)."""
    with _dl_lock:
        _dl_state.update({"state": "idle", "done": 0, "total": 0,
                          "version": "", "zip": "", "error": ""})
        return dict(_dl_state)


def _dl_progress(done: int, total: int) -> None:
    with _dl_lock:
        _dl_state["done"] = done
        _dl_state["total"] = total


def start_download(info: dict) -> dict:
    """Mulai unduh rilis di background thread; idempoten saat downloading.

    Mengembalikan status langsung — Web UI mem-poll download_status().
    """
    with _dl_lock:
        if _dl_state.get("state") == "downloading":
            return dict(_dl_state)
        _dl_state.update({"state": "downloading", "done": 0, "total": 0,
                          "version": str((info or {}).get("version") or ""),
                          "zip": "", "error": ""})

    def _run():
        try:
            zip_path = download_release(info, progress_cb=_dl_progress)
        except Exception as e:
            with _dl_lock:
                _dl_state.update({"state": "error", "error": str(e) or "download_failed"})
            return
        with _dl_lock:
            _dl_state.update({"state": "ready", "zip": str(zip_path),
                              "done": _dl_state.get("total") or _dl_state.get("done")})

    threading.Thread(target=_run, name="craftlife-update-dl", daemon=True).start()
    return download_status()
