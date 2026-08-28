"""PyQt6 QWebEngineView shell that hosts the React UI after login."""
from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMainWindow, QLabel

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
    logout_signal = pyqtSignal()

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
        view.setUrl(QUrl(full))
        self.setCentralWidget(view)
        self._view = view

    def closeEvent(self, event):
        self.logout_signal.emit()
        super().closeEvent(event)
