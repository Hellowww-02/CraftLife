"""
CraftLife Desktop  —  main_pyqt6.py  v3.0  (all bugs fixed)
PyQt6 Windows / Linux / macOS
Install : pip install PyQt6
Run     : python main_pyqt6.py
"""
import matplotlib.pyplot as plt
from io import BytesIO
import tempfile

from PyQt6.QtWidgets import QToolButton

import json
import os
from datetime import datetime

import requests
import time as time_module

from multiprocessing.util import info
import sys, os
from turtle import done
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QScrollArea, QFrame,
    QTabWidget, QDialog, QProgressBar, QGridLayout, QTextEdit,
    QCheckBox, QStackedWidget, QSizePolicy, QGroupBox, QListWidget,
    QSpinBox, QGraphicsOpacityEffect, QRadioButton, QButtonGroup,
    QFormLayout, QMessageBox, QHeaderView,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QColor, QFont, QIcon

import database as db

import traceback
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

import sys, os

# ═══════════════════════════════════════════════════════════════════
#  OPTIONAL IMPORTS FOR EXPORT (Excel, Word, PDF, Charts)
# ═══════════════════════════════════════════════════════════════════
try:
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    from openpyxl.utils import get_column_letter
    from openpyxl.chart import BarChart, Reference
    from docx import Document
    from docx.shared import Inches, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    import matplotlib.pyplot as plt
    EXPORT_IMPORTS_OK = True
except ImportError as e:
    EXPORT_IMPORTS_OK = False
    print(f"Peringatan: Beberapa library ekspor tidak terinstall: {e}")

def resource_path(relative_path):
    """Mendapatkan path absolut untuk file, baik saat running dari source maupun setelah di-exe."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

import os
import sys

def get_appdata_session_path():
    """Mendapatkan path untuk session.json di AppData."""
    if getattr(sys, 'frozen', False):
        # Jika dijalankan sebagai .exe, simpan session di %APPDATA%\CraftLife
        appdata = os.getenv('APPDATA')
        base_dir = os.path.join(appdata, 'CraftLife')
        os.makedirs(base_dir, exist_ok=True)
        return os.path.join(base_dir, 'session.json')
    else:
        # Jika dijalankan sebagai skrip Python biasa, simpan di folder yang sama dengan skrip
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'session.json')

SESSION_FILE = get_appdata_session_path()

def get_icon_path(filename):
    """Mengembalikan path absolut ke file ikon, bekerja baik di development maupun PyInstaller .exe"""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, 'icons', filename)

def setup_error_handling():
    """Tangkap error global dan tulis ke Error.txt."""
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Error.txt")
    def handler(err_type, err_value, tb):
        err_text = "".join(traceback.format_exception(err_type, err_value, tb))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(err_text)
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("CraftLife Error")
        msg.setText(f"Terjadi kesalahan fatal!\n\n{err_value}")
        msg.setInformativeText("Detail error disimpan di Error.txt.\nSilakan laporkan ke developer.")
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        sys.exit(1)
    sys.excepthook = handler

# ══════════════════════════════════════════════════════════════════════════════
# ANIMATION POOL — prevents GC from killing animations mid-flight
# ══════════════════════════════════════════════════════════════════════════════
_anim_pool: list = []

def fade_in(widget, ms: int = 220):
    """Fade a widget from opacity 0 → 1. NEVER call on QMainWindow or QDialog directly."""
    try:
        if hasattr(widget, '_fading') and widget._fading:
            return
        widget._fading = True
        eff = QGraphicsOpacityEffect()
        widget.setGraphicsEffect(eff)
        a = QPropertyAnimation(eff, b"opacity")
        a.setDuration(ms)
        a.setStartValue(0.0)
        a.setEndValue(1.0)
        a.setEasingCurve(QEasingCurve.Type.OutCubic)
        _anim_pool.append(a)

        def _done():
            if a in _anim_pool:
                _anim_pool.remove(a)
            widget._fading = False
            # Optionally remove effect after animation to avoid paint warnings
            widget.setGraphicsEffect(None)

        a.finished.connect(_done)
        a.start()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
# SOUND ENGINE
# ══════════════════════════════════════════════════════════════════════════════
class SoundEngine:
    enabled: bool = True

    @staticmethod
    def _beep(freq: int, dur: int):
        if not SoundEngine.enabled:
            return
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(max(37, min(32767, freq)), max(30, dur))
        except Exception:
            pass

    @staticmethod
    def complete(): SoundEngine._beep(880, 60); SoundEngine._beep(1100, 80)
    @staticmethod
    def level_up():
        for f in [523, 659, 784, 1047]: SoundEngine._beep(f, 80)
    @staticmethod
    def buy(): SoundEngine._beep(600, 80); SoundEngine._beep(800, 80)
    @staticmethod
    def error(): SoundEngine._beep(200, 180)
    @staticmethod
    def boss_hit(): SoundEngine._beep(150, 200)
    @staticmethod
    def boss_dead():
        for f in [300, 500, 800, 1200]: SoundEngine._beep(f, 85)
    @staticmethod
    def click(): SoundEngine._beep(700, 30)
    @staticmethod
    def notify(): SoundEngine._beep(520, 50); SoundEngine._beep(720, 50)

SND = SoundEngine()

# ══════════════════════════════════════════════════════════════════════════════
# Time Synchronization with online server to prevent local time exploits (e.g. changing system clock to bypass timers)
# ══════════════════════════════════════════════════════════════════════════════
class TimeSync:
    """Sinkronisasi waktu dengan server online (anti-eksploitasi)"""
    _offset = 0
    _last_sync = 0
    _zone = "Asia/Jakarta"
    _last_attempt = 0        # waktu terakhir mencoba sync
    _backoff = 60            # delay awal 60 detik (naik eksponensial)

    @classmethod
    def sync(cls):
        """Sinkronkan waktu dengan server worldtimeapi.org (dengan backoff)"""
        now = time_module.time()
        # Jangan sync terlalu sering jika gagal
        if now - cls._last_attempt < cls._backoff:
            return False
        cls._last_attempt = now

        try:
            url = f"http://worldtimeapi.org/api/timezone/{cls._zone}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                server_unixtime = data['unixtime']
                local_unixtime = int(time_module.time())
                cls._offset = server_unixtime - local_unixtime
                cls._last_sync = now
                cls._backoff = 3600      # sukses, sync ulang setelah 1 jam
                return True
        except Exception as e:
            print(f"Time sync failed: {e}")
            # Exponential backoff: 60, 120, 240, 480, ... maksimal 3600 detik
            cls._backoff = min(cls._backoff * 2, 3600)
        return False

    @classmethod
    def get_current_time(cls):
        """Mendapatkan datetime objek dari waktu server yang sudah disinkronkan"""
        if cls._last_sync == 0:
            # Belum pernah sync, coba sync sekali
            cls.sync()
        local_now = time_module.time()
        server_now = local_now + cls._offset
        return datetime.fromtimestamp(server_now)

    @classmethod
    def get_formatted_time(cls):
        """Format waktu HH:MM:SS"""
        dt = cls.get_current_time()
        return dt.strftime("%H:%M:%S")

# ══════════════════════════════════════════════════════════════════════════════
# THEME ENGINE
# ══════════════════════════════════════════════════════════════════════════════
_theme: dict = {
    "primary": "#5a8a2e", "light": "#7bbf3e",
    "bg": "#1a1a1a", "panel": "#2d2d2d", "border": "#444",
    "accent": "#80c000", "text": "#e8e8e8", "muted": "#888",
}

def _T(key: str) -> str:
    return _theme.get(key, "#888")

def apply_theme(theme_dict: dict):
    global _theme
    _theme = theme_dict

def build_ss() -> str:
    p = _T("primary"); l = _T("light"); bg = _T("bg"); pan = _T("panel")
    brd = _T("border"); acc = _T("accent"); txt = _T("text"); mut = _T("muted")
    return f"""
/* ── Global ── */
QMainWindow, QDialog, QWidget {{
    background: {bg};
    color: {txt};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}
/* ── Tabs ── */
QTabWidget::pane {{ border: 1px solid {brd}; background: {bg}; }}
QTabBar::tab {{
    background: {pan}; color: {mut};
    padding: 10px 16px;
    border: 1px solid {brd}; border-bottom: none;
    font-weight: bold; font-size: 12px;
    min-height: 30px;
}}
QTabBar::tab:selected  {{ background: {bg}; color: {l}; border-bottom: 2px solid {l}; }}
QTabBar::tab:hover:!selected {{ background: {brd}; color: {txt}; }}
/* ── Buttons ── */
QPushButton {{
    background: {pan}; color: {l};
    border: 1px solid {p}; border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold; font-size: 12px;
    min-height: 34px;
}}
QPushButton:hover   {{ background: {p}; color: #fff; border-color: {l}; }}
QPushButton:pressed {{ background: {bg}; }}
QPushButton#danger  {{ background: #2a0808; color: #e05050; border-color: #8a2e2e; }}
QPushButton#danger:hover {{ background: #3a0808; }}
QPushButton#gold    {{ background: #2e2500; color: #f0a800; border-color: #8a7000; }}
QPushButton#gold:hover   {{ background: #3e3300; }}
QPushButton#diamond {{ background: #00252a; color: #4dd9e0; border-color: #006a6a; }}
QPushButton#diamond:hover {{ background: #003a3a; }}
QPushButton#solid   {{ background: {p}; color: #fff; border-color: {l}; }}
QPushButton#solid:hover  {{ background: {l}; }}
QPushButton#flat    {{ background: transparent; color: {mut}; border: none; padding: 4px 8px; }}
QPushButton#flat:hover   {{ color: {txt}; }}
/* ── Inputs ── */
QLineEdit {{
    background: #111; color: {txt};
    border: 1px solid {brd}; border-radius: 5px;
    padding: 8px 10px; font-size: 13px;
    min-height: 30px;
}}
QTextEdit {{
    background: #111; color: {txt};
    border: 1px solid {brd}; border-radius: 5px;
    padding: 8px 10px; font-size: 13px;
}}
QComboBox {{
    background: #111; color: {txt};
    border: 1px solid {brd}; border-radius: 5px;
    padding: 8px 10px; font-size: 13px;
    min-height: 30px;
}}
QSpinBox {{
    background: #111; color: {txt};
    border: 1px solid {brd}; border-radius: 5px;
    padding: 6px 10px; font-size: 13px;
    min-height: 30px;
}}
QLineEdit:focus, QTextEdit:focus {{ border-color: {l}; }}
QComboBox:focus {{ border-color: {l}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{
    background: #111; color: {txt};
    selection-background-color: {p};
}}
/* ── Scroll ── */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {bg}; width: 7px; border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {brd}; border-radius: 3px;
}}
QScrollBar::handle:vertical:hover {{ background: {p}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
/* ── Progress ── */
QProgressBar {{
    background: {bg}; border: 1px solid {brd};
    border-radius: 4px; height: 14px;
    text-align: center; font-size: 10px; color: {mut};
}}
QProgressBar::chunk {{ background: {acc}; border-radius: 3px; }}
/* ── Cards ── */
QFrame#card {{ background: {pan}; border: 1px solid {brd}; border-radius: 8px; }}
QFrame#card:hover {{ border-color: {p}; }}
/* ── Lists ── */
QListWidget {{
    background: {bg}; border: 1px solid {brd};
    border-radius: 6px; color: {txt};
}}
QListWidget::item {{ padding: 8px; border-bottom: 1px solid {brd}; }}
QListWidget::item:selected {{ background: {p}; color: #fff; }}
/* ── Groups ── */
QGroupBox {{
    color: {l}; font-weight: bold;
    border: 1px solid {brd}; border-radius: 6px;
    margin-top: 12px; padding-top: 10px;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 10px;
    padding: 0 6px; background: {bg};
}}
/* ── Checkboxes ── */
QCheckBox {{ color: {txt}; font-size: 13px; spacing: 6px; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 2px solid {p}; border-radius: 4px; background: #111;
}}
QCheckBox::indicator:checked {{ background: {l}; border-color: {l}; }}
/* ── Labels ── */
QLabel#section {{ color: {l}; font-size: 14px; font-weight: bold; }}
QLabel#sub     {{ color: {mut}; font-size: 12px; }}
QLabel#chip_hp   {{ color: #e05050; font-weight: bold; font-size: 13px; }}
QLabel#chip_mp   {{ color: #4da6ff; font-weight: bold; font-size: 13px; }}
QLabel#chip_gold {{ color: #f0a800; font-weight: bold; font-size: 13px; }}
"""

def build_overworld_ss() -> str:
    """Stylesheet statis tema Overworld (hardcoded, tidak berubah)"""
    return """
    QMainWindow, QDialog, QWidget {
        background: #1a1a1a;
        color: #e8e8e8;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 13px;
    }
    QTabWidget::pane { border: 1px solid #444; background: #1a1a1a; }
    QTabBar::tab {
        background: #2d2d2d; color: #888;
        padding: 10px 16px;
        border: 1px solid #444; border-bottom: none;
        font-weight: bold; font-size: 12px;
        min-height: 30px;
    }
    QTabBar::tab:selected { background: #1a1a1a; color: #7bbf3e; border-bottom: 2px solid #7bbf3e; }
    QPushButton {
        background: #2d2d2d; color: #7bbf3e;
        border: 1px solid #5a8a2e; border-radius: 6px;
        padding: 8px 16px;
        font-weight: bold; font-size: 12px;
        min-height: 34px;
    }
    QPushButton:hover { background: #5a8a2e; color: #fff; border-color: #7bbf3e; }
    QPushButton#solid { background: #5a8a2e; color: #fff; border-color: #7bbf3e; }
    QPushButton#danger { background: #2a0808; color: #e05050; border-color: #8a2e2e; }
    QPushButton#gold { background: #2e2500; color: #f0a800; border-color: #8a7000; }
    QPushButton#diamond { background: #00252a; color: #4dd9e0; border-color: #006a6a; }
    QLineEdit, QTextEdit, QComboBox, QSpinBox {
        background: #111; color: #e8e8e8;
        border: 1px solid #444; border-radius: 5px;
        padding: 8px 10px; font-size: 13px;
        min-height: 30px;
    }
    QProgressBar {
        background: #1a1a1a; border: 1px solid #444;
        border-radius: 4px; height: 14px;
        text-align: center; font-size: 10px; color: #888;
    }
    QProgressBar::chunk { background: #80c000; border-radius: 3px; }
    QFrame#card { background: #2d2d2d; border: 1px solid #444; border-radius: 8px; }
    QGroupBox { color: #7bbf3e; font-weight: bold; border: 1px solid #444; border-radius: 6px; margin-top: 12px; padding-top: 10px; }
    QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; background: #1a1a1a; }
    QCheckBox { color: #e8e8e8; font-size: 13px; spacing: 6px; }
    QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #5a8a2e; border-radius: 4px; background: #111; }
    QCheckBox::indicator:checked { background: #7bbf3e; border-color: #7bbf3e; }
    QLabel#section { color: #7bbf3e; font-size: 14px; font-weight: bold; }
    QLabel#sub { color: #888; font-size: 12px; }
    QLabel#chip_hp { color: #e05050; font-weight: bold; font-size: 13px; }
    QLabel#chip_mp { color: #4da6ff; font-weight: bold; font-size: 13px; }
    QLabel#chip_gold { color: #f0a800; font-weight: bold; font-size: 13px; }
    QListWidget { background: #1a1a1a; border: 1px solid #444; border-radius: 6px; color: #e8e8e8; }
    QListWidget::item { padding: 8px; border-bottom: 1px solid #444; }
    QListWidget::item:selected { background: #5a8a2e; color: #fff; }
    QScrollArea { border: none; background: transparent; }
    QScrollBar:vertical { background: #1a1a1a; width: 7px; border-radius: 3px; }
    QScrollBar::handle:vertical { background: #444; border-radius: 3px; }
    QScrollBar::handle:vertical:hover { background: #5a8a2e; }
    """
# ══════════════════════════════════════════════════════════════════════════════
#  Loading Animation
# ══════════════════════════════════════════════════════════════════════════════
class LoadingDialog(QDialog):
    """Dialog loading sederhana dengan animasi titik-titik"""
    def __init__(self, message="Memproses...", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setFixedSize(300, 100)
        self.setStyleSheet("background: #2d2d2d; border: 1px solid #5a8a2e; border-radius: 10px;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label = QLabel(message)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("color: #e8e8e8; font-size: 14px;")
        layout.addWidget(self.label)
        
        self.dot_count = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._animate)
        self.timer.start(500)

    def _animate(self):
        self.dot_count = (self.dot_count + 1) % 4
        dots = "." * self.dot_count
        base_text = self.label.text().split(".")[0]
        self.label.setText(f"{base_text}{dots}")
    
    def closeEvent(self, e):
        self.timer.stop()
        super().closeEvent(e)

import traceback
import json
import os
import hashlib
from datetime import datetime

def save_session(user_id, username, password_hash):
    """Simpan session dengan hash password (bukan plain)."""
    try:
        data = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "timestamp": datetime.now().isoformat()
        }
        # Tulis ke file sementara lalu rename untuk atomic operation
        temp_file = SESSION_FILE + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f)
        os.replace(temp_file, SESSION_FILE)  # atomic di Windows
    except Exception as e:
        print(f"Save session error: {e}")

def load_session():
    """Load session jika valid."""
    if not os.path.exists(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)
        # Validasi struktur
        if not all(k in data for k in ("user_id", "username", "password_hash")):
            return None
        conn = db.get_conn()
        row = conn.execute("SELECT id, password_hash FROM users WHERE id=?", (data["user_id"],)).fetchone()
        conn.close()
        if row and row["password_hash"] == data["password_hash"]:
            return {"user_id": row["id"], "username": data["username"]}
        else:
            # Session tidak valid, hapus file
            clear_session()
            return None
    except Exception:
        clear_session()
        return None

def clear_session():
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except Exception:
        pass
# ══════════════════════════════════════════════════════════════════════════════
#  APP STATE  ─ single source of truth, avoids restart-to-sync bugs
# ══════════════════════════════════════════════════════════════════════════════
class AppState:
    user_id: int = 0
    _cbs: list = []

    @classmethod
    def set_user(cls, uid: int):
        cls.user_id = uid
        t = db.get_user_theme(uid)
        apply_theme(t)
        SoundEngine.enabled = bool(db.get_user(uid).get("sound_enabled", 1))

    @classmethod
    def user(cls) -> dict:
        return db.get_user(cls.user_id) if cls.user_id else {}

    @classmethod
    def refresh(cls):
        for cb in list(cls._cbs):
            try: cb()
            except: pass

    @classmethod
    def register(cls, cb):
        if cb not in cls._cbs: cls._cbs.append(cb)

    @classmethod
    def unregister(cls, cb):
        if cb in cls._cbs: cls._cbs.remove(cb)


# ══════════════════════════════════════════════════════════════════════════════
#  SMALL HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _lbl(text, obj="", size=13, bold=False):
    if size <= 0: size = 10
    w = QLabel(text)
    w.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    if obj: w.setObjectName(obj)
    return w

def _btn(text, obj="", slot=None, h=38):
    b = QPushButton(text)
    if obj: b.setObjectName(obj)
    if slot: b.clicked.connect(slot)
    b.setMinimumHeight(h)
    return b

from PyQt6.QtWidgets import QGraphicsDropShadowEffect

def _card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    # Efek shadow halus
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(15)
    shadow.setXOffset(0)
    shadow.setYOffset(2)
    shadow.setColor(QColor(0, 0, 0, 80))
    f.setGraphicsEffect(shadow)
    return f

def _scrolled(inner):
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setWidget(inner)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return sa

def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color: {_T('border')};")
    return f

def _combo(items):
    cb = QComboBox()
    cb.setMinimumHeight(42)
    for text, data in items:
        cb.addItem(text, data)
    return cb

def _input(placeholder="", password=False):
    f = QLineEdit()
    f.setPlaceholderText(placeholder)
    f.setMinimumHeight(42)
    if password: f.setEchoMode(QLineEdit.EchoMode.Password)
    return f

def _show(parent, title, msg, kind="info"):
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    dlg.setFixedWidth(380)
    dlg.setMinimumHeight(140)
    dlg.setStyleSheet(build_ss())
    lay = QVBoxLayout(dlg)
    lay.setContentsMargins(24,20,24,20)
    lay.setSpacing(14)
    icon = {"info":"💬","success":"✅","error":"❌","warning":"⚠️","levelup":"🎉"}.get(kind,"💬")
    lbl = QLabel(f"{icon}  {msg}")
    lbl.setWordWrap(True)
    lbl.setStyleSheet(f"color: {_T('text')}; font-size:13px;")
    lay.addWidget(lbl)
    ok = _btn("OK", "solid", dlg.accept, 40)
    lay.addWidget(ok)
    dlg.exec()



# ══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
class TopBar(QWidget):
    def __init__(self, on_notif, on_profile):
        super().__init__()
        self.setFixedHeight(72)
        self._update_bg()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)

        self._logo = QLabel("⛏  CraftLife")
        self._logo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self._logo.setStyleSheet(f"color: {_T('light')};")
        lay.addWidget(self._logo)
        lay.addSpacing(8)

        # XP column
        xp_col = QVBoxLayout()
        xp_col.setSpacing(3)
        self._xp_lbl = QLabel("Level 1")
        self._xp_lbl.setStyleSheet(
            f"color: {_T('accent')}; font-size: 11px; font-weight: bold;")
        self._xp_bar = QProgressBar()
        self._xp_bar.setFixedHeight(10)
        self._xp_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {_T('accent')}; border-radius: 4px; }}")
        xp_col.addWidget(self._xp_lbl)
        xp_col.addWidget(self._xp_bar)
        xp_w = QWidget()
        xp_w.setLayout(xp_col)
        xp_w.setSizePolicy(QSizePolicy.Policy.Expanding,
                            QSizePolicy.Policy.Preferred)
        lay.addWidget(xp_w)
        lay.addSpacing(8)

        # Stat chips
        self._hp_lbl   = self._chip("❤️ --",   "chip_hp")
        self._mp_lbl   = self._chip("💙 -- MP", "chip_mp")
        self._gold_lbl = self._chip("💰 --",    "chip_gold")
        self._time_lbl = QLabel("--:--:--")
        self._time_lbl.setObjectName("chip_time")
        self._time_lbl.setStyleSheet(
            f"background: {_T('panel')}; border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 3px 10px;"
            f" font-family: monospace; font-size: 13px;"
        )
        lay.addWidget(self._time_lbl)
        for w in [self._hp_lbl, self._mp_lbl, self._gold_lbl]:
            lay.addWidget(w)

        self._notif_btn = _btn("🔔", slot=on_notif)
        self._notif_btn.setFixedWidth(44)
        self._notif_btn.setFixedHeight(34)
        lay.addWidget(self._notif_btn)

        prof_btn = _btn("👤", slot=on_profile)
        prof_btn.setFixedWidth(44)
        prof_btn.setFixedHeight(34)
        lay.addWidget(prof_btn)

        exit_btn = _btn("🚪", slot=QApplication.instance().quit)
        exit_btn.setFixedWidth(44)
        exit_btn.setFixedHeight(34)
        lay.addWidget(exit_btn)

        logout_btn = _btn("Logout", slot=self._logout)
        logout_btn.setFixedWidth(70)
        logout_btn.setFixedHeight(34)
        lay.addWidget(logout_btn)

        self.refresh()

        # Timer untuk jam digital (update setiap detik)
        self._time_timer = QTimer()
        self._time_timer.timeout.connect(self._update_time)
        self._time_timer.start(1000)
        self._update_time()  # langsung tampilkan

    # ── Timer ────────────────────────────────────────────────────────────────
    def _update_time(self):
        try:
            self._time_lbl.setText(TimeSync.get_formatted_time())
            if TimeSync._last_sync > 0:
                self._time_lbl.setStyleSheet(
                    f"background: {_T('panel')}; border: 1px solid {_T('border')};"
                    f" border-radius: 6px; padding: 3px 10px;"
                    f" font-family: monospace; font-size: 13px;"
                )
        except Exception:
            self._time_lbl.setText(datetime.now().strftime("%H:%M:%S"))
            self._time_lbl.setStyleSheet("color: #e05050;")

    # ── LogOut ────────────────────────────────────────────────────────────────
    def _logout(self):
        clear_session()
        main_win = self.window()
        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, LoginWindow):
                widget.show()
                break
        else:
            login = LoginWindow()
            login.show()
        main_win.close()

    # ── internal ──────────────────────────────────────────────────────────────

    def _chip(self, text: str, obj: str) -> QLabel:
        w = QLabel(text)
        w.setObjectName(obj)
        w.setStyleSheet(
            f"background: {_T('panel')}; border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 3px 10px;"
        )
        return w

    def _update_bg(self):
        self.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            f"stop:0 {_T('bg')},stop:1 {_T('panel')});"
            f"border-bottom: 2px solid {_T('primary')};"
        )

    # ── public ────────────────────────────────────────────────────────────────

    def refresh(self):
        u = AppState.user()
        if not u:
            return
        lvl  = u["level"]
        xp   = u["xp"]
        need = lvl * 150
        dn   = u.get("display_name", "") or u.get("username", "")
        self._xp_lbl.setText(f"Level {lvl}  ·  {dn}  —  {xp}/{need} XP")
        self._xp_bar.setMaximum(need)
        self._xp_bar.setValue(int(xp))
        self._hp_lbl.setText(f"❤️  {u['hp']}/{u['max_hp']}")

        # MP chip shows skill name
        cls   = u.get("avatar_class", "warrior")
        skill = db.CLASS_SKILLS.get(cls, {})
        self._mp_lbl.setText(
            f"💙 {u['mp']}/{u['max_mp']} MP  ({skill.get('name','?')})")

        self._gold_lbl.setText(f"💰  {u['gold']:.0f}")
        notifs = db.get_notifications(AppState.user_id)
        self._notif_btn.setText(
            f"🔔 {len(notifs)}" if notifs else "🔔")

    def retheme(self):
        self._update_bg()
        # Logo
        self._logo.setStyleSheet(f"color: {_T('light')};")
        # XP row
        self._xp_lbl.setStyleSheet(
            f"color: {_T('accent')}; font-size: 11px; font-weight: bold;")
        self._xp_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {_T('accent')}; border-radius:4px; }}")
        # Stat chips — wajib di-restyle saat theme berubah
        _chip_ss = (
            f"background: {_T('panel')}; border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 3px 10px;"
        )
        self._hp_lbl.setStyleSheet(_chip_ss)
        self._mp_lbl.setStyleSheet(_chip_ss)
        self._gold_lbl.setStyleSheet(_chip_ss)
        # Jam digital
        self._time_lbl.setStyleSheet(
            f"background: {_T('panel')}; border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 3px 10px;"
            f" font-family: monospace; font-size: 13px;"
        )
        self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  NAV BAR  (left sidebar)
# ══════════════════════════════════════════════════════════════════════════════
class NavBar(QWidget):
    tab_changed = pyqtSignal(str)

    _TABS = [
        ("⛏", "Habits",      "habits"),
        ("📅", "Dailies",     "dailies"),
        ("📜", "Quests",      "todos"),
        ("🏅", "SportTrack",  "sport"),
        ("💰", "Economy",     "economy"),
        ("🏪", "Shop",        "shop"),
        ("🐾", "Pets",        "pets"),
        ("👥", "Friends",     "friends"),
        ("⚔️", "Guild",       "guild"),
        ("📊", "Stats",       "stats"),
        ("🎭", "Profile",     "profile"),
        ("⚙️", "Settings",    "settings"),
        ("🏆", "Leaderboard", "leaderboard")
    ]

    def __init__(self):
        super().__init__()
        self.setFixedWidth(90)
        self._btns: dict = {}
        self._active = ""
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(2)
        for icon, label, key in self._TABS:
            b = QPushButton(f"{icon}\n{label}")
            b.setCheckable(True)
            b.setFixedHeight(64)
            b.clicked.connect(lambda _, k=key: self._select(k))
            lay.addWidget(b)
            self._btns[key] = b
        lay.addStretch()
        self.retheme()
        self._select("habits")

    def _style(self, active: bool) -> str:
        if active:
            return (f"QPushButton {{ background: {_T('primary')}; color: #fff;"
                    f" border: none; border-radius: 0;"
                    f" font-size: 10px; font-weight: bold;"
                    f" border-left: 3px solid {_T('light')}; }}")
        return (f"QPushButton {{ background: transparent; color: {_T('muted')};"
                f" border: none; border-radius: 0;"
                f" font-size: 10px; font-weight: bold; }}"
                f"QPushButton:hover {{ background: {_T('border')};"
                f" color: {_T('text')}; }}")

    def _select(self, key: str):
        self._active = key
        for k, b in self._btns.items():
            b.setChecked(k == key)
            b.setStyleSheet(self._style(k == key))
        SND.click()
        self.tab_changed.emit(key)

    def retheme(self):
        self.setStyleSheet(
            f"background: {_T('panel')};"
            f"border-right: 1px solid {_T('border')};")
        for k, b in self._btns.items():
            b.setStyleSheet(self._style(k == self._active))


# ══════════════════════════════════════════════════════════════════════════════
#  ADD TASK DIALOG  (fixed: proper heights, scroll if needed)
# ══════════════════════════════════════════════════════════════════════════════
class AddTaskDialog(QDialog):
    def __init__(self, mode: str, user_id: int, parent=None):
        super().__init__(parent)
        self.mode    = mode
        self.user_id = user_id
        titles = {"habit": "➕  Tambah Habit",
                  "daily": "➕  Tambah Daily",
                  "todo":  "➕  Tambah Quest"}
        self.setWindowTitle(titles.get(mode, "Tambah"))
        self.setMinimumWidth(460)
        self.setMinimumHeight(460)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Scrollable content ───────────────────────────────────────────────
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Name
        lay.addWidget(_lbl("Nama", size=12))
        self._name = _input("Tulis nama di sini…")
        lay.addWidget(self._name)

        # Icon
        lay.addWidget(_lbl("Icon", size=12))
        icons = [
            ("⚔️  Combat",     "⚔️"),
            ("📚  Study",      "📚"),
            ("🏃  Exercise",   "🏃"),
            ("🍎  Health",     "🍎"),
            ("💤  Sleep",      "💤"),
            ("🧘  Mindfulness","🧘"),
            ("💧  Hydration",  "💧"),
            ("🌱  Growth",     "🌱"),
            ("🎯  Focus",      "🎯"),
            ("💡  Ideas",      "💡"),
            ("📜  Quest",      "📜"),
            ("🏗️  Build",      "🏗️"),
        ]
        self._icon = _combo(icons)
        lay.addWidget(self._icon)

        # Difficulty / priority
        if self.mode == "todo":
            lay.addWidget(_lbl("Prioritas", size=12))
            opts = [
                ("⚪  Trivial  (+10 XP)",  "trivial"),
                ("🟢  Mudah   (+20 XP)",  "easy"),
                ("🟡  Sedang  (+40 XP)",  "medium"),
                ("🔴  Sulit   (+60 XP)",  "hard"),
            ]
        else:
            lay.addWidget(_lbl("Kesulitan", size=12))
            opts = [
                ("🟢  Mudah   (+15/20 XP)", "easy"),
                ("🟡  Sedang  (+25/30 XP)", "medium"),
                ("🔴  Sulit   (+40/50 XP)", "hard"),
                ("💜  Epic    (+60/75 XP)", "epic"),
            ]
        self._diff = _combo(opts)
        self._diff.setCurrentIndex(1)
        lay.addWidget(self._diff)

        # Notes
        lay.addWidget(_lbl("Catatan  (opsional)", size=12))
        self._notes = _input("Catatan…")
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl("Masukkan ke Folder  (opsional)", size=12))
        _folders = db.get_task_folders(self.user_id, self.mode)
        _fopts = [("📭  Tanpa Folder", None)] + [
            (f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok = _btn("➕  Tambah", "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        sa = _scrolled(content)
        root.addWidget(sa)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, "Error", "Nama tidak boleh kosong!", "error")
            return
        icon  = self._icon.currentData()
        diff  = self._diff.currentData()
        notes = self._notes.text()
        folder_id = self._folder.currentData()
        if self.mode == "habit":
            db.add_habit(self.user_id, name, icon, diff, 1, 1, notes)
            if folder_id:
                new_id = max(i["id"] for i in db.get_habits(self.user_id))
                db.set_item_folder(self.user_id, "habit", new_id, folder_id)
        elif self.mode == "daily":
            db.add_daily(self.user_id, name, icon, diff, notes)
            if folder_id:
                new_id = max(i["id"] for i in db.get_dailies(self.user_id))
                db.set_item_folder(self.user_id, "daily", new_id, folder_id)
        else:
            db.add_todo(self.user_id, name, diff, icon, None, notes)
            if folder_id:
                new_id = max(i["id"] for i in db.get_todos(self.user_id))
                db.set_item_folder(self.user_id, "todo", new_id, folder_id)
        SND.complete()
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  Edit Task Dialog  (Habits / Dailies / Todos)
# ══════════════════════════════════════════════════════════════════════════════
class EditTaskDialog(QDialog):
    def __init__(self, mode, user_id, item, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.user_id = user_id
        self.item = item
        self.setWindowTitle(f"✏️ Edit {mode.capitalize()}")
        self.setMinimumWidth(460)
        self.setMinimumHeight(460)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24,24,24,24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Name
        lay.addWidget(_lbl("Nama", size=12))
        self._name = _input(self.item["name"])
        lay.addWidget(self._name)

        # Icon (sama seperti AddTaskDialog)
        lay.addWidget(_lbl("Icon", size=12))
        icons = [
            ("⚔️  Combat",     "⚔️"),
            ("📚  Study",      "📚"),
            ("🏃  Exercise",   "🏃"),
            ("🍎  Health",     "🍎"),
            ("💤  Sleep",      "💤"),
            ("🧘  Mindfulness","🧘"),
            ("💧  Hydration",  "💧"),
            ("🌱  Growth",     "🌱"),
            ("🎯  Focus",      "🎯"),
            ("💡  Ideas",      "💡"),
            ("📜  Quest",      "📜"),
            ("🏗️  Build",      "🏗️"),
        ]
        self._icon = _combo(icons)
        # set current icon
        index = self._icon.findData(self.item["icon"])
        if index >= 0: self._icon.setCurrentIndex(index)
        lay.addWidget(self._icon)

        # Difficulty / priority
        if self.mode == "todo":
            lay.addWidget(_lbl("Prioritas", size=12))
            opts = [("⚪ Trivial","trivial"),("🟢 Mudah","easy"),("🟡 Sedang","medium"),("🔴 Sulit","hard")]
        else:
            lay.addWidget(_lbl("Kesulitan", size=12))
            opts = [("🟢 Mudah","easy"),("🟡 Sedang","medium"),("🔴 Sulit","hard"),("💜 Epic","epic")]
        self._diff = _combo(opts)
        idx = self._diff.findData(self.item.get("difficulty") or self.item.get("priority","medium"))
        if idx >= 0: self._diff.setCurrentIndex(idx)
        lay.addWidget(self._diff)

        # Notes
        lay.addWidget(_lbl("Catatan", size=12))
        self._notes = _input(self.item.get("notes",""))
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl("Masukkan ke Folder  (opsional)", size=12))
        _folders = db.get_task_folders(self.user_id, self.mode)
        _fopts = [("📭  Tanpa Folder", None)] + [
            (f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        cur_fid = self.item.get("folder_id")
        if cur_fid:
            idx = next((i for i,(_, d) in enumerate(_fopts) if d == cur_fid), 0)
            self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok = _btn("💾 Simpan", "solid", self._save, 46)
        lay.addWidget(ok)
        sa = _scrolled(content)
        root.addWidget(sa)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, "Error", "Nama tidak boleh kosong!", "error")
            return
        icon = self._icon.currentData()
        diff = self._diff.currentData()
        notes = self._notes.text()
        folder_id = self._folder.currentData()
        if self.mode == "habit":
            db.update_habit(self.item["id"], self.user_id, name=name, icon=icon, difficulty=diff, notes=notes)
        elif self.mode == "daily":
            db.update_daily(self.item["id"], self.user_id, name=name, icon=icon, difficulty=diff, notes=notes)
        else:
            db.update_todo(self.item["id"], self.user_id, name=name, icon=icon, priority=diff, notes=notes)
        db.set_item_folder(self.user_id, self.mode, self.item["id"], folder_id)
        SND.complete()
        self.accept()

# ══════════════════════════════════════════════════════════════════════════════
#  TASK PAGE  (Habits / Dailies / Todos)
# ══════════════════════════════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════════════════════════════
#  TASK ICON CATEGORIES  (sub-tab categories untuk habits/dailies/todos)
# ══════════════════════════════════════════════════════════════════════════════
TASK_ICON_CATEGORIES = {
    "⚔️":  {"name": "Combat",      "icon": "⚔️"},
    "📚":  {"name": "Study",       "icon": "📚"},
    "🏃":  {"name": "Exercise",    "icon": "🏃"},
    "🍎":  {"name": "Health",      "icon": "🍎"},
    "💤":  {"name": "Sleep",       "icon": "💤"},
    "🧘":  {"name": "Mindfulness", "icon": "🧘"},
    "💧":  {"name": "Hydration",   "icon": "💧"},
    "🌱":  {"name": "Growth",      "icon": "🌱"},
    "🎯":  {"name": "Focus",       "icon": "🎯"},
    "💡":  {"name": "Ideas",       "icon": "💡"},
    "📜":  {"name": "Quest",       "icon": "📜"},
    "🏗️": {"name": "Build",       "icon": "🏗️"},
}


# ══════════════════════════════════════════════════════════════════════════════
#  FOLDER HEADER WIDGET  (collapsible section for organizing cards)
# ══════════════════════════════════════════════════════════════════════════════
class FolderWidget(QWidget):
    """Collapsible folder widget - menggunakan panah bawaan Qt untuk toggle."""

    def __init__(self, folder: dict, mode: str, user_id: int,
                 on_reload, parent):
        super().__init__(parent)
        self.folder     = folder
        self.mode       = mode
        self.user_id    = user_id
        self.on_reload  = on_reload
        self._collapsed = bool(folder.get("collapsed", 0))
        self._item_count = 0
        self._build()

    def _build(self):
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(0, 2, 0, 6)
        self._root.setSpacing(0)

        # Header card — pakai _card() agar konsisten
        hdr = _card()
        hdr.setStyleSheet(
            f"QFrame#card {{"
            f" background:{_T('panel')};"
            f" border:1px solid {_T('primary')};"
            f" border-left:4px solid {_T('light')};"
            f" border-radius:8px; }}"
            f"QFrame#card:hover {{"
            f" border-color:{_T('light')};"
            f" border-left-color:{_T('accent')}; }}"
        )

        row = QHBoxLayout(hdr)
        row.setContentsMargins(10, 10, 10, 10)
        row.setSpacing(8)

        # Tombol toggle dengan panah Qt


        self._toggle_btn = QToolButton()
        self._toggle_btn.setArrowType(Qt.ArrowType.RightArrow if self._collapsed else Qt.ArrowType.DownArrow)
        self._toggle_btn.setFixedSize(28, 28)
        self._toggle_btn.setStyleSheet("border: none; background: transparent;")
        self._toggle_btn.clicked.connect(self._toggle)
        row.addWidget(self._toggle_btn)

        # Icon folder
        ico_lbl = QLabel(self.folder.get("icon", "\U0001f4c1"))
        ico_lbl.setFont(QFont("Segoe UI", 20))
        ico_lbl.setFixedWidth(34)
        row.addWidget(ico_lbl)

        # Nama folder + jumlah item
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self._name_lbl = QLabel(self.folder["name"])
        self._name_lbl.setStyleSheet(
            f"color:{_T('text')}; font-weight:bold; font-size:14px;"
            f" background:transparent; border:none;")
        info_col.addWidget(self._name_lbl)
        self._count_lbl = QLabel("0 item")
        self._count_lbl.setStyleSheet(
            f"color:{_T('muted')}; font-size:11px;"
            f" background:transparent; border:none;")
        info_col.addWidget(self._count_lbl)
        row.addLayout(info_col, 1)

        # Tombol aksi (edit, duplikat, hapus)
        edit_btn = _btn("\u270f\ufe0f", h=36)
        edit_btn.setFixedWidth(36)
        edit_btn.setToolTip("Edit folder")
        edit_btn.clicked.connect(self._edit_folder)
        row.addWidget(edit_btn)

        dup_btn = _btn("\U0001f4cb", h=36)
        dup_btn.setFixedWidth(36)
        dup_btn.setToolTip("Duplikasi folder")
        dup_btn.clicked.connect(self._dup_folder)
        row.addWidget(dup_btn)

        del_btn = _btn("\U0001f5d1", "danger", h=36)
        del_btn.setFixedWidth(36)
        del_btn.setToolTip("Hapus folder")
        del_btn.clicked.connect(self._del_folder)
        row.addWidget(del_btn)

        self._root.addWidget(hdr)

        # Area konten — dengan indentasi
        self._content = QWidget(self)
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(24, 4, 0, 0)
        self._content_lay.setSpacing(6)
        self._content.setVisible(not self._collapsed)
        self._root.addWidget(self._content)

    def add_card(self, card: QWidget):
        self._content_lay.addWidget(card)
        self._item_count += 1
        self._count_lbl.setText(
            f"{self._item_count} item{'s' if self._item_count > 1 else ''}")

    def _toggle(self):
        self._collapsed = not self._collapsed
        # Ubah panah sesuai status
        self._toggle_btn.setArrowType(Qt.ArrowType.RightArrow if self._collapsed else Qt.ArrowType.DownArrow)
        self._content.setVisible(not self._collapsed)
        # Simpan status ke database
        db.update_task_folder(self.folder["id"], self.user_id,
                              collapsed=int(self._collapsed))

    def _edit_folder(self):
        dlg = FolderDialog(self.mode, self.user_id,
                           existing=self.folder, parent=self)
        if dlg.exec():
            self.on_reload()

    def _dup_folder(self):
        r = db.duplicate_task_folder(self.user_id, self.folder["id"], self.mode)
        SND.notify() if r["ok"] else SND.error()
        self.on_reload()

    def _del_folder(self):
        db.delete_task_folder(self.user_id, self.folder["id"], self.mode)
        SND.click()
        self.on_reload()


# ══════════════════════════════════════════════════════════════════════════════
#  FOLDER DIALOG  (add / edit folder)
# ══════════════════════════════════════════════════════════════════════════════
class FolderDialog(QDialog):
    """Dialog untuk membuat atau mengedit folder."""

    FOLDER_ICONS = [
        ("📁 Default",   "📁"),
        ("⭐ Favorit",   "⭐"),
        ("🔥 Prioritas", "🔥"),
        ("💪 Latihan",   "💪"),
        ("📖 Belajar",   "📖"),
        ("🎯 Tujuan",    "🎯"),
        ("🌙 Malam",     "🌙"),
        ("☀️ Pagi",      "☀️"),
        ("🎮 Hobi",      "🎮"),
        ("💼 Kerja",     "💼"),
        ("🏠 Rumah",     "🏠"),
        ("🌿 Sehat",     "🌿"),
    ]

    def __init__(self, mode: str, user_id: int,
                 existing=None, parent=None):
        super().__init__(parent)
        self.mode     = mode
        self.user_id  = user_id
        self.existing = existing
        title = "✏️ Edit Folder" if existing else "📁 Buat Folder Baru"
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 13, True))
        lay.addWidget(_sep())

        lay.addWidget(_lbl("Nama Folder", size=12))
        self._name = _input("Nama folder...")
        if self.existing:
            self._name.setText(self.existing["name"])
        lay.addWidget(self._name)

        lay.addWidget(_lbl("Icon", size=12))
        self._icon = _combo(self.FOLDER_ICONS)
        if self.existing:
            idx = next((i for i, (_, d) in enumerate(self.FOLDER_ICONS)
                        if d == self.existing.get("icon", "📁")), 0)
            self._icon.setCurrentIndex(idx)
        lay.addWidget(self._icon)

        ok_text = "💾 Simpan" if self.existing else "📁 Buat Folder"
        ok = _btn(ok_text, "solid", self._save, 44)
        lay.addWidget(ok)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, "Error", "Nama folder tidak boleh kosong!", "error")
            return
        icon = self._icon.currentData()
        if self.existing:
            db.update_task_folder(self.existing["id"], self.user_id,
                                  name=name, icon=icon)
        else:
            db.add_task_folder(self.user_id, self.mode, name, icon)
        SND.complete()
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  TASK PAGE  (habits / dailies / todos)  — with sub-tabs + folders
# ══════════════════════════════════════════════════════════════════════════════
class TaskPage(QWidget):
    def __init__(self, user_id: int, mode: str):
        super().__init__()
        self.user_id = user_id
        self.mode    = mode
        self._build()
        AppState.register(self.load)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        titles = {"habit": "⛏  Daily Habits",
                  "daily": "📅  Dailies",
                  "todo":  "📜  Quest Log"}
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(titles[self.mode], "section", 14, True))
        hdr.addStretch()
        # Tombol tambah folder
        folder_btn = _btn("📁  Folder", h=36)
        folder_btn.setFixedWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add = _btn("➕  Tambah", "solid", self._open_add)
        add.setFixedWidth(130)
        hdr.addWidget(add)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Filter bar
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari...")
        self.search_input.textChanged.connect(self.load)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Semua", "Easy", "Medium", "Hard", "Epic"])
        self.filter_combo.currentTextChanged.connect(self.load)
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.filter_combo)
        root.addWidget(filter_widget)

        # ── Tab widget: Semua + satu per kategori icon ──────────────────────
        self._tabs = QTabWidget()

        # Tab "Semua"
        self._inner_all = QWidget()
        self._lay_all   = QVBoxLayout(self._inner_all)
        self._lay_all.setSpacing(8)
        self._lay_all.addStretch()
        self._tabs.addTab(_scrolled(self._inner_all), "🗂 Semua")

        # Tab per icon category
        self._cat_lays: dict   = {}
        self._cat_inners: dict  = {}
        for key, cat in TASK_ICON_CATEGORIES.items():
            inner = QWidget()
            lay   = QVBoxLayout(inner)
            lay.setSpacing(8)
            lay.addStretch()
            self._cat_lays[key]   = lay
            self._cat_inners[key] = inner
            self._tabs.addTab(_scrolled(inner),
                              f"{cat['icon']} {cat['name']}")

        root.addWidget(self._tabs, 1)
        self.load()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clear_lay(self, lay: QVBoxLayout):
        while lay.count() > 1:
            it = lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()

    def _get_items(self):
        if self.mode == "habit":
            return db.get_habits(self.user_id)
        elif self.mode == "daily":
            return db.get_dailies(self.user_id)
        else:
            return db.get_todos(self.user_id)

    # ── load / refresh ────────────────────────────────────────────────────────

    def load(self):
        if not AppState.user_id:
            return
        db.reset_daily_tasks(self.user_id)

        # Bersihkan semua tab
        self._clear_lay(self._lay_all)
        for lay in self._cat_lays.values():
            self._clear_lay(lay)

        all_items = self._get_items()

        # Filter
        search     = self.search_input.text().lower()
        filter_diff = self.filter_combo.currentText().lower()
        if search:
            all_items = [i for i in all_items if search in i["name"].lower()]
        if filter_diff != "semua":
            all_items = [i for i in all_items
                         if i.get("difficulty", i.get("priority", "")).lower() == filter_diff]

        folders = db.get_task_folders(self.user_id, self.mode)

        # Render ke tab "Semua" dan tab per-kategori
        self._render_to_layout(self._lay_all, self._inner_all, all_items, folders)
        by_cat: dict = {}
        for item in all_items:
            icon_key = item.get("icon", "")
            # Normalise: strip variation selector
            norm_key = icon_key.replace("\ufe0f", "").strip()
            matched  = None
            for k in self._cat_lays:
                if k.replace("\ufe0f", "").strip() == norm_key:
                    matched = k
                    break
            if matched:
                by_cat.setdefault(matched, []).append(item)

        for key, lay in self._cat_lays.items():
            cat_items = by_cat.get(key, [])
            self._render_to_layout(lay, self._cat_inners[key], cat_items, folders)

    def _render_to_layout(self, lay: QVBoxLayout, container: QWidget, items: list, folders: list):
        """Render items ke layout dengan dukungan folder collapsible."""
        if not items and not folders:
            e_icon = {"habit": "⛏️", "daily": "📅", "todo": "📜"}[self.mode]
            e_msg  = {
                "habit": "Belum ada habit. Tambahkan yang pertama!",
                "daily": "Belum ada daily. Buat rutinitasmu!",
                "todo":  "Quest log kosong. Tambahkan tugasmu!",
            }[self.mode]
            el = _lbl(f"{e_icon}  {e_msg}", "sub", 13)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color: {_T('muted')}; padding: 40px;")
            lay.insertWidget(0, el)
            return

        insert_pos = 0

        # Items per folder
        folder_items: dict = {f["id"]: [] for f in folders}
        ungrouped: list = []
        for item in items:
            fid = item.get("folder_id")
            if fid and fid in folder_items:
                folder_items[fid].append(item)
            else:
                ungrouped.append(item)

        # Render folders
        for folder in folders:
            fw = FolderWidget(folder, self.mode, self.user_id, self.load, parent=container)
            cards_in_folder = folder_items.get(folder["id"], [])
            if not cards_in_folder:
                empty_lbl = QLabel("   📭  Folder kosong")
                empty_lbl.setStyleSheet(
                    f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards_in_folder:
                    fw.add_card(self._make_card(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        # Render ungrouped
        for item in ungrouped:
            card = self._make_card(item)
            lay.insertWidget(insert_pos, card)
            insert_pos += 1

    # ── card builder ──────────────────────────────────────────────────────────

    def _make_card(self, item: dict) -> QFrame:
        done = bool(item.get("done_today") or item.get("done", False))
        f    = _card()
        row  = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        # Icon
        ico = QLabel(item["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setFixedWidth(38)
        row.addWidget(ico)

        # Info block
        info = QVBoxLayout()
        info.setSpacing(2)
        name_style = (f"text-decoration:line-through; color:{_T('muted')};"
                      if done else
                      f"color:{_T('text')}; font-weight:bold;")
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; {name_style}")
        info.addWidget(nm)

        if self.mode == "todo":
            pc = {"trivial": _T("muted"), "easy": _T("light"),
                  "medium": "#f0a800",    "hard": "#e05050"}
            col = pc.get(item.get("priority", "medium"), _T("muted"))
            sub = QLabel(
                f"<span style='color:{col}'>{item.get('priority','?').title()}</span>"
                f"  ·  +{item['xp_reward']} XP  ·  +{item['gold_reward']:.0f} G")
            sub.setTextFormat(Qt.TextFormat.RichText)
        else:
            streak_txt = (f"   🔥 {item['streak']} hari"
                          if item.get("streak", 0) > 0 else "")
            sub = QLabel(
                f"+{item['xp_reward']} XP  ·  +{item['gold_reward']:.0f} G"
                f"{streak_txt}")
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)
        row.addLayout(info, 1)

        # Notes untuk semua mode
        if item.get("notes"):
            notes_lbl = QLabel(f"📝 {item['notes']}")
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet(
                f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(notes_lbl)

        # Indikator action hari ini
        if done and item.get("last_action"):
            action_text  = "✅ Berhasil" if item["last_action"] == "up" else "❌ Gagal"
            action_color = "#80c000" if item["last_action"] == "up" else "#e05050"
            action_label = QLabel(action_text)
            action_label.setStyleSheet(
                f"color:{action_color}; font-size:11px; font-weight:bold;")
            info.addWidget(action_label)

        # Action buttons
        if self.mode == "habit":
            ck = _btn("✔ Done" if done else "✔ Check", h=36)
            ck.setEnabled(not done)
            if done:
                ck.setStyleSheet(
                    f"background:{_T('border')}; color:{_T('muted')};"
                    f" border-color:{_T('border')};")
            ck.setFixedWidth(92)
            ck.clicked.connect(lambda _, i=item["id"]: self._do("up", i))
            row.addWidget(ck)

            nb = _btn("✗ Gagal", "danger", h=36)
            nb.setEnabled(not done)
            if done:
                nb.setStyleSheet(
                    f"background:{_T('border')}; color:{_T('muted')};"
                    f" border-color:{_T('border')};")
            nb.setFixedWidth(82)
            nb.clicked.connect(lambda _, i=item["id"]: self._do("down", i))
            row.addWidget(nb)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setFixedWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        elif self.mode == "daily":
            ck = _btn("✔ Done" if done else "✔ Check", h=36)
            ck.setEnabled(not done)
            if done:
                ck.setStyleSheet(
                    f"background:{_T('border')}; color:{_T('muted')};"
                    f" border-color:{_T('border')};")
            ck.setFixedWidth(92)
            ck.clicked.connect(lambda _, i=item["id"]: self._do_daily(i))
            row.addWidget(ck)

            nb = _btn("✗ Gagal", "danger", h=36)
            nb.setEnabled(not done)
            if done:
                nb.setStyleSheet(
                    f"background:{_T('border')}; color:{_T('muted')};"
                    f" border-color:{_T('border')};")
            nb.setFixedWidth(82)
            nb.clicked.connect(lambda _, i=item["id"]: self._fail_daily(i))
            row.addWidget(nb)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setFixedWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        else:  # todo
            cb = QCheckBox()
            cb.setChecked(done)
            cb.setEnabled(not done)
            cb.stateChanged.connect(lambda _, i=item["id"]: self._do_todo(i))
            row.addWidget(cb)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setFixedWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        dl = _btn("🗑", "danger", h=36)
        dl.setFixedWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        dup_btn = _btn("📋", h=36)
        dup_btn.setFixedWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn("📁", h=36)
        folder_btn.setFixedWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"): 
                                self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)                                                                       

        return f

    # ── actions ───────────────────────────────────────────────────────────────
    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, self.mode)
        folder_names = ["(Tidak di folder)"] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]

        dlg = QDialog(self)
        dlg.setWindowTitle("Pindahkan ke folder")
        dlg.setFixedSize(300, 200)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        combo = QComboBox()
        for name in folder_names:
            combo.addItem(name)
        if current_folder_id is not None:
            try:
                idx = folder_ids.index(current_folder_id)
                combo.setCurrentIndex(idx)
            except ValueError:
                pass
        btn_ok = _btn("Pindahkan", "solid", dlg.accept)
        layout.addWidget(QLabel("Pilih folder:"))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.set_item_folder(self.user_id, self.mode, item_id, selected_id)
            self.load()
            SND.notify()

    def _do(self, direction: str, iid: int):
        r = db.complete_habit(self.user_id, iid, direction)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, "Info", r["msg"])
            return
        if direction == "up":
            SND.complete()
            msg = (f"✅ +{r.get('xp_gained',0)} XP,"
                   f" +{r.get('gold_gained',0):.1f} Gold!")
            if r.get("leveled_up"):
                SND.level_up()
                msg += f"\n🎉 LEVEL UP! Level {r['new_level']}!"
            _show(self, "Habit ✔", msg, "success")
        else:
            SND.error()
            _show(self, "HP Berkurang",
                  "💔 -5 HP karena kebiasaan buruk!", "warning")
        AppState.refresh()
        self.load()

    def _duplicate_habit(self, iid):
        r = db.duplicate_habit(self.user_id, iid)
        if r["ok"]:
            SND.notify()
        else:
            SND.error()
        self.load()

    def _do_daily(self, iid: int):
        r = db.complete_daily(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, "Info", r["msg"])
            return
        SND.complete()
        msg = f"✅ +{r.get('xp_gained',0)} XP!"
        if r.get("leveled_up"):
            SND.level_up()
            msg += f"\n🎉 LEVEL UP! Level {r['new_level']}!"
        _show(self, "Daily ✔", msg, "success")
        AppState.refresh()
        self.load()

    def _duplicate_daily(self, iid):
        r = db.duplicate_daily(self.user_id, iid)
        if r["ok"]:
            SND.notify()
        else:
            SND.error()
        self.load()

    def _fail_daily(self, iid: int):
        r = db.fail_daily(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, "Info", r["msg"])
            return
        SND.error()
        _show(self, "Daily Gagal", "💔 -5 HP! Streak daily reset ke 0.", "warning")
        AppState.refresh()
        self.load()

    def _do_todo(self, iid: int):
        r = db.complete_todo(self.user_id, iid)
        if not r.get("ok"):
            return
        SND.complete()
        msg = f"✅ Quest selesai! +{r.get('xp_gained',0)} XP"
        if r.get("leveled_up"):
            SND.level_up()
            msg += f"\n🎉 LEVEL UP! Level {r['new_level']}!"
        _show(self, "Quest ✔", msg, "success")
        AppState.refresh()
        self.load()

    def _delete(self, iid: int):
        fns = {"habit": db.delete_habit,
               "daily": db.delete_daily,
               "todo":  db.delete_todo}
        fns[self.mode](self.user_id, iid)
        SND.click()
        self.load()

    def _duplicate(self, iid):
        if self.mode == "habit":
            db.duplicate_habit(self.user_id, iid)
        elif self.mode == "daily":
            db.duplicate_daily(self.user_id, iid)
        else:
            db.duplicate_todo(self.user_id, iid)
        SND.click()
        self.load()

    def _edit(self, iid):
        items_map = {
            "habit": db.get_habits,
            "daily": db.get_dailies,
            "todo":  db.get_todos,
        }
        all_items = items_map[self.mode](self.user_id)
        item = next((i for i in all_items if i["id"] == iid), None)
        if not item:
            return
        dlg = EditTaskDialog(self.mode, self.user_id, item, self)
        if dlg.exec():
            self.load()

    def _open_add(self):
        dlg = AddTaskDialog(self.mode, self.user_id, self)
        if dlg.exec():
            self.load()

    def _open_folder_add(self):
        dlg = FolderDialog(self.mode, self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  SPORT TRACK PAGE  — sub-halaman per jenis olahraga
# ══════════════════════════════════════════════════════════════════════════════

class AddSportActivityDialog(QDialog):
    """Dialog untuk tambah/edit aktivitas sport."""
    def __init__(self, user_id: int, item=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.item    = item          # None = add, dict = edit
        self.setWindowTitle(
            "✏️ Edit Aktivitas Sport" if item else "➕ Tambah Aktivitas Sport")
        self.setMinimumWidth(480)
        self.setMinimumHeight(480)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Nama
        lay.addWidget(_lbl("Nama Aktivitas", size=12))
        self._name = _input(
            self.item["name"] if self.item else "Contoh: Lari pagi 5 km…")
        lay.addWidget(self._name)

        # Jenis olahraga
        lay.addWidget(_lbl("Jenis Olahraga", size=12))
        sport_opts = [
            (f"{v['icon']}  {v['name']}", k)
            for k, v in db.SPORT_TYPES.items()
        ]
        self._sport_type = _combo(sport_opts)
        if self.item:
            idx = self._sport_type.findData(self.item.get("sport_type","running"))
            if idx >= 0: self._sport_type.setCurrentIndex(idx)
        lay.addWidget(self._sport_type)

        # Intensitas
        lay.addWidget(_lbl("Intensitas", size=12))
        diff_opts = [
            ("🟢  Mudah    (+15 XP / +8 Sport Pts)",   "easy"),
            ("🟡  Sedang   (+25 XP / +15 Sport Pts)",  "medium"),
            ("🔴  Berat    (+40 XP / +25 Sport Pts)",  "hard"),
            ("💜  Ekstrem  (+60 XP / +40 Sport Pts)",  "epic"),
        ]
        self._diff = _combo(diff_opts)
        if self.item:
            idx = self._diff.findData(self.item.get("difficulty","medium"))
            if idx >= 0: self._diff.setCurrentIndex(idx)
        else:
            self._diff.setCurrentIndex(1)   # medium default
        lay.addWidget(self._diff)

        # Catatan
        lay.addWidget(_lbl("Catatan (opsional)", size=12))
        self._notes = _input(
            self.item.get("notes","") if self.item else "Catatan…")
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl("Masukkan ke Folder  (opsional)", size=12))
        _folders = db.get_task_folders(self.user_id, "sport")
        _fopts = [("📭  Tanpa Folder", None)] + [
            (f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        if self.item:
            cur_fid = self.item.get("folder_id")
            if cur_fid:
                idx = next((i for i,(_, d) in enumerate(_fopts) if d == cur_fid), 0)
                self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok_lbl = "💾 Simpan" if self.item else "➕ Tambah"
        ok = _btn(ok_lbl, "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        root.addWidget(_scrolled(content))

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, "Error", "Nama tidak boleh kosong!", "error")
            return
        sport_type = self._sport_type.currentData()
        diff       = self._diff.currentData()
        notes      = self._notes.text()
        icon       = db.SPORT_TYPES.get(sport_type, {}).get("icon", "🏅")

        folder_id = self._folder.currentData()
        if self.item:
            db.update_sport_activity(
                self.item["id"], self.user_id,
                name=name, sport_type=sport_type, icon=icon,
                difficulty=diff, notes=notes)
            db.set_item_folder(self.user_id, "sport", self.item["id"], folder_id)
        else:
            db.add_sport_activity(
                self.user_id, name, sport_type, icon, diff, notes)
            if folder_id:
                new_id = max(a["id"] for a in db.get_sport_activities(self.user_id))
                db.set_item_folder(self.user_id, "sport", new_id, folder_id)
        SND.complete()
        self.accept()


class SportTrackPage(QWidget):
    """Halaman utama SportTrack dengan sub-tab per jenis olahraga."""

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._build()
        AppState.register(self.load)

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("🏅  SportTrack", "section", 14, True))
        hdr.addStretch()
        folder_btn = _btn("📁  Folder", h=36)
        folder_btn.setFixedWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add_btn = _btn("➕  Tambah", "solid", self._open_add)
        add_btn.setFixedWidth(130)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Sport Level bar
        lvl_row = QHBoxLayout()
        self._sport_lvl_lbl = QLabel("🏅 Sport Level 1")
        self._sport_lvl_lbl.setStyleSheet(
            "color:#f0a800; font-weight:bold; font-size:13px;")
        self._sport_xp_bar = QProgressBar()
        self._sport_xp_bar.setFixedHeight(12)
        self._sport_xp_bar.setTextVisible(False)
        self._sport_xp_bar.setStyleSheet(
            "QProgressBar { background:#222; border:1px solid #555;"
            " border-radius:5px; }"
            "QProgressBar::chunk { background:#f0a800; border-radius:4px; }")
        lvl_row.addWidget(self._sport_lvl_lbl)
        lvl_row.addWidget(self._sport_xp_bar, 1)
        root.addLayout(lvl_row)

        # Tab widget — "Semua" + satu tab per jenis olahraga
        self._tabs = QTabWidget()

        # Tab "Semua"
        self._inner_all = QWidget()
        self._lay_all   = QVBoxLayout(self._inner_all)
        self._lay_all.setSpacing(8)
        self._lay_all.addStretch()
        self._tabs.addTab(_scrolled(self._inner_all), "🏅 Semua")

        # Satu tab per jenis olahraga
        self._sport_lays: dict   = {}
        self._sport_inners: dict  = {}
        for key, sport in db.SPORT_TYPES.items():
            inner = QWidget()
            lay   = QVBoxLayout(inner)
            lay.setSpacing(8)
            lay.addStretch()
            self._sport_lays[key]   = lay
            self._sport_inners[key] = inner
            self._tabs.addTab(_scrolled(inner),
                              f"{sport['icon']} {sport['name']}")

        # ── Baris filter (search + difficulty) ──
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari aktivitas...")
        self.search_input.textChanged.connect(self.load)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["Semua", "Easy", "Medium", "Hard", "Epic"])
        self.filter_combo.currentTextChanged.connect(self.load)
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.filter_combo)
        root.insertWidget(3, filter_widget)

        root.addWidget(self._tabs, 1)
        self.load()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _clear_lay(self, lay: QVBoxLayout):
        while lay.count() > 1:
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_sport_to_layout(self, lay: QVBoxLayout, container: QWidget,
                                items: list, folders: list, empty_msg: str):
        """Render sport items ke layout dengan dukungan folder collapsible."""
        if not items and not folders:
            el = _lbl(empty_msg, "sub", 13)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            lay.insertWidget(0, el)
            return

        insert_pos = 0
        folder_items: dict = {f["id"]: [] for f in folders}
        ungrouped: list    = []
        for item in items:
            fid = item.get("folder_id")
            if fid and fid in folder_items:
                folder_items[fid].append(item)
            else:
                ungrouped.append(item)

        for folder in folders:
            fw = FolderWidget(folder, "sport", self.user_id, self.load, parent=container)
            cards_in_folder = folder_items.get(folder["id"], [])
            if not cards_in_folder:
                empty_lbl = QLabel("   📭  Folder kosong")
                empty_lbl.setStyleSheet(
                    f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards_in_folder:
                    fw.add_card(self._make_card(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        for item in ungrouped:
            lay.insertWidget(insert_pos, self._make_card(item))
            insert_pos += 1

    # ── load / refresh ────────────────────────────────────────────────────────

    def load(self):
        if not AppState.user_id:
            return
        db.reset_daily_tasks(self.user_id)

        # Update sport level bar
        u = AppState.user()
        sport_lvl = u.get("sport_level", 1) or 1
        sport_xp  = u.get("sport_xp", 0)  or 0
        needed    = sport_lvl * 100
        self._sport_lvl_lbl.setText(
            f"🏅 Sport Level {sport_lvl}  ·  {sport_xp}/{needed} SP")
        self._sport_xp_bar.setMaximum(needed)
        self._sport_xp_bar.setValue(sport_xp)

        # Bersihkan semua layout
        self._clear_lay(self._lay_all)
        for lay in self._sport_lays.values():
            self._clear_lay(lay)

        activities = db.get_sport_activities(self.user_id)
        folders    = db.get_task_folders(self.user_id, "sport")

        # Filter berdasarkan search & difficulty
        search = self.search_input.text().lower()
        filter_diff = self.filter_combo.currentText().lower()
        if search:
            activities = [a for a in activities if search in a["name"].lower()]
        if filter_diff != "semua":
            activities = [a for a in activities
                          if a.get("difficulty", "").lower() == filter_diff]

        # ── Tab "Semua" ───────────────────────────────────────────────────────
        self._render_sport_to_layout(
            self._lay_all, self._inner_all, activities, folders,
            "🏅  Belum ada aktivitas sport. Klik ➕ Tambah!")

        # ── Tab per jenis ─────────────────────────────────────────────────────
        by_sport: dict = {}
        for a in activities:
            by_sport.setdefault(a["sport_type"], []).append(a)

        for key, lay in self._sport_lays.items():
            sport_nm = db.SPORT_TYPES[key]["name"]
            self._render_sport_to_layout(
                lay, self._sport_inners[key], by_sport.get(key, []), folders,
                f"Belum ada aktivitas {sport_nm}.\nKlik ➕ Tambah dan pilih jenis ini!")

    # ── card builder ──────────────────────────────────────────────────────────

    def _make_card(self, item: dict) -> QFrame:
        done = bool(item.get("done_today", False))
        f    = _card()
        row  = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        # Icon olahraga
        sport_data = db.SPORT_TYPES.get(item["sport_type"], {"icon": "🏅"})
        ico = QLabel(item.get("icon") or sport_data["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setFixedWidth(38)
        row.addWidget(ico)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        name_style = (
            f"text-decoration:line-through; color:{_T('muted')};"
            if done else
            f"color:{_T('text')}; font-weight:bold;")
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; {name_style}")
        info.addWidget(nm)

        sport_nm   = sport_data.get("name", item["sport_type"])
        streak_txt = (f"   🔥 {item['streak']} hari"
                      if item.get("streak", 0) > 0 else "")
        sub = QLabel(
            f"<span style='color:#f0a800'>{sport_nm}</span>"
            f"  ·  +{item['xp_reward']} XP"
            f"  ·  +{item['gold_reward']:.0f} G"
            f"  ·  +{item['sport_points_reward']} SP{streak_txt}")
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        if item.get("notes"):
            nl = QLabel(f"📝 {item['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(
                f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        row.addLayout(info, 1)

        # Tombol Selesai
        ck = _btn("✔ Done" if done else "✔ Selesai", h=36)
        ck.setEnabled(not done)
        if done:
            ck.setStyleSheet(
                f"background:{_T('border')}; color:{_T('muted')};"
                f" border-color:{_T('border')};")
        ck.setFixedWidth(100)
        ck.clicked.connect(lambda _, i=item["id"]: self._complete(i))
        row.addWidget(ck)

        # Tombol Edit
        edit_btn = _btn("✏️", h=36)
        edit_btn.setFixedWidth(36)
        edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
        row.addWidget(edit_btn)

        # Tombol Hapus
        dl = _btn("🗑", "danger", h=36)
        dl.setFixedWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        # Tombol Duplikat
        dup_btn = _btn("📋", h=36)
        dup_btn.setFixedWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn("📁", h=36)
        folder_btn.setFixedWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"): 
                                self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)

        return f

    # ── actions ───────────────────────────────────────────────────────────────

    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, "sport")   # ✅
        folder_names = ["(Tidak di folder)"] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]

        dlg = QDialog(self)
        dlg.setWindowTitle("Pindahkan ke folder")
        dlg.setFixedSize(300, 200)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        combo = QComboBox()
        for name in folder_names:
            combo.addItem(name)
        if current_folder_id is not None:
            try:
                idx = folder_ids.index(current_folder_id)
                combo.setCurrentIndex(idx)
            except ValueError:
                pass
        btn_ok = _btn("Pindahkan", "solid", dlg.accept)
        layout.addWidget(QLabel("Pilih folder:"))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.set_item_folder(self.user_id, "sport", item_id, selected_id)   # ✅
            self.load()
            SND.notify()

    def _complete(self, iid: int):
        r = db.complete_sport_activity(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, "Info", r["msg"])
            return
        SND.complete()
        msg = (f"🏅 Aktivitas selesai!\n"
               f"+{r.get('xp_gained', 0)} XP  ·  "
               f"+{r.get('gold_gained', 0):.1f} Gold  ·  "
               f"+{r.get('sport_points_gained', 0)} Sport Points")
        if r.get("leveled_up"):
            SND.level_up()
            msg += f"\n🎉 LEVEL UP! Level {r['new_level']}!"
        if r.get("sport_leveled_up"):
            SND.level_up()
            msg += f"\n🏅 SPORT LEVEL UP! Sport Level {r['new_sport_level']}!"
        _show(self, "Sport ✔", msg, "success")
        AppState.refresh()
        self.load()

    def _edit(self, iid: int):
        activities = db.get_sport_activities(self.user_id)
        item = next((a for a in activities if a["id"] == iid), None)
        if not item:
            return
        dlg = AddSportActivityDialog(self.user_id, item, self)
        if dlg.exec():
            self.load()

    def _delete(self, iid: int):
        db.delete_sport_activity(self.user_id, iid)
        SND.click()
        self.load()

    def _duplicate(self, activity_id):
        r = db.duplicate_sport_activity(self.user_id, activity_id)
        if r["ok"]:
             SND.click()
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        self.load()

    def _open_add(self):
        dlg = AddSportActivityDialog(self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def _open_folder_add(self):
        dlg = FolderDialog("sport", self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  ECONOMY PAGE  — track income & expense with folders, categories, sub-tabs
# ══════════════════════════════════════════════════════════════════════════════

class AddEconomyDialog(QDialog):
    """Dialog untuk tambah/edit item ekonomi."""
    def __init__(self, user_id: int, item=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.item = item   # None = add, dict = edit
        self.setWindowTitle("✏️ Edit Transaksi" if item else "➕ Tambah Transaksi")
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Nama
        lay.addWidget(_lbl("Nama Transaksi", size=12))
        self._name = _input(self.item["name"] if self.item else "Contoh: Gaji, Makan Siang...")
        lay.addWidget(self._name)

        # Icon (pilihan singkat)
        lay.addWidget(_lbl("Icon", size=12))
        icon_choices = [
            ("💰 Income", "💰"), ("💸 Expense", "💸"), ("🏦 Salary", "🏦"),
            ("🍔 Food", "🍔"), ("🚗 Transport", "🚗"), ("🏠 Rent", "🏠"),
            ("📚 Education", "📚"), ("💊 Health", "💊"), ("🎮 Entertainment", "🎮"),
            ("📈 Investment", "📈"), ("🎁 Gift", "🎁"), ("🛒 Shopping", "🛒"),
        ]
        self._icon = _combo(icon_choices)
        if self.item:
            idx = self._icon.findData(self.item.get("icon", "💰"))
            if idx >= 0:
                self._icon.setCurrentIndex(idx)
        lay.addWidget(self._icon)

        # Tipe (income/expense)
        lay.addWidget(_lbl("Tipe", size=12))
        self._type = _combo([("💚 Pemasukan (Income)", "income"), ("❤️ Pengeluaran (Expense)", "expense")])
        if self.item:
            idx = self._type.findData(self.item.get("type", "expense"))
            if idx >= 0:
                self._type.setCurrentIndex(idx)
        lay.addWidget(self._type)

        # Jumlah
        lay.addWidget(_lbl("Jumlah (Rp / Gold)", size=12))
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0")
        self._amount.setMinimumHeight(42)
        if self.item:
            self._amount.setText(str(self.item["amount"]))
        lay.addWidget(self._amount)

        # Kategori (bisa custom atau pilih dari yang sudah ada)
        lay.addWidget(_lbl("Kategori", size=12))
        self._category = QLineEdit()
        self._category.setPlaceholderText("Contoh: Makanan, Gaji, Transport, Hiburan...")
        if self.item:
            self._category.setText(self.item["category"])
        # Tambahkan label penjelasan
        cat_hint = QLabel("💡 Bebas isi apapun. Nanti akan muncul sebagai tab filter.")
        cat_hint.setStyleSheet(f"color:{_T('muted')}; font-size:10px; font-style:italic;")
        lay.addWidget(self._category)
        lay.addWidget(cat_hint)
        # Saran kategori dari DB
        self._suggest_cat = QComboBox()
        self._suggest_cat.setMinimumHeight(36)
        self._suggest_cat.addItem("-- Pilih dari yang pernah dipakai --", None)
        try:
            cats = db.get_economy_categories(self.user_id)
            for cat in cats:
                self._suggest_cat.addItem(cat, cat)
            self._suggest_cat.currentIndexChanged.connect(self._on_suggest)
        except:
            pass
        lay.addWidget(self._suggest_cat)

        # Tanggal
        lay.addWidget(_lbl("Tanggal", size=12))
        self._date = QLineEdit()
        self._date.setPlaceholderText("YYYY-MM-DD")
        from datetime import date
        self._date.setText(date.today().isoformat() if not self.item else self.item["date"])
        self._date.setMinimumHeight(42)
        lay.addWidget(self._date)

        # Catatan
        lay.addWidget(_lbl("Catatan (opsional)", size=12))
        self._notes = _input(self.item.get("notes", "") if self.item else "")
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl("Masukkan ke Folder", size=12))
        _folders = db.get_task_folders(self.user_id, "economy")
        _fopts = [("📭  Tanpa Folder", None)] + [(f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        if self.item and self.item.get("folder_id"):
            cur_fid = self.item["folder_id"]
            idx = next((i for i, (_, d) in enumerate(_fopts) if d == cur_fid), 0)
            self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok_lbl = "💾 Simpan" if self.item else "➕ Tambah"
        ok = _btn(ok_lbl, "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        root.addWidget(_scrolled(content))

    def _on_suggest(self, idx):
        if idx >= 0:
            cat = self._suggest_cat.currentData()
            if cat:
                self._category.setText(cat)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, "Error", "Nama tidak boleh kosong!", "error")
            return
        try:
            amount = float(self._amount.text().strip())
        except:
            _show(self, "Error", "Jumlah harus berupa angka!", "error")
            return
        cat = self._category.text().strip()
        if not cat:
            cat = "other"
        date_str = self._date.text().strip()
        if not date_str:
            from datetime import date
            date_str = date.today().isoformat()
        icon = self._icon.currentData()
        type_ = self._type.currentData()
        notes = self._notes.text()
        folder_id = self._folder.currentData()

        if self.item:
            db.update_economy_item(self.item["id"], self.user_id,
                                   name=name, icon=icon, type=type_, amount=amount,
                                   category=cat, date=date_str, notes=notes, folder_id=folder_id)
        else:
            db.add_economy_item(self.user_id, name, icon, type_, amount, cat, date_str, notes, folder_id)
        SND.complete()
        self.accept()


class EconomyPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._build()
        AppState.register(self.load)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl("💰  Economy Tracker", "section", 14, True))
        hdr.addStretch()
        folder_btn = _btn("📁  Folder", h=36)
        folder_btn.setFixedWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add_btn = _btn("➕  Tambah", "solid", self._open_add)
        add_btn.setFixedWidth(130)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Summary cards (total income, expense, balance)
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setSpacing(12)
        self.income_card = self._stat_card("💚 Total Pemasukan", "0", "#80c000")
        self.income_card.setToolTip("Total semua pemasukan (income)")
        self.expense_card = self._stat_card("❤️ Total Pengeluaran", "0", "#e05050")
        self.expense_card.setToolTip("Total semua pengeluaran (expense)")
        self.balance_card = self._stat_card("💎 Saldo", "0", "#4da6ff")
        self.balance_card.setToolTip("Saldo = Pemasukan - Pengeluaran")
        summary_layout.addWidget(self.income_card)
        summary_layout.addWidget(self.expense_card)
        summary_layout.addWidget(self.balance_card)
        root.addWidget(summary_widget)

        # Filter bar
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Cari transaksi...")
        self.search_input.textChanged.connect(self.load)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Semua", "Pemasukan", "Pengeluaran"])
        self.type_combo.currentTextChanged.connect(self.load)
        self.category_combo = QComboBox()
        self.category_combo.addItem("Semua Kategori", "all")
        self.category_combo.setToolTip("Filter berdasarkan kategori yang pernah kamu pakai. Kategori ditentukan saat input transaksi.")
        self.category_combo.currentIndexChanged.connect(self.load)
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.type_combo)
        filter_layout.addWidget(self.category_combo)
        root.addWidget(filter_widget)

        # Tab widget: "Semua" + per kategori dinamis
        self._tabs = QTabWidget()
        self._inner_all = QWidget()
        self._lay_all = QVBoxLayout(self._inner_all)
        self._lay_all.setSpacing(8)
        self._lay_all.addStretch()
        self._tabs.addTab(_scrolled(self._inner_all), "📋 Semua")

        self._cat_lays = {}
        self._cat_inners = {}
        root.addWidget(self._tabs, 1)
        self.load()

    def _stat_card(self, title, value, color):
        card = _card()
        card.setFixedHeight(90)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        # simpan referensi untuk update
        card.value_label = lbl_value
        return card

    def _clear_lay(self, lay: QVBoxLayout):
        while lay.count() > 1:
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _render_to_layout(self, lay: QVBoxLayout, container: QWidget, items: list, folders: list, empty_msg: str):
        if not items and not folders:
            el = _lbl(empty_msg, "sub", 13)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            lay.insertWidget(0, el)
            return

        insert_pos = 0
        folder_items = {f["id"]: [] for f in folders}
        ungrouped = []
        for item in items:
            fid = item.get("folder_id")
            if fid and fid in folder_items:
                folder_items[fid].append(item)
            else:
                ungrouped.append(item)

        for folder in folders:
            fw = FolderWidget(folder, "economy", self.user_id, self.load, parent=container)
            cards = folder_items.get(folder["id"], [])
            if not cards:
                empty_lbl = QLabel("   📭  Folder kosong")
                empty_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards:
                    fw.add_card(self._make_card(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        for item in ungrouped:
            lay.insertWidget(insert_pos, self._make_card(item))
            insert_pos += 1

    def _make_card(self, item: dict) -> QFrame:
        f = _card()
        row = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        # Icon
        ico = QLabel(item["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setFixedWidth(38)
        row.addWidget(ico)

        # Info
        info = QVBoxLayout()
        info.setSpacing(2)
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(nm)

        tipe = "Pemasukan" if item["type"] == "income" else "Pengeluaran"
        color = "#80c000" if item["type"] == "income" else "#e05050"
        amount_str = f"+{item['amount']:.0f}" if item["type"] == "income" else f"-{item['amount']:.0f}"
        sub = QLabel(f"<span style='color:{color}'>{tipe}</span>  |  {amount_str}  |  {item['category']}  |  {item['date']}")
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        if item.get("notes"):
            nl = QLabel(f"📝 {item['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        row.addLayout(info, 1)

        # Buttons
        edit_btn = _btn("✏️", h=36)
        edit_btn.setFixedWidth(36)
        edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
        row.addWidget(edit_btn)

        dl = _btn("🗑", "danger", h=36)
        dl.setFixedWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        dup_btn = _btn("📋", h=36)
        dup_btn.setFixedWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn("📁", h=36)
        folder_btn.setFixedWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"): self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)

        return f

    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, "economy")
        folder_names = ["(Tidak di folder)"] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]
        dlg = QDialog(self)
        dlg.setWindowTitle("Pindahkan ke folder")
        dlg.setFixedSize(300, 200)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        combo = QComboBox()
        for name in folder_names:
            combo.addItem(name)
        if current_folder_id is not None:
            try:
                idx = folder_ids.index(current_folder_id)
                combo.setCurrentIndex(idx)
            except ValueError:
                pass
        btn_ok = _btn("Pindahkan", "solid", dlg.accept)
        layout.addWidget(QLabel("Pilih folder:"))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.update_economy_item(item_id, self.user_id, folder_id=selected_id)
            self.load()
            SND.notify()

    def load(self):
        if not AppState.user_id:
            return

        # Update summary cards
        summary = db.get_economy_summary(self.user_id)
        self.income_card.value_label.setText(f"{summary['total_income']:.0f}")
        self.expense_card.value_label.setText(f"{summary['total_expense']:.0f}")
        self.balance_card.value_label.setText(f"{summary['balance']:.0f}")

        # Refresh category combo
        current_cat = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("Semua Kategori", "all")
        try:
            cats = db.get_economy_categories(self.user_id)
            for cat in cats:
                self.category_combo.addItem(cat, cat)
        except:
            pass
        if current_cat and current_cat != "all":
            idx = self.category_combo.findData(current_cat)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)
        self.category_combo.blockSignals(False)

        # Filter items
        type_filter = None
        type_text = self.type_combo.currentText()
        if type_text == "Pemasukan":
            type_filter = "income"
        elif type_text == "Pengeluaran":
            type_filter = "expense"

        cat_filter = self.category_combo.currentData()
        if cat_filter == "all":
            cat_filter = None
        search = self.search_input.text().strip() or None

        items = db.get_economy_items(self.user_id, type_filter, cat_filter, search)
        folders = db.get_task_folders(self.user_id, "economy")

        # Bersihkan semua tab
        self._clear_lay(self._lay_all)
        # Hapus tab kategori dinamis (kecuali "Semua")
        while self._tabs.count() > 1:
            self._tabs.removeTab(1)
        self._cat_lays.clear()
        self._cat_inners.clear()

        # Tab "Semua"
        self._render_to_layout(self._lay_all, self._inner_all, items, folders,
                               "💰 Belum ada transaksi. Klik ➕ Tambah!")

        # Tab per kategori (hanya dari items yang ada)
        by_cat = {}
        for it in items:
            cat = it["category"]
            by_cat.setdefault(cat, []).append(it)
        for cat, cat_items in by_cat.items():
            inner = QWidget()
            lay = QVBoxLayout(inner)
            lay.setSpacing(8)
            lay.addStretch()
            self._cat_lays[cat] = lay
            self._cat_inners[cat] = inner
            self._tabs.addTab(_scrolled(inner), f"📁 {cat}")
            self._render_to_layout(lay, inner, cat_items, folders, f"Tidak ada transaksi di kategori {cat}")

    def _edit(self, item_id):
        items = db.get_economy_items(self.user_id)
        item = next((i for i in items if i["id"] == item_id), None)
        if not item:
            return
        dlg = AddEconomyDialog(self.user_id, item, self)
        if dlg.exec():
            self.load()

    def _delete(self, item_id):
        db.delete_economy_item(self.user_id, item_id)
        SND.click()
        self.load()

    def _duplicate(self, item_id):
        r = db.duplicate_economy_item(self.user_id, item_id)
        if r["ok"]:
            SND.click()
        else:
            SND.error()
            _show(self, "Gagal", r.get("msg", "Gagal menduplikasi"), "error")
        self.load()

    def _open_add(self):
        dlg = AddEconomyDialog(self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def _open_folder_add(self):
        dlg = FolderDialog("economy", self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  SHOP PAGE  (real buffs, use consumables)
# ══════════════════════════════════════════════════════════════════════════════
class ShopPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._build()
        AppState.register(self.load)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)
        root.addWidget(_lbl("🏪  Item Shop & Pet Stable", "section", 14, True))
        root.addWidget(_sep())

        self._buff_bar = QLabel("")
        self._buff_bar.setWordWrap(True)
        self._buff_bar.setStyleSheet(
            f"background: {_T('panel')}; color: {_T('accent')};"
            f" border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 8px 12px; font-size: 12px;")
        root.addWidget(self._buff_bar)

        self._tabs = QTabWidget()
        self._items_inner = QWidget()
        self._items_grid  = QGridLayout(self._items_inner)
        self._items_grid.setSpacing(8)
        self._pets_inner  = QWidget()
        self._pets_grid   = QGridLayout(self._pets_inner)
        self._pets_grid.setSpacing(8)
        self._tabs.addTab(_scrolled(self._items_inner), "🎒  Items")
        self._tabs.addTab(_scrolled(self._pets_inner),  "🐾  Pets")
        root.addWidget(self._tabs)
        self.load()

    def _clear_grid(self, grid: QGridLayout):
        while grid.count():
            item = grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def load(self):
        if not AppState.user_id:
            return
        self._clear_grid(self._items_grid)
        self._clear_grid(self._pets_grid)
        u   = AppState.user()
        inv = db.get_inventory(self.user_id)
        owned = {i["item_id"]: i for i in inv}

        # ── Buff summary ──────────────────────────────────────────────────────
        buffs = []
        if u.get("xp_multiplier",  1.0) > 1.001:
            buffs.append(f"📈 XP x{u['xp_multiplier']:.2f}")
        if u.get("gold_multiplier",1.0) > 1.001:
            buffs.append(f"💰 Gold x{u['gold_multiplier']:.2f}")
        if u.get("boss_damage_bonus", 0) > 0:
            buffs.append(f"⚔️ Boss +{u['boss_damage_bonus']:.0f} DMG")
        if u.get("hp_damage_reduction", 0) > 0:
            buffs.append(f"🛡️ -{u['hp_damage_reduction']:.0f} HP taken")
        if u.get("mp_bonus", 0) > 0:
            buffs.append(f"💙 +{u['mp_bonus']} Max MP")
        if u.get("has_revive"):
            buffs.append("🗿 Totem aktif")
        self._buff_bar.setText(
            "⚡ Buff aktif:  " + (
                "  ·  ".join(buffs) if buffs
                else "Beli item untuk mendapatkan buff permanen!"))
        self._buff_bar.setStyleSheet(
            f"background: {_T('panel')}; color: {_T('accent')};"
            f" border: 1px solid {_T('border')};"
            f" border-radius: 6px; padding: 8px 12px; font-size: 12px;")

        # ── Items ─────────────────────────────────────────────────────────────
        COLS = 4
        for idx, (iid, item) in enumerate(db.SHOP_ITEMS.items()):
            f   = _card()
            cl  = QVBoxLayout(f)
            cl.setContentsMargins(10, 10, 10, 10)
            cl.setSpacing(4)

            cl.addWidget(QLabel(item["icon"],
                                alignment=Qt.AlignmentFlag.AlignCenter))
            nm = QLabel(item["name"])
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet(
                f"font-size:12px; font-weight:bold; color:{_T('text')};")
            cl.addWidget(nm)
            bd = QLabel(item["buff_desc"])
            bd.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bd.setWordWrap(True)
            bd.setStyleSheet(f"font-size:10px; color:{_T('accent')};")
            cl.addWidget(bd)
            tp = QLabel(item["type"].title())
            tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tp.setStyleSheet(f"font-size:10px; color:{_T('muted')};")
            cl.addWidget(tp)

            if iid in owned:
                qty = owned[iid]["quantity"]
                ol  = QLabel("✔ Dimiliki")
                ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ol.setStyleSheet(
                    f"color:{_T('light')}; font-size:11px; font-weight:bold;")
                cl.addWidget(ol)
                if item["type"] == "consumable":
                    ub = _btn(f"Gunakan ({qty}×)", "diamond", h=30)
                    ub.clicked.connect(
                        lambda _, i=iid: self._use(i))
                    cl.addWidget(ub)
                    bb = _btn("Beli Lagi", "gold", h=30)
                    bb.clicked.connect(
                        lambda _, i=iid: self._buy(i))
                    cl.addWidget(bb)
            else:
                cl.addWidget(QLabel(
                    f"💰 {item['cost']} G",
                    alignment=Qt.AlignmentFlag.AlignCenter))
                bb = _btn("Beli", "gold", h=30)
                bb.clicked.connect(lambda _, i=iid: self._buy(i))
                cl.addWidget(bb)
            self._items_grid.addWidget(f, idx // COLS, idx % COLS)

        # ── Pets ──────────────────────────────────────────────────────────────
        user_pets  = db.get_user_pets(self.user_id)
        owned_pets = {p["pet_id"] for p in user_pets}
        active_pet = next((p["pet_id"] for p in user_pets
                           if p["is_active"]), None)
        for idx, (pid, pet) in enumerate(db.PETS_DATA.items()):
            f   = _card()
            cl  = QVBoxLayout(f)
            cl.setContentsMargins(10, 10, 10, 10)
            cl.setSpacing(4)
            ico = QLabel(pet["icon"])
            ico.setFont(QFont("Segoe UI", 28))
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(ico)
            nm = QLabel(pet["name"])
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet(
                f"font-size:12px; font-weight:bold; color:{_T('text')};")
            cl.addWidget(nm)
            bns = QLabel(pet["bonus"])
            bns.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bns.setStyleSheet("font-size:10px; color:#4dd9e0;")
            bns.setWordWrap(True)
            cl.addWidget(bns)
            if pid in owned_pets:
                if pid == active_pet:
                    al = QLabel("✔ AKTIF")
                    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    al.setStyleSheet(
                        "color:#4dd9e0; font-size:11px; font-weight:bold;")
                    cl.addWidget(al)
                else:
                    eq = _btn("Aktifkan", "diamond", h=30)
                    eq.clicked.connect(lambda _, p=pid: self._equip(p))
                    cl.addWidget(eq)
            else:
                cl.addWidget(QLabel(
                    f"💰 {pet['cost']} G",
                    alignment=Qt.AlignmentFlag.AlignCenter))
                ab = _btn("Adopsi", "gold", h=30)
                ab.clicked.connect(lambda _, p=pid: self._adopt(p))
                cl.addWidget(ab)
            self._pets_grid.addWidget(f, idx // 3, idx % 3)

    def _buy(self, iid):
        r = db.buy_item(self.user_id, iid)
        if r["ok"]:
            SND.buy()
            _show(self, "Berhasil!", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()

    def _use(self, iid):
        r = db.use_item(self.user_id, iid)
        if r.get("ok"):
            SND.complete()
            _show(self, "Item Digunakan", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal",
                  r.get("msg", "Item tidak bisa digunakan."), "error")
        AppState.refresh()

    def _adopt(self, pid):
        r = db.adopt_pet(self.user_id, pid)
        if r["ok"]:
            SND.buy()
            _show(self, "Pet Diadopsi!", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()

    def _equip(self, pid):
        r = db.equip_pet(self.user_id, pid)
        SND.notify()
        _show(self, "Pet Aktif", r["msg"], "success")
        AppState.refresh()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ================================================================== #
class PetsPage(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self._build()
        AppState.register(self.load)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        self.title = _lbl("🐾  Pelihara Pet", "section", 14, True)
        layout.addWidget(self.title)
        layout.addWidget(_sep())
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(12)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.load()

    def load(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        pets = db.get_user_pets(self.user_id)
        if not pets:
            empty = _lbl("🐣 Belum punya pet. Beli di Shop dulu!", "sub", 13)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(empty, 0, 0)
            return
        # Atur jumlah kolom berdasarkan lebar (responsif)  
        for i, p in enumerate(pets):
            pet_data = db.PETS_DATA.get(p["pet_id"], {})
            card = _card()
            card.setFixedWidth(260)
            vlay = QVBoxLayout(card)
            vlay.setSpacing(4)
            vlay.setContentsMargins(8, 8, 8, 8)

            # Header baris
            top = QHBoxLayout()
            ico = QLabel(pet_data.get("icon", "🐾"))
            ico.setFont(QFont("Segoe UI", 22))
            top.addWidget(ico)
            name = QLabel(pet_data.get("name", p["pet_id"]))
            name.setStyleSheet("font-size:13px; font-weight:bold;")
            top.addWidget(name, 1)
            if p["is_active"]:
                active_lbl = QLabel("✔ AKTIF")
                active_lbl.setStyleSheet("color:#80c000; font-size:10px;")
                top.addWidget(active_lbl)
            vlay.addLayout(top)

            # Level & EXP
            lvl_lbl = QLabel(f"Lv. {p['level']}")
            lvl_lbl.setStyleSheet("color:#f0a800; font-size:11px;")
            vlay.addWidget(lvl_lbl)
            exp_bar = QProgressBar()
            exp_needed = p["level"] * 100
            exp_bar.setMaximum(exp_needed)
            exp_bar.setValue(int(p["exp"]))
            exp_bar.setFormat(f"EXP: {p['exp']}/{exp_needed}")
            exp_bar.setFixedHeight(8)
            vlay.addWidget(exp_bar)

            # Hunger
            hunger_bar = QProgressBar()
            hunger_bar.setMaximum(100)
            hunger_bar.setValue(int(p["hunger"]))
            hunger_bar.setFormat(f"🥩 {p['hunger']}/100")
            hunger_bar.setFixedHeight(12)
            hunger_bar.setStyleSheet("QProgressBar::chunk { background: #f0a800; }")
            vlay.addWidget(hunger_bar)

            # Buff (bisa diketik kecil)
            base_buff = pet_data.get("base_buff", {})
            scale = 1 + (p["level"]-1)*0.02
            buff_text = []
            if "xp_pct" in base_buff:
                buff_text.append(f"📈 +{base_buff['xp_pct']*scale:.0f}% XP")
            if "gold_pct" in base_buff:
                buff_text.append(f"💰 +{base_buff['gold_pct']*scale:.0f}% Gold")
            if "boss_dmg" in base_buff:
                buff_text.append(f"⚔️ +{base_buff['boss_dmg']*scale:.0f} DMG")
            if "hp_reduc" in base_buff:
                buff_text.append(f"🛡️ -{base_buff['hp_reduc']*scale:.0f} HP")
            if buff_text:
                buff_label = QLabel(" | ".join(buff_text))
                buff_label.setStyleSheet("font-size:9px; color:#aaa;")
                vlay.addWidget(buff_label)

            # Tombol
            btn_row = QHBoxLayout()
            feed_btn = _btn("🍖 10G", h=28)
            feed_btn.setFixedWidth(70)
            feed_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._feed(pid))
            train_btn = _btn("🏋️ 5G", h=28)
            train_btn.setFixedWidth(70)
            train_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._train(pid))
            equip_btn = _btn("⭐ Equip", "diamond", h=28)
            equip_btn.setFixedWidth(80)
            equip_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._equip(pid))
            btn_row.addWidget(feed_btn)
            btn_row.addWidget(train_btn)
            btn_row.addWidget(equip_btn)
            vlay.addLayout(btn_row)

            self.grid.addWidget(card, i // 3, i % 3)

    def _feed(self, pet_id):
        r = db.feed_pet(self.user_id, pet_id)
        self._show_result(r)
        self.load()
        AppState.refresh()

    def _train(self, pet_id):
        r = db.train_pet(self.user_id, pet_id)
        self._show_result(r)
        self.load()
        AppState.refresh()

    def _equip(self, pet_id):
        r = db.equip_pet(self.user_id, pet_id)
        self._show_result(r)
        self.load()
        AppState.refresh()

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, "Berhasil", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
# GUILD / BOSS PAGE — FIXED
# ══════════════════════════════════════════════════════════════════════════════
class GuildPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 16, 20, 16)
        self._root.setSpacing(10)
        self._boss_info = None
        self._tier_cb = None
        self._boss_cb = None
        AppState.register(self.load)
        self.load()

    def _clear(self):
        while self._root.count():
            item = self._root.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._boss_info = None
        self._tier_cb = None
        self._boss_cb = None

    def load(self):
        if not AppState.user_id:
            return
        self._clear()
        self._root.addWidget(_lbl("⚔️  Guild & Boss Battle", "section", 14, True))
        self._root.addWidget(_sep())

        u = AppState.user()
        pid = u.get("guild_id")
        if not pid:
            self._no_guild()
            return

        data    = db.get_guild(pid)
        guild   = data.get("guild", {})
        members = data.get("members", [])
        boss    = data.get("boss")

        # Guild header
        hrow_w = QWidget()
        hrow = QHBoxLayout(hrow_w)
        hrow.setContentsMargins(0, 0, 0, 0)
        hrow.addWidget(_lbl(f"🏰  {guild.get('name','')}  (ID: {pid})", "section", 13, True))
        hrow.addStretch()
        leave = _btn("Keluar", "danger", lambda: self._leave(), 34)
        leave.setFixedWidth(80)
        hrow.addWidget(leave)
        chat_guild_btn = _btn("💬 Chat Guild", "diamond", self._open_guild_chat)
        hrow.addWidget(chat_guild_btn)
        self._root.addWidget(hrow_w)

        if guild.get("description"):
            self._root.addWidget(_lbl(f"📝  {guild['description']}", "sub", 12))
        if u["id"] == guild.get("leader_id"):
            edit_bio_btn = _btn("✏️ Edit Deskripsi", "flat", self._edit_guild_bio)
            self._root.addWidget(edit_bio_btn)

        # Members
        mg = QGroupBox(f"👥 Anggota ({len(members)})")
        ml = QGridLayout(mg)
        ml.setSpacing(8)
        for i, m in enumerate(members):
            f   = _card()
            cl  = QVBoxLayout(f)
            cl.setContentsMargins(10, 8, 10, 8)
            cl.setSpacing(4)
            cls = db.AVATAR_CLASSES.get(m.get("avatar_class", "warrior"), {})
            alive = m["hp"] > 0
            cl.addWidget(_lbl(f"{cls.get('icon','⚔️')} {m['display_name']}  Lv.{m['level']}", size=12))
            pb = QProgressBar()
            pb.setMaximum(int(m["max_hp"]))
            pb.setValue(int(m["hp"]))
            pb.setFixedHeight(8)
            pb.setStyleSheet(f"QProgressBar::chunk {{ background:{'#7bbf3e' if alive else '#e05050'}; border-radius:3px; }}")
            cl.addWidget(pb)
            if u["id"] == guild.get("leader_id") and m["id"] != u["id"]:
                kick_btn = _btn("🚪 Kick", "danger", h=24)
                kick_btn.setFixedWidth(50)
                kick_btn.clicked.connect(lambda _, uid=m["id"]: self._kick_member(uid))
                cl.addWidget(kick_btn)
            if not alive:
                dl = _lbl("💀 HP 0", size=10)
                dl.setStyleSheet("color:#e05050;")
                dl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cl.addWidget(dl)
            ml.addWidget(f, i // 4, i % 4)
        self._root.addWidget(mg)

        # Skill row
        skill = db.CLASS_SKILLS.get(u.get("avatar_class", "warrior"), {})
        sr_w = QWidget()
        sr = QHBoxLayout(sr_w)
        sr.setContentsMargins(0, 0, 0, 0)
        sr.addWidget(_lbl(f"💙 {u['mp']}/{u['max_mp']} MP  —  Skill: {skill.get('icon','')} {skill.get('name','')} (cost {skill.get('mp_cost',10)} MP)", "sub", 12))
        sr.addStretch()
        sk = _btn(f"{skill.get('icon','⚡')} Gunakan Skill", "diamond", h=36)
        sk.setFixedWidth(180)
        sk.clicked.connect(self._skill)
        sr.addWidget(sk)
        self._root.addWidget(sr_w)

        # Boss section
        bg = QGroupBox("👹 Boss Battle")
        bl = QVBoxLayout(bg)
        if boss:
            self._active_boss(bl, boss, u)
        else:
            self._boss_selector(bl, guild, u)
        self._root.addWidget(bg)
        # Tampilkan undangan masuk
        self._show_invites()
        
        # Tampilkan permintaan join (hanya untuk leader)
        if guild and isinstance(guild, dict) and guild.get("id") and u["id"] == guild.get("leader_id"):
            self._show_join_requests(guild["id"])
        
        # Tampilkan transfer leader jika ada
        self._show_leader_transfers()
        self._root.addStretch()

        # Tampilkan hadiah boss yang belum diklaim
        self._show_unclaimed_rewards()

    def _show_unclaimed_rewards(self):
        rewards = db.get_unclaimed_boss_rewards(self.user_id)
        if not rewards:
            return
        group = QGroupBox("🎁 Hadiah Boss Belum Diklaim")
        vlay = QVBoxLayout(group)
        for r in rewards:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{r['boss_name']}  (+{r['xp_reward']} XP, +{r['gold_reward']} Gold)"))
            claim_btn = _btn("Klaim Sekarang", "solid", h=30)
            claim_btn.clicked.connect(lambda _, rid=r["id"]: self._claim_reward(rid))
            row.addWidget(claim_btn)
            vlay.addLayout(row)
        self._root.addWidget(group)

    def _claim_reward(self, reward_id):
        r = db.claim_boss_reward(reward_id, self.user_id)
        if r["ok"]:
            SND.complete()
            if r.get("leveled_up"):
                SND.level_up()
            _show(self, "Berhasil", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()
        self.load()  

    def _open_guild_chat(self):
        u = AppState.user()
        gid = u.get("guild_id")
        if not gid: return
        dlg = GuildChatDialog(gid, self.user_id, self)
        dlg.exec()

    def _edit_guild_bio(self):
        from PyQt6.QtWidgets import QInputDialog
        u = AppState.user()
        gid = u.get("guild_id")
        if not gid: return
        guild_data = db.get_guild(gid)
        old_desc = guild_data.get("guild", {}).get("description", "")
        new_desc, ok = QInputDialog.getMultiLineText(self, "Edit Deskripsi Guild", "Deskripsi baru:", old_desc)
        if ok and new_desc != old_desc:
            db.update_guild(gid, description=new_desc)
            SND.notify()
            _show(self, "Sukses", "Deskripsi guild diperbarui!", "success")
            self.load()

    def _no_guild(self):
        self._root.addWidget(_lbl("Kamu belum bergabung ke guild manapun.", "sub", 13))
        self._root.addSpacing(8)

        cg = QGroupBox("⚔️ Buat Guild Baru")
        cl = QVBoxLayout(cg)
        n_in = _input("Nama guild…")
        d_in = _input("Deskripsi (opsional)…")
        cl.addWidget(_lbl("Nama", size=12)); cl.addWidget(n_in)
        cl.addWidget(_lbl("Deskripsi", size=12)); cl.addWidget(d_in)
        def _create():
            n = n_in.text().strip()
            if n:
                r = db.create_guild(self.user_id, n, d_in.text())
                SND.notify()
                _show(self, "Guild Dibuat", r["msg"], "success")
                AppState.refresh()
        cl.addWidget(_btn("⚔️ Buat Guild", "solid", _create, 40))
        self._root.addWidget(cg)
        
        # Ganti jg (join langsung) dengan request join
        rg = QGroupBox("📝 Kirim Permintaan ke Guild (masukkan ID)")
        rl = QVBoxLayout(rg)
        sp = QSpinBox()
        sp.setRange(1, 99999)
        sp.setMinimumHeight(42)
        rl.addWidget(sp)
        def _request():
            r = db.send_guild_request(self.user_id, sp.value())
            if r["ok"]:
                SND.notify()
                _show(self, "Berhasil", r["msg"], "success")
            else:
                SND.error()
                _show(self, "Gagal", r["msg"], "error")
        rl.addWidget(_btn("📨 Kirim Permintaan", "solid", _request, 40))
        self._root.addWidget(rg)

    def _leave(self):
        r = db.leave_guild_with_transfer(self.user_id)   # <-- GANTI
        SND.click()
        _show(self, "Guild", r["msg"])
        AppState.refresh()
        self.load()

    def _kick_member(self, target_id):
        u = AppState.user()
        r = db.kick_guild_member(u.get("guild_id"), u["id"], target_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        self.load()    

    def _active_boss(self, lay, boss, u):
        tc   = db.BOSS_TIER_COLOR.get(boss.get("boss_tier","normal"), "#f0a800")
        hp   = boss["boss_hp"]
        mhp  = boss["boss_max_hp"]
        lay.addWidget(_lbl(f"{boss['boss_icon']}  {boss['boss_name']}  [{boss.get('boss_tier','?').upper()}]", size=15, bold=True))
        lay.addWidget(_lbl(f"HP: {hp:.0f} / {mhp:.0f}", "sub", 12))
        pb = QProgressBar()
        pb.setMaximum(int(mhp))
        pb.setValue(int(hp))
        pb.setFixedHeight(20)
        pb.setStyleSheet(f"QProgressBar::chunk {{ background:{tc}; border-radius:6px; }}")
        lay.addWidget(pb)
        dmg_bonus = u.get("boss_damage_bonus", 0)
        lay.addWidget(_lbl(f"⚔️ Boss ATK: {boss['boss_attack']}  ·  Damage kamu: 25 + {dmg_bonus:.0f} bonus = {25+dmg_bonus:.0f} total", "sub", 12))
        if u["hp"] <= 0:
            warn = QLabel("❌ HP kamu 0! Tidak bisa menyerang.\nGunakan Golden Apple di Shop, atau skill Healer.")
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#e05050; font-weight:bold; font-size:13px;")
            lay.addWidget(warn)
            qh = _btn("🍎 Gunakan Golden Apple (jika punya)", "gold", h=40)
            qh.clicked.connect(self._quick_heal)
            lay.addWidget(qh)
            return
        atk = _btn(f"⚔️  Serang!  ({25 + dmg_bonus:.0f} DMG)", "solid", self._attack, 48)
        lay.addWidget(atk)

    def _boss_selector(self, lay, guild, u):
        lay.addWidget(_lbl("Tidak ada boss aktif. Pilih boss dan mulai battle!", "sub", 12))

        tier_row = QHBoxLayout()
        tier_row.addWidget(_lbl("Filter Tier:", size=12))
        self._tier_cb = _combo([("Semua", "all")] + [(t.title(), t) for t in db.BOSS_TIER_ORDER])
        user_level = u["level"]

        def on_tier_changed():
            self._fill_boss_cb(user_level)
            self._update_boss_info()

        self._tier_cb.currentIndexChanged.connect(on_tier_changed)
        tier_row.addWidget(self._tier_cb)
        tier_row.addStretch()
        lay.addLayout(tier_row)

        self._boss_cb = QComboBox()
        self._boss_cb.setMinimumHeight(42)
        self._boss_info = QLabel("")
        self._boss_info.setWordWrap(True)
        self._boss_info.setTextFormat(Qt.TextFormat.RichText)

        self._fill_boss_cb(user_level)

        self._boss_cb.currentIndexChanged.connect(self._update_boss_info)
        lay.addWidget(self._boss_cb)
        lay.addWidget(self._boss_info)

        self._update_boss_info()

        is_leader = (u["id"] == guild.get("leader_id"))
        sb = _btn("👹 Mulai Boss Battle!", "danger" if is_leader else "flat", h=46)
        if is_leader:
            sb.clicked.connect(self._start_boss)
        else:
            sb.setEnabled(False)
            sb.setText("👹 Hanya leader yang bisa mulai")
        lay.addWidget(sb)

    def _fill_boss_cb(self, user_level: int):
        if not hasattr(self, "_boss_cb") or self._boss_cb is None:
            return
        self._boss_cb.blockSignals(True)
        self._boss_cb.clear()

        tier = self._tier_cb.currentData() if self._tier_cb else "all"
        for bid, bd in db.BOSSES.items():
            if tier != "all" and bd["tier"] != tier:
                continue
            lock = "🔒 " if user_level < bd.get("min_level", 1) else ""
            self._boss_cb.addItem(
                f"{lock}{bd['icon']} {bd['name']} [{bd['tier'].upper()}]  HP:{bd['hp']}  Lv.{bd['min_level']}+",
                bid)
        self._boss_cb.blockSignals(False)

    def _update_boss_info(self):
        if not isinstance(self._boss_info, QLabel):
            return
        if not self._boss_cb or self._boss_cb.count() == 0:
            return
        bid = self._boss_cb.currentData()
        bd  = db.BOSSES.get(bid, {})
        u   = AppState.user()
        tc  = db.BOSS_TIER_COLOR.get(bd.get("tier", "normal"), "#f0a800")
        ok  = u.get("level", 1) >= bd.get("min_level", 1)
        self._boss_info.setText(
            f"<span style='color:{tc}'>{bd.get('icon','')} {bd.get('name','')} — Tier: {bd.get('tier','?').upper()}</span>"
            f"  |  HP: {bd.get('hp','?')}  ·  ATK: {bd.get('atk','?')}  ·  +{bd.get('xp','?')} XP  ·  +{bd.get('gold','?')} Gold"
            f"  |  Min Level: {bd.get('min_level',1)}  {'✅' if ok else '❌ Level Kurang'}")

    def _start_boss(self):
        u   = AppState.user()
        bid = self._boss_cb.currentData()
        r   = db.start_boss(u.get("guild_id"), bid, u["level"])
        if r["ok"]:
            SND.boss_hit()
            _show(self, "Boss Muncul!", r["msg"], "warning")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()

    def _attack(self):
        u = AppState.user()
        if u["hp"] <= 0:
            SND.error()
            _show(self, "HP Habis!", "HP kamu 0! Tidak bisa menyerang.\nGunakan Consumable atau skill Healer.", "error")
            return
        r = db.attack_boss(self.user_id, u.get("guild_id"), 25)
        if not r.get("ok"):
            SND.error()
            _show(self, "Tidak Bisa Menyerang", r["msg"], "error")
            # Tambahkan log ke crash.log
            with open("crash.log", "a", encoding="utf-8") as f:
                f.write(f"{datetime.now()} - Attack error: {r.get('msg')}\n")
            return
        if r.get("defeated"):
            SND.boss_dead()
            _show(self, "VICTORY! 🏆", r["msg"], "success")
            self.load()
        else:
            SND.boss_hit()
            u2 = AppState.user()
            msg = f"💥 {r['total_dmg']:.0f} DMG!\nHP Boss: {r['remaining_hp']:.0f}\n❤️ HP kamu: {u2['hp']}"
            if r.get("revived"):
                msg += "\n🗿 Totem menyelamatkanmu!"
            _show(self, "Serangan!", msg)
        AppState.refresh()

    def _quick_heal(self):
        r = db.use_item(self.user_id, "golden_apple")
        if r.get("ok"):
            SND.complete()
            _show(self, "HP Dipulihkan", r["msg"], "success")
        else:
            _show(self, "Tidak Ada Item", "Tidak punya Golden Apple.\nBeli di Shop terlebih dahulu!", "warning")
        AppState.refresh()

    def _skill(self):
        r = db.use_class_skill(self.user_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Skill Digunakan!", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()

    def _show_leader_transfers(self):
        conn = db.get_conn()
        gid = AppState.user().get("guild_id")
        if not gid:
            conn.close()
            return
        rows = conn.execute("""
            SELECT * FROM guild_leader_transfers
            WHERE guild_id=? AND status='pending'
        """, (gid,)).fetchall()
        conn.close()
        if not rows:
            return
        transfers = [dict(r) for r in rows]
        group = QGroupBox("👑 Pergantian Leader")
        vlay = QVBoxLayout(group)
        for t in transfers:
            row = QHBoxLayout()
            row.addWidget(QLabel("Leader sebelumnya keluar. Klik Terima untuk menjadi leader baru!"))
            accept = _btn("✅ Terima", h=28)
            accept.clicked.connect(lambda _, tid=t["id"]: self._accept_leader(tid))
            row.addWidget(accept)
            vlay.addLayout(row)
        self._root.addWidget(group)

    def _accept_leader(self, transfer_id):
        r = db.accept_leader_transfer(self.user_id, transfer_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        self.load()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

    def _show_join_requests(self, guild_id):
        requests = db.get_guild_requests(guild_id)
        if not requests:
            return
        group = QGroupBox("📥 Permintaan Bergabung")
        vlay = QVBoxLayout(group)
        for req in requests:
            if not req.get("display_name") or not req.get("username") or not req.get("id"):
                continue
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{req['display_name']} (@{req['username']})"))
            accept = _btn("✅ Terima", h=28)
            accept.clicked.connect(lambda _, rid=req["id"]: self._accept_join(rid))
            reject = _btn("❌ Tolak", "danger", h=28)
            reject.clicked.connect(lambda _, rid=req["id"]: self._reject_join(rid))
            row.addWidget(accept)
            row.addWidget(reject)
            vlay.addLayout(row)
        self._root.addWidget(group)

    def _accept_join(self, request_id):
        u = AppState.user()
        r = db.accept_guild_request(u.get("guild_id"), u["id"], request_id)
        self._show_result(r)
        self.load()

    def _reject_join(self, request_id):
        u = AppState.user()
        r = db.reject_guild_request(u.get("guild_id"), u["id"], request_id)
        self._show_result(r)
        self.load()

    def _show_invites(self):
        invites = db.get_guild_invites(self.user_id)
        if not invites:
            return
        invite_group = QGroupBox("📨 Undangan Masuk")
        vlay = QVBoxLayout(invite_group)
        for inv in invites:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"Dari Guild: {inv['guild_name']}"))
            accept_btn = _btn("✅ Terima", h=28)
            accept_btn.clicked.connect(lambda _, iid=inv["id"]: self._accept_invite(iid))
            reject_btn = _btn("❌ Tolak", "danger", h=28)
            reject_btn.clicked.connect(lambda _, iid=inv["id"]: self._reject_invite(iid))
            row.addWidget(accept_btn)
            row.addWidget(reject_btn)
            vlay.addLayout(row)
        self._root.addWidget(invite_group)

    def _accept_invite(self, invite_id):
        r = db.accept_invite(self.user_id, invite_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Berhasil", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()
        self.load()

    def _reject_invite(self, invite_id):
        r = db.reject_invite(self.user_id, invite_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Info", r["msg"], "info")
        self.load()

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        
# ══════════════════════════════════════════════════════════════════════════════
#  STATS PAGE
# ══════════════════════════════════════════════════════════════════════════════
class StatsPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 16, 20, 16)
        self._root.setSpacing(10)
        AppState.register(self.load)
        self.load()

    def _clear(self):
        while self._root.count():
            i = self._root.takeAt(0)
            if i.widget():
                i.widget().deleteLater()

    def load(self):
        if not AppState.user_id:
            return
        self._clear()
        self._root.addWidget(
            _lbl("📊  Statistik & Progress", "section", 14, True))
        self._root.addWidget(_sep())
        # Tombol ekspor
        export_btn = _btn("📎 Ekspor ke CSV", "solid", self._export_data)
        self._root.addWidget(export_btn)
        self._root.addWidget(_sep())

        s = db.get_stats(self.user_id)
        u = s["user"]
        # Sport stats
        ss = db.get_sport_stats(self.user_id)
        inner = QWidget()
        il    = QVBoxLayout(inner)
        il.setSpacing(12)
        il.setContentsMargins(0, 0, 0, 0)

        eco_summary = db.get_economy_summary(self.user_id)
        eco_count = db.get_economy_count(self.user_id)

        # ── Main grid ─────────────────────────────────────────────────────────
        data = [
            ("⭐ Level",             str(u["level"]),                          "#80c000"),
            ("🔥 Streak Terpanjang", f"{s['max_streak']} hari",               "#f0a800"),
            ("✅ Habit Hari Ini",    f"{s['habits_done_today']}/{s['habits_total']}", _T("light")),
            ("📅 Daily Hari Ini",    f"{s['dailies_done_today']}/{s['dailies_total']}","#4da6ff"),
            ("📜 Quest Selesai",     f"{s['todos_done']}/{s['todos_total']}",  "#a97fff"),
            ("👹 Boss Dikalahkan",   str(s["bosses_killed"]),                  "#e05050"),
            ("💰 Total Gold Earned", f"{u.get('total_gold_earned',0):.0f}",   "#f0a800"),
            ("🧪 Total XP Earned",   str(u.get("total_xp_earned", 0)),         "#80c000"),
            ("🎒 Item Dimiliki",     str(s["inv_count"]),                      "#4da6ff"),
            ("🐾 Pet Diadopsi",      str(s["pet_count"]),                      "#a97fff"),
            ("❤️ HP Saat Ini",       f"{u['hp']}/{u['max_hp']}",               "#e05050"),
            ("💙 MP Saat Ini",       f"{u['mp']}/{u['max_mp']}",               "#4da6ff"),
            # Sport stats
            ("🏅 Sport Level",       str(ss["sport_level"]),                   "#f0a800"),
            ("⚡ Total Sport Pts",   str(ss["total_sport_points_earned"]),     "#f0a800"),  
            ("🏃 Sport Hari Ini",    f"{ss['done_sport_today']}/{ss['total_sport']}", "#4dd9e0"),
            ("🔥 Sport Streak Max",  f"{ss['max_sport_streak']} hari",         "#ff8c42"),
        ]
        data.extend([
            ("💰 Total Pemasukan", f"{eco_summary['total_income']:.0f}", "#80c000"),
            ("💸 Total Pengeluaran", f"{eco_summary['total_expense']:.0f}", "#e05050"),
            ("💎 Saldo", f"{eco_summary['balance']:.0f}", "#4da6ff"),
            ("📊 Jumlah Transaksi", str(eco_count), "#f0a800"),
        ])

        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (lbl_t, val_t, color) in enumerate(data):
            f  = _card()
            cl = QVBoxLayout(f)
            cl.setContentsMargins(12, 12, 12, 12)
            lb = QLabel(lbl_t)
            lb.setObjectName("sub")
            lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vl = QLabel(val_t)
            vl.setStyleSheet(
                f"color:{color}; font-size:20px; font-weight:bold;")
            vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.addWidget(lb)
            cl.addWidget(vl)
            grid.addWidget(f, i // 4, i % 4)
        il.addLayout(grid)

        # ── Weekly XP bars ────────────────────────────────────────────────────
        if s["weekly"]:
            wg = QGroupBox("📈 XP per Hari (7 hari terakhir)")
            wl = QVBoxLayout(wg)
            max_xp = max((r["xp"] or 0 for r in s["weekly"]), default=1)
            for row in s["weekly"]:
                xp  = row["xp"] or 0
                day = row["day"][5:]
                rl  = QHBoxLayout()
                rl.addWidget(QLabel(day))
                pb = QProgressBar()
                pb.setMaximum(max(max_xp, 1))
                pb.setValue(int(xp))
                pb.setToolTip(f"📅 {row['day']}\n⭐ {xp} XP / 🪙 {row['gold']} Gold")
                pb.setFormat(f" {xp} XP")
                pb.setFixedHeight(22)
                rl.addWidget(pb, 1)
                wl.addLayout(rl)
            il.addWidget(wg)

        # ── Economy weekly ─────────────────────────────────────────────────────
        eco_weekly = db.get_economy_weekly(self.user_id)
        if eco_weekly:
            eco_group = QGroupBox("💰 Ekonomi 7 Hari Terakhir (Pemasukan/Pengeluaran)")
            eco_layout = QVBoxLayout(eco_group)
            max_val = max(max(r.get("income",0) for r in eco_weekly), max(r.get("expense",0) for r in eco_weekly)) or 1
            max_val = int(max_val) + 1   # Konversi ke integer dan +1 agar progress bar tidak penuh jika nilai sama dengan maks
            for row in eco_weekly:
                day = row["day"][5:]  # MM-DD
                inc = row["income"] or 0
                exp = row["expense"] or 0
                row_layout = QHBoxLayout()
                row_layout.addWidget(QLabel(day, minimumWidth=50))
                
                # Progress bar income
                inc_pb = QProgressBar()
                inc_pb.setMaximum(max_val)
                inc_pb.setValue(int(inc))
                inc_pb.setFormat(f"💚 +{inc:.0f}")
                inc_pb.setStyleSheet("QProgressBar::chunk { background: #80c000; }")
                row_layout.addWidget(inc_pb, 2)
                
                # Progress bar expense
                exp_pb = QProgressBar()
                exp_pb.setMaximum(max_val)
                exp_pb.setValue(int(exp))
                exp_pb.setFormat(f"❤️ -{exp:.0f}")
                exp_pb.setStyleSheet("QProgressBar::chunk { background: #e05050; }")
                row_layout.addWidget(exp_pb, 2)
                
                eco_layout.addLayout(row_layout)
            il.addWidget(eco_group)

        # ── Buff summary ──────────────────────────────────────────────────────
        bg = QGroupBox("⚡ Buff Aktif")
        bl = QVBoxLayout(bg)
        lines = []
        
        if u.get("xp_multiplier", 1.0) > 1.001:
            lines.append(f"📈 XP Multiplier: ×{u['xp_multiplier']:.2f}")
        if u.get("gold_multiplier", 1.0) > 1.001:
            lines.append(f"💰 Gold Multiplier: ×{u['gold_multiplier']:.2f}")
        if u.get("boss_damage_bonus", 0) > 0:
            lines.append(f"⚔️ Boss Damage Bonus: +{u['boss_damage_bonus']:.0f}")
        if u.get("hp_damage_reduction", 0) > 0:
            lines.append(f"🛡️ HP Damage Reduction: -{u['hp_damage_reduction']:.0f}")
        if u.get("mp_bonus", 0) > 0:
            lines.append(f"💙 Max MP Bonus: +{u['mp_bonus']}")
        if u.get("has_revive"):
            lines.append("🗿 Totem of Life: Aktif")

        # Tampilkan pet aktif (gunakan data dari user? Tidak ada di user, jadi kita query aman)
        try:
            conn = db.get_conn()
            active = conn.execute("SELECT pet_id FROM user_pets WHERE user_id=? AND is_active=1", (self.user_id,)).fetchone()
            conn.close()
            if active:
                pet = db.PETS_DATA.get(active["pet_id"], {})
                lines.append(f"🐾 Pet Aktif: {pet.get('name', active['pet_id'])} — {pet.get('bonus', '')}")
        except:
            pass

        cls = db.AVATAR_CLASSES.get(u.get("avatar_class", "warrior"), {})
        skill = db.CLASS_SKILLS.get(u.get("avatar_class", "warrior"), {})
        lines.append(f"🎭 Class: {cls.get('icon','')} {cls.get('name','')} — Skill: {skill.get('icon','')} {skill.get('name','')} ({skill.get('mp_cost',10)} MP)")

        if not lines:
            lines.append("Belum ada buff aktif.")

        for lt in lines:
            bl.addWidget(_lbl(lt, size=12))
        il.addWidget(bg)

        # ── Activity log ──────────────────────────────────────────────────────
        lg = QGroupBox("📋 Aktivitas Terkini")
        ll = QVBoxLayout(lg)
        lw = QListWidget()
        lw.setFixedHeight(180)
        for entry in s["recent_log"][:15]:
            lw.addItem(
                f"[{entry['created_at'][11:16]}]  "
                f"{entry['action']}  —  {entry['detail']}")
        ll.addWidget(lw)
        il.addWidget(lg)
        il.addStretch()
        self._root.addWidget(_scrolled(inner))
        fade_in(inner, 200)

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog, QComboBox, QDialogButtonBox, QVBoxLayout, QDialog, QLabel
        dlg = QDialog(self)
        dlg.setWindowTitle("Pilih Format Ekspor")
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("Pilih format file:"))
        combo = QComboBox()
        combo.addItems(["CSV (.csv)", "Excel (.xlsx)", "Word (.docx)", "PDF (.pdf)"])
        layout.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        fmt = combo.currentText()
        
        data = db.get_full_export_data(self.user_id)
        
        if fmt == "CSV (.csv)":
            filter_str = "CSV Files (*.csv)"
            ext = ".csv"
            path, _ = QFileDialog.getSaveFileName(self, "Simpan File", "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_csv(data, path)
        elif fmt == "Excel (.xlsx)":
            filter_str = "Excel Files (*.xlsx)"
            ext = ".xlsx"
            path, _ = QFileDialog.getSaveFileName(self, "Simpan File", "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_excel(data, path)
        elif fmt == "Word (.docx)":
            filter_str = "Word Files (*.docx)"
            ext = ".docx"
            path, _ = QFileDialog.getSaveFileName(self, "Simpan File", "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_word(data, path)
        else:  # PDF
            filter_str = "PDF Files (*.pdf)"
            ext = ".pdf"
            path, _ = QFileDialog.getSaveFileName(self, "Simpan File", "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_pdf(data, path)
    
    def _export_csv(self, data, filepath):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["=== DATA USER ==="])
            u = data['user']
            writer.writerow(["Username", u.get('username','')])
            writer.writerow(["Display Name", u.get('display_name','')])
            writer.writerow(["Level", u.get('level',1)])
            writer.writerow(["XP", f"{u.get('xp',0)}/{u.get('level',1)*150}"])
            writer.writerow(["Gold", u.get('gold',0)])
            writer.writerow(["HP", f"{u.get('hp',0)}/{u.get('max_hp',0)}"])
            writer.writerow(["MP", f"{u.get('mp',0)}/{u.get('max_mp',0)}"])
            writer.writerow(["Class", u.get('avatar_class','warrior')])
            writer.writerow(["Sport Level", data['sport_stats']['sport_level']])
            writer.writerow(["Total Sport Points", data['sport_stats']['total_sport_points_earned']])
            writer.writerow([])
            writer.writerow(["=== STATISTIK ==="])
            s = data['stats']
            writer.writerow(["Streak Terpanjang", s['max_streak']])
            writer.writerow(["Total XP Earned", u.get('total_xp_earned',0)])
            writer.writerow(["Total Gold Earned", u.get('total_gold_earned',0)])
            writer.writerow(["Boss Dikalahkan", s['bosses_killed']])
            writer.writerow([])
            writer.writerow(["=== EKONOMI ==="])
            eco = data['eco_summary']
            writer.writerow(["Total Pemasukan", eco['total_income']])
            writer.writerow(["Total Pengeluaran", eco['total_expense']])
            writer.writerow(["Saldo", eco['balance']])
            writer.writerow([])
            writer.writerow(["=== HABITS ==="])
            writer.writerow(["Nama", "Difficulty", "Streak", "Last Done", "Notes"])
            for h in data['habits']:
                writer.writerow([h['name'], h['difficulty'], h['streak'], h['last_done'], h['notes']])
            writer.writerow([])
            writer.writerow(["=== DAILIES ==="])
            writer.writerow(["Nama", "Difficulty", "Streak", "Last Done", "Notes"])
            for d in data['dailies']:
                writer.writerow([d['name'], d['difficulty'], d['streak'], d['last_done'], d['notes']])
            writer.writerow([])
            writer.writerow(["=== QUESTS ==="])
            writer.writerow(["Nama", "Priority", "Done", "Due Date", "Notes"])
            for t in data['todos']:
                writer.writerow([t['name'], t['priority'], t['done'], t['due_date'], t['notes']])
            writer.writerow([])
            writer.writerow(["=== SPORT ACTIVITIES ==="])
            writer.writerow(["Nama", "Type", "Difficulty", "Streak", "Last Done", "Notes"])
            for a in data['sport_activities']:
                writer.writerow([a['name'], a['sport_type'], a['difficulty'], a['streak'], a['last_done'], a['notes']])
            writer.writerow([])
            writer.writerow(["=== EKONOMI ITEMS ==="])
            writer.writerow(["Nama", "Tipe", "Jumlah", "Kategori", "Tanggal", "Catatan"])
            for ei in data['economy_items']:
                writer.writerow([ei['name'], ei['type'], ei['amount'], ei['category'], ei['date'], ei['notes']])
        _show(self, "Sukses", f"Data diekspor ke {filepath}", "success")

    def _export_excel(self, data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, "Error", "Library ekspor tidak lengkap. Install: pip install openpyxl matplotlib", "error")
            return
        import tempfile
        
        wb = openpyxl.Workbook()
        # Sheet ringkasan
        ws_summary = wb.active
        ws_summary.title = "Ringkasan"
        u = data['user']
        s = data['stats']
        eco = data['eco_summary']
        ws_summary.append(["Data User"])
        ws_summary.append(["Username", u.get('username','')])
        ws_summary.append(["Display Name", u.get('display_name','')])
        ws_summary.append(["Level", u.get('level',1)])
        ws_summary.append(["XP", f"{u.get('xp',0)}/{u.get('level',1)*150}"])
        ws_summary.append(["Gold", u.get('gold',0)])
        ws_summary.append(["HP", f"{u.get('hp',0)}/{u.get('max_hp',0)}"])
        ws_summary.append(["MP", f"{u.get('mp',0)}/{u.get('max_mp',0)}"])
        ws_summary.append(["Class", u.get('avatar_class','warrior')])
        ws_summary.append(["Sport Level", data['sport_stats']['sport_level']])
        ws_summary.append(["Total Sport Points", data['sport_stats']['total_sport_points_earned']])
        ws_summary.append([])
        ws_summary.append(["Statistik"])
        ws_summary.append(["Streak Terpanjang", s['max_streak']])
        ws_summary.append(["Total XP Earned", u.get('total_xp_earned',0)])
        ws_summary.append(["Total Gold Earned", u.get('total_gold_earned',0)])
        ws_summary.append(["Boss Dikalahkan", s['bosses_killed']])
        ws_summary.append([])
        ws_summary.append(["Ekonomi"])
        ws_summary.append(["Total Pemasukan", eco['total_income']])
        ws_summary.append(["Total Pengeluaran", eco['total_expense']])
        ws_summary.append(["Saldo", eco['balance']])
        
        # Chart XP per hari (weekly)
        weekly = s['weekly']
        if weekly:
            ws_chart = wb.create_sheet("Grafik XP Mingguan")
            days = [row['day'][5:] for row in weekly]
            xp_vals = [row['xp'] or 0 for row in weekly]
            gold_vals = [row['gold'] or 0 for row in weekly]
            ws_chart.append(["Hari", "XP", "Gold"])
            for d, x, g in zip(days, xp_vals, gold_vals):
                ws_chart.append([d, x, g])
            chart = BarChart()
            chart.title = "XP & Gold per Hari (7 hari terakhir)"
            data_ref = Reference(ws_chart, min_col=2, min_row=1, max_row=len(days)+1, max_col=3)
            cats = Reference(ws_chart, min_col=1, min_row=2, max_row=len(days)+1)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats)
            ws_chart.add_chart(chart, "E5")
        
        # Habits, Dailies, Todos, Sport, Economy items sebagai sheet terpisah
        self._add_sheet_from_list(wb, "Habits", data['habits'], ["name","difficulty","streak","last_done","notes"])
        self._add_sheet_from_list(wb, "Dailies", data['dailies'], ["name","difficulty","streak","last_done","notes"])
        self._add_sheet_from_list(wb, "Quests", data['todos'], ["name","priority","done","due_date","notes"])
        self._add_sheet_from_list(wb, "Sport", data['sport_activities'], ["name","sport_type","difficulty","streak","last_done","notes"])
        self._add_sheet_from_list(wb, "Ekonomi", data['economy_items'], ["name","type","amount","category","date","notes"])
        
        wb.save(filepath)
        _show(self, "Sukses", f"Data diekspor ke {filepath}", "success")
    
    def _add_sheet_from_list(self, wb, sheet_name, items, fields):
        from openpyxl.utils import get_column_letter
        ws = wb.create_sheet(sheet_name)
        ws.append(fields)
        for item in items:
            row = [item.get(f, '') for f in fields]
            ws.append(row)
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try:
                    max_len = max(max_len, len(str(cell.value)))
                except:
                    pass
            ws.column_dimensions[col_letter].width = min(max_len+2, 40)
    
    def _export_word(self, data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, "Error", "Library ekspor tidak lengkap. Install: pip install openpyxl matplotlib", "error")
            return
        import tempfile
        
        doc = Document()
        title = doc.add_heading("CraftLife - Ekspor Data Lengkap", 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        u = data['user']
        doc.add_heading("Data User", level=1)
        doc.add_paragraph(f"Username: {u.get('username','')}")
        doc.add_paragraph(f"Display Name: {u.get('display_name','')}")
        doc.add_paragraph(f"Level: {u.get('level',1)}")
        doc.add_paragraph(f"XP: {u.get('xp',0)}/{u.get('level',1)*150}")
        doc.add_paragraph(f"Gold: {u.get('gold',0):.0f}")
        doc.add_paragraph(f"HP: {u.get('hp',0)}/{u.get('max_hp',0)}")
        doc.add_paragraph(f"MP: {u.get('mp',0)}/{u.get('max_mp',0)}")
        doc.add_paragraph(f"Class: {u.get('avatar_class','warrior')}")
        doc.add_paragraph(f"Sport Level: {data['sport_stats']['sport_level']}")
        doc.add_paragraph(f"Total Sport Points: {data['sport_stats']['total_sport_points_earned']}")
        
        s = data['stats']
        doc.add_heading("Statistik", level=1)
        doc.add_paragraph(f"Streak Terpanjang: {s['max_streak']} hari")
        doc.add_paragraph(f"Total XP Earned: {u.get('total_xp_earned',0)}")
        doc.add_paragraph(f"Total Gold Earned: {u.get('total_gold_earned',0):.0f}")
        doc.add_paragraph(f"Boss Dikalahkan: {s['bosses_killed']}")
        
        eco = data['eco_summary']
        doc.add_heading("Ekonomi", level=1)
        doc.add_paragraph(f"Total Pemasukan: {eco['total_income']:.0f}")
        doc.add_paragraph(f"Total Pengeluaran: {eco['total_expense']:.0f}")
        doc.add_paragraph(f"Saldo: {eco['balance']:.0f}")
        
        weekly = s['weekly']
        if weekly:
            doc.add_heading("XP & Gold Mingguan", level=1)
            days = [row['day'][5:] for row in weekly]
            xp_vals = [row['xp'] or 0 for row in weekly]
            gold_vals = [row['gold'] or 0 for row in weekly]
            plt.figure(figsize=(6,4))
            plt.bar(days, xp_vals, label='XP', color='#80c000')
            plt.bar(days, gold_vals, label='Gold', color='#f0a800', alpha=0.7)
            plt.xlabel('Hari')
            plt.ylabel('Jumlah')
            plt.title('XP & Gold per Hari (7 hari terakhir)')
            plt.legend()
            from io import BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100)
            plt.close()
            img_buffer.seek(0)
            doc.add_picture(img_buffer, width=Inches(5))
        
        self._add_table_to_word(doc, "Habits", data['habits'], ["Nama","Difficulty","Streak","Last Done","Catatan"])
        self._add_table_to_word(doc, "Dailies", data['dailies'], ["Nama","Difficulty","Streak","Last Done","Catatan"])
        self._add_table_to_word(doc, "Quests", data['todos'], ["Nama","Priority","Done","Due Date","Catatan"])
        self._add_table_to_word(doc, "Sport Activities", data['sport_activities'], ["Nama","Type","Difficulty","Streak","Last Done","Catatan"])
        self._add_table_to_word(doc, "Ekonomi Items", data['economy_items'], ["Nama","Tipe","Jumlah","Kategori","Tanggal","Catatan"])
        
        doc.save(filepath)
        _show(self, "Sukses", f"Data diekspor ke {filepath}", "success")
    
    def _add_table_to_word(self, doc, title, items, headers):
        if not items:
            return
        doc.add_heading(title, level=2)
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
        field_map = {"Nama":"name","Difficulty":"difficulty","Streak":"streak",
                     "Last Done":"last_done","Catatan":"notes","Priority":"priority",
                     "Done":"done","Due Date":"due_date","Type":"sport_type",
                     "Tipe":"type","Jumlah":"amount","Kategori":"category","Tanggal":"date"}
        for item in items:
            row_cells = table.add_row().cells
            for i, h in enumerate(headers):
                field = field_map.get(h, h.lower().replace(" ","_"))
                val = item.get(field, '')
                if field == "amount":
                    val = f"{val:.0f}" if isinstance(val, (int,float)) else val
                row_cells[i].text = str(val)
    
    def _export_pdf(self, data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, "Error", "Library ekspor tidak lengkap. Install: pip install openpyxl matplotlib", "error")
            return
        import tempfile
        
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(name='Title', parent=styles['Title'], alignment=1, fontSize=16)
        story.append(Paragraph("CraftLife - Ekspor Data Lengkap", title_style))
        story.append(Spacer(1, 0.2*inch))
        
        u = data['user']
        s = data['stats']
        eco = data['eco_summary']
        summary_data = [
            ["Username", u.get('username','')],
            ["Display Name", u.get('display_name','')],
            ["Level", str(u.get('level',1))],
            ["XP", f"{u.get('xp',0)}/{u.get('level',1)*150}"],
            ["Gold", f"{u.get('gold',0):.0f}"],
            ["HP", f"{u.get('hp',0)}/{u.get('max_hp',0)}"],
            ["MP", f"{u.get('mp',0)}/{u.get('max_mp',0)}"],
            ["Class", u.get('avatar_class','warrior')],
            ["Sport Level", str(data['sport_stats']['sport_level'])],
            ["Total Sport Points", str(data['sport_stats']['total_sport_points_earned'])],
            ["Streak Terpanjang", str(s['max_streak'])],
            ["Total XP Earned", str(u.get('total_xp_earned',0))],
            ["Total Gold Earned", f"{u.get('total_gold_earned',0):.0f}"],
            ["Boss Dikalahkan", str(s['bosses_killed'])],
            ["Total Pemasukan", f"{eco['total_income']:.0f}"],
            ["Total Pengeluaran", f"{eco['total_expense']:.0f}"],
            ["Saldo", f"{eco['balance']:.0f}"],
        ]
        table = Table(summary_data, colWidths=[2*inch, 3*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#5a8a2e")),
            ('TEXTCOLOR', (0,0), (0,-1), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2*inch))
        
        weekly = s['weekly']
        if weekly:
            days = [row['day'][5:] for row in weekly]
            xp_vals = [row['xp'] or 0 for row in weekly]
            gold_vals = [row['gold'] or 0 for row in weekly]
            plt.figure(figsize=(6,4))
            plt.bar(days, xp_vals, label='XP', color='#80c000')
            plt.bar(days, gold_vals, label='Gold', color='#f0a800', alpha=0.7)
            plt.xlabel('Hari')
            plt.ylabel('Jumlah')
            plt.title('XP & Gold per Hari (7 hari terakhir)')
            plt.legend()
            from io import BytesIO
            img_buffer = BytesIO()
            plt.savefig(img_buffer, format='png', dpi=100)
            plt.close()
            img_buffer.seek(0)
            img = RLImage(img_buffer, width=5*inch, height=3*inch)
            story.append(img)
            story.append(Spacer(1, 0.2*inch))
        
        self._add_pdf_table(story, "Habits", data['habits'], ["Nama","Difficulty","Streak","Last Done","Catatan"])
        self._add_pdf_table(story, "Dailies", data['dailies'], ["Nama","Difficulty","Streak","Last Done","Catatan"])
        self._add_pdf_table(story, "Quests", data['todos'], ["Nama","Priority","Done","Due Date","Catatan"])
        self._add_pdf_table(story, "Sport Activities", data['sport_activities'], ["Nama","Type","Difficulty","Streak","Last Done","Catatan"])
        self._add_pdf_table(story, "Ekonomi Items", data['economy_items'], ["Nama","Tipe","Jumlah","Kategori","Tanggal","Catatan"])
        
        doc.build(story)
        _show(self, "Sukses", f"Data diekspor ke {filepath}", "success")
    
    def _add_pdf_table(self, story, title, items, headers):
        if not items:
            return
        styles = getSampleStyleSheet()
        story.append(Paragraph(title, styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        data = [headers]
        field_map = {"Nama":"name","Difficulty":"difficulty","Streak":"streak",
                     "Last Done":"last_done","Catatan":"notes","Priority":"priority",
                     "Done":"done","Due Date":"due_date","Type":"sport_type",
                     "Tipe":"type","Jumlah":"amount","Kategori":"category","Tanggal":"date"}
        for item in items:
            row = []
            for h in headers:
                field = field_map.get(h, h.lower().replace(" ","_"))
                val = item.get(field, '')
                if field == "amount":
                    val = f"{val:.0f}" if isinstance(val, (int,float)) else val
                row.append(str(val))
            data.append(row)
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5a8a2e")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.2*inch))


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE PAGE  (instant sync — no restart needed)
# ══════════════════════════════════════════════════════════════════════════════
class ProfilePage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(20, 16, 20, 16)
        self._root.setSpacing(10)
        AppState.register(self.load)
        self.load()

    def _clear(self):
        while self._root.count():
            i = self._root.takeAt(0)
            if i.widget():
                i.widget().deleteLater()

    def load(self):
        if not AppState.user_id:
            return
        self._clear()
        u = AppState.user()
        cls = db.AVATAR_CLASSES.get(u.get("avatar_class", "warrior"), {})

        self._root.addWidget(
            _lbl("🎭  Profile & Avatar", "section", 14, True))
        self._root.addWidget(_sep())

        inner = QWidget()
        il    = QVBoxLayout(inner)
        il.setSpacing(14)
        il.setContentsMargins(0, 0, 0, 0)

        # ── Avatar display ────────────────────────────────────────────────────
        av_row = QHBoxLayout()
        av_row.setSpacing(18)
        av_icon = QLabel(u.get("avatar_emoji", "⚔️"))
        av_icon.setFont(QFont("Segoe UI", 48))
        av_icon.setFixedSize(86, 86)
        av_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        av_icon.setStyleSheet(
            f"background: {u.get('avatar_color', _T('primary'))};"
            f" border-radius: 12px;"
            f" border: 2px solid {_T('light')};")
        av_row.addWidget(av_icon)

        av_info = QVBoxLayout()
        av_info.setSpacing(4)
        av_info.addWidget(_lbl(
            u.get("display_name", "—"), size=18, bold=True))
        av_info.addWidget(_lbl(
            f"@{u.get('username','')}", "sub", 12))
        av_info.addWidget(_lbl(
            f"{cls.get('icon','')} {cls.get('name','')}  ·  Level {u['level']}",
            "sub", 13))
        av_info.addWidget(_lbl(
            u.get("bio", "Belum ada bio."), "sub", 12))
        av_info.addWidget(_lbl(
            f"Bergabung: {u.get('created_at','')[:10]}", "sub", 11))
        av_row.addLayout(av_info, 1)
        il.addLayout(av_row)

        # ── Edit profil ───────────────────────────────────────────────────────
        eg = QGroupBox("✏️ Edit Profil")
        el = QVBoxLayout(eg)
        el.setSpacing(8)
        self._dn  = _input("Nama display…")
        self._dn.setText(u.get("display_name", ""))
        self._bio = _input("Bio singkat…")
        self._bio.setText(u.get("bio", ""))
        sqg = QGroupBox("🔐 Pertanyaan Keamanan (untuk reset password)")
        sql = QVBoxLayout(sqg)
        self.question_combo = QComboBox()
        for q in db.SECURITY_QUESTIONS:
            self.question_combo.addItem(q)
        self.answer_input = _input("Jawaban (simpan baik-baik)")
        save_sq = _btn("Simpan Pertanyaan Keamanan", "solid", self._save_security)
        sql.addWidget(self.question_combo)
        sql.addWidget(self.answer_input)
        sql.addWidget(save_sq)
        il.addWidget(sqg)
        # Backup Codes
        bcg = QGroupBox("🎫 Kode Cadangan (Backup Codes)")
        bcl = QVBoxLayout(bcg)
        self.backup_codes_label = QLabel("Klik tombol di bawah untuk menghasilkan 5 kode cadangan. Simpan kode-kode ini di tempat aman. Setiap kode hanya bisa dipakai sekali.")
        self.backup_codes_label.setWordWrap(True)
        self.backup_codes_label.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        bcl.addWidget(self.backup_codes_label)
        self.generate_backup_btn = _btn("🔑 Generate Kode Cadangan Baru", "solid", self._generate_backup_codes)
        bcl.addWidget(self.generate_backup_btn)
        self.backup_codes_display = QTextEdit()
        self.backup_codes_display.setReadOnly(True)
        self.backup_codes_display.setFixedHeight(100)
        self.backup_codes_display.setVisible(False)
        bcl.addWidget(self.backup_codes_display)
        il.addWidget(bcg)
        el.addWidget(_lbl("Nama Display", size=12))
        el.addWidget(self._dn)
        el.addWidget(_lbl("Bio", size=12))
        el.addWidget(self._bio)
        el.addWidget(_btn("💾 Simpan Profil", "solid", self._save_profile, 40))
        il.addWidget(eg)

        # ── Class picker ──────────────────────────────────────────────────────
        cg = QGroupBox("🎮 Pilih Class")
        cl_lay = QGridLayout(cg)
        cl_lay.setSpacing(8)
        for i, (cid, cdata) in enumerate(db.AVATAR_CLASSES.items()):
            f  = _card()
            cv = QVBoxLayout(f)
            cv.setContentsMargins(10, 8, 10, 8)
            cv.setSpacing(4)
            cv.addWidget(QLabel(cdata["icon"],
                                alignment=Qt.AlignmentFlag.AlignCenter))
            nm = QLabel(cdata["name"])
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet(
                f"font-size:12px; font-weight:bold; color:{_T('text')};")
            cv.addWidget(nm)
            bn = QLabel(cdata["bonus"])
            bn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bn.setWordWrap(True)
            bn.setStyleSheet(f"font-size:10px; color:{_T('muted')};")
            cv.addWidget(bn)
            active = (u.get("avatar_class") == cid)
            if active:
                al = QLabel("✔ Aktif")
                al.setAlignment(Qt.AlignmentFlag.AlignCenter)
                al.setStyleSheet(
                    f"color:{_T('light')}; font-weight:bold; font-size:11px;")
                cv.addWidget(al)
            else:
                sb = _btn("Pilih", h=30)
                sb.clicked.connect(lambda _, c=cid: self._set_class(c))
                cv.addWidget(sb)
            cl_lay.addWidget(f, i // 3, i % 3)
        il.addWidget(cg)

        # ── Color picker ──────────────────────────────────────────────────────
        colg = QGroupBox("🎨 Warna Avatar")
        col_lay = QHBoxLayout(colg)
        col_lay.setContentsMargins(12, 12, 12, 12)
        col_lay.setSpacing(8)
        colors = [
            ("#5a8a2e","Hijau"), ("#d04020","Merah"), ("#4da6ff","Biru"),
            ("#f0a800","Emas"),  ("#9a50e0","Ungu"),  ("#4dd9e0","Cyan"),
            ("#e8e8e8","Putih"), ("#ff6a00","Orange"),
        ]
        current_color = u.get("avatar_color", "#5a8a2e")
        for hex_c, name in colors:
            cb = QPushButton(name)
            cb.setFixedHeight(36)
            border = "2px solid #fff" if hex_c == current_color else "2px solid transparent"
            cb.setStyleSheet(
                f"background:{hex_c}; color:#fff;"
                f" border:{border}; border-radius:6px;"
                f" font-size:11px; font-weight:bold;")
            cb.clicked.connect(lambda _, c=hex_c: self._set_color(c))
            col_lay.addWidget(cb)
        il.addWidget(colg)

        # ── Emoji picker ──────────────────────────────────────────────────────
        emg = QGroupBox("😀 Emoji Avatar")
        em_lay = QHBoxLayout(emg)
        em_lay.setContentsMargins(12, 12, 12, 12)
        em_lay.setSpacing(6)
        emojis = ["⚔️","🧙","🏹","💊","🗡️","🛡️","🔮","🌟","👑","🐉","🦊","🐺"]
        cur_em = u.get("avatar_emoji", "⚔️")
        for em in emojis:
            eb = QPushButton(em)
            eb.setFixedSize(42, 42)
            bg_active = _T("primary") if em == cur_em else _T("panel")
            eb.setStyleSheet(
                f"font-size:20px; background:{bg_active};"
                f" border:1px solid {_T('border')}; border-radius:6px;")
            eb.clicked.connect(lambda _, e=em: self._set_emoji(e))
            em_lay.addWidget(eb)
        il.addWidget(emg)

        # ── Change password ───────────────────────────────────────────────────
        pg = QGroupBox("🔑 Ganti Password")
        pl = QVBoxLayout(pg)
        pl.setSpacing(8)
        self._old_pw = _input("Password lama…", True)
        self._new_pw = _input("Password baru…", True)
        pl.addWidget(self._old_pw)
        pl.addWidget(self._new_pw)
        pl.addWidget(_btn("🔑 Ganti Password", "gold", self._change_pw, 40))
        il.addWidget(pg)

        il.addStretch()
        self._root.addWidget(_scrolled(inner))
        fade_in(inner, 200)

    # ── actions (all call AppState.refresh() for instant sync) ────────────────

    def _save_profile(self):
        db.set_avatar(self.user_id,
                      bio=self._bio.text(),
                      display_name=self._dn.text().strip())
        SND.notify()
        _show(self, "Tersimpan", "Profil berhasil diupdate!", "success")
        AppState.refresh()   # ← instant sync

    def _set_class(self, cls_id: str):
        r = db.change_class(self.user_id, cls_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        AppState.refresh()

    def _set_color(self, color: str):
        db.set_avatar(self.user_id, color=color)
        SND.click()
        AppState.refresh()   # ← instant sync

    def _set_emoji(self, emoji: str):
        db.set_avatar(self.user_id, emoji=emoji)
        SND.click()
        AppState.refresh()   # ← instant sync

    def _change_pw(self):
        r = db.change_password(
            self.user_id, self._old_pw.text(), self._new_pw.text())
        if r["ok"]:
            SND.notify()
            _show(self, "Berhasil", r["msg"], "success")
            self._old_pw.clear()
            self._new_pw.clear()
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")

    def _save_security(self):
        question = self.question_combo.currentText()
        answer = self.answer_input.text().strip()
        if not answer:
            _show(self, "Error", "Jawaban tidak boleh kosong!", "error")
            return
        db.set_security_question(self.user_id, question, answer)
        SND.notify()
        _show(self, "Sukses", "Pertanyaan keamanan berhasil disimpan!", "success")
        self.answer_input.clear()

    def _generate_backup_codes(self):
        codes = db.generate_backup_codes(self.user_id, num_codes=5)
        if codes:
            msg = "🔐 Kode Cadangan Anda (simpan baik-baik, jangan sampai hilang):\n\n"
            for i, code in enumerate(codes, 1):
                msg += f"{i}. {code}\n"
            msg += "\nSetiap kode hanya bisa dipakai SEKALI untuk reset password.\nSimpan di tempat aman!"
            self.backup_codes_display.setText(msg)
            self.backup_codes_display.setVisible(True)
            SND.notify()
            _show(self, "Kode Cadangan", msg, "success")
        else:
            _show(self, "Error", "Gagal generate kode cadangan.", "error")

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS PAGE  (5 themes + sound toggle)
# ══════════════════════════════════════════════════════════════════════════════
class SettingsPage(QWidget):
    theme_changed = pyqtSignal()

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)
        root.addWidget(_lbl("⚙️  Pengaturan", "section", 14, True))
        root.addWidget(_sep())

        u = db.get_user(self.user_id)
        cur = u.get("theme", "overworld")

        # ── Theme chooser ─────────────────────────────────────────────────────
        tg = QGroupBox("🎨 Pilih Theme Minecraft (5 pilihan)")
        tl = QVBoxLayout(tg)
        tl.setSpacing(10)
        for key, td in db.THEMES.items():
            row = QHBoxLayout()
            preview = QLabel("●")
            preview.setStyleSheet(
                f"color:{td['light']}; font-size:22px;")
            preview.setFixedWidth(30)
            rb = QRadioButton(
                f"{td['label']}   "
                f"( Accent: {td['accent']} )")
            rb.setChecked(key == cur)
            rb.setStyleSheet(
                f"font-size:13px; color:{_T('text')};")
            rb.toggled.connect(
                lambda checked, k=key: self._apply(k) if checked else None)
            row.addWidget(preview)
            row.addWidget(rb, 1)
            tl.addLayout(row)
        root.addWidget(tg)

        # ── Sound toggle ──────────────────────────────────────────────────────
        sg = QGroupBox("🔊 Sound Effects")
        sl = QVBoxLayout(sg)
        self._snd = QCheckBox("Aktifkan sound effects (Windows only)")
        self._snd.setChecked(bool(u.get("sound_enabled", 1)))
        self._snd.stateChanged.connect(self._toggle_snd)
        sl.addWidget(self._snd)
        sl.addWidget(_lbl(
            "Sound menggunakan winsound bawaan Windows.\n"
            "Tidak ada efek di Linux/macOS.", "sub", 11))
        root.addWidget(sg)

        # ── DB path info ──────────────────────────────────────────────────────
        dg = QGroupBox("💾 Data")
        dl = QVBoxLayout(dg)
        dl.addWidget(_lbl(f"Database: {db.DB_PATH}", "sub", 11))
        root.addWidget(dg)
        root.addStretch()

        # ─── Exit button (danger) ─────────────────────────────────────────────────
        exit_btn = _btn("🚪 Keluar Aplikasi", "danger", QApplication.instance().quit)
        root.addWidget(exit_btn)

    def _apply(self, key: str):
        db.set_user_theme(self.user_id, key)
        t = db.THEMES[key]
        apply_theme(t)
        self.theme_changed.emit()

    def _toggle_snd(self, state: int):
        enabled = bool(state)
        SoundEngine.enabled = enabled
        db.set_user_settings(self.user_id, sound_enabled=enabled)
        if enabled:
            SND.notify()


# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION POPUP
# ══════════════════════════════════════════════════════════════════════════════
class NotifPopup(QDialog):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔔  Notifikasi")
        self.setFixedSize(420, 400)
        self.setStyleSheet(build_ss())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)
        lay.addWidget(_lbl("🔔  Notifikasi", "section", 14, True))
        lw = QListWidget()
        notifs = db.get_notifications(user_id, unread_only=False)
        db.mark_read(user_id)
        if not notifs:
            lw.addItem("Tidak ada notifikasi.")
        else:
            icons = {"levelup": "🎉", "success": "✅",
                     "danger":  "💀", "info":    "💬",
                     "warning": "⚠️"}
            for n in notifs:
                ic = icons.get(n["type"], "💬")
                lw.addItem(
                    f"{ic}  {n['message']}\n"
                    f"      {n['created_at'][:16]}")
        lay.addWidget(lw)
        lay.addWidget(_btn("Tutup", "solid", self.accept, 40))
        # fade only the inner widget, not the dialog
        fade_in(lw, 200)

# ══════════════════════════════════════════════════════════════════════════════
#  LeaderBoard 
# ══════════════════════════════════════════════════════════════════════════════
class LeaderboardPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(_lbl("🏆  Leaderboard", "section", 14, True))
        layout.addWidget(_sep())

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["User", "Level", "Total XP", "Gold", "🏅 Sport Lv.", "Pet"])

        # ── Nonaktifkan semua interaksi edit / ubah struktur ──
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        AppState.register(self.load)
        self.load()

    def load(self):
        bg         = _T("bg")
        panel      = _T("panel")
        alt_bg     = _T("border")
        text       = _T("text")
        header_bg  = _T("primary")
        header_txt = _T("light")
        grid       = _T("border")

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {panel};
                alternate-background-color: {alt_bg};
                gridline-color: {grid};
                font-size: 12px;
                border: 1px solid {_T("border")};
                border-radius: 6px;
                color: {text};
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {header_txt};
                padding: 8px;
                font-weight: bold;
                border: 1px solid {grid};
            }}
        """)

        data = db.get_leaderboard()
        self.table.setRowCount(len(data))
        for i, r in enumerate(data):
            self.table.setItem(
                i, 0, QTableWidgetItem(r["display_name"] or r["username"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(r["level"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["total_xp_earned"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['gold']:.0f}"))
            # Sport level — kolom baru
            sport_lv = r.get("sport_level", 1) or 1
            sport_item = QTableWidgetItem(f"Lv.{sport_lv}")
            sport_item.setForeground(QColor("#f0a800"))
            self.table.setItem(i, 4, sport_item)
            self.table.setItem(i, 5, QTableWidgetItem(str(r["pet_count"])))

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  Friends Page (Add Friend System)
# ══════════════════════════════════════════════════════════════════════════════
class FriendsPage(QWidget):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self._build()
        AppState.register(self.load)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,16,20,16)
        layout.setSpacing(10)
        layout.addWidget(_lbl("👥  Teman", "section", 14, True))
        layout.addWidget(_sep())

        # Form tambah teman
        add_form = QHBoxLayout()
        self.friend_username = _input("Username teman...")
        add_btn = _btn("➕ Kirim Permintaan", "solid", self._send_request)
        add_form.addWidget(self.friend_username)
        add_form.addWidget(add_btn)
        layout.addLayout(add_form)

        # Daftar permintaan masuk
        self.pending_group = QGroupBox("📨 Permintaan Masuk")
        self.pending_layout = QVBoxLayout(self.pending_group)
        layout.addWidget(self.pending_group)

        # Daftar teman
        self.friends_group = QGroupBox("👫 Daftar Teman")
        self.friends_layout = QVBoxLayout(self.friends_group)
        layout.addWidget(self.friends_group)

        layout.addStretch()
        self.load()

    def load(self):
        # Clear
        while self.pending_layout.count():
            item = self.pending_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Hapus semua widget di dalam sub-layout
                sub_layout = item.layout()
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                sub_layout.deleteLater()
        while self.friends_layout.count():
            item = self.friends_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub_layout = item.layout()
                while sub_layout.count():
                    sub_item = sub_layout.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                sub_layout.deleteLater()
        # Pending requests
        pending = db.get_pending_friend_requests(self.user_id)
        if pending:
            self.pending_group.setVisible(True)
            for req in pending:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"📨 {req['display_name']} (@{req['username']})"))
                accept = _btn("✅ Terima", h=28)
                accept.clicked.connect(lambda _, rid=req["id"]: self._accept(rid))
                reject = _btn("❌ Tolak", "danger", h=28)
                reject.clicked.connect(lambda _, rid=req["id"]: self._reject(rid))
                row.addWidget(accept)
                row.addWidget(reject)
                self.pending_layout.addLayout(row)
        else:
            self.pending_group.setVisible(False)

        # Friends list
        friends = db.get_friends(self.user_id)
        if friends:
            self.friends_group.setVisible(True)
            for f in friends:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{f['avatar_emoji']} {f['display_name']} (Lv.{f['level']})"))
                row.addStretch()
                chat_btn = _btn("💬 Chat", h=28)
                chat_btn.clicked.connect(lambda _, fid=f["id"], name=f["display_name"]: self._open_chat(fid, name))
                profile_btn = _btn("👤", h=28)
                profile_btn.clicked.connect(lambda _, fid=f["id"]: self._view_profile(fid))
                kick_btn = _btn("❌ Hapus", "danger", h=28)
                kick_btn.clicked.connect(lambda _, fid=f["id"]: self._remove_friend(fid))
                row.addWidget(chat_btn)
                row.addWidget(profile_btn)
                row.addWidget(kick_btn)
                self.friends_layout.addLayout(row)
        else:
            self.friends_group.setVisible(False)

    def _open_chat(self, friend_id, friend_name):
        dlg = ChatDialog(self.user_id, friend_id, friend_name, self)
        dlg.exec()

    def _view_profile(self, friend_id):
        dlg = FriendProfileDialog(friend_id, self)
        dlg.exec()

    def _remove_friend(self, friend_id):
        r = db.remove_friend(self.user_id, friend_id)
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")
        self.load()

    def _send_request(self):
        username = self.friend_username.text().strip()
        if not username:
            _show(self, "Error", "Masukkan username!", "error")
            return
        r = db.send_friend_request(self.user_id, username)
        if r["ok"]:
            SND.notify()
            _show(self, "Berhasil", r["msg"], "success")
            self.friend_username.clear()
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")

    def _accept(self, req_id):
        r = db.accept_friend_request(self.user_id, req_id)
        self._show_result(r)
        self.load()

    def _reject(self, req_id):
        r = db.reject_friend_request(self.user_id, req_id)
        self._show_result(r)
        self.load()

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, "Sukses", r["msg"], "success")
        else:
            SND.error()
            _show(self, "Gagal", r["msg"], "error")

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  ChatDialog (Direct Messaging System with real-time updates)
# ══════════════════════════════════════════════════════════════════════════════
class ChatDialog(QDialog):
    def __init__(self, user_id, friend_id, friend_name, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.friend_id = friend_id
        self.setWindowTitle(f"💬 Chat dengan {friend_name}")
        self.setMinimumSize(400, 500)
        self.setStyleSheet(build_ss())
        self._build()
        self._load_messages()
        self.timer = QTimer()
        self.timer.timeout.connect(self._load_messages)
        self.timer.start(3000)

    def _build(self):
        layout = QVBoxLayout(self)
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        send_btn = _btn("Kirim", "solid", self._send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def _load_messages(self):
        messages = db.get_messages(self.user_id, self.friend_id)
        self.chat_area.clear()
        for m in messages:
            sender = "Kamu" if m["sender_id"] == self.user_id else "Teman"
            self.chat_area.append(f"[{m['created_at'][11:16]}] {sender}: {m['message']}")
        db.mark_messages_read(self.user_id, self.friend_id)

    def _send_message(self):
        msg = self.message_input.text().strip()
        if msg:
            server_now = TimeSync.get_current_time().isoformat()
            db.send_message(self.user_id, self.friend_id, msg, server_now)
            self.message_input.clear()
            self._load_messages()

    def closeEvent(self, e):
        self.timer.stop()
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  GuildChatDialog (Direct Messaging Guild System with real-time updates)
# ══════════════════════════════════════════════════════════════════════════════
class GuildChatDialog(QDialog):
    def __init__(self, guild_id, user_id, parent=None):
        super().__init__(parent)
        self.guild_id = guild_id
        self.user_id = user_id
        self.setWindowTitle(f"💬 Chat Guild")
        self.setMinimumSize(450, 550)
        self.setStyleSheet(build_ss())
        self._build()
        self._load_messages()
        self.timer = QTimer()
        self.timer.timeout.connect(self._load_messages)
        self.timer.start(3000)

    def _build(self):
        layout = QVBoxLayout(self)
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        send_btn = _btn("Kirim", "solid", self._send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def _load_messages(self):
        msgs = db.get_guild_messages(self.guild_id)
        self.chat_area.clear()
        for m in msgs:
            self.chat_area.append(f"[{m['created_at'][11:16]}] {m['display_name']}: {m['message']}")

    def _send_message(self):
        msg = self.message_input.text().strip()
        if msg:
            server_now = TimeSync.get_current_time().isoformat()
            db.send_guild_message(self.guild_id, self.user_id, msg, server_now)
            self.message_input.clear()
            self._load_messages()

    def closeEvent(self, e):
        self.timer.stop()
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  FriendProfileDialog
# ══════════════════════════════════════════════════════════════════════════════
class FriendProfileDialog(QDialog):
    def __init__(self, friend_id, parent=None):
        super().__init__(parent)
        self.friend_id = friend_id
        self.setWindowTitle("Profil Teman")
        self.setMinimumSize(400, 500)
        self.setStyleSheet(build_ss())
        self._build()
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        scroll = _scrolled(self.content)
        layout.addWidget(scroll)

    def _load(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        u = db.get_user(self.friend_id)
        stats = db.get_stats(self.friend_id)
        if not u:
            return
        avatar = QLabel(u.get("avatar_emoji", "⚔️"))
        avatar.setFont(QFont("Segoe UI", 48))
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(f"background: {u.get('avatar_color', '#5a8a2e')}; border-radius: 12px; padding: 10px;")
        self.content_layout.addWidget(avatar)
        self.content_layout.addWidget(_lbl(u.get("display_name", "No name"), size=16, bold=True))
        self.content_layout.addWidget(_lbl(f"@{u.get('username', '')}", "sub"))
        self.content_layout.addWidget(_lbl(f"Level {u.get('level', 1)}", "sub"))
        self.content_layout.addWidget(_lbl(f"Bio: {u.get('bio', 'Tidak ada bio')}", "sub"))
        self.content_layout.addWidget(_sep())
        data = [
            ("Habit Hari Ini", f"{stats['habits_done_today']}/{stats['habits_total']}"),
            ("Daily Hari Ini", f"{stats['dailies_done_today']}/{stats['dailies_total']}"),
            ("Quest Selesai", f"{stats['todos_done']}/{stats['todos_total']}"),
            ("Streak Terpanjang", str(stats["max_streak"])),
            ("Boss Dikalahkan", str(stats["bosses_killed"])),
            ("Pet Dimiliki", str(stats["pet_count"])),
        ]
        for label, value in data:
            row = QHBoxLayout()
            row.addWidget(QLabel(label))
            row.addStretch()
            row.addWidget(QLabel(value))
            self.content_layout.addLayout(row)
        self.content_layout.addStretch()


# ══════════════════════════════════════════════════════════════════════════════
#  Reset Password via Pertanyaan Keamanan 
# ══════════════════════════════════════════════════════════════════════════════
class ResetPasswordBySecurityDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password via Pertanyaan Keamanan")
        self.setFixedSize(450, 400)
        self.setStyleSheet(build_overworld_ss())
        self.user_id = None
        self.security_question = None
        self._build()
    
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        self.step = 1  # 1: username, 2: jawaban, 3: reset
        self._step1()
    
    def _step1(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl("Masukkan username:", size=12))
        self.username_input = _input("Username")
        layout.addWidget(self.username_input)
        btn = _btn("Cek Pertanyaan Keamanan", "solid", self._check_username)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _check_username(self):
        username = self.username_input.text().strip()
        if not username:
            self.msg_label.setText("Username tidak boleh kosong!")
            return
        conn = db.get_conn()
        row = conn.execute(
            "SELECT id, security_question FROM users WHERE username=?",
            (username.lower(),)
        ).fetchone()
        conn.close()
        if not row:
            self.msg_label.setText("Username tidak ditemukan!")
            return
        if not row["security_question"]:
            self.msg_label.setText("User ini belum mengatur pertanyaan keamanan. Gunakan metode lain atau hubungi admin.")
            return
        self.user_id = row["id"]
        self.security_question = row["security_question"]
        self._step2() 

    def _step2(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl(f"Pertanyaan keamanan:", size=12))
        layout.addWidget(_lbl(self.security_question, size=12, bold=True))
        self.answer_input = _input("Jawaban")
        layout.addWidget(self.answer_input)
        btn = _btn("Verifikasi Jawaban", "solid", self._verify)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _verify(self):
        answer = self.answer_input.text().strip()
        if not answer:
            self.msg_label.setText("Jawaban tidak boleh kosong!")
            return
        if db.verify_security_answer(self.user_id, answer):
            self._step3()
        else:
            self.msg_label.setText("Jawaban salah! Coba lagi.")
    
    def _step3(self):
        self._clear()
        if not self.user_id:  
            self.msg_label.setText("Terjadi kesalahan. Silakan ulangi dari awal.")
            return
        layout = self.layout()
        layout.addWidget(_lbl("Buat password baru:", size=12))
        self.new_pass = _input("Password baru", password=True)
        self.confirm_pass = _input("Konfirmasi password", password=True)
        layout.addWidget(self.new_pass)
        layout.addWidget(self.confirm_pass)
        btn = _btn("Reset Password", "solid", self._reset)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _reset(self):
        p1 = self.new_pass.text()
        p2 = self.confirm_pass.text()
        if len(p1) < 4:
            self.msg_label.setText("Password minimal 4 karakter!")
            return
        if p1 != p2:
            self.msg_label.setText("Password tidak cocok!")
            return
        db.reset_password_by_security(self.user_id, p1)
        _show(self, "Sukses", "Password berhasil direset! Silakan login.", "success")
        self.accept()
    
    def _clear(self):
        # Hapus semua widget dari layout
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

# ══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW  (complex & user-friendly — no fade_in on self)
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow(QDialog):
    logged_in = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("⛏ CraftLife — Selamat Datang")
        self.setFixedSize(500, 620)
        self.setWindowIcon(QIcon(get_icon_path('craftlife.ico')))
        self.setStyleSheet(build_ss())
        self._build()
        # Sembunyikan dulu, cek session
        self.hide()
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(10, self._check_auto_login)

    def _check_auto_login(self):
        session = load_session()
        if session:
            user = db.get_user(session["user_id"])
            if user:
                self.logged_in.emit(user)
                self.accept()  
                return
        self.show()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Banner (plain widget, safe to fade_in)
        banner = QWidget()
        banner.setFixedHeight(110)
        banner.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {_T('bg')},stop:1 {_T('panel')});"
            f"border-bottom: 2px solid {_T('primary')};")
        bl = QVBoxLayout(banner)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1 = _lbl("⛏  CraftLife", size=24, bold=True)
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setStyleSheet(f"color: {_T('light')};")
        t2 = _lbl("Minecraft Habit Tracker  ·  Jadikan hidupmu petualangan!",
                   "sub", 12)
        t2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(t1)
        bl.addWidget(t2)
        root.addWidget(banner)
        fade_in(banner, 300)   # fade on banner widget — safe

        body = QWidget()
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(40, 20, 40, 20)
        body_lay.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._login_tab(),    "🗡️  Login")
        tabs.addTab(self._register_tab(), "🌱  Daftar Akun")
        body_lay.addWidget(tabs)
        root.addWidget(body)

    def _login_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        self._l_user = _input("Username")
        self._l_pass = _input("Password", True)
        self._l_msg  = _lbl("", "sub", 12)
        self._l_msg.setStyleSheet("color: #e05050;")
        self._l_msg.setWordWrap(True)

        self._remember_cb = QCheckBox("🔐 Remember Me (tetap login)")
        self._remember_cb.setStyleSheet(f"color: {_T('text')};")
        lay.addWidget(self._remember_cb)

        ok = _btn("⚔️  Masuk ke Dunia", "solid", self._do_login, 48)
        for w_ in [self._l_user, self._l_pass, ok, self._l_msg]:
            lay.addWidget(w_)
        lay.addStretch()

        forgot_layout = QHBoxLayout()
        forgot_btn = _btn("❓ Lupa Password", "flat", self._forgot_password)
        lay.addWidget(forgot_btn)       
        self._l_pass.returnPressed.connect(self._do_login)
        self._l_user.returnPressed.connect(self._l_pass.setFocus)
        return w

    def _forgot_password(self):
        dlg = ChooseResetMethodDialog(self)
        dlg.exec()

    def _register_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(10)

        self._r_user  = _input("Username (huruf kecil, tanpa spasi)")
        self._r_disp  = _input("Nama Display (bebas)")
        self._r_pass  = _input("Password (min 4 karakter)", True)
        self._r_pass2 = _input("Konfirmasi Password", True)
        self._r_bio   = _input("Bio singkat (opsional)")

        lay.addWidget(_lbl("Pilih Class Awal:", size=12))
        self._r_class = QComboBox()
        self._r_class.setMinimumHeight(42)
        for cid, cdata in db.AVATAR_CLASSES.items():
            self._r_class.addItem(
                f"{cdata['icon']}  {cdata['name']}  —  {cdata['bonus']}",
                cid)

        self._r_msg = _lbl("", "sub", 12)
        self._r_msg.setWordWrap(True)

        ok = _btn("🌱  Buat Karakter Baru", "solid", self._do_register, 48)
        for w_ in [self._r_user, self._r_disp, self._r_pass,
                   self._r_pass2, self._r_bio, self._r_class,
                   ok, self._r_msg]:
            lay.addWidget(w_)
        lay.addStretch()
        return w

    def _do_login(self):
        loading = LoadingDialog("Memproses login", self)
        loading.show()
        QApplication.processEvents()
        
        try:
            r = db.login_user(self._l_user.text(), self._l_pass.text())
            if r["ok"]:
                SND.complete()
                if self._remember_cb.isChecked():
                    user = r["user"]
                    save_session(user["id"], user["username"], user["password_hash"])
                loading.accept()
                self.logged_in.emit(r["user"])
                self.accept()
            else:
                loading.accept()
                SND.error()
                self._l_msg.setText(r["msg"])
        except Exception as e:
            loading.accept()
            self._l_msg.setText(f"Error: {e}")

    def _do_register(self):
        u = self._r_user.text().strip()
        if not u or " " in u:
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(
                "Username tidak boleh kosong atau mengandung spasi!")
            return
        if len(self._r_pass.text()) < 4:
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText("Password minimal 4 karakter!")
            return
        if self._r_pass.text() != self._r_pass2.text():
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText("Password tidak cocok!")
            return
        r = db.register_user(
            u, self._r_pass.text(),
            self._r_disp.text().strip(),
            self._r_bio.text(),
            self._r_class.currentData(),
        )
        if r["ok"]:
            SND.level_up()
            self._r_msg.setStyleSheet(f"color:{_T('light')};")
            self._r_msg.setText("✅ " + r["msg"] + "\nSilakan login sekarang!")
        else:
            SND.error()
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(r["msg"])


# ══════════════════════════════════════════════════════════════════════════════
#  Forgot Password
# ══════════════════════════════════════════════════════════════════════════════
class ChooseResetMethodDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pilih Metode Reset Password")
        self.setFixedSize(350, 200)
        self.setStyleSheet(build_overworld_ss())
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_lbl("Pilih metode untuk mereset password:", size=12))
        btn_security = _btn("🔐 Pertanyaan Keamanan", "solid", self._choose_security)
        btn_backup = _btn("🎫 Kode Cadangan (Backup Code)", "solid", self._choose_backup)
        layout.addWidget(btn_security)
        layout.addWidget(btn_backup)
        cancel = _btn("Batal", "flat", self.reject)
        layout.addWidget(cancel)
    
    def _choose_security(self):
        self.accept()
        dlg = ResetPasswordBySecurityDialog(self.parent())
        dlg.exec()
    
    def _choose_backup(self):
        self.accept()
        dlg = ResetPasswordByBackupCodeDialog(self.parent())
        dlg.exec()


# ══════════════════════════════════════════════════════════════════════════════
#  Backup Code Reset Password
# ══════════════════════════════════════════════════════════════════════════════
class ResetPasswordByBackupCodeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password - Kode Cadangan")
        self.setFixedSize(450, 350)
        self.setStyleSheet(build_overworld_ss())
        self.user_id = None
        self._build()
    
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        self._step1()
    
    def _step1(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl("Masukkan username:", size=12))
        self.username_input = _input("Username")
        layout.addWidget(self.username_input)
        btn = _btn("Cek Kode Cadangan", "solid", self._check_username)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _check_username(self):
        username = self.username_input.text().strip()
        if not username:
            self.msg_label.setText("Username tidak boleh kosong!")
            return
        conn = db.get_conn()
        row = conn.execute("SELECT id FROM users WHERE username=?", (username.lower(),)).fetchone()
        conn.close()
        if not row:
            self.msg_label.setText("Username tidak ditemukan!")
            return
        self.user_id = row["id"]
        # Cek apakah user memiliki backup codes yang belum dipakai
        codes = db.get_user_backup_codes(self.user_id, only_unused=True)
        if not codes:
            self.msg_label.setText("User ini belum memiliki kode cadangan. Silakan generate di halaman Profile terlebih dahulu.")
            return
        self._step2()
    
    def _step2(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl("Masukkan salah satu kode cadangan Anda:", size=12))
        self.code_input = _input("Kode cadangan (8 karakter)")
        layout.addWidget(self.code_input)
        btn = _btn("Verifikasi", "solid", self._verify)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _verify(self):
        code = self.code_input.text().strip().upper()
        if not code:
            self.msg_label.setText("Kode tidak boleh kosong!")
            return
        if db.verify_backup_code(self.user_id, code):
            self._step3()
        else:
            self.msg_label.setText("Kode tidak valid atau sudah dipakai!")
    
    def _step3(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl("Buat password baru:", size=12))
        self.new_pass = _input("Password baru", password=True)
        self.confirm_pass = _input("Konfirmasi password", password=True)
        layout.addWidget(self.new_pass)
        layout.addWidget(self.confirm_pass)
        btn = _btn("Reset Password", "solid", self._reset)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _reset(self):
        p1 = self.new_pass.text()
        p2 = self.confirm_pass.text()
        if len(p1) < 4:
            self.msg_label.setText("Password minimal 4 karakter!")
            return
        if p1 != p2:
            self.msg_label.setText("Password tidak cocok!")
            return
        db.reset_password_with_backup_code(self.user_id, p1)
        _show(self, "Sukses", "Password berhasil direset! Silakan login.", "success")
        self.accept()
    
    def _clear(self):
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        self.setWindowIcon(QIcon(get_icon_path('craftlife.ico')))
        AppState.set_user(user["id"])
        TimeSync.sync()
        db.reset_daily_tasks(user["id"])

        dn = user.get("display_name") or user.get("username", "")
        self.setWindowTitle(f"⛏ CraftLife — {dn}")
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(build_ss())
        self._pages: dict = {}
        self._build()
        AppState.register(self._topbar.refresh)

        self._timer = QTimer()
        self._timer.timeout.connect(self._topbar.refresh)
        self._timer.start(20000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        super().keyPressEvent(event)

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        self._topbar = TopBar(self._show_notif, self._goto_profile)
        root.addWidget(self._topbar)

        # Body
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        self._nav = NavBar()
        self._nav.tab_changed.connect(self._switch)
        body.addWidget(self._nav)

        uid = AppState.user_id
        # ── Pages created HERE, after AppState.set_user() ─────────────────────
        self._pages = {
            "habits":      TaskPage(uid, "habit"),
            "dailies":     TaskPage(uid, "daily"),
            "todos":       TaskPage(uid, "todo"),
            "sport":       SportTrackPage(uid),
            "economy":     EconomyPage(uid),
            "shop":        ShopPage(uid),
            "pets":        PetsPage(uid),
            "friends":     FriendsPage(uid),
            "guild":       GuildPage(uid),
            "stats":       StatsPage(uid),
            "profile":     ProfilePage(uid),
            "settings":    SettingsPage(uid),
            "leaderboard": LeaderboardPage(),
        }
        self._pages["settings"].theme_changed.connect(self._retheme)

        self._stack = QStackedWidget()
        for p in self._pages.values():
            self._stack.addWidget(p)
        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        self._switch("habits")

    def _switch(self, key: str):
        page = self._pages.get(key)
        if not page:
            return
        self._stack.setCurrentWidget(page)
        if hasattr(page, "load"):
            try:
                page.load()
            except Exception as e:
                import traceback
                err_text = traceback.format_exc()
                with open("crash.log", "a", encoding="utf-8") as f:
                    f.write(f"{datetime.now()} - Error loading {key}: {e}\n{err_text}\n")
                # Tampilkan pesan error ke user
                _show(self, "Error", f"Gagal memuat halaman {key}: {e}", "error")
        if hasattr(page, "_inner"):
            fade_in(page._inner, 180)

    def _show_notif(self):
        NotifPopup(AppState.user_id, self).exec()

    def _goto_profile(self):
        self._nav._select("profile")
        self._switch("profile")

    def _retheme(self):
        """Called when user changes theme in Settings — updates everything."""
        th  = db.get_user_theme(AppState.user_id)
        apply_theme(th)
        SoundEngine.enabled = bool(
            AppState.user().get("sound_enabled", 1))

        new_ss = build_ss()
        QApplication.instance().setStyleSheet(new_ss)
        self.setStyleSheet(new_ss)

        self._topbar.retheme()
        self._nav.retheme()

        # Reload every page so colours update
        for p in self._pages.values():
            p.setStyleSheet(new_ss)
            if hasattr(p, "load"):
                try:
                    p.load()
                except Exception:
                    pass

        _show(self, "Theme", "Theme berhasil diubah! ✨", "success")

    def closeEvent(self, e):
        AppState.unregister(self._topbar.refresh)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    setup_error_handling()
    db.init_db()
    app = QApplication(sys.argv)
    app.setApplicationName("CraftLife")
    app.setStyleSheet(build_ss())

    login = LoginWindow()
    main_win = None

    def on_login(user):
        nonlocal main_win
        AppState.set_user(user["id"])
        th = db.get_user_theme(user["id"])
        apply_theme(th)
        app.setStyleSheet(build_ss())
        main_win = MainWindow(user)
        main_win.logout_signal.connect(lambda: login.show())  # saat close, tampilkan login
        main_win.show()
        login.hide()   # sembunyikan login

    def on_main_window_closed():
        if main_win is not None:
            main_win.deleteLater()
        login.show()  # tampilkan login lagi

    login.logged_in.connect(on_login)

    result = login.exec()
    if result == QDialog.DialogCode.Accepted:
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()