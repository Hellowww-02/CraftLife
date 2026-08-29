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
                    opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "noplaylist": True}
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
            use_ff = has_ffmpeg()
            opts = {
                "quiet": True, "no_warnings": True, "noplaylist": True,
                "outtmpl": os.path.join(self.dir, "%(title)s.%(ext)s"),
                "format": "bestaudio/best",
            }
            if use_ff:
                opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
            else:
                opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best"

            def hook(d):
                if d.get("status") == "downloading":
                    self.progress.emit(str(d.get("_percent_str") or "").strip())

            opts["progress_hooks"] = [hook]
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(self.url, download=True)
                    if not info:
                        return self.done.emit("", "empty")
                    path = ydl.prepare_filename(info)
                    if use_ff:
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


def search_music(query: str) -> list:
    results = []
    if not (YT_AVAILABLE and (query or "").strip()):
        return results
    try:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": "in_playlist", "noplaylist": True}
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


def list_library() -> list:
    folder = Path(get_download_dir())
    out = []
    if not folder.is_dir():
        return out
    for p in sorted(folder.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.suffix.lower() in (".mp3", ".m4a", ".ogg", ".wav", ".opus", ".flac"):
            item = {"name": p.name, "path": str(p), "size": p.stat().st_size}
            item.update(_read_metadata(str(p)))
            out.append(item)
    return out[:80]


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
    use_ff = has_ffmpeg()
    target = get_download_dir()
    opts = {
        "quiet": True, "no_warnings": True, "noplaylist": True,
        "outtmpl": os.path.join(target, "%(title)s.%(ext)s"),
        "format": "bestaudio/best",
    }
    if use_ff:
        opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}]
    else:
        opts["format"] = "bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best"

    def hook(d):
        if d.get("status") == "downloading":
            set_job(percent=str(d.get("_percent_str") or "").strip())

    opts["progress_hooks"] = [hook]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info:
                set_job(done=True, error="empty")
                return
            path = ydl.prepare_filename(info)
            if use_ff:
                path = re.sub(r"\.[A-Za-z0-9]+$", "", path) + ".mp3"
            if not os.path.exists(path):
                set_job(done=True, error="missing_file")
                return
            set_job(done=True, path=path, percent="100%", error="")
    except Exception as exc:
        set_job(done=True, error=str(exc)[:300])
