"""PyQt6 QWebEngineView shell that hosts the React UI after login.

A03.5 — UNDUHAN (audit export/download):
Qt WebEngine **tidak menyimpan unduhan apa pun** bila sinyal
``QWebEngineProfile.downloadRequested`` tidak disambungkan; permintaan unduhan
(blob, lampiran HTTP, atau tautan ber-``Content-Disposition: attachment``)
dibuang diam-diam tanpa pesan. Itulah sebabnya semua tombol ekspor di UI web
(Health & Food, tracker JSON, lirik .lrc, lampiran) tampak "tidak bisa" dan
tidak ada berkas di komputer. Modul ini kini punya ``DownloadManager`` yang:
  1. menyimpan setiap unduhan ke ``<folder unduhan>/CraftLife`` (dibuat otomatis),
  2. memberi nama unik ``nama (1).ext`` bila berkas sudah ada,
  3. memberi tahu UI (``window.craftlifeDownloadSaved``) berisi LOKASI berkas,
  4. menyediakan ``request_open_folder()`` untuk membuka folder dari UI web,
  5. fallback ``os.startfile``/``xdg-open`` saat shell Qt tidak aktif.
"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import sys

# Impor Qt dijaga: api_server (mode web/headless) boleh `import web_shell`
# untuk membaca folder unduhan tanpa PyQt6 terpasang. Yang butuh Qt tetap
# dipanggil hanya saat shell benar-benar dibuat.
try:  # pragma: no cover — bergantung lingkungan desktop
    from PyQt6.QtCore import QUrl, pyqtSignal, QTimer
    from PyQt6.QtGui import QDesktopServices, QIcon
    from PyQt6.QtWidgets import QMainWindow, QLabel

    HAS_QT = True
except Exception:  # headless / tanpa PyQt6
    HAS_QT = False
    QUrl = None          # type: ignore
    pyqtSignal = None    # type: ignore
    QTimer = None        # type: ignore
    QDesktopServices = None  # type: ignore
    QIcon = None         # type: ignore

    class QMainWindow:  # type: ignore
        pass

    class QLabel:  # type: ignore
        pass

from translations import get_text

HAS_WEBENGINE = False
WEBENGINE_IMPORT_ERROR = ""
QWebEngineView = None  # type: ignore


def _bundle_roots() -> list[str]:
    roots: list[str] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(meipass)
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        roots.append(exe_dir)
        roots.append(os.path.join(exe_dir, "_internal"))
    try:
        import PyQt6
        roots.append(os.path.dirname(PyQt6.__file__))
    except Exception:
        pass
    here = os.path.dirname(os.path.abspath(__file__))
    roots.append(here)
    out, seen = [], set()
    for r in roots:
        n = os.path.normpath(r)
        if n not in seen and os.path.isdir(n):
            seen.add(n)
            out.append(n)
    return out


def configure_webengine_env() -> str | None:
    """Point Qt at bundled Chromium (exe) before importing WebEngine."""
    names = (
        "QtWebEngineProcess.exe",
        os.path.join("PyQt6", "Qt6", "bin", "QtWebEngineProcess.exe"),
        os.path.join("PyQt6", "Qt", "bin", "QtWebEngineProcess.exe"),
        "QtWebEngineProcess",
        os.path.join("PyQt6", "Qt6", "libexec", "QtWebEngineProcess"),
    )
    found = None
    for root in _bundle_roots():
        for rel in names:
            path = os.path.join(root, rel)
            if os.path.isfile(path):
                found = path
                break
        if found:
            break
        # last-resort walk one level (can be slow; skip deep walk)
        try:
            for dirpath, _dirs, files in os.walk(root):
                if "QtWebEngineProcess.exe" in files or "QtWebEngineProcess" in files:
                    name = "QtWebEngineProcess.exe" if "QtWebEngineProcess.exe" in files else "QtWebEngineProcess"
                    found = os.path.join(dirpath, name)
                    break
                if dirpath.count(os.sep) - root.count(os.sep) > 4:
                    _dirs.clear()
        except Exception:
            pass
        if found:
            break
    if found:
        os.environ.setdefault("QTWEBENGINEPROCESS_PATH", found)
        proc_dir = os.path.dirname(found)
        os.environ["PATH"] = proc_dir + os.pathsep + os.environ.get("PATH", "")
        for extra in ("resources", "translations", os.path.join("..", "resources")):
            res = os.path.normpath(os.path.join(proc_dir, extra))
            if os.path.isdir(res):
                os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", res)
                break
    return found


def try_import_webengine() -> bool:
    global HAS_WEBENGINE, WEBENGINE_IMPORT_ERROR, QWebEngineView
    if HAS_WEBENGINE:
        return True
    configure_webengine_env()
    try:
        from PyQt6.QtWebEngineWidgets import QWebEngineView as _View
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage  # noqa: F401

        QWebEngineView = _View
        HAS_WEBENGINE = True
        WEBENGINE_IMPORT_ERROR = ""
        return True
    except Exception as exc:
        HAS_WEBENGINE = False
        WEBENGINE_IMPORT_ERROR = f"{type(exc).__name__}: {exc}"
        QWebEngineView = None
        return False


# ───────────────────────── A03.5: unduhan ke komputer ─────────────────────────
DOWNLOAD_SUBDIR = "CraftLife"
# Folder unduhan di-cache saat GUI thread menyiapkannya (QStandardPaths aman di sana).
_DOWNLOAD_FOLDER: str = ""
_OPEN_REQUESTS: "queue.Queue[str]" = queue.Queue()
_download_manager = None


def downloads_root() -> str:
    """Folder unduhan milik pengguna (env CRAFTLIFE_DOWNLOAD_DIR menimpanya)."""
    env = os.environ.get("CRAFTLIFE_DOWNLOAD_DIR")
    if env:
        return env
    home = os.path.expanduser("~")
    for name in ("Downloads", "Unduhan", "Download"):
        cand = os.path.join(home, name)
        if os.path.isdir(cand):
            return cand
    return home


def download_dir(create: bool = True) -> str:
    """Folder tujuan unduhan CraftLife: <unduhan>/CraftLife."""
    global _DOWNLOAD_FOLDER
    if not _DOWNLOAD_FOLDER:
        _DOWNLOAD_FOLDER = os.path.join(downloads_root(), DOWNLOAD_SUBDIR)
    if create:
        try:
            os.makedirs(_DOWNLOAD_FOLDER, exist_ok=True)
        except Exception:
            return downloads_root()
    return _DOWNLOAD_FOLDER


def set_download_dir(path: str) -> str:
    """Tetapkan folder unduhan (dipakai GUI thread via QStandardPaths)."""
    global _DOWNLOAD_FOLDER
    _DOWNLOAD_FOLDER = path
    return _DOWNLOAD_FOLDER


def sanitize_filename(name: str) -> str:
    """Bersihkan nama berkas (tanpa path, tanpa karakter ilegal Windows)."""
    base = os.path.basename((name or "").replace("\\", "/").split("/")[-1]).strip()
    base = "".join(ch for ch in base if ch not in '<>:"/\\|?*' and ord(ch) >= 32)
    base = base.strip(" .")
    return base or "craftlife-download"


def unique_path(folder: str, name: str) -> str:
    """Nama berkas unik di dalam folder: ``laporan.csv`` → ``laporan (1).csv``."""
    safe = sanitize_filename(name)
    stem, ext = os.path.splitext(safe)
    cand = os.path.join(folder, safe)
    idx = 1
    while os.path.exists(cand):
        cand = os.path.join(folder, f"{stem} ({idx}){ext}")
        idx += 1
    return cand


def open_folder_via_os(path: str) -> bool:
    """Buka folder/berkas tanpa Qt (mode web/dev): Windows/macOS/Linux."""
    target = path or download_dir()
    try:
        if sys.platform.startswith("win"):
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True
    except Exception:
        return False


def request_open_folder(path: str = "") -> bool:
    """Minta shell membuka folder unduhan (aman dipanggil dari thread server)."""
    _OPEN_REQUESTS.put(path or download_dir(create=False))
    return True


class DownloadManager:
    """Simpan unduhan WebEngine ke komputer pengguna + beri tahu UI."""

    def __init__(self):
        self.installed = False
        self.view = None
        self.folder = download_dir()
        self.last_name = ""
        self.last_path = ""
        self.count = 0
        self.failures = 0
        self._timer = None

    # ── pemasangan di GUI thread ───────────────────────────────────────────────
    def install(self, view) -> bool:
        if not HAS_QT or view is None:
            return False
        self.view = view
        ok = False
        try:
            from PyQt6.QtCore import QStandardPaths
            loc = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DownloadLocation)
            if loc:
                set_download_dir(os.path.join(loc, DOWNLOAD_SUBDIR))
                self.folder = download_dir()
        except Exception:
            self.folder = download_dir()
        try:
            profile = view.page().profile()
        except Exception:
            profile = None
        for prof in (profile, self._default_profile()):
            if prof is None:
                continue
            try:
                prof.downloadRequested.connect(self._on_download)
                ok = True
            except Exception:
                continue
        self.installed = ok
        # Timer GUI-thread untuk melayani permintaan "buka folder" dari api_server.
        if QTimer is not None:
            try:
                self._timer = QTimer(view)
                self._timer.setInterval(400)
                self._timer.timeout.connect(self._drain_open_requests)
                self._timer.start()
            except Exception:
                self._timer = None
        return ok

    @staticmethod
    def _default_profile():
        try:
            from PyQt6.QtWebEngineCore import QWebEngineProfile
            return QWebEngineProfile.defaultProfile()
        except Exception:
            return None

    # ── handler unduhan ───────────────────────────────────────────────────────
    def _suggested_name(self, download) -> str:
        for getter in ("suggestedFileName", "downloadFileName"):
            try:
                val = getattr(download, getter)()
                if val:
                    return sanitize_filename(val)
            except Exception:
                continue
        try:
            url = download.url().path() or ""
            if url and not url.startswith("/download") and not url.startswith("/blob"):
                return sanitize_filename(url)
        except Exception:
            pass
        return "craftlife-download"

    def _on_download(self, download) -> None:
        try:
            name = self._suggested_name(download)
            target = unique_path(self.folder, name)
            download.setDownloadDirectory(os.path.dirname(target))
            download.setDownloadFileName(os.path.basename(target))
            download.accept()
            self.last_name = os.path.basename(target)
            self.last_path = target
            self.count += 1
            print(f"[Download] mulai → {target}", flush=True)
            for sig in ("stateChanged", "finished", "isFinishedChanged"):
                try:
                    getattr(download, sig).connect(lambda *a, d=download: self._on_progress(d))
                except Exception:
                    continue
            # Beri tahu UI bahwa proses simpan dimulai (unggungan 400 ms sudah ada).
            self._notify_ui("start", self.last_name, self.last_path)
        except Exception as exc:  # pragma: no cover — jangan sampai crash UI
            print(f"[Download] gagal menyiapkan unduhan: {exc}", flush=True)
            try:
                download.cancel()
            except Exception:
                pass

    def _state_name(self, download) -> str:
        try:
            state = download.state()
        except Exception:
            return ""
        return str(getattr(state, "name", state) or "")

    def _on_progress(self, download) -> None:
        finished = False
        try:
            finished = bool(download.isFinished())
        except Exception:
            finished = False
        state = self._state_name(download)
        if not finished and state not in ("DownloadCompleted", "DownloadCancelled", "DownloadInterrupted"):
            return
        if state in ("DownloadCancelled", "DownloadInterrupted"):
            self.failures += 1
            reason = ""
            try:
                reason = download.interruptReasonString() or ""
            except Exception:
                reason = ""
            print(f"[Download] gagal: {self.last_name} {state} {reason}", flush=True)
            self._notify_ui("failed", self.last_name, reason)
            return
        exists = os.path.isfile(self.last_path)
        size = os.path.getsize(self.last_path) if exists else 0
        print(f"[Download] selesai → {self.last_path} ({size} byte)", flush=True)
        self._notify_ui("done", self.last_name, self.last_path)

    def _notify_ui(self, status: str, name: str, path: str) -> None:
        """Panggil window.craftlifeDownloadSaved/Failed di React (toast + lokasi file)."""
        if self.view is None:
            return
        try:
            page = self.view.page()
            payload_name = json.dumps(name or "")
            payload_path = json.dumps(path or "")
            payload_status = json.dumps(status or "done")
            page.runJavaScript(
                "(function(){try{"
                "if(window.craftlifeDownloadEvent){window.craftlifeDownloadEvent("
                f"{payload_status},{payload_name},{payload_path});"
                "}}catch(e){}})();"
            )
        except Exception:
            pass

    # ── "buka folder" dari UI web ─────────────────────────────────────────────
    def _drain_open_requests(self) -> None:
        while True:
            try:
                path = _OPEN_REQUESTS.get_nowait()
            except queue.Empty:
                break
            target = path or self.folder
            opened = False
            try:
                from PyQt6.QtCore import QUrl as _QUrl
                opened = bool(QDesktopServices.openUrl(_QUrl.fromLocalFile(target)))
            except Exception:
                opened = False
            if not opened:
                open_folder_via_os(target)
        # bersihkan permintaan lama bila timer hidup lebih lama dari window
        try:
            self._timer.isActive()
        except Exception:
            pass


def get_download_manager() -> "DownloadManager | None":
    return _download_manager


def install_download_handler(view) -> bool:
    """Pasang handler unduhan pada view WebEngine (dipanggil WebMainWindow)."""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager()
    return _download_manager.install(view)


def download_info() -> dict:
    """Info folder unduhan + unduhan terakhir (dipakai /api/system/downloads-info)."""
    mgr = _download_manager
    folder = (mgr.folder if mgr else download_dir())
    return {
        "dir": folder,
        "lastName": (mgr.last_name if mgr else ""),
        "lastPath": (mgr.last_path if mgr else ""),
        "active": bool(mgr and mgr.installed),
        "count": int(mgr.count if mgr else 0),
        "failures": int(mgr.failures if mgr else 0),
    }


def web_dist_candidates() -> list[str]:
    cands: list[str] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        cands.append(os.path.join(meipass, "web", "dist"))
    here = os.path.dirname(os.path.abspath(__file__))
    cands.append(os.path.join(here, "web", "dist"))
    cands.append(os.path.join(os.path.dirname(here), "web", "dist"))
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        cands.append(os.path.join(exe_dir, "web", "dist"))
        cands.append(os.path.join(exe_dir, "_internal", "web", "dist"))
    out: list[str] = []
    seen = set()
    for c in cands:
        n = os.path.normpath(c)
        if n not in seen:
            seen.add(n)
            out.append(n)
    return out


def web_dist_index() -> str | None:
    for root in web_dist_candidates():
        index = os.path.join(root, "index.html")
        if os.path.isfile(index):
            return index
    return None


def default_web_url() -> str:
    env = os.environ.get("CRAFTLIFE_WEB_URL")
    if env:
        return env
    # Always the Python API (serves web/dist). Do not point at Vite :3000 —
    # that port is empty unless `npm run dev` is running, which caused
    # ERR_CONNECTION_REFUSED in the WebEngine window.
    port = os.environ.get("CRAFTLIFE_API_PORT", "8765")
    return f"http://127.0.0.1:{port}/"


class WebMainWindow(QMainWindow):
    if pyqtSignal is not None:
        logout_signal = pyqtSignal()
    else:  # headless: atribut pengganti agar tidak AttributeError
        class _DummySignal:
            def emit(self, *args, **kwargs):
                return None

        logout_signal = _DummySignal()

    def __init__(self, user: dict, url: str, token: str | None = None, parent=None):
        super().__init__(parent)
        uid = user.get("id")
        lang = (user.get("language") or "id")
        self.setWindowTitle(get_text("web_shell_title", lang))
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "craftlife.ico")
        if not os.path.isfile(icon_path):
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                icon_path = os.path.join(meipass, "icons", "craftlife.ico")
        if os.path.isfile(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.resize(1280, 800)

        try_import_webengine()
        if not HAS_WEBENGINE or QWebEngineView is None:
            detail = WEBENGINE_IMPORT_ERROR or "-"
            msg = get_text("web_engine_missing_exe" if getattr(sys, "frozen", False) else "web_engine_missing", lang)
            box = QLabel(f"{msg}\n\n{detail}")
            box.setWordWrap(True)
            box.setStyleSheet("padding:24px;font-size:14px;")
            self.setCentralWidget(box)
            return

        view = QWebEngineView(self)
        qs = []
        if token:
            qs.append(f"token={token}")
        if uid is not None:
            qs.append(f"uid={uid}")
        full = url
        if qs:
            full += ("&" if "?" in url else "?") + "&".join(qs)
        # A03.5: WAJIB — tanpa handler ini Qt WebEngine membuang semua unduhan
        # (ekspor nutrisi, tracker JSON, lirik .lrc, lampiran) tanpa pesan apa pun.
        try:
            if install_download_handler(view):
                info = download_info()
                print(f"[Download] folder unduhan: {info['dir']}", flush=True)
        except Exception as exc:
            print(f"[Download] handler unduhan gagal dipasang: {exc}", flush=True)
        view.setUrl(QUrl(full))
        self.setCentralWidget(view)
        self._view = view

    def closeEvent(self, event):
        # P57: hentikan media halaman web SEBELUM window ditutup — audio
        # Chromium bisa terus bunyi setelah window hilang sampai page
        # benar-benar dibebaskan (bug #17: musik tetap main setelah logout).
        view = getattr(self, "_view", None)
        if view is not None:
            try:
                view.page().setAudioMuted(True)
            except Exception:
                pass
            try:
                view.page().runJavaScript(
                    "(window.craftlifeStopAllAudio && window.craftlifeStopAllAudio());"
                    "document.querySelectorAll('audio,video').forEach(function(e){e.pause();})"
                )
            except Exception:
                pass
            try:
                view.stop()
            except Exception:
                pass
        self.logout_signal.emit()
        super().closeEvent(event)
