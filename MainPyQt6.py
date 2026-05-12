"""
CraftLife Desktop  —  main_pyqt6.py  v3.0  (all bugs fixed)
PyQt6 Windows / Linux / macOS
Install : pip install PyQt6
Run     : python main_pyqt6.py
"""
from multiprocessing.util import info
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QScrollArea, QFrame,
    QTabWidget, QDialog, QProgressBar, QGridLayout, QTextEdit,
    QCheckBox, QStackedWidget, QSizePolicy, QGroupBox, QListWidget,
    QSpinBox, QGraphicsOpacityEffect, QRadioButton, QButtonGroup,
    QFormLayout, QMessageBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QColor, QFont

import database as db

import traceback
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

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
        # Abort if widget is already animating to prevent paint device conflicts
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

        logo = QLabel("⛏  CraftLife")
        logo.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {_T('light')};")
        lay.addWidget(logo)
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

        self.refresh()

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
        self._xp_bar.setValue(xp)
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
        self._xp_lbl.setStyleSheet(
            f"color: {_T('accent')}; font-size: 11px; font-weight: bold;")
        self._xp_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background: {_T('accent')}; border-radius:4px; }}")
        self.refresh()


# ══════════════════════════════════════════════════════════════════════════════
#  NAV BAR  (left sidebar)
# ══════════════════════════════════════════════════════════════════════════════
class NavBar(QWidget):
    tab_changed = pyqtSignal(str)

    _TABS = [
        ("⛏", "Habits",   "habits"),
        ("📅", "Dailies",  "dailies"),
        ("📜", "Quests",   "todos"),
        ("🏪", "Shop",     "shop"),
        ("🐾", "Pets",    "pets"),
        ("⚔️", "Guild",    "guild"),
        ("📊", "Stats",    "stats"),
        ("🎭", "Profile",  "profile"),
        ("⚙️", "Settings", "settings"),
        
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

        # Positive / negative (habits only)
        if self.mode == "habit":
            row = QHBoxLayout()
            row.setSpacing(16)
            self._pos = QCheckBox("Positif  ✔  (centang berhasil)")
            self._pos.setChecked(True)
            self._neg = QCheckBox("Negatif  ✗  (kurangi HP kalau gagal)")
            row.addWidget(self._pos)
            row.addWidget(self._neg)
            lay.addLayout(row)

        # Notes
        lay.addWidget(_lbl("Catatan  (opsional)", size=12))
        self._notes = _input("Catatan…")
        lay.addWidget(self._notes)

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
        if self.mode == "habit":
            db.add_habit(self.user_id, name, icon, diff,
                         int(self._pos.isChecked()),
                         int(self._neg.isChecked()), notes)
        elif self.mode == "daily":
            db.add_daily(self.user_id, name, icon, diff, notes)
        else:
            db.add_todo(self.user_id, name, diff, icon, None, notes)
        SND.complete()
        self.accept()


# ══════════════════════════════════════════════════════════════════════════════
#  TASK PAGE  (Habits / Dailies / Todos)
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
        add = _btn("➕  Tambah", "solid", self._open_add)
        add.setFixedWidth(130)
        hdr.addWidget(add)
        root.addLayout(hdr)
        root.addWidget(_sep())

        self._inner = QWidget()
        self._lay   = QVBoxLayout(self._inner)
        self._lay.setSpacing(8)
        self._lay.addStretch()
        root.addWidget(_scrolled(self._inner))
        self.load()

    def load(self):
        if not AppState.user_id:   # guard
            return
        db.reset_daily_tasks(self.user_id)
        # Remove all except the trailing stretch
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if self.mode == "habit":
            items = db.get_habits(self.user_id)
        elif self.mode == "daily":
            items = db.get_dailies(self.user_id)
        else:
            items = db.get_todos(self.user_id)

        if not items:
            e_icon = {"habit": "⛏️", "daily": "📅", "todo": "📜"}[self.mode]
            e_msg  = {
                "habit": "Belum ada habit. Tambahkan yang pertama!",
                "daily": "Belum ada daily. Buat rutinitasmu!",
                "todo":  "Quest log kosong. Tambahkan tugasmu!",
            }[self.mode]
            el = _lbl(f"{e_icon}  {e_msg}", "sub", 13)
            el.setAlignment(Qt.AlignmentFlag.AlignCenter)
            el.setStyleSheet(f"color: {_T('muted')}; padding: 40px;")
            self._lay.insertWidget(0, el)
            return

        for item in items:
            card = self._make_card(item)
            self._lay.insertWidget(self._lay.count() - 1, card)

            # fade_in(card, 180)

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
            notes_lbl.setStyleSheet(f"color:{_T('muted')}; font-size:11px; font-style:italic;")
            info.addWidget(notes_lbl)

        # Action buttons
        if self.mode == "habit":
            if item.get("positive"):
                ck = _btn("✔ Done" if done else "✔ Check", h=36)
                ck.setEnabled(not done)
                if done:
                    ck.setStyleSheet(
                        f"background:{_T('border')}; color:{_T('muted')};"
                        f" border-color:{_T('border')};")
                ck.setFixedWidth(92)
                ck.clicked.connect(
                    lambda _, i=item["id"]: self._do("up", i))
                row.addWidget(ck)
            if item.get("negative"):
                nb = _btn("✗ Gagal", "danger", h=36)
                nb.setEnabled(not done)
                if done:
                    nb.setStyleSheet(
                        f"background:{_T('border')}; color:{_T('muted')};"
                        f" border-color:{_T('border')};")
                nb.setFixedWidth(82)
                nb.clicked.connect(
                    lambda _, i=item["id"]: self._do("down", i))
                row.addWidget(nb)
        elif self.mode == "daily":
            ck = _btn("✔ Done" if done else "✔ Check", h=36)
            ck.setEnabled(not done)
            if done:
                ck.setStyleSheet(
                    f"background:{_T('border')}; color:{_T('muted')};"
                    f" border-color:{_T('border')};")
            ck.setFixedWidth(92)
            ck.clicked.connect(
                lambda _, i=item["id"]: self._do_daily(i))
            row.addWidget(ck)
        else:   # todo
            cb = QCheckBox()
            cb.setChecked(done)
            cb.setEnabled(not done)
            cb.stateChanged.connect(
                lambda _, i=item["id"]: self._do_todo(i))
            row.addWidget(cb)

        dl = _btn("🗑", "danger", h=36)
        dl.setFixedWidth(36)
        dl.clicked.connect(lambda _, i=item["id"]: self._delete(i))
        row.addWidget(dl)
        return f

    # ── actions ───────────────────────────────────────────────────────────────

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

    def _open_add(self):
        dlg = AddTaskDialog(self.mode, self.user_id, self)
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
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.load()

    def load(self):
        # Bersihkan grid
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
        for i, p in enumerate(pets):
            pet_data = db.PETS_DATA.get(p["pet_id"], {})
            card = _card()
            vlay = QVBoxLayout(card)
            vlay.setSpacing(6)
            # Icon & nama
            top = QHBoxLayout()
            top.addWidget(QLabel(pet_data.get("icon", "🐾"), font=QFont("Segoe UI", 28)))
            name = QLabel(pet_data.get("name", p["pet_id"]))
            name.setStyleSheet(f"font-size:14px; font-weight:bold; color:{_T('text')};")
            top.addWidget(name)
            if p["is_active"]:
                active_lbl = QLabel("✔ AKTIF")
                active_lbl.setStyleSheet(f"color:{_T('light')}; font-size:11px;")
                top.addWidget(active_lbl)
            top.addStretch()
            vlay.addLayout(top)
            # Level & EXP
            level_lbl = QLabel(f"Level {p['level']}")
            level_lbl.setStyleSheet(f"color:{_T('accent')};")
            exp_needed = p["level"] * 100
            exp_bar = QProgressBar()
            exp_bar.setMaximum(exp_needed)
            exp_bar.setValue(p["exp"])
            exp_bar.setFormat(f"EXP: {p['exp']}/{exp_needed}")
            vlay.addWidget(level_lbl)
            vlay.addWidget(exp_bar)
            # Hunger
            hunger_bar = QProgressBar()
            hunger_bar.setMaximum(100)
            hunger_bar.setValue(p["hunger"])
            hunger_bar.setFormat(f"Hunger: {p['hunger']}/100")
            hunger_bar.setStyleSheet("QProgressBar::chunk { background: #f0a800; }")
            vlay.addWidget(hunger_bar)
            # Buff dari pet
            base_buff = pet_data.get("base_buff", {})
            scale = 1 + (p["level"]-1)*0.02
            buff_text = []
            if "xp_pct" in base_buff:
                buff_text.append(f"📈 +{base_buff['xp_pct']*scale:.1f}% XP")
            if "gold_pct" in base_buff:
                buff_text.append(f"💰 +{base_buff['gold_pct']*scale:.1f}% Gold")
            if "boss_dmg" in base_buff:
                buff_text.append(f"⚔️ +{base_buff['boss_dmg']*scale:.1f} DMG Boss")
            if "hp_reduc" in base_buff:
                buff_text.append(f"🛡️ -{base_buff['hp_reduc']*scale:.1f} HP taken")
            if buff_text:
                buff_label = QLabel(" | ".join(buff_text))
                buff_label.setStyleSheet(f"font-size:10px; color:{_T('muted')};")
                vlay.addWidget(buff_label)
            # Tombol aksi
            btn_row = QHBoxLayout()
            feed_btn = _btn(f"🍖 Makan (10 G)", h=30)
            feed_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._feed(pid))
            train_btn = _btn(f"🏋️ Latih (5 G)", h=30)
            train_btn.clicked.connect(lambda _, pid=p["pet_id"]: self._train(pid))
            equip_btn = _btn("⭐ Equip", "diamond", h=30)
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
        self._root.addWidget(hrow_w)

        if guild.get("description"):
            self._root.addWidget(_lbl(f"📝  {guild['description']}", "sub", 12))

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
            pb.setMaximum(m["max_hp"])
            pb.setValue(m["hp"])
            pb.setFixedHeight(8)
            pb.setStyleSheet(f"QProgressBar::chunk {{ background:{'#7bbf3e' if alive else '#e05050'}; border-radius:3px; }}")
            cl.addWidget(pb)
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
        self._show_invites()
        self._root.addStretch()

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

        jg = QGroupBox("🤝 Gabung Guild (masukkan ID)")
        jl = QVBoxLayout(jg)
        sp = QSpinBox()
        sp.setRange(1, 99999)
        sp.setMinimumHeight(42)
        jl.addWidget(sp)
        def _join():
            r = db.join_guild(self.user_id, sp.value())
            if r["ok"]:
                SND.notify()
                _show(self, "Berhasil", r["msg"], "success")
                AppState.refresh()
            else:
                SND.error()
                _show(self, "Gagal", r["msg"], "error")
        jl.addWidget(_btn("🤝 Gabung", "solid", _join, 40))
        self._root.addWidget(jg)
        self._root.addStretch()

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
            _show(self, "HP Habis!", "HP kamu 0! Tidak bisa menyerang.\nGunakan Golden Apple atau skill Healer.", "error")
            return
        r = db.attack_boss(self.user_id, u.get("guild_id"), 25)
        if not r.get("ok"):
            SND.error()
            _show(self, "Tidak Bisa Menyerang", r["msg"], "error")
            return
        if r.get("defeated"):
            SND.boss_dead()
            _show(self, "VICTORY! 🏆", r["msg"], "success")
        else:
            SND.boss_hit()
            u2  = AppState.user()
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

    def _leave(self):
        r = db.leave_guild(self.user_id)
        SND.click()
        _show(self, "Guild", r["msg"])
        AppState.refresh()

    def closeEvent(self, e):
        AppState.unregister(self.load)
        super().closeEvent(e)

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

        s = db.get_stats(self.user_id)
        u = s["user"]
        inner = QWidget()
        il    = QVBoxLayout(inner)
        il.setSpacing(12)
        il.setContentsMargins(0, 0, 0, 0)

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
        ]
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
                pb.setValue(xp)
                pb.setToolTip(f"📅 {row['day']}\n⭐ {xp} XP / 🪙 {row['gold']} Gold")
                pb.setFormat(f" {xp} XP")
                pb.setFixedHeight(22)
                rl.addWidget(pb, 1)
                wl.addLayout(rl)
            il.addWidget(wg)

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
        el.addWidget(_lbl("Nama Display", size=12))
        el.addWidget(self._dn)
        el.addWidget(_lbl("Bio", size=12))
        el.addWidget(self._bio)
        el.addWidget(_btn("💾 Simpan Profil", "solid", self._save_profile, 40))
        il.addWidget(eg)

        # ── Class picker ──────────────────────────────────────────────────────
        cg = QGroupBox("🎮 Pilih Class  (langsung aktif)")
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
        colg = QGroupBox("🎨 Warna Avatar  (langsung aktif)")
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
        emg = QGroupBox("😀 Emoji Avatar  (langsung aktif)")
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
#  LOGIN WINDOW  (complex & user-friendly — no fade_in on self)
# ══════════════════════════════════════════════════════════════════════════════
class LoginWindow(QDialog):
    logged_in = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("⛏ CraftLife — Selamat Datang")
        self.setFixedSize(500, 620)
        self.setStyleSheet(build_ss())
        self._build()
        # ⚠ Do NOT call fade_in(self) here — would make window black

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

        ok = _btn("⚔️  Masuk ke Dunia", "solid", self._do_login, 48)
        for w_ in [self._l_user, self._l_pass, ok, self._l_msg]:
            lay.addWidget(w_)
        lay.addStretch()

        self._l_pass.returnPressed.connect(self._do_login)
        self._l_user.returnPressed.connect(self._l_pass.setFocus)
        return w

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
        r = db.login_user(self._l_user.text(), self._l_pass.text())
        if r["ok"]:
            SND.complete()
            self.logged_in.emit(r["user"])
            self.accept()
        else:
            SND.error()
            self._l_msg.setText(r["msg"])

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
            self._r_class.currentData())
        if r["ok"]:
            SND.level_up()
            self._r_msg.setStyleSheet(f"color:{_T('light')};")
            self._r_msg.setText("✅ " + r["msg"] + "\nSilakan login sekarang!")
        else:
            SND.error()
            self._r_msg.setStyleSheet("color:#e05050;")
            self._r_msg.setText(r["msg"])


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self, user: dict):
        super().__init__()
        AppState.set_user(user["id"])
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
            "habits":   TaskPage(uid, "habit"),
            "dailies":  TaskPage(uid, "daily"),
            "todos":    TaskPage(uid, "todo"),
            "shop":     ShopPage(uid),
            "pets":     PetsPage(uid),
            "guild":    GuildPage(uid),
            "stats":    StatsPage(uid),
            "profile":  ProfilePage(uid),
            "settings": SettingsPage(uid),
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
        # Reload data when switching to a tab
        if hasattr(page, "load"):
            page.load()
        # Gentle fade on inner content (not on page widget itself)
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
    app.setStyleSheet(build_ss())   # default Overworld theme

    _main_win = [None]             # keep reference alive

    login = LoginWindow()

    def on_login(user: dict):
        AppState.set_user(user["id"])
        # Update stylesheet with user's saved theme
        th = db.get_user_theme(user["id"])
        apply_theme(th)
        app.setStyleSheet(build_ss())

        w = MainWindow(user)
        _main_win[0] = w
        w.show()

    login.logged_in.connect(on_login)

    result = login.exec()
    if result == QDialog.DialogCode.Accepted:
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()