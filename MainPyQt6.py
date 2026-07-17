"""
CraftLife Desktop Version  —  MainPyQt6.py  v1.0
PyQt6 Windows / Linux / macOS
Install : pip install PyQt6
Run     : python MainPyQt6.py
"""

# =============================================================================
# STANDARD LIBRARY IMPORTS
# =============================================================================
import calendar as calmod
import json
import os
import sys
import tempfile
import time as time_module
import traceback
from datetime import date, datetime, timedelta
from functools import partial
from io import BytesIO
import re

# =============================================================================
# THIRD-PARTY IMPORTS (PyQt6)
# =============================================================================
from PyQt6.QtCore import (
    QDate, QDateTime, QEasingCurve, QMimeData, QPropertyAnimation,
    Qt, QTimer, QUrl, pyqtSignal
)
from PyQt6.QtGui import QColor, QDrag, QFont, QIcon, QTextCharFormat, QTextCursor
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QColorDialog,
    QComboBox, QDateEdit, QDateTimeEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QFrame, QGraphicsOpacityEffect, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
    QSpacerItem, QSpinBox, QSplitter, QStackedWidget, QSystemTrayIcon,
    QTabBar, QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit,
    QTimeEdit, QToolButton, QTreeWidget, QTreeWidgetItem,
    QTreeWidgetItemIterator, QVBoxLayout, QWidget
)

# =============================================================================
# EXTERNAL API & NETWORK
# =============================================================================
import requests

# =============================================================================
# INTERNAL MODULES
# =============================================================================
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
from food_data import get_food_name
from holidays import get_holiday_name, get_holidays_for_year
from translations import get_text

# ═══════════════════════════════════════════════════════════════════
#  OPTIONAL IMPORTS FOR EXPORT (Excel, Word, PDF, Charts)
# ═══════════════════════════════════════════════════════════════════
try:
    import matplotlib.pyplot as plt
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
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Error.txt")
    def handler(err_type, err_value, tb):
        err_text = "".join(traceback.format_exception(err_type, err_value, tb))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(err_text)
        # ── BACKUP DATABASE SAAT CRASH ──
        try:
            import database as db
            db.backup_database()
        except:
            pass
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle(tr("app_error_title"))
        msg.setText(f"Terjadi kesalahan fatal!\n\n{err_value}")
        msg.setInformativeText("Detail error disimpan di Error.txt.\nDatabase telah dibackup otomatis.")
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
    _offset = 0
    _last_sync = 0
    _zone = "Asia/Jakarta"
    _last_attempt = 0
    _backoff = 60
    DEBUG = True

    @classmethod
    def sync(cls):
        """Sinkronkan waktu dengan server (dengan debug print)."""
        now = time_module.time()
        
        # Debug: tampilkan status backoff
        if cls.DEBUG:
            print(f"[TimeSync] 🔄 Sync dipanggil. Backoff tersisa: {cls._backoff:.0f} detik")
        
        if now - cls._last_attempt < cls._backoff:
            if cls.DEBUG:
                print(f"[TimeSync] ⏳ Menunggu backoff... ({cls._backoff:.0f}s tersisa)")
            return False
        cls._last_attempt = now

        # Daftar API cadangan (gratis & tanpa API key)
        apis = [
            f"https://time.now/developer/api/timezone/{cls._zone}",
            f"https://timeapi.world/api/timezone/{cls._zone}",
            "https://1.1.1.1/cdn-cgi/trace"  # Cloudflare fallback
        ]

        if cls.DEBUG:
            print(f"[TimeSync] 🌐 Mencoba {len(apis)} API...")

        for idx, url in enumerate(apis, 1):
            try:
                if cls.DEBUG:
                    print(f"[TimeSync]   [{idx}] Mencoba: {url}")

                resp = requests.get(url, timeout=5)
                
                if cls.DEBUG:
                    print(f"[TimeSync]   [{idx}] HTTP Status: {resp.status_code}")

                if resp.status_code != 200:
                    if cls.DEBUG:
                        print(f"[TimeSync]   [{idx}] ❌ Status bukan 200, lanjut...")
                    continue

                # Parse response berdasarkan URL
                server_unixtime = None
                if "time.now" in url or "timeapi.world" in url:
                    data = resp.json()
                    server_unixtime = data.get('unixtime')
                    if cls.DEBUG:
                        print(f"[TimeSync]   [{idx}] 📦 JSON diterima, unixtime: {server_unixtime}")
                else:  # Cloudflare trace
                    for line in resp.text.splitlines():
                        if line.startswith('ts='):
                            server_unixtime = int(float(line.split('=')[1]))
                            if cls.DEBUG:
                                print(f"[TimeSync]   [{idx}] 📝 Cloudflare trace, ts={server_unixtime}")
                            break
                    else:
                        if cls.DEBUG:
                            print(f"[TimeSync]   [{idx}] ❌ Gagal parsing Cloudflare trace")
                        continue

                if server_unixtime is None:
                    if cls.DEBUG:
                        print(f"[TimeSync]   [{idx}] ❌ unixtime kosong, lanjut...")
                    continue

                # Hitung offset
                local_unixtime = int(time_module.time())
                cls._offset = server_unixtime - local_unixtime
                cls._last_sync = now
                cls._backoff = 3600  # sukses, jeda 1 jam

                if cls.DEBUG:
                    print(f"[TimeSync] ✅ SUKSES!")
                    print(f"[TimeSync]   🕐 Server time:  {server_unixtime}")
                    print(f"[TimeSync]   🖥️ Local time:   {local_unixtime}")
                    print(f"[TimeSync]   ⏱️  Offset:       {cls._offset} detik")
                    print(f"[TimeSync]   📅 Server time: {datetime.fromtimestamp(server_unixtime).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"[TimeSync]   📅 Local time:  {datetime.fromtimestamp(local_unixtime).strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"[TimeSync]   ⏳ Next sync:   {cls._backoff} detik lagi")
                return True

            except Exception as e:
                if cls.DEBUG:
                    print(f"[TimeSync]   [{idx}] ❌ Error: {type(e).__name__}: {e}")
                continue  # coba API berikutnya

        # Semua API gagal
        cls._backoff = min(cls._backoff * 2, 3600)
        if cls.DEBUG:
            print(f"[TimeSync] ❌ SEMUA API GAGAL! Backoff menjadi {cls._backoff:.0f} detik")
            print(f"[TimeSync]   💡 Aplikasi tetap berjalan dengan waktu lokal (anti-exploit nonaktif)")
        return False

    @classmethod
    def get_current_time(cls):
        """Mendapatkan datetime objek dari waktu server yang sudah disinkronkan"""
        if cls._last_sync == 0:
            if cls.DEBUG:
                print("[TimeSync] ⚠️ Belum pernah sync, mencoba sync...")
            cls.sync()
        local_now = time_module.time()
        server_now = local_now + cls._offset
        dt = datetime.fromtimestamp(server_now)
        
        if cls.DEBUG:
            print(f"[TimeSync] 🕐 get_current_time() -> {dt.strftime('%Y-%m-%d %H:%M:%S')} (offset={cls._offset})")
        
        return dt

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
    def __init__(self, message="Loading...", parent=None):
        super().__init__(parent)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setModal(True)
        self.setMinimumSize(300, 100)
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
    _lang: str = "en"
    _cbs: list = []
    _lang_cbs: list = []

    @classmethod
    def set_user(cls, uid: int):
        cls.user_id = uid
        t = db.get_user_theme(uid)
        apply_theme(t)
        SoundEngine.enabled = bool(db.get_user(uid).get("sound_enabled", 1))
        # Load language from DB
        cls._lang = db.get_user_language(uid)

    @classmethod
    def get_language(cls):
        return cls._lang

    @classmethod
    def set_language(cls, lang_code):
        if lang_code not in ("id", "en"):
            return
        cls._lang = lang_code
        if cls.user_id:
            db.set_user_language(cls.user_id, lang_code)
        # Trigger all language callbacks
        for cb in cls._lang_cbs:
            try:
                cb()
            except:
                pass

    @classmethod
    def register_lang_cb(cls, cb):
        if cb not in cls._lang_cbs:
            cls._lang_cbs.append(cb)

    @classmethod
    def unregister_lang_cb(cls, cb):
        if cb in cls._lang_cbs:
            cls._lang_cbs.remove(cb)

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
# Fungsi global untuk memudahkan akses terjemahan
def tr(key, **kwargs):
    """Get translated text for current user language."""
    lang = AppState.get_language()
    text = get_text(key, lang)
    if kwargs:
        return text.format(**kwargs)
    return text

def _lbl(text, obj="", size=13, bold=False):
    if size <= 0: size = 10
    w = QLabel(text)
    w.setFont(QFont("Segoe UI", size, QFont.Weight.Bold if bold else QFont.Weight.Normal))
    if obj: w.setObjectName(obj)
    return w

def _btn(text, obj="", slot=None, h=38):
    b = QPushButton(text)
    if obj:
        b.setObjectName(obj)
    if slot:
        b.clicked.connect(slot)
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
    dlg.setMinimumWidth(380)
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
    ok = _btn(tr("msg_ok"), "solid", dlg.accept, 40)
    lay.addWidget(ok)
    dlg.exec()



# ══════════════════════════════════════════════════════════════════════════════
#  TOP BAR
# ══════════════════════════════════════════════════════════════════════════════
class TopBar(QWidget):
    def __init__(self, on_notif, on_profile):
        super().__init__()
        
        self.setMinimumHeight(72)
        self._update_bg()

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)

        self._logo = QLabel(tr("app_logo"))
        self._logo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        self._logo.setStyleSheet(f"color: {_T('light')};")
        lay.addWidget(self._logo)
        lay.addSpacing(8)

        # XP column
        xp_col = QVBoxLayout()
        xp_col.setSpacing(3)
        self._xp_lbl = QLabel(tr("level_label", lvl=1))
        self._xp_lbl.setStyleSheet(
            f"color: {_T('accent')}; font-size: 11px; font-weight: bold;")
        self._xp_bar = QProgressBar()
        self._xp_bar.setMinimumHeight(10)
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
        self._notif_btn.setMinimumWidth(44)
        self._notif_btn.setMinimumHeight(34)
        lay.addWidget(self._notif_btn)

        prof_btn = _btn("👤", slot=on_profile)
        prof_btn.setMinimumWidth(44)
        prof_btn.setMinimumHeight(34)
        lay.addWidget(prof_btn)

        exit_btn = _btn("🚪", slot=QApplication.instance().quit)
        exit_btn.setMinimumWidth(44)
        exit_btn.setMinimumHeight(34)
        lay.addWidget(exit_btn)

        logout_btn = _btn(tr("logout"), slot=self._logout)
        logout_btn.setMinimumWidth(70)
        logout_btn.setMinimumHeight(34)
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
        # ── FORCE CHECKPOINT SEBELUM LOGOUT ──
        db.force_checkpoint()
        
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
        self._xp_lbl.setText(tr("level_xp_format", lvl=lvl, name=dn, xp=xp, need=need))
        self._xp_bar.setMaximum(need)
        self._xp_bar.setValue(int(xp))
        self._hp_lbl.setText(tr("hp_format", hp=u['hp'], max_hp=u['max_hp']))

        # MP chip shows skill name
        cls   = u.get("avatar_class", "warrior")
        skill = db.CLASS_SKILLS.get(cls, {})
        self._mp_lbl.setText(tr("mp_format", mp=u['mp'], max_mp=u['max_mp'], skill=skill.get('name','?')))

        self._gold_lbl.setText(tr("gold_format", gold=u['gold']))
        notifs = db.get_notifications(AppState.user_id)
        self._notif_btn.setText(
            tr("notif_button", count=len(notifs)) if notifs else tr("notif_button_empty"))

    def load(self):
        """Update UI text when language changes"""
        self._logo.setText(tr("app_logo"))
        self.refresh() 

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

    ICON_MAP = {
        "habits": "⛏",
        "dailies": "📅",
        "todos": "📜",
        "sport": "🏅",
        "economy": "💰",
        "health_food": "💚",
        "calendar": "📅",
        "notes": "📝",
        "reminders": "⏰",
        "shop": "🏪",
        "pets": "🐾",
        "friends": "👥",
        "guild": "⚔️",
        "stats": "📊",
        "achievements": "🏆",
        "profile": "🎭",
        "settings": "⚙️",
        "leaderboard": "🎖️",
    }

    _TABS = [
        ("nav_habits",      "habits"),
        ("nav_dailies",     "dailies"),
        ("nav_quests",      "todos"),
        ("nav_sport",       "sport"),
        ("nav_economy",     "economy"),
        ("nav_health_food", "health_food"),
        ("nav_calendar", "calendar"),
        ("nav_notes", "notes"),
        ("nav_reminders", "reminders"),
        ("nav_shop",        "shop"),
        ("nav_pets",        "pets"),
        ("nav_friends",     "friends"),
        ("nav_guild",       "guild"),
        ("nav_stats",       "stats"),
        ("nav_achievements","achievements"),
        ("nav_profile",     "profile"),
        ("nav_settings",    "settings"),
        ("nav_leaderboard", "leaderboard")
    ]

    def __init__(self):
        super().__init__()
        
        self.setMinimumWidth(90)
        self._btns: dict = {}
        self._active = ""
        self._build()
        # Register untuk perubahan bahasa
        AppState.register_lang_cb(self.reload_texts)
        self.reload_texts()
        self._select("habits")

    def load(self):
        """Update UI text when language changes"""
        self.reload_texts()

    def _build(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 6, 0, 6)
        lay.setSpacing(2)
        # Simpan hanya tombol, label akan diisi di reload_texts
        for key_label, key in self._TABS:
            b = QPushButton()
            b.setCheckable(True)
            b.setMinimumHeight(75)       # cukup untuk dua baris
            b.setStyleSheet("text-align: center;")
            b.clicked.connect(lambda _, k=key: self._select(k))
            lay.addWidget(b)
            self._btns[key] = b
        lay.addStretch()
        self.retheme()

    def reload_texts(self):
        for key_label, key in self._TABS:
            b = self._btns.get(key)
            if b:
                icon = self.ICON_MAP.get(key, "❓")
                b.setText(f"{icon}\n{tr(key_label)}")

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
        titles = {"habit": tr("dialog_add_habit"),
                  "daily": tr("dialog_add_daily"),
                  "todo":  tr("dialog_add_todo")}
        self.setWindowTitle(titles.get(mode, tr("dialog_add")))
        self.setMinimumWidth(460)
        self.setMinimumHeight(460)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Name
        lay.addWidget(_lbl(tr("dialog_name"), size=12))
        self._name = _input(tr("dialog_name_placeholder"))
        lay.addWidget(self._name)

        # Icon
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        icons = [
            (tr("task_icon_combat"), "⚔️"),
            (tr("task_icon_study"), "📚"),
            (tr("task_icon_exercise"), "🏃"),
            (tr("task_icon_health"), "🍎"),	
            (tr("task_icon_sleep"), "💤"),	
            (tr("task_icon_mindfulness"), "🧘"),	
            (tr("task_icon_hydration"), "💧"),	
            (tr("task_icon_growth"), "🌱"),	
            (tr("task_icon_focus"), "🎯"),	
            (tr("task_icon_ideas"), "💡"),
            (tr("task_icon_quest"), "📜"),	
            (tr("task_icon_build"), "🏗️")
        ]
        self._icon = _combo(icons)
        lay.addWidget(self._icon)

        # Difficulty / priority
        if self.mode == "todo":
            lay.addWidget(_lbl(tr("dialog_priority"), size=12))
            opts = [
                (tr("task_priority_trivial_text"), "trivial"),
                (tr("task_priority_easy_text"), "easy"),
                (tr("task_priority_medium_text"), "medium"),
                (tr("task_priority_hard_text"), "hard"),
            ]
        else:
            lay.addWidget(_lbl(tr("dialog_difficulty"), size=12))
            opts = [
                (tr("task_diff_easy_text"), "easy"),
                (tr("task_diff_medium_text"), "medium"),
                (tr("task_diff_hard_text"), "hard"),
                (tr("task_diff_epic_text"), "epic"),
            ]
        self._diff = _combo(opts)
        self._diff.setCurrentIndex(1)
        lay.addWidget(self._diff)

        # Notes
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder"))
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl(tr("dialog_folder"), size=12))
        _folders = db.get_task_folders(self.user_id, self.mode)
        _fopts = [(tr("dialog_no_folder"), None)] + [(f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok = _btn(tr("dialog_add"), "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        sa = _scrolled(content)
        root.addWidget(sa)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("msg_name_empty"), "error")
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
        self.setWindowTitle(tr("dialog_edit_mode", mode=mode.capitalize()))
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
        lay.addWidget(_lbl(tr("dialog_name"), size=12))
        self._name = _input(tr("dialog_name_placeholder"))
        if self.item:
            self._name.setText(self.item["name"])
        lay.addWidget(self._name)

        # Icon (sama seperti AddTaskDialog)
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
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
            lay.addWidget(_lbl(tr("dialog_priority"), size=12))
            opts = [
                (tr("task_priority_trivial_text"), "trivial"), 
                (tr("task_priority_easy_text"), "easy"), 
                (tr("task_priority_medium_text"), "medium"), 
                (tr("task_priority_hard_text"), "hard")
            ]
        else:
            lay.addWidget(_lbl(tr("dialog_difficulty"), size=12))
            opts = [
                (tr("task_diff_easy_text"), "easy"), 
                (tr("task_diff_medium_text"), "medium"), 
                (tr("task_diff_hard_text"), "hard"), 
                (tr("task_diff_epic_text"), "epic")
            ]
        self._diff = _combo(opts)
        idx = self._diff.findData(self.item.get("difficulty") or self.item.get("priority","medium"))
        if idx >= 0: self._diff.setCurrentIndex(idx)
        lay.addWidget(self._diff)

        # Notes
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder2"))
        if self.item:
            self._notes.setText(self.item["notes"])
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl(tr("dialog_folder"), size=12))
        _folders = db.get_task_folders(self.user_id, self.mode)
        _fopts = [(tr("dialog_no_folder"), None)] + [
            (f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        cur_fid = self.item.get("folder_id")
        if cur_fid:
            idx = next((i for i,(_, d) in enumerate(_fopts) if d == cur_fid), 0)
            self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok = _btn(tr("dialog_save"), "solid", self._save, 46)
        lay.addWidget(ok)
        sa = _scrolled(content)
        root.addWidget(sa)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("msg_name_empty"), "error")
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
        self.folder = folder
        self.mode = mode
        self.user_id = user_id
        self.on_reload = on_reload
        self.folder_id = folder["id"] 
        self._collapsed = bool(folder.get("collapsed", 0))
        self._item_count = 0
        self._build()
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-craftlife-card"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        raw = event.mimeData().data("application/x-craftlife-card")
        info = json.loads(raw.data().decode())
        if info["mode"] == self.mode and info["user_id"] == self.user_id:
            source_folder = info.get("current_folder_id")
            target_folder = self.folder_id
            if source_folder == target_folder:
                # Drop di folder yang sama → tidak ada reorder, biarkan
                event.acceptProposedAction()
            else:
                # Pindahkan item ke folder ini (posisi terakhir)
                db.move_item_to_folder(self.user_id, self.mode, info["item_id"], target_folder)
                self.on_reload()
                event.acceptProposedAction()
        else:
            event.ignore()

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
        self._toggle_btn.setMinimumSize(28, 28)
        self._toggle_btn.setStyleSheet("border: none; background: transparent;")
        self._toggle_btn.clicked.connect(self._toggle)
        row.addWidget(self._toggle_btn)

        # Icon folder
        ico_lbl = QLabel(self.folder.get("icon", "\U0001f4c1"))
        ico_lbl.setFont(QFont("Segoe UI", 20))
        ico_lbl.setMinimumWidth(34)
        row.addWidget(ico_lbl)

        # Nama folder + jumlah item
        info_col = QVBoxLayout()
        info_col.setSpacing(1)
        self._name_lbl = QLabel(self.folder["name"])
        self._name_lbl.setStyleSheet(
            f"color:{_T('text')}; font-weight:bold; font-size:14px;"
            f" background:transparent; border:none;")
        info_col.addWidget(self._name_lbl)
        self._count_lbl = QLabel(tr("folder_item_count", count=0))
        self._count_lbl.setStyleSheet(
            f"color:{_T('muted')}; font-size:11px;"
            f" background:transparent; border:none;")
        info_col.addWidget(self._count_lbl)
        row.addLayout(info_col, 1)

        # Tombol aksi (edit, duplikat, hapus)
        edit_btn = _btn("\u270f\ufe0f", h=36)
        edit_btn.setMinimumWidth(36)
        edit_btn.setToolTip(tr("folder_tooltip_edit"))
        edit_btn.clicked.connect(self._edit_folder)
        row.addWidget(edit_btn)

        dup_btn = _btn("\U0001f4cb", h=36)
        dup_btn.setMinimumWidth(36)
        dup_btn.setToolTip(tr("folder_tooltip_dup"))
        dup_btn.clicked.connect(self._dup_folder)
        row.addWidget(dup_btn)

        del_btn = _btn("\U0001f5d1", "danger", h=36)
        del_btn.setMinimumWidth(36)
        del_btn.setToolTip(tr("folder_tooltip_del"))
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
        (tr("folder_icon_default"), "📁"),
        (tr("folder_icon_favorite"), "⭐"),
        (tr("folder_icon_priority"), "🔥"),
        (tr("folder_icon_exercise"), "💪"),
        (tr("folder_icon_study"), "📖"),
        (tr("folder_icon_goal"), "🎯"),
        (tr("folder_icon_night"), "🌙"),
        (tr("folder_icon_morning"), "☀️"),
        (tr("folder_icon_hobby"), "🎮"),
        (tr("folder_icon_work"), "💼"),
        (tr("folder_icon_home"), "🏠"),
        (tr("folder_icon_health"), "🌿"),
    ]

    def __init__(self, mode: str, user_id: int,
                 existing=None, parent=None):
        super().__init__(parent)
        self.mode     = mode
        self.user_id  = user_id
        self.existing = existing
        title = "✏️ Edit Folder" if existing else tr("folder_create_new")
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

        lay.addWidget(_lbl(tr("folder_name"), size=12))
        self._name = _input(tr("folder_name_placeholder"))
        if self.existing:
            self._name.setText(self.existing["name"])
        lay.addWidget(self._name)

        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        self._icon = _combo(self.FOLDER_ICONS)
        if self.existing:
            idx = next((i for i, (_, d) in enumerate(self.FOLDER_ICONS)
                        if d == self.existing.get("icon", "📁")), 0)
            self._icon.setCurrentIndex(idx)
        lay.addWidget(self._icon)

        ok_text = tr("dialog_save") if self.existing else tr("folder_create_btn")
        ok = _btn(ok_text, "solid", self._save, 44)
        lay.addWidget(ok)

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("folder_name_empty"), "error")
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
#  Draggable Card Widget  (untuk drag & drop ke folder lain)
# ══════════════════════════════════════════════════════════════════════════════
class DraggableCard(QFrame):
    """Kartu yang bisa di-drag untuk dipindahkan ke folder lain."""
    def __init__(self, item_id: int, mode: str, user_id: int, current_folder_id: int, content_widget: QWidget, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.mode = mode
        self.user_id = user_id
        self.current_folder_id = current_folder_id
        self.setAcceptDrops(True)
        self.setObjectName("card")
        self.setStyleSheet(f"QFrame#card {{ background:{_T('panel')}; border:1px solid {_T('border')}; border-radius:8px; }}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_widget)
        self.drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if self.drag_start_pos is None:
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        drag = QDrag(self)
        mime = QMimeData()
        data = {
            "item_id": self.item_id,
            "mode": self.mode,
            "user_id": self.user_id,
            "current_folder_id": self.current_folder_id
        }
        mime.setData("application/x-craftlife-card", json.dumps(data).encode())
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-craftlife-card"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat("application/x-craftlife-card"):
            event.ignore()
            return
        raw = event.mimeData().data("application/x-craftlife-card")
        info = json.loads(raw.data().decode())
        if info["user_id"] != self.user_id or info["mode"] != self.mode:
            event.ignore()
            return

        if info["item_id"] == self.item_id:
            event.acceptProposedAction()
            return

        source_folder = info.get("current_folder_id")
        target_folder = self.current_folder_id

        if source_folder == target_folder:
            # Reorder: pindahkan source relatif terhadap target
            r = db.reorder_item_relative(self.user_id, self.mode, info["item_id"], self.item_id)
            if not r.get("ok"):
                print(f"Reorder error: {r.get('msg')}")
        else:
            # Pindahkan ke folder target
            db.move_item_to_folder(self.user_id, self.mode, info["item_id"], target_folder)

        # Cari parent terdekat yang punya method load()
        parent = self.parent()
        while parent and not hasattr(parent, "load"):
            parent = parent.parent()
        if parent and hasattr(parent, "load"):
            parent.load()
        event.acceptProposedAction()

# ══════════════════════════════════════════════════════════════════════════════
#  TASK PAGE  (habits / dailies / todos)  — with sub-tabs + folders
# ══════════════════════════════════════════════════════════════════════════════
class TaskPage(QWidget):
    def __init__(self, user_id: int, mode: str):
        super().__init__()
        self.user_id = user_id
        self.mode    = mode
        self.card_widgets = {}
        self._build()
        AppState.register(self.load)
        AppState.register_lang_cb(self.load)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        titles = {"habit": tr("task_title_habit"),
                  "daily": tr("task_title_daily"),
                  "todo":  tr("task_title_todo")}
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(titles[self.mode], "section", 14, True))
        hdr.addStretch()
        folder_btn = _btn(tr("task_folder_button"), h=36)
        folder_btn.setMinimumWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add = _btn(tr("task_add_button"), "solid", self._open_add)
        add.setMinimumWidth(130)
        hdr.addWidget(add)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Filter bar
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("task_search"))
        self.search_input.textChanged.connect(self.load)
        self.filter_combo = QComboBox()
        if self.mode == "todo":
            self.filter_combo.addItem(tr("task_filter_all"), "all")
            self.filter_combo.addItem(tr("task_priority_trivial"), "trivial")
            self.filter_combo.addItem(tr("task_priority_easy"), "easy")
            self.filter_combo.addItem(tr("task_priority_medium"), "medium")
            self.filter_combo.addItem(tr("task_priority_hard"), "hard")
        else:
            self.filter_combo.addItem(tr("task_filter_all"), "all")
            self.filter_combo.addItem(tr("task_difficulty_easy"), "easy")
            self.filter_combo.addItem(tr("task_difficulty_medium"), "medium")
            self.filter_combo.addItem(tr("task_difficulty_hard"), "hard")
            self.filter_combo.addItem(tr("task_difficulty_epic"), "epic")
        self.filter_combo.currentIndexChanged.connect(self.load)
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.filter_combo)
        root.addWidget(filter_widget)

        # Tab widget: Semua + per kategori icon
        self._tabs = QTabWidget()
        self._inner_all = QWidget()
        self._lay_all   = QVBoxLayout(self._inner_all)
        self._lay_all.setSpacing(8)
        self._lay_all.addStretch()
        self._tabs.addTab(_scrolled(self._inner_all), "🗂 " + tr("task_tab_all"))

        self._cat_lays: dict   = {}
        self._cat_inners: dict  = {}
        for key, cat in TASK_ICON_CATEGORIES.items():
            inner = QWidget()
            lay   = QVBoxLayout(inner)
            lay.setSpacing(8)
            lay.addStretch()
            self._cat_lays[key]   = lay
            self._cat_inners[key] = inner
            self._tabs.addTab(_scrolled(inner), f"{cat['icon']} {cat['name']}")

        root.addWidget(self._tabs, 1)
        self.load()

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

    def load(self):
        self.card_widgets.clear()
        if not AppState.user_id:
            return
        db.reset_daily_tasks(self.user_id)

        self._clear_lay(self._lay_all)
        for lay in self._cat_lays.values():
            self._clear_lay(lay)

        all_items = self._get_items()
        if self.mode == "todo":
            all_items.sort(key=lambda x: (x.get('done', 0), -x.get('sort_order', 0)))
        else:
            all_items.sort(key=lambda x: (x.get('done_today', 0), -x.get('sort_order', 0)))
        search     = self.search_input.text().lower()
        filter_diff = self.filter_combo.currentData()
        if search:
            all_items = [i for i in all_items if search in i["name"].lower()]
        if filter_diff != "all":
            all_items = [i for i in all_items
                         if i.get("difficulty", i.get("priority", "")).lower() == filter_diff]

        folders = db.get_task_folders(self.user_id, self.mode)

        self._render_to_layout(self._lay_all, self._inner_all, all_items, folders)
        by_cat: dict = {}
        for item in all_items:
            icon_key = item.get("icon", "").replace("\ufe0f", "").strip()
            matched = None
            for k in self._cat_lays:
                if k.replace("\ufe0f", "").strip() == icon_key:
                    matched = k
                    break
            if matched:
                by_cat.setdefault(matched, []).append(item)

        for key, lay in self._cat_lays.items():
            cat_items = by_cat.get(key, [])
            self._render_to_layout(lay, self._cat_inners[key], cat_items, folders)

    # ========== RENDER WITH DROP AREA ==========
    def _render_to_layout(self, lay: QVBoxLayout, container: QWidget, items: list, folders: list):
        if not items and not folders:
            e_icon = {"habit": "⛏️", "daily": "📅", "todo": "📜"}[self.mode]
            e_msg  = {"habit": tr("task_empty_habit"),
                      "daily": tr("task_empty_daily"),
                      "todo": tr("task_empty_todo")}[self.mode]
            el = _lbl(f"{e_icon}  {e_msg}", "sub", 13)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color: {_T('muted')}; padding: 40px;")
            lay.insertWidget(0, el)
            return

        insert_pos = 0
        folder_items: dict = {f["id"]: [] for f in folders}
        ungrouped: list = []
        for item in items:
            fid = item.get("folder_id")
            if fid and fid in folder_items:
                folder_items[fid].append(item)
            else:
                ungrouped.append(item)

        for folder in folders:
            fw = FolderWidget(folder, self.mode, self.user_id, self.load, parent=container)
            cards_in_folder = folder_items.get(folder["id"], [])
            if not cards_in_folder:
                empty_lbl = QLabel("   📭  " + tr("folder_empty"))
                empty_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards_in_folder:
                    fw.add_card(self._create_card_widget(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        for item in ungrouped:
            lay.insertWidget(insert_pos, self._create_card_widget(item))
            insert_pos += 1

        # ── Drop area untuk "Tanpa Folder" ──
        drop_area = QFrame()
        drop_area.setAcceptDrops(True)
        drop_area.setMinimumHeight(50)
        drop_area.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T('border')};
                border-radius: 8px;
                background: {_T('bg')};
                margin-top: 8px;
            }}
            QFrame:hover {{
                border-color: {_T('accent')};
                background: {_T('panel')};
            }}
        """)
        drop_label = QLabel(tr("drop_here_to_remove_folder") if hasattr(tr, "__call__") else "📂 Taruh di sini untuk keluarkan dari folder")
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        drop_area_layout = QVBoxLayout(drop_area)
        drop_area_layout.addWidget(drop_label)

        def _drag_enter(e):
            if e.mimeData().hasFormat("application/x-craftlife-card"):
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dragEnterEvent = _drag_enter

        def _drop(e):
            raw = e.mimeData().data("application/x-craftlife-card")
            info = json.loads(raw.data().decode())
            if info["mode"] == self.mode and info["user_id"] == self.user_id:
                db.set_item_folder(self.user_id, self.mode, info["item_id"], None)
                self.load()
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dropEvent = _drop

        lay.insertWidget(insert_pos, drop_area)

    def _update_item(self, item_id: int):
        """Update hanya satu kartu tanpa reload seluruh halaman"""
        items = self._get_items()
        item = next((i for i in items if i['id'] == item_id), None)
        if not item:
            self.load()
            return

        card = self.card_widgets.get(item_id)
        if not card:
            self.load()
            return

        # Hapus konten lama
        while card.layout().count():
            child = card.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Buat konten baru
        new_content = self._build_card_content(item)
        card.layout().addWidget(new_content)
        card.current_folder_id = item.get('folder_id')   # update untuk drag

        # Update top bar
        AppState.refresh()

    # ========== MAKE CARD (dengan DraggableCard) ==========
    def _build_card_content(self, item: dict) -> QWidget:
        """Buat widget konten kartu (tanpa wrapper DraggableCard)"""
        done = bool(item.get("done_today") or item.get("done", False))

        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        # Icon
        ico = QLabel(item["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setMinimumWidth(38)
        row.addWidget(ico)

        # Info block
        info = QVBoxLayout()
        info.setSpacing(2)

        name_style = (f"text-decoration:line-through; color:{_T('muted')};"
                    if done else f"color:{_T('text')}; font-weight:bold;")
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; {name_style}")
        info.addWidget(nm)

        if self.mode == "todo":
            val = item.get("priority", "medium")
            color_map = {"trivial": _T("muted"), "easy": _T("light"),
                        "medium": "#f0a800", "hard": "#e05050"}
            label_text = tr(f"task_priority_{val}")
        else:
            val = item.get("difficulty", "medium")
            color_map = {"easy": "#80c000", "medium": "#f0a800",
                        "hard": "#e05050", "epic": "#a97fff"}
            label_text = tr(f"task_difficulty_{val}")
        diff_lbl = QLabel(label_text)
        diff_lbl.setStyleSheet(f"color: {color_map.get(val, '#888')}; font-size: 10px; font-weight: bold;")
        info.addWidget(diff_lbl)

        streak_txt = (tr("task_streak_days", streak=item['streak'])
                    if item.get("streak", 0) > 0 else "")
        sub = QLabel(tr("task_reward_format", xp=item['xp_reward'], gold=item['gold_reward'], streak=streak_txt))
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        fail_streak = item.get("fail_streak", 0)
        if fail_streak > 0:
            fail_lbl = QLabel(tr("task_fail_streak_days", streak=fail_streak))
            fail_lbl.setStyleSheet(f"color:#e05050; font-size:10px; font-weight:bold;")
            info.addWidget(fail_lbl)

        if item.get("notes"):
            notes_lbl = QLabel(f"📝 {item['notes']}")
            notes_lbl.setWordWrap(True)
            notes_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(notes_lbl)

        # History
        history = db.get_task_last_history(self.user_id, self.mode, item["id"])
        if history:
            action = history["action"]
            date_str = history["action_date"]
            emoji = "✅" if action == "success" else "❌" if action == "fail" else "⏭️"
            color = "#80c000" if action == "success" else "#e05050" if action == "fail" else "#f0a800"
            status_label = QLabel(tr("task_status_history", emoji=emoji, date=date_str))
            status_label.setStyleSheet(f"color:{color}; font-size:10px;")
            info.addWidget(status_label)
        else:
            status_label = QLabel(tr("task_status_never"))
            status_label.setStyleSheet(f"color:{_T('muted')}; font-size:10px;")
            info.addWidget(status_label)

        row.addLayout(info, 1)

        # Tombol aksi (sama seperti sebelumnya, tapi sekarang tidak dibungkus DraggableCard)
        if self.mode == "habit":
            ck = _btn(tr("task_btn_done") if done else tr("task_btn_check"), h=36)
            ck.setEnabled(not done)
            if done:
                ck.setStyleSheet(f"background:{_T('border')}; color:{_T('muted')}; border-color:{_T('border')};")
            ck.setMinimumWidth(92)
            ck.clicked.connect(lambda _, i=item["id"]: self._do("up", i))
            row.addWidget(ck)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setMinimumWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        elif self.mode == "daily":
            ck = _btn(tr("task_btn_done") if done else tr("task_btn_check"), h=36)
            ck.setEnabled(not done)
            if done:
                ck.setStyleSheet(f"background:{_T('border')}; color:{_T('muted')}; border-color:{_T('border')};")
            ck.setMinimumWidth(92)
            ck.clicked.connect(lambda _, i=item["id"]: self._do_daily(i))
            row.addWidget(ck)

            # ── Tombol Freeze ──
            freeze_btn = _btn("🧊 Freeze", h=36)
            freeze_btn.setMinimumWidth(70)
            freeze_btn.clicked.connect(lambda _, i=item["id"]: self._add_freeze(i))
            row.addWidget(freeze_btn)

            nb = _btn(tr("task_btn_fail"), "danger", h=36)
            nb.setEnabled(not done)
            if done:
                nb.setStyleSheet(f"background:{_T('border')}; color:{_T('muted')}; border-color:{_T('border')};")
            nb.setMinimumWidth(82)
            nb.clicked.connect(lambda _, i=item["id"]: self._fail_daily(i))
            row.addWidget(nb)

            # Tampilkan freeze slots
            freeze_slots = item.get("freeze_slots", 0)
            freeze_label = QLabel(f"🧊 Freeze: {freeze_slots}/3")
            freeze_label.setStyleSheet(f"color:{_T('accent')}; font-size:10px; font-weight:bold;")
            info.addWidget(freeze_label)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setMinimumWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        else:  # todo
            cb = QCheckBox()
            cb.setChecked(done)
            cb.setEnabled(not done)
            cb.stateChanged.connect(lambda _, i=item["id"]: self._do_todo(i))
            row.addWidget(cb)

            edit_btn = _btn("✏️", h=36)
            edit_btn.setMinimumWidth(36)
            edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
            row.addWidget(edit_btn)

        # Tombol hapus, duplikat, folder
        dl = _btn(tr("task_btn_delete"), "danger", h=36)
        dl.setMinimumWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        dup_btn = _btn(tr("task_btn_duplicate"), h=36)
        dup_btn.setMinimumWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn(tr("task_btn_folder"), h=36)
        folder_btn.setMinimumWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"):
                                self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)

        up_btn = _btn("⬆", h=36)
        up_btn.setMinimumWidth(36)
        up_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "up"))
        row.addWidget(up_btn)

        down_btn = _btn("⬇", h=36)
        down_btn.setMinimumWidth(36)
        down_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "down"))
        row.addWidget(down_btn)

        return content

    def _create_card_widget(self, item: dict) -> DraggableCard:
        """Bungkus konten dengan DraggableCard dan simpan referensi"""
        content = self._build_card_content(item)
        card = DraggableCard(
            item_id=item["id"],
            mode=self.mode,
            user_id=self.user_id,
            current_folder_id=item.get("folder_id"),
            content_widget=content,
            parent=self
        )
        self.card_widgets[item["id"]] = card
        return card

    # ========== AKSI LAINNYA (sama seperti sebelumnya) ==========
    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, self.mode)
        folder_names = [tr("dialog_no_folder")] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dialog_move_folder"))
        dlg.setMinimumSize(300, 200)
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
        btn_ok = _btn(tr("dialog_move"), "solid", dlg.accept)
        layout.addWidget(QLabel(tr("dialog_select_folder")))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.set_item_folder(self.user_id, self.mode, item_id, selected_id)
            QTimer.singleShot(0, self.load)
            SND.notify()

    def _do(self, direction: str, iid: int):
        r = db.complete_habit(self.user_id, iid, direction)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, tr("msg_info"), r["msg"])
            return
        if direction == "up":
            SND.complete()
            msg = tr("habit_complete_msg", xp=r.get('xp_gained',0), gold=r.get('gold_gained',0))
            if r.get("leveled_up"):
                SND.level_up()
                msg += f"\n🎉 {tr('level_up_msg', lvl=r['new_level'])}"
            _show(self, tr("task_habit_success"), msg, "success")
        else:
            SND.error()
            lost_hp = r.get("lost_hp", 5)
            _show(self, tr("task_hp_loss"), f"💔 -{lost_hp:.0f} HP " + tr("task_bad_habit"), "warning")
        AppState.refresh()
        self._update_item(iid)

    def _do_daily(self, iid: int):
        r = db.complete_daily(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, tr("msg_info"), r["msg"])
            return
        SND.complete()
        msg = tr("daily_complete_msg", xp=r.get('xp_gained',0))
        if r.get("leveled_up"):
            SND.level_up()
            msg += f"\n🎉 {tr('level_up_msg', lvl=r['new_level'])}"
        _show(self, tr("task_daily_success"), msg, "success")
        AppState.refresh()
        self._update_item(iid)

    def _fail_daily(self, iid: int):
        r = db.fail_daily(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, tr("msg_info"), r["msg"])
            return

        if r.get("freeze_used"):
            SND.notify()
            _show(self, tr("task_daily_freeze_title"), r["msg"], "success")
            AppState.refresh()
            self._update_item(iid)
            return

        penalty_type = r.get("penalty_type", "hp")
        penalty_amount = r.get("penalty_amount", 0)
        lost_hp = r.get("lost_hp", 0)

        if penalty_type == "hp":
            msg = tr("task_daily_fail", hp=lost_hp)
        elif penalty_type == "gold":
            msg = tr("penalty_gold_popup", gold=penalty_amount)
        elif penalty_type == "xp":
            msg = tr("penalty_xp_popup_percent", xp=penalty_amount, new_level=r.get("new_level", 1))
        else:
            msg = tr("penalty_none_popup")

        SND.error()
        _show(self, tr("task_daily_fail_title"), msg, "warning")
        AppState.refresh()
        self._update_item(iid)

    def _add_freeze(self, daily_id):
        loading = LoadingDialog(tr("proces_freeze"), self)
        loading.show()
        QApplication.processEvents()
        r = db.add_freeze_to_daily(self.user_id, daily_id)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()
        self._update_item(daily_id)

    def _do_todo(self, iid: int):
        r = db.complete_todo(self.user_id, iid)
        if not r.get("ok"):
            return
        SND.complete()
        msg = tr("quest_complete_msg", text=tr('task_quest_complete'), xp=r.get('xp_gained',0))
        if r.get("leveled_up"):
            SND.level_up()
            msg += f"\n🎉 {tr('level_up_msg', lvl=r['new_level'])}"
        _show(self, tr("task_quest_success"), msg, "success")
        AppState.refresh()
        self._update_item(iid)

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

    def _reorder(self, item_id, direction):
        # Tentukan status berdasarkan mode
        status = None
        items = self._get_items()
        item = next((i for i in items if i["id"] == item_id), None)
        if item:
            if self.mode == "todo":
                status = item.get("done", 0)
            elif self.mode in ("habit", "daily", "sport"):
                status = item.get("done_today", 0)

        # Balik arah untuk mode yang menggunakan sort_order DESC di tampilan
        actual_direction = direction
        if self.mode in ("todo", "habit", "daily", "sport"):
            actual_direction = "down" if direction == "up" else "up"

        r = db.reorder_item(self.user_id, self.mode, item_id, actual_direction, status)
        if r.get("ok"):
            if r.get("moved", False):
                SND.click()
                QTimer.singleShot(0, self.load)
            # else tidak ada perubahan, tidak perlu reload
        else:
            SND.error()
            _show(self, tr("msg_error"), r.get("msg", "Gagal mengubah urutan"), "error")

    def closeEvent(self, e):
        AppState.unregister(self.load)
        AppState.unregister_lang_cb(self.load)
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
            tr("sport_edit_title") if item else tr("sport_add_title"))
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
        lay.addWidget(_lbl(tr("sport_activity_name"), size=12))
        self._name = _input(tr("sport_activity_ph"))
        if self.item:
            self._name.setText(self.item["name"])
        lay.addWidget(self._name)

        # Jenis olahraga
        lay.addWidget(_lbl(tr("sport_type_label"), size=12))
        sport_opts = [
            (f"{v['icon']}  {tr('sport_type_' + k)}", k)
            for k, v in db.SPORT_TYPES.items()
        ]   
        self._sport_type = _combo(sport_opts)
        if self.item:
            idx = self._sport_type.findData(self.item.get("sport_type","running"))
            if idx >= 0: self._sport_type.setCurrentIndex(idx)
        lay.addWidget(self._sport_type)

        # Intensitas
        lay.addWidget(_lbl(tr("sport_intensity"), size=12))
        diff_opts = [
            (tr("sport_intensity_easy"), "easy"),
            (tr("sport_intensity_medium"), "medium"),
            (tr("sport_intensity_hard"), "hard"),
            (tr("sport_intensity_epic"), "epic"),
        ]
        self._diff = _combo(diff_opts)
        if self.item:
            idx = self._diff.findData(self.item.get("difficulty","medium"))
            if idx >= 0: self._diff.setCurrentIndex(idx)
        else:
            self._diff.setCurrentIndex(1)   # medium default
        lay.addWidget(self._diff)

        # Kalori terbakar
        lay.addWidget(_lbl(tr("sport_calories_label"), size=12))
        self.calories_burned = QSpinBox()
        self.calories_burned.setRange(0, 2000)
        self.calories_burned.setSuffix(tr("unit_kcal"))
        self.calories_burned.setValue(100)
        lay.addWidget(self.calories_burned)

        # Durasi (menit)
        lay.addWidget(_lbl(tr("sport_duration"), size=12))
        self.duration = QSpinBox()
        self.duration.setRange(1, 480)
        self.duration.setSuffix(tr("unit_minutes"))
        self.duration.setValue(30)
        lay.addWidget(self.duration)

        # Catatan
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder"))
        if self.item:
            self._notes.setText(self.item.get("notes", ""))
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl(tr("dialog_folder"), size=12))
        _folders = db.get_task_folders(self.user_id, "sport")
        _fopts = [(tr("dialog_no_folder"), None)] + [
            (f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        if self.item:
            cur_fid = self.item.get("folder_id")
            if cur_fid:
                idx = next((i for i,(_, d) in enumerate(_fopts) if d == cur_fid), 0)
                self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok_lbl = tr("dialog_save") if self.item else tr("dialog_add")
        ok = _btn(ok_lbl, "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        root.addWidget(_scrolled(content))

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("msg_name_empty"), "error")
            return
        sport_type = self._sport_type.currentData()
        diff = self._diff.currentData()
        notes = self._notes.text()
        icon = db.SPORT_TYPES.get(sport_type, {}).get("icon", "🏅")
        calories_burned = self.calories_burned.value()
        duration = self.duration.value()
        folder_id = self._folder.currentData()
        
        if self.item:
            db.update_sport_activity(
                self.item["id"], self.user_id,
                name=name, sport_type=sport_type, icon=icon,
                difficulty=diff, notes=notes,
                calories_burned=calories_burned, duration_minutes=duration
            )
            db.set_item_folder(self.user_id, "sport", self.item["id"], folder_id)
        else:
            db.add_sport_activity(
                self.user_id, name, sport_type, icon, diff, notes,
                calories_burned=calories_burned, duration_minutes=duration
            )
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
        self.card_widgets = {}
        self.mode = "sport"
        self._build()
        AppState.register(self.load)

    # ── build UI ──────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("sport_title"), "section", 14, True))
        hdr.addStretch()
        folder_btn = _btn(tr("task_folder_button"), h=36)
        folder_btn.setMinimumWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add_btn = _btn(tr("task_add_button"), "solid", self._open_add)
        add_btn.setMinimumWidth(130)
        hdr.addWidget(add_btn)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Sport Level bar
        lvl_row = QHBoxLayout()
        self._sport_lvl_lbl = QLabel(tr("sport_level_default"))
        self._sport_lvl_lbl.setStyleSheet(
            "color:#f0a800; font-weight:bold; font-size:13px;")
        self._sport_xp_bar = QProgressBar()
        self._sport_xp_bar.setMinimumHeight(12)
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
        self._tabs.addTab(_scrolled(self._inner_all), tr("sport_tab_all"))

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
                            f"{sport['icon']} {tr('sport_type_' + key)}")

        # ── Baris filter (search + difficulty) ──
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("task_search"))
        self.search_input.textChanged.connect(self.load)
        self.filter_combo = QComboBox()
        self.filter_combo.addItem(tr("sport_filter_all"), "all")
        self.filter_combo.addItem(tr("sport_difficulty_easy"), "easy")
        self.filter_combo.addItem(tr("sport_difficulty_medium"), "medium")
        self.filter_combo.addItem(tr("sport_difficulty_hard"), "hard")
        self.filter_combo.addItem(tr("sport_difficulty_epic"), "epic")
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
                empty_lbl = QLabel("   📭  " + tr("folder_empty"))
                empty_lbl.setStyleSheet(
                    f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards_in_folder:
                    fw.add_card(self._create_card_widget(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        for item in ungrouped:
            lay.insertWidget(insert_pos, self._create_card_widget(item))
            insert_pos += 1

        # ── Drop area untuk "Tanpa Folder" ──
        drop_area = QFrame()
        drop_area.setAcceptDrops(True)
        drop_area.setMinimumHeight(50)
        drop_area.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T('border')};
                border-radius: 8px;
                background: {_T('bg')};
                margin-top: 8px;
            }}
            QFrame:hover {{
                border-color: {_T('accent')};
                background: {_T('panel')};
            }}
        """)
        drop_label = QLabel(tr("drop_here_to_remove_folder"))
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        drop_area_layout = QVBoxLayout(drop_area)
        drop_area_layout.addWidget(drop_label)

        def _drag_enter(e):
            if e.mimeData().hasFormat("application/x-craftlife-card"):
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dragEnterEvent = _drag_enter

        def _drop(e):
            raw = e.mimeData().data("application/x-craftlife-card")
            info = json.loads(raw.data().decode())
            if info["mode"] == self.mode and info["user_id"] == self.user_id:
                db.set_item_folder(self.user_id, self.mode, info["item_id"], None)
                self.load()
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dropEvent = _drop

        lay.insertWidget(insert_pos, drop_area)

    def _update_item(self, item_id: int):
        activities = db.get_sport_activities(self.user_id)
        item = next((a for a in activities if a['id'] == item_id), None)
        if not item:
            self.load()
            return

        card = self.card_widgets.get(item_id)
        if not card:
            self.load()
            return

        while card.layout().count():
            child = card.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        new_content = self._build_card_content(item)
        card.layout().addWidget(new_content)
        card.current_folder_id = item.get('folder_id')
        AppState.refresh()

    # ── load / refresh ────────────────────────────────────────────────────────
    def load(self):
        self.card_widgets.clear()
        if not AppState.user_id:
            return
        db.reset_daily_tasks(self.user_id)

        # Update sport level bar
        u = AppState.user()
        sport_lvl = u.get("sport_level", 1) or 1
        sport_xp  = u.get("sport_xp", 0)  or 0
        needed    = sport_lvl * 100
        self._sport_lvl_lbl.setText(
            tr("sport_level", lvl=sport_lvl, xp=sport_xp, need=needed))
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
        filter_diff = self.filter_combo.currentData()
        if search:
            activities = [a for a in activities if search in a["name"].lower()]
        if filter_diff != "all":
            activities = [a for a in activities if a.get("difficulty", "").lower() == filter_diff]

        # ── Tab "Semua" ───────────────────────────────────────────────────────
        self._render_sport_to_layout(
            self._lay_all, self._inner_all, activities, folders,
            tr("sport_empty"))

        # ── Tab per jenis ─────────────────────────────────────────────────────
        by_sport: dict = {}
        for a in activities:
            by_sport.setdefault(a["sport_type"], []).append(a)

        for key, lay in self._sport_lays.items():
            sport_nm = tr("sport_type_" + key)
            self._render_sport_to_layout(
                lay, self._sport_inners[key], by_sport.get(key, []), folders,
                tr("sport_no_activity", sport_nm=sport_nm))

    # ── card builder ──────────────────────────────────────────────────────────
    def _build_card_content(self, item: dict) -> QWidget:
        done = bool(item.get("done_today", False))

        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        sport_data = db.SPORT_TYPES.get(item["sport_type"], {"icon": "🏅"})
        ico = QLabel(item.get("icon") or sport_data["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setMinimumWidth(38)
        row.addWidget(ico)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_style = (f"text-decoration:line-through; color:{_T('muted')};"
                    if done else f"color:{_T('text')}; font-weight:bold;")
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; {name_style}")
        info.addWidget(nm)

        sport_nm = tr("sport_type_" + item["sport_type"])
        streak_txt = (tr("task_streak_days", streak=item['streak'])
                    if item.get("streak", 0) > 0 else "")
        sub = QLabel(tr("sport_reward_format", sport=sport_nm, xp=item['xp_reward'],
                        gold=item['gold_reward'], sp=item['sport_points_reward'], streak=streak_txt))
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        if item.get("notes"):
            nl = QLabel(f"📝 {item['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        history = db.get_task_last_history(self.user_id, "sport", item["id"])
        if history:
            date_str = history["action_date"]
            emoji = "✅" if history["action"] == "success" else "❌" if history["action"] == "fail" else "⏭️"
            color = "#80c000" if history["action"] == "success" else "#e05050" if history["action"] == "fail" else "#f0a800"
            status_label = QLabel(tr("task_status_history", emoji=emoji, date=date_str))
            status_label.setStyleSheet(f"color:{color}; font-size:10px;")
            info.addWidget(status_label)
        else:
            status_label = QLabel(tr("task_status_never"))
            status_label.setStyleSheet(f"color:{_T('muted')}; font-size:10px;")
            info.addWidget(status_label)

        row.addLayout(info, 1)

        ck = _btn(tr("sport_btn_done") if done else tr("sport_btn_complete"), h=36)
        ck.setEnabled(not done)
        if done:
            ck.setStyleSheet(f"background:{_T('border')}; color:{_T('muted')}; border-color:{_T('border')};")
        ck.setMinimumWidth(100)
        ck.clicked.connect(lambda _, i=item["id"]: self._complete(i))
        row.addWidget(ck)

        edit_btn = _btn("✏️", h=36)
        edit_btn.setMinimumWidth(36)
        edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
        row.addWidget(edit_btn)

        dl = _btn("🗑", "danger", h=36)
        dl.setMinimumWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        dup_btn = _btn("📋", h=36)
        dup_btn.setMinimumWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn("📁", h=36)
        folder_btn.setMinimumWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"): self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)

        up_btn = _btn("⬆", h=36)
        up_btn.setMinimumWidth(36)
        up_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "up"))
        row.addWidget(up_btn)

        down_btn = _btn("⬇", h=36)
        down_btn.setMinimumWidth(36)
        down_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "down"))
        row.addWidget(down_btn)

        return content

    def _create_card_widget(self, item: dict) -> DraggableCard:
        content = self._build_card_content(item)
        card = DraggableCard(
            item_id=item["id"],
            mode="sport",
            user_id=self.user_id,
            current_folder_id=item.get("folder_id"),
            content_widget=content,
            parent=self
        )
        self.card_widgets[item["id"]] = card
        return card

    # ── actions ───────────────────────────────────────────────────────────────

    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, "sport")   # ✅
        folder_names = [tr("folder_no_folder")] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]

        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dialog_move_folder"))
        dlg.setMinimumSize(300, 200)
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
        btn_ok = _btn(tr("dialog_move"), "solid", dlg.accept)
        layout.addWidget(QLabel(tr("dialog_select_folder")))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.set_item_folder(self.user_id, "sport", item_id, selected_id)
            QTimer.singleShot(0, self.load)
            SND.notify()

    def _complete(self, iid: int):
        r = db.complete_sport_activity(self.user_id, iid)
        if not r.get("ok", True) and r.get("msg"):
            _show(self, tr("info_title"), r["msg"])
            return
        SND.complete()
        msg = tr("sport_complete_message",
        xp=r.get('xp_gained', 0),
        gold=r.get('gold_gained', 0),
        sp=r.get('sport_points_gained', 0))
        if r.get("leveled_up"):
            msg += tr("level_up_sport", lvl=r['new_level'])
        if r.get("sport_leveled_up"):
            msg += tr("sport_level_up", lvl=r['new_sport_level'])
        _show(self, tr("sport_complete_title"), msg, "success")
        AppState.refresh()
        self._update_item(iid)

    def _edit(self, iid: int):
        activities = db.get_sport_activities(self.user_id)
        item = next((a for a in activities if a["id"] == iid), None)
        if not item:
            return
        dlg = AddSportActivityDialog(self.user_id, item, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _delete(self, iid: int):
        db.delete_sport_activity(self.user_id, iid)
        SND.click()
        QTimer.singleShot(0, self.load)

    def _duplicate(self, activity_id):
        r = db.duplicate_sport_activity(self.user_id, activity_id)
        if r["ok"]:
             SND.click()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)

    def _open_add(self):
        dlg = AddSportActivityDialog(self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _open_folder_add(self):
        dlg = FolderDialog("sport", self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _reorder(self, item_id, direction):
        r = db.reorder_item(self.user_id, self.mode, item_id, direction)
        if r.get("ok"):
            if r.get("moved", False):
                SND.click()
                QTimer.singleShot(0, self.load)
            # else tidak ada perubahan, tidak perlu reload
        else:
            SND.error()
            _show(self, tr("msg_error"), r.get("msg", "Gagal mengubah urutan"), "error")

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
        self.item = item
        self.setWindowTitle(tr("economy_transaction_title_edit") if item else tr("economy_transaction_title_add"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setMaximumHeight(700)
        self.setStyleSheet(build_ss())
        self._build()
        # Jika edit, konversi amount dari IDR ke mata uang user
        if self.item:
            user_curr = db.get_user_currency(self.user_id)
            amount_idr = self.item['amount']
            amount_usr = db.convert_from_idr(amount_idr, user_curr)
            self._amount.setText(f"{amount_usr:.2f}")

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

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
        lay.addWidget(_lbl(tr("economy_transaction_name"), size=12))
        self._name = _input(tr("economy_transaction_name_ph"))
        if self.item:
            self._name.setText(self.item["name"])
        lay.addWidget(self._name)

        # Icon (pilihan singkat)
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        icon_choices = [
            (tr("economy_icon_income"), "💰"),
            (tr("economy_icon_expense"), "💸"),
            (tr("economy_icon_salary"), "🏦"),
            (tr("economy_icon_food"), "🍔"),
            (tr("economy_icon_transport"), "🚗"),
            (tr("economy_icon_rent"), "🏠"),
            (tr("economy_icon_education"), "📚"),
            (tr("economy_icon_health"), "💊"),
            (tr("economy_icon_entertainment"), "🎮"),
            (tr("economy_icon_investment"), "📈"),
            (tr("economy_icon_gift"), "🎁"),
            (tr("economy_icon_shopping"), "🛒")
        ]
        self._icon = _combo(icon_choices)
        if self.item:
            idx = self._icon.findData(self.item.get("icon", "💰"))
            if idx >= 0:
                self._icon.setCurrentIndex(idx)
        lay.addWidget(self._icon)

        # Tipe (income/expense)
        lay.addWidget(_lbl(tr("economy_transaction_type"), size=12))
        self._type = _combo([(tr("economy_type_income"), "income"), (tr("economy_type_expense"), "expense")])
        if self.item:
            idx = self._type.findData(self.item.get("type", "expense"))
            if idx >= 0:
                self._type.setCurrentIndex(idx)
        lay.addWidget(self._type)

        # Jumlah
        lay.addWidget(_lbl(tr("economy_amount_label", symbol=self.currency_symbol()), size=12))
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0")
        self._amount.setMinimumHeight(42)
        if self.item:
            self._amount.setText(str(self.item["amount"]))
        lay.addWidget(self._amount)

        # Kategori (bisa custom atau pilih dari yang sudah ada)
        lay.addWidget(_lbl(tr("economy_category"), size=12))
        self._category = QLineEdit()
        self._category.setPlaceholderText(tr("economy_category_ph"))
        if self.item:
            self._category.setText(self.item["category"])
        # Tambahkan label penjelasan
        cat_hint = QLabel(tr("economy_category_hint"))
        cat_hint.setStyleSheet(f"color:{_T('muted')}; font-size:10px; font-style:italic;")
        lay.addWidget(self._category)
        lay.addWidget(cat_hint)
        # Saran kategori dari DB
        self._suggest_cat = QComboBox()
        self._suggest_cat.setMinimumHeight(36)
        self._suggest_cat.addItem(tr("economy_category_suggest"), None)
        try:
            cats = db.get_economy_categories(self.user_id)
            for cat in cats:
                self._suggest_cat.addItem(cat, cat)
            self._suggest_cat.currentIndexChanged.connect(self._on_suggest)
        except:
            pass
        lay.addWidget(self._suggest_cat)

        # Tanggal
        lay.addWidget(_lbl(tr("economy_date_label"), size=12))
        self._date = QLineEdit()
        self._date.setPlaceholderText("YYYY-MM-DD")
        if self.item:
            self._date.setText(self.item["date"])
        else:
            from datetime import date
            self._date.setText(date.today().isoformat())
        self._date.setMinimumHeight(42)
        lay.addWidget(self._date)

        # Catatan
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder"))
        if self.item:
            self._notes.setText(self.item.get("notes", ""))
        lay.addWidget(self._notes)

        # Folder
        lay.addWidget(_lbl(tr("economy_folder_label"), size=12))
        _folders = db.get_task_folders(self.user_id, "economy")
        _fopts = [(tr("dialog_no_folder"), None)] + [(f"{fd['icon']}  {fd['name']}", fd["id"]) for fd in _folders]
        self._folder = _combo(_fopts)
        if self.item and self.item.get("folder_id"):
            cur_fid = self.item["folder_id"]
            idx = next((i for i, (_, d) in enumerate(_fopts) if d == cur_fid), 0)
            self._folder.setCurrentIndex(idx)
        lay.addWidget(self._folder)

        lay.addSpacing(8)
        ok_lbl = tr("dialog_save") if self.item else tr("dialog_add")
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
            _show(self, tr("msg_error"), tr("msg_name_empty"), "error")
            return
        
        # Ambil jumlah dalam mata uang user
        try:
            amount_user = float(self._amount.text().strip())
            if amount_user <= 0:
                raise ValueError
        except:
            _show(self, tr("msg_error"), tr("msg_invalid_amount"), "error")
            return
        
        # Konversi ke IDR untuk disimpan
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        
        icon = self._icon.currentData()
        type_ = self._type.currentData()
        cat = self._category.text().strip()
        if not cat:
            cat = "other"
        date_str = self._date.text().strip()
        if not date_str:
            from datetime import date
            date_str = date.today().isoformat()
        notes = self._notes.text()
        folder_id = self._folder.currentData()
        
        if self.item:
            db.update_economy_item(self.item["id"], self.user_id,
                                name=name, icon=icon, type=type_, amount=amount_idr,
                                category=cat, date=date_str, notes=notes, folder_id=folder_id)
        else:
            db.add_economy_item(self.user_id, name, icon, type_, amount_idr, cat, date_str, notes, folder_id)
        
        SND.complete()
        self.accept()


class EconomyPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        
        self.user_id = user_id
        self.mode = "economy"
        self.currency = "IDR"
        self.currency_symbol = "Rp"
        self.card_widgets = {}
        self._load_currency_settings()
        self._build()
        AppState.register(self.load)

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("economy_title"), "section", 14, True))
        hdr.addStretch()
        folder_btn = _btn(tr("economy_folder"), h=36)
        folder_btn.setMinimumWidth(110)
        folder_btn.clicked.connect(self._open_folder_add)
        hdr.addWidget(folder_btn)
        add_btn = _btn(tr("economy_add"), "solid", self._open_add)
        add_btn.setMinimumWidth(130)
        hdr.addWidget(add_btn)
        debt_add_btn = _btn(tr("economy_add_debt"), "gold", self._add_debt)
        debt_add_btn.setMinimumWidth(140)
        hdr.addWidget(debt_add_btn)
        saving_add_btn = _btn(tr("economy_add_saving"), "gold", self._add_saving)
        saving_add_btn.setMinimumWidth(150)
        hdr.addWidget(saving_add_btn)
        root.addLayout(hdr)
        root.addWidget(_sep())

        # Summary cards (total income, expense, balance)
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setSpacing(12)
        self.income_card = self._stat_card(tr("economy_total_income"), "0", "#80c000")
        self.income_card.setToolTip(tr("economy_tooltip_income"))
        self.expense_card = self._stat_card(tr("economy_total_expense"), "0", "#e05050")
        self.expense_card.setToolTip(tr("economy_tooltip_expense"))
        self.balance_card = self._stat_card(tr("economy_balance"), "0", "#4da6ff")
        self.balance_card.setToolTip(tr("economy_tooltip_balance"))
        self.debt_label = QLabel()
        self.net_worth_label = QLabel()
        summary_layout.addWidget(self.income_card)
        summary_layout.addWidget(self.expense_card)
        summary_layout.addWidget(self.balance_card)
        # Baris info hutang & tabungan
        info_row = QWidget()
        info_layout = QHBoxLayout(info_row)
        info_layout.setContentsMargins(0, 8, 0, 0)
        info_layout.setSpacing(20)

        self.debt_label = QLabel(tr("economy_total_debt", amount="0"))
        self.debt_label.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")
        self.saving_label = QLabel(tr("economy_total_saving", amount="0"))
        self.saving_label.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")

        info_layout.addWidget(self.debt_label)
        info_layout.addStretch()
        info_layout.addWidget(self.saving_label)

        root.addWidget(info_row)
        root.addWidget(summary_widget)

        # Filter bar
        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("economy_search"))
        self.search_input.textChanged.connect(self.load)
        self.type_combo = QComboBox()
        self.type_combo.addItem(tr("economy_filter_all"), None)
        self.type_combo.addItem(tr("economy_filter_income"), "income")
        self.type_combo.addItem(tr("economy_filter_expense"), "expense")
        self.type_combo.currentTextChanged.connect(self.load)
        self.category_combo = QComboBox()
        self.category_combo.addItem(tr("economy_all_categories"), "all")
        self.category_combo.setToolTip(tr("economy_tooltip_category"))
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
        self._tabs.addTab(_scrolled(self._inner_all), tr("economy_tab_all"))

        self._inner_debt = QWidget()
        self._lay_debt = QVBoxLayout(self._inner_debt)
        self._lay_debt.setSpacing(8)
        self._lay_debt.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._tabs.addTab(_scrolled(self._inner_debt), tr("economy_tab_debt"))

        self._inner_saving = QWidget()
        self._lay_saving = QVBoxLayout(self._inner_saving)
        self._lay_saving.setSpacing(8)
        self._lay_saving.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._tabs.addTab(_scrolled(self._inner_saving), tr("economy_tab_saving"))

        self._inner_invest = QWidget()
        self._lay_invest = QVBoxLayout(self._inner_invest)
        self._lay_invest.setSpacing(8)
        self._lay_invest.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._tabs.addTab(_scrolled(self._inner_invest), tr("economy_tab_invest"))

        self._inner_subscription = QWidget()
        self._lay_subscription = QVBoxLayout(self._inner_subscription)
        self._lay_subscription.setSpacing(8)
        self._lay_subscription.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._tabs.addTab(_scrolled(self._inner_subscription), tr("economy_tab_subscription"))

        self._cat_lays = {}
        self._cat_inners = {}
        root.addWidget(self._tabs, 1)
        self.load()

    def _create_card_widget(self, item: dict) -> DraggableCard:
        card = self._make_card(item)
        self.card_widgets[item["id"]] = card
        return card

    def _add_investment(self):
        dlg = AddInvestmentDialog(self.user_id, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _collect_return(self, invest_id):
        from PyQt6.QtWidgets import QInputDialog
        dlg = QInputDialog(self)
        dlg.setWindowTitle(tr("economy_invest_return_title"))
        dlg.setLabelText(tr("economy_invest_return_label", symbol=self.currency_symbol))
        dlg.setDoubleDecimals(0)
        dlg.setDoubleRange(0, 1e9)
        dlg.setDoubleValue(0)
        if dlg.exec():
            amount_user = dlg.doubleValue()
            if amount_user > 0:
                user_currency = db.get_user_currency(self.user_id)
                amount_idr = db.convert_to_idr(amount_user, user_currency)
                r = db.add_investment_return(invest_id, self.user_id, amount_idr)
                if r["ok"]:
                    SND.complete()
                    symbol = self.currency_symbol
                    _show(self, tr("return_title"),
                        tr("investment_return_detail", amount=f"{symbol}{amount_user:.0f}", total=self.format_currency(r['new_amount'])),
                        "success")
                else:
                    SND.error()
                    _show(self, tr("gagal_title"), r["msg"], "error")
                QTimer.singleShot(0, self.load)

    def _withdraw_investment(self, invest_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("economy_invest_withdraw_confirm"),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            r = db.withdraw_investment(invest_id, self.user_id)
            if r["ok"]:
                SND.complete()
                amount_usr = self.convert_from_idr(r['amount'])
                _show(self, tr("berhasil_title"), tr("berhasil_invest_withdraw", symbol=self.currency_symbol, amount=amount_usr), "success")
                AppState.refresh()
            else:
                SND.error()
                _show(self, tr("gagal_title"), r["msg"], "error")
            QTimer.singleShot(0, self.load)


    def _delete_investment(self, invest_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("economy_invest_delete_confirm"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_investment(invest_id, self.user_id)
            SND.click()
            QTimer.singleShot(0, self.load)

    def _add_subscription(self):
        dlg = AddSubscriptionDialog(self.user_id, parent=self)   
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _renew_subscription(self, sub_id):
        # Renew manual (pengguna klik)
        r = db.renew_subscription(sub_id, self.user_id, auto_pay=False)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)
        AppState.refresh()

    def _edit_subscription(self, sub):
        dlg = AddSubscriptionDialog(self.user_id, sub, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _delete_subscription(self, sub_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("economy_sub_delete_confirm"),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_subscription(sub_id, self.user_id)
            SND.click()
            QTimer.singleShot(0, self.load)

    def _make_investment_card(self, inv: dict) -> QFrame:
        f = _card()
        row = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        icon = QLabel(inv["icon"])
        icon.setFont(QFont("Segoe UI", 22))
        icon.setMinimumWidth(38)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(inv["name"])
        name.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(name)

        amount = QLabel(self.format_currency(inv["amount"]))
        amount.setStyleSheet(f"color:{_T('accent')}; font-size:13px;")
        info.addWidget(amount)

        date_str = tr("economy_invest_date_label", date=inv['invested_date'][:10])
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        info.addWidget(date_lbl)

        if inv.get("notes"):
            note = QLabel(f"📝 {inv['notes']}")
            note.setWordWrap(True)
            note.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(note)

        row.addLayout(info, 1)

        collect_btn = _btn(tr("economy_invest_collect"), "solid", h=36)
        collect_btn.clicked.connect(lambda _, iid=inv["id"]: self._collect_return(iid))
        row.addWidget(collect_btn)

        withdraw_btn = _btn(tr("economy_invest_withdraw_btn"), "diamond", h=36)
        withdraw_btn.clicked.connect(lambda _, iid=inv["id"]: self._withdraw_investment(iid))
        row.addWidget(withdraw_btn)

        del_btn = _btn("🗑", "danger", h=36)
        del_btn.clicked.connect(lambda _, iid=inv["id"]: self._delete_investment(iid))
        row.addWidget(del_btn)

        return f

    def _make_subscription_card(self, sub: dict) -> QFrame:
        f = _card()
        today = date.today().isoformat()
        overdue = sub["due_date"] < today

        if overdue:
            f.setStyleSheet(
                f"QFrame#card {{ background: {_T('panel')}; "
                f"border: 2px solid #e05050; border-left: 6px solid #e05050; "
                f"border-radius: 8px; }}"
            )
        else:
            f.setStyleSheet(f"QFrame#card {{ background: {_T('panel')}; "
                            f"border: 1px solid {_T('border')}; border-radius: 8px; }}")

        row = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        icon = QLabel(sub["icon"])
        icon.setFont(QFont("Segoe UI", 22))
        icon.setMinimumWidth(38)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(sub["name"])
        name.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(name)

        amount = QLabel(tr("subscription_amount_period", amount=self.format_currency(sub['amount']), period=sub['period']))
        amount.setStyleSheet(f"color:{_T('accent')}; font-size:12px;")
        info.addWidget(amount)

        due = tr("economy_sub_due_format", date=sub['due_date'])
        due_lbl = QLabel(due)
        due_lbl.setStyleSheet(f"color:{'#e05050' if overdue else _T('muted')}; font-size:11px;")
        info.addWidget(due_lbl)

        if sub.get("notes"):
            note = QLabel(f"📝 {sub['notes']}")
            note.setWordWrap(True)
            note.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(note)

        row.addLayout(info, 1)

        if overdue:
            renew_btn = _btn(tr("economy_sub_renew"), "gold", h=36)
            renew_btn.clicked.connect(lambda _, sid=sub["id"]: self._renew_subscription(sid))
            row.addWidget(renew_btn)

        edit_btn = _btn("✏️", h=36)
        edit_btn.clicked.connect(lambda _, s=sub: self._edit_subscription(s))
        row.addWidget(edit_btn)

        del_btn = _btn("🗑", "danger", h=36)
        del_btn.clicked.connect(lambda _, sid=sub["id"]: self._delete_subscription(sid))
        row.addWidget(del_btn)

        return f

    def _load_investments(self):
        # Bersihkan layout
        while self._lay_invest.count():
            item = self._lay_invest.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        investments = db.get_investments(self.user_id)
        if not investments:
            empty = QLabel(tr("economy_invest_empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            self._lay_invest.addWidget(empty)
        else:
            for inv in investments:
                card = self._make_investment_card(inv)
                self._lay_invest.addWidget(card)
        
        # Tombol tambah investasi
        add_btn = _btn(tr("economy_invest_add"), "gold", self._add_investment)
        add_btn.setMinimumHeight(40)
        self._lay_invest.addWidget(add_btn)

    def _load_subscriptions(self):
        while self._lay_subscription.count():
            item = self._lay_subscription.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Cek overdue & auto-renewal
        db.check_all_subscriptions(self.user_id)
        subs = db.get_subscriptions(self.user_id, active_only=True)
        if not subs:
            empty = QLabel(tr("economy_sub_empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            self._lay_subscription.addWidget(empty)
        else:
            for sub in subs:
                card = self._make_subscription_card(sub)
                self._lay_subscription.addWidget(card)
        
        add_btn = _btn(tr("economy_sub_add"), "gold", self._add_subscription)
        add_btn.setMinimumHeight(40)
        self._lay_subscription.addWidget(add_btn)

    def _add_saving(self):
        dlg = AddEditSavingDialog(self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _load_savings(self):
        # Bersihkan layout tabungan
        while self._lay_saving.count():
            item = self._lay_saving.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        savings = db.get_savings(self.user_id)
        if not savings:
            empty = QLabel(tr("economy_saving_empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            self._lay_saving.addWidget(empty)
        else:
            for saving in savings:
                card = self._make_saving_card(saving)
                self._lay_saving.addWidget(card)

    def _make_saving_card(self, saving: dict) -> QFrame:
        f = _card()
        row = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        icon = QLabel(saving["icon"])
        icon.setFont(QFont("Segoe UI", 22))
        icon.setMinimumWidth(38)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        nm = QLabel(saving["name"])
        nm.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(nm)

        target_text = ""
        if saving["target_amount"] > 0:
            percent = (saving["current_amount"] / saving["target_amount"]) * 100
            target_text = "  " + tr("saving_target_format", amount=self.format_currency(saving['target_amount']), percent=percent)
        if saving.get("target_date"):
            target_text += "  " + tr("saving_deadline_format", date=saving['target_date'])
        sub = QLabel(tr("saving_current_amount", amount=self.format_currency(saving['current_amount']), target_text=target_text))
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        if saving.get("notes"):
            nl = QLabel(f"📝 {saving['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        if saving["target_amount"] > 0:
            pb = QProgressBar()
            target = int(saving["target_amount"])
            if target > 2147483647:
                target = 2147483647
            pb.setMaximum(target)
            pb.setValue(int(saving["current_amount"]))
            pb.setMinimumHeight(10)
            pb.setTextVisible(False)
            info.addWidget(pb)

        row.addLayout(info, 1)

        add_btn = _btn(tr("dialog_add"), "gold", h=36)
        add_btn.setMinimumWidth(80)
        add_btn.clicked.connect(lambda _, sid=saving["id"], cur=saving["current_amount"]: self._add_to_saving(sid, cur))
        row.addWidget(add_btn)

        withdraw_btn = _btn(tr("economy_saving_withdraw_btn"), "diamond", h=36)
        withdraw_btn.setMinimumWidth(80)
        withdraw_btn.clicked.connect(lambda _, sid=saving["id"], name=saving["name"], cur=saving["current_amount"]: self._withdraw_from_saving(sid, name, cur))
        row.addWidget(withdraw_btn)

        edit_btn = _btn("✏️", h=36)
        edit_btn.setMinimumWidth(36)
        edit_btn.clicked.connect(lambda _, s=saving: self._edit_saving(s))
        row.addWidget(edit_btn)

        del_btn = _btn("🗑", "danger", h=36)
        del_btn.setMinimumWidth(36)
        del_btn.clicked.connect(lambda _, sid=saving["id"]: self._delete_saving(sid))
        row.addWidget(del_btn)

        return f

    def _add_to_saving(self, saving_id, current_amount_idr):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("economy_saving_add_funds"))
        dlg.setMinimumSize(350, 200)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(QLabel(tr("saving_balance_label", balance=self.format_currency(current_amount_idr))))
        layout.addWidget(QLabel(tr("saving_add_amount_label", symbol=self.currency_symbol)))
        
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 1_000_000_000)
        amount_spin.setValue(10000)
        amount_spin.setPrefix(f"{self.currency_symbol}: ")
        amount_spin.setMinimumHeight(42)
        layout.addWidget(amount_spin)

        btn = _btn(tr("economy_saving_add_confirm_btn"), "solid")
        btn.clicked.connect(lambda: self._process_add_to_saving(saving_id, amount_spin.value(), dlg))
        layout.addWidget(btn)
        
        dlg.exec()

    def _process_add_to_saving(self, saving_id, amount_user, dialog):
        if amount_user <= 0:
            _show(self, tr("msg_error"), tr("economy_amount_gt_zero"), "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        r = db.add_to_saving(saving_id, self.user_id, amount_idr)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), tr("berhasil_saving_add", symbol=self.currency_symbol, amount=amount_user), "success")
            dialog.accept()
            QTimer.singleShot(0, self.load)
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _edit_saving(self, saving):
        dlg = AddEditSavingDialog(self.user_id, saving, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _delete_saving(self, saving_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("economy_saving_delete_confirm"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_saving(saving_id, self.user_id)
            SND.click()
            QTimer.singleShot(0, self.load)

    def _withdraw_from_saving(self, saving_id, saving_name, current_amount_idr):
        """Dialog untuk menarik uang dari tabungan dengan konversi mata uang"""
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("economy_saving_withdraw_title", name=saving_name))
        dlg.setMinimumSize(400, 260)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        current_user = self.convert_from_idr(current_amount_idr)
        layout.addWidget(QLabel(tr("saving_withdraw_balance_label", symbol=self.currency_symbol, balance=current_user)))
        layout.addWidget(QLabel(tr("economy_saving_withdraw_label")))
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, current_user)
        amount_spin.setPrefix(f"{self.currency_symbol}: ")
        amount_spin.setValue(0)
        layout.addWidget(amount_spin)

        cb_income = QCheckBox(tr("economy_saving_withdraw_record"))
        cb_income.setChecked(True)
        layout.addWidget(cb_income)

        btn_ok = _btn(tr("economy_saving_withdraw_btn"), "solid")
        btn_ok.clicked.connect(lambda: self._do_withdraw(saving_id, amount_spin.value(), cb_income.isChecked(), dlg))
        layout.addWidget(btn_ok)
        dlg.exec()

    def _do_withdraw(self, saving_id, amount_user, add_to_income, dialog):
        if amount_user <= 0:
            _show(self, tr("msg_error"), tr("economy_amount_gt_zero"), "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        r = db.withdraw_from_saving(saving_id, self.user_id, amount_idr)
        if r["ok"]:
            SND.complete()
            if add_to_income:
                from datetime import date
                today = date.today().isoformat()
                db.add_economy_item(
                    self.user_id,
                    name="Penarikan Tabungan",
                    icon="🏦",
                    type_="income",
                    amount=amount_idr,
                    category="Tabungan",
                    date_str=today,
                    notes=f"Penarikan dari tabungan ID {saving_id}"
                )
                _show(self, tr("berhasil_title"), tr("berhasil_saving_withdraw", symbol=self.currency_symbol, amount=amount_user), "success")
            else:
                _show(self, tr("berhasil_title"), tr("berhasil_saving_withdraw2", symbol=self.currency_symbol, amount=amount_user), "success")
            dialog.accept()
            QTimer.singleShot(0, self.load)
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _stat_card(self, title, value, color):
        card = _card()
        card.setMinimumHeight(90)
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
                empty_lbl = QLabel("   📭  " + tr("folder_empty"))
                empty_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:12px; padding:6px 0;")
                fw.add_card(empty_lbl)
            else:
                for item in cards:
                    fw.add_card(self._create_card_widget(item))
            lay.insertWidget(insert_pos, fw)
            insert_pos += 1

        for item in ungrouped:
            lay.insertWidget(insert_pos, self._create_card_widget(item))
            insert_pos += 1

        # ── Drop area untuk "Tanpa Folder" ──
        drop_area = QFrame()
        drop_area.setAcceptDrops(True)
        drop_area.setMinimumHeight(50)
        drop_area.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {_T('border')};
                border-radius: 8px;
                background: {_T('bg')};
                margin-top: 8px;
            }}
            QFrame:hover {{
                border-color: {_T('accent')};
                background: {_T('panel')};
            }}
        """)
        drop_label = QLabel(tr("drop_here_to_remove_folder"))
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_label.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        drop_area_layout = QVBoxLayout(drop_area)
        drop_area_layout.addWidget(drop_label)

        def _drag_enter(e):
            if e.mimeData().hasFormat("application/x-craftlife-card"):
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dragEnterEvent = _drag_enter

        def _drop(e):
            raw = e.mimeData().data("application/x-craftlife-card")
            info = json.loads(raw.data().decode())
            if info["mode"] == self.mode and info["user_id"] == self.user_id:
                db.set_item_folder(self.user_id, self.mode, info["item_id"], None)
                self.load()
                e.acceptProposedAction()
            else:
                e.ignore()
        drop_area.dropEvent = _drop

        lay.insertWidget(insert_pos, drop_area)

    def _make_card(self, item: dict) -> QFrame:
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        ico = QLabel(item["icon"])
        ico.setFont(QFont("Segoe UI", 22))
        ico.setMinimumWidth(38)
        row.addWidget(ico)

        info = QVBoxLayout()
        info.setSpacing(2)
        nm = QLabel(item["name"])
        nm.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(nm)

        tipe = tr("economy_type_income") if item["type"] == "income" else tr("economy_type_expense")
        color = "#80c000" if item["type"] == "income" else "#e05050"
        amount_str = f"+{self.format_currency(item['amount'])}" if item["type"] == "income" else f"-{self.format_currency(item['amount'])}"
        sub = QLabel(tr("economy_item_format", color=color, type=tipe, amount=amount_str, category=item['category'], date=item['date']))
        sub.setTextFormat(Qt.TextFormat.RichText)
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        if item.get("notes"):
            nl = QLabel(f"📝 {item['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        row.addLayout(info, 1)

        edit_btn = _btn("✏️", h=36)
        edit_btn.setMinimumWidth(36)
        edit_btn.clicked.connect(lambda _, i=item["id"]: self._edit(i))
        row.addWidget(edit_btn)

        dl = _btn("🗑", "danger", h=36)
        dl.setMinimumWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)

        dup_btn = _btn("📋", h=36)
        dup_btn.setMinimumWidth(36)
        dup_btn.clicked.connect(lambda _, i=item["id"]: self._duplicate(i))
        row.addWidget(dup_btn)

        folder_btn = _btn("📁", h=36)
        folder_btn.setMinimumWidth(36)
        folder_btn.clicked.connect(lambda _, iid=item["id"], fid=item.get("folder_id"): self._move_to_folder(iid, fid))
        row.addWidget(folder_btn)

        # Tombol panah untuk reorder (naik/turun)
        up_btn = _btn("⬆", h=36)
        up_btn.setMinimumWidth(36)
        up_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "up"))
        row.addWidget(up_btn)

        down_btn = _btn("⬇", h=36)
        down_btn.setMinimumWidth(36)
        down_btn.clicked.connect(lambda _, i=item["id"]: self._reorder(i, "down"))
        row.addWidget(down_btn)

        card = DraggableCard(
            item_id=item["id"],
            mode="economy",
            user_id=self.user_id,
            current_folder_id=item.get("folder_id"),
            content_widget=content,
            parent=self
        )
        return card

    def _create_card_widget(self, item: dict) -> DraggableCard:
        """Bungkus kartu dan simpan referensi."""
        card = self._make_card(item)
        self.card_widgets[item["id"]] = card
        return card

    def _reorder(self, item_id, direction):
        r = db.reorder_item(self.user_id, self.mode, item_id, direction)
        if r.get("ok"):
            if r.get("moved", False):
                SND.click()
                QTimer.singleShot(0, self.load)
            # else tidak ada perubahan, tidak perlu reload
        else:
            SND.error()
            _show(self, tr("msg_error"), r.get("msg", "Gagal mengubah urutan"), "error")

    def _move_to_folder(self, item_id: int, current_folder_id: int = None):
        folders = db.get_task_folders(self.user_id, "economy")
        folder_names = [tr("folder_no_folder")] + [f["name"] for f in folders]
        folder_ids = [None] + [f["id"] for f in folders]
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("dialog_move_folder"))
        dlg.setMinimumSize(300, 200)
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
        btn_ok = _btn(tr("dialog_move"), "solid", dlg.accept)
        layout.addWidget(QLabel(tr("dialog_select_folder")))
        layout.addWidget(combo)
        layout.addWidget(btn_ok)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected_id = folder_ids[combo.currentIndex()]
            db.update_economy_item(item_id, self.user_id, folder_id=selected_id)
            QTimer.singleShot(0, self.load)
            SND.notify()

    def load(self):
        if not AppState.user_id:
            return

        self.card_widgets.clear()
        self._load_currency_settings()
        self._check_and_apply_debt_penalties()

        # Update summary cards
        summary = db.get_economy_summary(self.user_id)
        self.income_card.value_label.setText(self.format_currency(summary['total_income']))
        self.expense_card.value_label.setText(self.format_currency(summary['total_expense']))
        self.balance_card.value_label.setText(self.format_currency(summary['balance']))
        unpaid_total = db.get_total_unpaid_debt(self.user_id)
        self.debt_label.setText(tr("economy_total_debt", amount=self.format_currency(unpaid_total)))
        savings_list = db.get_savings(self.user_id)
        total_savings = sum(s['current_amount'] for s in savings_list) if savings_list else 0
        self.saving_label.setText(tr("economy_total_saving", amount=self.format_currency(total_savings)))
        self.saving_label.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")

        # Refresh category combo
        current_cat = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem(tr("economy_all_categories"), "all")
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

        while self._lay_debt.count():
            item = self._lay_debt.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        debts = db.get_debts(self.user_id, include_paid=False)  # hanya yang belum lunas
        unpaid_total = db.get_total_unpaid_debt(self.user_id)

        # Filter items
        type_filter = None
        type_text = self.type_combo.currentData()
        if type_text == "income":
            type_filter = "income"
        elif type_text == "expense":
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
        while self._tabs.count() > 5:
            self._tabs.removeTab(5)
        self._cat_lays.clear()
        self._cat_inners.clear()

        # Tab "Semua"
        self._render_to_layout(self._lay_all, self._inner_all, items, folders,
                               tr("economy_empty"))

        # Refresh tab hutang

        if not debts:
            empty = QLabel(tr("economy_debt_empty"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:30px;")
            self._lay_debt.addWidget(empty)
        else:
            for debt in debts:
                card = self._make_debt_card(debt)
                self._lay_debt.addWidget(card)

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

        # Tampilkan jumlah hutang overdue sebagai label (bukan popup agar tidak mengganggu)
        overdue_count = db.get_overdue_debts_count(self.user_id)
        if overdue_count > 0:
            self.debt_label.setText(
                tr("economy_overdue_warning", count=overdue_count)
            )
            self.debt_label.setStyleSheet("color: #e05050; font-size: 12px; font-weight: bold;")
        else:
            self.debt_label.setText(tr("economy_total_debt", amount=self.format_currency(unpaid_total)))
            self.debt_label.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")
      
        self._load_savings()
        self._load_investments()
        self._load_subscriptions()

    def _check_and_apply_debt_penalties(self):
        conn = db.get_conn()
        today = date.today().isoformat()
        try:
            debts = conn.execute("""
                SELECT id, due_date, name FROM debts
                WHERE user_id=? AND is_paid=0 AND penalty_applied=0 AND due_date IS NOT NULL
            """, (self.user_id,)).fetchall()
            debts = [dict(d) for d in debts]
        finally:
            conn.close()

        penalties = []  # untuk menyimpan pesan
        for debt in debts:
            due = debt["due_date"]
            if due < today:
                days_late = (date.today() - datetime.strptime(due, "%Y-%m-%d").date()).days
                if days_late >= 3:
                    r = db.apply_late_debt_penalty(self.user_id, debt["id"], days_late)
                    if r.get("ok"):
                        penalties.append(
                            tr("debt_penalty_detail", due=due, days=days_late, gold=r['gold_lost'])
                        )
        if penalties:
            SND.error()
            msg = "\n".join(penalties)
            _show(self, tr("penalty_title"), msg, "warning")

    def _make_debt_card(self, debt: dict) -> QFrame:
        today = date.today().isoformat()
        is_overdue = debt.get("due_date") and debt["due_date"] < today

        f = _card()
        if is_overdue:
            f.setStyleSheet(
                f"QFrame#card {{ background: {_T('panel')}; "
                f"border: 2px solid #e05050; border-left: 6px solid #e05050; "
                f"border-radius: 8px; }}"
            )
        else:
            f.setStyleSheet(f"QFrame#card {{ background: {_T('panel')}; "
                            f"border: 1px solid {_T('border')}; border-radius: 8px; }}")

        row = QHBoxLayout(f)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(10)

        icon = QLabel("💸")
        icon.setFont(QFont("Segoe UI", 22))
        icon.setMinimumWidth(38)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)

        nm = QLabel(debt["name"])
        nm.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        info.addWidget(nm)

        amount_str = self.format_currency(debt['amount'])
        due_str = f"  ⏰ Tenggat: {debt['due_date']}" if debt.get("due_date") else ""
        sub = QLabel(amount_str + due_str)
        sub.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(sub)

        penalty = debt.get("penalty_applied", 0)
        if penalty:
            penalty_lbl = QLabel(tr("debt_penalty_label", amount=self.format_currency(debt.get('penalty_amount',0))))
            penalty_lbl.setStyleSheet("color:#e05050; font-size:10px;")
            info.addWidget(penalty_lbl)

        if debt.get("notes"):
            nl = QLabel(f"📝 {debt['notes']}")
            nl.setWordWrap(True)
            nl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(nl)

        row.addLayout(info, 1)

        pay_btn = _btn(tr("economy_btn_pay"), "gold", h=36)
        pay_btn.setMinimumWidth(80)
        pay_btn.clicked.connect(lambda _, d=debt["id"]: self._pay_debt(d))
        row.addWidget(pay_btn)

        installment_btn = _btn(tr("economy_btn_installment"), "diamond", h=36)
        installment_btn.setMinimumWidth(80)
        installment_btn.clicked.connect(lambda _, d=debt: self._installment_debt(d))
        row.addWidget(installment_btn)

        edit_btn = _btn("✏️", h=36)
        edit_btn.setMinimumWidth(36)
        edit_btn.clicked.connect(lambda _, d=debt: self._edit_debt(d))
        row.addWidget(edit_btn)

        del_btn = _btn("🗑", "danger", h=36)
        del_btn.setMinimumWidth(36)
        del_btn.clicked.connect(lambda _, d=debt["id"]: self._delete_debt(d))
        row.addWidget(del_btn)

        return f

    def _installment_debt(self, debt):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("economy_debt_installment_title", name=debt['name']))
        dlg.setMinimumSize(400, 250)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        remaining_text = tr("debt_remaining", amount=self.format_currency(debt['amount']))
        layout.addWidget(QLabel(remaining_text))
        layout.addWidget(QLabel(tr("economy_debt_installment_label")))
        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(1, debt['amount'])
        amount_spin.setPrefix(f"{self.currency_symbol}: ")
        amount_spin.setValue(min(10000, debt['amount']))
        amount_spin.setMinimumHeight(42)
        layout.addWidget(amount_spin)

        info = QLabel(tr("economy_debt_installment_hint"))
        info.setWordWrap(True)
        info.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        layout.addWidget(info)

        btn = _btn(tr("economy_debt_installment_btn"), "solid")
        btn.clicked.connect(lambda: self._process_installment(debt['id'], amount_spin.value(), dlg))
        layout.addWidget(btn)
        dlg.exec()

    def _process_installment(self, debt_id, amount_user, dialog):
        if amount_user <= 0:
            _show(self, tr("msg_error"), tr("installment_amount_zero"), "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        loading = LoadingDialog("Memproses cicilan...", self)
        loading.show()
        QApplication.processEvents()
        r = db.pay_debt_installment(debt_id, self.user_id, amount_idr)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            dialog.accept()
            QTimer.singleShot(0, self.load)
            AppState.refresh()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _edit(self, item_id):
        items = db.get_economy_items(self.user_id)
        item = next((i for i in items if i["id"] == item_id), None)
        if not item:
            return
        dlg = AddEconomyDialog(self.user_id, item, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _delete(self, item_id):
        db.delete_economy_item(self.user_id, item_id)
        SND.click()
        QTimer.singleShot(0, self.load)

    def _duplicate(self, item_id):
        r = db.duplicate_economy_item(self.user_id, item_id)
        if r["ok"]:
            SND.click()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r.get("msg", tr("duplicate_failed")), "error")
        QTimer.singleShot(0, self.load)

    def _open_add(self):
        dlg = AddEconomyDialog(self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _open_folder_add(self):
        dlg = FolderDialog("economy", self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _add_debt(self):
        dlg = AddEditDebtDialog(self.user_id, parent=self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _edit_debt(self, debt):
        dlg = AddEditDebtDialog(self.user_id, debt, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _delete_debt(self, debt_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("economy_debt_delete_confirm"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_debt(debt_id, self.user_id)
            SND.click()
            QTimer.singleShot(0, self.load)

    def _pay_debt(self, debt_id):
        loading = LoadingDialog("Memproses pelunasan...", self)
        loading.show()
        QApplication.processEvents()
        r = db.mark_debt_paid(debt_id, self.user_id)
        loading.accept()
        if r["ok"]:
            SND.complete()
            conn = db.get_conn()
            debt = conn.execute("SELECT amount FROM debts WHERE id=?", (debt_id,)).fetchone()
            conn.close()
            if debt:
                amount_usr = self.convert_from_idr(debt["amount"])
                _show(self, tr("berhasil_title"), tr("berhasil_debt_paid", symbol=self.currency_symbol, amount=amount_usr), "success")
            else:
                _show(self, tr("berhasil_title"), r["msg"], "success")
            AppState.refresh()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)

    def _load_currency_settings(self):
        curr = db.get_user_currency(self.user_id)
        self.currency = curr
        self.CURRENCY_RATES = {"IDR": 1, "USD": 17800, "EUR": 20700}
        self.currency_symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}[curr]

    def convert_from_idr(self, amount_idr):
        """Konversi dari IDR ke mata uang user (untuk tampilan)."""
        rate = self.CURRENCY_RATES[self.currency]
        return amount_idr / rate

    def convert_to_idr(self, amount):
        """Konversi dari mata uang user ke IDR (untuk penyimpanan)."""
        rate = self.CURRENCY_RATES[self.currency]
        return amount * rate

    def format_currency(self, amount_idr):
        """Kembalikan string mata uang yang sudah dikonversi + simbol."""
        converted = self.convert_from_idr(amount_idr)
        return f"{self.currency_symbol} {converted:,.0f}"

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ========== DEBT DIALOG ==========
class AddEditDebtDialog(QDialog):
    def __init__(self, user_id: int, debt=None, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.debt = debt
        self.setWindowTitle(tr("debt_edit_title") if debt else tr("debt_add_title"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(420)
        self.setStyleSheet(build_ss())
        self._build()
        if self.debt:
            user_curr = db.get_user_currency(self.user_id)
            amount_idr = self.debt['amount']
            amount_usr = db.convert_from_idr(amount_idr, user_curr)
            self._amount.setText(f"{amount_usr:.2f}")

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Nama hutang
        lay.addWidget(_lbl(tr("economy_debt_name_label"), size=12) )
        self._name = _input(tr("economy_debt_name_ph"))
        if self.debt:
            self._name.setText(self.debt["name"])
        lay.addWidget(self._name)

        # Jumlah
        lay.addWidget(_lbl(tr("economy_amount_label", symbol=self.currency_symbol()), size=12))
        self._amount = QLineEdit()
        self._amount.setPlaceholderText("0")
        self._amount.setMinimumHeight(42)
        if self.debt:
            self._amount.setText(str(self.debt["amount"]))
        lay.addWidget(self._amount)

        # Tenggat waktu (opsional)
        lay.addWidget(_lbl(tr("economy_debt_deadline_label"), size=12))
        self._due_date = QLineEdit()
        self._due_date.setPlaceholderText("YYYY-MM-DD")
        from datetime import date, timedelta
        if self.debt and self.debt.get("due_date"):
            self._due_date.setText(self.debt["due_date"])
        else:
            self._due_date.setText((date.today() + timedelta(days=14)).isoformat())
        lay.addWidget(self._due_date)

        # Catatan
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder"))
        if self.debt:
            self._notes.setText(self.debt.get("notes", ""))
        lay.addWidget(self._notes)

        lay.addSpacing(8)
        ok_lbl = tr("dialog_save") if self.debt else tr("economy_debt_add_title")
        ok = _btn(ok_lbl, "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        root.addWidget(_scrolled(content))

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("economy_debt_nama_not_empty"), "error")
            return
        try:
            amount_user = float(self._amount.text().strip())
            if amount_user <= 0:
                raise ValueError
        except:
            _show(self, tr("msg_error"), tr("msg_invalid_amount"), "error")
            return
        
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        
        due_date = self._due_date.text().strip()
        if due_date == "":
            due_date = None
        notes = self._notes.text()
        
        if self.debt:
            db.update_debt(self.debt["id"], self.user_id,
                        name=name, amount=amount_idr, due_date=due_date, notes=notes)
            SND.complete()
            _show(self, tr("berhasil_title"), tr("economy_debt_done_update"), "success")
        else:
            r = db.add_debt(self.user_id, name, amount_idr, due_date, notes)
            if r["ok"]:
                SND.complete()
                _show(self, tr("berhasil_title"), tr("economy_succes_add_debt", name=name), "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r["msg"], "error")
                return
        self.accept()

# ========== SAVINGS DIALOG ==========
class AddEditSavingDialog(QDialog):
    def __init__(self, user_id: int, saving=None, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.saving = saving
        self.setWindowTitle(tr("saving_edit_title") if saving else tr("saving_add_title"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setStyleSheet(build_ss())
        self._build()
        if self.saving:
            user_curr = db.get_user_currency(self.user_id)
            current_idr = self.saving.get('current_amount', 0)
            target_idr = self.saving.get('target_amount', 0)
            current_usr = db.convert_from_idr(current_idr, user_curr)
            target_usr = db.convert_from_idr(target_idr, user_curr)
            self._current.setValue(current_usr)
            self._target.setValue(target_usr)

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Nama tabungan
        lay.addWidget(_lbl(tr("economy_saving_name_label"), size=12))
        self._name = _input(tr("economy_saving_name_ph"))
        if self.saving:
            self._name.setText(self.saving["name"])
        lay.addWidget(self._name)

        # Icon
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        icon_choices = [
            (tr("saving_icon_bank"), "🏦"), 
            (tr("saving_icon_target"), "🎯"),
            (tr("saving_icon_vacation"), "🏖️"),
            (tr("saving_icon_vehicle"), "🚗"),
            (tr("saving_icon_house"), "🏠"),
            (tr("saving_icon_education"), "📚"),
            (tr("saving_icon_health"), "💊"),
            (tr("saving_icon_shopping"), "🛒"),
            (tr("saving_icon_investment"), "💰"),
            (tr("saving_icon_gift"), "🎁"),
            (tr("saving_icon_pet"), "🐾"),
            (tr("saving_icon_food"), "🍽️")
        ]
        self._icon = _combo(icon_choices)
        if self.saving:
            idx = self._icon.findData(self.saving.get("icon", "🏦"))
            if idx >= 0:
                self._icon.setCurrentIndex(idx)
        lay.addWidget(self._icon)

        # Jumlah saat ini
        lay.addWidget(_lbl(tr("economy_saving_current_amount", symbol=self.currency_symbol()), size=12))
        self._current = QDoubleSpinBox()
        self._current.setRange(0, 1_000_000_000)
        self._current.setValue(self.saving["current_amount"] if self.saving else 0)
        self._current.setPrefix(f"{self.currency_symbol()}: ")
        self._current.setMinimumHeight(42)
        lay.addWidget(self._current)

        # Target jumlah
        lay.addWidget(_lbl(tr("economy_saving_target_amount_label"), size=12))
        self._target = QDoubleSpinBox()
        self._target.setRange(0, 1_000_000_000)
        self._target.setValue(self.saving["target_amount"] if self.saving and self.saving.get("target_amount") else 0)
        self._target.setPrefix(f"{self.currency_symbol()}: ")
        self._target.setMinimumHeight(42)
        lay.addWidget(self._target)

        # Target tanggal
        lay.addWidget(_lbl(tr("economy_saving_target_date_label"), size=12))
        self._target_date = QLineEdit()
        from datetime import date, timedelta
        if self.saving and self.saving.get("target_date"):
            self._target_date.setText(self.saving["target_date"])
        else:
            self._target_date.setText((date.today() + timedelta(days=90)).isoformat())
        self._target_date.setMinimumHeight(42)
        lay.addWidget(self._target_date)

        # Catatan
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self._notes = _input(tr("dialog_notes_placeholder"))
        if self.saving:
            self._notes.setText(self.saving.get("notes", ""))
        lay.addWidget(self._notes)

        lay.addSpacing(8)
        ok_lbl = tr("dialog_save") if self.saving else tr("economy_saving_add_btn")
        ok = _btn(ok_lbl, "solid", self._save, 46)
        lay.addWidget(ok)
        self._name.returnPressed.connect(self._save)

        root.addWidget(_scrolled(content))

    def _save(self):
        name = self._name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("saving_name_empty"), "error")
            return
        icon = self._icon.currentData()
        
        current_user = self._current.value()
        target_user = self._target.value()
        
        user_currency = db.get_user_currency(self.user_id)
        current_idr = db.convert_to_idr(current_user, user_currency)
        target_idr = db.convert_to_idr(target_user, user_currency)
        
        target_date = self._target_date.text().strip()
        if target_date == "":
            target_date = None
        notes = self._notes.text()
        
        if self.saving:
            db.update_saving(self.saving["id"], self.user_id,
                            name=name, icon=icon, current_amount=current_idr,
                            target_amount=target_idr, target_date=target_date, notes=notes)
            SND.complete()
            _show(self, tr("berhasil_title"), "Tabungan berhasil diupdate!", "success")
        else:
            r = db.add_saving(self.user_id, name, icon, target_idr, current_idr, target_date, notes)
            if r["ok"]:
                SND.complete()
                _show(self, tr("berhasil_title"), f"Tabungan '{name}' ditambahkan!", "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r["msg"], "error")
                return
        self.accept()

class AddToSavingDialog(QDialog):
    def __init__(self, saving_id, user_id, current_amount, parent=None):
        super().__init__(parent)
        
        self.saving_id = saving_id
        self.user_id = user_id
        self.current_amount = current_amount
        self.setWindowTitle(tr("saving_add_funds_title"))
        self.setMinimumSize(350, 200)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(_lbl(f"Jumlah yang ingin ditambahkan: ({self.currency_symbol()})", size=12))
        self.amount = QDoubleSpinBox()
        self.amount.setRange(0, 1_000_000_000)
        self.amount.setValue(10000)
        self.amount.setPrefix(f"{self.currency_symbol()}: ")
        self.amount.setMinimumHeight(42)
        layout.addWidget(self.amount)
        btn = _btn(tr("economy_saving_add_confirm_btn"), "solid", self._add, 40)
        layout.addWidget(btn)

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

    def _add(self):
        amt_user = self.amount.value()
        if amt_user <= 0:
            _show(self, tr("msg_error"), "Jumlah harus lebih dari 0", "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amt_idr = db.convert_to_idr(amt_user, user_currency)
        r = db.add_to_saving(self.saving_id, self.user_id, amt_idr)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), tr("berhasil_saving_add", symbol=self.currency_symbol(), amount=f"{amt_user:.0f}"), "success")
            self.accept()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

# =========== INVESTMENT DIALOG =========== #
class AddInvestmentDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.setWindowTitle(tr("economy_invest_add"))
        self.setMinimumWidth(450)
        self.setMinimumHeight(420)
        self.setStyleSheet(build_ss())
        self._build()

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(14)

        lay.addWidget(_lbl(tr("investment_add_title"), "section", 14, True))
        lay.addWidget(_sep())

        lay.addWidget(_lbl(tr("economy_invest_name"), size=12))
        self.name = _input(tr("economy_invest_name_ph"))
        lay.addWidget(self.name)

        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        icons = [
            (tr("invest_icon_stock"), "📈"), 
            (tr("invest_icon_deposit"), "🏦"), 
            (tr("invest_icon_gold"), "💰"), 
            (tr("invest_icon_property"), "🏠"), 
            (tr("invest_icon_crypto"), "🚀")
        ]
        self.icon = _combo(icons)
        lay.addWidget(self.icon)

        lay.addWidget(_lbl(tr("economy_invest_amount_label", symbol=self.currency_symbol()), size=12))
        self.amount = QDoubleSpinBox()
        self.amount.setRange(1000, 1e9)
        self.amount.setValue(50000)
        self.amount.setPrefix(f"{self.currency_symbol()}: ")
        lay.addWidget(self.amount)

        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self.notes = _input()
        lay.addWidget(self.notes)

        btn = _btn(tr("economy_invest_btn"), "solid", self._save)
        lay.addWidget(btn)
        root.addWidget(_scrolled(content))

    def _save(self):
        name = self.name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("invest_name_empty"), "error")
            return
        amount_user = self.amount.value()
        if amount_user <= 0:
            _show(self, tr("msg_error"), tr("invest_amount_positive"), "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        icon = self.icon.currentData()
        notes = self.notes.text()
        r = db.add_investment(self.user_id, name, icon, amount_idr, notes)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            self.accept()
        else:
            SND.error()
            msg = r["msg"]
            import re
            match = re.search(r"Saldo: (\d+)", msg)
            if match:
                saldo_idr = int(match.group(1))
                saldo_usr = db.convert_from_idr(saldo_idr, user_currency)
                saldo_str = f"{self.currency_symbol()} {saldo_usr:,.0f}"
                msg = msg.replace(f"Saldo: {saldo_idr}", f"Saldo: {saldo_str}")
            _show(self, tr("gagal_title"), msg, "error")

# ========== AddSubscriptionDialog ========== #
class AddSubscriptionDialog(QDialog):
    def __init__(self, user_id, sub=None, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.sub = sub
        self.setWindowTitle(tr("subscription_edit_title") if sub else tr("subscription_add_title"))
        self.setMinimumWidth(480)
        self.setMinimumHeight(520)
        self.setStyleSheet(build_ss())
        self._build()
        if self.sub:
            user_curr = db.get_user_currency(self.user_id)
            amount_idr = self.sub['amount']
            amount_usr = db.convert_from_idr(amount_idr, user_curr)
            self.amount.setValue(amount_usr)

    def currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        symbols = {"IDR": "Rp", "USD": "$", "EUR": "€"}
        return symbols.get(curr, "Rp")

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
        lay.addWidget(_lbl(tr("economy_sub_name_label"), size=12))
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr("sub_name_placeholder"))
        if self.sub:
            self.name.setText(self.sub["name"])
        lay.addWidget(self.name)

        # Icon
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        icons = [
            (tr("sub_icon_tv"), "📺"), 
            (tr("sub_icon_music"), "🎵"), 
            (tr("sub_icon_ai"), "🤖"), 
            (tr("sub_icon_book"), "📚"), 
            (tr("sub_icon_gym"), "🏋️"), 
            (tr("sub_icon_general"), "📅")
        ]
        self.icon = _combo(icons)
        if self.sub:
            idx = self.icon.findData(self.sub.get("icon", "📅"))
            if idx >= 0:
                self.icon.setCurrentIndex(idx)
        lay.addWidget(self.icon)

        # Amount
        lay.addWidget(_lbl(tr("economy_sub_cost_label", symbol=self.currency_symbol()), size=12))
        self.amount = QDoubleSpinBox()
        self.amount.setRange(1000, 1e7)
        self.amount.setValue(self.sub["amount"] if self.sub else 10000)
        self.amount.setPrefix(f"{self.currency_symbol()}: ")
        lay.addWidget(self.amount)

        # Due date
        lay.addWidget(_lbl(tr("economy_sub_due_label"), size=12))
        self.due_date = QLineEdit()
        from datetime import date, timedelta
        default_date = (date.today() + timedelta(days=30)).isoformat() if not self.sub else self.sub["due_date"]
        self.due_date.setText(default_date)
        lay.addWidget(self.due_date)

        # Period
        lay.addWidget(_lbl(tr("economy_sub_period_label"), size=12))
        period_opts = [(tr("sub_period_monthly"), "monthly"), (tr("sub_period_yearly"), "yearly"), (tr("sub_period_onetime"), "one-time")]
        self.period = _combo(period_opts)
        if self.sub:
            idx = self.period.findData(self.sub["period"])
            if idx >= 0:
                self.period.setCurrentIndex(idx)
        lay.addWidget(self.period)
        self.period.currentIndexChanged.connect(self._on_period_changed)

        # Recurring checkbox
        self.recurring_cb = QCheckBox(tr("economy_sub_autorenew"))
        self.recurring_cb.setChecked(self.sub["is_recurring"] if self.sub else True)
        lay.addWidget(self.recurring_cb)

        # Notes
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self.notes = QLineEdit()
        self.notes.setPlaceholderText(tr("dialog_notes_placeholder"))
        if self.sub:
            self.notes.setText(self.sub.get("notes", ""))
        lay.addWidget(self.notes)

        btn = _btn(tr("dialog_save"), "solid", self._save)
        lay.addWidget(btn)
        root.addWidget(_scrolled(content))

    def _save(self):
        name = self.name.text().strip()
        if not name:
            _show(self, tr("msg_error"), "Nama layanan harus diisi", "error")
            return
        icon = self.icon.currentData()
        amount_user = self.amount.value()
        if amount_user <= 0:
            _show(self, tr("msg_error"), "Biaya harus lebih dari 0", "error")
            return
        user_currency = db.get_user_currency(self.user_id)
        amount_idr = db.convert_to_idr(amount_user, user_currency)
        
        due_date = self.due_date.text().strip()
        if not due_date:
            from datetime import date, timedelta
            due_date = (date.today() + timedelta(days=30)).isoformat()
        period = self.period.currentData()
        is_recurring = self.recurring_cb.isChecked()
        if period == 'one-time':
            is_recurring = False
        notes = self.notes.text()
        
        if self.sub:
            db.update_subscription(self.sub["id"], self.user_id,
                                name=name, icon=icon, amount=amount_idr, due_date=due_date,
                                period=period, is_recurring=is_recurring, notes=notes)
            SND.complete()
            _show(self, tr("berhasil_title"), "Subscription berhasil diupdate", "success")
        else:
            r = db.add_subscription(self.user_id, name, icon, amount_idr, due_date, period, is_recurring, notes)
            if r["ok"]:
                SND.complete()
                _show(self, tr("berhasil_title"), f"Subscription '{name}' ditambahkan", "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r.get("msg", "Gagal menambah subscription"), "error")
                return
        self.accept()

    def _on_period_changed(self):
        period = self.period.currentData()
        if period == 'one-time':
            self.recurring_cb.setChecked(False)
            self.recurring_cb.setEnabled(False)
        else:
            self.recurring_cb.setEnabled(True)

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
        root.addWidget(_lbl(tr("shop_title"), "section", 14, True))
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
        self._tabs.addTab(_scrolled(self._items_inner), tr("shop_tab_items"))
        self._tabs.addTab(_scrolled(self._pets_inner),  tr("shop_tab_pets"))
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
        buffs = db.get_all_active_buffs(self.user_id)
        if buffs:
            self._buff_bar.setText("⚡ Buff Aktif :  " + "  ·  ".join(buffs))
        else:
            self._buff_bar.setText("⚡ Buff Aktif :  Tidak ada buff aktif.")

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
            tp = QLabel(tr(f"shop_type_{item['type']}"))
            tp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tp.setStyleSheet(f"font-size:10px; color:{_T('muted')};")
            cl.addWidget(tp)

            if iid in owned:
                qty = owned[iid]["quantity"]
                inv_id = owned[iid]["id"]
                
                # Label "Dimiliki"
                ol = QLabel(tr("shop_owned"))
                ol.setAlignment(Qt.AlignmentFlag.AlignCenter)
                ol.setStyleSheet(f"color:{_T('light')}; font-size:11px; font-weight:bold;")
                cl.addWidget(ol)
                
                # Tampilkan tombol berdasarkan tipe
                if item["type"] == "consumable":
                    ub = _btn(tr("shop_use", qty=qty), "diamond", h=30)
                    ub.clicked.connect(lambda _, i=iid: self._use(i))
                    cl.addWidget(ub)

                    bb = _btn(tr("shop_buy_again"), "gold", h=30)
                    bb.clicked.connect(lambda _, i=iid: self._buy(i))
                    cl.addWidget(bb)

                    sell_price = int(item["cost"] * 0.1)
                    sell_price = max(1, sell_price)
                    sell_btn = _btn(tr("shop_sell"), h=30)
                    sell_btn.setMinimumWidth(60)
                    sell_btn.clicked.connect(lambda _, inv=owned[iid]["id"], name=item['name'], cost=item['cost'], qty=qty: 
                                            self._sell_item(inv, name, cost, qty))
                    cl.addWidget(sell_btn)
                    # Tampilkan harga jual
                    price_lbl = QLabel(tr("shop_sell_price", gold=sell_price))
                    price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    price_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:10px;")
                    cl.addWidget(price_lbl)
                else:
                    # Tombol Jual
                    sell_price = int(item["cost"] * 0.1)
                    sell_price = max(1, sell_price)
                    sell_btn = _btn(tr("shop_sell"), h=30)
                    sell_btn.setMinimumWidth(60)
                    sell_btn.clicked.connect(lambda _, inv=inv_id, name=item['name'], cost=item['cost'], qty=qty: 
                                            self._sell_item(inv, name, cost, qty))
                    cl.addWidget(sell_btn)
                    
                    # Tampilkan harga jual
                    price_lbl = QLabel(tr("shop_sell_price", gold=sell_price))
                    price_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    price_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:10px;")
                    cl.addWidget(price_lbl)
            else:
                # Belum dimiliki: tampilkan harga dan tombol Beli
                cl.addWidget(QLabel(
                    f"💰 {item['cost']} G",
                    alignment=Qt.AlignmentFlag.AlignCenter))
                bb = _btn(tr("shop_buy"), "gold", h=30)
                bb.clicked.connect(lambda _, i=iid: self._buy(i))
                cl.addWidget(bb)
                
            self._items_grid.addWidget(f, idx // COLS, idx % COLS)

        # ── Pets ──────────────────────────────────────────────────────────────
        user_pets  = db.get_user_pets(self.user_id)
        owned_pets = {p["pet_id"] for p in user_pets}
        active_pets = {p["pet_id"] for p in user_pets if p["is_active"]}
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
                if pid in active_pets:
                    # Label AKTIF
                    al = QLabel(tr("shop_active"))
                    al.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    al.setStyleSheet("color:#4dd9e0; font-size:11px; font-weight:bold;")
                    cl.addWidget(al)
                    # Tombol Unequip
                    uq = _btn(tr("shop_unequip"), "danger", h=30)
                    uq.clicked.connect(lambda _, p=pid: self._unequip(p))
                    cl.addWidget(uq)
                else:
                    eq = _btn(tr("shop_equip"), "diamond", h=30)
                    eq.clicked.connect(lambda _, p=pid: self._equip(p))
                    cl.addWidget(eq)
            else:
                cl.addWidget(QLabel(
                    f"💰 {pet['cost']} G",
                    alignment=Qt.AlignmentFlag.AlignCenter))
                ab = _btn(tr("shop_adopt"), "gold", h=30)
                ab.clicked.connect(lambda _, p=pid: self._adopt(p))
                cl.addWidget(ab)
            self._pets_grid.addWidget(f, idx // 3, idx % 3)

    def _buy(self, iid):
        r = db.buy_item(self.user_id, iid)
        if r["ok"]:
            SND.buy()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()

    def _sell_item(self, inv_id, item_name, item_cost, max_qty):
        """Dialog untuk menjual item dengan pilihan quantity."""
        sell_price_per_item = int(item_cost * 0.1)
        sell_price_per_item = max(1, sell_price_per_item)
        
        # Dialog pilih quantity
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("shop_sell_title"))
        dlg.setMinimumSize(350, 200)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        layout.addWidget(QLabel(tr("shop_sell_confirm", name=item_name, qty=1, gold=sell_price_per_item)))
        
        # Spin untuk quantity
        qty_spin = QSpinBox()
        qty_spin.setRange(1, max_qty)
        qty_spin.setValue(1)
        qty_spin.setSuffix(f" (max {max_qty})")
        qty_spin.setMinimumHeight(42)
        layout.addWidget(qty_spin)
        
        # Label total harga
        total_label = QLabel(tr("shop_sell_price", gold=sell_price_per_item))
        total_label.setStyleSheet(f"color:{_T('accent')}; font-weight:bold;")
        layout.addWidget(total_label)
        
        def update_total(value):
            total = value * sell_price_per_item
            total_label.setText(tr("shop_sell_price", gold=total))

        qty_spin.valueChanged.connect(update_total)
        
        btn_layout = QHBoxLayout()
        cancel_btn = _btn(tr("btn_cancel"), "flat", dlg.reject)
        sell_btn = _btn(tr("shop_sell"), "gold", dlg.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(sell_btn)
        layout.addLayout(btn_layout)
        
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        
        qty = qty_spin.value()
        
        # Konfirmasi akhir
        total_gold = qty * sell_price_per_item
        reply = QMessageBox.question(
            self,
            tr("shop_sell_title"),
            tr("shop_sell_confirm", name=item_name, qty=qty, gold=total_gold),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Proses penjualan
        r = db.sell_item(self.user_id, inv_id, qty)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            AppState.refresh()
            self.load()       
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _use(self, iid):
        r = db.use_item(self.user_id, iid)
        if r.get("ok"):
            SND.complete()
            _show(self, tr("item_used_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"),
                  r.get("msg", "Item tidak bisa digunakan."), "error")
        AppState.refresh()

    def _adopt(self, pid):
        r = db.adopt_pet(self.user_id, pid)
        if r["ok"]:
            SND.buy()
            _show(self, tr("adopt_success"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()

    def _equip(self, pid):
        r = db.equip_pet(self.user_id, pid)
        SND.notify()
        _show(self, "Pet Aktif", r["msg"], "success")
        AppState.refresh()

    def _unequip(self, pet_id):
        r = db.unequip_pet(self.user_id, pet_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()
        QTimer.singleShot(0, self.load)

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
        self.title = _lbl(tr("pets_title"), "section", 14, True)
        layout.addWidget(self.title)
        layout.addWidget(_sep())
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(12)
        # Atur alignment agar card tidak meregang
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        # Buat kolom dengan stretch yang sama (agar card terdistribusi merata)
        for col in range(3):
            self.grid.setColumnStretch(col, 1)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        self.grid.setColumnStretch(2, 1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.load()

    def load(self):
        # Bersihkan grid terlebih dahulu
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Ambil data pets dari database
        pets = db.get_user_pets(self.user_id)
        
        if not pets:
            empty = _lbl(tr("pets_empty"), "sub", 13)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(empty, 0, 0)
            return

        # Hitung jumlah pet aktif & info batas
        active_count = len([p for p in pets if p["is_active"]])
        user_level = AppState.user().get("level", 1)
        max_pets = 2 if user_level >= 25 else 1
        status_text = tr("pets_max_2") if user_level >= 25 else tr("pets_max_1")
        
        # Buat widget info (ditampilkan sebagai card di atas daftar pet)
        info_widget = _card()
        info_layout = QVBoxLayout(info_widget)
        info_label = QLabel(tr("pets_active_info", active=active_count, max=max_pets, level=user_level, status=status_text))
        info_label.setStyleSheet(f"color:{_T('light')}; font-size:13px; font-weight:bold;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(info_label)
        # Tambahkan info widget ke grid (baris 0, kolom 0, lebar 3 kolom)
        self.grid.addWidget(info_widget, 0, 0, 1, 3)

        # Mulai baris berikutnya untuk kartu pet (mulai dari baris 1)
        row = 1
        col = 0
        for i, p in enumerate(pets):
            pet_data = db.PETS_DATA.get(p["pet_id"], {})
            card = _card()
            card.setMinimumWidth(260)
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
                active_lbl = QLabel(tr("shop_active"))
                active_lbl.setStyleSheet("color:#80c000; font-size:10px;")
                top.addWidget(active_lbl)
            vlay.addLayout(top)

            # Level & EXP
            lvl_lbl = QLabel(tr("pets_level_label", level=p['level']))
            lvl_lbl.setStyleSheet("color:#f0a800; font-size:11px;")
            vlay.addWidget(lvl_lbl)
            exp_bar = QProgressBar()
            exp_needed = p["level"] * 100
            exp_bar.setMaximum(exp_needed)
            exp_bar.setValue(int(p["exp"]))
            exp_bar.setFormat(tr("pets_exp_format", exp=p['exp'], need=exp_needed))
            exp_bar.setMinimumHeight(8)
            vlay.addWidget(exp_bar)

            # Hunger
            hunger_bar = QProgressBar()
            hunger_bar.setMaximum(100)
            hunger_bar.setValue(int(p["hunger"]))
            hunger_bar.setFormat(tr("pets_hunger", hunger=p["hunger"]))
            hunger_bar.setMinimumHeight(12)
            hunger_bar.setStyleSheet("QProgressBar::chunk { background: #f0a800; }")
            vlay.addWidget(hunger_bar)

            # Buff
            base_buff = pet_data.get("base_buff", {})
            level = p["level"]
            scale = 1 + (level - 1) * 0.1   # Harus sama dengan scaling di database
            buff_lines = []
            if "xp_pct" in base_buff:
                val = base_buff['xp_pct'] * scale
                buff_lines.append(tr("pets_buff_xp_format", val=val))
            if "gold_pct" in base_buff:
                val = base_buff['gold_pct'] * scale
                buff_lines.append(tr("pets_buff_gold_format", val=val))
            if "boss_dmg" in base_buff:
                val = base_buff['boss_dmg'] * scale
                buff_lines.append(tr("pets_buff_dmg_format", val=val))
            if "hp_reduc" in base_buff:
                val = base_buff['hp_reduc'] * scale
                buff_lines.append(tr("pets_buff_reduc_format", val=val))
            if buff_lines:
                buff_label = QLabel(" | ".join(buff_lines))
                buff_label.setStyleSheet("font-size:10px; color:#4dd9e0;")
                vlay.addWidget(buff_label)

            # Tombol
            btn_row = QHBoxLayout()
            feed_cost = 30
            feed_btn = _btn(tr("pets_feed", cost=feed_cost), h=28)
            feed_btn.setMinimumWidth(70)
            feed_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._feed(pid))
            train_cost = 25 + (p["level"] - 1) * 5
            train_btn = _btn(tr("pets_train", cost=train_cost), h=28)
            train_btn.setMinimumWidth(70)
            train_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._train(pid))
            if p["is_active"]:
                unequip_btn = _btn(tr("shop_unequip"), "danger", h=28)
                unequip_btn.setMinimumWidth(80)
                unequip_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._unequip(pid))
                btn_row.addWidget(unequip_btn)
            else:
                equip_btn = _btn(tr("shop_equip"), "diamond", h=28)
                equip_btn.setMinimumWidth(80)
                equip_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._equip(pid))
                btn_row.addWidget(equip_btn)
            btn_row.addWidget(feed_btn)
            btn_row.addWidget(train_btn)
            vlay.addLayout(btn_row)

            # Tambahkan kartu ke grid (mulai dari row 1)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1

    def _feed(self, pet_id):
        r = db.feed_pet(self.user_id, pet_id)
        if r["ok"]:
            msg = tr("pet_fed", name=r['name'], cost=r['cost'])
            _show(self, tr("berhasil_title"), msg, "success")
        else:
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)
        AppState.refresh()

    def _train(self, pet_id):
        r = db.train_pet(self.user_id, pet_id)
        if r["ok"]:
            msg = tr("pet_trained", name=r['name'], exp=r['exp_gained'], cost=r['cost'])
            _show(self, tr("berhasil_title"), msg, "success")
            if r.get("leveled_up"):
                SND.level_up()
        else:
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)
        AppState.refresh()

    def _equip(self, pet_id):
        r = db.equip_pet(self.user_id, pet_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)
        AppState.refresh()

    def _unequip(self, pet_id):
        r = db.unequip_pet(self.user_id, pet_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)
        AppState.refresh()

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

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

    # ---------- KOMPONEN DASHBOARD ----------
    def _make_header(self, guild: dict, user: dict) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        info = QVBoxLayout()
        info.setSpacing(2)
        name_label = QLabel(tr("guild_name_header", name=guild.get('name', 'Guild')))
        name_label.setStyleSheet(f"font-size:18px; font-weight:bold; color:{_T('light')};")
        info.addWidget(name_label)
        id_label = QLabel(tr("guild_id_level", id=guild.get('id', '?'), level=guild.get('level', 1)))
        id_label.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
        info.addWidget(id_label)
        if guild.get('description'):
            desc = QLabel(tr("guild_description_label", desc=guild['description']))
            desc.setWordWrap(True)
            desc.setStyleSheet(f"color:{_T('text')}; font-size:12px;")
            info.addWidget(desc)

        layout.addLayout(info, 1)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)

        chat_btn = _btn(tr("guild_chat_title"), "diamond", self._open_guild_chat, 34)
        chat_btn.setMinimumWidth(80)
        btn_layout.addWidget(chat_btn)

        if user["id"] == guild.get("leader_id"):
            edit_btn = _btn(tr("guild_edit_desc_btn"), "flat", self._edit_guild_bio, 34)
            btn_layout.addWidget(edit_btn)

        leave_btn = _btn(tr("guild_leave_btn"), "danger", self._leave, 34)
        leave_btn.setMinimumWidth(80)
        btn_layout.addWidget(leave_btn)

        layout.addLayout(btn_layout)
        return w

    def _make_stats(self, guild: dict, members: list) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setSpacing(10)

        level = guild.get('level', 1)
        exp = guild.get('exp', 0)
        need = level * 500
        member_count = len(members)
        buff_xp = guild.get('buff_xp', 0)
        buff_gold = guild.get('buff_gold', 0)
        buff_damage = guild.get('buff_damage', 0)
        crit_chance = guild.get('crit_chance', 0)

        cards = [
            (tr("guild_stats_level"), tr("guild_stats_level_value", level=level), "#80c000"),
            (tr("guild_stats_members"), tr("guild_stats_members_value", count=member_count), "#4da6ff"),
            (tr("guild_stats_bonus_xp"), tr("guild_stats_bonus_xp_value", xp=buff_xp), "#f0a800"),
            (tr("guild_stats_bonus_gold"), tr("guild_stats_bonus_gold_value", gold=buff_gold), "#f0a800"),
            (tr("guild_stats_bonus_damage"), tr("guild_stats_bonus_damage_value", damage=buff_damage), "#e05050"),
            (tr("guild_stats_bonus_crit"), tr("guild_stats_bonus_crit_value", crit=crit_chance), "#a97fff"),
        ]

        for i, (title, value, color) in enumerate(cards):
            card = self._stat_card(title, value, color)
            grid.addWidget(card, i // 3, i % 3)

        exp_card = _card()
        exp_layout = QVBoxLayout(exp_card)
        exp_layout.setContentsMargins(12, 10, 12, 10)
        exp_layout.addWidget(_lbl(tr("guild_exp_progress", exp=exp, need=need), size=12))
        pb = QProgressBar()
        pb.setMaximum(need)
        pb.setValue(int(exp))
        pb.setMinimumHeight(16)
        pb.setStyleSheet("QProgressBar::chunk { background: #80c000; }")
        exp_layout.addWidget(pb)
        grid.addWidget(exp_card, len(cards)//3 + 1, 0, 1, 3)

        return w

    def _stat_card(self, title: str, value: str, color: str) -> QFrame:
        card = _card()
        card.setMinimumHeight(70)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color:{color}; font-size:18px; font-weight:bold;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card

    def _make_members_section(self, guild: dict, members: list, user: dict) -> QGroupBox:
        group = QGroupBox(tr("guild_members", count=len(members)))
        layout = QGridLayout(group)
        layout.setSpacing(10)

        leader = None
        regular = []
        for m in members:
            if m["id"] == guild.get("leader_id"):
                leader = m
            else:
                regular.append(m)

        row = 0
        if leader:
            leader_card = self._make_member_card(leader, user, guild, is_leader=True)
            layout.addWidget(leader_card, row, 0, 1, 2)
            row += 1

        for i, m in enumerate(regular):
            card = self._make_member_card(m, user, guild, is_leader=False)
            layout.addWidget(card, row + i // 4, i % 4)
        return group

    def _make_member_card(self, member: dict, current_user: dict, guild: dict, is_leader: bool) -> QFrame:
        f = _card()
        f.setMinimumWidth(120)
        f.setMaximumHeight(130)
        f.setStyleSheet(
            f"QFrame#card {{ background:{_T('panel')}; "
            f"border:1px solid {'#f0a800' if is_leader else _T('border')}; "
            f"border-radius:6px; }}"
        )
        layout = QVBoxLayout(f)
        layout.setContentsMargins(6, 5, 6, 5)
        layout.setSpacing(2)

        top = QHBoxLayout()
        avatar = QLabel(member.get('avatar_emoji', '⚔️'))
        avatar.setFont(QFont("Segoe UI", 18))
        top.addWidget(avatar)
        name = QLabel(member['display_name'])
        name.setStyleSheet(f"font-size:12px; font-weight:bold; color:{_T('text')};")
        top.addWidget(name, 1)
        if is_leader:
            crown = QLabel("👑")
            crown.setStyleSheet("font-size:14px;")
            top.addWidget(crown)
        layout.addLayout(top)

        level_label = QLabel(tr("level_abbr", level=member['level']))
        level_label.setStyleSheet(f"color:{_T('muted')}; font-size:10px;")
        layout.addWidget(level_label)

        hp_pb = QProgressBar()
        hp_pb.setMaximum(int(member['max_hp']))
        hp_pb.setValue(int(member['hp']))
        hp_pb.setMinimumHeight(6)
        hp_pb.setTextVisible(False)
        hp_pb.setStyleSheet(
            f"QProgressBar::chunk {{ background:{'#7bbf3e' if member['hp'] > 0 else '#e05050'}; }}"
        )
        layout.addWidget(hp_pb)

        if current_user["id"] == guild.get("leader_id") and member["id"] != current_user["id"]:
            btn_row = QHBoxLayout()
            btn_row.setSpacing(4)
            kick_btn = _btn(tr("guild_kick"), "danger", h=24)
            kick_btn.setMinimumWidth(45)
            kick_btn.clicked.connect(lambda _, uid=member["id"]: self._kick_member(uid))
            transfer_btn = _btn(tr("guild_transfer"), "gold", h=24)
            transfer_btn.setMinimumWidth(60)
            transfer_btn.clicked.connect(lambda _, uid=member["id"]: self._transfer_leadership(uid))
            btn_row.addWidget(kick_btn)
            btn_row.addWidget(transfer_btn)
            layout.addLayout(btn_row)

        return f

    def _make_boss_section(self, boss: dict, guild: dict, user: dict) -> QGroupBox:
        group = QGroupBox(tr("guild_boss_battle"))
        layout = QVBoxLayout(group)

        if boss:
            tier_color = db.BOSS_TIER_COLOR.get(boss.get('boss_tier', 'normal'), '#f0a800')
            title = QLabel(tr("boss_title_format", icon=boss['boss_icon'], name=boss['boss_name'], tier=boss.get('boss_tier', '?').upper()))
            title.setStyleSheet(f"font-size:15px; font-weight:bold; color:{tier_color};")
            layout.addWidget(title)

            hp_label = QLabel(tr("guild_boss_hp", hp=boss['boss_hp'], max_hp=boss['boss_max_hp']))
            hp_label.setStyleSheet(f"color:{_T('text')};")
            layout.addWidget(hp_label)

            pb = QProgressBar()
            pb.setMaximum(int(boss['boss_max_hp']))
            pb.setValue(int(boss['boss_hp']))
            pb.setMinimumHeight(20)
            pb.setStyleSheet(f"QProgressBar::chunk {{ background:{tier_color}; border-radius:6px; }}")
            layout.addWidget(pb)

            dmg_bonus = user.get('boss_damage_bonus', 0)
            atk_info = QLabel(tr("guild_boss_atk_info", atk=boss['boss_attack'], bonus=dmg_bonus, total=25+dmg_bonus))
            atk_info.setStyleSheet(f"color:{_T('muted')}; font-size:12px;")
            layout.addWidget(atk_info)

            # Info ultimate
            cls = user.get("avatar_class", "warrior")
            ult_name = tr(f"boss_ultimate_name_{cls}")
            ult_label = QLabel(tr("raid_ultimate_label", name=ult_name))
            ult_label.setStyleSheet(f"color:{_T('accent')}; font-weight:bold;")
            layout.addWidget(ult_label)

            if user["hp"] <= 0:
                warn = QLabel(tr("guild_hp_zero"))
                warn.setWordWrap(True)
                warn.setStyleSheet("color:#e05050; font-weight:bold;")
                layout.addWidget(warn)
                heal_btn = _btn(tr("guild_quick_heal"), "gold", self._quick_heal, 40)
                layout.addWidget(heal_btn)
            else:
                # ── Tombol aksi baru (Light, Heavy, Block, Ultimate) ──
                action_layout = QGridLayout()
                action_layout.setSpacing(10)
                action_layout.setContentsMargins(0, 10, 0, 0)

                # Light Attack
                light_btn = _btn(tr("boss_action_light_label"), slot=lambda: self._perform_action("light"), h=44)
                light_btn.setToolTip(tr("boss_action_light_tip"))
                action_layout.addWidget(light_btn, 0, 0)

                # Heavy Attack (15 MP)
                heavy_btn = _btn(tr("boss_action_heavy_label"), slot=lambda: self._perform_action("heavy"), h=44)
                heavy_btn.setToolTip(tr("boss_action_heavy_tip"))
                action_layout.addWidget(heavy_btn, 0, 1)

                # Block
                block_btn = _btn(tr("boss_action_block_label"), slot=lambda: self._perform_action("block"), h=44)
                block_btn.setToolTip(tr("boss_action_block_tip"))
                action_layout.addWidget(block_btn, 1, 0)

                # Ultimate (50 MP)
                ultimate_btn = _btn(tr("boss_action_ultimate_label"), slot=lambda: self._perform_action("ultimate"), h=44)
                ultimate_btn.setToolTip(tr("boss_action_ultimate_tip"))
                action_layout.addWidget(ultimate_btn, 1, 1)

                layout.addLayout(action_layout)
        else:
            layout.addWidget(_lbl(tr("guild_boss_none"), "sub", 12))
            self._boss_selector(layout, guild, user)

        return group

    def _boss_selector(self, lay: QVBoxLayout, guild: dict, user: dict):
        tier_row = QHBoxLayout()
        tier_row.addWidget(_lbl(tr("guild_boss_filter"), size=12))
        self._tier_cb = _combo([(tr("guild_boss_all"), "all")] + [(t.title(), t) for t in db.BOSS_TIER_ORDER])
        self._tier_cb.currentIndexChanged.connect(lambda: self._fill_boss_cb(user["level"]) or self._update_boss_info())
        tier_row.addWidget(self._tier_cb)
        tier_row.addStretch()
        lay.addLayout(tier_row)

        self._boss_cb = QComboBox()
        self._boss_cb.setMinimumHeight(42)
        self._boss_info = QLabel("")
        self._boss_info.setWordWrap(True)
        self._boss_info.setTextFormat(Qt.TextFormat.RichText)

        self._fill_boss_cb(user["level"])
        self._boss_cb.currentIndexChanged.connect(self._update_boss_info)
        lay.addWidget(self._boss_cb)
        lay.addWidget(self._boss_info)

        is_leader = (user["id"] == guild.get("leader_id"))
        start_btn = _btn(tr("guild_start_boss"), "danger" if is_leader else "flat", h=44)
        if is_leader:
            start_btn.clicked.connect(self._start_boss)
        else:
            start_btn.setEnabled(False)
            start_btn.setText(tr("guild_only_leader"))
        lay.addWidget(start_btn)

        # Tambahkan info spyglass jika dimiliki
        u = AppState.user()
        if u.get("has_spyglass", 0):
            info = QLabel(tr("guild_spyglass_active"))
            info.setStyleSheet(f"color:{_T('accent')}; font-size:11px; font-style:italic;")
            lay.addWidget(info)
            # Tampilkan boss stats lebih detail
            if self._boss_cb and self._boss_cb.count() > 0:
                self._boss_info.setText(
                    self._boss_info.text() + "\n🔭 " + tr("guild_spyglass_detail")
                )

    def _make_actions(self, user: dict, guild: dict) -> QWidget:
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)

        skill = db.CLASS_SKILLS.get(user.get("avatar_class", "warrior"), {})
        skill_text = tr("guild_skill_info",
                        mp=user['mp'], max_mp=user['max_mp'],
                        skill_icon=skill.get('icon', '❓'),
                        skill_name=skill.get('name', 'Unknown'),
                        skill_cost=skill.get('mp_cost', 0))
        skill_label = QLabel(skill_text)
        skill_label.setStyleSheet(f"color:{_T('text')}; font-size:12px;")
        layout.addWidget(skill_label, 1)

        skill_btn = _btn(tr("guild_use_skill_with_icon", icon=skill.get('icon', '⚡')), "diamond", self._skill, 36)
        skill_btn.setMinimumWidth(140)
        layout.addWidget(skill_btn)

        return w

    def _add_requests_and_invites(self, parent_layout: QVBoxLayout, guild: dict, user: dict):
        invites = db.get_guild_invites(self.user_id)
        if invites:
            invite_group = QGroupBox(tr("guild_invites"))
            vlay = QVBoxLayout(invite_group)
            for inv in invites:
                row = QHBoxLayout()
                row.addWidget(QLabel(tr("guild_invite_from", name=inv['guild_name'])))
                accept_btn = _btn(tr("guild_accept"), h=28)
                accept_btn.clicked.connect(lambda _, iid=inv["id"]: self._accept_invite(iid))
                reject_btn = _btn(tr("guild_reject"), "danger", h=28)
                reject_btn.clicked.connect(lambda _, iid=inv["id"]: self._reject_invite(iid))
                row.addWidget(accept_btn)
                row.addWidget(reject_btn)
                vlay.addLayout(row)
            parent_layout.addWidget(invite_group)

        if user["id"] == guild.get("leader_id"):
            requests = db.get_guild_requests(guild["id"])
            if requests:
                req_group = QGroupBox(tr("guild_join_requests"))
                vlay = QVBoxLayout(req_group)
                for req in requests:
                    row = QHBoxLayout()
                    row.addWidget(QLabel(tr("guild_join_request_format", name=req['display_name'], username=req['username'])))
                    accept_btn = _btn(tr("guild_accept"), h=28)
                    accept_btn.clicked.connect(lambda _, rid=req["id"]: self._accept_join(rid))
                    reject_btn = _btn(tr("guild_reject"), "danger", h=28)
                    reject_btn.clicked.connect(lambda _, rid=req["id"]: self._reject_join(rid))
                    row.addWidget(accept_btn)
                    row.addWidget(reject_btn)
                    vlay.addLayout(row)
                parent_layout.addWidget(req_group)

        conn = db.get_conn()
        transfers = conn.execute(
            "SELECT * FROM guild_leader_transfers WHERE guild_id=? AND status='pending'",
            (guild["id"],)
        ).fetchall()
        conn.close()
        if transfers:
            trans_group = QGroupBox(tr("guild_leader_inherit_box"))
            vlay = QVBoxLayout(trans_group)
            for t in transfers:
                row = QHBoxLayout()
                row.addWidget(QLabel(tr("guild_leader_inherit_msg")))
                accept_btn = _btn(tr("guild_accept"), h=28)
                accept_btn.clicked.connect(lambda _, tid=t["id"]: self._accept_leader(tid))
                row.addWidget(accept_btn)
                vlay.addLayout(row)
            parent_layout.addWidget(trans_group)

    # ---------- LOAD ----------
    def load(self):
        if not AppState.user_id:
            return
        if AppState.user().get("is_admin", 0):
            self._clear()
            msg = QLabel(tr("guild_admin_warning"))
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(f"color:{_T('muted')}; font-size:14px; padding:40px;")
            self._root.addWidget(msg)
            return
        self._clear()
        u = AppState.user()
        gid = u.get("guild_id")
        if not gid:
            self._no_guild()
            return

        data = db.get_guild(gid)
        guild = data.get("guild", {})
        members = data.get("members", [])
        boss = data.get("boss")

        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setSpacing(12)

        dashboard_layout.addWidget(self._make_header(guild, u))
        dashboard_layout.addWidget(self._make_stats(guild, members))
        dashboard_layout.addWidget(self._make_members_section(guild, members, u))
        dashboard_layout.addWidget(self._make_boss_section(boss, guild, u))
        dashboard_layout.addWidget(self._make_actions(u, guild))
        self._add_requests_and_invites(dashboard_layout, guild, u)

        # Tampilkan hadiah boss yang belum diklaim
        self._show_unclaimed_rewards(dashboard_layout)

        self._root.addWidget(dashboard)
        self._root.addStretch()

    # ---------- ACTION METHODS (tetap dari kode lama, hanya beberapa disesuaikan) ----------
    def _no_guild(self):
        self._root.addWidget(_lbl(tr("guild_no_guild"), "sub", 13))
        self._root.addSpacing(8)

        cg = QGroupBox(tr("guild_create"))
        cl = QVBoxLayout(cg)
        n_in = _input(tr("guild_name"))
        d_in = _input(tr("guild_desc"))
        cl.addWidget(_lbl(tr("dialog_name"), size=12)); cl.addWidget(n_in)
        cl.addWidget(_lbl(tr("guild_desc"), size=12)); cl.addWidget(d_in)
        def _create():
            n = n_in.text().strip()
            if n:
                r = db.create_guild(self.user_id, n, d_in.text())
                SND.notify()
                _show(self, tr("guild_created_title"), r["msg"], "success")
                AppState.refresh()
        cl.addWidget(_btn(tr("guild_create_btn"), "solid", _create, 40))
        self._root.addWidget(cg)

        rg = QGroupBox(tr("guild_request"))
        rl = QVBoxLayout(rg)
        sp = QSpinBox()
        sp.setRange(1, 99999)
        sp.setMinimumHeight(42)
        rl.addWidget(sp)
        def _request():
            r = db.send_guild_request(self.user_id, sp.value())
            if r["ok"]:
                SND.notify()
                _show(self, tr("berhasil_title"), r["msg"], "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r["msg"], "error")
        rl.addWidget(_btn(tr("guild_request_btn"), "solid", _request, 40))
        self._root.addWidget(rg)

    def _show_unclaimed_rewards(self, parent_layout: QVBoxLayout):
        rewards = db.get_unclaimed_boss_rewards(self.user_id)
        if not rewards:
            return
        group = QGroupBox(tr("guild_unclaimed_rewards"))
        vlay = QVBoxLayout(group)
        for r in rewards:
            row = QHBoxLayout()
            row.addWidget(QLabel(tr("guild_reward_format", name=r['boss_name'], xp=r['xp_reward'], gold=r['gold_reward'])))
            claim_btn = _btn(tr("guild_claim"), "solid", h=30)
            claim_btn.clicked.connect(lambda _, rid=r["id"]: self._claim_reward(rid))
            row.addWidget(claim_btn)
            vlay.addLayout(row)
        parent_layout.addWidget(group)

    def _claim_reward(self, reward_id):
        r = db.claim_boss_reward(reward_id, self.user_id)
        if r["ok"]:
            SND.complete()
            if r.get("leveled_up"):
                SND.level_up()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()
        QTimer.singleShot(0, self.load)

    def _open_guild_chat(self):
        if AppState.user().get("is_admin", 0):
            _show(self, tr("info_title"), tr("guild_chat_admin_block"), "warning")
            return
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
        new_desc, ok = QInputDialog.getMultiLineText(self, tr("guild_decs_edit_title"), tr("guild_new_desc"), old_desc)
        if ok and new_desc != old_desc:
            db.update_guild(gid, description=new_desc)
            SND.notify()
            _show(self, tr("berhasil_title"), tr("guild_desc_done"), "success")
            QTimer.singleShot(0, self.load)

    def _leave(self):
        r = db.leave_guild_with_transfer(self.user_id)
        SND.click()
        _show(self, tr("guild_title"), r["msg"])
        AppState.refresh()
        QTimer.singleShot(0, self.load)

    def _kick_member(self, target_id):
        u = AppState.user()
        r = db.kick_guild_member(u.get("guild_id"), u["id"], target_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)

    def _transfer_leadership(self, new_leader_id):
        reply = QMessageBox.question(self, tr("guild_transfer_title"), tr("guild_transfer_confirm_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        u = AppState.user()
        guild_id = u.get("guild_id")
        if not guild_id:
            _show(self, tr("msg_error"), tr("db_guild_leave_not_in"), "error")
            return
        loading = LoadingDialog("Memproses transfer...", self)
        loading.show()
        QApplication.processEvents()
        r = db.transfer_guild_leadership(guild_id, u["id"], new_leader_id)
        loading.accept()
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            AppState.refresh()
            QTimer.singleShot(0, self.load)
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

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
                tr("guild_boss_selector_item", lock=lock, icon=bd['icon'], name=bd['name'], tier=bd['tier'].upper(), hp=bd['hp'], min_level=bd['min_level']),
                bid)
        self._boss_cb.blockSignals(False)

    def _update_boss_info(self):
        """Update info boss di label. Jika tidak punya spyglass, hanya tampilkan nama dan tier."""
        if not isinstance(self._boss_info, QLabel):
            return
        if not self._boss_cb or self._boss_cb.count() == 0:
            return
        bid = self._boss_cb.currentData()
        bd = db.BOSSES.get(bid, {})
        u = AppState.user()
        has_spyglass = u.get("has_spyglass", 0)
        ok = u.get("level", 1) >= bd.get("min_level", 1)
        
        if has_spyglass:
            # Tampilkan detail lengkap dengan HP, ATK, XP, Gold
            tc = db.BOSS_TIER_COLOR.get(bd.get("tier", "normal"), "#f0a800")
            text = tr("guild_boss_info_format",
                color=tc,
                icon=bd.get('icon', '🐉'),
                name=bd.get('name', 'Unknown'),
                tier=bd.get('tier', 'normal').upper(),
                hp=bd.get('hp', 0),
                atk=bd.get('atk', 0),
                xp=bd.get('xp', 0),
                gold=bd.get('gold', 0),
                min_level=bd.get('min_level', 1),
                ok="✅" if ok else "🔒")
            text += f"\n🔭 {tr('guild_spyglass_detail')}"
        else:
            # Tanpa spyglass: hanya nama, tier, dan status level
            tier_color = db.BOSS_TIER_COLOR.get(bd.get("tier", "normal"), "#f0a800")
            text = (f"<span style='color:{tier_color};font-weight:bold;'>"
                    f"{bd.get('icon', '🐉')} {bd.get('name', 'Unknown')} "
                    f"[{bd.get('tier', 'normal').upper()}]</span>\n")
            text += f"Min Level: {bd.get('min_level', 1)}  { '✅' if ok else '🔒' }"
            text += "\n\n🔒 Beli Spyglass di Shop untuk melihat statistik boss!"
        
        self._boss_info.setText(text)

    def _start_boss(self):
        u   = AppState.user()
        bid = self._boss_cb.currentData()
        r = db.start_boss(u.get("guild_id"), bid, u)
        if r["ok"]:
            SND.boss_hit()
            _show(self, tr("boss_appear_title"), r["msg"], "warning")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()

    def _attack(self):
        u = AppState.user()
        if u["hp"] <= 0:
            SND.error()
            _show(self, tr("hp_habis_title"), tr("guild_hp_zero_msg"), "error")
            return
        r = db.attack_boss(self.user_id, u.get("guild_id"), 25)
        if not r.get("ok"):
            SND.error()
            _show(self, tr("guild_cant_attack"), r["msg"], "error")
            return
        if r.get("defeated"):
            SND.boss_dead()
            _show(self, tr("victory_title"), r["msg"], "success")
            QTimer.singleShot(0, self.load)
        else:
            SND.boss_hit()
            u2 = AppState.user()
            has_spyglass = u2.get("has_spyglass", 0)
            
            user_dmg = r.get("user_damage", 0)
            user_crit = r.get("user_critical", False)
            user_dmg_text = f"⚔️ {user_dmg} DMG" + (" ⚡CRITICAL!" if user_crit else "")
            
            boss_dmg = r.get("boss_damage", 0)
            boss_crit = r.get("boss_critical", False)
            boss_dmg_text = f"💥 {boss_dmg} DMG" + (" ⚡CRITICAL!" if boss_crit else "")
            
            if has_spyglass:
                msg = f"{user_dmg_text}\nBoss HP: {r.get('boss_hp_left',0):.0f}/{r.get('boss_max_hp',0):.0f}\n"
                msg += f"Boss menyerang balik: {boss_dmg_text}\n❤️ HP kamu: {u2['hp']}"
            else:
                actual_damage = r.get('actual_damage', 0)
                msg = f"{user_dmg_text}\n"
                msg += f"Kamu kehilangan {actual_damage} HP!\n❤️ HP kamu: {u2['hp']}"
            
            reduc = u2.get("hp_damage_reduction", 0)
            if reduc > 0 and not has_spyglass:
                msg += f"\n🛡️ Damage reduction: -{reduc:.0f}"
            elif reduc > 0 and has_spyglass:
                msg += f" (reduksi: -{reduc:.0f})"
            
            if r.get("revived"):
                msg += "\n🗿 Totem menyelamatkanmu!"
            
            _show(self, tr("attack_title"), msg, "info" if not r.get("revived") else "success")
        AppState.refresh()

    def _quick_heal(self):
        r = db.use_item(self.user_id, "golden_apple")
        if r.get("ok"):
            SND.complete()
            _show(self, tr("hp_restored_title"), r["msg"], "success")
        else:
            _show(self, tr("no_item_title"), tr("no_golden_apple"), "warning")
        AppState.refresh()

    def _skill(self):
        r = db.use_class_skill(self.user_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("skill_used_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()

    def _accept_invite(self, invite_id):
        r = db.accept_invite(self.user_id, invite_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()
        QTimer.singleShot(0, self.load)

    def _reject_invite(self, invite_id):
        r = db.reject_invite(self.user_id, invite_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("info_title"), r["msg"], "info")
        QTimer.singleShot(0, self.load)

    def _accept_join(self, request_id):
        u = AppState.user()
        r = db.accept_guild_request(u.get("guild_id"), u["id"], request_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)

    def _reject_join(self, request_id):
        u = AppState.user()
        r = db.reject_guild_request(u.get("guild_id"), u["id"], request_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)

    def _accept_leader(self, transfer_id):
        r = db.accept_leader_transfer(self.user_id, transfer_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _perform_action(self, action):
        """Panggil attack_boss dengan action tertentu."""
        u = AppState.user()
        if u["hp"] <= 0:
            SND.error()
            _show(self, tr("hp_habis_title"), tr("guild_hp_zero_msg"), "error")
            return

        # ── CEK MP UNTUK SEMUA AKSI YANG MEMBUTUHKAN MP ──
        if action in ("heavy", "ultimate", "block"):
            if action == "heavy":
                mp_cost = 15
            elif action == "ultimate":
                mp_cost = 50
            else:  # block
                mp_cost = 5
            if u.get("mp", 0) < mp_cost:
                SND.error()
                _show(self, tr("db_mp_insufficient_title"), tr("db_mp_insufficient_msg", cost=mp_cost, mp=u['mp']), "error")
                return

        loading = LoadingDialog(tr("boss_loading"), self)
        loading.show()
        QApplication.processEvents()

        r = db.attack_boss(self.user_id, u.get("guild_id"), action)
        loading.accept()

        if not r.get("ok"):
            SND.error()
            _show(self, tr("guild_cant_attack"), r.get("msg", "Error"), "error")
            return

        if r.get("defeated"):
            SND.boss_dead()
            msg = r.get("msg", "Boss defeated!")
            if r.get("extra_effect"):
                msg += "\n" + r["extra_effect"]
            _show(self, tr("victory_title"), msg, "success")
            QTimer.singleShot(0, self.load)
            AppState.refresh()
            return

        # Tampilkan hasil
        SND.boss_hit()
        u2 = AppState.user()
        has_spyglass = u2.get("has_spyglass", 0)

        user_dmg = r.get("user_damage", 0)
        user_crit = r.get("user_critical", False)
        user_dmg_text = f"⚔️ {user_dmg} DMG" + (" " + tr("boss_critical_mark") if user_crit else "")

        # BLOCK – ditangani terpisah
        if action == "block":
            reduction = r.get("block_reduction", 0)
            msg = tr("boss_block_result", reduction=reduction)
            _show(self, tr("boss_block_title"), msg, "info")
            QTimer.singleShot(0, self.load)
            AppState.refresh()
            return

        # ── BUAT PESAN SERANGAN ──
        if has_spyglass:
            boss_dmg = r.get("boss_damage", 0)
            boss_crit = r.get("boss_critical", False)
            boss_dmg_text = tr("boss_damage_text", dmg=boss_dmg) + (" " + tr("boss_critical_mark") if boss_crit else "")
            msg = tr("boss_attack_spyglass",
                    user_dmg=user_dmg,
                    boss_hp_left=r.get('boss_hp_left', 0),
                    boss_max_hp=r.get('boss_max_hp', 0),
                    boss_dmg_text=boss_dmg_text,
                    user_hp=u2['hp'])
        else:
            actual_damage = r.get('actual_damage', 0)
            msg = tr("boss_attack_no_spyglass",
                    user_dmg=user_dmg,
                    actual_damage=actual_damage,
                    user_hp=u2['hp'])

        # ── TAMBAHKAN INFORMASI TAMBAHAN ──
        if r.get("block_reduction", 0) > 0:
            msg += "\n" + tr("boss_block_active_info", reduction=r['block_reduction'])

        reduc = u2.get("hp_damage_reduction", 0)
        if reduc > 0:
            if has_spyglass:
                msg += " " + tr("boss_reduction_info", reduction=reduc)
            else:
                msg += "\n" + tr("boss_reduction_info", reduction=reduc)

        if r.get("shield_used"):
            msg += "\n" + tr("boss_shield_used")

        if r.get("revived"):
            msg += "\n" + tr("attack_totem_revive")

        # ── EFFECT ULTIMATE ──
        if r.get("action") == "ultimate" and r.get("extra_effect"):
            msg += "\n" + r["extra_effect"]

        _show(self, tr("attack_title"), msg, "info" if not r.get("revived") else "success")
        AppState.refresh()
        QTimer.singleShot(0, self.load)

    def _show_team_selection(self):
        """Dialog untuk memilih anggota tim raid (maks 5 termasuk leader)."""
        u = AppState.user()
        guild_id = u.get("guild_id")
        if not guild_id:
            return
        data = db.get_guild(guild_id)
        members = data.get("members", [])
        # Leader otomatis masuk
        leader = next((m for m in members if m["id"] == u["id"]), None)
        if not leader:
            return
        
        # Pilihan boss
        bid = self._boss_cb.currentData()
        if not bid:
            _show(self, tr("msg_error"), "Pilih boss terlebih dahulu!", "error")
            return
        boss = db.BOSSES.get(bid, {})
        min_lvl = boss.get("min_level", 1)
        max_lvl = boss.get("max_level", 999)
        
        # Tampilkan dialog dengan checkbox
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("raid_team_selection"))
        dlg.setMinimumSize(400, 300)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(f"Pilih anggota tim (maks 4 anggota + leader).\nMin level: {min_lvl}, Max level: {max_lvl}"))
        
        checkboxes = []
        for m in members:
            if m["id"] == u["id"]:
                continue
            # Filter level
            if m["level"] < min_lvl or m["level"] > max_lvl:
                continue
            cb = QCheckBox(f"{m['display_name']} (Lv.{m['level']})")
            cb.setChecked(False)
            layout.addWidget(cb)
            checkboxes.append((cb, m["id"]))
        
        # Tombol ok
        btn_ok = _btn(tr("raid_start_btn"), "solid", dlg.accept)
        layout.addWidget(btn_ok)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        
        # Kumpulkan yang dipilih
        selected = [u["id"]]  # leader selalu masuk
        for cb, uid in checkboxes:
            if cb.isChecked():
                selected.append(uid)
                if len(selected) >= 5:
                    break
        self.selected_team = selected
        # Mulai boss dengan tim ini
        self._start_boss_with_team()

    def _start_boss_with_team(self):
        bid = self._boss_cb.currentData()
        if not bid:
            _show(self, tr("msg_error"), tr("raid_select_boss_first"), "error")
            return
        
        # Refresh user data
        u = AppState.user()
        if not u or not isinstance(u, dict) or not u.get("id"):
            # Coba refresh dari database langsung
            uid = AppState.user_id
            if uid:
                u = db.get_user(uid)
            if not u or not isinstance(u, dict):
                _show(self, tr("msg_error"), "Data user tidak valid.", "error")
                return
        
        uid = u.get("id")
        if not uid:
            _show(self, tr("msg_error"), "ID user tidak ditemukan.", "error")
            return
        guild_id = u.get("guild_id")
        if not guild_id:
            _show(self, tr("msg_error"), "Kamu tidak berada di guild.", "error")
            return
        
        if not self.selected_team:
            self.selected_team = [uid]
        elif uid not in self.selected_team:
            self.selected_team.insert(0, uid)
        self.selected_team = self.selected_team[:5]
        
        r = db.start_boss(guild_id, bid, u, self.selected_team)
        if r["ok"]:
            SND.boss_hit()
            _show(self, tr("boss_appear_title"), r["msg"], "warning")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        AppState.refresh()
        QTimer.singleShot(0, self.load)

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)
        
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
        self.cache = {"data": None, "timestamp": 0}
        self.cache_lifetime = 30   # 30 detik
        AppState.register(self.load)
        self.load()

    def _convert_currency(self, amount_idr):
        """Konversi dari IDR ke mata uang user"""
        curr = db.get_user_currency(self.user_id)
        return db.convert_from_idr(amount_idr, curr)

    def _currency_symbol(self):
        curr = db.get_user_currency(self.user_id)
        return {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(curr, "Rp")

    def _clear(self):
        while self._root.count():
            i = self._root.takeAt(0)
            if i.widget():
                i.widget().deleteLater()

    def load(self):
        if not AppState.user_id:
            return
        
        import time
        now = time.time()
        
        # Cek cache
        if self.cache.get("data") is not None and (now - self.cache["timestamp"]) < self.cache_lifetime:
            # Gunakan data dari cache
            data = self.cache["data"]
            s = data["s"]
            u = data["u"]
            health = data["health"]
            ss = data["ss"]
            eco_summary = data["eco_summary"]
            eco_count = data["eco_count"]
            food_stats = data["food_stats"]
            weekly_cal = data["weekly_cal"]
            health_logs = data["health_logs"]
            eco_weekly = data["eco_weekly"]
        else:
            # Ambil data baru dari database
            s = db.get_stats(self.user_id)
            u = s["user"]
            health = db.get_health_summary(self.user_id)
            ss = db.get_sport_stats(self.user_id)
            eco_summary = db.get_economy_summary(self.user_id)
            eco_count = db.get_economy_count(self.user_id)
            food_stats = db.get_food_summary_stats(self.user_id)
            weekly_cal = db.get_weekly_calories(self.user_id)
            health_logs = db.get_health_logs(self.user_id, days=7)
            eco_weekly = db.get_economy_weekly(self.user_id)
            
            # Simpan ke cache
            self.cache["data"] = {
                "s": s, "u": u, "health": health, "ss": ss,
                "eco_summary": eco_summary, "eco_count": eco_count,
                "food_stats": food_stats, "weekly_cal": weekly_cal,
                "health_logs": health_logs, "eco_weekly": eco_weekly
            }
            self.cache["timestamp"] = now
            data = self.cache["data"]
        
        self._clear()
        self._root.addWidget(_lbl(tr("stats_title"), "section", 14, True))
        self._root.addWidget(_sep())
        export_btn = _btn(tr("stats_export"), "solid", self._export_data)
        self._root.addWidget(export_btn)
        self._root.addWidget(_sep())

        s = db.get_stats(self.user_id)
        u = s["user"]
        health = db.get_health_summary(self.user_id)
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
            (tr("stats_level"), str(u["level"]), "#80c000"),
            (tr("stats_max_streak"), tr("stats_streak_value", count=s['max_streak']), "#f0a800"),
            (tr("stats_habit_today"), tr("stats_habit_today_value", done=s['habits_done_today'], total=s['habits_total']), _T("light")),
            (tr("stats_daily_today"), tr("stats_daily_today_value", done=s['dailies_done_today'], total=s['dailies_total']), "#4da6ff"),
            (tr("stats_quest_done"), tr("stats_quest_done_value", done=s['todos_done'], total=s['todos_total']), "#a97fff"),
            (tr("stats_boss_killed"), tr("stats_boss_killed_value", count=s["bosses_killed"]), "#e05050"),
            (tr("stats_total_gold"), tr("stats_total_gold_value", gold=u.get('total_gold_earned',0)), "#f0a800"),
            (tr("stats_total_xp"), tr("stats_total_xp_value", xp=u.get('total_xp_earned',0)), "#80c000"),
            (tr("stats_items"), tr("stats_items_value", count=s["inv_count"]), "#4da6ff"),
            (tr("stats_pets"), tr("stats_pets_value", count=s["pet_count"]), "#a97fff"),
            (tr("stats_hp"), tr("stats_hp_value", hp=u['hp'], max_hp=u['max_hp']), "#e05050"),
            (tr("stats_mp"), tr("stats_mp_value", mp=u['mp'], max_mp=u['max_mp']), "#4da6ff"),
            (tr("stats_avg_steps"), tr("stats_avg_steps_value", steps=health['avg_steps']), "#80c000"),
            (tr("stats_avg_sleep"), tr("stats_avg_sleep_value", sleep=health['avg_sleep']), "#4da6ff"),
            (tr("stats_avg_water"), tr("stats_avg_water_value", water=health['avg_water']), "#4da6ff"),
            (tr("stats_avg_weight"), tr("stats_avg_weight_value", weight=health['avg_weight']), "#f0a800"),
            (tr("stats_avg_hr"), tr("stats_avg_hr_value", hr=health['avg_hr']), "#e05050"),
            (tr("stats_days_recorded"), tr("stats_days_recorded_value", days=health['days_recorded']), "#a97fff"),
            (tr("stats_sport_level"), tr("stats_sport_level_value", level=ss["sport_level"]), "#f0a800"),
            (tr("stats_total_sport_pts"), tr("stats_total_sport_pts_value", points=ss["total_sport_points_earned"]), "#f0a800"),
            (tr("stats_sport_today"), tr("stats_sport_today_value", done=ss['done_sport_today'], total=ss['total_sport']), "#4dd9e0"),
            (tr("stats_sport_streak"), tr("stats_sport_streak_value", streak=ss['max_sport_streak']), "#ff8c42"),
        ]
        # Konversi nilai ekonomi ke mata uang user
        user_curr = db.get_user_currency(self.user_id)
        income_conv = db.convert_from_idr(eco_summary['total_income'], user_curr)
        expense_conv = db.convert_from_idr(eco_summary['total_expense'], user_curr)
        balance_conv = db.convert_from_idr(eco_summary['balance'], user_curr)
        symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")

        data.extend([
            (tr("economy_total_income"), f"{symbol} {income_conv:,.0f}", "#80c000"),
            (tr("economy_total_expense"), f"{symbol} {expense_conv:,.0f}", "#e05050"),
            (tr("economy_balance"), f"{symbol} {balance_conv:,.0f}", "#4da6ff"),
            (tr("stats_total_transactions"), str(eco_count), "#f0a800"),
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
            wg = QGroupBox(tr("stats_weekly_xp"))
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
                pb.setMinimumHeight(22)
                rl.addWidget(pb, 1)
                wl.addLayout(rl)
            il.addWidget(wg)

        # ── Economy weekly dengan mata uang user ─────────────────────────────────
        eco_weekly = db.get_economy_weekly(self.user_id)
        if eco_weekly:
            eco_group = QGroupBox(tr("stats_weekly_economy"))
            eco_layout = QVBoxLayout(eco_group)
            
            # Dapatkan mata uang user
            user_curr = db.get_user_currency(self.user_id)
            symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
            
            # Konversi semua nilai ke mata uang user
            conv_weekly = []
            max_income = 0
            max_expense = 0
            for row in eco_weekly:
                inc_usr = self._convert_currency(row.get("income", 0))
                exp_usr = self._convert_currency(row.get("expense", 0))
                conv_weekly.append({
                    "day": row["day"],
                    "income": inc_usr,
                    "expense": exp_usr
                })
                if inc_usr > max_income: max_income = inc_usr
                if exp_usr > max_expense: max_expense = exp_usr
            
            max_val = max(max_income, max_expense) or 1
            max_val = int(max_val) + 1
            # Batasi overflow Qt
            if max_val > 2147483647:
                max_val = 2147483647
            
            for row in conv_weekly:
                day = row["day"][5:]  # MM-DD
                inc = row["income"]
                exp = row["expense"]
                row_layout = QHBoxLayout()
                row_layout.addWidget(QLabel(day, minimumWidth=50))
                
                inc_pb = QProgressBar()
                inc_pb.setMaximum(max_val)
                inc_val = int(inc) if inc <= max_val else max_val
                inc_pb.setValue(inc_val)
                inc_pb.setFormat(f"💚 +{symbol} {inc:,.0f}")
                inc_pb.setStyleSheet("QProgressBar::chunk { background: #80c000; }")
                row_layout.addWidget(inc_pb, 2)
                
                exp_pb = QProgressBar()
                exp_pb.setMaximum(max_val)
                exp_val = int(exp) if exp <= max_val else max_val
                exp_pb.setValue(exp_val)
                exp_pb.setFormat(f"❤️ -{symbol} {exp:,.0f}")
                exp_pb.setStyleSheet("QProgressBar::chunk { background: #e05050; }")
                row_layout.addWidget(exp_pb, 2)
                
                eco_layout.addLayout(row_layout)
            il.addWidget(eco_group)

        # ── Health Progress Chart (7 hari) ──────────────────────────────────
        if EXPORT_IMPORTS_OK:
            try:
                import matplotlib.pyplot as plt
                from io import BytesIO
                from PyQt6.QtGui import QPixmap
                health_logs = db.get_health_logs(self.user_id, days=7)
                if health_logs:
                    health_chart_group = QGroupBox(tr("stats_health_7days"))
                    health_chart_layout = QVBoxLayout(health_chart_group)
                    # Siapkan data 7 hari terakhir (urutan hari)
                    from datetime import date, timedelta
                    today = date.today()
                    days = []
                    steps_data = []
                    sleep_data = []
                    water_data = []
                    for i in range(7):
                        d = (today - timedelta(days=6-i)).isoformat()
                        days.append(d[5:])  # MM-DD
                        log = next((l for l in health_logs if l['log_date'] == d), None)
                        if log:
                            steps_data.append(log['steps'] / 1000)           # ribuan langkah
                            sleep_data.append(log['sleep_hours'])
                            water_data.append(log.get('water_ml', 0) / 1000) # liter
                        else:
                            steps_data.append(0)
                            sleep_data.append(0)
                            water_data.append(0)
                    # Buat figure dengan gaya yang sama seperti FoodPage
                    fig, ax = plt.subplots(figsize=(6, 3))
                    _lang = AppState.get_language()
                    ax.plot(days, steps_data, marker='o', color='#80c000', linewidth=2, label='Langkah (ribu)' if _lang=="id" else 'Steps (k)')
                    ax.plot(days, sleep_data, marker='s', color='#4da6ff', linewidth=2, label='Tidur (jam)' if _lang=="id" else 'Sleep (h)')
                    ax.plot(days, water_data, marker='^', color='#f4a261', linewidth=2, label='Air (L)' if _lang=="id" else 'Water (L)')
                    ax.set_ylabel('Nilai' if _lang=="id" else 'Value')
                    ax.set_title(tr("health_progress_chart"))
                    ax.set_facecolor('#2d2d2d')
                    fig.patch.set_facecolor('#2d2d2d')
                    ax.tick_params(colors='#e8e8e8')
                    ax.xaxis.label.set_color('#e8e8e8')
                    ax.yaxis.label.set_color('#e8e8e8')
                    ax.title.set_color('#7bbf3e')
                    plt.setp(ax.get_xticklabels(), rotation=20, ha='right')
                    ax.legend(facecolor='#2d2d2d', edgecolor='#444', labelcolor='#e8e8e8', fontsize=8)
                    ax.grid(axis='y', color='#444', alpha=0.5)
                    fig.subplots_adjust(bottom=0.2)
                    # Simpan ke buffer
                    buf = BytesIO()
                    plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
                    buf.seek(0)
                    plt.close(fig)
                    # Tampilkan di QLabel
                    pixmap = QPixmap()
                    pixmap.loadFromData(buf.read())
                    chart_label = QLabel()
                    chart_label.setPixmap(pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation))
                    chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    health_chart_layout.addWidget(chart_label)
                    il.addWidget(health_chart_group)
            except Exception as e:
                print(f"Health chart error: {e}")

        # ── Food & Water Stats ──────────────────────────────────────────────
        food_stats = db.get_food_summary_stats(self.user_id)
        fg = QGroupBox(tr("stats_nutrition"))
        fl = QVBoxLayout(fg)
        fl.addWidget(_lbl(tr("stats_avg_calories", cal=f"{food_stats['avg_calories']:.0f}"), size=12))
        fl.addWidget(_lbl(tr("stats_total_calories", cal=f"{food_stats['total_calories_30d']:.0f}"), size=12))
        fl.addWidget(_lbl(tr("stats_avg_water_ml", water=f"{food_stats['avg_water']:.0f}"), size=12))
        fl.addWidget(_lbl(tr("stats_total_water", water=f"{food_stats['total_water_30d']:.0f}"), size=12))
        fl.addWidget(_lbl(tr("stats_days_tracked", days=food_stats['days_tracked']), size=12))
        il.addWidget(fg)

        # Grafik kalori mingguan (opsional)
        weekly_cal = db.get_weekly_calories(self.user_id)
        if weekly_cal:
            wg = QGroupBox(tr("stats_calories_7days"))
            wl = QVBoxLayout(wg)
            max_cal = max(weekly_cal.values()) or 1
            for day, cal in weekly_cal.items():
                day_label = day[5:]  # MM-DD
                pb = QProgressBar()
                pb.setMaximum(int(max_cal))
                pb.setValue(int(cal))
                pb.setFormat(f"{cal:.0f} kcal")
                pb.setMinimumHeight(20)
                row = QHBoxLayout()
                row.addWidget(QLabel(day_label, minimumWidth=60))
                row.addWidget(pb, 1)
                wl.addLayout(row)
            il.addWidget(wg)

       # ── Buff summary ──────────────────────────────────────────────────────
        bg = QGroupBox(tr("stats_buff_active"))
        bl = QVBoxLayout(bg)
        lines = db.get_all_active_buffs(self.user_id)
        if not lines:
            lines.append(tr("stats_no_buff", default="Belum ada buff aktif."))
        for lt in lines:
            bl.addWidget(_lbl(lt, size=12))
        il.addWidget(bg)

        # ── Activity log ──────────────────────────────────────────────────────
        lg = QGroupBox(tr("stats_activity_log"))
        ll = QVBoxLayout(lg)
        lw = QListWidget()
        lw.setMinimumHeight(180)
        for entry in s["recent_log"][:15]:
            action_text = tr(f"action_{entry['action']}", default=entry['action'])
            lw.addItem(f"[{entry['created_at'][11:16]}]  {action_text}  —  {entry['detail']}")
        ll.addWidget(lw)
        il.addWidget(lg)
        il.addStretch()
        self._root.addWidget(_scrolled(inner))
        fade_in(inner, 200)

    def _export_data(self):
        from PyQt6.QtWidgets import QFileDialog, QComboBox, QDialogButtonBox, QVBoxLayout, QDialog, QLabel
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("economy_export_title"))
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(tr("economy_export_label")))
        combo = QComboBox()
        combo.addItems([tr("export_csv_option"), "Excel (.xlsx)", "Word (.docx)", "PDF (.pdf)"])
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
            path, _ = QFileDialog.getSaveFileName(self, tr("stats_save_file"), "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_csv(data, path)
        elif fmt == "Excel (.xlsx)":
            filter_str = "Excel Files (*.xlsx)"
            ext = ".xlsx"
            path, _ = QFileDialog.getSaveFileName(self, tr("stats_save_file"), "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_excel(data, path)
        elif fmt == "Word (.docx)":
            filter_str = "Word Files (*.docx)"
            ext = ".docx"
            path, _ = QFileDialog.getSaveFileName(self, tr("stats_save_file"), "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_word(data, path)
        else:  # PDF
            filter_str = "PDF Files (*.pdf)"
            ext = ".pdf"
            path, _ = QFileDialog.getSaveFileName(self, tr("stats_save_file"), "", filter_str)
            if path:
                if not path.endswith(ext): path += ext
                self._export_pdf(data, path)
    
    def _export_csv(self, data, filepath):
        import csv
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([tr("export_section_user")])
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
            writer.writerow([tr("export_section_stats")])
            s = data['stats']
            writer.writerow(["Streak Terpanjang", s['max_streak']])
            writer.writerow(["Total XP Earned", u.get('total_xp_earned',0)])
            writer.writerow(["Total Gold Earned", u.get('total_gold_earned',0)])
            writer.writerow(["Boss Dikalahkan", s['bosses_killed']])
            writer.writerow([])
            writer.writerow([tr("export_section_economy")])
            eco = data['eco_summary']
            user_curr = db.get_user_currency(self.user_id)
            symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
            income_conv = db.convert_from_idr(eco['total_income'], user_curr)
            expense_conv = db.convert_from_idr(eco['total_expense'], user_curr)
            balance_conv = db.convert_from_idr(eco['balance'], user_curr)

            writer.writerow(["Total Pemasukan", f"{symbol} {income_conv:,.0f}"])
            writer.writerow(["Total Pengeluaran", f"{symbol} {expense_conv:,.0f}"])
            writer.writerow(["Saldo", f"{symbol} {balance_conv:,.0f}"])
            writer.writerow([])
            writer.writerow([tr("export_section_habits")])
            writer.writerow([tr("dialog_name"), "Difficulty", "Streak", "Last Done", "Notes"])
            for h in data['habits']:
                writer.writerow([h['name'], h['difficulty'], h['streak'], h['last_done'], h['notes']])
            writer.writerow([])
            writer.writerow([tr("export_section_dailies")])
            writer.writerow([tr("dialog_name"), "Difficulty", "Streak", "Last Done", "Notes"])
            for d in data['dailies']:
                writer.writerow([d['name'], d['difficulty'], d['streak'], d['last_done'], d['notes']])
            writer.writerow([])
            writer.writerow([tr("export_section_quests")	])
            writer.writerow([tr("dialog_name"), "Priority", "Done", "Due Date", "Notes"])
            for t in data['todos']:
                writer.writerow([t['name'], t['priority'], t['done'], t['due_date'], t['notes']])
            writer.writerow([])
            writer.writerow([tr("export_section_sport")])
            writer.writerow([tr("dialog_name"), "Type", "Difficulty", "Streak", "Last Done", "Notes"])
            for a in data['sport_activities']:
                writer.writerow([a['name'], a['sport_type'], a['difficulty'], a['streak'], a['last_done'], a['notes']])
            writer.writerow([])
            writer.writerow([tr("export_section_economy_items")])
            writer.writerow([tr("dialog_name"), "Tipe", "Jumlah", "Kategori", "Tanggal", "Catatan"])
            for ei in data['economy_items']:
                amount_conv = db.convert_from_idr(ei['amount'], user_curr)
                writer.writerow([ei['name'], ei['type'], f"{symbol} {amount_conv:,.0f}", ei['category'], ei['date'], ei['notes']]) 
            writer.writerow([])
            writer.writerow([tr("export_section_health")])
            writer.writerow([tr("export_metric"),tr("export_value")])
            writer.writerow(["Rata-rata Langkah", data['health_summary']['avg_steps']])
            writer.writerow(["Rata-rata Tidur", data['health_summary']['avg_sleep']])
            writer.writerow(["Rata-rata Air", data['health_summary']['avg_water']])
            writer.writerow(["Rata-rata Berat", data['health_summary']['avg_weight']])
            writer.writerow(["Rata-rata Detak Jantung", data['health_summary']['avg_hr']])
            writer.writerow(["Hari Tercatat", data['health_summary']['days_recorded']])
            writer.writerow([])
            writer.writerow([tr("export_section_health_log")])
            writer.writerow(["Tanggal","Langkah","Tidur","Air (ml)","Berat (kg)","HR","Stress","Mood","Catatan"])
            for hl in data['health_logs']:
                writer.writerow([hl['log_date'], hl['steps'], hl['sleep_hours'], hl.get('water_ml',0), hl.get('weight_kg',0), hl.get('resting_hr',0), hl.get('stress_level',''), hl.get('mood',''), hl.get('notes','')])
            writer.writerow([])
            writer.writerow(["=== TASK HISTORY ==="])
            writer.writerow(["Tanggal", "Tipe Task", "Task ID", "Aksi"])
            history = db.get_all_task_history(self.user_id)
            for h in history:
                writer.writerow([h["action_date"], h["task_type"], h["task_id"], h["action"]])
        _show(self, tr("berhasil_title"), f"Data diekspor ke {filepath}", "success")

    def _export_excel(self, data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, tr("msg_error"), tr("export_lib_missing"), "error")
            return
        import tempfile
        
        wb = openpyxl.Workbook()
        # Sheet ringkasan
        ws_summary = wb.active
        ws_summary.title = tr("excel_sheet_summary")
        u = data['user']
        s = data['stats']
        eco = data['eco_summary']
        
        # ← TAMBAHKAN: konversi mata uang untuk nilai ekonomi
        user_curr = db.get_user_currency(self.user_id)
        symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
        income_conv = db.convert_from_idr(eco['total_income'], user_curr)
        expense_conv = db.convert_from_idr(eco['total_expense'], user_curr)
        balance_conv = db.convert_from_idr(eco['balance'], user_curr)
        
        ws_summary.append([tr("word_section_user")])
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
        ws_summary.append([tr("word_section_stats")])
        ws_summary.append(["Streak Terpanjang", s['max_streak']])
        ws_summary.append(["Total XP Earned", u.get('total_xp_earned',0)])
        ws_summary.append(["Total Gold Earned", u.get('total_gold_earned',0)])
        ws_summary.append(["Boss Dikalahkan", s['bosses_killed']])
        ws_summary.append([])
        ws_summary.append([tr("word_section_economy")])
        ws_summary.append(["Total Pemasukan", f"{symbol} {income_conv:,.0f}"])
        ws_summary.append(["Total Pengeluaran", f"{symbol} {expense_conv:,.0f}"])
        ws_summary.append(["Saldo", f"{symbol} {balance_conv:,.0f}"])
        
        # Sheet Kesehatan
        ws_health = wb.create_sheet(tr("excel_sheet_health"))
        ws_health.append([tr("export_metric"),tr("export_value")])
        health = data['health_summary']
        ws_health.append(["Rata-rata Langkah", health['avg_steps']])
        ws_health.append(["Rata-rata Tidur", health['avg_sleep']])
        ws_health.append(["Rata-rata Air", health['avg_water']])
        ws_health.append(["Rata-rata Berat", health['avg_weight']])
        ws_health.append(["Rata-rata Detak Jantung", health['avg_hr']])
        ws_health.append(["Hari Tercatat", health['days_recorded']])

        # Sheet Log Kesehatan
        health_logs = data['health_logs']
        ws_health_log = wb.create_sheet(tr("excel_sheet_health_log"))
        health_headers = ["Tanggal","Langkah","Tidur","Air (ml)","Berat (kg)","HR","Stress","Mood","Catatan"]
        ws_health_log.append(health_headers)
        for hl in health_logs:
            ws_health_log.append([hl['log_date'], hl['steps'], hl['sleep_hours'], hl.get('water_ml',0), hl.get('weight_kg',0), hl.get('resting_hr',0), hl.get('stress_level',''), hl.get('mood',''), hl.get('notes','')])

        # Sheet Nutrisi
        food_data = db.get_food_export_data(self.user_id, days=30)
        ws_nutri = wb.create_sheet(tr("excel_sheet_nutrition"))
        headers = ["Tanggal","Kalori","Protein","Karbo","Lemak","Air (ml)","Kalori Terbakar","Net Kalori"]
        ws_nutri.append(headers)
        for fd in food_data:
            ws_nutri.append([fd['date'], fd['calories'], fd['protein'], fd['carbs'], fd['fat'], fd['water_ml'], fd['calories_burned'], fd['net_calories']])
        for col in ws_nutri.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                try: max_len = max(max_len, len(str(cell.value)))
                except: pass
            ws_nutri.column_dimensions[col_letter].width = min(max_len+2, 20)

        # Chart XP per hari (weekly)
        weekly = s['weekly']
        if weekly:
            ws_chart = wb.create_sheet(tr("excel_sheet_xp_chart"))
            days = [row['day'][5:] for row in weekly]
            xp_vals = [row['xp'] or 0 for row in weekly]
            gold_vals = [row['gold'] or 0 for row in weekly]
            ws_chart.append(["Hari", "XP", "Gold"])
            for d, x, g in zip(days, xp_vals, gold_vals):
                ws_chart.append([d, x, g])
            chart = BarChart()
            chart.title = tr("stats_chart_xp_gold")
            data_ref = Reference(ws_chart, min_col=2, min_row=1, max_row=len(days)+1, max_col=3)
            cats = Reference(ws_chart, min_col=1, min_row=2, max_row=len(days)+1)
            chart.add_data(data_ref, titles_from_data=True)
            chart.set_categories(cats)
            ws_chart.add_chart(chart, "E5")
        
        # Habits, Dailies, Todos, Sport, Economy items sebagai sheet terpisah
        self._add_sheet_from_list(wb, tr("excel_sheet_habits"), data['habits'], ["name","difficulty","streak","last_done","notes"])
        self._add_sheet_from_list(wb, tr("excel_sheet_dailies"), data['dailies'], ["name","difficulty","streak","last_done","notes"])
        self._add_sheet_from_list(wb, tr("excel_sheet_quests"), data['todos'], ["name","priority","done","due_date","notes"])
        self._add_sheet_from_list(wb, tr("excel_sheet_sport"), data['sport_activities'], ["name","sport_type","difficulty","streak","last_done","notes"])
        # Untuk sheet Ekonomi, kita konversi amount ke mata uang user
        self._add_economy_sheet_with_currency(wb, tr("excel_sheet_economy"), data['economy_items'], user_curr)
        
        # Sheet Task History
        history = db.get_all_task_history(self.user_id)
        if history:
            ws_history = wb.create_sheet(tr("excel_sheet_history"))
            headers = [tr("export_history_date"), tr("export_history_type"), tr("export_history_task_id"), tr("export_history_action")]
            ws_history.append(headers)
            for h in history:
                ws_history.append([h["action_date"], h["task_type"], h["task_id"], h["action"]])
            # Atur lebar kolom
            for col in ws_history.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    try:
                        max_len = max(max_len, len(str(cell.value)))
                    except:
                        pass
                ws_history.column_dimensions[col_letter].width = min(max_len+2, 30)

        wb.save(filepath)
        _show(self, tr("berhasil_title"), f"Data diekspor ke {filepath}", "success")
    
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
    
    def _add_economy_sheet_with_currency(self, wb, sheet_name, items, user_curr):
        from openpyxl.utils import get_column_letter
        ws = wb.create_sheet(sheet_name)
        headers = [tr("dialog_name"), "Tipe", "Jumlah", "Kategori", "Tanggal", "Catatan"]
        ws.append(headers)
        symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
        for item in items:
            amount_conv = db.convert_from_idr(item['amount'], user_curr)
            row = [
                item.get('name', ''),
                item.get('type', ''),
                f"{symbol} {amount_conv:,.0f}",
                item.get('category', ''),
                item.get('date', ''),
                item.get('notes', '')
            ]
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
            _show(self, tr("msg_error"), tr("export_lib_missing"), "error")
            return
        import tempfile
        
        doc = Document()
        title = doc.add_heading(tr("word_title_export"), 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        u = data['user']
        doc.add_heading(tr("word_section_user"), level=1)
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
        doc.add_heading(tr("word_section_stats"), level=1)
        doc.add_paragraph(f"Streak Terpanjang: {s['max_streak']} hari")
        doc.add_paragraph(f"Total XP Earned: {u.get('total_xp_earned',0)}")
        doc.add_paragraph(f"Total Gold Earned: {u.get('total_gold_earned',0):.0f}")
        doc.add_paragraph(f"Boss Dikalahkan: {s['bosses_killed']}")
        
        eco = data['eco_summary']
        doc.add_heading(tr("word_section_economy"), level=1)
        # ← TAMBAHKAN konversi mata uang
        user_curr = db.get_user_currency(self.user_id)
        symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
        income_conv = db.convert_from_idr(eco['total_income'], user_curr)
        expense_conv = db.convert_from_idr(eco['total_expense'], user_curr)
        balance_conv = db.convert_from_idr(eco['balance'], user_curr)
        doc.add_paragraph(f"Total Pemasukan: {symbol} {income_conv:,.0f}")
        doc.add_paragraph(f"Total Pengeluaran: {symbol} {expense_conv:,.0f}")
        doc.add_paragraph(f"Saldo: {symbol} {balance_conv:,.0f}")
    
        health = data['health_summary']
        doc.add_heading(tr("word_section_health"), level=1)
        doc.add_paragraph(f"Rata-rata Langkah: {health['avg_steps']}")
        doc.add_paragraph(f"Rata-rata Tidur: {health['avg_sleep']} jam")
        doc.add_paragraph(f"Rata-rata Air: {health['avg_water']} ml")
        doc.add_paragraph(f"Rata-rata Berat: {health['avg_weight']} kg")
        doc.add_paragraph(f"Rata-rata Detak Jantung: {health['avg_hr']} bpm")
        doc.add_paragraph(f"Hari Tercatat: {health['days_recorded']}")
        
        health_logs = data['health_logs']
        if health_logs:
            doc.add_heading("Log Kesehatan 30 Hari", level=2)
            table = doc.add_table(rows=1, cols=9)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = "Tanggal"
            hdr[1].text = "Langkah"
            hdr[2].text = "Tidur"
            hdr[3].text = "Air (ml)"
            hdr[4].text = "Berat (kg)"
            hdr[5].text = "HR"
            hdr[6].text = "Stress"
            hdr[7].text = "Mood"
            hdr[8].text = "Catatan"
            for hl in health_logs:
                row = table.add_row().cells
                row[0].text = hl['log_date']
                row[1].text = str(hl['steps'])
                row[2].text = str(hl['sleep_hours'])
                row[3].text = str(hl.get('water_ml',0))
                row[4].text = str(hl.get('weight_kg',0))
                row[5].text = str(hl.get('resting_hr',0))
                row[6].text = hl.get('stress_level','')
                row[7].text = hl.get('mood','')
                row[8].text = hl.get('notes','')

        food_data = db.get_food_export_data(self.user_id, days=30)
        if food_data:
            doc.add_heading(tr("word_section_nutrition"), level=2)
            table = doc.add_table(rows=1, cols=8)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = "Tanggal"
            hdr[1].text = "Kalori"
            hdr[2].text = "Protein"
            hdr[3].text = "Karbo"
            hdr[4].text = "Lemak"
            hdr[5].text = "Air (ml)"
            hdr[6].text = "Kalori Terbakar"
            hdr[7].text = "Net Kalori"
            for fd in food_data:
                row = table.add_row().cells
                row[0].text = fd['date']
                row[1].text = str(fd['calories'])
                row[2].text = str(fd['protein'])
                row[3].text = str(fd['carbs'])
                row[4].text = str(fd['fat'])
                row[5].text = str(fd['water_ml'])
                row[6].text = str(fd['calories_burned'])
                row[7].text = str(fd['net_calories'])

        weekly = s['weekly']
        if weekly:
            doc.add_heading(tr("word_section_xp_gold"), level=1)
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
        
        self._add_table_to_word(doc, "Habits", data['habits'], [tr("dialog_name"),"Difficulty","Streak","Last Done","Catatan"])
        self._add_table_to_word(doc, "Dailies", data['dailies'], [tr("dialog_name"),"Difficulty","Streak","Last Done","Catatan"])
        self._add_table_to_word(doc, "Quests", data['todos'], [tr("dialog_name"),"Priority","Done","Due Date","Catatan"])
        self._add_table_to_word(doc, "Sport Activities", data['sport_activities'], [tr("dialog_name"),"Type","Difficulty","Streak","Last Done","Catatan"])
        # Task History
        history = db.get_all_task_history(self.user_id)
        if history:
            doc.add_heading(tr("export_section_history"), level=2)
            table = doc.add_table(rows=1, cols=4)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            hdr_cells[0].text = tr("export_history_date")
            hdr_cells[1].text = tr("export_history_type")
            hdr_cells[2].text = tr("export_history_task_id")
            hdr_cells[3].text = tr("export_history_action")
            for h in history:
                row_cells = table.add_row().cells
                row_cells[0].text = h["action_date"]
                row_cells[1].text = h["task_type"]
                row_cells[2].text = str(h["task_id"])
                row_cells[3].text = h["action"]
        if data['economy_items']:
            doc.add_heading(tr("word_table_economy"), level=2)
            table = doc.add_table(rows=1, cols=6)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            headers = [tr("dialog_name"),"Tipe","Jumlah","Kategori","Tanggal","Catatan"]
            for i, h in enumerate(headers):
                hdr_cells[i].text = h
            user_curr = db.get_user_currency(self.user_id)
            symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
            for item in data['economy_items']:
                row_cells = table.add_row().cells
                amount_conv = db.convert_from_idr(item['amount'], user_curr)
                row_cells[0].text = item.get('name', '')
                row_cells[1].text = item.get('type', '')
                row_cells[2].text = f"{symbol} {amount_conv:,.0f}"
                row_cells[3].text = item.get('category', '')
                row_cells[4].text = item.get('date', '')
                row_cells[5].text = item.get('notes', '')
        
        doc.save(filepath)
        _show(self, tr("berhasil_title"), f"Data diekspor ke {filepath}", "success")
    
    def _add_table_to_word(self, doc, title, items, headers):
        if not items:
            return
        doc.add_heading(title, level=2)
        table = doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        for i, h in enumerate(headers):
            hdr_cells[i].text = h
        field_map = {tr("dialog_name"):"name","Difficulty":"difficulty","Streak":"streak",
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
            _show(self, tr("msg_error"), tr("export_lib_missing"), "error")
            return
        import tempfile
        
        doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(name='Title', parent=styles['Title'], alignment=1, fontSize=16)
        story.append(Paragraph(tr("word_title_export"), title_style))
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
        ]
        user_curr = db.get_user_currency(self.user_id)
        symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
        income_conv = db.convert_from_idr(eco['total_income'], user_curr)
        expense_conv = db.convert_from_idr(eco['total_expense'], user_curr)
        balance_conv = db.convert_from_idr(eco['balance'], user_curr)
        summary_data.extend([
            ["Total Pemasukan", f"{symbol} {income_conv:,.0f}"],
            ["Total Pengeluaran", f"{symbol} {expense_conv:,.0f}"],
            ["Saldo", f"{symbol} {balance_conv:,.0f}"],
        ])
        health = data['health_summary']
        summary_data.extend([
            ["Rata-rata Langkah", str(health['avg_steps'])],
            ["Rata-rata Tidur", str(health['avg_sleep']) + " jam"],
            ["Rata-rata Air", str(health['avg_water']) + " ml"],
            ["Rata-rata Berat", str(health['avg_weight']) + " kg"],
            ["Rata-rata Detak Jantung", str(health['avg_hr']) + " bpm"],
            ["Hari Tercatat", str(health['days_recorded'])],
        ])
        # Tabel Nutrisi
        food_data = db.get_food_export_data(self.user_id, days=30)
        if food_data:
            story.append(Paragraph(tr("word_section_nutrition"), styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            nut_data = [["Tanggal","Kalori","Protein","Karbo","Lemak","Air (ml)","Kalori Terbakar","Net Kalori"]]
            for fd in food_data:
                nut_data.append([fd['date'], str(fd['calories']), str(fd['protein']), str(fd['carbs']), str(fd['fat']), str(fd['water_ml']), str(fd['calories_burned']), str(fd['net_calories'])])
            table = Table(nut_data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5a8a2e")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
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
        
        self._add_pdf_table(story, tr("word_table_habits"), data['habits'], [tr("dialog_name"),"Difficulty","Streak","Last Done","Catatan"])
        self._add_pdf_table(story, tr("word_table_dailies"), data['dailies'], [tr("dialog_name"),"Difficulty","Streak","Last Done","Catatan"])
        self._add_pdf_table(story, tr("word_table_quests"), data['todos'], [tr("dialog_name"),"Priority","Done","Due Date","Catatan"])
        self._add_pdf_table(story, tr("word_table_sport"), data['sport_activities'], [tr("dialog_name"),"Type","Difficulty","Streak","Last Done","Catatan"])
        # Task History
        history = db.get_all_task_history(self.user_id)
        if history:
            story.append(Paragraph(tr("export_section_history"), styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            hist_data = [[tr("export_history_date"), tr("export_history_type"), tr("export_history_task_id"), tr("export_history_action")]]
            for h in history:
                hist_data.append([h["action_date"], h["task_type"], str(h["task_id"]), h["action"]])
            hist_table = Table(hist_data, repeatRows=1)
            hist_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5a8a2e")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            story.append(hist_table)
            story.append(Spacer(1, 0.2*inch))
        if data['economy_items']:
            story.append(Paragraph(tr("word_table_economy"), styles['Heading2']))
            story.append(Spacer(1, 0.1*inch))
            # Buat data tabel dengan konversi amount
            user_curr = db.get_user_currency(self.user_id)
            symbol = {"IDR": "Rp", "USD": "$", "EUR": "€"}.get(user_curr, "Rp")
            eco_data = [[tr("dialog_name"),"Tipe","Jumlah","Kategori","Tanggal","Catatan"]]
            for item in data['economy_items']:
                amount_conv = db.convert_from_idr(item['amount'], user_curr)
                eco_data.append([
                    item.get('name',''),
                    item.get('type',''),
                    f"{symbol} {amount_conv:,.0f}",
                    item.get('category',''),
                    item.get('date',''),
                    item.get('notes','')
                ])
            table = Table(eco_data, repeatRows=1)
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
        
        doc.build(story)
        _show(self, tr("berhasil_title"), f"Data diekspor ke {filepath}", "success")
    
    def _add_pdf_table(self, story, title, items, headers):
        if not items:
            return
        styles = getSampleStyleSheet()
        story.append(Paragraph(title, styles['Heading2']))
        story.append(Spacer(1, 0.1*inch))
        data = [headers]
        field_map = {tr("dialog_name"):"name","Difficulty":"difficulty","Streak":"streak",
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
#  Achievement Page - Menampilkan daftar achievement
# ══════════════════════════════════════════════════════════════════════════════
class AchievementPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        
        self.user_id = user_id
        self._build()
        AppState.register(self.load)
    
    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(_lbl(tr("achievement_title"), "section", 14, True))
        layout.addWidget(_sep())

        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("achievement_search"))
        self.search_input.textChanged.connect(self.load)
        self.category_combo = QComboBox()
        # Gunakan data, bukan teks untuk filter
        self.category_combo.addItem(tr("achievement_all"), "all")
        self.category_combo.addItem(tr("achievement_category_level"), "level")
        self.category_combo.addItem(tr("achievement_category_habit"), "habit")
        self.category_combo.addItem(tr("achievement_category_daily"), "daily")
        self.category_combo.addItem(tr("achievement_category_todo"), "todo")
        self.category_combo.addItem(tr("achievement_category_sport"), "sport")
        self.category_combo.addItem(tr("achievement_category_economy"), "economy")
        self.category_combo.addItem(tr("achievement_category_pet"), "pet")
        self.category_combo.addItem(tr("achievement_category_guild"), "guild")
        self.category_combo.addItem(tr("achievement_category_boss"), "boss")
        self.category_combo.addItem(tr("achievement_category_social"), "social")
        self.category_combo.addItem(tr("achievement_category_health"), "health")
        self.category_combo.addItem(tr("achievement_category_nutrition"), "nutrition")
        self.category_combo.addItem(tr("achievement_category_special"), "special")
        self.category_combo.currentIndexChanged.connect(self.load)
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(self.category_combo)
        layout.addWidget(filter_widget)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.grid = QGridLayout(self.container)
        self.grid.setSpacing(12)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for col in range(3):
            self.grid.setColumnStretch(col, 1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.load()

    def load(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        achievements = db.get_user_achievements(self.user_id)
        search_text = self.search_input.text().lower()
        category_data = self.category_combo.currentData()
        if category_data != "all":
            achievements = [a for a in achievements if a["category"] == category_data]
        if search_text:
            achievements = [a for a in achievements if search_text in a["name"].lower() or search_text in a["description"].lower()]

        if not achievements:
            empty = _lbl(tr("achievement_empty"), "sub", 13)
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid.addWidget(empty, 0, 0)
            return

        col = 0
        row = 0
        for ach in achievements:
            card = self._make_achievement_card(ach)
            self.grid.addWidget(card, row, col)
            col += 1
            if col >= 3:
                col = 0
                row += 1
     
    def _make_achievement_card(self, ach: dict) -> QFrame:
        card = _card()
        card.setMinimumWidth(260)
        layout = QVBoxLayout(card)
        layout.setSpacing(1)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Ambil terjemahan untuk nama & deskripsi
        name_key = f"ach_name_{ach['name']}"
        desc_key = f"ach_desc_{ach['name']}"
        # Jika tidak ada terjemahan, gunakan nilai asli
        from translations import TRANSLATIONS, get_text
        name_text = get_text(name_key, AppState.get_language()) if name_key in TRANSLATIONS else ach["name"]
        desc_text = get_text(desc_key, AppState.get_language()) if desc_key in TRANSLATIONS else ach["description"]

        # Header: icon + nama
        header = QHBoxLayout()
        icon = QLabel(ach["icon"])
        icon.setFont(QFont("Segoe UI", 24))
        header.addWidget(icon)
        name = QLabel(name_text)
        name.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
        header.addWidget(name, 1)
        layout.addLayout(header)
        
        # Deskripsi
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        layout.addWidget(desc)
        
        # Progress bar
        progress = ach.get("progress", 0)
        req = ach["requirement_value"]
        percent = min(100, int(progress / req * 100)) if req > 0 else 0
        pb = QProgressBar()
        pb.setMaximum(req)
        pb.setValue(int(min(progress, req)))
        pb.setFormat(tr("achievement_progress_format", progress=int(progress), req=int(req), percent=percent))
        pb.setMinimumHeight(16)
        layout.addWidget(pb)
        
        # Reward info
        reward_text = tr("achievement_reward_format", xp=ach['xp_reward'], gold=ach['gold_reward'])
        reward_lbl = QLabel(reward_text)
        reward_lbl.setStyleSheet(f"color:{_T('accent')}; font-size:10px;")
        layout.addWidget(reward_lbl)
        
        # Status
        unlocked = ach.get("unlocked_at") is not None
        if unlocked:
            status = QLabel(tr("achievement_unlocked"))
            status.setStyleSheet("color:#80c000; font-weight:bold;")
            layout.addWidget(status)
            if not ach.get("claimed", 0):
                claim_btn = _btn(tr("achievement_claim"), "gold", h=28)
                claim_btn.clicked.connect(lambda _, aid=ach["id"]: self._claim_reward(aid))
                layout.addWidget(claim_btn)
        else:
            status = QLabel(tr("achievement_locked"))
            status.setStyleSheet("color:#e05050; font-size:10px;")
            layout.addWidget(status)
        
        return card
    
    def _claim_reward(self, ach_id):
        r = db.claim_achievement_reward(self.user_id, ach_id)
        if r["ok"]:
            SND.complete()
            _show(self, tr("achievement_claimed"), r["msg"], "success")
            AppState.refresh()
            QTimer.singleShot(0, self.load)
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
    
    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE PAGE  (instant sync — no restart needed)
# ══════════════════════════════════════════════════════════════════════════════
class ProfilePage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self._root = QVBoxLayout(self)
        self.class_buttons = {}
        self._root.setContentsMargins(20, 16, 20, 16)
        self._root.setSpacing(10)
        # Inisialisasi atribut untuk rebirth agar aman
        self.rebirth_info_label = None
        self.rebirth_conditions_label = None
        self._build()
        self.load()
        AppState.register(self.load)

    def _clear(self):
        while self._root.count():
            i = self._root.takeAt(0)
            if i.widget():
                i.widget().deleteLater()

    def _build(self):
        # ========== Buat semua widget di sini ==========
        self._root.addWidget(_lbl(tr("profile_title"), "section", 14, True))
        self._root.addWidget(_sep())

        inner = QWidget()
        il    = QVBoxLayout(inner)
        il.setSpacing(14)
        il.setContentsMargins(0, 0, 0, 0)

        # ── Avatar display ────────────────────────────────────────────────────
        av_row = QHBoxLayout()
        av_row.setSpacing(18)
        self.av_icon = QLabel("⚔️")
        self.av_icon.setFont(QFont("Segoe UI", 48))
        self.av_icon.setMinimumSize(86, 86)
        self.av_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.av_icon.setStyleSheet(
            f"background: {_T('primary')};"
            f" border-radius: 12px;"
            f" border: 2px solid {_T('light')};")
        av_row.addWidget(self.av_icon)

        av_info = QVBoxLayout()
        av_info.setSpacing(4)
        self.av_display = _lbl("—", size=18, bold=True)
        self.av_username = _lbl("@username", "sub", 12)
        self.av_class_level = _lbl("Class · Level 0", "sub", 13)
        self.av_bio = _lbl("Bio", "sub", 12)
        self.av_joined = _lbl("Joined: ", "sub", 11)
        av_info.addWidget(self.av_display)
        av_info.addWidget(self.av_username)
        av_info.addWidget(self.av_class_level)
        av_info.addWidget(self.av_bio)
        av_info.addWidget(self.av_joined)
        av_row.addLayout(av_info, 1)
        il.addLayout(av_row)

        # ── Edit profil ───────────────────────────────────────────────────────
        eg = QGroupBox(tr("profile_edit"))
        el = QVBoxLayout(eg)
        el.setSpacing(8)
        self._dn  = _input(tr("profile_display_ph"))
        self._bio = _input(tr("profile_bio"))
        el.addWidget(_lbl(tr("profile_display_name_label"), size=12))
        el.addWidget(self._dn)
        el.addWidget(_lbl(tr("profile_bio_label_short"), size=12))
        el.addWidget(self._bio)
        el.addWidget(_btn(tr("profile_save"), "solid", self._save_profile, 40))
        il.addWidget(eg)

        # ── Security Question ────────────────────────────────────────────────
        sqg = QGroupBox(tr("profile_security"))
        sql = QVBoxLayout(sqg)
        self.question_combo = QComboBox()
        for i in range(1, 8):
            self.question_combo.addItem(tr(f"security_q{i}"))
        self.answer_input = _input(tr("profile_security_answer"))
        save_sq = _btn(tr("profile_save_security_btn"), "solid", self._save_security)
        sql.addWidget(self.question_combo)
        sql.addWidget(self.answer_input)
        sql.addWidget(save_sq)
        il.addWidget(sqg)

        # ── Backup Codes ─────────────────────────────────────────────────────
        bcg = QGroupBox(tr("profile_backup_codes"))
        bcl = QVBoxLayout(bcg)
        self.backup_codes_label = QLabel(tr("profile_backup_desc"))
        self.backup_codes_label.setWordWrap(True)
        self.backup_codes_label.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        bcl.addWidget(self.backup_codes_label)
        self.generate_backup_btn = _btn(tr("profile_generate_backup"), "solid", self._generate_backup_codes)
        bcl.addWidget(self.generate_backup_btn)
        self.backup_codes_display = QTextEdit()
        self.backup_codes_display.setReadOnly(True)
        self.backup_codes_display.setMinimumHeight(100)
        self.backup_codes_display.setVisible(False)
        bcl.addWidget(self.backup_codes_display)
        il.addWidget(bcg)

        # ── Class picker ──────────────────────────────────────────────────────
        cg = QGroupBox(tr("profile_class"))
        cl_lay = QGridLayout(cg)
        cl_lay.setSpacing(8)
        for i, (cid, cdata) in enumerate(db.AVATAR_CLASSES.items()):
            f = _card()
            cv = QVBoxLayout(f)
            cv.setContentsMargins(10, 8, 10, 8)
            cv.setSpacing(4)
            cv.addWidget(QLabel(cdata["icon"], alignment=Qt.AlignmentFlag.AlignCenter))
            nm = QLabel(tr(f"class_{cid}_name"))
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet(f"font-size:12px; font-weight:bold; color:{_T('text')};")
            cv.addWidget(nm)
            bn = QLabel(tr(f"class_{cid}_bonus"))
            bn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bn.setWordWrap(True)
            bn.setStyleSheet(f"font-size:10px; color:{_T('muted')};")
            cv.addWidget(bn)
            # Tombol select class
            sb = _btn(tr("profile_select_class"), h=30)
            sb.clicked.connect(lambda _, c=cid: self._set_class(c))
            cv.addWidget(sb)
            self.class_buttons[cid] = sb   # ← SIMPAN REFERENSI
            cl_lay.addWidget(f, i // 3, i % 3)
        il.addWidget(cg)

        # ── Color picker ──────────────────────────────────────────────────────
        colg = QGroupBox(tr("profile_color"))
        col_lay = QHBoxLayout(colg)
        col_lay.setContentsMargins(12, 12, 12, 12)
        col_lay.setSpacing(8)
        colors = [
            ("#5a8a2e",tr("color_green")), ("#d04020",tr("color_red")), ("#4da6ff",tr("color_blue")),
            ("#f0a800", tr("color_gold")),  ("#9a50e0",tr("color_purple")),  ("#4dd9e0",tr("color_cyan")),
            ("#e8e8e8",tr("color_white")), ("#ff6a00",tr("color_orange")),
        ]
        for hex_c, name in colors:
            cb = QPushButton(name)
            cb.setMinimumHeight(36)
            cb.setStyleSheet(
                f"background:{hex_c}; color:#fff;"
                f" border:2px solid transparent; border-radius:6px;"
                f" font-size:11px; font-weight:bold;")
            cb.clicked.connect(lambda _, c=hex_c: self._set_color(c))
            col_lay.addWidget(cb)
        il.addWidget(colg)

        # ── Emoji picker ──────────────────────────────────────────────────────
        emg = QGroupBox(tr("profile_emoji"))
        em_lay = QHBoxLayout(emg)
        em_lay.setContentsMargins(12, 12, 12, 12)
        em_lay.setSpacing(6)
        emojis = ["⚔️","🧙","🏹","💊","🗡️","🛡️","🔮","🌟","👑","🐉","🦊","🐺"]
        for em in emojis:
            eb = QPushButton(em)
            eb.setMinimumSize(42, 42)
            eb.setStyleSheet(
                f"font-size:20px; background:{_T('panel')};"
                f" border:1px solid {_T('border')}; border-radius:6px;")
            eb.clicked.connect(lambda _, e=em: self._set_emoji(e))
            em_lay.addWidget(eb)
        il.addWidget(emg)

        # ── Redeem Code ──────────────────────────────────────────────────────
        rcg = QGroupBox(tr("profile_redeem"))
        rcl = QVBoxLayout(rcg)
        self.redeem_input = _input(tr("profile_redeem_placeholder"))
        redeem_btn = _btn(tr("profile_redeem_btn"), "gold", self._redeem_code)
        rcl.addWidget(self.redeem_input)
        rcl.addWidget(redeem_btn)
        rcl.addWidget(_lbl(tr("profile_redeem_desc"), "sub", 10))
        il.addWidget(rcg)

        # ── Admin badge (jika admin) ────────────────────────────────────────
        self.admin_badge = QLabel(tr("admin_mode_active"))
        self.admin_badge.setWordWrap(True)
        self.admin_badge.setStyleSheet("color:#e05050; font-weight:bold; background:#2a0808; padding:10px; border-radius:8px; margin:5px;")
        self.admin_badge.setVisible(False)
        il.addWidget(self.admin_badge)

        # ========== REBIRTH SECTION ==========
        rebirth_group = QGroupBox(tr("profile_rebirth_title"))
        rebirth_layout = QVBoxLayout(rebirth_group)

        self.rebirth_info_label = QLabel()
        self.rebirth_info_label.setWordWrap(True)
        self.rebirth_info_label.setStyleSheet(f"color: {_T('accent')}; font-weight: bold;")
        rebirth_layout.addWidget(self.rebirth_info_label)

        self.rebirth_conditions_label = QLabel()
        self.rebirth_conditions_label.setWordWrap(True)
        self.rebirth_conditions_label.setStyleSheet(f"color: {_T('muted')}; font-size: 11px;")
        rebirth_layout.addWidget(self.rebirth_conditions_label)

        rebirth_btn = _btn(tr("profile_rebirth_btn"), "diamond", self._rebirth)
        rebirth_btn.setMinimumHeight(40)
        rebirth_layout.addWidget(rebirth_btn)

        il.addWidget(rebirth_group)

        # ── Change password ───────────────────────────────────────────────────
        pg = QGroupBox(tr("profile_change_pw"))
        pl = QVBoxLayout(pg)
        pl.setSpacing(8)
        self._old_pw = _input(tr("profile_old_pw_placeholder"), True)
        self._new_pw = _input(tr("profile_new_pw_placeholder"), True)
        pl.addWidget(self._old_pw)
        pl.addWidget(self._new_pw)
        pl.addWidget(_btn(tr("profile_change_pw_btn"), "gold", self._change_pw, 40))
        il.addWidget(pg)

        # ── Delete account ──────────────────────────────────────────────────
        delete_group = QGroupBox(tr("profile_delete_account"))
        delete_layout = QVBoxLayout(delete_group)
        delete_layout.addWidget(_lbl(tr("profile_delete_warning"), "sub", 12))
        delete_btn = _btn(tr("profile_delete_btn"), "danger", self._delete_account)
        delete_layout.addWidget(delete_btn)
        il.addWidget(delete_group)

        il.addStretch()
        self._root.addWidget(_scrolled(inner))
        fade_in(inner, 200)

    def load(self):
        if not AppState.user_id:
            return
        u = AppState.user()
        cls = db.AVATAR_CLASSES.get(u.get("avatar_class", "warrior"), {})

        # Update avatar
        self.av_icon.setText(u.get("avatar_emoji", "⚔️"))
        self.av_icon.setStyleSheet(
            f"background: {u.get('avatar_color', _T('primary'))};"
            f" border-radius: 12px;"
            f" border: 2px solid {_T('light')};")
        self.av_display.setText(u.get("display_name", "—"))
        self.av_username.setText(f"@{u.get('username','')}")
        self.av_class_level.setText(
            tr("profile_class_level", icon=cls.get('icon',''), name=cls.get('name',''), level=u['level'])
        )
        self.av_bio.setText(u.get("bio", tr("profile_no_bio")))
        self.av_joined.setText(
            (tr("profile_joined_prefix")) + f"{u.get('created_at','')[:10]}"
        )

        # Update display name & bio input fields
        self._dn.setText(u.get("display_name", ""))
        self._bio.setText(u.get("bio", ""))

        # Update admin badge
        is_admin = u.get("is_admin", 0)
        self.admin_badge.setVisible(is_admin)

        # Update class picker buttons
        # (cari child widgets di class picker dan set active label)
        class_group = self.findChild(QGroupBox, "profile_class")  # belum di-set objectName
        # Lebih mudah: kita update di load dengan mencari tombol yang aktif

        # Update rebirth info (pastikan label sudah dibuat)
        if self.rebirth_info_label is not None:
            rebirth_count = u.get("rebirth_count", 0)
            xp_bonus = rebirth_count * 10
            gold_bonus = rebirth_count * 5
            self.rebirth_info_label.setText(tr("profile_rebirth_info", count=rebirth_count, xp_bonus=xp_bonus, gold_bonus=gold_bonus))

        if self.rebirth_conditions_label is not None:
            conn = db.get_conn()
            ach_count = conn.execute(
                "SELECT COUNT(*) FROM user_achievements WHERE user_id=? AND unlocked_at IS NOT NULL",
                (self.user_id,)
            ).fetchone()[0]
            pet_count = conn.execute("SELECT COUNT(*) FROM user_pets WHERE user_id=?", (self.user_id,)).fetchone()[0]
            item_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (self.user_id,)).fetchone()[0]
            conn.close()
            conditions_text = (
                f"{'✅' if ach_count >= 10 else '❌'} {tr('profile_rebirth_cond_achievements', count=ach_count, need=10)}\n"
                f"{'✅' if u['level'] >= 25 else '❌'} {tr('profile_rebirth_cond_level', level=u['level'], need=25)}\n"
                f"{'✅' if pet_count >= 2 else '❌'} {tr('profile_rebirth_cond_pets', count=pet_count, need=2)}\n"
                f"{'✅' if item_count >= 6 else '❌'} {tr('profile_rebirth_cond_items', count=item_count, need=6)}"
            )
            self.rebirth_conditions_label.setText(conditions_text)

        class_group = None
        for child in self.findChildren(QGroupBox):
            if child.title() == tr("profile_class"):
                class_group = child
                break
        if class_group:
            grid = class_group.layout()
            if isinstance(grid, QGridLayout):
                for i in range(grid.count()):
                    item = grid.itemAt(i)
                    if item.widget():
                        card = item.widget()
                        if isinstance(card, QFrame):
                            for child_widget in card.findChildren(QLabel):
                                if child_widget.text() in [tr("profile_active_label"), "✔ Aktif"]:
                                    pass
                            pass

        # Update class picker buttons
        u = AppState.user()
        current_class = u.get("avatar_class", "warrior")
        for cid, btn in self.class_buttons.items():
            if cid == current_class:
                btn.setText(tr("profile_active_label"))   # "✔ Aktif"
                btn.setStyleSheet(
                    f"background: {_T('primary')}; color: #fff; "
                    f"border: 2px solid {_T('light')}; font-weight: bold;"
                )
            else:
                btn.setText(tr("profile_select_class"))
                btn.setStyleSheet("")  # reset ke default

    # ── actions ──────────────────────────────────────────────────────────────
    def _rebirth(self):
        # Cek syarat terlebih dahulu dengan preview
        u = AppState.user()
        conn = db.get_conn()
        ach_count = conn.execute(
            "SELECT COUNT(*) FROM user_achievements WHERE user_id=? AND unlocked_at IS NOT NULL",
            (self.user_id,)
        ).fetchone()[0]
        pet_count = conn.execute("SELECT COUNT(*) FROM user_pets WHERE user_id=?", (self.user_id,)).fetchone()[0]
        item_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (self.user_id,)).fetchone()[0]
        conn.close()

        # Cek apakah syarat terpenuhi
        conditions_met = (
            ach_count >= 10 and
            u["level"] >= 25 and
            pet_count >= 2 and
            item_count >= 6
        )

        if not conditions_met:
            # Tampilkan detail syarat yang belum terpenuhi
            missing = []
            if ach_count < 10:
                missing.append(tr("profile_rebirth_cond_achievements", count=ach_count, need=10))
            if u["level"] < 25:
                missing.append(tr("profile_rebirth_cond_level", level=u["level"], need=25))
            if pet_count < 2:
                missing.append(tr("profile_rebirth_cond_pets", count=pet_count, need=2))
            if item_count < 6:
                missing.append(tr("profile_rebirth_cond_items", count=item_count, need=6))
            _show(self, tr("msg_error"), "\n".join(missing), "error")
            return

        # Konfirmasi
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("profile_rebirth_confirm_title"))
        dlg.setMinimumSize(450, 350)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(_lbl(tr("profile_rebirth_confirm_warning"), size=14, bold=True))
        layout.addWidget(_lbl(tr("profile_rebirth_confirm_detail"), "sub", 12))
        layout.addWidget(_lbl(tr("profile_rebirth_confirm_benefit", xp=10, gold=5), "sub", 12))

        layout.addWidget(_lbl(tr("reset_confirm_type_label"), size=12))
        confirm_input = QLineEdit()
        confirm_input.setPlaceholderText(tr("profile_rebirth_confirm_placeholder"))
        confirm_input.setMinimumHeight(40)
        layout.addWidget(confirm_input)

        btn_layout = QHBoxLayout()
        cancel_btn = _btn(tr("btn_cancel"), "flat", dlg.reject)
        confirm_btn = _btn(tr("profile_rebirth_confirm_btn"), "diamond", dlg.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(confirm_btn)
        layout.addLayout(btn_layout)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if confirm_input.text().strip().upper() != "REBIRTH":
            _show(self, tr("msg_error"), tr("reset_confirm_invalid"), "error")
            return

        # Proses Rebirth
        loading = LoadingDialog(tr("profile_rebirth_loading"), self)
        loading.show()
        QApplication.processEvents()

        try:
            r = db.perform_rebirth(self.user_id)
            loading.accept()
            if r["ok"]:
                SND.level_up()  # sukses besar
                _show(self, tr("profile_rebirth_success_title"), r["msg"], "success")
                # Refresh data user dan UI
                AppState.refresh()
                self.load()
                # Refresh semua halaman agar buff terupdate
                main_win = self.window()
                if hasattr(main_win, "_pages"):
                    for page in main_win._pages.values():
                        if hasattr(page, "load"):
                            try:
                                page.load()
                            except:
                                pass
            else:
                SND.error()
                _show(self, tr("gagal_title"), r["msg"], "error")
        except Exception as e:
            loading.accept()
            SND.error()
            _show(self, tr("msg_error"), tr("profile_rebirth_error", error=str(e)), "error")

    def _redeem_code(self):
        code = self.redeem_input.text().strip().upper()
        if not code:
            _show(self, tr("msg_error"), tr("redeem_code_empty"), "error")
            return
        loading = LoadingDialog("Memverifikasi kode...", self)
        loading.show()
        QApplication.processEvents()
        r = db.redeem_code(self.user_id, code)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            self.load()  # reload halaman
            AppState.refresh()
            # Jika menjadi admin, mungkin perlu reload seluruh window agar efek langsung terasa
            if "MODE ADMIN" in r["msg"]:
                # Refresh topbar dan nav mungkin cukup
                main_win = self.window()
                if hasattr(main_win, "_retheme"):
                    main_win._retheme()
                # Tampilkan notifikasi tambahan
                _show(self, tr("admin_mode_title"), tr("admin_mode_msg"), "warning")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        self.redeem_input.clear()

    def _delete_account(self):
        # Dialog konfirmasi
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("profile_delete_title"))
        dlg.setMinimumSize(450, 300)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(_lbl(tr("profile_delete_warning_label"), size=14, bold=True))
        layout.addWidget(_lbl(tr("profile_delete_warning2"), "sub", 12))
        warning_text = QLabel(
            tr("delete_account_warning_list")
        )
        warning_text.setStyleSheet(f"color: #e05050; font-size: 12px; margin: 10px;")
        layout.addWidget(warning_text)

        layout.addWidget(_lbl(tr("delete_account_confirm"), size=12))
        confirm_input = QLineEdit()
        confirm_input.setPlaceholderText(tr("profile_delete_ph"))
        confirm_input.setMinimumHeight(40)
        layout.addWidget(confirm_input)

        layout.addWidget(_lbl(tr("delete_account_password"), size=12))
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setMinimumHeight(40)
        layout.addWidget(password_input)

        btn_layout = QHBoxLayout()
        cancel_btn = _btn(tr("profile_delete_cancel"), "flat", dlg.reject)
        delete_btn = _btn(tr("profile_delete_permanent"), "danger", dlg.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        confirm_text = confirm_input.text().strip()
        password = password_input.text()

        if confirm_text != "DELETE ACCOUNT":
            _show(self, tr("profile_confirm_title"), tr("profile_confirm_delete_type"), "error")
            return

        # Proses delete account
        loading = LoadingDialog(tr("delete_account_loading"), self)
        loading.show()
        QApplication.processEvents()
        r = db.delete_account(self.user_id, password)
        loading.accept()

        if r["ok"]:
            SND.error()  # efek suara
            _show(self, tr("account_deleted_title"), r["msg"], "warning")
            # Hapus session
            clear_session()
            # Tutup main window dan kembali ke login
            main_win = self.window()
            if isinstance(main_win, QMainWindow):
                main_win.close()
            # Tampilkan login
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, LoginWindow):
                    widget.show()
                    break
            else:
                login = LoginWindow()
                login.show()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _save_profile(self):
        db.set_avatar(self.user_id,
                      bio=self._bio.text(),
                      display_name=self._dn.text().strip())
        SND.notify()
        _show(self, tr("berhasil_title"), tr("profile_update_success"), "success")
        AppState.refresh()   # ← instant sync

    def _set_class(self, cls_id: str):
        r = db.change_class(self.user_id, cls_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
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
            _show(self, tr("berhasil_title"), r["msg"], "success")
            self._old_pw.clear()
            self._new_pw.clear()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _save_security(self):
        question = self.question_combo.currentText()
        answer = self.answer_input.text().strip()
        if not answer:
            _show(self, tr("msg_error"), tr("security_questions_not_empty"), "error")
            return
        db.set_security_question(self.user_id, question, answer)
        SND.notify()
        _show(self, tr("berhasil_title"), tr("security_questions_saved"), "success")
        self.answer_input.clear()

    def _generate_backup_codes(self):
        codes = db.generate_backup_codes(self.user_id, num_codes=5)
        if codes:
            msg = tr("backup_codes_intro") + "\n\n"
            for i, code in enumerate(codes, 1):
                msg += f"{i}. {code}\n"
            msg += "\n\n" + tr("backup_codes_warning")
            self.backup_codes_display.setText(msg)
            self.backup_codes_display.setVisible(True)
            SND.notify()
            _show(self, tr("backup_codes_title"), msg, "success")
        else:
            _show(self, tr("msg_error"), tr("backup_code_generate_fail"), "error")

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  SETTINGS PAGE  (5 themes + sound toggle)
# ══════════════════════════════════════════════════════════════════════════════
class SettingsPage(QWidget):
    theme_changed = pyqtSignal()
    language_changed = pyqtSignal()

    def __init__(self, user_id: int):
        super().__init__()
        
        self.user_id = user_id
        self._admin_was_shown = False
        self._build()
        AppState.register_lang_cb(self._retranslate)
        AppState.register(self._check_admin_panel)

    def _retranslate(self):
        self.section_title.setText(tr("settings_title"))
        self.theme_group.setTitle(tr("settings_theme"))
        self.sound_group.setTitle(tr("settings_sound"))
        self.currency_group.setTitle(tr("settings_currency"))
        self.lang_group.setTitle(tr("settings_language"))
        self.db_group.setTitle(tr("settings_database"))
        self._snd.setText(tr("settings_sound_enable"))
        self.exit_btn.setText(tr("settings_exit"))
        self.sound_hint.setText(tr("settings_sound_hint"))
        self.db_path_label.setText(tr("settings_db_path", path=db.DB_PATH))
        self.lang_combo.setItemText(0, tr("lang_id"))
        self.lang_combo.setItemText(1, tr("lang_en"))

    def load(self):
        self._retranslate()

    def _check_admin_panel(self):
        """Tampilkan admin panel jika user baru menjadi admin tanpa restart."""
        is_admin = bool(AppState.user().get("is_admin", 0))
        if is_admin and not self._admin_was_shown:
            self._admin_was_shown = True
            # Cari layout container dalam scroll area
            scroll = self.findChild(QScrollArea)
            if scroll and scroll.widget():
                container_layout = scroll.widget().layout()
                if container_layout:
                    admin_group = QGroupBox(tr("admin_panel"))
                    admin_layout = QVBoxLayout(admin_group)
                    row1 = QHBoxLayout()
                    self.debug_xp = QSpinBox()
                    self.debug_xp.setRange(0, 100000)
                    self.debug_xp.setValue(1000)
                    self.debug_xp.setSuffix(tr("unit_xp"))
                    add_xp_btn = _btn(tr("admin_add_xp"), "solid", self._debug_add_xp)
                    row1.addWidget(self.debug_xp)
                    row1.addWidget(add_xp_btn)
                    self.debug_gold = QSpinBox()
                    self.debug_gold.setRange(0, 100000)
                    self.debug_gold.setValue(500)
                    self.debug_gold.setSuffix(tr("unit_gold"))
                    add_gold_btn = _btn(tr("admin_add_gold"), "solid", self._debug_add_gold)
                    row1.addWidget(self.debug_gold)
                    row1.addWidget(add_gold_btn)
                    admin_layout.addLayout(row1)
                    row2 = QHBoxLayout()
                    fill_hp_btn = _btn(tr("admin_fill_hp_mp"), "gold", self._debug_fill_hp_mp)
                    set_max_level_btn = _btn(tr("admin_max_level"), "diamond", self._debug_set_max_level)
                    row2.addWidget(fill_hp_btn)
                    row2.addWidget(set_max_level_btn)
                    admin_layout.addLayout(row2)
                    row3 = QHBoxLayout()
                    reset_tasks_btn = _btn(tr("admin_complete_tasks"), "danger", self._debug_complete_all_tasks)
                    row3.addWidget(reset_tasks_btn)
                    admin_layout.addLayout(row3)
                    pet_cheat_group = QGroupBox(tr("admin_pet_cheat"))
                    pet_cheat_layout = QVBoxLayout(pet_cheat_group)
                    btn_level_up_pets = _btn(tr("admin_pet_level_up"), "diamond", self._debug_level_up_pets)
                    pet_cheat_layout.addWidget(btn_level_up_pets)
                    exp_row = QHBoxLayout()
                    self.debug_pet_exp = QSpinBox()
                    self.debug_pet_exp.setRange(1, 10000)
                    self.debug_pet_exp.setValue(100)
                    self.debug_pet_exp.setSuffix(tr("unit_exp"))
                    add_exp_btn = _btn(tr("admin_pet_add_exp"), "gold", self._debug_add_exp_pets)
                    exp_row.addWidget(self.debug_pet_exp)
                    exp_row.addWidget(add_exp_btn)
                    pet_cheat_layout.addLayout(exp_row)
                    feed_btn = _btn(tr("admin_pet_feed"), "solid", self._debug_feed_pets)
                    pet_cheat_layout.addWidget(feed_btn)
                    admin_layout.addWidget(pet_cheat_group)
                    warn = QLabel(tr("admin_warning"))
                    warn.setWordWrap(True)
                    warn.setStyleSheet("color:#e05050; font-size:11px;")
                    admin_layout.addWidget(warn)
                    # Sisipkan sebelum stretch (index -2 biasanya stretch + exit_btn)
                    insert_idx = container_layout.count() - 2
                    if insert_idx < 0:
                        insert_idx = 0
                    container_layout.insertWidget(insert_idx, admin_group)

    def closeEvent(self, e):
        AppState.unregister(self._check_admin_panel)
        super().closeEvent(e)

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(14)

        self.section_title = _lbl("", "section", 14, True)
        layout.addWidget(self.section_title)
        layout.addWidget(_sep())

        u = db.get_user(self.user_id)
        cur = u.get("theme", "overworld")

        self.theme_group = QGroupBox("")
        tl = QVBoxLayout(self.theme_group)
        tl.setSpacing(10)
        for key, td in db.THEMES.items():
            row = QHBoxLayout()
            preview = QLabel("●")
            preview.setStyleSheet(f"color:{td['light']}; font-size:22px;")
            preview.setMinimumWidth(30)
            rb = QRadioButton(f"{td['label']}   ")
            rb.setChecked(key == cur)
            rb.setStyleSheet(f"font-size:13px; color:{_T('text')};")
            rb.toggled.connect(lambda checked, k=key: self._apply(k) if checked else None)
            row.addWidget(preview)
            row.addWidget(rb, 1)
            tl.addLayout(row)
        layout.addWidget(self.theme_group)

        self.sound_group = QGroupBox("")
        sl = QVBoxLayout(self.sound_group)
        self._snd = QCheckBox("")
        self._snd.setChecked(bool(u.get("sound_enabled", 1)))
        self._snd.stateChanged.connect(self._toggle_snd)
        self.sound_hint = _lbl("", "sub", 11)
        sl.addWidget(self._snd)
        sl.addWidget(self.sound_hint)
        layout.addWidget(self.sound_group)

        self.currency_group = QGroupBox("")
        cl = QVBoxLayout(self.currency_group)
        self.currency_combo = QComboBox()
        self.currency_combo.addItems([tr("currency_idr"), "USD ($)", "EUR (€)"])
        current_curr = db.get_user_currency(self.user_id)
        curr_map = {"IDR": 0, "USD": 1, "EUR": 2}
        self.currency_combo.setCurrentIndex(curr_map.get(current_curr, 0))
        self.currency_combo.currentIndexChanged.connect(self._change_currency)
        cl.addWidget(self.currency_combo)
        layout.addWidget(self.currency_group)

        self.lang_group = QGroupBox("")
        lang_layout = QVBoxLayout(self.lang_group)
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("", "id")
        self.lang_combo.addItem("", "en")
        current_lang = AppState.get_language()
        idx = 0 if current_lang == "id" else 1
        self.lang_combo.setCurrentIndex(idx)
        self.lang_combo.currentIndexChanged.connect(self._change_language)
        lang_layout.addWidget(self.lang_combo)
        layout.addWidget(self.lang_group)

        reset_group = QGroupBox(tr("settings_reset_progress"))
        reset_layout = QVBoxLayout(reset_group)
        reset_layout.addWidget(_lbl(tr("settings_reset_warning"), "sub", 12))
        reset_btn = _btn(tr("settings_reset_btn"), "danger", self._reset_progress)
        reset_layout.addWidget(reset_btn)
        layout.addWidget(reset_group)

        if AppState.user().get("is_admin", 0):
            self._admin_was_shown = True
            admin_group = QGroupBox(tr("admin_panel"))
            admin_layout = QVBoxLayout(admin_group)
            row1 = QHBoxLayout()
            self.debug_xp = QSpinBox()
            self.debug_xp.setRange(0, 100000)
            self.debug_xp.setValue(1000)
            self.debug_xp.setSuffix(tr("unit_xp"))
            add_xp_btn = _btn(tr("admin_add_xp"), "solid", self._debug_add_xp)
            row1.addWidget(self.debug_xp)
            row1.addWidget(add_xp_btn)
            self.debug_gold = QSpinBox()
            self.debug_gold.setRange(0, 100000)
            self.debug_gold.setValue(500)
            self.debug_gold.setSuffix(tr("unit_gold"))
            add_gold_btn = _btn(tr("admin_add_gold"), "solid", self._debug_add_gold)
            row1.addWidget(self.debug_gold)
            row1.addWidget(add_gold_btn)
            admin_layout.addLayout(row1)
            row2 = QHBoxLayout()
            fill_hp_btn = _btn(tr("admin_fill_hp_mp"), "gold", self._debug_fill_hp_mp)
            set_max_level_btn = _btn(tr("admin_max_level"), "diamond", self._debug_set_max_level)
            row2.addWidget(fill_hp_btn)
            row2.addWidget(set_max_level_btn)
            admin_layout.addLayout(row2)
            row3 = QHBoxLayout()
            reset_tasks_btn = _btn(tr("admin_complete_tasks"), "danger", self._debug_complete_all_tasks)
            row3.addWidget(reset_tasks_btn)
            admin_layout.addLayout(row3)
            pet_cheat_group = QGroupBox(tr("admin_pet_cheat"))
            pet_cheat_layout = QVBoxLayout(pet_cheat_group)
            btn_level_up_pets = _btn(tr("admin_pet_level_up"), "diamond", self._debug_level_up_pets)
            pet_cheat_layout.addWidget(btn_level_up_pets)
            exp_row = QHBoxLayout()
            self.debug_pet_exp = QSpinBox()
            self.debug_pet_exp.setRange(1, 10000)
            self.debug_pet_exp.setValue(100)
            self.debug_pet_exp.setSuffix(tr("unit_exp"))
            add_exp_btn = _btn(tr("admin_pet_add_exp"), "gold", self._debug_add_exp_pets)
            exp_row.addWidget(self.debug_pet_exp)
            exp_row.addWidget(add_exp_btn)
            pet_cheat_layout.addLayout(exp_row)
            feed_btn = _btn(tr("admin_pet_feed"), "solid", self._debug_feed_pets)
            pet_cheat_layout.addWidget(feed_btn)
            admin_layout.addWidget(pet_cheat_group)
            warn = QLabel(tr("admin_warning"))
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#e05050; font-size:11px;")
            admin_layout.addWidget(warn)
            layout.addWidget(admin_group)

        self.db_group = QGroupBox("")
        dl = QVBoxLayout(self.db_group)
        self.db_path_label = _lbl("", "sub", 11)
        dl.addWidget(self.db_path_label)
        layout.addWidget(self.db_group)
        backup_btn = _btn(tr("settings_backup_now"), "solid", self._manual_backup)
        dl.addWidget(backup_btn)

        layout.addStretch()
        self.exit_btn = _btn("", "danger", QApplication.instance().quit)
        layout.addWidget(self.exit_btn)

        scroll.setWidget(container)
        main_layout.addWidget(scroll)
        self._retranslate()

    def _manual_backup(self):
        path = db.backup_database()
        if path:
            _show(self, tr("berhasil_title"), f"Backup berhasil disimpan di:\n{path}", "success")
        else:
            _show(self, tr("gagal_title"), "Backup gagal!", "error")

    def _reset_progress(self):
        # Dialog konfirmasi dengan input verifikasi
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("reset_confirm_title"))
        dlg.setMinimumSize(450, 300)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        layout.addWidget(_lbl(tr("reset_confirm_warning"), size=14, bold=True))
        layout.addWidget(_lbl(tr("reset_confirm_detail"), "sub", 12))
        layout.addWidget(_lbl(tr("reset_confirm_type_label"), size=12))

        confirm_input = QLineEdit()
        confirm_input.setPlaceholderText(tr("reset_confirm_placeholder"))
        confirm_input.setMinimumHeight(40)
        layout.addWidget(confirm_input)

        btn_layout = QHBoxLayout()
        cancel_btn = _btn(tr("btn_cancel"), "flat", dlg.reject)
        reset_btn = _btn(tr("reset_confirm_btn"), "danger", dlg.accept)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        if confirm_input.text().strip().upper() != "RESET PROGRESS":
            _show(self, tr("msg_error"), tr("reset_confirm_invalid"), "error")
            return

        # Proses reset
        loading = LoadingDialog(tr("reset_loading"), self)
        loading.show()
        QApplication.processEvents()

        try:
            db.reset_user_progress(self.user_id)
            SND.error()
            _show(self, tr("reset_success_title"), tr("reset_success_msg"), "warning")
            clear_session()
            main_win = self.window()
            if isinstance(main_win, QMainWindow):
                main_win.close()
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, LoginWindow):
                    widget.show()
                    break
            else:
                login = LoginWindow()
                login.show()
        except Exception as e:
            SND.error()
            _show(self, tr("msg_error"), tr("reset_error", error=str(e)), "error")
        finally:
            loading.accept()

    def _change_language(self, idx):
        new_lang = self.lang_combo.itemData(idx)
        current_lang = AppState.get_language()
        if new_lang == current_lang:
            return

        # Ambil teks dalam bahasa baru (tanpa mengubah bahasa saat ini)
        title = get_text("settings_language_restart_title", new_lang)
        msg = get_text("settings_language_restart_msg", new_lang)
        yes_btn = get_text("settings_language_restart_yes", new_lang)
        no_btn = get_text("settings_language_restart_no", new_lang)

        reply = QMessageBox.question(
            self,
            title,
            msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # Simpan bahasa ke database dan AppState
            AppState.set_language(new_lang)
            db.set_user_language(AppState.user_id, new_lang)

            # Restart aplikasi
            self._restart_app()

    def _restart_app(self):
        """Restart aplikasi menggunakan QProcess."""
        from PyQt6.QtCore import QProcess
        import sys

        # Path ke executable Python dan skrip utama
        if getattr(sys, 'frozen', False):
            # Jika dijalankan sebagai .exe
            program = sys.executable
            arguments = []
        else:
            # Jika dijalankan sebagai skrip Python
            program = sys.executable
            arguments = [sys.argv[0]]

        QProcess.startDetached(program, arguments)
        QApplication.quit()

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

    def _change_currency(self, idx):
        curr = ["IDR", "USD", "EUR"][idx]
        db.set_user_currency(self.user_id, curr)
        SND.notify()
        self.theme_changed.emit()

    def _debug_add_xp(self):
        amount = self.debug_xp.value()
        r = db.gain_xp_gold(self.user_id, amount, 0)
        if r["ok"]:
            SND.complete()
            _show(self, tr("debug_title"), tr("debug_xp_added", amount=amount), "success")
            AppState.refresh()
        else:
            SND.error()
            _show(self, tr("msg_error"), r.get("msg", "Gagal"), "error")

    def _debug_add_gold(self):
        amount = self.debug_gold.value()
        r = db.gain_xp_gold(self.user_id, 0, amount)
        if r["ok"]:
            SND.complete()
            _show(self, tr("debug_title"), tr("debug_gold_added", amount=amount), "success")
            AppState.refresh()
        else:
            SND.error()
            _show(self, tr("msg_error"), r.get("msg", "Gagal"), "error")

    def _debug_fill_hp_mp(self):
        u = AppState.user()
        db.update_user(self.user_id, hp=u["max_hp"], mp=u["max_mp"])
        SND.complete()
        _show(self, tr("debug_title"), tr("debug_hp_mp_restored"), "success")
        AppState.refresh()

    def _debug_set_max_level(self):
        target_level = 50
        u = AppState.user()
        current_level = u["level"]
        if current_level >= target_level:
            _show(self, tr("info_title"), tr("debug_level_already", level=current_level), "info")
            return
        needed_xp = 0
        for lvl in range(current_level, target_level):
            needed_xp += lvl * 150
        db.gain_xp_gold(self.user_id, needed_xp, 0)
        _show(self, tr("debug_title"), tr("debug_level_set", target=target_level), "success")
        AppState.refresh()

    def _debug_complete_all_tasks(self):
        habits = db.get_habits(self.user_id)
        for h in habits:
            if not h["done_today"]:
                db.complete_habit(self.user_id, h["id"], "up")
        dailies = db.get_dailies(self.user_id)
        for d in dailies:
            if not d["done_today"]:
                db.complete_daily(self.user_id, d["id"])
        todos = db.get_todos(self.user_id)
        for t in todos:
            if not t["done"]:
                db.complete_todo(self.user_id, t["id"])
        SND.complete()
        _show(self, tr("debug_title"), tr("debug_tasks_done"), "success")
        AppState.refresh()

    def _debug_level_up_pets(self):
        loading = LoadingDialog("Menaikkan level pet...", self)
        loading.show()
        QApplication.processEvents()
        r = db.admin_level_up_all_pets(self.user_id)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("cheat_title"), r["msg"], "success")
            AppState.refresh()
            main_win = self.window()
            if hasattr(main_win, "_pages") and "pets" in main_win._pages:
                main_win._pages["pets"].load()
        else:
            SND.error()
            _show(self, tr("msg_error"), r["msg"], "error")

    def _debug_add_exp_pets(self):
        amount = self.debug_pet_exp.value()
        loading = LoadingDialog("Menambah EXP pet...", self)
        loading.show()
        QApplication.processEvents()
        r = db.admin_add_exp_all_pets(self.user_id, amount)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("cheat_title"), r["msg"], "success")
            AppState.refresh()
            main_win = self.window()
            if hasattr(main_win, "_pages") and "pets" in main_win._pages:
                main_win._pages["pets"].load()
        else:
            SND.error()
            _show(self, tr("msg_error"), r["msg"], "error")

    def _debug_feed_pets(self):
        loading = LoadingDialog("Mengisi hunger pet...", self)
        loading.show()
        QApplication.processEvents()
        r = db.admin_feed_all_pets(self.user_id)
        loading.accept()
        if r["ok"]:
            SND.complete()
            _show(self, tr("cheat_title"), r["msg"], "success")
            main_win = self.window()
            if hasattr(main_win, "_pages") and "pets" in main_win._pages:
                main_win._pages["pets"].load()
        else:
            SND.error()
            _show(self, tr("msg_error"), r["msg"], "error")

# ══════════════════════════════════════════════════════════════════════════════
#  NOTIFICATION POPUP
# ══════════════════════════════════════════════════════════════════════════════
class NotifPopup(QDialog):
    def __init__(self, user_id: int, parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(tr("notif_window_title"))
        self.setMinimumSize(420, 400)
        self.setStyleSheet(build_ss())
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(10)
        lay.addWidget(_lbl(tr("notif_title"), "section", 14, True))
        lw = QListWidget()
        notifs = db.get_notifications(user_id, unread_only=False)
        db.mark_read(user_id)
        if not notifs:
            lw.addItem(tr("notif_empty"))
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
        lay.addWidget(_btn(tr("notif_close"), "solid", self.accept, 40))
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
        layout.addWidget(_lbl(tr("leaderboard_title"), "section", 14, True))
        layout.addWidget(_sep())

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self._update_headers()

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        layout.addWidget(self.table)
        AppState.register(self.load)
        AppState.register_lang_cb(self._retranslate)
        self.load()

    def _update_headers(self):
        self.table.setHorizontalHeaderLabels([
            tr("leaderboard_col_user"),
            tr("leaderboard_col_level"),
            tr("leaderboard_col_xp"),
            tr("leaderboard_col_gold"),
            tr("leaderboard_col_sport"),
            tr("leaderboard_col_pet"),
            tr("leaderboard_col_rebirth")
        ])

    def _retranslate(self):
        self._update_headers()

    def load(self):
        # Terapkan style agar background sesuai tema
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {_T("panel")};
                alternate-background-color: {_T("border")};
                gridline-color: {_T("border")};
                border: 1px solid {_T("border")};
                border-radius: 6px;
                color: {_T("text")};
            }}
            QHeaderView::section {{
                background-color: {_T("primary")};
                color: {_T("light")};
                padding: 8px;
                font-weight: bold;
                border: 1px solid {_T("border")};
            }}
        """)

        data = db.get_leaderboard_for_user(AppState.user_id)
        self.table.setRowCount(len(data))
        for i, r in enumerate(data):
            self.table.setItem(i, 0, QTableWidgetItem(r["display_name"] or r["username"]))
            self.table.setItem(i, 1, QTableWidgetItem(str(r["level"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(r["total_xp_earned"])))
            self.table.setItem(i, 3, QTableWidgetItem(f"{r['gold']:.0f}"))
            sport_lv = r.get("sport_level", 1) or 1
            sport_item = QTableWidgetItem(f"Lv.{sport_lv}")
            sport_item.setForeground(QColor("#f0a800"))
            self.table.setItem(i, 4, sport_item)
            self.table.setItem(i, 5, QTableWidgetItem(str(r["pet_count"])))
            rebirth_item = QTableWidgetItem(str(r.get("rebirth_count", 0)))
            rebirth_item.setForeground(QColor("#ff6b00"))
            self.table.setItem(i, 6, rebirth_item)

    def closeEvent(self, e):
        AppState.unregister(self.load)
        AppState.unregister_lang_cb(self._retranslate)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  Friends Page (Add Friend System)
# ══════════════════════════════════════════════════════════════════════════════
class FriendsPage(QWidget):
    def __init__(self, user_id):
        super().__init__()
        
        self.user_id = user_id
        self.main_layout = None  # referensi layout utama
        self._build()
        AppState.register(self.load)

    def _build(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 16, 20, 16)
        self.main_layout.setSpacing(10)
        self.main_layout.addWidget(_lbl(tr("friends_title"), "section", 14, True))
        self.main_layout.addWidget(_sep())

        # Form tambah teman
        add_form = QHBoxLayout()
        self.friend_username = _input(tr("friends_add_placeholder"))
        add_btn = _btn(tr("friends_add_btn"), "solid", self._send_request)
        add_form.addWidget(self.friend_username)
        add_form.addWidget(add_btn)
        self.main_layout.addLayout(add_form)

        # Daftar permintaan masuk
        self.pending_group = QGroupBox(tr("friends_pending"))
        self.pending_layout = QVBoxLayout(self.pending_group)
        self.main_layout.addWidget(self.pending_group)

        # Daftar teman
        self.friends_group = QGroupBox(tr("friends_list"))
        self.friends_layout = QVBoxLayout(self.friends_group)
        self.main_layout.addWidget(self.friends_group)

        self.main_layout.addStretch()
        self.load()

    def _clear_layout(self):
        """Hapus semua widget dan sub-layout dari layout utama."""
        if self.main_layout:
            while self.main_layout.count():
                item = self.main_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    # Bersihkan sub-layout juga
                    sub_layout = item.layout()
                    while sub_layout.count():
                        sub_item = sub_layout.takeAt(0)
                        if sub_item.widget():
                            sub_item.widget().deleteLater()
                    sub_layout.deleteLater()

    def load(self):
        if not AppState.user_id:
            return

        # ========== CEK ADMIN ==========
        if AppState.user().get("is_admin", 0):
            self._clear_layout()
            msg = QLabel(tr("friends_admin_block"))
            msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            msg.setStyleSheet(f"color:{_T('muted')}; font-size:14px; padding:40px;")
            self.main_layout.addWidget(msg)
            return

        # ========== NON-ADMIN: TAMPILKAN UI NORMAL ==========
        # Bersihkan isi pending_layout dan friends_layout (tapi jangan hapus group box-nya)
        while self.pending_layout.count():
            item = self.pending_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                sub.deleteLater()

        while self.friends_layout.count():
            item = self.friends_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                sub = item.layout()
                while sub.count():
                    sub_item = sub.takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()
                sub.deleteLater()

        # Pending requests
        pending = db.get_pending_friend_requests(self.user_id)
        if pending:
            self.pending_group.setVisible(True)
            for req in pending:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"📨 {req['display_name']} (@{req['username']})"))
                accept = _btn(tr("guild_accept"), h=28)
                accept.clicked.connect(lambda _, rid=req["id"]: self._accept(rid))
                reject = _btn(tr("guild_reject"), "danger", h=28)
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
                row.addWidget(QLabel(tr("friend_level_format", emoji=f['avatar_emoji'], name=f['display_name'], level=f['level'])))
                row.addStretch()
                chat_btn = _btn(tr("friends_chat_btn"), h=28)
                chat_btn.clicked.connect(lambda _, fid=f["id"], name=f["display_name"]: self._open_chat(fid, name))
                profile_btn = _btn("👤", h=28)
                profile_btn.clicked.connect(lambda _, fid=f["id"]: self._view_profile(fid))
                kick_btn = _btn(tr("friends_remove_btn"), "danger", h=28)
                kick_btn.clicked.connect(lambda _, fid=f["id"]: self._remove_friend(fid))
                row.addWidget(chat_btn)
                row.addWidget(profile_btn)
                row.addWidget(kick_btn)
                self.friends_layout.addLayout(row)
        else:
            self.friends_group.setVisible(False)

    def _open_chat(self, friend_id, friend_name):
        if AppState.user().get("is_admin", 0):
            _show(self, tr("info_title"), tr("chat_admin_block"), "warning")
            return
        dlg = ChatDialog(self.user_id, friend_id, friend_name, self)
        dlg.exec()

    def _view_profile(self, friend_id):
        dlg = FriendProfileDialog(friend_id, self)
        dlg.exec()

    def _remove_friend(self, friend_id):
        r = db.remove_friend(self.user_id, friend_id)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")
        QTimer.singleShot(0, self.load)

    def _send_request(self):
        username = self.friend_username.text().strip()
        if not username:
            _show(self, tr("msg_error"), tr("msg_enter_username"), "error")
            return
        r = db.send_friend_request(self.user_id, username)
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            self.friend_username.clear()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _accept(self, req_id):
        r = db.accept_friend_request(self.user_id, req_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)

    def _reject(self, req_id):
        r = db.reject_friend_request(self.user_id, req_id)
        self._show_result(r)
        QTimer.singleShot(0, self.load)

    def _show_result(self, r):
        if r["ok"]:
            SND.notify()
            _show(self, tr("berhasil_title"), r["msg"], "success")
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

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
        self.setWindowTitle(tr("chat_with", name=friend_name))
        self.setMinimumSize(400, 500)
        self.setStyleSheet(build_ss())
        self._build()
        self._load_messages()
        self.timer = QTimer()
        self.timer.timeout.connect(self._load_messages)
        self.timer.start(3000)

    def _build(self):
        layout = QVBoxLayout(self)
        
        # Tombol Clear Chat
        btn_layout = QHBoxLayout()
        clear_btn = _btn(tr("chat_clear_self"), "danger", self._clear_chat, 32)
        btn_layout.addStretch()
        btn_layout.addWidget(clear_btn)
        layout.addLayout(btn_layout)
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        send_btn = _btn(tr("chat_send_btn"), "solid", self._send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def _clear_chat(self):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("chat_clear_confirm_self"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_friend_chat(self.user_id, self.friend_id)
            self._load_messages()
            SND.notify()

    def _load_messages(self):
        messages = db.get_messages(self.user_id, self.friend_id)
        self.chat_area.clear()
        for m in messages:
            sender = tr("chat_you") if m["sender_id"] == self.user_id else tr("chat_friend")
            self.chat_area.append(tr("chat_message_format", time=m['created_at'][11:16], sender=sender, message=m['message']))
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
        conn = db.get_conn()
        leader_row = conn.execute("SELECT leader_id FROM guilds WHERE id=?", (guild_id,)).fetchone()
        self.is_leader = leader_row and leader_row["leader_id"] == user_id
        conn.close()
        self.setWindowTitle(tr("guild_chat_title"))
        self.setMinimumSize(450, 550)
        self.setStyleSheet(build_ss())
        self._build()
        self._load_messages()
        self.timer = QTimer()
        self.timer.timeout.connect(self._load_messages)
        self.timer.start(3000)

    def _build(self):
        layout = QVBoxLayout(self)
        
        # Tombol Clear All jika leader
        if self.is_leader:
            btn_layout = QHBoxLayout()
            clear_all_btn = _btn(tr("chat_clear_all"), "danger", self._clear_all, 32)
            btn_layout.addStretch()
            btn_layout.addWidget(clear_all_btn)
            layout.addLayout(btn_layout)
        
        self.chat_area = QTextEdit()
        self.chat_area.setReadOnly(True)
        layout.addWidget(self.chat_area)
        
        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        send_btn = _btn(tr("chat_send_btn"), "solid", self._send_message)
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(send_btn)
        layout.addLayout(input_layout)

    def _clear_all(self):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("chat_clear_all_confirm"), 
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.clear_guild_chat(self.guild_id)
            self._load_messages()
            SND.notify()

    def _load_messages(self):
        msgs = db.get_guild_messages(self.guild_id)
        self.chat_area.clear()
        for m in msgs:
            self.chat_area.append(tr("guild_chat_message_format", time=m['created_at'][11:16], name=m['display_name'], message=m['message']))

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
        self.setWindowTitle(tr("friend_profile_title"))
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
        self.content_layout.addWidget(_lbl(tr("profile_bio_label") + " " + (u.get('bio', 'Tidak ada bio')), "sub"))
        self.content_layout.addWidget(_sep())
        data = [
            (tr("stats_habit_today"), f"{stats['habits_done_today']}/{stats['habits_total']}"),
            (tr("stats_daily_today"), f"{stats['dailies_done_today']}/{stats['dailies_total']}"),
            (tr("stats_quest_done"), f"{stats['todos_done']}/{stats['todos_total']}"),
            (tr("stats_max_streak"), str(stats["max_streak"])),
            (tr("stats_boss_killed"), str(stats["bosses_killed"])),
            (tr("stats_pets"), str(stats["pet_count"])),
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
        
        self.setWindowTitle(tr("reset_password_security_title"))
        self.setMinimumSize(450, 400)
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
        layout.addWidget(_lbl(tr("reset_password_username"), size=12))
        self.username_input = _input(tr("login_username"))
        layout.addWidget(self.username_input)
        btn = _btn(tr("reset_password_check"), "solid", self._check_username)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _check_username(self):
        username = self.username_input.text().strip()
        if not username:
            self.msg_label.setText(tr("reset_username_empty"))
            return
        conn = db.get_conn()
        row = conn.execute(
            "SELECT id, security_question FROM users WHERE username=?",
            (username.lower(),)
        ).fetchone()
        conn.close()
        if not row:
            self.msg_label.setText(tr("reset_username_notfound"))
            return
        if not row["security_question"]:
            self.msg_label.setText(tr("reset_no_sq"))
            return
        self.user_id = row["id"]
        self.security_question = row["security_question"]
        self._step2() 

    def _step2(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl(tr("reset_password_security_question"), size=12))
        layout.addWidget(_lbl(self.security_question, size=12, bold=True))
        self.answer_input = _input(tr("reset_password_answer"))
        layout.addWidget(self.answer_input)
        btn = _btn(tr("reset_password_verify"), "solid", self._verify)

        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _verify(self):
        answer = self.answer_input.text().strip()
        if not answer:
            self.msg_label.setText(tr("reset_answer_empty"))
            return
        if db.verify_security_answer(self.user_id, answer):
            self._step3()
        else:
            self.msg_label.setText(tr("reset_answer_wrong"))
    
    def _step3(self):
        self._clear()
        if not self.user_id:  
            self.msg_label.setText(tr("reset_error"))
            return
        layout = self.layout()
        layout.addWidget(_lbl(tr("reset_password_new"), size=12))   
        self.new_pass = _input(tr("reset_password_new"), password=True)
        self.confirm_pass = _input(tr("reset_password_confirm"), password=True)
        layout.addWidget(self.new_pass)
        layout.addWidget(self.confirm_pass)
        btn = _btn(tr("reset_password_btn"), "solid", self._reset)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _reset(self):
        p1 = self.new_pass.text()
        p2 = self.confirm_pass.text()
        if len(p1) < 4:
            self.msg_label.setText(tr("login_pw_min"))
            return
        if p1 != p2:
            self.msg_label.setText(tr("login_pw_mismatch"))
            return
        db.reset_password_by_security(self.user_id, p1)
        _show(self, tr("berhasil_title"), tr("reset_success_msg"), "success")
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
        self.setWindowTitle(tr("login_title"))
        self.setMinimumSize(500, 620)
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
        banner.setMinimumHeight(110)
        banner.setStyleSheet(
            f"background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 {_T('bg')},stop:1 {_T('panel')});"
            f"border-bottom: 2px solid {_T('primary')};")
        bl = QVBoxLayout(banner)
        bl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1 = _lbl(tr("app_logo"), size=24, bold=True)
        t1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t1.setStyleSheet(f"color: {_T('light')};")
        t2 = _lbl(tr("app_tagline"), size=12)
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
        tabs.addTab(self._login_tab(),    tr("login_tab_login_label"))
        tabs.addTab(self._register_tab(), tr("login_tab_register_label"))
        body_lay.addWidget(tabs)
        root.addWidget(body)

    def _login_tab(self) -> QWidget:
        w   = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 16, 0, 0)
        lay.setSpacing(12)

        self._l_user = _input(tr("login_username"))
        self._l_pass = _input(tr("login_password"), True)
        self._l_msg  = _lbl("", "sub", 12)
        self._l_msg.setStyleSheet("color: #e05050;")
        self._l_msg.setWordWrap(True)

        self._remember_cb = QCheckBox(tr("login_remember_text"))
        self._remember_cb.setStyleSheet(f"color: {_T('text')};")
        lay.addWidget(self._remember_cb)

        ok = _btn(tr("login_button_text"), "solid", self._do_login, 48)
        for w_ in [self._l_user, self._l_pass, ok, self._l_msg]:
            lay.addWidget(w_)
        lay.addStretch()

        forgot_btn = _btn(tr("login_forgot_btn"), "flat", self._forgot_password)
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

        self._r_user  = _input(tr("register_username"))
        self._r_disp  = _input(tr("register_display"))
        self._r_pass = _input(tr("register_password"), True)
        self._r_pass2 = _input(tr("register_confirm"), True)
        self._r_bio   = _input(tr("register_bio"))

        lay.addWidget(_lbl(tr("register_class_label"), size=12))
        self._r_class = QComboBox()
        self._r_class.setMinimumHeight(42)
        for cid, cdata in db.AVATAR_CLASSES.items():
            from translations import TRANSLATIONS
            # Ambil terjemahan nama class dan bonus
            name_key = f"class_{cid}_name"
            bonus_key = f"class_{cid}_bonus"
            name_text = tr(name_key) if name_key in TRANSLATIONS else cdata['name']
            bonus_text = tr(bonus_key) if bonus_key in TRANSLATIONS else cdata['bonus']
            self._r_class.addItem(
                f"{cdata['icon']}  {name_text}  —  {bonus_text}",
                cid)

        self._r_msg = _lbl("", "sub", 12)
        self._r_msg.setWordWrap(True)

        ok = _btn(tr("register_button_text"), "solid", self._do_register, 48)
        for w_ in [self._r_user, self._r_disp, self._r_pass,
                   self._r_pass2, self._r_bio, self._r_class,
                   ok, self._r_msg]:
            lay.addWidget(w_)
        lay.addStretch()
        return w

    def _do_login(self):
        loading = LoadingDialog(tr("login_processing"), self)
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
            self._l_msg.setText(tr("error_occurred", error=e))

    def _do_register(self):
        u = self._r_user.text().strip()
        if not u or " " in u:
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(tr("register_username_invalid"))
            return
        if len(self._r_pass.text()) < 4:
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(tr("login_pw_min"))
            return
        if self._r_pass.text() != self._r_pass2.text():
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(tr("login_pw_mismatch"))
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
            self._r_msg.setText("✅ " + r["msg"] + tr("register_success_login_now"))
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
        
        self.setWindowTitle(tr("login_forgot"))
        self.setMinimumSize(350, 200)
        self.setStyleSheet(build_overworld_ss())
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(_lbl(tr("reset_method_title"), size=12))
        btn_security = _btn(tr("forgot_security_btn"), "solid", self._choose_security)
        btn_backup = _btn(tr("forgot_backup_btn"), "solid", self._choose_backup)
        layout.addWidget(btn_security)
        layout.addWidget(btn_backup)
        cancel = _btn(tr("forgot_cancel_btn"), "flat", self.reject)
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
        
        self.setWindowTitle(tr("reset_password_backup_title"))
        self.setMinimumSize(450, 350)
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
        layout.addWidget(_lbl(tr("reset_password_username"), size=12))
        self.username_input = _input(tr("login_username"))
        layout.addWidget(self.username_input)
        btn = _btn(tr("check_backup_code_btn"), "solid", self._check_username)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _check_username(self):
        username = self.username_input.text().strip()
        if not username:
            self.msg_label.setText(tr("reset_username_empty"))
            return
        conn = db.get_conn()
        row = conn.execute("SELECT id FROM users WHERE username=?", (username.lower(),)).fetchone()
        conn.close()
        if not row:
            self.msg_label.setText(tr("reset_username_notfound"))
            return
        self.user_id = row["id"]
        # Cek apakah user memiliki backup codes yang belum dipakai
        codes = db.get_user_backup_codes(self.user_id, only_unused=True)
        if not codes:
            self.msg_label.setText(tr("reset_no_bc_long"))
            return
        self._step2()
    
    def _step2(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl(tr("reset_backup_code_label"), size=12))
        self.code_input = _input(tr("reset_password_backup_code"))
        layout.addWidget(self.code_input)
        btn = _btn(tr("reset_password_backup_btn"), "solid", self._verify)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _verify(self):
        code = self.code_input.text().strip().upper()
        if not code:
            self.msg_label.setText(tr("reset_bc_empty"))
            return
        if db.verify_backup_code(self.user_id, code):
            self._step3()
        else:
            self.msg_label.setText(tr("reset_bc_invalid"))
    
    def _step3(self):
        self._clear()
        layout = self.layout()
        layout.addWidget(_lbl(tr("reset_password_new"), size=12))
        self.new_pass = _input(tr("reset_password_new"), password=True)
        self.confirm_pass = _input(tr("reset_password_confirm"), password=True)
        layout.addWidget(self.new_pass)
        layout.addWidget(self.confirm_pass)
        btn = _btn(tr("reset_backup_reset_btn"), "solid", self._reset)
        layout.addWidget(btn)
        self.msg_label = _lbl("", "sub", 12)
        layout.addWidget(self.msg_label)
    
    def _reset(self):
        p1 = self.new_pass.text()
        p2 = self.confirm_pass.text()
        if len(p1) < 4:
            self.msg_label.setText(tr("login_pw_min"))
            return
        if p1 != p2:
            self.msg_label.setText(tr("login_pw_mismatch"))
            return
        db.reset_password_with_backup_code(self.user_id, p1)
        _show(self, tr("berhasil_title"), tr("reset_success_msg"), "success")
        self.accept()
    
    def _clear(self):
        layout = self.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

# ==================================================================
# FOOD PAGE (Calorie Tracker)
# ==================================================================
class AddFoodDialog(QDialog):
    """Dialog untuk mencatat makanan atau menambah makanan custom."""
    def __init__(self, user_id, mode="log", parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.mode = mode
        self.all_foods = []  # akan diisi list of dict
        self.setWindowTitle(tr("food_log") if mode == "log" else tr("food_add_custom"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(550)
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

        if self.mode == "log":
            # ========== FILTER KATEGORI ==========
            lay.addWidget(_lbl(tr("food_filter_category"), size=12))
            self.category_filter = QComboBox()
            self.category_filter.setMinimumHeight(42)
            self.category_filter.addItem(tr("food_all_categories"), "all")
            self.category_filter.addItem(tr("food_category_main"), "main")
            self.category_filter.addItem(tr("food_category_protein"), "protein")
            self.category_filter.addItem(tr("food_category_veg"), "veg")
            self.category_filter.addItem(tr("food_category_drink"), "drink")
            self.category_filter.addItem(tr("food_category_snack"), "snack")
            self.category_filter.addItem(tr("food_category_international"), "international")
            self.category_filter.currentIndexChanged.connect(self._filter_food_combo)
            lay.addWidget(self.category_filter)

            # ========== SEARCH BAR ==========
            lay.addWidget(_lbl(tr("food_search_label"), size=12))
            self.search_input = QLineEdit()
            self.search_input.setPlaceholderText(tr("food_search_ph"))
            self.search_input.setMinimumHeight(42)
            self.search_input.textChanged.connect(self._filter_food_combo)
            lay.addWidget(self.search_input)

            # ========== COMBO MAKANAN ==========
            lay.addWidget(_lbl(tr("food_ingredient_select_label_short"), size=12))
            self.food_combo = QComboBox()
            self.food_combo.setMinimumHeight(42)
            lay.addWidget(self.food_combo)

            # Ambil data makanan
            foods = db.get_food_items(self.user_id)
            lang = AppState.get_language()   # ambil bahasa aktif
            self.all_foods = []
            for f in foods:
                display_name = get_food_name(f['name'], lang)  # terjemahkan
                display = f"{f['icon']} {display_name} - {f['calories']:.0f} kcal"
                self.all_foods.append({
                    "id": f["id"],
                    "name": f['name'],
                    "icon": f['icon'],
                    "display": display
                })

            # ========== PORS ==========
            lay.addWidget(_lbl(tr("food_serving_label"), size=12))
            self.serving = QDoubleSpinBox()
            self.serving.setMinimum(0.25)
            self.serving.setMaximum(10)
            self.serving.setSingleStep(0.25)
            self.serving.setValue(1)
            self.serving.setMinimumHeight(42)
            lay.addWidget(self.serving)

            # ========== JENIS MAKAN ==========
            lay.addWidget(_lbl(tr("food_meal_type"), size=12))
            self.meal_type = _combo([
                (tr("food_meal_breakfast"), "breakfast"),
                (tr("food_meal_lunch"), "lunch"),
                (tr("food_meal_dinner"), "dinner"),
                (tr("food_meal_snack"), "snack")
            ])
            lay.addWidget(self.meal_type)

            # ========== TANGGAL ==========
            lay.addWidget(_lbl(tr("food_date"), size=12))
            self.log_date = QLineEdit()
            self.log_date.setText(date.today().isoformat())
            self.log_date.setMinimumHeight(42)
            lay.addWidget(self.log_date)

            # ========== CATATAN ==========
            lay.addWidget(_lbl(tr("dialog_notes"), size=12))
            self.notes = _input()
            lay.addWidget(self.notes)

            btn = _btn(tr("food_log_btn"), "solid", self._log_food, 46)
            lay.addWidget(btn)

            # Isi combo awal
            self._filter_food_combo("")

        else:  # mode "add" untuk makanan custom
            lay.addWidget(_lbl(tr("food_name_label"), size=12))
            self.name = _input(tr("food_custom_ph"))
            lay.addWidget(self.name)

            lay.addWidget(_lbl(tr("food_icon_label"), size=12))
            self.icon = _input("🍎")
            lay.addWidget(self.icon)

            lay.addWidget(_lbl(tr("food_calories_label"), size=12))
            self.calories = QDoubleSpinBox()
            self.calories.setMaximum(2000)
            self.calories.setMinimum(0)
            self.calories.setValue(100)
            lay.addWidget(self.calories)

            lay.addWidget(_lbl(tr("food_protein_label"), size=12))
            self.protein = QDoubleSpinBox()
            self.protein.setMaximum(200)
            self.protein.setValue(10)
            lay.addWidget(self.protein)

            lay.addWidget(_lbl(tr("food_carbs_label"), size=12))
            self.carbs = QDoubleSpinBox()
            self.carbs.setMaximum(200)
            self.carbs.setValue(20)
            lay.addWidget(self.carbs)

            lay.addWidget(_lbl(tr("food_fat_label"), size=12))
            self.fat = QDoubleSpinBox()
            self.fat.setMaximum(100)
            self.fat.setValue(5)
            lay.addWidget(self.fat)

            btn = _btn(tr("food_save_btn"), "solid", self._add_food, 46)
            lay.addWidget(btn)

        root.addWidget(_scrolled(content))

    # ========== FUNGSI FILTER ==========
    def _filter_food_combo(self, text=""):
        """Filter daftar makanan berdasarkan teks pencarian dan kategori."""
        if not self.all_foods:
            return
        self.food_combo.blockSignals(True)
        self.food_combo.clear()

        search_text = self.search_input.text().strip().lower() if hasattr(self, 'search_input') else ""
        category = self.category_filter.currentText() if hasattr(self, 'category_filter') else tr("food_all_categories")

        for item in self.all_foods:
            # Filter berdasarkan teks
            if search_text and search_text not in item["display"].lower() and search_text not in item["name"].lower():
                continue
            # Filter berdasarkan kategori
            if not self._is_in_category(item["name"], item["icon"], category):
                continue
            self.food_combo.addItem(item["display"], item["id"])

        self.food_combo.blockSignals(False)

    def _is_in_category(self, name: str, icon: str, category: str) -> bool:
        """Cek apakah makanan termasuk dalam kategori berdasarkan nama dan icon."""
        name_lower = name.lower()
        icon_lower = icon.lower()

        if category == tr("food_all_categories"):
            return True

        # Makanan Utama
        if category == tr("food_category_main"):
            keywords = ["nasi", "mie", "mi ", "roti", "burger", "pizza", "sandwich",
                        "spaghetti", "pasta", "bubur", "ketupat", "lontong", "noodle",
                        "donut", "croissant", "bagel", "taco", "burrito", "quesadilla"]
            return any(k in name_lower for k in keywords)

        # Lauk
        if category == tr("food_category_protein"):
            keywords = ["ayam", "daging", "ikan", "telur", "tahu", "tempe", "sapi",
                        "kambing", "bebek", "udang", "cumi", "kepiting", "sate",
                        "rendang", "gulai", "tuna", "salmon", "tofu", "egg", "chicken",
                        "beef", "pork", "lamb", "shrimp", "crab", "meat"]
            return any(k in name_lower for k in keywords)

        # Sayur & Buah
        if category == tr("food_category_veg"):
            keywords = ["sayur", "sayuran", "buah", "salad", "tumis", "capcay", "gado",
                        "karedok", "pecel", "lalapan", "apel", "pisang", "jeruk",
                        "mangga", "semangka", "alpukat", "anggur", "stroberi", "nanas",
                        "melon", "pepaya", "jambu", "wortel", "kangkung", "bayam",
                        "brokoli", "kubis", "timun", "tomat", "lettuce", "vegetable",
                        "fruit", "apple", "banana", "orange", "mango", "watermelon"]
            return any(k in name_lower for k in keywords)

        # Minuman
        if category == tr("food_category_drink"):
            keywords = ["air", "kopi", "teh", "jus", "susu", "soda", "milk", "coffee",
                        "tea", "juice", "smoothie", "coklat panas", "matcha", "latte",
                        "cappuccino", "es ", "wedang", "bandrek", "bajigur", "soda",
                        "lemonade", "milkshake", "yogurt drink", "kefir", "kombucha",
                        "boba", "bubble tea", "thai tea", "chai", "horlicks", "ovaltine"]
            return any(k in name_lower for k in keywords)

        # Snack & Dessert
        if category == tr("food_category_snack"):
            keywords = ["keripik", "kue", "es krim", "coklat", "chocolate", "cake",
                        "cookie", "biscuit", "donat", "pastry", "puding", "pudding",
                        "cheesecake", "brownie", "muffin", "cupcake", "waffle", "pancake",
                        "ice cream", "gelato", "sorbet", "pie", "tart", "croissant",
                        "kripik", "popcorn", "permen", "candy", "wafer", "biskuit",
                        "martabak", "terang bulan", "klepon", "lupis", "getuk", "nagasari"]
            return any(k in name_lower for k in keywords)

        # Internasional
        if category == tr("food_category_international"):
            keywords = ["katsu", "sushi", "ramen", "curry", "tempura", "takoyaki",
                        "okonomiyaki", "teriyaki", "gyoza", "dim sum", "pho", "tom yum",
                        "pad thai", "bibimbap", "bulgogi", "kimchi", "naan", "biryani",
                        "falafel", "hummus", "paella", "croissant", "baguette", "lasagna",
                        "carbonara", "alfredo", "bolognese", "doner", "shawarma", "kebab"]
            return any(k in name_lower for k in keywords)

        return True

    # ========== FUNGSI LOG FOOD ==========
    def _log_food(self):
        food_id = self.food_combo.currentData()
        if food_id is None:
            _show(self, tr("msg_error"), tr("food_select_first"), "error")
            return
        serving = self.serving.value()
        meal_type = self.meal_type.currentData()
        log_date = self.log_date.text().strip()
        notes = self.notes.text()
        if not log_date:
            log_date = date.today().isoformat()
        r = db.log_food(self.user_id, food_id, serving, meal_type, log_date, notes)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), tr("calories_logged", cal=r['calories']), "success")
            self.accept()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r.get("msg", "Gagal mencatat makanan"), "error")

    def _add_food(self):
        name = self.name.text().strip()
        icon = self.icon.text().strip() or "🍎"
        cal = self.calories.value()
        pro = self.protein.value()
        carb = self.carbs.value()
        fat = self.fat.value()
        if not name:
            _show(self, tr("msg_error"), tr("food_name_empty"), "error")
            return
        r = db.add_custom_food(self.user_id, name, icon, cal, pro, carb, fat)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), tr("food_added_success", name=name), "success")
            self.accept()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r.get("msg", "Gagal menambah makanan"), "error")


class AddRecipeDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.selected_items = []  # list of (food_id, quantity)
        self.setWindowTitle(tr("recipe_add_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(600)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lay.addWidget(_lbl(tr("recipe_add_title"), "section", 14, True))
        lay.addWidget(_sep())

        # Nama resep
        lay.addWidget(_lbl(tr("food_recipe_name_label"), size=12))
        self.name = _input(tr("food_recipe_name_ph"))
        lay.addWidget(self.name)

        # Icon
        lay.addWidget(_lbl(tr("dialog_icon"), size=12))
        self.icon = _input("🍲")
        lay.addWidget(self.icon)

        # Porsi standar
        lay.addWidget(_lbl(tr("food_recipe_serving_label"), size=12))
        self.serving = QDoubleSpinBox()
        self.serving.setRange(0.5, 10)
        self.serving.setValue(1)
        self.serving.setSuffix(tr("unit_serving"))
        lay.addWidget(self.serving)

        # Daftar bahan
        lay.addWidget(_lbl(tr("food_recipe_ingredients_label"), size=12))
        self.ingredients_list = QListWidget()
        self.ingredients_list.setMaximumHeight(120)
        lay.addWidget(self.ingredients_list)

        # Tombol tambah bahan
        add_ing_btn = _btn(tr("food_recipe_add_ingredient"), h=32)
        add_ing_btn.clicked.connect(self._add_ingredient)
        lay.addWidget(add_ing_btn)

        # Catatan
        lay.addWidget(_lbl(tr("dialog_notes"), size=12))
        self.notes = _input(tr("food_recipe_instructions_ph"))
        lay.addWidget(self.notes)

        lay.addSpacing(8)
        save_btn = _btn(tr("food_recipe_save"), "solid", self._save)
        lay.addWidget(save_btn)

        root.addWidget(_scrolled(content))

    def _add_ingredient(self):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("food_ingredient_picker_title"))
        dlg.setMinimumSize(450, 400)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)

        layout.addWidget(QLabel(tr("food_ingredient_search_label")))
        search_input = QLineEdit()
        search_input.setPlaceholderText(tr("food_ingredient_search_ph"))
        search_input.setMinimumHeight(36)
        layout.addWidget(search_input)

        layout.addWidget(QLabel(tr("food_ingredient_select_label")))
        combo = QComboBox()
        combo.setMinimumHeight(42)
        layout.addWidget(combo)

        # Ambil semua makanan
        all_foods = db.get_food_items(self.user_id)
        # Simpan dalam bentuk list of (id, display_text, icon, name)
        foods_data = [(f["id"], f"{f['icon']} {f['name']} - {f['calories']:.0f} kcal", f["icon"], f["name"]) for f in all_foods]

        def update_combo(text=""):
            combo.blockSignals(True)
            combo.clear()
            search_text = text.strip().lower()
            for fid, display, icon, name in foods_data:
                if search_text == "" or search_text in name.lower() or search_text in display.lower():
                    combo.addItem(display, fid)
            combo.blockSignals(False)

        # Isi combo awal (semua)
        update_combo("")

        # Hubungkan event textChanged
        search_input.textChanged.connect(update_combo)

        layout.addWidget(QLabel(tr("food_ingredient_qty_label")))
        qty = QDoubleSpinBox()
        qty.setRange(0.1, 10)
        qty.setValue(1)
        qty.setSuffix(tr("unit_quantity"))
        layout.addWidget(qty)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        # Jalankan dialog
        if dlg.exec() == QDialog.DialogCode.Accepted:
            food_id = combo.currentData()
            if food_id is None:
                return
            # Cari nama makanan untuk ditampilkan di list
            food_name = next((disp for fid, disp, _, _ in foods_data if fid == food_id), "")
            quantity = qty.value()
            self.selected_items.append((food_id, quantity))
            self.ingredients_list.addItem(f"{food_name} x{quantity:.1f}")

    def _save(self):
        name = self.name.text().strip()
        if not name:
            _show(self, tr("msg_error"), tr("food_recipe_name_empty"), "error")
            return
        if not self.selected_items:
            _show(self, tr("msg_error"), tr("food_recipe_no_ingredient"), "error")
            return
        icon = self.icon.text().strip() or "🍲"
        serving = self.serving.value()
        notes = self.notes.text()
        r = db.add_recipe(self.user_id, name, icon, serving, notes, self.selected_items)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), tr("food_recipe_saved", name=name), "success")
            self.accept()
        else:
            SND.error()
            _show(self, tr("gagal_title"), r.get("msg", "Gagal menyimpan resep"), "error")

class SetGoalsDialog(QDialog):
    """Dialog untuk mengatur target nutrisi harian."""
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.setWindowTitle(tr("food_goals_title_window"))
        self.setMinimumSize(400, 350)
        self.setStyleSheet(build_ss())
        self._build()

    def _build(self):
        goals = db.get_nutrition_goals(self.user_id)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        layout.addWidget(_lbl(tr("health_daily_targets"), "section", 14, True))
        layout.addWidget(_sep())

        layout.addWidget(_lbl(tr("food_calories_label"), size=12))
        self.calories = QSpinBox()
        self.calories.setRange(500, 10000)
        self.calories.setValue(goals["daily_calories"])
        layout.addWidget(self.calories)

        layout.addWidget(_lbl(tr("food_protein_label"), size=12))
        self.protein = QSpinBox()
        self.protein.setRange(0, 500)
        self.protein.setValue(goals["daily_protein"])
        layout.addWidget(self.protein)

        layout.addWidget(_lbl(tr("food_carbs_label"), size=12))
        self.carbs = QSpinBox()
        self.carbs.setRange(0, 500)
        self.carbs.setValue(goals["daily_carbs"])
        layout.addWidget(self.carbs)

        layout.addWidget(_lbl(tr("food_fat_label"), size=12))
        self.fat = QSpinBox()
        self.fat.setRange(0, 200)
        self.fat.setValue(goals["daily_fat"])
        layout.addWidget(self.fat)

        btn = _btn(tr("food_save_goals"), "solid", self._save)
        layout.addWidget(btn)

    def _save(self):
        db.update_nutrition_goals(self.user_id, self.calories.value(), self.protein.value(),
                                  self.carbs.value(), self.fat.value())
        SND.complete()
        self.accept()


class RecipeManagerDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.setWindowTitle(tr("recipe_add_title"))
        self.setMinimumSize(500, 400)
        self.setStyleSheet(build_ss())
        self._build()
        self.load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("food_recipe_manager_title"), "section", 14, True))
        add_btn = _btn(tr("food_recipe_add_btn"), "solid", self._add_recipe)
        hdr.addWidget(add_btn)
        layout.addLayout(hdr)
        layout.addWidget(_sep())

        self.recipe_list = QListWidget()
        self.recipe_list.itemDoubleClicked.connect(self._view_recipe)
        layout.addWidget(self.recipe_list)

        # Tombol aksi
        btn_layout = QHBoxLayout()
        use_btn = _btn(tr("food_recipe_log_today"), "gold", self._log_selected_recipe)
        delete_btn = _btn(tr("food_recipe_delete"), "danger", self._delete_selected)
        btn_layout.addWidget(use_btn)
        btn_layout.addWidget(delete_btn)
        layout.addLayout(btn_layout)

    def load(self):
        self.recipe_list.clear()
        recipes = db.get_recipes(self.user_id)
        for r in recipes:
            self.recipe_list.addItem(f"{r['icon']} {r['name']} ({r['serving_size']} porsi)")

    def _add_recipe(self):
        dlg = AddRecipeDialog(self.user_id, self)
        if dlg.exec():
            QTimer.singleShot(0, self.load)

    def _view_recipe(self, item):
        recipe_name = item.text().split(' ', 1)[1].split(' (')[0]
        recipes = db.get_recipes(self.user_id)
        recipe = next((r for r in recipes if r['name'] == recipe_name), None)
        if recipe:
            details = db.get_recipe_details(recipe['id'])
            if details:
                msg = f"🍲 {details['recipe']['name']}\nPorsi standar: {details['recipe']['serving_size']}\n\nBahan:\n"
                for i in details['items']:
                    msg += f"- {i['name']} x{i['quantity']:.1f} porsi\n"
                if details['recipe']['notes']:
                    msg += f"\nCatatan: {details['recipe']['notes']}"
                QMessageBox.information(self, tr("food_recipe_detail_title"), msg)

    def _log_selected_recipe(self):
        selected = self.recipe_list.currentItem()
        if not selected:
            return
        recipe_name = selected.text().split(' ', 1)[1].split(' (')[0]
        recipes = db.get_recipes(self.user_id)
        recipe = next((r for r in recipes if r['name'] == recipe_name), None)
        if not recipe:
            return
        # Tanyakan berapa porsi yang dimakan
        multiplier, ok = QInputDialog.getDouble(self, tr("food_serving_dialog_title"), tr("food_serving_dialog_msg", name=recipe['name']), 1, 0.25, 10, 1)
        if not ok:
            return
        # Tanyakan jenis makan
        meal_types = {"breakfast": tr("food_meal_breakfast"), "lunch": tr("food_meal_lunch"), "dinner": tr("food_meal_dinner"), "snack": tr("food_meal_snack")}
        meal, ok = QInputDialog.getItem(self, "Jenis Makan", "Pilih waktu makan:", list(meal_types.values()), 0, False)
        if not ok:
            return
        meal_key = {v: k for k, v in meal_types.items()}[meal]
        log_date = date.today().isoformat()
        r = db.log_recipe(self.user_id, recipe['id'], multiplier, meal_key, log_date, "")
        if r["ok"]:
            SND.complete()
            _show(self, tr('berhasil_title'), tr('food_recipe_log_success', name=recipe['name'], calories=r['calories']), "success")
            self.accept()  # tutup dialog, refresh FoodPage
        else:
            SND.error()
            _show(self, tr("gagal_title"), r.get("msg", tr("food_recipe_log_fail")), "error")

    def _delete_selected(self):
        selected = self.recipe_list.currentItem()
        if not selected:
            return
        recipe_name = selected.text().split(' ', 1)[1].split(' (')[0]
        recipes = db.get_recipes(self.user_id)
        recipe = next((r for r in recipes if r['name'] == recipe_name), None)
        if recipe:
            reply = QMessageBox.question(self, tr("confirm_title"), tr("food_recipe_delete_confirm", name=recipe_name), QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                db.delete_recipe(self.user_id, recipe['id'])
                SND.click()
                QTimer.singleShot(0, self.load)

# ═════════════════════════════════════════════════════════════════════════════
#  HEALTH DIALOG
# ═════════════════════════════════════════════════════════════════════════════
class HealthGoalsDialog(QDialog):
    def __init__(self, user_id, parent=None):
        super().__init__(parent)
        
        self.user_id = user_id
        self.setWindowTitle(tr("health_target_title"))
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.steps_goal_input = QSpinBox()
        self.steps_goal_input.setRange(1000, 50000)
        self.steps_goal_input.setSingleStep(500)
        self.steps_goal_input.setSuffix(tr("unit_steps"))
        layout.addWidget(_lbl(tr("health_steps_goal_label"), size=12))
        layout.addWidget(self.steps_goal_input)

        self.sleep_goal_input = QDoubleSpinBox()
        self.sleep_goal_input.setRange(4.0, 12.0)
        self.sleep_goal_input.setSingleStep(0.5)
        self.sleep_goal_input.setSuffix(tr("unit_hours"))
        layout.addWidget(_lbl(tr("health_sleep_goal_label"), size=12))
        layout.addWidget(self.sleep_goal_input)

        self.water_goal_input = QSpinBox()
        self.water_goal_input.setRange(1000, 10000)
        self.water_goal_input.setSingleStep(250)
        self.water_goal_input.setSuffix(tr("unit_ml"))
        layout.addWidget(_lbl(tr("health_water_goal_label"), size=12))
        layout.addWidget(self.water_goal_input)

        self.calorie_goal_input = QSpinBox()
        self.calorie_goal_input.setRange(1000, 5000)
        self.calorie_goal_input.setSingleStep(100)
        self.calorie_goal_input.setSuffix(tr("unit_kcal"))
        layout.addWidget(_lbl(tr("health_calorie_goal_label"), size=12))
        layout.addWidget(self.calorie_goal_input)

        goals = db.get_health_goals(self.user_id)
        nutrition_goals = db.get_nutrition_goals(self.user_id)
        self.steps_goal_input.setValue(goals.get('daily_steps', 10000))
        self.sleep_goal_input.setValue(goals.get('daily_sleep_hours', 7.0))
        self.water_goal_input.setValue(db.get_water_goal(self.user_id))
        self.calorie_goal_input.setValue(nutrition_goals.get('daily_calories', 2000))

        buttons = QHBoxLayout()
        save_btn = _btn(tr("health_save_goals_btn"), "solid", self.accept)
        cancel_btn = _btn(tr("forgot_cancel_btn"), "ghost", self.reject)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)

    def accept(self):
        db.update_health_goals(
            self.user_id,
            self.steps_goal_input.value(),
            self.sleep_goal_input.value()
        )
        db.set_water_goal(self.user_id, self.water_goal_input.value())
        current_nutrition = db.get_nutrition_goals(self.user_id)
        db.update_nutrition_goals(
            self.user_id,
            self.calorie_goal_input.value(),
            current_nutrition.get('daily_protein', 80),
            current_nutrition.get('daily_carbs', 250),
            current_nutrition.get('daily_fat', 70)
        )
        super().accept()

    def reject(self):
        super().reject()

# ══════════════════════════════════════════════════════════════════════════════
#  HEALTH & FOOD PAGE
# ══════════════════════════════════════════════════════════════════════════════
class HealthFoodPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.current_date = date.today()
        self._build()
        AppState.register(self.load)

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        container = QWidget()
        self.main_layout = QVBoxLayout(container)
        self.main_layout.setSpacing(16)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # ── Header / Judul Halaman (konsisten dengan halaman lain) ──
        title_widget = QWidget()
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.addWidget(_lbl(tr("health_title"), "section", 14, True))
        title_layout.addStretch()
        self.main_layout.addWidget(title_widget)
        self.main_layout.addWidget(_sep())

        # Date selector
        self._build_date_selector()
        # Nutrition summary
        self._build_nutrition_summary()
        # BMI & auto goals
        self._build_bmi_section()
        # Action buttons
        self._build_action_buttons()
        # Food log
        self._build_food_log_section()
        # Water section
        self._build_water_section()
        # Health status cards
        self._build_health_status_section()
        # Health input
        self._build_health_input_section()
        # History charts & tips
        self._build_history_charts()

        scroll.setWidget(container)
        root_layout = QVBoxLayout(self)
        root_layout.addWidget(scroll)
        self.load()

    # ---------- Date selector ----------
    def _build_date_selector(self):
        date_widget = QWidget()
        date_layout = QHBoxLayout(date_widget)
        date_layout.setContentsMargins(0, 0, 0, 0)
        self.prev_date_btn = _btn(tr("nav_prev"), h=32)
        self.prev_date_btn.setMinimumWidth(40)
        self.prev_date_btn.clicked.connect(self._prev_date)
        self.date_label = _lbl("", size=13, bold=True)
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.next_date_btn = _btn(tr("nav_next"), h=32)
        self.next_date_btn.setMinimumWidth(40)
        self.next_date_btn.clicked.connect(self._next_date)
        self.today_btn = _btn(tr("food_today"), h=32)
        self.today_btn.clicked.connect(self._today)
        date_layout.addWidget(self.prev_date_btn)
        date_layout.addWidget(self.date_label, 1)
        date_layout.addWidget(self.next_date_btn)
        date_layout.addWidget(self.today_btn)
        self.main_layout.addWidget(date_widget)

    def _prev_date(self):
        self.current_date -= timedelta(days=1)
        self.load()
    def _next_date(self):
        self.current_date += timedelta(days=1)
        self.load()
    def _today(self):
        self.current_date = date.today()
        self.load()

    # ---------- Nutrition summary ----------
    def _build_nutrition_summary(self):
        summary_widget = QWidget()
        summary_layout = QHBoxLayout(summary_widget)
        summary_layout.setSpacing(12)
        self.cal_card = self._stat_card(tr("food_cal_stat"), "0 / 0 kcal", "#f0a800")
        self.protein_card = self._stat_card(tr("food_protein_stat"), "0 / 0 g", "#80c000")
        self.carbs_card = self._stat_card(tr("food_carbs_stat"), "0 / 0 g", "#4da6ff")
        self.fat_card = self._stat_card(tr("food_fat_stat"), "0 / 0 g", "#e05050")
        summary_layout.addWidget(self.cal_card)
        summary_layout.addWidget(self.protein_card)
        summary_layout.addWidget(self.carbs_card)
        summary_layout.addWidget(self.fat_card)
        self.main_layout.addWidget(summary_widget)

        self.cal_progress = QProgressBar()
        self.cal_progress.setMinimumHeight(12)
        self.cal_progress.setTextVisible(False)
        self.main_layout.addWidget(self.cal_progress)

        goals_btn = _btn(tr("food_set_goals_btn"), "gold", self._open_goals)
        self.main_layout.addWidget(goals_btn)

    def _stat_card(self, title, value, color):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(f"color:{color}; font-size:16px; font-weight:bold;")
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        card.value_label = lbl_value
        return card

    def _open_goals(self):
        dlg = SetGoalsDialog(self.user_id, self)
        if dlg.exec():
            self.load()

    # ---------- Water section ----------
    def _build_water_section(self):
        water_group = QGroupBox(tr("food_tab_water"))
        water_layout = QVBoxLayout(water_group)

        goal_widget = QWidget()
        goal_layout = QHBoxLayout(goal_widget)
        self.water_goal_label = QLabel(tr("food_water_goal_default"))
        self.water_goal_label.setStyleSheet(f"color:{_T('light')}; font-weight:bold;")
        set_goal_btn = _btn(tr("food_water_set_goal"), "gold", self._set_water_goal)
        goal_layout.addWidget(self.water_goal_label)
        goal_layout.addStretch()
        goal_layout.addWidget(set_goal_btn)
        water_layout.addWidget(goal_widget)

        self.water_progress = QProgressBar()
        self.water_progress.setMinimumHeight(20)
        self.water_progress.setTextVisible(True)
        self.water_progress.setFormat("%v / %m ml")
        water_layout.addWidget(self.water_progress)

        add_water_widget = QWidget()
        add_water_layout = QHBoxLayout(add_water_widget)
        for amount, label in [(250, tr("food_water_add_250")), (500, tr("food_water_add_500")), (1000, tr("food_water_add_1000"))]:
            btn = _btn(label, "solid")
            btn.clicked.connect(partial(self._add_water, amount))
            add_water_layout.addWidget(btn)
        water_layout.addWidget(add_water_widget)

        custom_row = QHBoxLayout()
        self.water_custom = QSpinBox()
        self.water_custom.setRange(1, 5000)
        self.water_custom.setValue(1000)
        self.water_custom.setSuffix(tr("unit_ml"))
        custom_btn = _btn(tr("dialog_add"), h=36)
        custom_btn.clicked.connect(lambda: self._add_water(self.water_custom.value()))
        custom_row.addWidget(QLabel(tr("food_water_custom_label")))
        custom_row.addWidget(self.water_custom)
        custom_row.addWidget(custom_btn)
        water_layout.addLayout(custom_row)

        self.water_logs_group = QGroupBox(tr("food_water_log_title"))
        self.water_logs_layout = QVBoxLayout(self.water_logs_group)
        water_layout.addWidget(self.water_logs_group)

        self.main_layout.addWidget(water_group)

    def _add_water(self, amount):
        db.add_water_log(self.user_id, amount, self.current_date.isoformat())
        SND.complete()
        self.load()
        total = db.get_water_total(self.user_id, self.current_date.isoformat())
        goal = db.get_water_goal(self.user_id)
        if total >= goal and total - amount < goal:
            db.gain_xp_gold(self.user_id, 10, 2)
            db.add_notification(self.user_id, tr("water_goal_reached"), "success")
            AppState.refresh()

    def _delete_water_log(self, log_id):
        db.delete_water_log(self.user_id, log_id)
        SND.click()
        self.load()

    def _set_water_goal(self):
        from PyQt6.QtWidgets import QInputDialog
        current = db.get_water_goal(self.user_id)
        new_goal, ok = QInputDialog.getInt(self, tr("food_water_goal_dialog_title"), tr("food_water_goal_dialog_label"), current, 500, 10000, 100)
        if ok:
            db.set_water_goal(self.user_id, new_goal)
            SND.notify()
            self.load()

    # ---------- BMI section ----------
    def _build_bmi_section(self):
        bmi_group = QGroupBox(tr("food_bmi_title"))
        bmi_layout = QVBoxLayout(bmi_group)
        form = QFormLayout()
        self.height_input = QDoubleSpinBox()
        self.height_input.setRange(100, 250)
        self.height_input.setSuffix(tr("unit_cm"))
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setRange(30, 300)
        self.weight_input.setSuffix(tr("unit_kg"))
        self.age_input = QSpinBox()
        self.age_input.setRange(15, 100)
        self.gender_combo = QComboBox()
        self.gender_combo.addItems([tr("food_bmi_gender_m"), tr("food_bmi_gender_f")])
        self.activity_combo = QComboBox()
        self.activity_combo.addItems([tr("food_bmi_activity_sedentary"), tr("food_bmi_activity_light"),
                                      tr("food_bmi_activity_moderate"), tr("food_bmi_activity_active"),
                                      tr("food_bmi_activity_very_active")])
        form.addRow(tr("food_bmi_height"), self.height_input)
        form.addRow(tr("food_bmi_weight"), self.weight_input)
        form.addRow(tr("food_bmi_age"), self.age_input)
        form.addRow(tr("food_bmi_gender"), self.gender_combo)
        form.addRow(tr("food_bmi_activity"), self.activity_combo)
        bmi_layout.addLayout(form)

        btn_row = QHBoxLayout()
        calc_btn = _btn(tr("food_bmi_calc"), "solid", self._calculate_bmi)
        set_target_btn = _btn(tr("food_bmi_set_target"), "gold", self._set_auto_goals)
        btn_row.addWidget(calc_btn)
        btn_row.addWidget(set_target_btn)
        bmi_layout.addLayout(btn_row)

        self.bmi_result_label = QLabel(tr("food_bmi_result"))
        self.bmi_result_label.setWordWrap(True)
        self.bmi_result_label.setStyleSheet(f"color:{_T('accent')}; font-weight:bold; padding:8px; background:{_T('panel')}; border-radius:6px;")
        bmi_layout.addWidget(self.bmi_result_label)

        self.main_layout.addWidget(bmi_group)
        self.load_bmi_settings()

    def load_bmi_settings(self):
        settings = db.get_user_bmi_settings(self.user_id)
        self.height_input.setValue(settings["height_cm"])
        self.weight_input.setValue(settings["weight_kg"])
        self.age_input.setValue(settings["age"])
        idx = self.gender_combo.findText(settings["gender"])
        if idx >= 0:
            self.gender_combo.setCurrentIndex(idx)
        activity_factors = [1.2, 1.375, 1.55, 1.725, 1.9]
        if settings["activity_factor"] in activity_factors:
            idx = activity_factors.index(settings["activity_factor"])
            self.activity_combo.setCurrentIndex(idx)

    def _calculate_bmi(self):
        height = self.height_input.value() / 100
        weight = self.weight_input.value()
        bmi = weight / (height * height)
        if bmi < 18.5:
            status = tr("food_bmi_status_underweight")
            color = "#f0a800"
        elif 18.5 <= bmi < 25:
            status = tr("food_bmi_status_normal")
            color = "#80c000"
        elif 25 <= bmi < 30:
            status = tr("food_bmi_status_overweight")
            color = "#e05050"
        else:
            status = tr("food_bmi_status_obese")
            color = "#e05050"
        self.bmi_result_label.setText(tr("food_bmi_result_format", color=color, bmi=bmi, status=status))

    def _set_auto_goals(self):
        height = self.height_input.value()
        weight = self.weight_input.value()
        age = self.age_input.value()
        gender = self.gender_combo.currentText()
        activity_idx = self.activity_combo.currentIndex()
        activity_factors = [1.2, 1.375, 1.55, 1.725, 1.9]
        factor = activity_factors[activity_idx]
        if gender == "Laki-laki":
            bmr = 10 * weight + 6.25 * height - 5 * age + 5
        else:
            bmr = 10 * weight + 6.25 * height - 5 * age - 161
        tdee = bmr * factor
        recommended_cal = int(tdee)
        recommended_protein = int(weight * 1.6)
        recommended_carbs = int(recommended_cal * 0.5 / 4)
        recommended_fat = int(recommended_cal * 0.3 / 9)
        db.update_nutrition_goals(self.user_id, recommended_cal, recommended_protein,
                                 recommended_carbs, recommended_fat)
        db.update_user_bmi_settings(self.user_id, height, weight, age, gender, factor)
        db.log_user_weight(self.user_id, weight)
        SND.complete()
        _show(self, tr("food_target_updated_title"),
              tr("food_target_updated_msg", cal=recommended_cal),
              "success")
        self.load()
        AppState.refresh()

    # ---------- Food log section ----------
    def _build_food_log_section(self):
        self.logs_group = QGroupBox(tr("food_log_group_title"))
        self.logs_layout = QVBoxLayout(self.logs_group)
        self.main_layout.addWidget(self.logs_group)

    def _refresh_food_log(self, log_date):
        # Bersihkan layout
        while self.logs_layout.count():
            item = self.logs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        logs = db.get_food_logs(self.user_id, log_date)
        if not logs:
            empty = QLabel(tr("food_no_logs_today"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:20px;")
            self.logs_layout.addWidget(empty)
            return

        meal_order = ["breakfast", "lunch", "dinner", "snack"]
        meal_names = {"breakfast": tr("food_meal_breakfast"),
                      "lunch": tr("food_meal_lunch"),
                      "dinner": tr("food_meal_dinner"),
                      "snack": tr("food_meal_snack")}

        for meal in meal_order:
            meal_logs = [l for l in logs if l["meal_type"] == meal]
            if meal_logs:
                # Label jenis makan
                meal_label = QLabel(meal_names[meal])
                meal_label.setStyleSheet(f"color:{_T('light')}; font-weight:bold; margin-top:8px;")
                self.logs_layout.addWidget(meal_label)

                # Tampilkan kartu log
                for log in meal_logs:
                    card = self._make_food_log_card(log)
                    self.logs_layout.addWidget(card)

                # ── Drop area untuk memindahkan log ke meal type ini ──
                drop_area = QFrame()
                drop_area.setAcceptDrops(True)
                drop_area.setMinimumHeight(40)
                drop_area.setStyleSheet(f"""
                    QFrame {{
                        border: 2px dashed {_T('border')};
                        border-radius: 6px;
                        background: {_T('bg')};
                        margin: 4px 0;
                    }}
                    QFrame:hover {{
                        border-color: {_T('accent')};
                        background: {_T('panel')};
                    }}
                """)

                def make_drop_handler(target_meal):
                    def handler(event):
                        if not event.mimeData().hasFormat("application/x-craftlife-card"):
                            event.ignore()
                            return
                        raw = event.mimeData().data("application/x-craftlife-card")
                        info = json.loads(raw.data().decode())
                        if info["mode"] == "food" and info["user_id"] == self.user_id:
                            # Gunakan move_item_to_folder dengan mode "food"
                            db.move_item_to_folder(self.user_id, "food", info["item_id"], target_meal)
                            self.load()
                            event.acceptProposedAction()
                        else:
                            event.ignore()
                    return handler

                def make_drag_enter_handler():
                    def handler(event):
                        if event.mimeData().hasFormat("application/x-craftlife-card"):
                            event.acceptProposedAction()
                        else:
                            event.ignore()
                    return handler

                drop_area.dropEvent = make_drop_handler(meal)
                drop_area.dragEnterEvent = make_drag_enter_handler()

                self.logs_layout.addWidget(drop_area)

    def _make_food_log_card(self, log: dict) -> QFrame:
        content = QWidget()
        row = QHBoxLayout(content)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(10)

        icon = QLabel(log["icon"])
        icon.setFont(QFont("Segoe UI", 22))
        icon.setMinimumWidth(40)
        row.addWidget(icon)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(tr("food_log_name_serving", name=log['name'], serving=log['serving']))
        name.setStyleSheet(f"font-size:13px; font-weight:bold; color:{_T('text')};")
        info.addWidget(name)

        nut = QLabel(tr("food_nutrition_detail", cal=log['calories'], protein=log['protein'], carbs=log['carbs'], fat=log['fat']))
        nut.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        info.addWidget(nut)

        if log.get("notes"):
            notes = QLabel(f"📝 {log['notes']}")
            notes.setStyleSheet(f"color:{_T('muted')}; font-size:10px; font-style:italic;")
            info.addWidget(notes)

        row.addLayout(info, 1)

        del_btn = _btn("🗑", "danger", h=32)
        del_btn.setMinimumWidth(36)
        del_btn.clicked.connect(lambda _, lid=log["id"]: self._delete_food_log(lid))
        row.addWidget(del_btn)

        card = DraggableCard(
            item_id=log["id"],
            mode="food",
            user_id=self.user_id,
            current_folder_id=log.get("meal_type"),
            content_widget=content,
            parent=self
        )
        return card

    def _delete_food_log(self, log_id):
        db.delete_food_log(self.user_id, log_id)
        SND.click()
        self.load()

    # ---------- Health status section ----------
    def _build_health_status_section(self):
        self.status_grid_layout = QGridLayout()
        self.status_grid_layout.setSpacing(10)
        self.main_layout.addLayout(self.status_grid_layout)

        self.note_display_widget = QWidget()
        note_layout = QHBoxLayout(self.note_display_widget)
        note_layout.setContentsMargins(0, 8, 0, 0)
        
        self.note_display_label = QLabel()
        self.note_display_label.setWordWrap(True)
        self.note_display_label.setStyleSheet(
            f"color:{_T('muted')}; background:{_T('panel')}; "
            f"padding:10px; border-radius:6px; border:1px solid {_T('border')};"
            f"font-style:italic;"
        )
        note_layout.addWidget(self.note_display_label)
        self.main_layout.addWidget(self.note_display_widget)

    def _refresh_health_status(self, log_date):
        # Bersihkan grid
        while self.status_grid_layout.count():
            item = self.status_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        # Ambil data
        conn = db.get_conn()
        today_row = conn.execute(
            "SELECT * FROM health_logs WHERE user_id=? AND log_date=?",
            (self.user_id, log_date)
        ).fetchone()
        conn.close()
        today_log = dict(today_row) if today_row else None

        health_goals = db.get_health_goals(self.user_id)
        water_total = db.get_water_total(self.user_id, log_date)
        water_goal = db.get_water_goal(self.user_id)
        nutrition = db.get_nutrition_summary(self.user_id, log_date)
        nutrition_goals = db.get_nutrition_goals(self.user_id)
        burned = db.get_total_calories_burned_today(self.user_id, log_date)
        net_cal = nutrition['calories'] - burned
        steps_goal = health_goals.get('daily_steps', 10000)
        sleep_goal = health_goals.get('daily_sleep_hours', 7.0)

        # Berat: prioritas historis, fallback ke user_health_goals
        if today_log and today_log.get('weight_kg') is not None:
            weight_kg = today_log['weight_kg']
        else:
            weight_kg = health_goals.get('weight_kg', 70.0)
        height_cm = health_goals.get('height_cm', 170)

        # Buat kartu
        cards = [
            self._stat_card(tr("health_steps"), tr("health_steps_value", steps=today_log['steps'] if today_log else 0, goal=steps_goal), "#80c000"),
            self._stat_card(tr("health_sleep"), tr("health_sleep_value", sleep=today_log['sleep_hours'] if today_log else 0, goal=sleep_goal), "#4da6ff"),
            self._stat_card(tr("health_water"), tr("health_water_value", water=water_total, goal=water_goal), "#38bdf8"),
            self._stat_card(tr("health_mood"), tr("health_mood_value", mood=(today_log['mood'] if today_log else "normal").capitalize()), "#f0a800"),
            self._stat_card(tr("health_weight"), tr("health_weight_value", weight=weight_kg), "#a97fff"),
            self._stat_card(tr("health_height"), tr("health_height_value", height=height_cm), "#a97fff"),
            self._stat_card(tr("health_hr"), tr("health_hr_value", hr=today_log.get('resting_hr', 0) if today_log else 0), "#e05050"),
            self._stat_card(tr("health_stress"), tr("health_stress_value", stress=(today_log.get('stress_level','normal') if today_log else "normal").capitalize()), "#80c000"),
            self._stat_card(tr("health_calories"), tr("health_calories_value", cal=nutrition['calories'], goal=nutrition_goals['daily_calories']), "#ff9f1c"),
            self._stat_card(tr("health_protein"), tr("health_protein_value", protein=nutrition['protein'], goal=nutrition_goals['daily_protein']), "#f4a261"),
            self._stat_card(tr("health_burned"), tr("health_burned_value", burned=burned), "#e76f51"),
            self._stat_card(tr("health_net_calories"), tr("health_net_calories_value", net=net_cal, goal=nutrition_goals['daily_calories']), "#2a9d8f"),
        ]
        for i, card in enumerate(cards):
            row = i // 4
            col = i % 4
            self.status_grid_layout.addWidget(card, row, col)

        # ── Tampilkan Catatan (Note) jika ada ──
        if today_log and today_log.get('notes'):
            self.note_display_label.setText(f"📝  {today_log['notes']}")
            self.note_display_label.setStyleSheet(
                f"color:{_T('text')}; background:{_T('panel')}; "
                f"padding:10px; border-radius:6px; border:1px solid {_T('border')};"
            )
        else:
            self.note_display_label.setText(tr("health_note_placeholder"))
            self.note_display_label.setStyleSheet(
                f"color:{_T('muted')}; background:{_T('panel')}; "
                f"padding:10px; border-radius:6px; border:1px solid {_T('border')};"
                f"font-style:italic;"
            )

    # ---------- Health input section ----------
    def _build_health_input_section(self):
        input_group = QGroupBox(tr("health_tab_input"))
        input_layout = QVBoxLayout(input_group)

        phys_box = QGroupBox(tr("health_activity_group"))
        phys_form = QFormLayout(phys_box)
        self.steps_input = QSpinBox()
        self.steps_input.setRange(0, 50000)
        self.steps_input.setSuffix(tr("unit_steps"))
        self.hr_input = QSpinBox()
        self.hr_input.setRange(0, 220)
        self.hr_input.setSuffix(" bpm")

        self.weight_input_daily = QDoubleSpinBox()
        self.weight_input_daily.setRange(30, 300)
        self.weight_input_daily.setSingleStep(0.5)
        self.weight_input_daily.setSuffix(tr("unit_kg"))
        self.height_input_daily = QDoubleSpinBox()
        self.height_input_daily.setRange(100, 250)
        self.height_input_daily.setSingleStep(0.5)
        self.height_input_daily.setSuffix(tr("unit_cm"))

        phys_form.addRow(tr("health_steps_label"), self.steps_input)
        phys_form.addRow(tr("health_hr_label"), self.hr_input)
        phys_form.addRow(tr("health_weight"), self.weight_input_daily)
        phys_form.addRow(tr("health_height"), self.height_input_daily)
        input_layout.addWidget(phys_box)

        sleep_box = QGroupBox(tr("health_sleep_group"))
        sleep_form = QFormLayout(sleep_box)
        self.sleep_input = QDoubleSpinBox()
        self.sleep_input.setRange(0, 24)
        self.sleep_input.setSingleStep(0.5)
        self.sleep_input.setSuffix(tr("unit_hours"))
        self.stress_combo = QComboBox()
        self.stress_combo.addItem(tr("health_stress_low"), "low")
        self.stress_combo.addItem(tr("health_stress_normal"), "normal")
        self.stress_combo.addItem(tr("health_stress_high"), "high")
        self.mood_combo = QComboBox()
        self.mood_combo.addItem(tr("health_mood_happy"), "happy")
        self.mood_combo.addItem(tr("health_mood_normal"), "normal")
        self.mood_combo.addItem(tr("health_mood_tired"), "tired")
        self.mood_combo.addItem(tr("health_mood_sad"), "sad")
        sleep_form.addRow(tr("health_sleep_label"), self.sleep_input)
        sleep_form.addRow(tr("health_stress_label"), self.stress_combo)
        sleep_form.addRow(tr("health_mood_label"), self.mood_combo)
        input_layout.addWidget(sleep_box)

        notes_box = QGroupBox(tr("health_notes_group"))
        notes_vlay = QVBoxLayout(notes_box)
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText(tr("health_notes_placeholder"))
        notes_vlay.addWidget(self.notes_input)
        input_layout.addWidget(notes_box)

        save_btn = _btn(tr("health_save"), "solid", self._save_health)
        input_layout.addWidget(save_btn)
        self.main_layout.addWidget(input_group)

    def _refresh_health_input(self, log_date):
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM health_logs WHERE user_id=? AND log_date=?", (self.user_id, log_date)).fetchone()
        conn.close()
        today_log = dict(row) if row else None

        # Ambil goals untuk fallback
        health_goals = db.get_health_goals(self.user_id)

        if today_log:
            self.steps_input.setValue(today_log.get('steps', 0))
            self.sleep_input.setValue(today_log.get('sleep_hours', 0))
            self.hr_input.setValue(today_log.get('resting_hr', 0))
            # ── AMBIL BERAT & TINGGI DARI LOG (jika ada) ──
            self.weight_input_daily.setValue(today_log.get('weight_kg', health_goals.get('weight_kg', 70.0)))
            self.height_input_daily.setValue(today_log.get('height_cm', health_goals.get('height_cm', 170.0)))
            self.mood_combo.setCurrentIndex(self.mood_combo.findData(today_log.get('mood', 'normal')))
            self.stress_combo.setCurrentIndex(self.stress_combo.findData(today_log.get('stress_level', 'normal')))
            self.notes_input.setText(today_log.get('notes', ''))
        else:
            self.steps_input.setValue(0)
            self.sleep_input.setValue(0)
            self.hr_input.setValue(0)
            # ── FALLBACK KE GOALS ──
            self.weight_input_daily.setValue(health_goals.get('weight_kg', 70.0))
            self.height_input_daily.setValue(health_goals.get('height_cm', 170.0))
            self.mood_combo.setCurrentIndex(1)
            self.stress_combo.setCurrentIndex(1)
            self.notes_input.clear()

    def _save_health(self):
        log_date = self.current_date.isoformat()
        water_total = db.get_water_total(self.user_id, log_date)
        nutrition = db.get_nutrition_summary(self.user_id, log_date)
        calories_burned = db.get_total_calories_burned_today(self.user_id, log_date)
        net_calories = nutrition['calories'] - calories_burned

        steps = self.steps_input.value()
        sleep = self.sleep_input.value()
        resting_hr = self.hr_input.value()
        weight = self.weight_input_daily.value()
        height = self.height_input_daily.value()
        mood = self.mood_combo.currentData()
        stress = self.stress_combo.currentData()
        notes = self.notes_input.text()

        db.add_health_log(
            self.user_id, log_date,
            steps=steps,
            sleep_hours=sleep,
            water_ml=water_total,
            weight_kg=weight,                   # kirim berat
            resting_hr=resting_hr,
            stress_level=stress,
            mood=mood,
            notes=notes,
            net_calories=net_calories
        )

        # ── UPDATE JUGA KE user_health_goals (agar BMI dan grafik konsisten) ──
        current_goals = db.get_health_goals(self.user_id)
        db.update_health_goals(
            self.user_id,
            current_goals.get('daily_steps', 10000),
            current_goals.get('daily_sleep_hours', 7.0),
            height_cm=height,
            weight_kg=weight
        )

        SND.complete()
        _show(self, tr("saved_title"), tr("health_data_saved"), "success")
        self.load()
        AppState.refresh()

    # ---------- History charts ----------
    def _build_history_charts(self):
        # Trend cards
        trend_group = QGroupBox(tr("health_avg_7days"))
        trend_layout = QHBoxLayout(trend_group)
        self.avg_steps_card = self._trend_card(tr("health_avg_steps"), "0", tr("health_avg_7days_suffix"), "#80c000")
        self.avg_sleep_card = self._trend_card(tr("health_avg_sleep"), "0 jam", tr("health_avg_7days_suffix"), "#4da6ff")
        self.avg_water_card = self._trend_card(tr("health_avg_water"), "0 ml", tr("health_avg_7days_suffix"), "#38bdf8")
        self.avg_hr_card = self._trend_card(tr("health_avg_hr"), "0 bpm", tr("health_avg_7days_suffix"), "#e05050")
        trend_layout.addWidget(self.avg_steps_card)
        trend_layout.addWidget(self.avg_sleep_card)
        trend_layout.addWidget(self.avg_water_card)
        trend_layout.addWidget(self.avg_hr_card)
        self.main_layout.addWidget(trend_group)

        self.weight_chart_label = QLabel()
        self.weight_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        weight_group = QGroupBox(tr("health_weight_trend"))
        weight_group_layout = QVBoxLayout(weight_group)
        weight_group_layout.addWidget(self.weight_chart_label)
        self.main_layout.addWidget(weight_group)

        self.height_chart_label = QLabel()
        self.height_chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        height_group = QGroupBox(tr("health_height_trend"))
        height_group_layout = QVBoxLayout(height_group)
        height_group_layout.addWidget(self.height_chart_label)
        self.main_layout.addWidget(height_group)

        tips_group = QGroupBox(tr("health_tips"))
        tips_layout = QVBoxLayout(tips_group)
        self.tips_label = QLabel()
        self.tips_label.setWordWrap(True)
        tips_layout.addWidget(self.tips_label)
        self.main_layout.addWidget(tips_group)

    def _trend_card(self, title, value, note, color=_T("light")):
        card = _card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        t = QLabel(title)
        t.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        v = QLabel(value)
        v.setStyleSheet(f"color:{color}; font-size:16px; font-weight:bold;")
        n = QLabel(note)
        n.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        layout.addWidget(t)
        layout.addWidget(v)
        layout.addWidget(n)
        card.value_label = v
        return card

    def _refresh_history_charts(self):
        logs_7days = db.get_health_logs(self.user_id, days=7)
        health_goals = db.get_health_goals(self.user_id)
        water_goal = db.get_water_goal(self.user_id)
        # Rata-rata
        if logs_7days:
            avg_steps = sum(l['steps'] for l in logs_7days) // len(logs_7days)
            avg_sleep = round(sum(l['sleep_hours'] for l in logs_7days) / len(logs_7days), 1)
            avg_water = sum(l.get('water_ml', 0) for l in logs_7days) // len(logs_7days)
            avg_hr = sum(l.get('resting_hr', 0) for l in logs_7days) // len(logs_7days)
        else:
            avg_steps = avg_sleep = avg_water = avg_hr = 0
        self.avg_steps_card.value_label.setText(f"{avg_steps}")
        self.avg_sleep_card.value_label.setText(f"{avg_sleep} {tr('health_unit_hour')}")
        self.avg_water_card.value_label.setText(f"{avg_water} {tr('health_unit_ml')}")
        self.avg_hr_card.value_label.setText(f"{avg_hr} {tr('health_unit_bpm')}")

        # Grafik berat
        self._update_weight_chart(logs_7days)
        # Grafik tinggi
        self._update_height_chart(logs_7days, health_goals)
        # Tips
        self._update_tips(logs_7days)

    def _update_weight_chart(self, logs_7days):
        if not EXPORT_IMPORTS_OK:
            return
        try:
            import matplotlib.pyplot as plt
            from io import BytesIO
            from PyQt6.QtGui import QPixmap
            days = []
            weights = []
            for i in range(7):
                d = (date.today() - timedelta(days=6-i)).isoformat()
                days.append(d[5:])
                log = next((l for l in logs_7days if l['log_date'] == d), None)
                if log and log.get('weight_kg') is not None:
                    weights.append(float(log['weight_kg']))
                else:
                    weights.append(0.0)
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(days, weights, marker='o', color='#80c000', linewidth=2)
            ax.fill_between(days, weights, color='#80c000', alpha=0.2)
            ax.set_ylabel('Berat (kg)' if AppState.get_language()=="id" else 'Weight (kg)', color='#e8e8e8')
            ax.set_title(tr("health_chart_weight"), color='#7bbf3e')
            ax.set_facecolor('#2d2d2d')
            fig.patch.set_facecolor('#2d2d2d')
            ax.tick_params(colors='#e8e8e8')
            plt.setp(ax.get_xticklabels(), rotation=20, ha='right')
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.weight_chart_label.setPixmap(pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print(f"Weight chart error: {e}")

    def _update_height_chart(self, logs_7days, health_goals):
        if not EXPORT_IMPORTS_OK:
            return
        try:
            import matplotlib.pyplot as plt
            from io import BytesIO
            from PyQt6.QtGui import QPixmap
            height_cm = health_goals.get('height_cm', 170)
            days = []
            heights = []
            for i in range(7):
                d = (date.today() - timedelta(days=6-i)).isoformat()
                days.append(d[5:])
                heights.append(height_cm)
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.plot(days, heights, marker='o', color='#4da6ff', linewidth=2, linestyle='-')
            ax.fill_between(days, heights, color='#4da6ff', alpha=0.2)
            ax.set_ylabel('Tinggi (cm)' if AppState.get_language()=="id" else 'Height (cm)', color='#e8e8e8')
            ax.set_title(tr("health_chart_height"), color='#7bbf3e')
            ax.set_facecolor('#2d2d2d')
            fig.patch.set_facecolor('#2d2d2d')
            ax.tick_params(colors='#e8e8e8')
            plt.setp(ax.get_xticklabels(), rotation=20, ha='right')
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=80, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            pixmap = QPixmap()
            pixmap.loadFromData(buf.read())
            self.height_chart_label.setPixmap(pixmap.scaledToWidth(500, Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print(f"Height chart error: {e}")

    def _update_tips(self, logs_7days):
        today = date.today().isoformat()
        nutrition = db.get_nutrition_summary(self.user_id, today)
        burned = db.get_total_calories_burned_today(self.user_id, today)
        net_cal = nutrition['calories'] - burned
        goals = db.get_nutrition_goals(self.user_id)
        dynamic_tip = ""
        if net_cal < 0:
            dynamic_tip = tr("health_tip_calorie_deficit")
        elif net_cal > goals['daily_calories'] * 1.1:
            dynamic_tip = tr("health_tip_calorie_surplus")
        else:
            dynamic_tip = tr("health_tip_calorie_normal")
        import random
        tip_keys = [f"health_tip_static_{i}" for i in range(1, 8)]
        random_tip = tr(random.choice(tip_keys))
        self.tips_label.setText(f"{random_tip} {dynamic_tip}")

    # ---------- Action buttons ----------
    def _build_action_buttons(self):
        btn_layout = QHBoxLayout()
        add_food_btn = _btn(tr("food_add_custom"), h=36)
        add_food_btn.clicked.connect(self._open_add_food)
        log_food_btn = _btn(tr("food_log"), "solid", self._open_log_food)
        recipe_btn = _btn(tr("food_recipes"), h=36)
        recipe_btn.clicked.connect(self._open_recipe_manager)
        export_btn = _btn(tr("food_export"), h=36)
        export_btn.clicked.connect(self._export_nutrition)
        btn_layout.addWidget(add_food_btn)
        btn_layout.addWidget(log_food_btn)
        btn_layout.addWidget(recipe_btn)
        btn_layout.addWidget(export_btn)
        self.main_layout.addLayout(btn_layout)

    def _open_add_food(self):
        dlg = AddFoodDialog(self.user_id, mode="add", parent=self)
        if dlg.exec():
            self.load()
    def _open_log_food(self):
        dlg = AddFoodDialog(self.user_id, mode="log", parent=self)
        if dlg.exec():
            self.load()
    def _open_recipe_manager(self):
        dlg = RecipeManagerDialog(self.user_id, self)
        if dlg.exec():
            self.load()
    def _export_nutrition(self):
        # Salin dari FoodPage._export_nutrition
        from PyQt6.QtWidgets import QFileDialog, QComboBox, QDialog, QVBoxLayout, QLabel, QDialogButtonBox
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("food_export_format_title"))
        dlg.setModal(True)
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(tr("economy_export_label")))
        combo = QComboBox()
        combo.addItems([tr("export_csv_option"), "Excel (.xlsx)", "Word (.docx)", "PDF (.pdf)"])
        layout.addWidget(combo)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        fmt = combo.currentText()
        food_data = db.get_food_export_data(self.user_id, days=30)
        if fmt == "CSV (.csv)":
            path, _ = QFileDialog.getSaveFileName(self, tr("food_save_csv"), "", tr("food_csv_filter"))
            if path:
                if not path.endswith(".csv"): path += ".csv"
                self._export_food_csv(food_data, path)
        elif fmt == "Excel (.xlsx)":
            path, _ = QFileDialog.getSaveFileName(self, tr("food_save_excel"), "", tr("food_xlsx_filter"))
            if path:
                if not path.endswith(".xlsx"): path += ".xlsx"
                self._export_food_excel(food_data, path)
        elif fmt == "Word (.docx)":
            path, _ = QFileDialog.getSaveFileName(self, tr("food_save_word"), "", tr("food_docx_filter"))
            if path:
                if not path.endswith(".docx"): path += ".docx"
                self._export_food_word(food_data, path)
        else:  # PDF
            path, _ = QFileDialog.getSaveFileName(self, tr("food_save_pdf"), "", tr("food_pdf_filter"))
            if path:
                if not path.endswith(".pdf"): path += ".pdf"
                self._export_food_pdf(food_data, path)

    # Ekspor (copy dari FoodPage)
    def _export_food_csv(self, food_data, filepath):
        import csv
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([tr("export_date"), tr("export_calories"), tr("export_protein"), tr("export_carbs"), tr("export_fat"), tr("export_water_ml"), tr("export_calories_burned"), tr("export_net_calories")])
                for fd in food_data:
                    writer.writerow([fd['date'], fd['calories'], fd['protein'], fd['carbs'], fd['fat'], fd['water_ml'], fd['calories_burned'], fd['net_calories']])
            _show(self, tr("berhasil_title"), f"Data nutrisi diekspor ke {filepath}", "success")
        except Exception as e:
            _show(self, tr("msg_error"), f"Gagal mengekspor CSV: {str(e)}", "error")

    def _export_food_excel(self, food_data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, tr("msg_error"), tr("export_lib_openpyxl"), "error")
            return
        try:
            import openpyxl
            from openpyxl.styles import Font, Alignment, PatternFill
            from openpyxl.utils import get_column_letter
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = tr("excel_sheet_nutrition")
            headers = [tr("export_date"), tr("export_calories"), tr("export_protein"), tr("export_carbs"), tr("export_fat"), tr("export_water_ml"), tr("export_calories_burned"), tr("export_net_calories")]
            ws.append(headers)
            for col in range(1, len(headers)+1):
                cell = ws.cell(row=1, column=col)
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill(start_color="5a8a2e", end_color="5a8a2e", fill_type="solid")
                cell.alignment = Alignment(horizontal="center")
            for fd in food_data:
                ws.append([fd['date'], fd['calories'], fd['protein'], fd['carbs'], fd['fat'], fd['water_ml'], fd['calories_burned'], fd['net_calories']])
            for col in ws.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                for cell in col:
                    try: max_len = max(max_len, len(str(cell.value)))
                    except: pass
                ws.column_dimensions[col_letter].width = min(max_len + 2, 20)
            wb.save(filepath)
            _show(self, tr("berhasil_title"), f"Data nutrisi diekspor ke {filepath}", "success")
        except Exception as e:
            _show(self, tr("msg_error"), f"Gagal mengekspor: {str(e)}", "error")

    def _export_food_word(self, food_data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, tr("msg_error"), tr("export_lib_docx"), "error") 
            return
        try:
            from docx import Document
            from docx.shared import Inches, Pt
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            doc = Document()
            title = doc.add_heading("CraftLife - Data Nutrisi & Air", 0)
            title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            total_cal = sum(fd['calories'] for fd in food_data)
            avg_cal = total_cal / len(food_data) if food_data else 0
            total_water = sum(fd['water_ml'] for fd in food_data)
            avg_water = total_water / len(food_data) if food_data else 0
            doc.add_heading("Ringkasan 30 Hari", level=1)
            doc.add_paragraph(f"📊 Total Kalori: {total_cal:.0f} kcal")
            doc.add_paragraph(f"📈 Rata-rata Kalori Harian: {avg_cal:.0f} kcal")
            doc.add_paragraph(f"💧 Total Air: {total_water:.0f} ml")
            doc.add_paragraph(f"🚰 Rata-rata Air Harian: {avg_water:.0f} ml")
            doc.add_heading("Data Harian", level=1)
            table = doc.add_table(rows=1, cols=8)
            table.style = 'Table Grid'
            hdr_cells = table.rows[0].cells
            headers = [tr("export_date"), tr("export_calories"), tr("export_protein"), tr("export_carbs"), tr("export_fat"), tr("export_water_ml"), tr("export_calories_burned"), tr("export_net_calories")]
            for i, h in enumerate(headers):
                hdr_cells[i].text = h
            for fd in food_data:
                row_cells = table.add_row().cells
                row_cells[0].text = fd['date']
                row_cells[1].text = str(fd['calories'])
                row_cells[2].text = str(fd['protein'])
                row_cells[3].text = str(fd['carbs'])
                row_cells[4].text = str(fd['fat'])
                row_cells[5].text = str(fd['water_ml'])
                row_cells[6].text = str(fd['calories_burned'])
                row_cells[7].text = str(fd['net_calories'])
            doc.save(filepath)
            _show(self, tr("berhasil_title"), f"Data nutrisi diekspor ke {filepath}", "success")
        except Exception as e:
            _show(self, tr("msg_error"), f"Gagal mengekspor: {str(e)}", "error")

    def _export_food_pdf(self, food_data, filepath):
        if not EXPORT_IMPORTS_OK:
            _show(self, tr("msg_error"), tr("export_lib_reportlab"), "error") 
            return
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
            story = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(name='Title', parent=styles['Title'], alignment=1, fontSize=16)
            story.append(Paragraph("CraftLife - Data Nutrisi & Air", title_style))
            story.append(Spacer(1, 0.2*inch))
            total_cal = sum(fd['calories'] for fd in food_data)
            avg_cal = total_cal / len(food_data) if food_data else 0
            total_water = sum(fd['water_ml'] for fd in food_data)
            avg_water = total_water / len(food_data) if food_data else 0
            summary_data = [
                ["Total Kalori 30 Hari", f"{total_cal:.0f} kcal"],
                ["Rata-rata Kalori Harian", f"{avg_cal:.0f} kcal"],
                ["Total Air 30 Hari", f"{total_water:.0f} ml"],
                ["Rata-rata Air Harian", f"{avg_water:.0f} ml"],
            ]
            sum_table = Table(summary_data, colWidths=[3*inch, 2*inch])
            sum_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#5a8a2e")),
                ('TEXTCOLOR', (0,0), (0,-1), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ]))
            story.append(sum_table)
            story.append(Spacer(1, 0.2*inch))
            data = [[tr("export_date"), tr("export_calories"), tr("export_protein"), tr("export_carbs"), tr("export_fat"), tr("export_water_ml"), tr("export_calories_burned"), tr("export_net_calories")]]
            for fd in food_data:
                data.append([fd['date'], str(fd['calories']), str(fd['protein']), str(fd['carbs']), str(fd['fat']), str(fd['water_ml']), str(fd['calories_burned']), str(fd['net_calories'])])
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5a8a2e")),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(table)
            doc.build(story)
            _show(self, tr("berhasil_title"), f"Data nutrisi diekspor ke {filepath}", "success")
        except Exception as e:
            _show(self, tr("msg_error"), f"Gagal mengekspor: {str(e)}", "error")

    # ---------- Bonus ----------
    def _check_nutrition_bonus(self, log_date):
        if self.current_date == date.today():
            r = db.check_daily_nutrition_bonus(self.user_id, log_date)
            if r.get("ok"):
                SND.level_up()
                msg = tr("health_nutrition_bonus_msg", xp=r['xp_gained'], gold=r['gold_gained'])
                if r.get("leveled_up"): 
                    msg += tr("level_up_bonus")
                _show(self, tr("bonus_title"), msg, "success")
                AppState.refresh()

    # ---------- LOAD ----------
    def load(self):
        if not AppState.user_id:
            return
        log_date = self.current_date.isoformat()
        today = date.today()
        self.date_label.setText(self.current_date.strftime("%A, %d %B %Y"))
        self.next_date_btn.setEnabled(self.current_date < today)

        # Refresh semua bagian
        self._refresh_nutrition_summary(log_date)
        self._refresh_water_section(log_date)
        self._refresh_food_log(log_date)
        self._refresh_health_status(log_date)
        self._refresh_health_input(log_date)
        self._refresh_history_charts()
        self._check_nutrition_bonus(log_date)

    def _refresh_nutrition_summary(self, log_date):
        summary = db.get_nutrition_summary(self.user_id, log_date)
        goals = db.get_nutrition_goals(self.user_id)
        self.cal_card.value_label.setText(f"{summary['calories']:.0f} / {goals['daily_calories']} kcal")
        self.protein_card.value_label.setText(f"{summary['protein']:.0f} / {goals['daily_protein']} g")
        self.carbs_card.value_label.setText(f"{summary['carbs']:.0f} / {goals['daily_carbs']} g")
        self.fat_card.value_label.setText(f"{summary['fat']:.0f} / {goals['daily_fat']} g")
        cal_percent = int((summary['calories'] / goals['daily_calories']) * 100) if goals['daily_calories'] > 0 else 0
        self.cal_progress.setValue(min(100, cal_percent))
        if cal_percent >= 100:
            self.cal_progress.setStyleSheet("QProgressBar::chunk { background: #e05050; }")
        elif cal_percent >= 80:
            self.cal_progress.setStyleSheet("QProgressBar::chunk { background: #f0a800; }")
        else:
            self.cal_progress.setStyleSheet("QProgressBar::chunk { background: #80c000; }")

    def _refresh_water_section(self, log_date):
        water_goal = db.get_water_goal(self.user_id)
        water_total = db.get_water_total(self.user_id, log_date)
        self.water_goal_label.setText(f"Target: {water_goal} ml")
        self.water_progress.setMaximum(water_goal)
        self.water_progress.setValue(water_total)
        self.water_progress.setFormat(tr("water_progress_format", current=water_total, goal=water_goal))
        # Refresh water logs
        while self.water_logs_layout.count():
            item = self.water_logs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        water_logs = db.get_water_logs(self.user_id, log_date)
        if not water_logs:
            empty = QLabel(tr("food_no_water_today"))
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{_T('muted')}; padding:20px;")
            self.water_logs_layout.addWidget(empty)
        else:
            for wlog in water_logs:
                card = _card()
                row = QHBoxLayout(card)
                row.setContentsMargins(12, 8, 12, 8)
                row.addWidget(QLabel("💧"))
                row.addWidget(QLabel(f"+{wlog['amount_ml']} ml"), 1)
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(wlog['created_at'])
                    time_str = dt.strftime("%H:%M")
                except:
                    time_str = wlog['created_at'][11:16]
                row.addWidget(QLabel(time_str))
                del_btn = _btn("🗑", "danger", h=28)
                del_btn.setMinimumWidth(36)
                del_btn.clicked.connect(lambda _, lid=wlog["id"]: self._delete_water_log(lid))
                row.addWidget(del_btn)
                self.water_logs_layout.addWidget(card)

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  Calendar Page
# ══════════════════════════════════════════════════════════════════════════════
class CalendarPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.holidays = {}
        self.notes = {}
        self._holidays_fetched = False
        self._loading_holidays = False
        self._build()
        AppState.register(self.load)
        AppState.register_lang_cb(self.load)

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # ── Header ──
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("calendar_title"), "section", 14, True))
        hdr.addStretch()

        self.prev_year_btn = _btn("◀", h=34)
        self.prev_year_btn.clicked.connect(self._prev_year)
        self.year_label = _lbl(str(self.current_year), size=14, bold=True)
        self.next_year_btn = _btn("▶", h=34)
        self.next_year_btn.clicked.connect(self._next_year)
        self.today_btn = _btn(tr("food_today"), h=34)
        self.today_btn.clicked.connect(self._goto_today)

        hdr.addWidget(self.prev_year_btn)
        hdr.addWidget(self.year_label)
        hdr.addWidget(self.next_year_btn)
        hdr.addWidget(self.today_btn)
        main_layout.addLayout(hdr)
        main_layout.addWidget(_sep())

        # ── Scroll Area ──
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

        self.months_container = QWidget()
        self.months_grid = QGridLayout(self.months_container)
        self.months_grid.setSpacing(20)               # lebih lega
        self.months_grid.setContentsMargins(10, 10, 10, 10)

        # Agar 3 kolom meregang rata
        for col in range(3):
            self.months_grid.setColumnStretch(col, 1)

        self.scroll_area.setWidget(self.months_container)
        main_layout.addWidget(self.scroll_area, 1)    # stretch agar memenuhi sisa ruang

        self.load()

    def load(self):
        if not AppState.user_id:
            return
        self._fetch_notes()
        if not self._holidays_fetched and not self._loading_holidays:
            self._loading_holidays = True
            QTimer.singleShot(100, self._fetch_holidays)
        self._render()

    def _fetch_notes(self):
        """Ambil catatan untuk tahun ini + tahun lalu + tahun depan (3 tahun)."""
        all_notes = {}
        for y in [self.current_year - 1, self.current_year, self.current_year + 1]:
            notes = db.get_calendar_notes(self.user_id, year=y)
            all_notes.update(notes)
        self.notes = all_notes

    def _fetch_holidays(self):
        holidays = {}
        for year in [self.current_year - 1, self.current_year, self.current_year + 1]:
            year_data = get_holidays_for_year(year)
            holidays.update(year_data)
        self.holidays = holidays
        self._holidays_fetched = True
        self._loading_holidays = False
        print(f"[Calendar] Loaded {len(holidays)} holidays for {self.current_year-1}-{self.current_year+1}")
        QTimer.singleShot(0, self._render)

    def _render(self):
        # Kosongkan grid
        while self.months_grid.count():
            item = self.months_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Render 12 bulan
        for month in range(1, 13):
            month_widget = self._make_month(month)
            row = (month - 1) // 3
            col = (month - 1) % 3
            self.months_grid.addWidget(month_widget, row, col)

        self.year_label.setText(str(self.current_year))

    def _make_month(self, month):
        widget = QWidget()
        widget.setObjectName("card")
        widget.setMinimumHeight(420)   # cukup untuk 6 baris + header
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)   # margin minimal
        layout.setSpacing(6)

        # Nama bulan
        month_name = tr(f"month_{month:02d}")
        lbl_month = QLabel(month_name)
        lbl_month.setStyleSheet(f"font-size:16px; font-weight:bold; color:{_T('light')}; padding-bottom:4px;")
        lbl_month.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_month)

        # Grid hari
        grid = QGridLayout()
        grid.setHorizontalSpacing(4)    # jarak horizontal (kiri-kanan) tetap rapat
        grid.setVerticalSpacing(10)     # jarak vertikal (atas-bawah) lebih longgar
        grid.setContentsMargins(0, 0, 0, 0)

        # Header hari (Senin–Minggu)
        days_abbr = [tr(f"day_{i}") for i in range(7)]
        for col, d in enumerate(days_abbr):
            lbl = QLabel(d)
            lbl.setStyleSheet(f"font-size:11px; color:{_T('muted')}; font-weight:bold;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, col)

        # Isi tanggal
        first_day, num_days = calmod.monthrange(self.current_year, month)
        row = 1
        col = first_day
        for day in range(1, num_days + 1):
            date_str = f"{self.current_year:04d}-{month:02d}-{day:02d}"
            is_today = (date_str == datetime.now().strftime("%Y-%m-%d"))
            is_holiday = date_str in self.holidays
            has_note = date_str in self.notes and self.notes[date_str].strip() != ""

            btn = QPushButton(str(day))
            btn.setMinimumSize(40, 44)          # ukuran lebih proporsional
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {_T('bg')};
                    border: 1px solid {_T('border')};
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {_T('primary')};
                    color: #fff;
                }}
            """)
            if is_today:
                btn.setStyleSheet(btn.styleSheet() + f"""
                    QPushButton {{
                        background: {_T('primary')};
                        color: #fff;
                        border: 2px solid {_T('accent')};
                    }}
                """)
            if is_holiday:
                holiday_name = get_holiday_name(date_str, AppState.get_language())
                btn.setToolTip(f"🏷️ {holiday_name}" if holiday_name else "Libur")
                btn.setStyleSheet(btn.styleSheet() + """
                    QPushButton {
                        background: #3a1a1a;
                        color: #ff6b6b;
                        border-color: #e05050;
                    }
                """)
            if has_note:
                btn.setText(f"{day}\n📝")
                btn.setStyleSheet(btn.styleSheet() + f"""
                    QPushButton {{
                        border-color: {_T('accent')};
                    }}
                """)

            btn.clicked.connect(lambda checked, d=date_str, n=has_note: self._open_note_dialog(d, n))
            grid.addWidget(btn, row, col)
            col += 1
            if col >= 7:
                col = 0
                row += 1

        # ⭐ Kunci: Beri bobot peregangan pada setiap baris agar tinggi terdistribusi rata
        for r in range(1, row):   # row terakhir adalah jumlah baris + 1
            grid.setRowStretch(r, 1)

        layout.addLayout(grid)
        return widget

    def _open_note_dialog(self, date_str, has_existing):
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("calendar_note_title", date=date_str))
        dlg.setMinimumSize(400, 300)
        dlg.setStyleSheet(build_ss())

        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tampilkan hari libur jika ada
        holiday_name = get_holiday_name(date_str, AppState.get_language())
        if holiday_name:
            info = QLabel(tr("calendar_holiday_info", name=holiday_name))
            info.setStyleSheet(f"color:{_T('accent')}; font-weight:bold;")
            layout.addWidget(info)

        layout.addWidget(QLabel(tr("calendar_note_label")))

        note_edit = QTextEdit()
        note_edit.setPlaceholderText(tr("calendar_note_placeholder"))
        if has_existing:
            note_edit.setText(self.notes.get(date_str, ""))
        layout.addWidget(note_edit)

        # Tombol
        button_box = QDialogButtonBox()
        save_btn = button_box.addButton(tr("dialog_save"), QDialogButtonBox.ButtonRole.AcceptRole)
        delete_btn = button_box.addButton(tr("calendar_delete"), QDialogButtonBox.ButtonRole.DestructiveRole)
        cancel_btn = button_box.addButton(tr("btn_cancel"), QDialogButtonBox.ButtonRole.RejectRole)

        save_btn.clicked.connect(lambda: self._save_note(date_str, note_edit.toPlainText(), dlg))
        delete_btn.clicked.connect(lambda: self._delete_note(date_str, dlg))
        cancel_btn.clicked.connect(dlg.reject)

        layout.addWidget(button_box)
        dlg.exec()

    def _save_note(self, date_str, note, dialog):
        if note.strip():
            db.save_calendar_note(self.user_id, date_str, note.strip())
            SND.complete()
        else:
            db.delete_calendar_note(self.user_id, date_str)
            SND.click()
        dialog.accept()
        QTimer.singleShot(0, self.load)

    def _delete_note(self, date_str, dialog):
        db.delete_calendar_note(self.user_id, date_str)
        SND.click()
        dialog.accept()
        QTimer.singleShot(0, self.load)

    def _prev_year(self):
        self.current_year -= 1
        self._fetch_holidays()
        QTimer.singleShot(0, self.load)

    def _next_year(self):
        self.current_year += 1
        self._fetch_holidays()
        QTimer.singleShot(0, self.load)

    def _goto_today(self):
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self._fetch_holidays()
        QTimer.singleShot(0, self.load)

    def closeEvent(self, e):
        AppState.unregister(self.load)
        AppState.unregister_lang_cb(self.load)
        super().closeEvent(e)

# ══════════════════════════════════════════════════════════════════════════════
#  Notes Page
# ══════════════════════════════════════════════════════════════════════════════
class NotesPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.current_folder_id = None
        self.current_note_id = None
        self.show_archived = False
        self.search_text = ""
        self._is_dirty = False
        # ── Simpan setting font per note ──
        self._note_font_settings = {}  # {note_id: (size, color)}
        # ── Default fallback ──
        self._default_font_size = 12
        self._default_color = QColor("#e8e8e8")
        self._current_bold = False
        self._current_italic = False
        self._current_underline = False
        # ── ──
        self._build()
        AppState.register(self.load)
        AppState.register_lang_cb(self.load)

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("notes_title"), "section", 14, True))
        hdr.addStretch()
        self.archive_btn = _btn(tr("notes_archive"), h=34)
        self.archive_btn.clicked.connect(self._toggle_archive)
        hdr.addWidget(self.archive_btn)
        self.archive_toggle_btn = _btn(tr("notes_show_archived"), h=34)
        self.archive_toggle_btn.clicked.connect(self._toggle_show_archived)
        hdr.addWidget(self.archive_toggle_btn)
        main_layout.addLayout(hdr)
        main_layout.addWidget(_sep())

        # ── Search bar ──
        search_widget = QWidget()
        search_layout = QHBoxLayout(search_widget)
        search_layout.setContentsMargins(0, 0, 0, 0)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(tr("notes_search_placeholder"))
        self.search_input.textChanged.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        main_layout.addWidget(search_widget)

        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        add_folder_btn = _btn(tr("notes_add_folder"), h=34)
        add_folder_btn.clicked.connect(self._add_folder)
        add_note_btn = _btn(tr("notes_add_note"), "solid", h=34)
        add_note_btn.clicked.connect(self._add_note)
        delete_btn = _btn(tr("notes_delete"), "danger", h=34)
        delete_btn.clicked.connect(self._delete_selected)
        toolbar.addWidget(add_folder_btn)
        toolbar.addWidget(add_note_btn)
        toolbar.addWidget(delete_btn)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Splitter: left = folders + notes list, right = editor
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        # Folder Tree (hirarki)
        folder_row = QHBoxLayout()
        folder_row.addWidget(_lbl(tr("notes_folder_label"), size=12))
        folder_row.addStretch()

        # Tombol collapse/expand semua
        self.expand_btn = _btn(tr("expand_all"), h=28)
        self.expand_btn.clicked.connect(lambda: self.folder_tree.expandAll())
        self.collapse_btn = _btn(tr("collapse_all"), h=28)
        self.collapse_btn.clicked.connect(lambda: self.folder_tree.collapseAll())
        folder_row.addWidget(self.expand_btn)
        folder_row.addWidget(self.collapse_btn)


        self.folder_tree = QTreeWidget()
        self.folder_tree.setHeaderHidden(True)
        self.folder_tree.setMinimumHeight(200)
        self.folder_tree.setIndentation(20)   # indentasi untuk subfolder
        self.folder_tree.itemClicked.connect(self._on_folder_selected)
        self.folder_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.folder_tree.customContextMenuRequested.connect(self._show_folder_context_menu)

        left_layout.addLayout(folder_row)
        left_layout.addWidget(self.folder_tree)

        # Notes list
        left_layout.addWidget(_lbl(tr("notes_list_label"), size=12))
        self.notes_list = QListWidget()
        self.notes_list.setMinimumHeight(200)
        self.notes_list.itemClicked.connect(self._on_note_selected)
        left_layout.addWidget(self.notes_list)

        # Note count
        self.note_count_label = _lbl("", "sub", 11)
        left_layout.addWidget(self.note_count_label)

        splitter.addWidget(left_widget)

        # Right panel - editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(6)

        right_layout.addWidget(_lbl(tr("notes_title_label"), size=12))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(tr("notes_note_title_ph"))
        self.title_edit.setMinimumHeight(34)
        self.title_edit.textChanged.connect(self._mark_dirty)
        right_layout.addWidget(self.title_edit)

        # ── Toolbar Matematika ──
        math_scroll = QScrollArea()
        math_scroll.setWidgetResizable(True)
        math_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        math_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        math_scroll.setFixedHeight(80)  # Tinggi cukup untuk tombol 40px + padding
        math_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: {_T('bg')};
                height: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal {{
                background: {_T('border')};
                border-radius: 5px;
                min-width: 30px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {_T('primary')};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """)

        math_container = QWidget()
        math_container.setStyleSheet(f"background: transparent; padding: 8px 0px;")
        math_layout = QHBoxLayout(math_container)
        math_layout.setContentsMargins(4, 4, 4, 4)
        math_layout.setSpacing(6)

        # Simbol matematika
        symbols = [
            ("²", "²"), ("³", "³"), ("√", "√"), ("π", "π"),
            ("×", "×"), ("÷", "÷"), ("±", "±"), ("∑", "∑"),
            ("∫", "∫"), ("∞", "∞"), ("α", "α"), ("β", "β"),
            ("γ", "γ"), ("θ", "θ"), ("λ", "λ"), ("μ", "μ"),
            ("σ", "σ"), ("τ", "τ"), ("φ", "φ"), ("ω", "ω"),
            ("∂", "∂"), ("∇", "∇"), ("∆", "∆"), ("ℵ", "ℵ"),
            ("ℜ", "ℜ"), ("ℑ", "ℑ"), ("℘", "℘"),
        ]

        # Tombol simbol
        for label, sym in symbols:
            btn = QPushButton(label)
            btn.setFixedSize(40, 40)
            btn.setStyleSheet(f"""
                font-size: 18px;
                font-weight: bold;
                background: {_T('panel')};
                border: 1px solid {_T('border')};
                border-radius: 6px;
            """)
            btn.clicked.connect(lambda checked, s=sym: self._insert_symbol(s))
            math_layout.addWidget(btn)

        # Tombol Superscript
        sup_btn = QPushButton("x²")
        sup_btn.setFixedSize(40, 40)
        sup_btn.setStyleSheet(f"""
            font-size: 15px;
            background: {_T('panel')};
            border: 1px solid {_T('border')};
            border-radius: 6px;
        """)
        sup_btn.clicked.connect(self._insert_superscript)
        math_layout.addWidget(sup_btn)

        # Tombol Subscript
        sub_btn = QPushButton("x₂")
        sub_btn.setFixedSize(40, 40)
        sub_btn.setStyleSheet(f"""
            font-size: 15px;
            background: {_T('panel')};
            border: 1px solid {_T('border')};
            border-radius: 6px;
        """)
        sub_btn.clicked.connect(self._insert_subscript)
        math_layout.addWidget(sub_btn)

        # Tombol Pecahan
        frac_btn = QPushButton("a/b")
        frac_btn.setFixedSize(40, 40)
        frac_btn.setStyleSheet(f"""
            font-size: 15px;
            background: {_T('panel')};
            border: 1px solid {_T('border')};
            border-radius: 6px;
        """)
        frac_btn.clicked.connect(self._insert_fraction)
        math_layout.addWidget(frac_btn)

        math_layout.addStretch()

        math_scroll.setWidget(math_container)
        right_layout.addWidget(math_scroll)

        # ── Toolbar Font (Ukuran, Warna, Bold, Italic, Underline) ──
        font_toolbar = QWidget()
        font_toolbar.setStyleSheet(f"background: transparent; border: none; padding: 4px 0px;")
        font_layout = QHBoxLayout(font_toolbar)
        font_layout.setContentsMargins(8, 4, 8, 4)
        font_layout.setSpacing(6)

        # Label "Font:"
        font_label = QLabel("Font:")
        font_label.setStyleSheet(f"color: {_T('muted')}; font-size: 12px;")
        font_layout.addWidget(font_label)

        # ── ComboBox Ukuran ──
        self.font_size_combo = QComboBox()
        self.font_size_combo.setMinimumHeight(32)
        self.font_size_combo.setFixedWidth(70)
        self.font_size_combo.setStyleSheet(f"""
            QComboBox {{
                background: {_T('panel')};
                color: {_T('text')};
                border: 1px solid {_T('border')};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {_T('panel')};
                color: {_T('text')};
                selection-background-color: {_T('primary')};
            }}
        """)
        font_sizes = [8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 32, 36, 48, 72]
        for s in font_sizes:
            self.font_size_combo.addItem(f"{s}px", s)
        self.font_size_combo.setCurrentIndex(4)  # default 12px
        self.font_size_combo.currentIndexChanged.connect(self._change_font_size)
        font_layout.addWidget(self.font_size_combo)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.VLine)
        sep1.setStyleSheet(f"color: {_T('border')};")
        sep1.setFixedHeight(28)
        font_layout.addWidget(sep1)

        # ── Tombol Warna ──
        self.color_btn = QPushButton("🎨")
        self.color_btn.setFixedSize(36, 32)
        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 16px;
                background: {_T('panel')};
                border: 1px solid {_T('border')};
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background: {_T('border')};
            }}
        """)
        self.color_btn.clicked.connect(self._choose_font_color)
        font_layout.addWidget(self.color_btn)

        # Indikator warna
        self.color_indicator = QLabel()
        self.color_indicator.setFixedSize(28, 28)
        self.color_indicator.setStyleSheet(f"""
            background: {_T('text')};
            border: 1px solid {_T('border')};
            border-radius: 4px;
        """)
        font_layout.addWidget(self.color_indicator)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet(f"color: {_T('border')};")
        sep2.setFixedHeight(28)
        font_layout.addWidget(sep2)

        # ── Tombol Bold, Italic, Underline ──
        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedSize(36, 32)
        self.bold_btn.setCheckable(True)
        self.bold_btn.setStyleSheet(f"""
            QPushButton {{
                font-weight: bold;
                font-size: 14px;
                background: {_T('panel')};
                border: 1px solid {_T('border')};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background: {_T('primary')};
                color: #fff;
                border-color: {_T('light')};
            }}
            QPushButton:hover {{
                background: {_T('border')};
            }}
        """)
        self.bold_btn.clicked.connect(lambda: self._toggle_format('bold'))
        font_layout.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setFixedSize(36, 32)
        self.italic_btn.setCheckable(True)
        self.italic_btn.setStyleSheet(f"""
            QPushButton {{
                font-style: italic;
                font-size: 14px;
                background: {_T('panel')};
                border: 1px solid {_T('border')};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background: {_T('primary')};
                color: #fff;
                border-color: {_T('light')};
            }}
            QPushButton:hover {{
                background: {_T('border')};
            }}
        """)
        self.italic_btn.clicked.connect(lambda: self._toggle_format('italic'))
        font_layout.addWidget(self.italic_btn)

        self.underline_btn = QPushButton("U")
        self.underline_btn.setFixedSize(36, 32)
        self.underline_btn.setCheckable(True)
        self.underline_btn.setStyleSheet(f"""
            QPushButton {{
                text-decoration: underline;
                font-size: 14px;
                background: {_T('panel')};
                border: 1px solid {_T('border')};
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background: {_T('primary')};
                color: #fff;
                border-color: {_T('light')};
            }}
            QPushButton:hover {{
                background: {_T('border')};
            }}
        """)
        self.underline_btn.clicked.connect(lambda: self._toggle_format('underline'))
        font_layout.addWidget(self.underline_btn)

        # Spacer di ujung
        font_layout.addStretch()

        # ── Tambahkan ke layout utama ──
        right_layout.addWidget(font_toolbar)

        right_layout.addWidget(_lbl(tr("notes_content_label"), size=12))
        self.content_edit = NotesTextEdit(self)
        self.content_edit.setAcceptRichText(True)
        self.content_edit.setPlaceholderText(tr("notes_note_content_ph"))
        self.content_edit.cursorPositionChanged.connect(self._apply_default_format)
        self.content_edit.textChanged.connect(self._mark_dirty)
        right_layout.addWidget(self.content_edit)

        # Save button
        save_btn = _btn(tr("notes_save"), "solid", self._save_note, 40)
        right_layout.addWidget(save_btn)

        splitter.addWidget(right_widget)
        splitter.setSizes([350, 700])

        main_layout.addWidget(splitter, 1)

        self._is_dirty = False
        self.load()

    def load(self):
        if not AppState.user_id:
            return
        self._load_folder_tree()
        self._load_notes()

    def _load_folder_tree(self):
        self.folder_tree.clear()
        
        # Root "Semua Catatan"
        root_item = QTreeWidgetItem(self.folder_tree)
        root_item.setText(0, "📂 " + tr("notes_all"))
        root_item.setData(0, Qt.ItemDataRole.UserRole, -1)   # -1 = semua
        root_item.setExpanded(True)
        
        # "Tanpa Folder"
        no_folder_item = QTreeWidgetItem(root_item)
        no_folder_item.setText(0, "📭 " + tr("notes_no_folder"))
        no_folder_item.setData(0, Qt.ItemDataRole.UserRole, 0)   # 0 = tanpa folder
        no_folder_item.setExpanded(True)
        
        # Tree dari database
        tree_data = db.get_note_folders_tree(self.user_id)
        self._populate_tree_items(root_item, tree_data)
        
        self.folder_tree.expandAll()
        
        # Pilih item yang sesuai dengan current_folder_id
        self._select_tree_item_by_id(self.current_folder_id)

    def _populate_tree_items(self, parent_item, folders):
        """Rekursif untuk mengisi tree widget dari data folder."""
        for folder in folders:
            item = QTreeWidgetItem(parent_item)
            item.setText(0, f"{folder['icon']} {folder['name']}")
            item.setData(0, Qt.ItemDataRole.UserRole, folder["id"])
            item.setExpanded(True)
            
            if folder.get("children"):
                self._populate_tree_items(item, folder["children"])

    def _select_tree_item_by_id(self, folder_id):
        """Pilih item di tree berdasarkan folder_id."""
        if folder_id is None:
            folder_id = -1  # semua
        iterator = QTreeWidgetItemIterator(self.folder_tree)
        while iterator.value():
            item = iterator.value()
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data == folder_id:
                self.folder_tree.setCurrentItem(item)
                # Panggil _on_folder_selected hanya jika berbeda
                if self.current_folder_id != folder_id:
                    self._on_folder_selected(item, 0)
                return
            iterator += 1
        # fallback: pilih root (semua)
        if self.folder_tree.topLevelItemCount() > 0:
            root = self.folder_tree.topLevelItem(0)
            self.folder_tree.setCurrentItem(root)
            if self.current_folder_id != -1:
                self._on_folder_selected(root, 0)

    def _load_notes(self):
        self.notes_list.clear()
        
        folder_id = self.current_folder_id
        
        if folder_id is None:
            # Semua catatan (termasuk yang di folder dan subfolder)
            all_notes = db.get_notes(self.user_id, None, include_archived=self.show_archived)
        elif folder_id == 0:
            # Catatan tanpa folder (folder_id IS NULL)
            all_notes = db.get_notes(self.user_id, -1, include_archived=self.show_archived)
        else:
            # Catatan hanya di folder ini (tidak termasuk subfolder)
            all_notes = db.get_notes(self.user_id, folder_id, include_archived=self.show_archived)
        
        # Filter berdasarkan search text
        if self.search_text:
            all_notes = [n for n in all_notes if self.search_text in n["title"].lower() or self.search_text in n["content"].lower()]

        if not all_notes:
            self.note_count_label.setText(tr("notes_archive_empty") if self.show_archived else tr("notes_count_format", count=0))
            self._clear_editor()
            return
        
        self.note_count_label.setText(tr("notes_count_format", count=len(all_notes)))
        for n in all_notes:
            item = QListWidgetItem(f"{'📦 ' if n['is_archived'] else ''}{n['title']}")
            item.setData(Qt.ItemDataRole.UserRole, n["id"])
            self.notes_list.addItem(item)
        
        if self.search_text:
            self.note_count_label.setText(tr("notes_search_result", count=len(all_notes)))
        else:
            self.note_count_label.setText(tr("notes_count_format", count=len(all_notes)))

        if all_notes:
            self.notes_list.setCurrentRow(0)
            self._load_note(all_notes[0]["id"])
        else:
            self._clear_editor()
            self.current_note_id = None

    def _show_folder_context_menu(self, position):
        item = self.folder_tree.itemAt(position)
        if not item:
            return

        menu = QMenu(self)
        folder_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Jika item adalah folder (bukan root/no folder)
        if folder_id is not None and folder_id > 0:
            # Menu untuk folder biasa
            add_sub_act = menu.addAction(tr("notes_add_subfolder"))
            edit_name_act = menu.addAction(tr("notes_edit_folder"))
            edit_icon_act = menu.addAction(tr("notes_edit_icon"))
            duplicate_act = menu.addAction(tr("notes_duplicate_folder"))
            menu.addSeparator()
            delete_act = menu.addAction(tr("notes_delete"))
            menu.addSeparator()
            # Tambahkan indikator child count
            child_count = self._count_children(folder_id)
            info_act = menu.addAction(tr("notes_folder_info", count=child_count))
            info_act.setEnabled(False)

            action = menu.exec(self.folder_tree.viewport().mapToGlobal(position))

            if action == add_sub_act:
                self._add_subfolder(folder_id)
            elif action == edit_name_act:
                self._edit_folder_name(folder_id)
            elif action == edit_icon_act:
                self._edit_folder_icon(folder_id)
            elif action == duplicate_act:
                self._duplicate_folder(folder_id)
            elif action == delete_act:
                self._delete_folder_item(folder_id)

        elif folder_id == 0 or folder_id == -1:
            # Root atau "Tanpa Folder" – hanya tambah folder
            add_act = menu.addAction(tr("notes_add_folder"))
            action = menu.exec(self.folder_tree.viewport().mapToGlobal(position))
            if action == add_act:
                self._add_folder()

    def _on_search(self, text):
        self.search_text = text.strip().lower()
        self.load()

    def _add_subfolder(self, parent_id):
        name, ok = QInputDialog.getText(self, tr("notes_subfolder_title"), tr("notes_subfolder_name"))
        if ok and name.strip():
            r = db.add_note_folder(self.user_id, name.strip(), parent_id=parent_id)
            if r["ok"]:
                SND.notify()
                self._load_folder_tree()
                self._select_tree_item_by_id(r["folder_id"])
                _show(self, tr("berhasil_title"), tr("notes_subfolder_added", name=name.strip()), "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r.get("msg", "Gagal menambah subfolder"), "error")

    def _edit_folder_item(self, folder_id):
        name, ok = QInputDialog.getText(self, tr("notes_edit_folder_title"), tr("notes_folder_name_ph"))
        if ok and name.strip():
            conn = db.get_conn()
            conn.execute("UPDATE note_folders SET name=? WHERE id=? AND user_id=?", (name.strip(), folder_id, self.user_id))
            conn.commit()
            conn.close()
            SND.notify()
            self._load_folder_tree()

    def _delete_folder_item(self, folder_id):
        reply = QMessageBox.question(self, tr("confirm_title"), tr("notes_folder_delete_confirm"),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            conn = db.get_conn()
            # Hapus semua subfolder secara rekursif (pakai ON DELETE CASCADE jika sudah diatur)
            conn.execute("DELETE FROM note_folders WHERE id=? AND user_id=?", (folder_id, self.user_id))
            conn.commit()
            conn.close()
            SND.click()
            self._load_folder_tree()

    def _load_note(self, note_id):
        """Muat note ke editor, terapkan format default, update toolbar."""
        note = db.get_note(note_id, self.user_id)
        if not note:
            return
        
        # Isi judul dan konten
        self.title_edit.setText(note["title"])
        self.content_edit.setHtml(note["content"])
        self.current_note_id = note_id
        self._is_dirty = False
        
        # Ambil format dari karakter pertama
        cursor = self.content_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        fmt = cursor.charFormat()
        
        # Tentukan ukuran dan warna default
        if note_id in self._note_font_settings:
            # Gunakan setting tersimpan
            size, color = self._note_font_settings[note_id]
            self._current_font_size = size
            self._current_color = color
        else:
            # Ambil dari teks atau gunakan default
            if fmt.fontPointSize() > 0:
                size = fmt.fontPointSize()
            else:
                size = self._default_font_size
            if fmt.foreground().color().isValid():
                color = fmt.foreground().color()
            else:
                color = self._default_color
            
            # Simpan ke dictionary agar lain kali langsung pakai
            self._note_font_settings[note_id] = (size, color)
            self._current_font_size = size
            self._current_color = color
        
        # Baca status bold/italic/underline dari format karakter pertama
        self._current_bold = (fmt.fontWeight() == QFont.Weight.Bold)
        self._current_italic = fmt.fontItalic()
        self._current_underline = fmt.fontUnderline()
        
        # Update toolbar UI
        # Ukuran
        index = self.font_size_combo.findData(self._current_font_size)
        if index >= 0:
            self.font_size_combo.setCurrentIndex(index)
        # Warna
        self.color_indicator.setStyleSheet(f"""
            background: {self._current_color.name()};
            border: 1px solid {_T('border')};
            border-radius: 4px;
        """)
        # Bold/Italic/Underline buttons
        self.bold_btn.setChecked(self._current_bold)
        self.italic_btn.setChecked(self._current_italic)
        self.underline_btn.setChecked(self._current_underline)
        
        # Terapkan format default untuk pengetikan selanjutnya
        default_fmt = QTextCharFormat()
        default_fmt.setFontPointSize(self._current_font_size)
        default_fmt.setForeground(self._current_color)
        default_fmt.setFontWeight(QFont.Weight.Bold if self._current_bold else QFont.Weight.Normal)
        default_fmt.setFontItalic(self._current_italic)
        default_fmt.setFontUnderline(self._current_underline)
        self.content_edit.setCurrentCharFormat(default_fmt)
        
        # Pastikan kursor di awal
        cursor = self.content_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.content_edit.setTextCursor(cursor)

    def _clear_editor(self):
        self.title_edit.clear()
        self.content_edit.clear()
        self.current_note_id = None
        self._is_dirty = False

    def _on_folder_selected(self, item, column):
        folder_id = item.data(0, Qt.ItemDataRole.UserRole)
        if folder_id == -1:
            self.current_folder_id = None   # semua catatan
        elif folder_id == 0:
            self.current_folder_id = 0      # tanpa folder
        else:
            self.current_folder_id = folder_id
        self._load_notes()

    def _on_note_selected(self, item):
        note_id = item.data(Qt.ItemDataRole.UserRole)
        self._load_note(note_id)

    def _add_folder(self, parent_id=None):
        name, ok = QInputDialog.getText(self, tr("notes_folder_name"), tr("notes_folder_name_ph"))
        if ok and name.strip():
            r = db.add_note_folder(self.user_id, name.strip(), parent_id=parent_id)
            if r["ok"]:
                SND.notify()
                self._load_folder_tree()

    def _add_note(self):
        # Ambil folder yang dipilih dari tree
        current_item = self.folder_tree.currentItem()
        if current_item:
            folder_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            # folder_id = -1 berarti "Semua Catatan" -> tidak ada folder
            # folder_id = 0 berarti "Tanpa Folder" -> folder_id = None di DB
            if folder_id == -1:
                folder_id = None
            elif folder_id == 0:
                folder_id = None
        else:
            folder_id = None

        title = "Untitled"
        r = db.add_note(self.user_id, folder_id, title)
        if r["ok"]:
            SND.complete()
            self._load_notes()
            # Pilih note yang baru dibuat
            notes = db.get_notes(self.user_id, folder_id, include_archived=False)
            for n in notes:
                if n["id"] == r["note_id"]:
                    self._load_note(n["id"])
                    break
            # Refresh folder tree (untuk update count jika perlu)
            self._load_folder_tree()

    def _save_note(self):
        if self.current_note_id is None:
            return
        title = self.title_edit.text().strip()
        if not title:
            title = "Untitled"
        content = self.content_edit.toHtml()
        db.update_note(self.current_note_id, self.user_id, title=title, content=content)
        self._is_dirty = False
        SND.complete()
        _show(self, tr("berhasil_title"), tr("notes_saved"), "success")
        self._load_notes()  # refresh list

    def _delete_selected(self):
        if self.current_note_id is None:
            return
        reply = QMessageBox.question(self, tr("confirm_title"), tr("notes_delete_confirm"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_note(self.current_note_id, self.user_id)
            SND.click()
            _show(self, tr("berhasil_title"), tr("notes_deleted"), "success")
            self._clear_editor()
            self._load_notes()

    def _toggle_archive(self):
        if self.current_note_id is None:
            return
        note = db.get_note(self.current_note_id, self.user_id)
        if not note:
            return
        new_state = 0 if note["is_archived"] else 1
        db.archive_note(self.current_note_id, self.user_id, new_state)
        SND.notify()
        if new_state:
            _show(self, tr("info_title"), tr("notes_archived"), "info")
        else:
            _show(self, tr("info_title"), tr("notes_unarchived"), "info")
        self._clear_editor()
        self._load_notes()

    def _toggle_show_archived(self):
        self.show_archived = not self.show_archived
        if self.show_archived:
            self.archive_toggle_btn.setText(tr("notes_hide_archived"))
        else:
            self.archive_toggle_btn.setText(tr("notes_show_archived"))
        self._load_notes()

    def _mark_dirty(self):
        self._is_dirty = True

    def _count_children(self, folder_id):
        """Hitung jumlah total note di folder ini dan subfolder."""
        conn = db.get_conn()
        # Hitung note langsung di folder ini
        count = conn.execute(
            "SELECT COUNT(*) FROM notes WHERE user_id=? AND folder_id=?",
            (self.user_id, folder_id)
        ).fetchone()[0]
        # Hitung note di subfolder
        subfolders = conn.execute(
            "SELECT id FROM note_folders WHERE user_id=? AND parent_id=?",
            (self.user_id, folder_id)
        ).fetchall()
        conn.close()
        for sub in subfolders:
            count += self._count_children(sub["id"])
        return count

    def _edit_folder_icon(self, folder_id):
        """Dialog untuk memilih icon baru untuk folder."""
        # Daftar icon populer
        icons = ["📁", "📂", "⭐", "❤️", "🔥", "💼", "🏠", "🎯", "📖", "🎮", "💡", "🌿", "📚", "🏷️", "📎", "📌"]
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("notes_edit_icon_title"))
        dlg.setMinimumWidth(400)
        dlg.setStyleSheet(build_ss())
        layout = QVBoxLayout(dlg)
        layout.addWidget(_lbl(tr("notes_select_icon"), size=12))

        grid = QGridLayout()
        row, col = 0, 0
        for icon in icons:
            btn = QPushButton(icon)
            btn.setFixedSize(50, 50)
            btn.setStyleSheet("font-size: 24px;")
            btn.clicked.connect(lambda checked, i=icon: self._save_folder_icon(folder_id, i, dlg))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 5:
                col = 0
                row += 1

        layout.addLayout(grid)
        cancel_btn = _btn(tr("btn_cancel"), "flat", dlg.reject)
        layout.addWidget(cancel_btn)
        dlg.exec()

    def _save_folder_icon(self, folder_id, new_icon, dialog):
        db.update_note_folder_icon(folder_id, self.user_id, new_icon)
        SND.notify()
        dialog.accept()
        self._load_folder_tree()
        _show(self, tr("berhasil_title"), tr("notes_icon_updated"), "success")

    def _duplicate_folder(self, folder_id):
        r = db.duplicate_note_folder(self.user_id, folder_id)
        if r["ok"]:
            SND.complete()
            _show(self, tr("berhasil_title"), r["msg"], "success")
            self._load_folder_tree()
            # Pilih folder baru yang diduplikasi
            if "new_folder_id" in r:
                self._select_tree_item_by_id(r["new_folder_id"])
        else:
            SND.error()
            _show(self, tr("gagal_title"), r["msg"], "error")

    def _edit_folder_name(self, folder_id):
        """Edit nama folder (tanpa mengubah icon)."""
        current = db.get_conn().execute(
            "SELECT name FROM note_folders WHERE id=? AND user_id=?",
            (folder_id, self.user_id)
        ).fetchone()
        if not current:
            return
        old_name = current["name"]
        new_name, ok = QInputDialog.getText(self, tr("notes_edit_folder_title"), tr("notes_folder_name_ph"), text=old_name)
        if ok and new_name.strip():
            conn = db.get_conn()
            conn.execute(
                "UPDATE note_folders SET name=? WHERE id=? AND user_id=?",
                (new_name.strip(), folder_id, self.user_id)
            )
            conn.commit()
            conn.close()
            SND.notify()
            self._load_folder_tree()
            _show(self, tr("berhasil_title"), tr("notes_folder_renamed"), "success")

    def _insert_symbol(self, symbol):
        """Sisipkan simbol matematika di posisi kursor."""
        self.content_edit.insertPlainText(symbol)
        self.content_edit.setFocus()

    def _insert_superscript(self):
        """Sisipkan teks superscript (x²) di posisi kursor."""
        cursor = self.content_edit.textCursor()
        # Jika ada teks yang dipilih, bungkus dengan tag sup
        if cursor.hasSelection():
            selected = cursor.selectedText()
            html = f"<sup>{selected}</sup>"
            cursor.removeSelectedText()
            cursor.insertHtml(html)
        else:
            # Sisipkan placeholder
            cursor.insertText("x²")
        self.content_edit.setFocus()

    def _insert_subscript(self):
        """Sisipkan teks subscript (x₂) di posisi kursor."""
        cursor = self.content_edit.textCursor()
        if cursor.hasSelection():
            selected = cursor.selectedText()
            html = f"<sub>{selected}</sub>"
            cursor.removeSelectedText()
            cursor.insertHtml(html)
        else:
            cursor.insertText("x₂")
        self.content_edit.setFocus()

    def _insert_fraction(self):
        """Sisipkan pecahan: jika ada seleksi, konversi; jika ada pola angka/angka di sekitar kursor, konversi; 
        jika tidak, sisipkan template a/b."""
        cursor = self.content_edit.textCursor()
        
        # Ambil ukuran dan warna dari variabel instance
        size = self._current_font_size
        color = self._current_color.name()
        
        # Jika ada seleksi, gunakan sebagai pembilang
        if cursor.hasSelection():
            numerator = cursor.selectedText()
            cursor.removeSelectedText()
            denominator = "b"  # default
            self._insert_fraction_html(numerator, denominator, size, color, cursor)
            return
        
        # Tidak ada seleksi: cek apakah ada pola "angka/angka" di sekitar kursor
        # Ambil teks di sekitar kursor (maksimal 20 karakter ke kiri)
        cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, 20)
        text_left = cursor.selectedText()
        cursor.clearSelection()
        cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.MoveAnchor, 20)  # kembali ke posisi semula
        
        # Cari pola "angka/angka" di akhir teks kiri (paling dekat dengan kursor)
        import re
        match = re.search(r'(\d+)\s*/\s*(\d+)$', text_left)
        if match:
            # Ada pola, ambil angka-angkanya
            numerator = match.group(1)
            denominator = match.group(2)
            # Hapus pola dari teks (mulai dari posisi match)
            start_pos = len(text_left) - len(match.group(0))
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(match.group(0)))
            cursor.removeSelectedText()
            # Sisipkan pecahan
            self._insert_fraction_html(numerator, denominator, size, color, cursor)
            return
        
        # Tidak ada pola, sisipkan template a/b
        self._insert_fraction_html("a", "b", size, color, cursor)
    
    def _insert_fraction_html(self, numerator, denominator, size, color, cursor):
        """Sisipkan HTML pecahan di posisi kursor."""
        html = (
            '<span style="font-size:{}px;color:{};">'
            '<sup>{}</sup>/<sub>{}</sub>'
            '</span>'
        ).format(size, color, numerator, denominator)
        cursor.insertHtml(html)
        cursor.insertText(" ")
        
        # Kembalikan format default
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        fmt.setForeground(QColor(color))
        self.content_edit.setCurrentCharFormat(fmt)
        self.content_edit.setFocus()

    def _change_font_size(self, index):
        size = self.font_size_combo.currentData()
        if not size:
            return

        cursor = self.content_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setFontPointSize(size)
        fmt.setForeground(self._current_color)
        
        # Terapkan ke seleksi jika ada
        if cursor.hasSelection():
            cursor.mergeCharFormat(fmt)
        else:
            self.content_edit.setCurrentCharFormat(fmt)
        
        # ── SELALU simpan setting untuk note ini ──
        if self.current_note_id:
            self._note_font_settings[self.current_note_id] = (size, self._current_color)
        self._current_font_size = size
        
        self.content_edit.setFocus()

    def _choose_font_color(self):
        current_color = self.color_indicator.palette().window().color()
        
        color = QColorDialog.getColor(current_color, self, "Pilih Warna Teks")
        if color.isValid():
            self.color_indicator.setStyleSheet(f"""
                background: {color.name()};
                border: 1px solid {_T('border')};
                border-radius: 4px;
            """)
            
            cursor = self.content_edit.textCursor()
            fmt = QTextCharFormat()
            fmt.setFontPointSize(self._current_font_size)
            fmt.setForeground(color)
            
            if cursor.hasSelection():
                cursor.mergeCharFormat(fmt)
            else:
                self.content_edit.setCurrentCharFormat(fmt)
            
            # ── SELALU simpan setting untuk note ini ──
            if self.current_note_id:
                self._note_font_settings[self.current_note_id] = (self._current_font_size, color)
            self._current_color = color
            
            self.content_edit.setFocus()

    def _apply_default_format(self):
        """Terapkan format default untuk note yang sedang aktif."""
        if not self.current_note_id:
            return
        if self.current_note_id in self._note_font_settings:
            size, color = self._note_font_settings[self.current_note_id]
        else:
            size = self._default_font_size
            color = self._default_color
        
        cursor = self.content_edit.textCursor()
        if not cursor.hasSelection():
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            fmt.setForeground(color)
            # ── Terapkan bold/italic/underline default ──
            fmt.setFontWeight(QFont.Weight.Bold if self._current_bold else QFont.Weight.Normal)
            fmt.setFontItalic(self._current_italic)
            fmt.setFontUnderline(self._current_underline)
            # ── ──
            self.content_edit.setCurrentCharFormat(fmt)

    def _toggle_format(self, format_type):
        """Toggle bold/italic/underline untuk teks yang dipilih atau untuk teks selanjutnya."""
        cursor = self.content_edit.textCursor()
        fmt = QTextCharFormat()
        
        # Tentukan status toggle
        if format_type == 'bold':
            current = self._current_bold
            new_state = not current
            fmt.setFontWeight(QFont.Weight.Bold if new_state else QFont.Weight.Normal)
            # Update status default
            self._current_bold = new_state
            self.bold_btn.setChecked(new_state)
        elif format_type == 'italic':
            current = self._current_italic
            new_state = not current
            fmt.setFontItalic(new_state)
            self._current_italic = new_state
            self.italic_btn.setChecked(new_state)
        elif format_type == 'underline':
            current = self._current_underline
            new_state = not current
            fmt.setFontUnderline(new_state)
            self._current_underline = new_state
            self.underline_btn.setChecked(new_state)
        else:
            return
        
        # Pertahankan ukuran dan warna
        fmt.setFontPointSize(self._current_font_size)
        fmt.setForeground(self._current_color)
        
        if cursor.hasSelection():
            # Terapkan ke teks yang dipilih (merge)
            cursor.mergeCharFormat(fmt)
        else:
            # Terapkan sebagai format default untuk teks baru
            self.content_edit.setCurrentCharFormat(fmt)
        
        self.content_edit.setFocus()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        AppState.unregister_lang_cb(self.load)
        super().closeEvent(e)

# ── Custom QTextEdit untuk paste dengan tetap mempertahankan format, tetapi ukuran dan warna direset ──
class NotesTextEdit(QTextEdit):
    def __init__(self, parent):
        super().__init__(parent)
        self.notes_page = parent  # referensi ke NotesPage untuk ambil setting font

    def insertFromMimeData(self, source):
        """Paste HTML dari clipboard, ubah font-size dan color sesuai setting notes."""
        if source.hasHtml():
            html = source.html()
            # Ambil ukuran dan warna dari notes page
            size = self.notes_page._current_font_size
            color = self.notes_page._current_color.name()
            
            # Ganti font-size: ...px dengan setting user
            # Contoh: font-size: 24px → font-size: 12px
            html = re.sub(r'font-size:\s*\d+px', f'font-size:{size}px', html)
            # Ganti font-size: ...pt dengan setting user (jika ada)
            html = re.sub(r'font-size:\s*\d+pt', f'font-size:{size}px', html)
            
            # Ganti color: #... atau rgb(...) dengan setting user
            html = re.sub(r'color:\s*#[0-9a-fA-F]{6}', f'color:{color}', html)
            html = re.sub(r'color:\s*rgb\(\d+,\s*\d+,\s*\d+\)', f'color:{color}', html)
            
            # Sisipkan HTML yang sudah dimodifikasi
            self.insertHtml(html)
        elif source.hasText():
            # Jika hanya teks polos, gunakan insertPlainText agar mengikuti format default
            self.insertPlainText(source.text())
        else:
            super().insertFromMimeData(source)

# ══════════════════════════════════════════════════════════════════════════════
#  Reminders Page 
# ══════════════════════════════════════════════════════════════════════════════
class RemindersPage(QWidget):
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.player = None
        self.audio_output = None
        self._test_sound_playing = False
        self._build()
        AppState.register(self.load)
        AppState.register_lang_cb(self.load)

    def _build(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 16)
        main_layout.setSpacing(10)

        # Header
        hdr = QHBoxLayout()
        hdr.addWidget(_lbl(tr("reminders_title"), "section", 14, True))
        hdr.addStretch()
        main_layout.addLayout(hdr)
        main_layout.addWidget(_sep())

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn = _btn(tr("reminders_add"), "solid", self._add_reminder)
        refresh_btn = _btn(tr("reminders_refresh"), slot=self.load)
        toolbar.addWidget(add_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Daftar reminder
        self.reminder_list = QListWidget()
        self.reminder_list.setMinimumHeight(300)
        self.reminder_list.itemClicked.connect(self._on_item_clicked)
        main_layout.addWidget(self.reminder_list)

        # Tombol aksi (untuk item yang dipilih)
        action_row = QHBoxLayout()
        self.edit_btn = _btn(tr("reminders_edit"), slot=self._edit_selected)
        self.delete_btn = _btn(tr("reminders_delete"), "danger", self._delete_selected)
        self.toggle_btn = _btn(tr("reminders_toggle"), slot=self._toggle_selected) 
        self.test_btn = _btn(tr("reminders_test"), "gold", self._test_selected)
        action_row.addWidget(self.edit_btn)
        action_row.addWidget(self.delete_btn)
        action_row.addWidget(self.toggle_btn)
        action_row.addWidget(self.test_btn)
        action_row.addStretch()
        main_layout.addLayout(action_row)

        self._selected_id = None
        self.load()

    def load(self):
        if not AppState.user_id:
            return
        self.reminder_list.clear()
        reminders = db.get_reminders(self.user_id)
        if not reminders:
            empty = QListWidgetItem(tr("reminders_empty"))
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            self.reminder_list.addItem(empty)
            return
        for r in reminders:
            status = "🔔" if r["is_active"] else "🔕"
            triggered = " ✅" if r["triggered"] else ""
            time_str = r["reminder_datetime"][:16].replace("T", " ")
            item = QListWidgetItem(f"{status} {r['title']} - {time_str}{triggered}")
            item.setData(Qt.ItemDataRole.UserRole, r["id"])
            if not r["is_active"]:
                item.setForeground(QColor(_T("muted")))
            self.reminder_list.addItem(item)

    def _add_reminder(self):
        dlg = ReminderDialog(self.user_id, parent=self)
        if dlg.exec():
            self.load()

    def _edit_selected(self):
        if self._selected_id is None:
            return
        r = db.get_reminder(self._selected_id, self.user_id)
        if r:
            dlg = ReminderDialog(self.user_id, r, parent=self)
            if dlg.exec():
                self.load()

    def _delete_selected(self):
        if self._selected_id is None:
            return
        self._stop_sound()
        reply = QMessageBox.question(self, tr("confirm_title"), tr("reminders_delete_confirm"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            db.delete_reminder(self._selected_id, self.user_id)
            SND.click()
            self.load()

    def _toggle_selected(self):
        if self._selected_id is None:
            return
        self._stop_sound() 
        r = db.get_reminder(self._selected_id, self.user_id)
        if r:
            new_state = 0 if r["is_active"] else 1
            db.update_reminder(self._selected_id, self.user_id, is_active=new_state)
            if new_state:
                # reset triggered jika diaktifkan kembali
                db.reset_reminder_triggered(self._selected_id, self.user_id)
            SND.notify()
            self.load()

    def _test_selected(self):
        if self._selected_id is None:
            return
        r = db.get_reminder(self._selected_id, self.user_id)
        if r:
            self._stop_sound()  # hentikan suara sebelumnya jika ada
            self._test_sound_playing = True
            self._play_sound(r["sound_type"], r["sound_file"])
            # Tampilkan dialog dengan tombol OK, setelah OK suara dihentikan
            dlg = QDialog(self)
            dlg.setWindowTitle(tr("reminders_test_title"))
            dlg.setMinimumWidth(350)
            dlg.setMinimumHeight(120)
            dlg.setStyleSheet(build_ss())
            layout = QVBoxLayout(dlg)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)
            layout.addWidget(QLabel(tr("reminders_test_msg", title=r["title"])))
            ok_btn = _btn(tr("msg_ok"), "solid", dlg.accept)
            layout.addWidget(ok_btn)
            dlg.exec()
            # Setelah dialog ditutup, hentikan suara
            self._stop_sound()
            self._test_sound_playing = False

    def _play_sound(self, sound_type, sound_file=None):
        if sound_type == "default":
            SND.notify()
        elif sound_type == "beep1":
            SND._beep(600, 200)
            SND._beep(800, 200)
        elif sound_type == "beep2":
            SND._beep(400, 300)
            SND._beep(600, 300)
            SND._beep(800, 300)
        elif sound_type == "custom" and sound_file and os.path.exists(sound_file):
            self._play_mp3(sound_file)
        else:
            SND.notify()

    def _play_mp3(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"File MP3 tidak ditemukan: {filepath}")
                return
            
            if self.player is None:
                self.player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.player.setAudioOutput(self.audio_output)
                
                # Tambahkan debug error
                self.player.errorOccurred.connect(self._handle_media_error)
            
            url = QUrl.fromLocalFile(filepath)
            self.player.setSource(url)
            self.audio_output.setVolume(1.0)
            self.player.play()
            print(f"Memutar MP3: {filepath}")
            
        except Exception as e:
            print(f"Error playing MP3: {e}")
            import traceback
            traceback.print_exc()

    def _stop_sound(self):
        try:
            if self.player and self.player.isPlaying():
                self.player.stop()
                print("Suara dihentikan")
            self._test_sound_playing = False
        except Exception as e:
            print(f"Error stopping sound: {e}")

    def _handle_media_error(self, error):
        print(f"Media error: {error}")

    def _on_item_clicked(self, item):
        self._selected_id = item.data(Qt.ItemDataRole.UserRole)

    def closeEvent(self, e):
        self._stop_sound()
        AppState.unregister(self.load)
        AppState.unregister_lang_cb(self.load)
        if self.player:
            self.player.stop()
        super().closeEvent(e)

class ReminderDialog(QDialog):
    def __init__(self, user_id, reminder=None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.reminder = reminder
        self.setWindowTitle(tr("reminders_edit_title") if reminder else tr("reminders_add_title"))
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)
        self.setStyleSheet(build_ss())
        self._build()
        if reminder:
            self._load_data()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        lay.addWidget(_lbl(self.windowTitle(), "section", 14, True))
        lay.addWidget(_sep())

        # Judul
        lay.addWidget(_lbl(tr("reminders_title_label"), size=12))
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText(tr("reminders_title_ph"))
        lay.addWidget(self.title_edit)

        # Deskripsi
        lay.addWidget(_lbl(tr("reminders_desc_label"), size=12))
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText(tr("reminders_desc_ph"))
        self.desc_edit.setMaximumHeight(80)
        lay.addWidget(self.desc_edit)

        # Waktu
        lay.addWidget(_lbl(tr("reminders_datetime_label"), size=12))
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDateTime(QDateTime.currentDateTime())
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        lay.addWidget(self.datetime_edit)

        # ========== Repeat Options ==========
        lay.addWidget(_lbl(tr("reminders_repeat_label"), size=12))
        self.repeat_combo = QComboBox()
        self.repeat_combo.addItem(tr("reminders_repeat_none"), "none")
        self.repeat_combo.addItem(tr("reminders_repeat_daily"), "daily")
        self.repeat_combo.addItem(tr("reminders_repeat_weekly"), "weekly")
        self.repeat_combo.addItem(tr("reminders_repeat_custom"), "custom")
        self.repeat_combo.currentIndexChanged.connect(self._on_repeat_changed)
        lay.addWidget(self.repeat_combo)

        # Container untuk custom days (checkbox)
        self.custom_days_widget = QWidget()
        custom_days_layout = QHBoxLayout(self.custom_days_widget)
        self.day_checkboxes = []
        day_names = [tr("day_mon_short"), tr("day_tue_short"), tr("day_wed_short"),
                     tr("day_thu_short"), tr("day_fri_short"), tr("day_sat_short"), tr("day_sun_short")]
        for i, name in enumerate(day_names):
            cb = QCheckBox(name)
            cb.setStyleSheet(f"color:{_T('text')};")
            self.day_checkboxes.append(cb)
            custom_days_layout.addWidget(cb)
        self.custom_days_widget.setVisible(False)
        lay.addWidget(self.custom_days_widget)

        # Suara
        lay.addWidget(_lbl(tr("reminders_sound_label"), size=12))
        sound_row = QHBoxLayout()
        self.sound_combo = QComboBox()
        self.sound_combo.addItem(tr("reminders_sound_default"), "default")
        self.sound_combo.addItem(tr("reminders_sound_beep1"), "beep1")
        self.sound_combo.addItem(tr("reminders_sound_beep2"), "beep2")
        self.sound_combo.addItem(tr("reminders_sound_custom"), "custom")
        self.sound_combo.currentIndexChanged.connect(self._on_sound_changed)
        sound_row.addWidget(self.sound_combo, 1)

        self.browse_btn = _btn(tr("reminders_browse"), slot=self._browse_file)  # ← perbaiki
        self.browse_btn.setEnabled(False)
        sound_row.addWidget(self.browse_btn)

        self.sound_file_label = QLabel("")
        self.sound_file_label.setStyleSheet(f"color:{_T('muted')}; font-size:11px;")
        lay.addLayout(sound_row)
        lay.addWidget(self.sound_file_label)

        lay.addSpacing(8)
        save_btn = _btn(tr("dialog_save"), "solid", self._save)  # ← sudah benar (slot di posisi ketiga)
        lay.addWidget(save_btn)

        root.addWidget(_scrolled(content))

    def _on_sound_changed(self, idx):
        sound_type = self.sound_combo.currentData()
        self.browse_btn.setEnabled(sound_type == "custom")
        if sound_type != "custom":
            self.sound_file_label.setText("")

    def _browse_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            tr("reminders_select_mp3"),
            "",
            "MP3 Files (*.mp3);;All Files (*.*)"
        )
        if filepath:
            self.sound_file_label.setText(os.path.basename(filepath))
            self.sound_file_label.setStyleSheet(f"color:{_T('accent')}; font-size:11px;")
            self._selected_file = filepath

    def _load_data(self):
        r = self.reminder
        self.title_edit.setText(r["title"])
        self.desc_edit.setText(r["description"] or "")
        dt = QDateTime.fromString(r["reminder_datetime"], "yyyy-MM-dd HH:mm:ss")
        if dt.isValid():
            self.datetime_edit.setDateTime(dt)
        # Load repeat
        idx = self.repeat_combo.findData(r.get("repeat_type", "none"))
        if idx >= 0:
            self.repeat_combo.setCurrentIndex(idx)
        # Load repeat days
        days = r.get("repeat_days", "")
        if days:
            day_list = [int(d.strip()) for d in days.split(',') if d.strip()]
            for i, cb in enumerate(self.day_checkboxes):
                cb.setChecked(i in day_list)
        if r["sound_file"]:
            self.sound_file_label.setText(os.path.basename(r["sound_file"]))
            self._selected_file = r["sound_file"]

    def _on_repeat_changed(self, idx):
        repeat_type = self.repeat_combo.currentData()
        self.custom_days_widget.setVisible(repeat_type == "custom")

    def _save(self):
        if hasattr(self.parent(), '_stop_sound'):
            self.parent()._stop_sound()
        title = self.title_edit.text().strip()
        if not title:
            _show(self, tr("msg_error"), tr("reminders_title_required"), "error")
            return
        description = self.desc_edit.toPlainText().strip()
        dt = self.datetime_edit.dateTime()
        if not dt.isValid():
            _show(self, tr("msg_error"), tr("reminders_invalid_datetime"), "error")
            return
        now = QDateTime.currentDateTime()
        if dt < now:
            reply = QMessageBox.question(self, tr("confirm_title"), tr("reminders_past_datetime_confirm"),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return

        sound_type = self.sound_combo.currentData()
        sound_file = None
        if sound_type == "custom":
            if hasattr(self, '_selected_file') and self._selected_file:
                sound_file = self._selected_file
            else:
                _show(self, tr("msg_error"), tr("reminders_custom_file_required"), "error")
                return

        datetime_str = dt.toString("yyyy-MM-dd HH:mm:ss")

        repeat_type = self.repeat_combo.currentData()
        repeat_days = ""
        if repeat_type == "custom":
            selected = [str(i) for i, cb in enumerate(self.day_checkboxes) if cb.isChecked()]
            if not selected:
                _show(self, tr("msg_error"), tr("reminders_custom_days_required"), "error")
                return
            repeat_days = ",".join(selected)

        if self.reminder:
            db.update_reminder(
                self.reminder["id"],
                self.user_id,
                title=title,
                description=description,
                reminder_datetime=datetime_str,
                sound_type=sound_type,
                sound_file=sound_file,
                triggered=0,
                repeat_type=repeat_type,
                repeat_days=repeat_days,
            )
            SND.complete()
            _show(self, tr("berhasil_title"), tr("reminders_updated"), "success")
        else:
            r = db.add_reminder(self.user_id, title, description, datetime_str, sound_type, sound_file, repeat_type, repeat_days)
            if r["ok"]:
                SND.complete()
                _show(self, tr("berhasil_title"), tr("reminders_added"), "success")
            else:
                SND.error()
                _show(self, tr("gagal_title"), r.get("msg", "Gagal menambah reminder"), "error")
                return
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    logout_signal = pyqtSignal()

    def __init__(self, user: dict):
        super().__init__()
        
        self.reminder_player = None
        self.reminder_audio_output = None
        self.reminder_beep_timer = None

        self.setWindowIcon(QIcon(get_icon_path('craftlife.ico')))
        AppState.set_user(user["id"])
        QTimer.singleShot(300, lambda: TimeSync.sync())
        QTimer.singleShot(500, lambda: db.reset_daily_tasks(user["id"]))

        dn = user.get("display_name") or user.get("username", "")
        self.setWindowTitle(tr("app_title_format", name=dn))
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(build_ss())
        self._pages: dict = {}
        self._build()
        AppState.register(self._topbar.refresh)

        self._timer = QTimer()
        self._timer.timeout.connect(self._topbar.refresh)
        self._timer.start(20000)
        self._reminder_timer = QTimer()
        self._reminder_timer.timeout.connect(self._check_reminders)
        self._reminder_timer.start(5000)  # cek setiap 5 detik
        self._setup_tray_icon()
        self._pages["settings"].language_changed.connect(self._refresh_language_only)
        self._active_reminder_id = None
        self._pages["settings"].language_changed.connect(self._refresh_language_only)

    def _play_reminder_beep_loop(self, beep_func):
        """Looping beep menggunakan QTimer (setiap 2 detik)."""
        if self.reminder_beep_timer:
            self.reminder_beep_timer.stop()
            self.reminder_beep_timer.deleteLater()
            self.reminder_beep_timer = None
        self.reminder_beep_timer = QTimer()
        self.reminder_beep_timer.timeout.connect(beep_func)
        self.reminder_beep_timer.start(2000)  # 2 detik

    def _play_reminder_mp3_loop(self, filepath):
        """Looping MP3 menggunakan QMediaPlayer (ulang otomatis saat selesai)."""
        if not os.path.exists(filepath):
            return
        if self.reminder_player is None:
            self.reminder_player = QMediaPlayer()
            self.reminder_audio_output = QAudioOutput()
            self.reminder_player.setAudioOutput(self.reminder_audio_output)
        # Hapus koneksi sebelumnya jika ada
        try:
            self.reminder_player.mediaStatusChanged.disconnect()
        except:
            pass
        # Fungsi untuk memutar ulang saat selesai
        def on_status_changed(status):
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.reminder_player.play()
        self.reminder_player.mediaStatusChanged.connect(on_status_changed)
        url = QUrl.fromLocalFile(filepath)
        self.reminder_player.setSource(url)
        self.reminder_audio_output.setVolume(1.0)
        self.reminder_player.play()

    def _stop_reminder_sounds(self):
        """Hentikan semua suara reminder (beep dan MP3)."""
        if self.reminder_beep_timer:
            self.reminder_beep_timer.stop()
            self.reminder_beep_timer.deleteLater()
            self.reminder_beep_timer = None
        if self.reminder_player:
            try:
                self.reminder_player.mediaStatusChanged.disconnect()
            except:
                pass
            if self.reminder_player.isPlaying():
                self.reminder_player.stop()

    def load(self):
        """Called when language changes (if registered)"""
        self._refresh_language_only()

    def _refresh_language_only(self):
        for p in self._pages.values():
            if hasattr(p, "load"):
                p.load()
        if hasattr(self, '_topbar'):
            self._topbar.load()
        if hasattr(self, '_nav'):
            self._nav.load()

    def _refresh_language_only(self):
        # Hanya refresh teks tanpa reload semua halaman (biar cepat)
        for p in self._pages.values():
            if hasattr(p, "load"):
                p.load()
        # Update top bar
        if hasattr(self, '_topbar'):
            self._topbar.load()

    def _setup_tray_icon(self):
        """Buat System Tray Icon dengan menu konteks."""
        try:
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(QIcon(get_icon_path('craftlife.ico')))
            self.tray_icon.setToolTip("⛏ CraftLife")
            
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction(tr("restore_window"))
            show_action.triggered.connect(self.showNormal)
            
            quit_action = tray_menu.addAction(tr("exit_application"))
            quit_action.triggered.connect(QApplication.instance().quit)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
        except Exception as e:
            print(f"Tray icon tidak tersedia: {e}")

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
        
        # ===== BUAT HANYA SETTINGS SECARA LANGSUNG (tidak lazy) =====
        # Settings diperlukan untuk koneksi sinyal sejak awal
        settings_page = SettingsPage(uid)
        self._pages = {"settings": settings_page}   # inisialisasi dengan settings
        self._stack = QStackedWidget()
        self._stack.addWidget(settings_page)
        self._pages["settings"].theme_changed.connect(self._retheme)

        # ===== LAZY LOAD UNTUK HALAMAN LAINNYA =====
        self._page_classes = {
            "habits":      lambda: TaskPage(uid, "habit"),
            "dailies":     lambda: TaskPage(uid, "daily"),
            "todos":       lambda: TaskPage(uid, "todo"),
            "sport":       lambda: SportTrackPage(uid),
            "economy":     lambda: EconomyPage(uid),
            "health_food": lambda: HealthFoodPage(uid),
            "calendar":    lambda: CalendarPage(uid),
            "notes":       lambda: NotesPage(uid),
            "reminders":   lambda: RemindersPage(uid),
            "shop":        lambda: ShopPage(uid),
            "pets":        lambda: PetsPage(uid),
            "friends":     lambda: FriendsPage(uid),
            "guild":       lambda: GuildPage(uid),
            "stats":       lambda: StatsPage(uid),
            "achievements": lambda: AchievementPage(uid),
            "profile":     lambda: ProfilePage(uid),
            "leaderboard": lambda: LeaderboardPage(),
        }

        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        # Halaman awal: habits
        self._switch("habits")

    def _switch(self, key: str):
        # Buat halaman jika belum ada
        if key not in self._pages:
            if key in self._page_classes:
                page = self._page_classes[key]()
                self._pages[key] = page
                self._stack.addWidget(page)
            else:
                return
        
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
                _show(self, tr("msg_error"), tr("error_loading_page", key=key, e=e), "error")
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
        self._nav.reload_texts() 

        # Reload every page so colours update
        for p in self._pages.values():
            p.setStyleSheet(new_ss)
            if hasattr(p, "load"):
                try:
                    p.load()
                except Exception:
                    pass

        _show(self, tr("theme_changed_title"), tr("theme_change_success"), "success")

    def _play_mp3(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"File MP3 tidak ditemukan: {filepath}")
                return
            
            if self.player is None:
                self.player = QMediaPlayer()
                self.audio_output = QAudioOutput()
                self.player.setAudioOutput(self.audio_output)
                
                # Tambahkan debug error
                self.player.errorOccurred.connect(self._handle_media_error)
            
            url = QUrl.fromLocalFile(filepath)
            self.player.setSource(url)
            self.audio_output.setVolume(1.0)
            self.player.play()
            print(f"Memutar MP3: {filepath}")
            
        except Exception as e:
            print(f"Error playing MP3: {e}")
            import traceback
            traceback.print_exc()

    def _handle_media_error(self, error):
        print(f"Media error: {error}")

    def _check_reminders(self):
        if not AppState.user_id:
            return
        reminders = db.get_pending_reminders(AppState.user_id)
        for r in reminders:
            self._show_reminder_alert(r)
            repeat_type = r.get("repeat_type", "none")
            if repeat_type != "none":
                next_dt = db.get_next_reminder_datetime(
                    r["reminder_datetime"],
                    repeat_type,
                    r.get("repeat_days", "")
                )
                if next_dt:
                    db.update_reminder(
                        r["id"],
                        AppState.user_id,
                        reminder_datetime=next_dt,
                        triggered=0,
                        is_active=1
                    )
                else:
                    db.update_reminder(
                        r["id"],
                        AppState.user_id,
                        is_active=0,
                        triggered=1
                    )
            else:
                db.mark_reminder_triggered(r["id"], AppState.user_id)

    def _show_reminder_alert(self, reminder):
        """Tampilkan dialog reminder dengan suara looping sampai OK diklik."""
        # Tampilkan notifikasi tray jika tersedia
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                tr("reminders_alert_title"),
                f"⏰ {reminder['title']}",
                QSystemTrayIcon.MessageIcon.Information,
                5000
            )

        # Mulai suara looping sesuai jenis
        sound_type = reminder["sound_type"]
        sound_file = reminder["sound_file"]

        if sound_type == "custom" and sound_file and os.path.exists(sound_file):
            self._play_reminder_mp3_loop(sound_file)
        else:
            # Tentukan fungsi beep
            if sound_type == "beep1":
                beep_func = lambda: SND._beep(600, 200)
            elif sound_type == "beep2":
                beep_func = lambda: SND._beep(400, 300)
            else:
                beep_func = lambda: SND.notify()
            self._play_reminder_beep_loop(beep_func)

        # Buat dialog
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("reminders_alert_title"))
        dlg.setMinimumWidth(400)
        dlg.setMinimumHeight(180)
        dlg.setStyleSheet(build_ss())

        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        msg = f"⏰ {reminder['title']}\n{reminder['description'] or ''}\n\nWaktu: {reminder['reminder_datetime']}"
        lbl = QLabel(msg)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {_T('text')}; font-size:13px;")
        layout.addWidget(lbl)

        ok_btn = _btn(tr("msg_ok"), "solid", dlg.accept, 40)
        layout.addWidget(ok_btn)

        # Hentikan suara saat dialog ditutup (OK atau close)
        def on_finished():
            self._stop_reminder_sounds()
        dlg.finished.connect(on_finished)

        dlg.exec()

        # Tambahkan notifikasi ke database
        db.add_notification(
            AppState.user_id,
            db.tr_db(AppState.user_id, "reminders_notification", title=reminder['title']),
            "warning"
        )

    def _play_mp3_reminder(self, filepath):
        try:
            if not os.path.exists(filepath):
                print(f"File MP3 reminder tidak ditemukan: {filepath}")
                return
            
            if not hasattr(self, '_player') or self._player is None:
                self._player = QMediaPlayer()
                self._audio_output = QAudioOutput()
                self._player.setAudioOutput(self._audio_output)
                self._player.errorOccurred.connect(self._handle_media_error)
            
            url = QUrl.fromLocalFile(filepath)
            self._player.setSource(url)
            self._audio_output.setVolume(1.0)
            self._player.play()
            print(f"Memutar MP3 reminder: {filepath}")
            
        except Exception as e:
            print(f"Error playing MP3 reminder: {e}")

    def _handle_media_error(self, error):
        print(f"Media error: {error}")

    def _stop_reminder_sound(self):
        try:
            if hasattr(self, '_player') and self._player is not None:
                if self._player.isPlaying():
                    self._player.stop()
                    print("Reminder sound stopped")
        except Exception as e:
            print(f"Error stopping reminder sound: {e}")

    def closeEvent(self, e):
        # Hentikan semua timer
        if hasattr(self, '_timer') and self._timer.isActive():
            self._timer.stop()
        if hasattr(self, '_reminder_timer') and self._reminder_timer.isActive():
            self._reminder_timer.stop()
        
        # Hentikan suara reminder
        self._stop_reminder_sounds()
        
        # ── FORCE CHECKPOINT SEBELUM TUTUP ──
        db.stop_periodic_checkpoint()
        db.force_checkpoint()
        
        # ── (OPSIONAL) BUAT BACKUP OTOMATIS ──
        # db.backup_database()  # Buka komentar jika ingin backup setiap tutup
        
        AppState.unregister(self._topbar.refresh)
        super().closeEvent(e)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
def main():
    setup_error_handling()
    try:
        db.init_db()
    except Exception:
        import traceback
        with open("init_db_error.log", "w") as f:
            traceback.print_exc(file=f)
        print("Error di init_db(), lihat init_db_error.log")
        input("Tekan Enter untuk keluar...")   # pause
        sys.exit(1)

    import os
    os.environ["QT_LOGGING_RULES"] = "*.debug=false;qt.qpa.*=false"

    app = QApplication(sys.argv)
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    app.setApplicationName("CraftLife")
    app.setStyleSheet(build_ss())

    login = LoginWindow()
    main_win = None

    def on_login(user):
        nonlocal main_win
        AppState.set_user(user["id"])
        db.start_periodic_checkpoint(10) 

        th = db.get_user_theme(user["id"])
        apply_theme(th)
        app.setStyleSheet(build_ss())
        main_win = MainWindow(user)
        main_win.logout_signal.connect(lambda: login.show()) 
        main_win.show()
        login.hide()

    def on_main_window_closed():
        nonlocal main_win
        if main_win is not None:
            main_win.deleteLater() 
        login.show()

    # ── Hubungkan sinyal login ──
    login.logged_in.connect(on_login)

    # ── Jalankan login dialog ──
    result = login.exec()
    if result == QDialog.DialogCode.Accepted:
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()