"""CraftLife — music_downloader.py
Pencarian & unduhan musik dari internet (YouTube via yt-dlp) di background thread.
Konversi ke MP3 bila ffmpeg tersedia; bila tidak, unduh format audio asli (m4a/dll).
"""
import os
import re
import shutil
from pathlib import Path

# Qt (QThread/pyqtSignal) hanya diperlukan untuk backend desktop PyQt.
# Di web/headless, import ini skip agar modul tetap bisa dipakai (search/download via API).
try:
    from PyQt6.QtCore import QThread, pyqtSignal
except Exception:
    QThread = None
    pyqtSignal = None

try:
    import yt_dlp
    YT_AVAILABLE = True
except Exception:
    YT_AVAILABLE = False


def get_download_dir() -> str:
    d = Path.home() / "Music" / "CraftLife"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


# ── Opsi yt-dlp yang tangguh terhadap 403 (anti-bot YouTube) ──────────────────
# YouTube rajin memblokir client `web`/`web_embed` (HTTP 403: Forbidden pada
# extract_info/unduhan). Strategi yang umum dipakai & didukung yt-dlp:
#   * set header browser-like (User-Agent, Accept, Accept-Language),
#   * coba beberapa player_client selain web (android, ios, tv, web_safari, mweb)
#     sebagai fallback — cukup dipakai di sini tanpa menipu "sukses" bila tetap gagal,
#   * aktifkan retries agar transient error (403 sementara) dicoba ulang.
# Error asli tetap dibiarkan sampai ke caller (tidak di-swallow).
_MOBILE_YOUTUBE = frozenset(("android", "ios", "tv", "web_safari", "mweb", "web_embedded"))
_DEFAULT_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Mode": "navigate",
}


def _build_opts(download: bool, target_dir: str = None, progress_hook=None) -> dict:
    """Buat opsi yt-dlp yang dipakai bersama oleh worker & job API."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "http_headers": dict(_DEFAULT_HTTP_HEADERS),
        "retries": 3,
        "fragment_retries": 3,
        "extractor_retries": 3,
        # Fallback client selain default 'web' guna menghindari 403.
        "extractor_args": {"youtube": {"player_client": list(_MOBILE_YOUTUBE)}},
    }
    if download:
        opts.update({
            "outtmpl": os.path.join(target_dir or get_download_dir(), "%(title)s.%(ext)s"),
            "format": "bestaudio/best",
        })
        if has_ffmpeg():
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
        else:
            opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best"
    else:
        opts["extract_flat"] = "in_playlist"
    if progress_hook:
        opts["progress_hooks"] = [progress_hook]
    return opts


if QThread is not None:
    class MusicSearchWorker(QThread):
        """Cari musik via yt-dlp (ytsearch) tanpa memblokir UI."""
        done = pyqtSignal(list)

        def __init__(self, query, parent=None):
            super().__init__(parent)
            self.query = query

        def run(self):
            results = []
            if YT_AVAILABLE and self.query.strip():
                try:
                    opts = _build_opts(download=False)
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(f"ytsearch10:{self.query.strip()}", download=False)
                    for e in (info or {}).get("entries") or []:
                        vid = e.get("id") or ""
                        results.append({
                            "id": vid,
                            "title": e.get("title") or "",
                            "uploader": e.get("uploader") or e.get("channel") or "",
                            "duration": e.get("duration") or 0,
                            "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else ""),
                        })
                except Exception:
                    results = []
            self.done.emit(results)


if QThread is not None:
    class MusicDownloadWorker(QThread):
        """Unduh audio dari URL (YouTube dll.) ke folder unduhan, lalu laporkan path."""
        progress = pyqtSignal(str)
        done = pyqtSignal(str, str)  # path_final, error

        def __init__(self, url, target_dir=None, parent=None):
            super().__init__(parent)
            self.url = url
            self.dir = target_dir or get_download_dir()

        def run(self):
            if not YT_AVAILABLE:
                return self.done.emit("", "yt-dlp")

            def hook(d):
                if d.get("status") == "downloading":
                    self.progress.emit(str(d.get("_percent_str") or "").strip())

            opts = _build_opts(download=True, target_dir=self.dir, progress_hook=hook)
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=True)
                    if not info:
                        return self.done.emit("", "empty")
                    path = ydl.prepare_filename(info)
                    if has_ffmpeg():
                        path = re.sub(r"\.[A-Za-z0-9]+$", "", path) + ".mp3"
                    if not os.path.exists(path):
                        return self.done.emit("", "missing_file")
                    return self.done.emit(path, "")
            except Exception as exc:
                return self.done.emit("", str(exc))


import threading
import uuid

_jobs: dict = {}
_jobs_lock = threading.Lock()

# A02: cache metadata berkas (path → (mtime, meta)) — batch track-meta tidak membaca
# ulang tag berulang kali saat drawer lirik/music view meminta metadata yang sama.
_META_CACHE: dict = {}
_META_LOCK = threading.Lock()


def search_music(query: str) -> list:
    results = []
    if not (YT_AVAILABLE and (query or "").strip()):
        return results
    try:
        opts = _build_opts(download=False)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{query.strip()}", download=False)
        for e in (info or {}).get("entries") or []:
            vid = e.get("id") or ""
            results.append({
                "id": vid,
                "title": e.get("title") or "",
                "uploader": e.get("uploader") or e.get("channel") or "",
                "duration": e.get("duration") or 0,
                "url": e.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else ""),
            })
    except Exception:
        results = []
    return results


def _read_metadata(path: str) -> dict:
    """Baca metadata audio (title/artist/album/duration) via mutagen bila ada;
    fallback ke nama file bila tidak. Meniru _MetadataWorker PyQt."""
    meta = {"title": "", "artist": "", "album": "", "duration": 0}
    try:
        from mutagen import File
        f = File(path)
        if f is not None:
            for tag_key, out_key in (("title", "title"), ("artist", "artist"), ("album", "album")):
                val = None
                # mutagen: info di tag (TIT2/TPE1/TALB) atau dict custom
                try:
                    val = f.get(tag_key)
                    if val is None and hasattr(f, "tags") and f.tags:
                        mapping = {"title": "TIT2", "artist": "TPE1", "album": "TALB"}
                        val = f.tags.get(mapping.get(tag_key))
                except Exception:
                    val = None
                if val:
                    meta[out_key] = str(val)
            meta["duration"] = round(float(getattr(f.info, "length", 0) or 0))
    except Exception:
        meta = {"title": "", "artist": "", "album": "", "duration": 0}
    if not meta["title"]:
        stem = Path(path).stem
        # "Artist - Title" juga umum; kalau tidak, pakai nama file
        meta["title"] = stem
        if " - " in stem:
            a, t = stem.split(" - ", 1)
            if not meta["artist"]:
                meta["artist"] = a.strip()
            meta["title"] = t.strip()
    return meta


AUDIO_EXTS = (".mp3", ".m4a", ".ogg", ".wav", ".opus", ".flac")

# A02: batas listing library (dulu keras 80 → berkas lama kehilangan metadata →
# lirik tidak punya DURASI → pencarian lirik salah versi). Dapat diatur operator.
DEFAULT_LIB_LIMIT = 500


def lib_limit() -> int:
    """Batas jumlah berkas di /api/music/library (env CRAFTLIFE_MUSIC_LIB_LIMIT)."""
    try:
        val = int(os.environ.get("CRAFTLIFE_MUSIC_LIB_LIMIT") or DEFAULT_LIB_LIMIT)
    except (TypeError, ValueError):
        val = DEFAULT_LIB_LIMIT
    return max(1, min(val, 5000))


def _meta_cache_get(path: str, mtime: float):
    hit = _META_CACHE.get(path)
    if hit and abs(hit[0] - mtime) < 1e-6:
        return hit[1]
    return None


def _meta_cache_put(path: str, mtime: float, meta: dict) -> dict:
    with _META_LOCK:
        if len(_META_CACHE) > 4000:      # jaga memori tetap kecil
            _META_CACHE.clear()
        _META_CACHE[path] = (mtime, meta)
    return meta


def _item_for(path: Path) -> dict:
    """Satu baris library: nama/path/size + metadata (title/artist/album/duration)."""
    st = path.stat()
    item = {"name": path.name, "path": str(path), "size": st.st_size, "mtime": st.st_mtime}
    item.update(_read_metadata(str(path)))
    item["durationMs"] = int(round(float(item.get("duration") or 0) * 1000))
    return item


def list_library(limit=None) -> list:
    """Daftar berkas audio di folder library, terbaru dulu.

    A02: ``limit`` default = ``lib_limit()`` (500, env ``CRAFTLIFE_MUSIC_LIB_LIMIT``),
    bukan lagi keras 80. Setiap item memuat ``album``/``duration``/``durationMs``/
    ``mtime`` supaya pencarian lirik selalu punya durasi untuk mencocokkan versi.
    """
    folder = Path(get_download_dir())
    out = []
    if not folder.is_dir():
        return out
    if limit is None:
        limit = lib_limit()
    for p in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in AUDIO_EXTS:
            try:
                out.append(_item_for(p))
            except Exception:
                continue
    return out[: int(limit)]


def get_track_meta(file_path: str) -> dict:
    """Metadata 1 berkas (title/artist/album/duration) dengan cache berbasis mtime.

    Dipakai bila jalur playlist melewati batas listing library. Berkas di LUAR folder
    library tidak dibaca tag-nya (keamanan: API tidak boleh memprobe filesystem bebas);
    hanya nama berkas yang dikembalikan.
    """
    try:
        real = Path(os.path.realpath(file_path))
    except Exception:
        return {}
    if not real.is_file():
        return {}
    try:
        inside = str(real).startswith(str(Path(os.path.realpath(get_download_dir()))) + os.sep)
    except Exception:
        inside = False
    if not inside:
        return {"name": real.name, "path": str(real), "title": real.stem, "artist": "",
                "album": "", "duration": 0, "durationMs": 0}
    try:
        st = real.stat()
    except Exception:
        return {}
    cached = _meta_cache_get(str(real), st.st_mtime)
    if cached is not None:
        return dict(cached)
    meta = {"name": real.name, "path": str(real), "size": st.st_size, "mtime": st.st_mtime}
    meta.update(_read_metadata(str(real)))
    meta["durationMs"] = int(round(float(meta.get("duration") or 0) * 1000))
    return dict(_meta_cache_put(str(real), st.st_mtime, meta))


def get_track_meta_many(paths, max_paths: int = 200) -> list:
    """Batch metadata (dedupe, urutan dipertahankan, maks ``max_paths`` per request)."""
    out = []
    seen = set()
    for raw in paths or []:
        p = str(raw or "").strip()
        if not p or p in seen:
            continue
        seen.add(p)
        if len(out) >= int(max_paths):
            break
        try:
            meta = get_track_meta(p)
        except Exception:
            meta = {}
        if meta:
            out.append(meta)
    return out


def start_download_job(url: str) -> str:
    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"id": job_id, "percent": "0%", "path": "", "error": "", "done": False}
    t = threading.Thread(target=_run_download, args=(job_id, url), daemon=True)
    t.start()
    return job_id


def get_download_job(job_id: str) -> dict:
    with _jobs_lock:
        return dict(_jobs.get(job_id) or {"id": job_id, "error": "unknown_job", "done": True})


def _run_download(job_id: str, url: str) -> None:
    def set_job(**kw):
        with _jobs_lock:
            row = _jobs.get(job_id) or {}
            row.update(kw)
            _jobs[job_id] = row

    if not YT_AVAILABLE:
        set_job(done=True, error="yt-dlp_missing")
        return
    target = get_download_dir()

    def hook(d):
        if d.get("status") == "downloading":
            set_job(percent=str(d.get("_percent_str") or "").strip())

    opts = _build_opts(download=True, target_dir=target, progress_hook=hook)
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                set_job(done=True, error="empty")
                return
            path = ydl.prepare_filename(info)
            if has_ffmpeg():
                path = re.sub(r"\.[A-Za-z0-9]+$", "", path) + ".mp3"
            if not os.path.exists(path):
                set_job(done=True, error="missing_file")
                return
            set_job(done=True, path=path, percent="100%", error="")
    except Exception as exc:
        set_job(done=True, error=str(exc)[:300])
