"""CraftLife — music_downloader.py
Pencarian & unduhan musik dari internet (YouTube via yt-dlp) di background thread.
Konversi ke MP3 bila ffmpeg tersedia; bila tidak, unduh format audio asli (m4a/dll).
"""
import os
import re
import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

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
