# applog.py
# -*- coding: utf-8 -*-
"""
applog.py — Structured logging untuk CraftLife.

Semua modul memakai logger ini agar jejak error tidak hilang:
  - File   : logs/craftlife.log (rotasi: 3 file × 1 MB)
  - Console: level INFO ke atas (untuk mode debug / saat run dari terminal)

Pemakaian:
    from applog import get_logger
    log = get_logger(__name__)
    log.info("Pesan info")
    log.exception("Gagal melakukan X")   # otomatis sertakan traceback
"""

import logging
import logging.handlers
import os
import sys


def get_log_dir() -> str:
    """Folder logs — di APPDATA untuk .exe, di folder skrip untuk development."""
    if getattr(sys, "frozen", False):
        appdata = os.getenv("APPDATA") or os.path.expanduser("~")
        base = os.path.join(appdata, "CraftLife")
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(base, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


_CONFIGURED = False


def _configure_root() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    root = logging.getLogger("craftlife")
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── File handler dengan rotasi (3 × 1 MB) ──
    try:
        fh = logging.handlers.RotatingFileHandler(
            os.path.join(get_log_dir(), "craftlife.log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except Exception:
        # Jika file log tidak bisa dibuat (permission, dll.) tetap lanjut
        pass

    # ── Console handler (INFO ke atas) ──
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(ch)


def get_logger(name: str = "app") -> logging.Logger:
    """Ambil logger anak dengan namespace craftlife.<name>."""
    _configure_root()
    short = name.rsplit(".", 1)[-1]
    return logging.getLogger(f"craftlife.{short}")
