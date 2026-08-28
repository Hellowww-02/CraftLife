"""Copy Qt WebEngine Chromium helper + resources into a PyInstaller onedir tree."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path


def _qt_root() -> Path:
    import PyQt6

    root = Path(PyQt6.__file__).resolve().parent
    for name in ("Qt6", "Qt"):
        cand = root / name
        if cand.is_dir():
            return cand
    return root


def find_process() -> Path:
    hits = list(_qt_root().rglob("QtWebEngineProcess.exe"))
    if not hits:
        hits = list(PyQt6_dir().rglob("QtWebEngineProcess.exe"))
    if not hits:
        raise SystemExit(
            "QtWebEngineProcess.exe not found in PyQt6. "
            "Run: python -m pip install PyQt6-WebEngine"
        )
    return hits[0]


def PyQt6_dir() -> Path:
    import PyQt6

    return Path(PyQt6.__file__).resolve().parent


def copy_tree(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dest.exists():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        else:
            shutil.copytree(src, dest)
    else:
        shutil.copy2(src, dest)


def main(dist_root: str) -> None:
    dist = Path(dist_root).resolve()
    internal = dist / "_internal" if (dist / "_internal").is_dir() else dist
    proc = find_process()
    bin_dir = proc.parent
    qt_root = _qt_root()
    pkg = PyQt6_dir()

    targets = [
        internal / "QtWebEngineProcess.exe",
        internal / "PyQt6" / "Qt6" / "bin" / "QtWebEngineProcess.exe",
        dist / "QtWebEngineProcess.exe",
    ]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proc, t)

    for pattern in ("*WebEngine*", "Qt6WebEngine*.dll", "QtWebEngine*.dll"):
        for dll in bin_dir.glob(pattern):
            shutil.copy2(dll, internal / dll.name)
            dest_bin = internal / "PyQt6" / "Qt6" / "bin" / dll.name
            dest_bin.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dll, dest_bin)

    resources = qt_root / "resources"
    if resources.is_dir():
        copy_tree(resources, internal / "PyQt6" / "Qt6" / "resources")
        copy_tree(resources, internal / "resources")

    locales = qt_root / "translations" / "qtwebengine_locales"
    if locales.is_dir():
        copy_tree(locales, internal / "PyQt6" / "Qt6" / "translations" / "qtwebengine_locales")
        copy_tree(locales, internal / "qtwebengine_locales")

    print(f"Copied QtWebEngineProcess from {proc}")
    print(f"into {internal}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("usage: copy_qtwebengine.py dist/CraftLife")
    main(sys.argv[1])
