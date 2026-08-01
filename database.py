"""
CraftLife — database.py  v1.0
Works as PyInstaller .exe (Desktop)
"""

# ══════════════════════════════════════════════════════════════════════════════
# STRUKTUR FILE  (Table of Contents) — database.py
# ══════════════════════════════════════════════════════════════════════════════
# 1.  KONEKSI & MIGRASI DB : get_conn (pooled), init_db, _safe_alter, migrate_*
# 2.  AUTH & USER          : register_user, login_user, change_password, get_user,
#                            update_user, set_avatar, delete_account
# 3.  XP / GOLD / HP/SKILL : gain_xp_gold, lose_hp, penalize_*, recalculate_all_buffs,
#                            use_class_skill, apply_skill_effect
# 4.  TASKS                : habits, dailies, todos (CRUD + complete + folders + reorder)
# 5.  SPORT                : sport_activities (CRUD + complete + sport points)
# 6.  ECONOMY              : economy_items, debts, savings, investments, subscriptions
# 7.  SHOP / PETS          : SHOP_ITEMS, PETS_DATA, buy/use/sell, adopt/feed/train pet
# 8.  GUILD & BOSS         : create_guild, guild_members, BOSSES, start/attack_boss
# 9.  ACHIEVEMENTS         : check_achievements, claim, ACHIEVEMENTS_REBALANCED
# 10. HEALTH / FOOD        : food_logs, nutrition goals, water, health_logs, recipes
# 11. NOTES / REMINDERS    : notes (nested folders), reminders (repeat), calendar_notes
# 12. MUSIC / PLAYLIST     : playlists CRUD, song move/copy
# 13. LOCK PROFILE         : lock_account, unlock_account, is_account_locked
# 14. RANK                 : calculate_rank
# 15. THEME & SETTINGS     : THEMES (7 tema), get/set_user_theme, language, currency
# 16. BACKUP & CHECKPOINT  : force_checkpoint, backup_database, periodic checkpoint
# ══════════════════════════════════════════════════════════════════════════════

from food_data import DEFAULT_FOODS, get_food_name

import functools
import hashlib
import os
import sqlite3
import sys
import time
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
except ImportError:
    QApplication = None

# ========== TERJEMAHAN UNTUK DATABASE ==========
def tr_db(user_id=None, key=None, lang=None, **kwargs):
    """Ambil terjemahan untuk user tertentu berdasarkan bahasa di database."""
    if user_id is not None:
        try:
            conn = get_conn()
            row = conn.execute("SELECT language FROM users WHERE id=?", (user_id,)).fetchone()
            conn.close()
            lang = row["language"] if row and row["language"] else "id"
        except:
            lang = "id"
    elif lang is None:
        lang = "id"  # default
    
    from translations import get_text
    text = get_text(key, lang)
    if kwargs:
        return text.format(**kwargs)
    return text

def log_crash(error_msg):
    """Catat error ke file crash.log di folder yang sama dengan database."""
    log_path = os.path.join(os.path.dirname(DB_PATH), "crash.log")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - ERROR: {error_msg}\n")
        traceback.print_exc(file=f)
        f.write("\n")

def retry_on_lock(func):
    """Coba ulang jika database locked (maks 3 kali)"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "database is locked" in str(e) and attempt < 2:
                    time.sleep(0.2 * (attempt + 1))
                    continue
                raise
        return func(*args, **kwargs)
    return wrapper

def local_now():
    try:
        import tzlocal
        tz = tzlocal.get_localzone()
        return datetime.now(tz)
    except ImportError:
        # fallback ke waktu lokal sistem
        return datetime.now()

# ── Path auto-detect (VSCode + .exe) ─────────────────────────────────────────

def log_db_error(e, query=""):
    with open("db_error.log", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} - Error: {e}\nQuery: {query}\n\n")

def get_db_path():
    if getattr(sys, 'frozen', False):
        # Jika dijalankan sebagai .exe, simpan DB di %APPDATA%\CraftLife
        appdata = os.getenv('APPDATA')
        if not appdata:
            appdata = os.path.expanduser('~')
        app_dir = Path(appdata) / 'CraftLife'
        app_dir.mkdir(parents=True, exist_ok=True)
        return str(app_dir / 'craftlife.db')
    else:
        # Jika dijalankan sebagai skrip Python biasa, simpan di folder yang sama dengan skrip
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'craftlife.db')

DB_PATH = get_db_path()

import threading as _db_threading
_db_conn_local = _db_threading.local()

class _PooledConnection:
    """Wrapper koneksi: .close() jadi no-op supaya koneksi bisa di-reuse
    (connection pooling) -> jauh lebih cepat & bebas 'database is locked'.
    Akses lain didelegasikan ke koneksi asli."""
    def __init__(self, conn):
        object.__setattr__(self, "_conn", conn)
    def close(self):
        pass  # no-op: jangan benar-benar tutup
    def __getattr__(self, name):
        return getattr(object.__getattribute__(self, "_conn"), name)
    def __setattr__(self, name, value):
        if name == "_conn":
            object.__setattr__(self, name, value)
        else:
            setattr(object.__getattribute__(self, "_conn"), name, value)

def get_conn():
    """Koneksi DB yang di-reuse per thread (pooled). .close() adalah no-op."""
    c = getattr(_db_conn_local, "conn", None)
    if c is None:
        real = sqlite3.connect(DB_PATH, timeout=60.0, check_same_thread=False, cached_statements=256)
        real.row_factory = sqlite3.Row
        real.execute("PRAGMA foreign_keys = ON")
        real.execute("PRAGMA journal_mode = WAL")
        real.execute("PRAGMA busy_timeout = 60000")
        real.execute("PRAGMA synchronous = NORMAL")
        real.execute("PRAGMA cache_size = -20000")
        real.execute("PRAGMA wal_autocheckpoint = 0")
        c = _PooledConnection(real)
        _db_conn_local.conn = c
    return c

def _safe_alter(cur, table, col, defn):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}") 
    except Exception:
        pass
    
def update_guild(guild_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE guilds SET {fields} WHERE id=?", list(kwargs.values()) + [guild_id])
    conn.commit()
    conn.close()

def get_leaderboard(limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT username, display_name, level, total_xp_earned, gold,
               COALESCE(sport_level, 1) as sport_level,
               (SELECT COUNT(*) FROM user_pets WHERE user_id=users.id) as pet_count,
               COALESCE(rebirth_count, 0) as rebirth_count
        FROM users
        WHERE is_admin = 0
        ORDER BY level DESC, total_xp_earned DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def migrate_sort_order():
    """Isi sort_order untuk data yang sudah ada berdasarkan created_at."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = get_conn()
            tables = ["habits", "dailies", "todos", "sport_activities", "economy_items"]
            for table in tables:
                users = conn.execute(f"SELECT DISTINCT user_id FROM {table}").fetchall()
                for u in users:
                    uid = u["user_id"]
                    rows = conn.execute(f"""
                        SELECT id, folder_id, created_at FROM {table}
                        WHERE user_id = ?
                        ORDER BY COALESCE(folder_id, -1), created_at
                    """, (uid,)).fetchall()
                    current_folder = None
                    order = 0
                    for row in rows:
                        if row["folder_id"] != current_folder:
                            current_folder = row["folder_id"]
                            order = 0
                        order += 1
                        conn.execute(
                            f"UPDATE {table} SET sort_order = ? WHERE id = ?",
                            (order, row["id"])
                        )
            conn.commit()
            conn.close()
            return  # sukses
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
                continue
            else:
                raise
    conn.close()

def init_db():
    conn = get_conn()
    c = conn.cursor()

    # ========== SCHEMA MIGRATION (selalu dijalankan) ==========
    # Matikan foreign key sementara agar migrasi aman
    c.execute("PRAGMA foreign_keys = OFF")

    # --- Buat semua tabel dengan struktur baru (IF NOT EXISTS) ---
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT DEFAULT '',
        bio TEXT DEFAULT '',
        avatar_class TEXT DEFAULT 'warrior',
        avatar_color TEXT DEFAULT '#5a8a2e',
        avatar_emoji TEXT DEFAULT '⚔️',
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        hp INTEGER DEFAULT 50,
        max_hp INTEGER DEFAULT 50,
        mp INTEGER DEFAULT 30,
        max_mp INTEGER DEFAULT 30,
        gold REAL DEFAULT 0,
        gems INTEGER DEFAULT 10,
        longest_streak INTEGER DEFAULT 0,
        total_habits_done INTEGER DEFAULT 0,
        total_dailies_done INTEGER DEFAULT 0,
        total_todos_done INTEGER DEFAULT 0,
        total_xp_earned INTEGER DEFAULT 0,
        total_gold_earned REAL DEFAULT 0,
        boss_damage_bonus REAL DEFAULT 0,
        xp_multiplier REAL DEFAULT 1.0,
        gold_multiplier REAL DEFAULT 1.0,
        hp_damage_reduction REAL DEFAULT 0,
        has_revive INTEGER DEFAULT 0,
        mp_bonus INTEGER DEFAULT 0,
        guild_id INTEGER,
        last_login TEXT,
        theme TEXT DEFAULT 'modern_dark', 
        sound_enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT(datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guilds(
        id INTEGER PRIMARY KEY,   -- tanpa AUTOINCREMENT
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        leader_id INTEGER,
        quest_id TEXT,
        created_at TEXT DEFAULT(datetime('now')),
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        buff_xp REAL DEFAULT 0,
        buff_gold REAL DEFAULT 0,
        buff_damage REAL DEFAULT 0
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        joined_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(guild_id) REFERENCES guilds(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS habits(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '⚔️',
        difficulty TEXT DEFAULT 'medium',
        xp_reward INTEGER DEFAULT 25,
        gold_reward REAL DEFAULT 5,
        positive INTEGER DEFAULT 1,
        negative INTEGER DEFAULT 0,
        counter_up INTEGER DEFAULT 0,
        counter_down INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        done_today INTEGER DEFAULT 0,
        last_done TEXT,
        notes TEXT DEFAULT '',
        last_action TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS dailies(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📅',
        difficulty TEXT DEFAULT 'medium',
        xp_reward INTEGER DEFAULT 30,
        gold_reward REAL DEFAULT 6,
        streak INTEGER DEFAULT 0,
        done_today INTEGER DEFAULT 0,
        last_done TEXT,
        notes TEXT DEFAULT '',
        last_action TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS todos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📜',
        priority TEXT DEFAULT 'medium',
        xp_reward INTEGER DEFAULT 40,
        gold_reward REAL DEFAULT 8,
        done INTEGER DEFAULT 0,
        due_date TEXT,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS economy_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '💰',
        type TEXT NOT NULL,      -- 'income' atau 'expense'
        amount REAL NOT NULL,
        category TEXT DEFAULT 'other',
        date TEXT NOT NULL,      -- format YYYY-MM-DD
        notes TEXT DEFAULT '',
        folder_id INTEGER,
        created_at TEXT DEFAULT(datetime('now')),
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS inventory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        item_id TEXT NOT NULL,
        item_type TEXT NOT NULL,
        quantity INTEGER DEFAULT 1,
        equipped INTEGER DEFAULT 0,
        obtained_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_pets(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        pet_id TEXT NOT NULL,
        is_active INTEGER DEFAULT 0,
        happiness INTEGER DEFAULT 50,
        level INTEGER DEFAULT 1,
        exp INTEGER DEFAULT 0,
        hunger INTEGER DEFAULT 100,
        last_fed TEXT,
        adopted_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS boss_battles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        boss_id TEXT NOT NULL,
        boss_name TEXT NOT NULL,
        boss_icon TEXT DEFAULT '🐉',
        boss_tier TEXT DEFAULT 'normal',
        boss_hp REAL DEFAULT 100,
        boss_max_hp REAL DEFAULT 100,
        boss_attack REAL DEFAULT 5,
        status TEXT DEFAULT 'active',
        started_at TEXT DEFAULT(datetime('now')),
        ended_at TEXT,
        FOREIGN KEY(guild_id) REFERENCES guilds(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS boss_rewards(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        guild_id INTEGER NOT NULL,
        boss_name TEXT NOT NULL,
        boss_tier TEXT DEFAULT 'normal',
        xp_reward INTEGER DEFAULT 0,
        gold_reward REAL DEFAULT 0,
        is_claimed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(guild_id) REFERENCES guilds(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS debts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        amount REAL NOT NULL,
        due_date TEXT,
        is_paid INTEGER DEFAULT 0,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        paid_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS activity_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        detail TEXT,
        xp_gained INTEGER DEFAULT 0,
        gold_gained REAL DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notifications(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'info',
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_invites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(guild_id) REFERENCES guilds(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(guild_id) REFERENCES guilds(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS friends(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        friend_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        action_user_id INTEGER,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(friend_id) REFERENCES users(id),
        UNIQUE(user_id, friend_id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_leader_transfers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        old_leader_id INTEGER NOT NULL,
        created_at TEXT DEFAULT(datetime('now')),
        status TEXT DEFAULT 'pending'
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(sender_id) REFERENCES users(id),
        FOREIGN KEY(receiver_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS guild_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(guild_id) REFERENCES guilds(id),
        FOREIGN KEY(sender_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS backup_codes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        code_hash TEXT NOT NULL,
        is_used INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sport_activities(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        sport_type TEXT DEFAULT 'running',
        icon TEXT DEFAULT '🏃',
        difficulty TEXT DEFAULT 'medium',
        xp_reward INTEGER DEFAULT 25,
        gold_reward REAL DEFAULT 5,
        sport_points_reward INTEGER DEFAULT 15,
        done_today INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_done TEXT,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS food_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '🍎',
        calories REAL DEFAULT 0,
        protein REAL DEFAULT 0,
        carbs REAL DEFAULT 0,
        fat REAL DEFAULT 0,
        is_custom INTEGER DEFAULT 0,
        user_id INTEGER,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS food_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        food_id INTEGER NOT NULL,
        serving REAL DEFAULT 1.0,
        calories REAL DEFAULT 0,
        protein REAL DEFAULT 0,
        carbs REAL DEFAULT 0,
        fat REAL DEFAULT 0,
        meal_type TEXT DEFAULT 'snack',  -- breakfast, lunch, dinner, snack
        log_date TEXT NOT NULL,  -- YYYY-MM-DD
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(food_id) REFERENCES food_items(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_nutrition_goals(
        user_id INTEGER PRIMARY KEY,
        daily_calories INTEGER DEFAULT 2000,
        daily_protein INTEGER DEFAULT 50,
        daily_carbs INTEGER DEFAULT 250,
        daily_fat INTEGER DEFAULT 70,
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS food_achievements(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        achievement_date TEXT NOT NULL,  -- YYYY-MM-DD
        bonus_claimed INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, achievement_date)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS water_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount_ml INTEGER DEFAULT 0,
        log_date TEXT NOT NULL,  -- YYYY-MM-DD
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_water_goals(
        user_id INTEGER PRIMARY KEY,
        daily_ml INTEGER DEFAULT 2000,
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS user_health_goals(
        user_id INTEGER PRIMARY KEY,
        daily_steps INTEGER DEFAULT 10000,
        daily_sleep_hours REAL DEFAULT 7.0,
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS recipes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '🍲',
        serving_size REAL DEFAULT 1,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS recipe_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe_id INTEGER NOT NULL,
        food_id INTEGER NOT NULL,
        quantity REAL DEFAULT 1,
        FOREIGN KEY(recipe_id) REFERENCES recipes(id) ON DELETE CASCADE,
        FOREIGN KEY(food_id) REFERENCES food_items(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS savings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '🏦',
        target_amount REAL DEFAULT 0,
        current_amount REAL DEFAULT 0,
        target_date TEXT,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT(datetime('now')),
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""
        CREATE TABLE IF NOT EXISTS health_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            steps INTEGER DEFAULT 0,
            sleep_hours REAL DEFAULT 0,
            water_ml INTEGER DEFAULT 0,
            weight_kg REAL DEFAULT 0,
            resting_hr INTEGER DEFAULT 0,
            stress_level TEXT DEFAULT 'normal',
            mood TEXT DEFAULT 'normal',
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT(datetime('now')),
            net_calories REAL DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, log_date)
        )
    """)   

    c.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            icon TEXT DEFAULT '🏆',
            category TEXT NOT NULL,
            requirement_type TEXT NOT NULL,
            requirement_value INTEGER NOT NULL,
            xp_reward INTEGER DEFAULT 0,
            gold_reward REAL DEFAULT 0,
            is_hidden INTEGER DEFAULT 0
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            user_id INTEGER NOT NULL,
            achievement_id INTEGER NOT NULL,
            progress INTEGER DEFAULT 0,
            unlocked_at TEXT,
            claimed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(achievement_id) REFERENCES achievements(id) ON DELETE CASCADE,
            PRIMARY KEY(user_id, achievement_id)
        )
    """)

    c.execute("""CREATE TABLE IF NOT EXISTS investments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📈',
        amount REAL DEFAULT 0,
        invested_date TEXT DEFAULT(datetime('now')),
        last_update TEXT DEFAULT(datetime('now')),
        target_return REAL DEFAULT 0,
        notes TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS subscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📅',
        amount REAL DEFAULT 0,
        due_date TEXT NOT NULL,
        period TEXT DEFAULT 'monthly',
        is_recurring INTEGER DEFAULT 1,
        last_charged TEXT,
        notes TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS redeem_codes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        reward_type TEXT NOT NULL,   -- 'admin', 'xp', 'gold', 'item', etc.
        reward_value INTEGER DEFAULT 0,
        reward_item TEXT,            -- untuk item
        is_one_time INTEGER DEFAULT 1,
        used_by INTEGER,             -- user_id yang memakai (jika one-time)
        used_at TEXT,
        created_at TEXT DEFAULT(datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS task_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        task_type TEXT NOT NULL,
        task_id INTEGER NOT NULL,
        action_date TEXT NOT NULL,
        action TEXT NOT NULL,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")
    c.execute("CREATE INDEX IF NOT EXISTS idx_task_history_user_task_date ON task_history(user_id, task_type, task_id, action_date)")

    c.execute("""CREATE TABLE IF NOT EXISTS note_folders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📁',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        folder_id INTEGER,
        title TEXT NOT NULL,
        content TEXT DEFAULT '',
        is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(folder_id) REFERENCES note_folders(id) ON DELETE SET NULL
    )""")

    # ========== REMINDERS ==========
    c.execute("""CREATE TABLE IF NOT EXISTS reminders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        reminder_datetime TEXT NOT NULL,
        sound_type TEXT DEFAULT 'default',
        sound_file TEXT,
        is_active INTEGER DEFAULT 1,
        triggered INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    c.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user_datetime ON reminders(user_id, reminder_datetime)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_reminders_active ON reminders(user_id, is_active, triggered)")

    # ========== CALENDAR NOTES ==========
    c.execute("""CREATE TABLE IF NOT EXISTS calendar_notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        note_date TEXT NOT NULL,  -- YYYY-MM-DD
        note TEXT NOT NULL,
        created_at TEXT DEFAULT(datetime('now')),
        updated_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        UNIQUE(user_id, note_date)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS playlists(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        tracks TEXT NOT NULL DEFAULT '[]',
        is_favorite INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # ========== MIGRASI PLAYLISTS KE SKEMA BARU ==========
    c.execute("PRAGMA table_info(playlists)")
    cols = [row[1] for row in c.fetchall()]
    
    if 'tracks' not in cols:
        print("[DB] Migrasi playlists ke skema baru...")
        
        # 1. Buat tabel baru dengan skema yang benar
        c.execute("""
            CREATE TABLE IF NOT EXISTS playlists_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                tracks TEXT NOT NULL DEFAULT '[]',
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT(datetime('now'))
            )
        """)
        
        # 2. Copy data dari tabel lama
        if 'files' in cols:
            # Ada kolom files, ambil datanya
            c.execute("""
                INSERT INTO playlists_new (id, user_id, name, tracks, is_favorite, created_at)
                SELECT id, user_id, name, files, is_favorite, created_at FROM playlists
            """)
        else:
            # Tidak ada files, gunakan tracks kosong
            c.execute("""
                INSERT INTO playlists_new (id, user_id, name, tracks, is_favorite, created_at)
                SELECT id, user_id, name, '[]', is_favorite, created_at FROM playlists
            """)
        
        # 3. Hapus tabel lama dan rename tabel baru
        c.execute("DROP TABLE playlists")
        c.execute("ALTER TABLE playlists_new RENAME TO playlists")
        print("[DB] Migrasi playlists selesai.")

    # ========== HAPUS KOLOM 'files' LAMA JIKA MASIH ADA ==========
    c.execute("PRAGMA table_info(playlists)")
    cols = [row[1] for row in c.fetchall()]
    if 'files' in cols:
        print("[DB] Menghapus kolom 'files' usang dari playlists...")
        # Buat tabel baru tanpa kolom files
        c.execute("""
            CREATE TABLE IF NOT EXISTS playlists_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                tracks TEXT NOT NULL DEFAULT '[]',
                is_favorite INTEGER DEFAULT 0,
                created_at TEXT DEFAULT(datetime('now'))
            )
        """)
        # Salin data dari tabel lama, abaikan kolom files
        c.execute("""
            INSERT INTO playlists_new (id, user_id, name, tracks, is_favorite, created_at)
            SELECT id, user_id, name, tracks, is_favorite, created_at FROM playlists
        """)
        c.execute("DROP TABLE playlists")
        c.execute("ALTER TABLE playlists_new RENAME TO playlists")
        print("[DB] Kolom 'files' berhasil dihapus.")

    # --- MIGRASI: Perbaiki tabel boss_battles jika masih pakai party_id ---
    try:
        c.execute("PRAGMA table_info(boss_battles)")
        columns = [row[1] for row in c.fetchall()]
        if 'party_id' in columns:
            print("Migrasi boss_battles: party_id -> guild_id")
            c.execute("""CREATE TABLE boss_battles_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                boss_id TEXT NOT NULL,
                boss_name TEXT NOT NULL,
                boss_icon TEXT DEFAULT '🐉',
                boss_tier TEXT DEFAULT 'normal',
                boss_hp REAL DEFAULT 100,
                boss_max_hp REAL DEFAULT 100,
                boss_attack REAL DEFAULT 5,
                status TEXT DEFAULT 'active',
                started_at TEXT DEFAULT(datetime('now')),
                ended_at TEXT
            )""")
            c.execute("""INSERT INTO boss_battles_new
                (id, guild_id, boss_id, boss_name, boss_icon, boss_tier, boss_hp, boss_max_hp, boss_attack, status, started_at, ended_at)
                SELECT id, party_id, boss_id, boss_name, boss_icon, boss_tier, boss_hp, boss_max_hp, boss_attack, status, started_at, ended_at
                FROM boss_battles""")
            c.execute("DROP TABLE boss_battles")
            c.execute("ALTER TABLE boss_battles_new RENAME TO boss_battles")
            print("Migrasi boss_battles selesai.")
    except Exception as e:
        print(f"Migrasi boss_battles gagal (bisa diabaikan jika tidak perlu): {e}")
        log_crash(f"Migrasi boss_battles gagal: {e}")

    # --- Safe migration untuk kolom tambahan (schema) ---
    migrate_cols = [
        ("bio","TEXT DEFAULT ''"),
        ("avatar_emoji","TEXT DEFAULT '⚔️'"),
        ("gems","INTEGER DEFAULT 10"),
        ("longest_streak","INTEGER DEFAULT 0"),
        ("total_habits_done","INTEGER DEFAULT 0"),
        ("total_dailies_done","INTEGER DEFAULT 0"),
        ("total_todos_done","INTEGER DEFAULT 0"),
        ("total_xp_earned","INTEGER DEFAULT 0"),
        ("total_gold_earned","REAL DEFAULT 0"),
        ("boss_damage_bonus","REAL DEFAULT 0"),
        ("xp_multiplier","REAL DEFAULT 1.0"),
        ("gold_multiplier","REAL DEFAULT 1.0"),
        ("hp_damage_reduction","REAL DEFAULT 0"),
        ("has_revive","INTEGER DEFAULT 0"),
        ("mp_bonus","INTEGER DEFAULT 0"),
        ("theme","TEXT DEFAULT 'modern_dark'"),
        ("sound_enabled","INTEGER DEFAULT 1"),
        ("last_class_change", "TEXT"),
        ("reset_code", "TEXT"),
        ("reset_expiry", "TEXT"),
        ("sport_level", "INTEGER DEFAULT 1"),
        ("sport_xp", "INTEGER DEFAULT 0"),
        ("total_sport_points_earned", "INTEGER DEFAULT 0"),
        ("skill_buff_data", "TEXT DEFAULT '{}'"),
        ("class_passive_buffs", "TEXT DEFAULT '{}'"),
        ("is_admin", "INTEGER DEFAULT 0"),
        ("language", "TEXT DEFAULT 'en'")
    ]

    for col, defn in migrate_cols:
        _safe_alter(c, "users", col, defn)

    # Migrasi kolom untuk tabel lain
    _safe_alter(c, "habits", "last_action", "TEXT DEFAULT ''")
    _safe_alter(c, "dailies", "last_action", "TEXT DEFAULT ''")
    _safe_alter(c, "users", "security_question", "TEXT")
    _safe_alter(c, "users", "security_answer_hash", "TEXT")
    _safe_alter(c, "sport_activities", "calories_burned", "INTEGER DEFAULT 0")
    _safe_alter(c, "sport_activities", "duration_minutes", "INTEGER DEFAULT 30")
    _safe_alter(c, "habits", "folder_id", "INTEGER")
    _safe_alter(c, "dailies", "folder_id", "INTEGER")
    _safe_alter(c, "todos", "folder_id", "INTEGER")
    _safe_alter(c, "sport_activities", "folder_id", "INTEGER")
    _safe_alter(c, "economy_items", "folder_id", "INTEGER")
    _safe_alter(c, "debts", "penalty_applied", "INTEGER DEFAULT 0")
    _safe_alter(c, "debts", "penalty_amount", "INTEGER DEFAULT 0")
    _safe_alter(c, "debts", "name", "TEXT NOT NULL")
    _safe_alter(c, 'health_logs', 'water_ml', 'INTEGER DEFAULT 0')
    _safe_alter(c, 'health_logs', 'weight_kg', 'REAL DEFAULT 0')
    _safe_alter(c, 'health_logs', 'resting_hr', 'INTEGER DEFAULT 0')
    _safe_alter(c, 'health_logs', 'stress_level', "TEXT DEFAULT 'normal'")
    _safe_alter(c, "users", "total_tasks_completed", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "total_gold_spent", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "currency", "TEXT DEFAULT 'IDR'")
    _safe_alter(c, "health_logs", "net_calories", "REAL DEFAULT 0")
    _safe_alter(c, "user_health_goals", "height_cm", "INTEGER DEFAULT 170")
    _safe_alter(c, "user_health_goals", "weight_kg", "REAL DEFAULT 70")
    _safe_alter(c, "user_health_goals", "age", "INTEGER DEFAULT 25")
    _safe_alter(c, "user_health_goals", "gender", "TEXT DEFAULT 'Laki-laki'")
    _safe_alter(c, "user_health_goals", "activity_factor", "REAL DEFAULT 1.55")
    _safe_alter(c, "users", "is_admin", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "rebirth_count", "INTEGER DEFAULT 0")
    _safe_alter(c, "economy_items", "sort_order", "INTEGER DEFAULT 0")
    _safe_alter(c, "food_logs", "sort_order", "INTEGER DEFAULT 0")
    _safe_alter(c, "dailies", "fail_streak", "INTEGER DEFAULT 0")
    _safe_alter(c, "messages", "deleted_by", "TEXT DEFAULT ''")
    _safe_alter(c, "note_folders", "parent_id", "INTEGER DEFAULT NULL")
    _safe_alter(c, "reminders", "repeat_type", "TEXT DEFAULT 'none'")
    _safe_alter(c, "reminders", "repeat_days", "TEXT DEFAULT ''")
    _safe_alter(c, "users", "has_spyglass", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "crit_chance", "INTEGER DEFAULT 10")
    _safe_alter(c, "guilds", "crit_chance", "INTEGER DEFAULT 0")
    _safe_alter(c, "boss_battles", "boss_crit_chance", "INTEGER DEFAULT 15")
    _safe_alter(c, "users", "block_chance", "INTEGER DEFAULT 20")
    _safe_alter(c, "users", "block_strength", "INTEGER DEFAULT 10")
    _safe_alter(c, "users", "ultimate_last_used", "TEXT")
    _safe_alter(c, "users", "boss_attacks_today", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "boss_attacks_date", "TEXT")
    _safe_alter(c, "boss_battles", "participants", "TEXT")
    _safe_alter(c, "boss_battles", "attack_counts", "TEXT")
    _safe_alter(c, "boss_battles", "raid_leader_id", "INTEGER")
    _safe_alter(c, "guilds", "boss_defeated_today", "INTEGER DEFAULT 0")
    _safe_alter(c, "guilds", "boss_defeated_date", "TEXT")
    _safe_alter(c, "dailies", "freeze_slots", "INTEGER DEFAULT 0")
    _safe_alter(c, "playlists", "is_favorite", "INTEGER DEFAULT 0")
    _safe_alter(c, "playlists", "tracks", "TEXT NOT NULL DEFAULT '[]'")
    _safe_alter(c, "notes", "zoom_level", "INTEGER DEFAULT 100")
    _safe_alter(c, "users", "is_locked", "INTEGER DEFAULT 0")
    _safe_alter(c, "users", "locked_at", "TEXT")
    _safe_alter(c, "users", "last_tracking_date", "TEXT")

    for col, defn in [("level", "INTEGER DEFAULT 1"),
                      ("exp", "INTEGER DEFAULT 0"),
                      ("buff_xp", "REAL DEFAULT 0"),
                      ("buff_gold", "REAL DEFAULT 0"),
                      ("buff_damage", "REAL DEFAULT 0")]:
        try: c.execute(f"ALTER TABLE guilds ADD COLUMN {col} {defn}")
        except: pass

    for col, defn in [("level", "INTEGER DEFAULT 1"),
                      ("exp", "INTEGER DEFAULT 0"),
                      ("hunger", "INTEGER DEFAULT 100"),
                      ("last_fed", "TEXT")]:
        try: c.execute(f"ALTER TABLE user_pets ADD COLUMN {col} {defn}")
        except: pass

    # Tambahkan sort_order untuk drag & drop reorder
    for table in ["habits", "dailies", "todos", "sport_activities"]:
        _safe_alter(c, table, "sort_order", "INTEGER DEFAULT 0")

    # ── Task Folders (for organize habits/dailies/todos/sport) ────────────────
    c.execute("""CREATE TABLE IF NOT EXISTS task_folders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        mode TEXT NOT NULL,
        name TEXT NOT NULL,
        icon TEXT DEFAULT '📁',
        collapsed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # ========== DATA MIGRATION (hanya untuk database baru/kosong) ==========
    # CEK: Apakah database sudah memiliki data?
    table_check = c.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
    ).fetchone()
    is_new_db = True
    if table_check:
        user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count > 0:
            is_new_db = False
            print(f"[DB] Database sudah terisi ({user_count} user), skip initial data insertion.")

    # ========== HANYA UNTUK DATABASE BARU ==========
    print("[DB] Database baru, menjalankan migrasi data...")

    # Inisialisasi achievements
    init_achievements()

    # ========== MIGRASI ACHIEVEMENT ==========
    migrate_achievements()

    # ========== MIGRASI REDEEM CODES ==========
    migrate_redeem_codes()

    # Tambah makanan default
    cur = c.execute("SELECT name FROM food_items WHERE is_custom = 0")
    existing_default_names = {row[0] for row in cur.fetchall()}
    new_foods_added = 0
    for food in DEFAULT_FOODS:
        name_id = food[0]   # ambil nama Indonesia
        if name_id not in existing_default_names:
            c.execute(
                "INSERT INTO food_items(name, icon, calories, protein, carbs, fat, is_custom) "
                "VALUES(?,?,?,?,?,?,?)",
                (name_id, food[2], food[3], food[4], food[5], food[6], 0)
            )
            new_foods_added += 1
    if new_foods_added > 0:
        print(f"[DB] Menambahkan {new_foods_added} makanan default baru.")
    else:
        print("[DB] Tidak ada makanan default baru, skip.")

    # Insert default redeem codes
    cur = c.execute("SELECT COUNT(*) FROM redeem_codes")
    if cur.fetchone()[0] == 0:
        default_codes = [
            ("ADMINADMINADMIN", "admin", 0, None, 1),
            ("WELCOME100", "xp", 100, None, 1),
            ("STARTGOLD", "gold", 500, None, 1),
            ("WOODSWORD", "item", 0, "wooden_sword", 1),
            ("GOLDENAPPLE", "item", 0, "golden_apple", 1),
        ]
        for code, rtype, rval, ritem, onetime in default_codes:
            try:
                c.execute(
                    "INSERT INTO redeem_codes(code, reward_type, reward_value, reward_item, is_one_time) VALUES(?,?,?,?,?)",
                    (code, rtype, rval, ritem, onetime)
                )
            except:
                pass

    # ── OPTIMASI: Buat indeks untuk mempercepat query ─────────────────────────
    c.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_user_id ON activity_log(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_food_logs_user_log ON food_logs(user_id, log_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_food_logs_user_id ON food_logs(user_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_health_logs_user_log ON health_logs(user_id, log_date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_health_logs_user_id ON health_logs(user_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_water_logs_user_log ON water_logs(user_id, log_date)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_sport_activities_user_done ON sport_activities(user_id, done_today, last_done)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sport_activities_user_id ON sport_activities(user_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_economy_items_user_date ON economy_items(user_id, date)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_economy_items_user_type ON economy_items(user_id, type)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_habits_user_id ON habits(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dailies_user_id ON dailies(user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_todos_user_id ON todos(user_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_pets_user_active ON user_pets(user_id, is_active)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_guild_members_guild ON guild_members(guild_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_guild_members_user ON guild_members(user_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_messages_users ON messages(sender_id, receiver_id)")
    
    c.execute("CREATE INDEX IF NOT EXISTS idx_debts_user_paid ON debts(user_id, is_paid)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_habits_sort_order ON habits(user_id, sort_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dailies_sort_order ON dailies(user_id, sort_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_todos_sort_order ON todos(user_id, sort_order)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_sport_activities_sort_order ON sport_activities(user_id, sort_order)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_economy_items_sort_order ON economy_items(user_id, sort_order)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_food_logs_sort_order ON food_logs(user_id, sort_order)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_folder ON notes(user_id, folder_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_notes_user_archived ON notes(user_id, is_archived)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_note_folders_parent ON note_folders(parent_id)")

    c.execute("CREATE INDEX IF NOT EXISTS idx_habits_last_done ON habits(user_id, last_done)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_dailies_last_done ON dailies(user_id, last_done)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_task_history_user_date ON task_history(user_id, task_type, action_date)")

    # Nyalakan kembali foreign key
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print(f"[DB] Ready: {DB_PATH}")

    # Migrasi sort_order
    migrate_sort_order()

# ========== KODE REDEEM BARU ==========
NEW_REDEEM_CODES = [
    ("FREEXP200", "xp", 200, None, 1),
    ("FREEGOLD500", "gold", 500, None, 1),
    ("FREEPOTION", "item", 0, "health_potion", 1),
    ("FREESWORD", "item", 0, "iron_sword", 1),
    ("BIGBONUS", "gold", 1000, None, 1),
]

def migrate_redeem_codes():
    """Tambahkan kode redeem baru jika belum ada."""
    conn = get_conn()
    cur = conn.cursor()
    for code, rtype, rval, ritem, onetime in NEW_REDEEM_CODES:
        existing = cur.execute("SELECT id FROM redeem_codes WHERE code = ?", (code,)).fetchone()
        if not existing:
            try:
                cur.execute(
                    "INSERT INTO redeem_codes(code, reward_type, reward_value, reward_item, is_one_time) VALUES(?,?,?,?,?)",
                    (code, rtype, rval, ritem, onetime)
                )
            except:
                pass
    conn.commit()
    conn.close()
    print(f"[DB] Migrated {len(NEW_REDEEM_CODES)} new redeem codes.")

# ========== KONSTANTA TABEL YANG DI-EKSPOR ==========
EXPORT_TABLES = [
    'task_folders',
    'note_folders',
    'food_items',
    'recipes',
    'habits',
    'dailies',
    'todos',
    'sport_activities',
    'notes',
    'recipe_items',
    'food_logs',
    'economy_items',
    'debts',
    'savings',
    'investments',
    'subscriptions',
    'water_logs',
    'health_logs',
    'calendar_notes',
    'reminders',
]

# ========== EKSPOR ==========
def export_tracker_data(user_id):
    conn = get_conn()
    # Cek admin
    u = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if u and u["is_admin"]:
        conn.close()
        raise PermissionError("Admin tidak diperbolehkan mengekspor data tracker.")
    
    data = {"version": 1, "tables": {}}
    
    for table in EXPORT_TABLES:
        if table == "recipe_items":
            # Ambil recipe_items yang terkait dengan recipes milik user, sertakan food_name
            rows = conn.execute("""
                SELECT ri.*, fi.name as food_name
                FROM recipe_items ri
                JOIN recipes r ON ri.recipe_id = r.id
                JOIN food_items fi ON ri.food_id = fi.id
                WHERE r.user_id = ?
            """, (user_id,)).fetchall()
        elif table == "food_items":
            # Hanya custom food
            rows = conn.execute(
                "SELECT * FROM food_items WHERE user_id=? AND is_custom=1",
                (user_id,)
            ).fetchall()
        elif table == "food_logs":
            # Ambil food_logs beserta nama makanan (untuk mapping default food nanti)
            rows = conn.execute("""
                SELECT fl.*, fi.name as food_name
                FROM food_logs fl
                LEFT JOIN food_items fi ON fl.food_id = fi.id
                WHERE fl.user_id = ?
            """, (user_id,)).fetchall()
        else:
            # Tabel lain yang memiliki kolom user_id
            rows = conn.execute(f"SELECT * FROM {table} WHERE user_id=?", (user_id,)).fetchall()
        
        list_rows = [dict(r) for r in rows]
        # Hapus kolom user_id dari setiap baris (jika ada)
        for row in list_rows:
            row.pop('user_id', None)
        
        data["tables"][table] = list_rows
    
    conn.close()
    return data

# ========== BERSIHKAN DATA TRACKER ==========
def clear_tracker_data(user_id):
    """Hapus semua data tracker user (tanpa menyentuh data akun)."""
    conn = get_conn()
    conn.execute("PRAGMA foreign_keys = OFF")
    
    # 1. Hapus recipe_items terlebih dahulu (tidak punya user_id langsung)
    conn.execute(
        "DELETE FROM recipe_items WHERE recipe_id IN (SELECT id FROM recipes WHERE user_id=?)",
        (user_id,)
    )
    
    # 2. Hapus tabel lain yang memiliki kolom user_id
    for table in EXPORT_TABLES:
        if table == 'recipe_items':
            continue  # sudah dihapus
        conn.execute(f"DELETE FROM {table} WHERE user_id=?", (user_id,))
    
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

# ========== HELPER: DAPATKAN ID DEFAULT FOOD BERDASARKAN NAMA ==========
def get_default_food_id_by_name(name):
    """Cari ID makanan default (is_custom=0) berdasarkan nama."""
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM food_items WHERE is_custom=0 AND name=?",
        (name,)
    ).fetchone()
    conn.close()
    return row["id"] if row else None

# ========== IMPOR ==========
def import_tracker_data(user_id, data):
    """Impor data tracker dari file JSON ke user_id."""
    conn = get_conn()
    # Cek admin
    u = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if u and u["is_admin"]:
        conn.close()
        raise PermissionError("Admin tidak diperbolehkan mengimpor data tracker.")
    
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        # 1. Hapus data lama
        clear_tracker_data(user_id)
        
        # 2. Mapping untuk foreign key
        mapping = {
            'task_folders': {},
            'note_folders': {},
            'food_items': {},      # hanya custom yang di-insert
            'recipes': {},
            'habits': {},
            'dailies': {},
            'todos': {},
            'sport_activities': {},
            'notes': {},
        }
        # Mapping khusus task_history
        task_mapping = {
            'habit': {},
            'daily': {},
            'todo': {},
            'sport': {},
        }
        
        # 3. Insert parent tables (tanpa FK ke tabel lain dalam export)
        parent_tables = ['task_folders', 'note_folders', 'food_items', 'recipes']
        note_folder_parents = {}
        for table in parent_tables:
            rows = data['tables'].get(table, [])
            for row in rows:
                old_parent = row.get('parent_id')  
                insert_row = {k: v for k, v in row.items() if k != 'id'}
                insert_row['user_id'] = user_id
                # Jika ada kolom created_at/updated_at, tetap pakai nilai dari file
                cols = ','.join(insert_row.keys())
                placeholders = ','.join(['?'] * len(insert_row))
                cur = conn.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    list(insert_row.values())
                )
                new_id = cur.lastrowid                 # ← PERBAIKI TYPO
                mapping[table][row['id']] = new_id
                if table == 'note_folders':            # ← HANYA UNTUK note_folders
                    note_folder_parents[row['id']] = old_parent
        
        # Update parent_id untuk note_folders
        for old_id, old_parent in note_folder_parents.items():
            if old_parent is not None and old_parent in mapping['note_folders']:
                new_parent = mapping['note_folders'][old_parent]
                new_id = mapping['note_folders'][old_id]
                conn.execute(
                    "UPDATE note_folders SET parent_id = ? WHERE id = ?",
                    (new_parent, new_id)
                )

        # 4. Insert child tables dengan foreign key
        # 4a. habits, dailies, todos, sport
        for table, fk_table, fk_col in [
            ('habits', 'task_folders', 'folder_id'),
            ('dailies', 'task_folders', 'folder_id'),
            ('todos', 'task_folders', 'folder_id'),
            ('sport_activities', 'task_folders', 'folder_id'),
        ]:
            rows = data['tables'].get(table, [])
            for row in rows:
                insert_row = {k: v for k, v in row.items() if k != 'id'}
                insert_row['user_id'] = user_id

                # ── RESET PROGRES ──
                if table == 'habits':
                    insert_row['streak'] = 0
                    insert_row['done_today'] = 0
                    insert_row['counter_up'] = 0
                    insert_row['counter_down'] = 0
                    insert_row['last_done'] = None
                    insert_row['last_action'] = ''
                elif table == 'dailies':
                    insert_row['streak'] = 0
                    insert_row['done_today'] = 0
                    insert_row['fail_streak'] = 0
                    insert_row['last_done'] = None
                    insert_row['last_action'] = ''
                elif table == 'todos':
                    insert_row['done'] = 0
                elif table == 'sport_activities':
                    insert_row['streak'] = 0
                    insert_row['done_today'] = 0
                    insert_row['last_done'] = None
                    
                # Map folder_id
                old_fid = row.get('folder_id')
                if old_fid is not None and old_fid in mapping['task_folders']:
                    insert_row['folder_id'] = mapping['task_folders'][old_fid]
                else:
                    insert_row['folder_id'] = None
                cols = ','.join(insert_row.keys())
                placeholders = ','.join(['?'] * len(insert_row))
                cur = conn.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    list(insert_row.values())
                )
                new_id = cur.lastrowid
                mapping[table][row['id']] = new_id
                # Simpan di task_mapping
                ttype = 'habit' if table == 'habits' else \
                        'daily' if table == 'dailies' else \
                        'todo' if table == 'todos' else 'sport'
                task_mapping[ttype][row['id']] = new_id
        
        # 4b. notes
        rows = data['tables'].get('notes', [])
        for row in rows:
            old_parent = row.get('parent_id')
            insert_row = {k: v for k, v in row.items() if k != 'id'}
            insert_row['user_id'] = user_id
            old_fid = row.get('folder_id')
            if old_fid is not None and old_fid in mapping['note_folders']:
                insert_row['folder_id'] = mapping['note_folders'][old_fid]
            else:
                insert_row['folder_id'] = None
            cols = ','.join(insert_row.keys())
            placeholders = ','.join(['?'] * len(insert_row))
            cur = conn.execute(
                f"INSERT INTO notes ({cols}) VALUES ({placeholders})",
                list(insert_row.values())
            )
            mapping['notes'][row['id']] = cur.lastrowid
        
        # 4c. recipe_items
        rows = data['tables'].get('recipe_items', [])
        for row in rows:
            insert_row = {k: v for k, v in row.items() if k != 'id'}
            # Map recipe_id
            old_rid = row.get('recipe_id')
            if old_rid in mapping['recipes']:
                insert_row['recipe_id'] = mapping['recipes'][old_rid]
            else:
                continue  # skip jika resep tidak ada (seharusnya tidak terjadi)
            # Map food_id
            old_fid = row.get('food_id')
            if old_fid in mapping['food_items']:
                insert_row['food_id'] = mapping['food_items'][old_fid]
            else:
                # Cari default food berdasarkan nama (jika tersedia)
                food_name = row.get('food_name')
                if food_name:
                    default_id = get_default_food_id_by_name(food_name)
                    if default_id:
                        insert_row['food_id'] = default_id
                    else:
                        # Jika tidak ditemukan, skip atau raise error
                        continue
                else:
                    continue
            cols = ','.join(insert_row.keys())
            placeholders = ','.join(['?'] * len(insert_row))
            conn.execute(
                f"INSERT INTO recipe_items ({cols}) VALUES ({placeholders})",
                list(insert_row.values())
            )
        
        # 4d. food_logs
        rows = data['tables'].get('food_logs', [])
        for row in rows:
            insert_row = {k: v for k, v in row.items() if k != 'id'}
            insert_row['user_id'] = user_id
            old_fid = row.get('food_id')
            if old_fid in mapping['food_items']:
                insert_row['food_id'] = mapping['food_items'][old_fid]
            else:
                food_name = row.get('food_name')
                if food_name:
                    default_id = get_default_food_id_by_name(food_name)
                    if default_id:
                        insert_row['food_id'] = default_id
                    else:
                        continue
                else:
                    continue
            # Hapus food_name agar tidak ikut INSERT
            insert_row.pop('food_name', None)

            cols = ','.join(insert_row.keys())
            placeholders = ','.join(['?'] * len(insert_row))
            conn.execute(
                f"INSERT INTO food_logs ({cols}) VALUES ({placeholders})",
                list(insert_row.values())
            )
        
        # 4e. economy_items (opsional folder_id)
        rows = data['tables'].get('economy_items', [])
        for row in rows:
            insert_row = {k: v for k, v in row.items() if k != 'id'}
            insert_row['user_id'] = user_id
            old_fid = row.get('folder_id')
            if old_fid is not None and old_fid in mapping['task_folders']:
                insert_row['folder_id'] = mapping['task_folders'][old_fid]
            else:
                insert_row['folder_id'] = None
            cols = ','.join(insert_row.keys())
            placeholders = ','.join(['?'] * len(insert_row))
            conn.execute(
                f"INSERT INTO economy_items ({cols}) VALUES ({placeholders})",
                list(insert_row.values())
            )
        
        # 4f. debts, savings, investments, subscriptions, water_logs, health_logs, calendar_notes, reminders
        # Tidak memiliki foreign key ke tabel lain (selain user_id yang sudah diisi)
        tables_no_fk = [
            'debts', 'savings', 'investments', 'subscriptions',
            'water_logs', 'health_logs', 'calendar_notes', 'reminders'
        ]
        for table in tables_no_fk:
            rows = data['tables'].get(table, [])
            for row in rows:
                insert_row = {k: v for k, v in row.items() if k != 'id'}
                insert_row['user_id'] = user_id
                cols = ','.join(insert_row.keys())
                placeholders = ','.join(['?'] * len(insert_row))
                conn.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders})",
                    list(insert_row.values())
                )
        
        conn.commit()
    
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

def get_food_translation(name_id: str, lang: str = "id") -> str:
    """Wrapper untuk memudahkan akses terjemahan nama makanan dari database."""
    from food_data import get_food_name
    return get_food_name(name_id, lang)

# ========== DATABASE BACKUP & FORCE SYNC ==========
def force_checkpoint():
    """Paksa WAL checkpoint agar semua data di memori tertulis ke database utama."""
    try:
        conn = get_conn()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        print("[DB] Checkpoint berhasil.")
    except Exception as e:
        print(f"[DB] Checkpoint gagal: {e}")

def backup_database():
    """Buat backup database ke folder backups/ dengan timestamp."""
    try:
        # Force checkpoint dulu agar backup lengkap
        force_checkpoint()
        
        src = DB_PATH
        if not os.path.exists(src):
            print("[DB] Database tidak ditemukan, backup batal.")
            return None
        
        backup_dir = os.path.join(os.path.dirname(src), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(backup_dir, f"craftlife_backup_{timestamp}.db")
        
        import shutil
        shutil.copy2(src, dst)
        print(f"[DB] Backup berhasil: {dst}")
        
        # Hapus backup lama (lebih dari 7 hari)
        try:
            import time
            now = time.time()
            for f in os.listdir(backup_dir):
                if f.startswith("craftlife_backup_") and f.endswith(".db"):
                    path = os.path.join(backup_dir, f)
                    if os.path.getmtime(path) < now - (7 * 86400):
                        os.remove(path)
                        print(f"[DB] Hapus backup lama: {f}")
        except:
            pass
            
        return dst
    except Exception as e:
        print(f"[DB] Backup gagal: {e}")
        return None

# ── Auth ──────────────────────────────────────────────────────────────────────

def _hash(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def register_user(username, password, display_name="", bio="", avatar_class="warrior"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users(username,password_hash,display_name,bio,avatar_class)"
            " VALUES(?,?,?,?,?)", 
            (username.lower().strip(), _hash(password),
             display_name or username, bio, avatar_class)
        )
        conn.commit()
        user_id = conn.execute("SELECT id FROM users WHERE username=?", (username.lower().strip(),)).fetchone()
        uid = user_id["id"] if user_id else None
        msg = tr_db(user_id=uid, key="db_register_success") if uid else "Registrasi berhasil!"
        return {"ok": True, "msg": msg}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": tr_db(lang="id", key="db_register_username_taken")}
    finally:
        conn.close()


def login_user(username, password):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE username=? AND password_hash=?",
        (username.lower().strip(), _hash(password))
    ).fetchone()
    if row:
        conn.execute("UPDATE users SET last_login=? WHERE id=?",
                     (local_now().isoformat(), row["id"]))
        conn.commit()
        conn.close()
        return {"ok": True, "user": dict(row)}
    conn.close()
    return {"ok": False, "msg": tr_db(lang="id", key="db_login_failed")}


def change_password(user_id, old_pw, new_pw):
    u = get_user(user_id)
    if _hash(old_pw) != u.get("password_hash", ""):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_old_password_wrong")}
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (_hash(new_pw), user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_password_changed")}


# ── User ──────────────────────────────────────────────────────────────────────

def get_user(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}

@retry_on_lock
def update_user(user_id, **kw):
    if not kw:
        return
    fields = ", ".join(f"{k}=?" for k in kw)
    conn = get_conn()
    conn.execute(f"UPDATE users SET {fields} WHERE id=?",
                 list(kw.values()) + [user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def recalculate_all_buffs(user_id):
    conn = get_conn()
    try:
        # Ambil data user
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            return
        u = dict(u)

        # Inventory
        inv_rows = conn.execute("SELECT item_id FROM inventory WHERE user_id=?", (user_id,)).fetchall()
        owned = {row["item_id"] for row in inv_rows}

        # Hitung buff dari item
        dmg = 0.0
        xp_pct = 0.0
        gold_pct = 0.0
        reduc = 0.0
        mp = 0
        revive = 0
        has_spyglass = False
        crit = 0
        block_chance = 20
        block_strength = 10
        for iid in owned:
            b = SHOP_ITEMS.get(iid, {}).get("buff", {})
            dmg += b.get("boss_dmg", 0)
            xp_pct += b.get("xp_pct", 0) / 100
            gold_pct += b.get("gold_pct", 0) / 100
            reduc += b.get("hp_reduc", 0)
            mp += b.get("mp_bonus", 0)
            crit += b.get("crit_chance", 0)
            block_chance += b.get("block_chance", 0)
            block_strength += b.get("block_strength", 0) 
            if b.get("revive"):
                revive = 1
            if iid == "spyglass":
                has_spyglass = True

        # Ambil semua pet aktif
        active_pets = conn.execute(
            "SELECT pet_id, level FROM user_pets WHERE user_id=? AND is_active=1",
            (user_id,)
        ).fetchall()
        for pet_row in active_pets:
            pid = pet_row["pet_id"]
            base = PETS_DATA.get(pid, {}).get("base_buff", {})
            level = pet_row["level"]
            scale = 1 + (level - 1) * 0.05   # scaling 5% per level
            xp_pct += base.get("xp_pct", 0) * scale / 100   
            gold_pct += base.get("gold_pct", 0) * scale / 100
            dmg += base.get("boss_dmg", 0) * scale
            reduc += base.get("hp_reduc", 0) * scale

        # Guild buff
        gid = u.get("guild_id")
        if gid:
            guild = conn.execute("SELECT buff_xp, buff_gold, buff_damage FROM guilds WHERE id=?", (gid,)).fetchone()
            if guild:
                xp_pct += guild["buff_xp"] / 100
                gold_pct += guild["buff_gold"] / 100
                dmg += guild["buff_damage"]

        # Rebirth buffs
        rebirth_count = u.get("rebirth_count", 0)
        xp_pct += rebirth_count * 0.10
        gold_pct += rebirth_count * 0.05

        # Class passive buffs
        class_row = conn.execute("SELECT class_passive_buffs FROM users WHERE id=?", (user_id,)).fetchone()
        class_buffs = {}
        if class_row and class_row["class_passive_buffs"]:
            import json
            class_buffs = json.loads(class_row["class_passive_buffs"])
        xp_pct += class_buffs.get("xp_multiplier", 1.0) - 1.0
        gold_pct += class_buffs.get("gold_multiplier", 1.0) - 1.0

        # Hitung MP baru
        base_mp = 30 + (u["level"] - 1) * 5
        new_max_mp = base_mp + mp
        current_mp = u["mp"]
        if current_mp > new_max_mp:
            current_mp = new_max_mp

        # Update user dalam satu pernyataan
        conn.execute("""UPDATE users SET
            boss_damage_bonus=?,
            xp_multiplier=?,
            gold_multiplier=?,
            hp_damage_reduction=?,
            mp_bonus=?,
            max_mp=?,
            mp=?,
            has_revive=?,
            has_spyglass=?,
            crit_chance=?,
            block_chance=?,
            block_strength=?
            WHERE id=?""",
            (dmg, 
            round(1.0 + xp_pct, 4), 
            round(1.0 + gold_pct, 4),
            reduc, 
            mp, 
            new_max_mp, 
            current_mp, 
            revive, 
            1 if has_spyglass else 0, 
            crit + 10, 
            block_chance, 
            block_strength, 
            user_id))
        conn.commit()
    finally:
        conn.close()


# ── XP / Gold / HP ────────────────────────────────────────────────────────────

@retry_on_lock
def gain_xp_gold(user_id, xp_base, gold_base, skip_achievements=False):
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not u:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_user_not_found"), "leveled_up": False}
    
    buffs = get_skill_buffs(user_id)
    
    # Hitung XP multiplier dari skill
    skill_xp_mult = buffs.get("xp_multiplier", 1.0)
    if buffs.get("xp_remaining", 0) > 0:
        buffs["xp_remaining"] -= 1
        if buffs["xp_remaining"] == 0:
            buffs.pop("xp_multiplier", None)
            buffs.pop("xp_remaining", None)
        set_skill_buffs(user_id, buffs)
    else:
        skill_xp_mult = 1.0
    
    # Hitung Gold multiplier dari skill (Archer)
    skill_gold_mult = buffs.get("gold_multiplier", 1.0)
    if buffs.get("gold_remaining", 0) > 0:
        buffs["gold_remaining"] -= 1
        if buffs["gold_remaining"] == 0:
            buffs.pop("gold_multiplier", None)
            buffs.pop("gold_remaining", None)
        set_skill_buffs(user_id, buffs)
    else:
        skill_gold_mult = 1.0
    
    # Hitung multiplier dasar
    total_xp_mult = u.get("xp_multiplier", 1.0) * skill_xp_mult
    total_gold_mult = u.get("gold_multiplier", 1.0) * skill_gold_mult

    # Jika admin, kalikan 5
    if u.get("is_admin", 0):
        total_xp_mult *= 5
        total_gold_mult *= 5

    xp = int(xp_base * total_xp_mult)
    gold = gold_base * total_gold_mult
    new_xp   = u["xp"] + xp
    new_gold = u["gold"] + gold
    new_lvl  = u["level"]
    leveled  = False
    needed   = new_lvl * 150
    while new_xp >= needed:
        new_xp -= needed
        new_lvl += 1
        leveled = True
        mhp = 50 + (new_lvl - 1) * 10
        mmp = 30 + (new_lvl - 1) * 5
        class_buffs = get_class_passive_buffs(user_id)
        hp_mult = class_buffs.get("hp_multiplier", 1.0)
        mhp = int(mhp * hp_mult)
        mp_bonus = u.get("mp_bonus", 0)
        mmp += mp_bonus
        update_user(user_id, max_hp=mhp, hp=mhp, max_mp=mmp, mp=mmp)
        add_notification(user_id, tr_db(user_id=user_id, key="db_level_up", lvl=new_lvl), "levelup")
        apply_hp_multiplier(user_id)
        needed = new_lvl * 150
    if leveled and not skip_achievements:
        check_achievements(user_id, "level_reach", new_lvl)
    update_user(user_id,
                xp=new_xp, level=new_lvl, gold=new_gold,
                total_xp_earned=u.get("total_xp_earned", 0) + xp,
                total_gold_earned=u.get("total_gold_earned", 0.0) + gold)
    if not skip_achievements:
        check_achievements(user_id, "total_gold", u.get("total_gold_earned", 0) + gold) 
    log_activity(user_id, "reward", tr_db(user_id=user_id, key="log_reward", xp=xp, gold=gold), xp, gold)
    u2 = get_user(user_id)
    if u2.get("guild_id"):
        add_guild_exp(u2["guild_id"], xp_base // 5) 
    return {"ok": True, "leveled_up": leveled, "new_level": new_lvl,
            "new_xp": new_xp, "xp_gained": xp, "gold_gained": gold}


def lose_hp(user_id, base_amount, ignore_reduction=False):
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"revived": False, "new_hp": 0}
    if not u:
        return {"revived": False, "new_hp": 0}
    level = u.get("level", 1)
    additional = min(25, level * 0.5)
    total_damage = base_amount + additional
    if ignore_reduction:
        reduc = 0
    else:
        reduc = u.get("hp_damage_reduction", 0)
    actual = max(0.0, total_damage - reduc)
    actual_int = int(actual)                     # bulatkan ke bawah
    new_hp = max(0, u["hp"] - actual_int)
    new_hp_int = int(new_hp)                     # pastikan integer

    if new_hp_int == 0 and u.get("has_revive"):
        new_hp_int = int(u["max_hp"] * 0.3)
        update_user(user_id, hp=new_hp_int, has_revive=0)
        recalculate_all_buffs(user_id)
        add_notification(user_id, tr_db(user_id=user_id, key="db_totem_revive"), "success")
        return {"revived": True, "new_hp": new_hp_int, "damage_taken": actual_int}

    update_user(user_id, hp=new_hp_int)
    if new_hp_int == 0:
        add_notification(user_id, tr_db(user_id=user_id, key="db_hp_zero"), "danger")
    return {"revived": False, "new_hp": new_hp_int, "damage_taken": actual_int}

def penalize_gold(user_id, base_amount=5):
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"gold_lost": 0, "remaining_gold": 0}
    if not u:
        return {"gold_lost": 0, "remaining_gold": 0}
    level = u.get("level", 1)
    additional = min(25, level * 0.5)
    total_penalty = int(base_amount + additional)
    current_gold = u.get("gold", 0)
    if current_gold <= 0:
        return {"gold_lost": 0, "remaining_gold": 0}
    gold_lost = min(total_penalty, current_gold)
    new_gold = current_gold - gold_lost
    update_user(user_id, gold=new_gold)
    log_activity(user_id, "penalty_gold", tr_db(user_id=user_id, key="log_penalty_gold", gold=gold_lost), 0, -gold_lost)
    return {"gold_lost": gold_lost, "remaining_gold": new_gold}


def penalize_xp(user_id):
    """
    Kurangi XP user sebesar 10% dari XP yang dimiliki saat itu.
    Minimal 1 XP (jika XP > 0).
    Bisa menyebabkan turun level jika XP tidak cukup untuk menahan penalti.
    """
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not u:
        return {"xp_lost": 0, "new_level": 1}
    
    current_xp = u.get("xp", 0)
    current_level = u.get("level", 1)
    
    # Hitung 10% dari XP yang dimiliki, minimal 1 XP
    if current_xp <= 0:
        return {"xp_lost": 0, "new_level": current_level}
    
    xp_lost = max(1, int(current_xp * 0.1))  # 10% dari XP, minimal 1
    
    new_xp = current_xp - xp_lost
    new_level = current_level
    
    # Turunkan level jika XP negatif
    while new_xp < 0 and new_level > 1:
        new_level -= 1
        new_xp += new_level * 150
    if new_xp < 0:
        new_xp = 0
    
    update_user(user_id, xp=new_xp, level=new_level)
    log_activity(
        user_id,
        "penalty_xp",
        tr_db(user_id=user_id, key="log_penalty_xp", xp=xp_lost, level=new_level),
        -xp_lost,
        0
    )
    add_notification(
        user_id,
        tr_db(user_id=user_id, key="penalty_xp_loss_percent", xp=xp_lost, new_level=new_level),
        "danger"
    )
    
    return {"xp_lost": xp_lost, "new_level": new_level, "new_xp": new_xp}

def restore_mp(user_id, amount=5):
    u = get_user(user_id)
    cap = u["max_mp"] + u.get("mp_bonus", 0)
    update_user(user_id, mp=min(cap, u["mp"] + amount))


# ── Class Skills ──────────────────────────────────────────────────────────────

CLASS_SKILLS = {
    "warrior": {"name": "Shield Bash",  "icon": "🛡️",
                "mp_cost": 10,
                "desc": "Kurangi 50% damage dari boss satu kali"},
    "mage":    {"name": "Arcane Surge", "icon": "✨",
                "mp_cost": 15,
                "desc": "+30% XP untuk 3 habit berikutnya"},
    "archer":  {"name": "Gold Shot",    "icon": "🏹",
                "mp_cost": 10,
                "desc": "+50% Gold dari habit berikutnya"},
    "healer":  {"name": "Regenerate",   "icon": "💚",
                "mp_cost": 20,
                "desc": "Pulihkan 20 HP sekarang juga"},
    "rogue":   {"name": "Shadow Step",  "icon": "🗡️",
                "mp_cost": 15,
                "desc": "+1 streak untuk daily berikutnya"},
}


def use_class_skill(user_id):
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    cls = u.get("avatar_class", "warrior")
    skill = CLASS_SKILLS.get(cls, {})
    cost = skill.get("mp_cost", 10)
    
    # Admin: gratis, tanpa cek MP
    if u.get("is_admin", 0):
        cost = 0
    elif u["mp"] < cost:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_mp_insufficient", cost=cost, mp=u['mp'])}
    
    # Kurangi MP (hanya jika bukan admin atau admin dengan cost 0)
    update_user(user_id, mp=u["mp"] - cost)
    
    # Handle skill Healer
    if cls == "healer":
        new_hp = min(u["max_hp"], u["hp"] + 30)
        update_user(user_id, hp=new_hp)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_heal_regenerate")}
    
    # Skill lain
    result = apply_skill_effect(user_id, cls)
    if result["ok"]:
        add_notification(user_id, result["msg"], "info")
    return result

import json

def get_skill_buffs(user_id):
    """Ambil data buff skill user dari database (JSON)"""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    row = conn.execute("SELECT skill_buff_data FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["skill_buff_data"]:
        return json.loads(row["skill_buff_data"])
    return {}

def set_skill_buffs(user_id, buffs):
    """Simpan data buff skill user ke database"""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("UPDATE users SET skill_buff_data=? WHERE id=?", (json.dumps(buffs), user_id))
    conn.commit()
    conn.close()

def get_class_passive_buffs(user_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    row = conn.execute("SELECT class_passive_buffs FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["class_passive_buffs"]:
        return json.loads(row["class_passive_buffs"])
    return {}

def set_class_passive_buffs(user_id, buffs):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("UPDATE users SET class_passive_buffs=? WHERE id=?", (json.dumps(buffs), user_id))
    conn.commit()
    conn.close()

def update_class_passive_buffs(user_id):
    u = get_user(user_id)
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    cls = u.get("avatar_class", "warrior")
    buffs = {}
    if cls == "warrior":
        buffs = {"hp_multiplier": 1.10, "hp_bonus": 0}   # +10% HP (dari 20%)
    elif cls == "mage":
        buffs = {"xp_multiplier": 1.08}                  # +8% XP (dari 15%)
    elif cls == "archer":
        buffs = {"gold_multiplier": 1.06}                # +6% Gold (dari 10%)
    elif cls == "rogue":
        buffs = {"streak_bonus": 1}                      # +1 streak awal untuk daily/habit
    # Healer tidak punya buff pasif (sudah punya skill penyembuhan)
    set_class_passive_buffs(user_id, buffs)
    recalculate_all_buffs(user_id)

def apply_skill_effect(user_id, skill_name):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    """Terapkan efek skill ke user (simpan state)"""
    buffs = get_skill_buffs(user_id)
    if skill_name == "warrior":
        buffs["shield_active"] = True
        msg = tr_db(user_id=user_id, key="db_skill_shield")
    elif skill_name == "mage":
        buffs["xp_multiplier"] = 1.3
        buffs["xp_remaining"] = 3
        msg = tr_db(user_id=user_id, key="db_skill_arcane")
    elif skill_name == "archer":
        buffs["gold_multiplier"] = 1.5
        buffs["gold_remaining"] = 1
        msg = tr_db(user_id=user_id, key="db_skill_gold_shot")
    elif skill_name == "rogue":
        buffs["double_streak"] = 1
        msg = tr_db(user_id=user_id, key="db_skill_shadow")
    else:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_skill_unknown")}
    
    set_skill_buffs(user_id, buffs)
    return {"ok": True, "msg": msg}

# ── Habits ────────────────────────────────────────────────────────────────────

_XP  = {"trivial": 8,  "easy": 15, "medium": 25, "hard": 40, "epic": 60}
_GLD = {"trivial": 2,  "easy": 3,  "medium": 5,  "hard": 8,  "epic": 12}

# Daily rewards
_DAILY_XP = {"easy": 20, "medium": 30, "hard": 50, "epic": 75}
_DAILY_GLD = {"easy": 4, "medium": 6, "hard": 10, "epic": 15}

# Todo rewards
_TODO_XP = {"trivial": 10, "easy": 20, "medium": 40, "hard": 60}
_TODO_GLD = {"trivial": 2, "easy": 4, "medium": 8, "hard": 14}


def get_habits(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM habits WHERE user_id=? ORDER BY sort_order",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_habit(user_id, name, icon="⚔️", difficulty="medium", positive=1, negative=0, notes=""):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM habits WHERE user_id=? AND folder_id IS NULL",
        (user_id,)
    ).fetchone()[0]
    new_order = max_order + 1

    conn.execute(
        "INSERT INTO habits(user_id,name,icon,difficulty,"
        "xp_reward,gold_reward,positive,negative,notes,sort_order)"
        " VALUES(?,?,?,?,?,?,?,?,?,?)",
        (user_id, name, icon, difficulty,
         _XP.get(difficulty, 25), _GLD.get(difficulty, 5),
         positive, negative, notes, new_order)
    )
    conn.commit()
    conn.close()

def update_habit(habit_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if "difficulty" in kwargs:
        diff = kwargs["difficulty"]
        kwargs.setdefault("xp_reward", _XP.get(diff, 25))
        kwargs.setdefault("gold_reward", _GLD.get(diff, 5))
    
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE habits SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [habit_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_habit(user_id, habit_id, direction="up"):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        h = conn.execute("SELECT * FROM habits WHERE id=? AND user_id=?", (habit_id, user_id)).fetchone()
        if not h:
            return {"ok": False}
        today = date.today().isoformat()
        if h["done_today"]:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_habit_already_done")}
        new_streak = h["streak"] + 1 if direction == "up" else 0
        conn.execute("""UPDATE habits SET done_today=1, streak=?, last_done=?, last_action=?, 
                        counter_up=counter_up+?, counter_down=counter_down+? WHERE id=?""",
                     (new_streak, today, direction, 1 if direction=="up" else 0, 1 if direction=="down" else 0, habit_id))
        conn.execute("UPDATE users SET total_habits_done=total_habits_done+1 WHERE id=?", (user_id,))
        conn.execute("UPDATE users SET total_tasks_completed = total_tasks_completed + 1 WHERE id=?", (user_id,))
        new_total = conn.execute("SELECT total_tasks_completed FROM users WHERE id=?", (user_id,)).fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    if direction == "up":
        restore_mp(user_id, 3)
        u = get_user(user_id)
        if new_streak > u.get("longest_streak", 0):
            update_user(user_id, longest_streak=new_streak)
        # Panggil achievements
        check_achievements(user_id, "habit_complete", 1)
        check_achievements(user_id, "habit_streak", new_streak)
        check_achievements(user_id, "total_tasks", new_total)
        today = date.today().isoformat()
        log_task_history(user_id, "habit", habit_id, "success", today)
        return gain_xp_gold(user_id, h["xp_reward"], h["gold_reward"])
    else:
        today = date.today().isoformat()
        log_task_history(user_id, "habit", habit_id, "fail", today)
        damage_result = lose_hp(user_id, 5, ignore_reduction=True)
        return {"ok": True, "lost_hp": damage_result.get("damage_taken", 5)}

def add_guild_exp(guild_id, amount):
    # ── Step 1: Hitung level & update guilds, lalu TUTUP koneksi ─────────────
    conn = get_conn()
    g = conn.execute("SELECT * FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not g:
        conn.close()
        return
    g = dict(g)
    new_exp = g["exp"] + amount
    new_level = g["level"]
    needed = new_level * 500
    leveled = False
    member_ids = []
    while new_exp >= needed:
        new_exp -= needed
        new_level += 1
        leveled = True
        needed = new_level * 500
    if leveled:
        buff_xp = new_level * 2
        buff_gold = new_level * 1
        buff_damage = new_level * 1
        buff_crit = new_level * 1
        conn.execute(
            "UPDATE guilds SET level=?, exp=?, buff_xp=?, buff_gold=?, buff_damage=?, crit_chance=? WHERE id=?",
            (new_level, new_exp, buff_xp, buff_gold, buff_damage, buff_crit, guild_id))
        members = conn.execute("SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)).fetchall()
        member_ids = [m["user_id"] for m in members]
    else:
        conn.execute("UPDATE guilds SET exp=? WHERE id=?", (new_exp, guild_id))
    conn.commit()
    conn.close()   # ← TUTUP dulu sebelum panggil add_notification / recalculate_all_buffs

    # ── Step 2: Notifikasi & recalc buff (koneksi terpisah, tidak nested) ─────
    if leveled:
        for uid in member_ids:
            add_notification(uid, tr_db(user_id=uid, key="db_guild_level_up", name=g['name'], lvl=new_level), "levelup")
            recalculate_all_buffs(uid)

def delete_habit(user_id, habit_id):
    conn = get_conn()
    conn.execute("DELETE FROM habits WHERE id=? AND user_id=?",
                 (habit_id, user_id))
    conn.commit()
    conn.close()


@retry_on_lock
def reset_daily_tasks(user_id):
    today = date.today().isoformat()
    conn = get_conn()
    conn.execute(
        "UPDATE habits SET done_today=0"
        " WHERE user_id=? AND (last_done IS NULL OR last_done!=?)",
        (user_id, today))
    conn.execute(
        "UPDATE dailies SET done_today=0"
        " WHERE user_id=? AND (last_done IS NULL OR last_done!=?)",
        (user_id, today))
    conn.execute(
        "UPDATE sport_activities SET done_today=0"
        " WHERE user_id=? AND (last_done IS NULL OR last_done!=?)",
        (user_id, today))
    conn.commit()
    fill_skipped_history(user_id) 
    conn.close()


# ── Dailies ───────────────────────────────────────────────────────────────────
def get_dailies(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM dailies WHERE user_id=? ORDER BY sort_order",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_daily(user_id, name, icon="📅", difficulty="medium", notes=""):
    conn = get_conn()
    # Hitung sort_order terakhir untuk user ini tanpa folder
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM dailies WHERE user_id=? AND folder_id IS NULL",
        (user_id,)
    ).fetchone()[0]
    new_order = max_order + 1

    conn.execute(
        "INSERT INTO dailies(user_id,name,icon,difficulty,"
        "xp_reward,gold_reward,notes,sort_order) VALUES(?,?,?,?,?,?,?,?)",
        (user_id, name, icon, difficulty,
         _DAILY_XP.get(difficulty, 30), _DAILY_GLD.get(difficulty, 6), notes, new_order)
    )
    conn.commit()
    conn.close()

def update_daily(daily_id, user_id, **kwargs):
    if "difficulty" in kwargs:
        diff = kwargs["difficulty"]
        kwargs.setdefault("xp_reward", _DAILY_XP.get(diff, 30))
        kwargs.setdefault("gold_reward", _DAILY_GLD.get(diff, 6))
    
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE dailies SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [daily_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_daily(user_id, daily_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        d = conn.execute("SELECT * FROM dailies WHERE id=? AND user_id=?", (daily_id, user_id)).fetchone()
        if not d or d["done_today"]:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_daily_already_done")}
        d = dict(d)
    finally:
        conn.close()

    today = date.today().isoformat()
    buffs = get_skill_buffs(user_id)
    streak_bonus = 2 if buffs.get("double_streak") else 1
    if buffs.get("double_streak"):
        buffs.pop("double_streak", None)
        set_skill_buffs(user_id, buffs)
    new_streak = d["streak"] + streak_bonus

    conn2 = get_conn()
    try:
        conn2.execute("UPDATE dailies SET done_today=1, streak=?, last_done=?, last_action='up', fail_streak=0 WHERE id=?", (new_streak, today, daily_id))
        conn2.execute("UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?", (user_id,))
        conn2.execute("UPDATE users SET total_tasks_completed = total_tasks_completed + 1 WHERE id=?", (user_id,))
        new_total = conn2.execute("SELECT total_tasks_completed FROM users WHERE id=?", (user_id,)).fetchone()[0]
        conn2.commit()
    finally:
        conn2.close()

    restore_mp(user_id, 5)
    check_achievements(user_id, "daily_complete", 1)
    check_achievements(user_id, "total_tasks", new_total)
    today = date.today().isoformat()
    log_task_history(user_id, "daily", daily_id, "success", today)
    return gain_xp_gold(user_id, d["xp_reward"], d["gold_reward"])

@retry_on_lock
def fail_daily(user_id, daily_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    d = conn.execute("SELECT * FROM dailies WHERE id=? AND user_id=?", (daily_id, user_id)).fetchone()
    if not d or d["done_today"]:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_daily_fail_already")}
    
    today = date.today().isoformat()
    
    # ── CEK FREEZE SLOT ──
    if d["freeze_slots"] > 0:
        new_freeze = d["freeze_slots"] - 1
        conn.execute("""
            UPDATE dailies 
            SET done_today=1, freeze_slots=?, last_done=?, last_action='frozen' 
            WHERE id=?
        """, (new_freeze, today, daily_id))
        conn.execute("UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        log_task_history(user_id, "daily", daily_id, "freeze", today)
        return {
            "ok": True,
            "freeze_used": True,
            "remaining_freezes": new_freeze,
            "msg": tr_db(user_id, "freeze_used_message", remaining=new_freeze)
        }
    
    # ── LOGIKA PENALTI NORMAL (jika tidak ada freeze) ──
    new_fail_streak = (d["fail_streak"] or 0) + 1
    conn.execute("""
        UPDATE dailies 
        SET done_today=1, streak=0, fail_streak=?, last_done=?, last_action='down' 
        WHERE id=?
    """, (new_fail_streak, today, daily_id))
    conn.execute("UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()

    log_task_history(user_id, "daily", daily_id, "fail", today)

    u = get_user(user_id)
    damage_taken = 0
    penalty_type = "hp"
    penalty_amount = 0

    if u.get("hp", 0) > 0:
        hp_result = lose_hp(user_id, 5, ignore_reduction=True)
        damage_taken = hp_result.get("damage_taken", 0)
        penalty_type = "hp"
        penalty_amount = damage_taken
        u = get_user(user_id)

    if u.get("hp", 0) <= 0:
        gold_result = penalize_gold(user_id, base_amount=5)
        gold_lost = gold_result.get("gold_lost", 0)
        if gold_lost > 0:
            penalty_type = "gold"
            penalty_amount = gold_lost
            add_notification(user_id, tr_db(user_id=user_id, key="penalty_hp_zero_gold", gold=gold_lost), "warning")
        else:
            xp_result = penalize_xp(user_id)
            xp_lost = xp_result.get("xp_lost", 0)
            if xp_lost > 0:
                penalty_type = "xp"
                penalty_amount = xp_lost
            else:
                penalty_type = "none"
                penalty_amount = 0
                add_notification(user_id, tr_db(user_id=user_id, key="penalty_all_failed"), "error")

    return {
        "ok": True,
        "lost_hp": damage_taken,
        "fail_streak": new_fail_streak,
        "penalty_type": penalty_type,
        "penalty_amount": penalty_amount
    }

def delete_daily(user_id, daily_id):
    conn = get_conn()
    conn.execute("DELETE FROM dailies WHERE id=? AND user_id=?",
                 (daily_id, user_id))
    conn.commit()
    conn.close()

def add_freeze_to_daily(user_id, daily_id):
    """Gunakan 1 Ice Block untuk menambah 1 freeze slot ke Daily tertentu (max 3)."""
    conn = get_conn()
    try:
        daily = conn.execute(
            "SELECT id, freeze_slots FROM dailies WHERE id=? AND user_id=?",
            (daily_id, user_id)
        ).fetchone()
        if not daily:
            return {"ok": False, "msg": tr_db(user_id, "db_daily_not_found")}
        
        if daily["freeze_slots"] >= 3:
            return {"ok": False, "msg": tr_db(user_id, "freeze_max_reached")}
        
        inv = conn.execute(
            "SELECT id FROM inventory WHERE user_id=? AND item_id='ice_block' AND quantity>0",
            (user_id,)
        ).fetchone()
        if not inv:
            return {"ok": False, "msg": tr_db(user_id, "freeze_no_item")}
        
        conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id=?", (inv["id"],))
        new_freeze = daily["freeze_slots"] + 1
        conn.execute(
            "UPDATE dailies SET freeze_slots = freeze_slots + 1 WHERE id=?",
            (daily_id,)
        )
        conn.commit()
        return {
            "ok": True,
            "remaining": new_freeze,
            "msg": tr_db(user_id, "freeze_added_success", remaining=new_freeze)
        }
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": tr_db(user_id, "freeze_error", error=str(e))}
    finally:
        conn.close()


# ── Todos ─────────────────────────────────────────────────────────────────────

def get_todos(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM todos WHERE user_id=? ORDER BY sort_order",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_todo(user_id, name, priority="medium", icon="📜",
             due_date=None, notes=""):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Hitung sort_order terakhir untuk user ini tanpa folder
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM todos WHERE user_id=? AND folder_id IS NULL",
        (user_id,)
    ).fetchone()[0]
    new_order = max_order + 1

    conn.execute(
        "INSERT INTO todos(user_id,name,icon,priority,"
        "xp_reward,gold_reward,due_date,notes,sort_order) VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, name, icon, priority,
         _TODO_XP.get(priority, 40), _TODO_GLD.get(priority, 8), due_date, notes, new_order)
    )
    conn.commit()
    conn.close()

def update_todo(todo_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if "priority" in kwargs:
        prio = kwargs["priority"]
        kwargs.setdefault("xp_reward", _TODO_XP.get(prio, 40))
        kwargs.setdefault("gold_reward", _TODO_GLD.get(prio, 8))
    
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE todos SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [todo_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_todo(user_id, todo_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        t = conn.execute("SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)).fetchone()
        if not t or t["done"]:
            return {"ok": False}
        conn.execute("UPDATE todos SET done=1 WHERE id=?", (todo_id,))
        conn.execute("UPDATE users SET total_todos_done=total_todos_done+1 WHERE id=?", (user_id,))
        conn.execute("UPDATE users SET total_tasks_completed = total_tasks_completed + 1 WHERE id=?", (user_id,))
        new_total = conn.execute("SELECT total_tasks_completed FROM users WHERE id=?", (user_id,)).fetchone()[0]
        xp_reward = t["xp_reward"]
        gold_reward = t["gold_reward"]
        conn.commit()
    finally:
        conn.close()
    
    # Panggil log_task_history setelah transaksi selesai untuk menghindari deadlock
    today = date.today().isoformat()
    log_task_history(user_id, "todo", todo_id, "success", today)
    
    restore_mp(user_id, 4)
    check_achievements(user_id, "todo_complete", 1)
    check_achievements(user_id, "total_tasks", new_total)
    return gain_xp_gold(user_id, xp_reward, gold_reward)

def delete_todo(user_id, todo_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("DELETE FROM todos WHERE id=? AND user_id=?",
                 (todo_id, user_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════
#  TASK FOLDERS  (shared by habits / dailies / todos / sport)
# ═══════════════════════════════════════════════════════════════════════════

def get_task_folders(user_id, mode):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM task_folders WHERE user_id=? AND mode=? ORDER BY created_at",
        (user_id, mode)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_task_folder(user_id, mode, name, icon="📁"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO task_folders(user_id,mode,name,icon) VALUES(?,?,?,?)",
        (user_id, mode, name, icon))
    folder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "folder_id": folder_id}


def update_task_folder(folder_id, user_id, **kwargs):
    if not kwargs:
        return
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(
        f"UPDATE task_folders SET {fields} WHERE id=? AND user_id=?",
        list(kwargs.values()) + [folder_id, user_id])
    conn.commit()
    conn.close()


def delete_task_folder(user_id, folder_id, mode):
    """Hapus folder dan lepas semua item dari folder tersebut (set folder_id=NULL)."""
    conn = get_conn()
    table_map = {"habit": "habits", "daily": "dailies",
                 "todo": "todos", "sport": "sport_activities"}
    tbl = table_map.get(mode)
    if tbl:
        conn.execute(f"UPDATE {tbl} SET folder_id=NULL WHERE folder_id=? AND user_id=?",
                     (folder_id, user_id))
    conn.execute("DELETE FROM task_folders WHERE id=? AND user_id=?",
                 (folder_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True}


def duplicate_task_folder(user_id, folder_id, mode):
    """Duplikasi folder beserta semua item di dalamnya."""
    conn = get_conn()
    folder = conn.execute(
        "SELECT * FROM task_folders WHERE id=? AND user_id=?",
        (folder_id, user_id)).fetchone()
    if not folder:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_folder_not_found")}

    # Buat folder baru
    cur = conn.execute(
        "INSERT INTO task_folders(user_id,mode,name,icon) VALUES(?,?,?,?)",
        (user_id, mode, folder["name"], folder["icon"]))
    new_folder_id = cur.lastrowid
    conn.commit()
    conn.close()

    # Duplikasi semua item dalam folder
    table_map = {"habit": "habits", "daily": "dailies",
                 "todo": "todos", "sport": "sport_activities"}
    tbl = table_map.get(mode)
    if tbl:
        conn2 = get_conn()
        items = conn2.execute(
            f"SELECT * FROM {tbl} WHERE folder_id=? AND user_id=?",
            (folder_id, user_id)).fetchall()
        for item in items:
            d = dict(item)
            d.pop("id", None)
            d["folder_id"] = new_folder_id
            # Reset progress fields
            for field in ("done_today","done","streak","last_done","last_action","counter_up","counter_down"):
                if field in d:
                    d[field] = 0 if field != "last_done" and field != "last_action" else ""
            cols   = ", ".join(d.keys())
            placeholders = ", ".join("?" * len(d))
            conn2.execute(f"INSERT INTO {tbl}({cols}) VALUES({placeholders})",
                          list(d.values()))
        conn2.commit()
        conn2.close()

    return {"ok": True, "new_folder_id": new_folder_id}


def set_item_folder(user_id, mode, item_id, folder_id):
    table_map = {
        "habit": "habits",
        "daily": "dailies",
        "todo": "todos",
        "sport": "sport_activities",
        "economy": "economy_items",
        "food": "food_logs"
    }
    tbl = table_map.get(mode)
    if not tbl:
        return

    conn = get_conn()
    try:
        if mode == "food":
            # folder_id di sini adalah meal_type (string)
            if folder_id not in ("breakfast", "lunch", "dinner", "snack", None):
                folder_id = "snack"  # fallback
            conn.execute(
                f"UPDATE {tbl} SET meal_type=? WHERE id=? AND user_id=?",
                (folder_id, item_id, user_id)
            )
            conn.commit()
            return

        # Mode lain: update folder_id dan sort_order
        if folder_id is not None:
            row = conn.execute(
                f"SELECT MAX(sort_order) as max_order FROM {tbl} WHERE user_id=? AND folder_id=?",
                (user_id, folder_id)
            ).fetchone()
        else:
            row = conn.execute(
                f"SELECT MAX(sort_order) as max_order FROM {tbl} WHERE user_id=? AND folder_id IS NULL",
                (user_id,)
            ).fetchone()
        max_order = row["max_order"] if row and row["max_order"] is not None else -1
        new_order = max_order + 1
        conn.execute(
            f"UPDATE {tbl} SET folder_id=?, sort_order=? WHERE id=? AND user_id=?",
            (folder_id, new_order, item_id, user_id)
        )
        conn.commit()
    finally:
        conn.close()


SPORT_TYPES = {
    "running":      {"name": "Lari",          "icon": "🏃"},
    "gym":          {"name": "Gym",            "icon": "🏋️"},
    "cycling":      {"name": "Bersepeda",      "icon": "🚴"},
    "swimming":     {"name": "Renang",         "icon": "🏊"},
    "yoga":         {"name": "Yoga",           "icon": "🧘"},
    "football":     {"name": "Olahraga Bola",  "icon": "⚽"},
    "calisthenics": {"name": "Kalistenik",     "icon": "🤸"},
    "martial_arts": {"name": "Bela Diri",      "icon": "🥊"},
    "badminton":    {"name": "Badminton",       "icon": "🏸"},
    "other":        {"name": "Lainnya",         "icon": "🏅"},
}

# XP / Gold / Sport Points reward per difficulty
_SP_XP  = {"easy": 15, "medium": 25, "hard": 40, "epic": 60}
_SP_GLD = {"easy": 3,  "medium": 5,  "hard": 8,  "epic": 12}
_SP_PTS = {"easy": 8,  "medium": 15, "hard": 25, "epic": 40}


def get_sport_activities(user_id, sport_type=None):
    conn = get_conn()
    if sport_type:
        rows = conn.execute(
            "SELECT * FROM sport_activities WHERE user_id=? AND sport_type=? ORDER BY sort_order",
            (user_id, sport_type)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sport_activities WHERE user_id=? ORDER BY sort_order",
            (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_sport_activity(user_id, name, sport_type="running", icon="🏃",
                       difficulty="medium", notes="", calories_burned=0, duration_minutes=30):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Hitung sort_order terakhir untuk user ini tanpa folder
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), 0) FROM sport_activities WHERE user_id=? AND folder_id IS NULL",
        (user_id,)
    ).fetchone()[0]
    new_order = max_order + 1

    conn.execute("""
        INSERT INTO sport_activities
        (user_id, name, sport_type, icon, difficulty,
         xp_reward, gold_reward, sport_points_reward, notes,
         calories_burned, duration_minutes, sort_order)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (user_id, name, sport_type, icon, difficulty,
          _SP_XP.get(difficulty, 25), _SP_GLD.get(difficulty, 5),
          _SP_PTS.get(difficulty, 15), notes,
          calories_burned, duration_minutes, new_order))
    conn.commit()
    conn.close()


def update_sport_activity(activity_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Jika difficulty berubah, sesuaikan reward otomatis
    if "difficulty" in kwargs:
        diff = kwargs["difficulty"]
        kwargs.setdefault("xp_reward",           _SP_XP.get(diff, 25))
        kwargs.setdefault("gold_reward",          _SP_GLD.get(diff, 5))
        kwargs.setdefault("sport_points_reward",  _SP_PTS.get(diff, 15))
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(
        f"UPDATE sport_activities SET {fields} WHERE id=? AND user_id=?",
        list(kwargs.values()) + [activity_id, user_id])
    conn.commit()
    conn.close()


@retry_on_lock
def delete_sport_activity(user_id, activity_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    row = conn.execute("SELECT last_done FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id)).fetchone()
    log_date = row["last_done"] if row else None
    conn.execute("DELETE FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id))
    conn.commit()
    conn.close()
    if log_date:
        update_daily_net_calories(user_id, log_date)


@retry_on_lock
def complete_sport_activity(user_id, activity_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        a = conn.execute("SELECT * FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id)).fetchone()
        if not a:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_sport_activity_not_found")}
        if a["done_today"]:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_sport_activity_done_today")}
        today = date.today().isoformat()
        conn.execute("UPDATE sport_activities SET done_today=1, streak=streak+1, last_done=? WHERE id=?", (today, activity_id))
        conn.commit()
    finally:
        conn.close()
    today = date.today().isoformat()
    log_task_history(user_id, "sport", activity_id, "success", today)
    result = gain_xp_gold(user_id, a["xp_reward"], a["gold_reward"])
    sp_result = gain_sport_points(user_id, a["sport_points_reward"])
    result["sport_points_gained"] = a["sport_points_reward"]
    result["sport_leveled_up"] = sp_result.get("leveled_up", False)
    result["new_sport_level"] = sp_result.get("new_sport_level", 1)
    result["new_sport_xp"] = sp_result.get("new_sport_xp", 0)
    check_achievements(user_id, "sport_points", a["sport_points_reward"])
    check_achievements(user_id, "sport_streak", a["streak"] + 1)
    update_daily_net_calories(user_id, today)
    return result


def gain_sport_points(user_id, points):
    """Tambahkan sport points & hitung sport level.
    Sport level TIDAK mempengaruhi main level/XP user sama sekali.
    Formula naik level: butuh level*100 sport points.
    """
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    row = conn.execute(
        "SELECT COALESCE(sport_level,1) as sport_level,"
        " COALESCE(sport_xp,0) as sport_xp,"
        " COALESCE(total_sport_points_earned,0) as total_sport_points_earned"
        " FROM users WHERE id=?", (user_id,)).fetchone()
    if not row:
        conn.close()
        return {"ok": False}

    new_sport_xp   = row["sport_xp"] + points
    new_sport_lvl  = row["sport_level"]
    total_earned   = row["total_sport_points_earned"] + points
    leveled        = False
    needed         = new_sport_lvl * 100
    while new_sport_xp >= needed:
        new_sport_xp -= needed
        new_sport_lvl += 1
        leveled = True
        needed = new_sport_lvl * 100

    conn.execute(
        "UPDATE users SET sport_xp=?, sport_level=?, total_sport_points_earned=?"
        " WHERE id=?",
        (new_sport_xp, new_sport_lvl, total_earned, user_id))
    conn.commit()
    conn.close()

    if leveled:
        add_notification(user_id, tr_db(user_id=user_id, key="db_sport_level_up", lvl=new_sport_lvl), "levelup")

    return {"ok": True, "leveled_up": leveled,
            "new_sport_level": new_sport_lvl,
            "new_sport_xp": new_sport_xp}

# ── Duplikasi ─────────────────────────────────────────
def duplicate_habit(user_id, habit_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    h = conn.execute("SELECT * FROM habits WHERE id=? AND user_id=?", (habit_id, user_id)).fetchone()
    if not h:
        conn.close()
        return {"ok": False}
    new_name = h['name']  # tanpa tambahan (copy)
    conn.execute("""
        INSERT INTO habits(user_id,name,icon,difficulty,xp_reward,gold_reward,positive,negative,notes)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (user_id, new_name, h['icon'], h['difficulty'], h['xp_reward'], h['gold_reward'],
          h['positive'], h['negative'], h['notes']))
    conn.commit()
    conn.close()
    return {"ok": True}

def duplicate_daily(user_id, daily_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    d = conn.execute("SELECT * FROM dailies WHERE id=? AND user_id=?", (daily_id, user_id)).fetchone()
    if not d:
        conn.close()
        return {"ok": False}
    new_name = d['name']  # tanpa tambahan (copy)
    conn.execute("""
        INSERT INTO dailies(user_id,name,icon,difficulty,xp_reward,gold_reward,notes)
        VALUES(?,?,?,?,?,?,?)
    """, (user_id, new_name, d['icon'], d['difficulty'], d['xp_reward'], d['gold_reward'], d['notes']))
    conn.commit()
    conn.close()
    return {"ok": True}

def duplicate_todo(user_id, todo_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    t = conn.execute("SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)).fetchone()
    if not t:
        conn.close()
        return {"ok": False}
    new_name = t['name']  # tanpa tambahan (copy)
    conn.execute("""
        INSERT INTO todos(user_id,name,icon,priority,xp_reward,gold_reward,due_date,notes)
        VALUES(?,?,?,?,?,?,?,?)
    """, (user_id, new_name, t['icon'], t['priority'], t['xp_reward'], t['gold_reward'], t['due_date'], t['notes']))
    conn.commit()
    conn.close()
    return {"ok": True}

def duplicate_sport_activity(user_id, activity_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    a = conn.execute("SELECT * FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id)).fetchone()
    if not a:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_sport_activity_not_found")}
    new_name = a['name']  # tanpa tambahan (copy)
    conn.execute("""
        INSERT INTO sport_activities(
            user_id, name, sport_type, icon, difficulty,
            xp_reward, gold_reward, sport_points_reward, notes
        ) VALUES(?,?,?,?,?,?,?,?,?)
    """, (user_id, new_name, a['sport_type'], a['icon'], a['difficulty'],
          a['xp_reward'], a['gold_reward'], a['sport_points_reward'], a['notes']))
    conn.commit()
    conn.close()
    return {"ok": True}

# ── Shop data ─────────────────────────────────────────────────────────────────

SHOP_ITEMS = {
    # ── Weapons ──
    "wooden_sword":    {"name": "Wooden Sword",    "icon": "🗡️", "cost": 50,
                        "type": "weapon",    "desc": "Starter blade",
                        "buff": {"boss_dmg": 2},
                        "buff_desc": "+2 Boss Damage"},
    "enchanted_bow":   {"name": "Enchanted Bow",   "icon": "🏹", "cost": 180,
                        "type": "weapon",    "desc": "Ranged power",
                        "buff": {"boss_dmg": 6},
                        "buff_desc": "+6 Boss Damage"},
    "trident":         {"name": "Trident",         "icon": "🔱", "cost": 350,
                        "type": "weapon",    "desc": "Legendary weapon",
                        "buff": {"boss_dmg": 10},
                        "buff_desc": "+10 Boss Damage"},
    "iron_sword":      {"name": "Iron Sword",      "icon": "🗡️", "cost": 100,
                        "type": "weapon",    "desc": "Sharp blade",
                        "buff": {"crit_chance": 8},
                        "buff_desc": "+8% Critical Chance"},
    "diamond_sword":   {"name": "Diamond Sword",   "icon": "💎", "cost": 300,
                        "type": "weapon",    "desc": "Powerful strike",
                        "buff": {"crit_chance": 15},
                        "buff_desc": "+15% Critical Chance"},
    "netherite_sword": {"name": "Netherite Sword", "icon": "⚔️", "cost": 600,
                        "type": "weapon",    "desc": "Legendary blade",
                        "buff": {"crit_chance": 20, "boss_dmg": 5},
                        "buff_desc": "+20% Critical Chance, +5 Boss DMG"},

    # ── Armor ──
    "shield":          {"name": "Shield",          "icon": "🛡️", "cost": 120,
                        "type": "armor",     "desc": "Reduces HP damage",
                        "buff": {"hp_reduc": 8},
                        "buff_desc": "-8 per HP hit taken"},
    "golden_boots":    {"name": "Golden Boots",    "icon": "👢", "cost": 140,
                        "type": "armor",     "desc": "Swift & rich",
                        "buff": {"gold_pct": 10},
                        "buff_desc": "+10% Gold earned"},
    "diamond_armor":   {"name": "Diamond Armor",   "icon": "💎", "cost": 300,
                        "type": "armor",     "desc": "Max protection",
                        "buff": {"hp_reduc": 15},
                        "buff_desc": "-15 per HP hit taken"},
    "elytra":          {"name": "Elytra Wings",    "icon": "🪽", "cost": 500,
                        "type": "armor",     "desc": "Glide & grow",
                        "buff": {"xp_pct": 10},
                        "buff_desc": "+10% XP all sources"},
    "tower_shield":    {"name": "Tower Shield",    "icon": "🛡️", "cost": 200,
                        "type": "armor",    "desc": "Great defense",
                        "buff": {"block_strength": 15},
                        "buff_desc": "+15 Block Strength"},
    "guardian_chestplate": {"name": "Guardian Chestplate", "icon": "🛡️", "cost": 400,
                        "type": "armor",    "desc": "Guardian armor",
                        "buff": {"block_chance": 10, "block_strength": 15},
                        "buff_desc": "+10% Block Chance, +15 Block Strength"},
    "diamond_chestplate": {"name": "Diamond Chestplate", "icon": "💎", "cost": 600,
                        "type": "armor",    "desc": "Diamond protection",
                        "buff": {"block_chance": 15, "block_strength": 20},
                        "buff_desc": "+15% Block Chance, +20 Block Strength"},

    # ── Tools ──
    "iron_pickaxe":    {"name": "Iron Pickaxe",    "icon": "⛏️", "cost": 100,
                        "type": "tool",      "desc": "Mine habits faster",
                        "buff": {"xp_pct": 8},
                        "buff_desc": "+8% XP from habits"},
    "compass":         {"name": "Compass",         "icon": "🧭", "cost": 80,
                        "type": "tool",      "desc": "Navigate to gold",
                        "buff": {"gold_pct": 6},
                        "buff_desc": "+6% Gold earned"},
    "spyglass":        {"name": "Spyglass",        "icon": "🔭", "cost": 90,
                        "type": "tool",      "desc": "Scout ahead",
                        "buff": {},
                        "buff_desc": "Reveal boss stats"},

    # ── Special ──
    "ice_block":       {"name": "Ice Block",       "icon": "🧊", "cost": 25,
                        "type": "consumable", "desc": "Freeze Daily streak (1 slot)",
                        "buff": {},
                        "buff_desc": "Use: +1 Freeze Slot for a Daily"},
    "blaze_rod":       {"name": "Blaze Rod",       "icon": "🔥", "cost": 160,
                        "type": "special",   "desc": "Nether fire",
                        "buff": {"boss_dmg": 4},
                        "buff_desc": "+4 Boss Damage"},
    "totem":           {"name": "Totem of Life",   "icon": "🗿", "cost": 400,
                        "type": "legendary", "desc": "Auto-revive from death",
                        "buff": {"revive": True},
                        "buff_desc": "Auto-revive once at 30% HP"},

    # ── Consumables (HP & MP) ──
    "golden_apple":    {"name": "Golden Apple",     "icon": "🍎", "cost": 50,
                        "type": "consumable", "desc": "Restore 25 HP",
                        "buff": {},
                        "buff_desc": "Use: +25 HP"},
    "enchanted_apple": {"name": "Enchanted Apple",  "icon": "🍏", "cost": 200,
                        "type": "consumable", "desc": "Restore 100 HP",
                        "buff": {},
                        "buff_desc": "Use: +100 HP"},
    "health_potion":   {"name": "Health Potion",    "icon": "❤️‍🩹", "cost": 100,
                        "type": "consumable", "desc": "Restore 50 HP",
                        "buff": {},
                        "buff_desc": "Use: +50 HP"},
    "greater_health_potion": {"name": "Greater Health Potion", "icon": "❤️", "cost": 150,
                        "type": "consumable", "desc": "Restore 75 HP",
                        "buff": {},
                        "buff_desc": "Use: +75 HP"},
    "mana_potion":     {"name": "Mana Potion",      "icon": "💙", "cost": 80,
                        "type": "consumable", "desc": "Restore 15 MP",
                        "buff": {},
                        "buff_desc": "Use: +15 MP"},
    "greater_mana_potion": {"name": "Greater Mana Potion", "icon": "💎", "cost": 200,
                        "type": "consumable", "desc": "Restore 35 MP",
                        "buff": {},
                        "buff_desc": "Use: +35 MP"},
    "super_mana_potion": {"name": "Super Mana Potion", "icon": "🔮", "cost": 500,
                        "type": "consumable", "desc": "Restore 80 MP",
                        "buff": {},
                        "buff_desc": "Use: +80 MP"},
    "elixir":          {"name": "Elixir of Life",   "icon": "🧪", "cost": 1000,
                        "type": "consumable", "desc": "Restore 80 HP & 40 MP",
                        "buff": {},
                        "buff_desc": "Use: +80 HP & +40 MP"},
    "ender_pearl":     {"name": "Ender Pearl",      "icon": "🔮", "cost": 300,
                        "type": "consumable", "desc": "Permanently increase Max MP",
                        "buff": {},
                        "buff_desc": "Use: +30 Max MP (permanent)"},

    # ── Legendary ──
    "nether_star":     {"name": "Nether Star",     "icon": "⭐", "cost": 600,
                        "type": "legendary",
                        "desc": "Power of the Nether",
                        "buff": {"xp_pct": 12, "gold_pct": 12, "boss_dmg": 6},
                        "buff_desc": "+12% XP, +12% Gold, +6 Boss DMG"},
    "beacon":          {"name": "Beacon",          "icon": "🏮", "cost": 1000,
                        "type": "legendary", "desc": "Strongest relic",
                        "buff": {"xp_pct": 15, "gold_pct": 15,
                                 "boss_dmg": 10, "hp_reduc": 5},
                        "buff_desc": "+15% XP, +15% Gold, +10 DMG, -5 HP taken"},
}

PETS_DATA = {
    "wolf":     {"name": "Wolf", "icon": "🐺", "cost": 150,
                 "bonus": "+6% XP",                     
                 "base_buff": {"xp_pct": 6}},
    "cat":      {"name": "Cat", "icon": "🐱", "cost": 120,
                 "bonus": "-6 HP loss",                 
                 "base_buff": {"hp_reduc": 6}},
    "parrot":   {"name": "Parrot", "icon": "🦜", "cost": 140,
                 "bonus": "+4% Gold",                   
                 "base_buff": {"gold_pct": 4}},
    "panda":    {"name": "Panda", "icon": "🐼", "cost": 240,
                 "bonus": "+10% XP",                     
                 "base_buff": {"xp_pct": 10}},
    "fox":      {"name": "Fox", "icon": "🦊", "cost": 180,
                 "bonus": "+8% Gold",                   
                 "base_buff": {"gold_pct": 8}},
    "bee":      {"name": "Bee", "icon": "🐝", "cost": 110,
                 "bonus": "-4 HP loss",                 
                 "base_buff": {"hp_reduc": 4}},
    "dragon":   {"name": "Dragon", "icon": "🐉", "cost": 600,
                 "bonus": "+15% XP, +4 boss dmg",        
                 "base_buff": {"xp_pct": 15, "boss_dmg": 4}},
    "turtle":   {"name": "Turtle", "icon": "🐢", "cost": 130,
                 "bonus": "-8 HP loss",                 
                 "base_buff": {"hp_reduc": 8}},
    "axolotl":  {"name": "Axolotl", "icon": "🦎", "cost": 200,
                 "bonus": "-2 HP loss",                 
                 "base_buff": {"hp_reduc": 2}},
    "enderman": {"name": "Enderman", "icon": "👾", "cost": 400,
                 "bonus": "+12% XP, +4% Gold, +2 boss dmg", 
                 "base_buff": {"xp_pct": 12, "gold_pct": 4, "boss_dmg": 2}},
    "phoenix":     {"name": "Phoenix",   "icon": "🐦‍🔥", "cost": 800,
                    "bonus": "+10% XP, +5% Gold, +2 boss dmg",
                    "base_buff": {"xp_pct": 10, "gold_pct": 5, "boss_dmg": 2}},
    "unicorn":     {"name": "Unicorn",   "icon": "🦄", "cost": 650,
                    "bonus": "+8% XP, +8% Gold",
                    "base_buff": {"xp_pct": 8, "gold_pct": 8}},
    "griffin":     {"name": "Griffin",   "icon": "🦅", "cost": 700,
                    "bonus": "+10% XP, -5 HP loss",
                    "base_buff": {"xp_pct": 10, "hp_reduc": 5}},
    "mermaid":     {"name": "Mermaid",   "icon": "🧜‍♀️", "cost": 500,
                    "bonus": "+6% Gold, -8 HP loss",
                    "base_buff": {"gold_pct": 6, "hp_reduc": 8}},
    "slime":       {"name": "Slime",     "icon": "🟢", "cost": 80,
                    "bonus": "+2% Gold, -2 HP loss",
                    "base_buff": {"gold_pct": 2, "hp_reduc": 2}},
    "ghast":       {"name": "Ghost",     "icon": "👻", "cost": 150,
                    "bonus": "+4% XP, -4 HP loss",
                    "base_buff": {"xp_pct": 4, "hp_reduc": 4}},
    "skeleton":    {"name": "Skeleton",  "icon": "💀", "cost": 120,
                    "bonus": "+3% Gold, +1 boss dmg",
                    "base_buff": {"gold_pct": 3, "boss_dmg": 1}},
    "zombie":      {"name": "Zombie",    "icon": "🧟", "cost": 100,
                    "bonus": "+2% XP, +1 boss dmg",
                    "base_buff": {"xp_pct": 2, "boss_dmg": 1}},
    "creeper":     {"name": "Creeper",   "icon": "💥", "cost": 90,
                    "bonus": "+2% Gold, -2 HP loss",
                    "base_buff": {"gold_pct": 2, "hp_reduc": 2}},
}

BOSSES = {
    # Beginner
    "zombie":         {"name": "Zombie",          "icon": "🧟",
                       "tier": "beginner", "hp": 200,  "atk": 5,
                       "xp": 80,   "gold": 20,  "min_level": 1},
    "skeleton":       {"name": "Skeleton Archer", "icon": "💀",
                       "tier": "beginner", "hp": 300,  "atk": 8,
                       "xp": 120,  "gold": 30,  "min_level": 1},
    "creeper":        {"name": "Creeper",         "icon": "💥",
                       "tier": "beginner", "hp": 250,  "atk": 12,
                       "xp": 100,  "gold": 25,  "min_level": 2},
    # Normal
    "zombie_king":    {"name": "Zombie King",     "icon": "👑",
                       "tier": "normal",   "hp": 600,  "atk": 15,
                       "xp": 250,  "gold": 60,  "min_level": 3},
    "skeleton_lord":  {"name": "Skeleton Lord",   "icon": "☠️",
                       "tier": "normal",   "hp": 800,  "atk": 20,
                       "xp": 350,  "gold": 80,  "min_level": 5},
    "blaze_lord":     {"name": "Blaze Lord",      "icon": "🔥",
                       "tier": "normal",   "hp": 700,  "atk": 18,
                       "xp": 300,  "gold": 70,  "min_level": 4},
    # Hard
    "iron_golem":     {"name": "Iron Golem Boss", "icon": "⚙️",
                       "tier": "hard",    "hp": 1500, "atk": 25,
                       "xp": 600,  "gold": 150, "min_level": 8},
    "creeper_god":    {"name": "Creeper God",     "icon": "💣",
                       "tier": "hard",    "hp": 1200, "atk": 30,
                       "xp": 700,  "gold": 180, "min_level": 10},
    "spider_queen":   {"name": "Spider Queen",    "icon": "🕷️",
                       "tier": "hard",    "hp": 1000, "atk": 22,
                       "xp": 500,  "gold": 120, "min_level": 7},
    # Elite
    "wither":         {"name": "The Wither",      "icon": "💀",
                       "tier": "elite",   "hp": 2500, "atk": 40,
                       "xp": 1200, "gold": 300, "min_level": 15},
    "ender_dragon":   {"name": "Ender Dragon",    "icon": "🐲",
                       "tier": "elite",   "hp": 3000, "atk": 50,
                       "xp": 1500, "gold": 400, "min_level": 20},
    # Legendary
    "elder_guardian": {"name": "Elder Guardian",  "icon": "👁️",
                       "tier": "legendary", "hp": 5000, "atk": 70,
                       "xp": 3000, "gold": 800, "min_level": 30},
    "herobrine":      {"name": "Herobrine",       "icon": "👻",
                       "tier": "legendary", "hp": 8000, "atk": 100,
                       "xp": 5000, "gold": 1500,"min_level": 50},
}

BOSS_TIER_ORDER = ["beginner", "normal", "hard", "elite", "legendary"]
BOSS_TIER_COLOR = {
    "beginner":  "#7bbf3e",
    "normal":    "#f0a800",
    "hard":      "#e05050",
    "elite":     "#a97fff",
    "legendary": "#ff6b00",
}

SECURITY_QUESTIONS = [
    "Apa nama hewan peliharaan pertama Anda?",
    "Apa nama sekolah dasar Anda?",
    "Apa nama ibu kota tempat Anda lahir?",
    "Siapa tokoh idola Anda?",
    "Apa makanan favorit Anda?",
    "Apa merek handphone pertama Anda?",
    "Apa nama jalan tempat Anda tinggal saat kecil?",
]

# ── Inventory / Shop ──────────────────────────────────────────────────────────

def get_inventory(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM inventory WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buy_item(user_id, item_id):
    item = SHOP_ITEMS.get(item_id)
    if not item:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_not_found")}
    u = get_user(user_id)
    if u["gold"] < item["cost"]:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_gold_insufficient", cost=item['cost'])}
    conn = get_conn()
    ex = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=?",
        (user_id, item_id)).fetchone()
    if ex and item["type"] not in ("consumable",):
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_already_owned")}
    if ex:
        conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?",
                     (ex["id"],))
    else:
        conn.execute(
            "INSERT INTO inventory(user_id,item_id,item_type) VALUES(?,?,?)",
            (user_id, item_id, item["type"]))
    conn.execute("UPDATE users SET gold=gold-? WHERE id=?",
                 (item["cost"], user_id))
    conn.commit()
    conn.close()
    update_total_spent(user_id, item["cost"])
    recalculate_all_buffs(user_id)
    log_activity(user_id, "buy", tr_db(user_id=user_id, key="log_buy", item=item['name'], gold=item['cost']), 0, -item["cost"])
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_item_bought", icon=item['icon'], name=item['name'], buff=item['buff_desc'])}


def use_item(user_id, item_id):
    item = SHOP_ITEMS.get(item_id)
    if not item or item["type"] != "consumable":
        return {"ok": False}
    conn = get_conn()
    inv = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=? AND quantity>0",
        (user_id, item_id)
    ).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_not_found")}
    
    hp_map = {
        "golden_apple": 25,
        "enchanted_apple": 100,
        "health_potion": 50,
        "greater_health_potion": 75
    }
    mp_map = {
        "mana_potion": 15,
        "greater_mana_potion": 35,
        "super_mana_potion": 80,
        "elixir": 40
    }
    max_mp_map = {
        "ender_pearl": 30
    }
    
    restore_hp = hp_map.get(item_id, 0)
    restore_mp = mp_map.get(item_id, 0)
    restore_max_mp = max_mp_map.get(item_id, 0)
    
    if restore_hp == 0 and restore_mp == 0 and restore_max_mp == 0:
        conn.close()
        return {"ok": False, "msg": "Item tidak bisa digunakan."}
    
    msg_parts = []
    
    if restore_hp > 0:
        conn.execute("UPDATE users SET hp = MIN(max_hp, hp + ?) WHERE id=?", (restore_hp, user_id))
        msg_parts.append(f"+{restore_hp} HP")
    
    if restore_mp > 0:
        conn.execute("UPDATE users SET mp = MIN(max_mp, mp + ?) WHERE id=?", (restore_mp, user_id))
        msg_parts.append(f"+{restore_mp} MP")
    
    if restore_max_mp > 0:
        # Tambah Max MP permanen + isi MP sebesar jumlah yang sama agar langsung terasa
        conn.execute(
            "UPDATE users SET max_mp = max_mp + ?, mp = mp + ? WHERE id=?",
            (restore_max_mp, restore_max_mp, user_id)
        )
        msg_parts.append(f"+{restore_max_mp} Max MP (permanen)")
    
    conn.execute("UPDATE inventory SET quantity = quantity - 1 WHERE id=?", (inv["id"],))
    conn.commit()
    conn.close()
    
    msg = " & ".join(msg_parts)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_item_used", icon=item['icon'], restore=msg)}

@retry_on_lock
def sell_item(user_id, item_id, quantity=1):
    """
    Menjual item kembali ke shop dengan harga 10% dari harga asli.
    - item_id: ID item di inventory (bukan shop item_id)
    - quantity: jumlah yang dijual (default 1)
    """
    conn = get_conn()
    try:
        # Ambil data item dari inventory
        inv = conn.execute(
            "SELECT * FROM inventory WHERE id = ? AND user_id = ?",
            (item_id, user_id)
        ).fetchone()
        if not inv:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_not_found")}
        
        # Ambil data shop item
        shop_item = SHOP_ITEMS.get(inv["item_id"])
        if not shop_item:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_not_found")}
        
        # Hitung harga jual (10% dari harga beli)
        sell_price = shop_item["cost"] * 0.1
        sell_price = max(1, int(sell_price))  # minimal 1 Gold
        
        # Cek quantity
        if inv["quantity"] < quantity:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_item_insufficient_quantity")}
        
        # Kurangi quantity atau hapus item
        new_quantity = inv["quantity"] - quantity
        if new_quantity <= 0:
            conn.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        else:
            conn.execute("UPDATE inventory SET quantity = quantity - ? WHERE id = ?", (quantity, item_id))
        
        # Tambahkan gold ke user
        total_gold = sell_price * quantity
        conn.execute("UPDATE users SET gold = gold + ? WHERE id = ?", (total_gold, user_id))
        conn.commit()
    
        try:
            recalculate_all_buffs(user_id)
        except Exception as e:
            log_crash(f"recalculate_all_buffs failed after selling item: {e}")

        # Catat aktivitas
        log_activity(
            user_id,
            "sell_item",
            tr_db(user_id=user_id, key="log_sell_item", name=shop_item['name'], qty=quantity, gold=total_gold),
            0,
            total_gold
        )
        
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_item_sold", name=shop_item['name'], qty=quantity, gold=total_gold)}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e)}
    finally:
        conn.close()

# ── Pets ──────────────────────────────────────────────────────────────────────
def get_user_pets(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM user_pets WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def adopt_pet(user_id, pet_id):
    pet = PETS_DATA.get(pet_id)
    if not pet:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_found")}
    u = get_user(user_id)
    if u["gold"] < pet["cost"]:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_gold_insufficient", cost=pet['cost'])}
    conn = get_conn()
    try:
        if conn.execute("SELECT 1 FROM user_pets WHERE user_id=? AND pet_id=?", (user_id, pet_id)).fetchone():
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_already_owned")}
        conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (pet["cost"], user_id))
        conn.execute("INSERT INTO user_pets(user_id, pet_id, hunger, happiness) VALUES(?,?,100,50)", (user_id, pet_id))
        conn.commit()
    finally:
        conn.close()
    check_achievements(user_id, "pet_adopt", 1)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_pet_adopted", icon=pet['icon'], name=pet['name'])}

def equip_pet(user_id, pet_id):
    """Equip pet (aktifkan). Maksimal 2 pet jika user level >=25, selain itu maksimal 1.
       Jika sudah mencapai batas, akan mengganti pet aktif yang paling lama (ID terkecil)."""
    conn = get_conn()
    try:
        # Ambil level user
        user = conn.execute("SELECT level FROM users WHERE id=?", (user_id,)).fetchone()
        if not user:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_user_not_found")}
        user_level = user["level"]
        max_pets = 2 if user_level >= 25 else 1
        
        # Cek apakah pet yang akan di-equip sudah aktif?
        pet = conn.execute(
            "SELECT is_active FROM user_pets WHERE user_id=? AND pet_id=?",
            (user_id, pet_id)
        ).fetchone()
        if not pet:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_found")}
        if pet["is_active"]:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_already_active")}
        
        # Hitung jumlah pet yang sudah aktif
        active_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM user_pets WHERE user_id=? AND is_active=1",
            (user_id,)
        ).fetchone()["cnt"]
        
        if active_count >= max_pets:
            # Cari pet aktif yang paling lama (ID terkecil) untuk diganti
            oldest_active = conn.execute(
                "SELECT id FROM user_pets WHERE user_id=? AND is_active=1 ORDER BY id LIMIT 1",
                (user_id,)
            ).fetchone()
            if oldest_active:
                # Nonaktifkan pet lama
                conn.execute("UPDATE user_pets SET is_active=0 WHERE id=?", (oldest_active["id"],))
            else:
                # Seharusnya tidak terjadi
                return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_equip_fail")}
        
        # Aktifkan pet baru
        conn.execute("UPDATE user_pets SET is_active=1 WHERE user_id=? AND pet_id=?", (user_id, pet_id))
        conn.commit()
    finally:
        conn.close()
    
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_pet_equipped", name=pet_id)}

def unequip_pet(user_id, pet_id):
    """Nonaktifkan pet (unequip). Hanya bisa dilakukan jika pet sedang aktif."""
    conn = get_conn()
    try:
        # Cek apakah pet ada dan aktif
        pet = conn.execute(
            "SELECT is_active FROM user_pets WHERE user_id=? AND pet_id=?",
            (user_id, pet_id)
        ).fetchone()
        if not pet:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_found")}
        if not pet["is_active"]:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_active")}
        
        # Nonaktifkan pet
        conn.execute(
            "UPDATE user_pets SET is_active=0 WHERE user_id=? AND pet_id=?",
            (user_id, pet_id)
        )
        conn.commit()
    finally:
        conn.close()
    
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_pet_unequipped", name=pet_id)}

@retry_on_lock
def feed_pet(user_id, pet_id):
    pet = get_user_pet_by_id(user_id, pet_id)
    if not pet:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_found")}
    
    u = get_user(user_id)
    cost = 30
    if u["gold"] < cost:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_gold_insufficient", cost=cost)}
    
    # Ambil nama pet dengan aman
    pet_data = PETS_DATA.get(pet_id, {})
    pet_name = pet_data.get('name', f"Pet-{pet_id}")
    
    conn = get_conn()
    try:
        conn.execute("UPDATE user_pets SET hunger=100, last_fed=? WHERE id=?", (local_now().isoformat(), pet["id"]))
        conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
        conn.commit()
    finally:
        conn.close()
    
    # Kembalikan data mentah, BUKAN string terjemahan
    return {
        "ok": True,
        "name": pet_name,
        "cost": cost
    }

@retry_on_lock
def train_pet(user_id, pet_id):
    MAX_PET_LEVEL = 20
    pet = get_user_pet_by_id(user_id, pet_id)
    if not pet:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_not_found")}
    
    level = pet["level"]  # ← WAJIB, ambil level dari pet
    
    if level >= MAX_PET_LEVEL:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_max_level", max=MAX_PET_LEVEL)}
    
    if pet["hunger"] < 20:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_pet_hungry")}
    
    u = get_user(user_id)
    pet_data = PETS_DATA.get(pet_id, {})
    pet_name = pet_data.get('name', f"Pet-{pet_id}")
    
    cost = 25 + (level - 1) * 5
    if u["gold"] < cost:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_gold_insufficient", cost=cost)}
    
    needed = level * 100
    exp_gain = max(5, int(needed * 0.05))
    
    conn = get_conn()
    leveled = False
    try:
        new_hunger = max(0, pet["hunger"] - 20)
        conn.execute("UPDATE user_pets SET hunger=? WHERE id=?", (new_hunger, pet["id"]))
        leveled = add_pet_exp(conn, pet["id"], exp_gain)
        conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
        conn.commit()
    finally:
        conn.close()
    
    new_level = level
    if leveled:
        updated_pet = get_user_pet_by_id(user_id, pet_id)
        new_level = updated_pet["level"] if updated_pet else level + 1
        add_notification(user_id, tr_db(user_id=user_id, key="db_pet_level_up", name=pet_name, level=new_level), "levelup")
        recalculate_all_buffs(user_id)
    
    return {
        "ok": True,
        "name": pet_name,
        "exp_gained": exp_gain,
        "cost": cost,
        "leveled_up": leveled,
        "new_level": new_level
    }

def add_pet_exp(conn, pet_row_id, amount):
    """Return True jika level naik, False jika tidak"""
    pet = conn.execute("SELECT user_id, exp, level FROM user_pets WHERE id=?", (pet_row_id,)).fetchone()
    if not pet:
        return False
    new_exp = pet["exp"] + amount
    new_level = pet["level"]
    needed = pet["level"] * 100
    leveled = False
    while new_exp >= needed:
        new_exp -= needed
        new_level += 1
        needed = new_level * 100
        leveled = True
    conn.execute("UPDATE user_pets SET exp=?, level=? WHERE id=?", (new_exp, new_level, pet_row_id))
    return leveled

def get_user_pet_by_id(user_id, pet_id):
    conn = get_conn()
    pet = conn.execute("SELECT * FROM user_pets WHERE user_id=? AND pet_id=?", (user_id, pet_id)).fetchone()
    conn.close()
    return pet

# ── Party / Boss ──────────────────────────────────────────────────────────────

def create_guild(leader_id, name, description=""):
    u = get_user(leader_id)
    if u.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_admin_cannot_guild")}
    conn = get_conn()
    gid = get_next_guild_id()
    conn.execute("INSERT INTO guilds(id, name, description, leader_id) VALUES(?,?,?,?)",
                 (gid, name, description, leader_id))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (gid, leader_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (gid, leader_id))
    conn.commit()
    conn.close()
    check_achievements(leader_id, "join_guild", 1)
    return {"ok": True, "guild_id": gid, "msg": tr_db(user_id=leader_id, key="db_guild_created", name=name, id=gid)}


# ── Guild Request Join ───────────────────────────────────
def send_guild_request(user_id, guild_id):
    u = get_user(user_id)
    if u.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_admin_cannot_guild")}
    conn = get_conn()
    guild = conn.execute("SELECT id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_not_found")}
    # Cek apakah sudah member
    existing = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_already_in_guild")}
    # Cek apakah sudah ada request pending
    pending = conn.execute("SELECT 1 FROM guild_requests WHERE guild_id=? AND user_id=? AND status='pending'", (guild_id, user_id)).fetchone()
    if pending:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_request_pending")}
    conn.execute("INSERT INTO guild_requests(guild_id, user_id) VALUES(?,?)", (guild_id, user_id))
    conn.commit()
    # Ambil leader_id sebelum conn ditutup
    leader = conn.execute("SELECT leader_id FROM guilds WHERE id=?", (guild_id,)).fetchone()
    leader_id = leader["leader_id"] if leader else None
    conn.close()
    # Notifikasi ke leader (setelah conn ditutup agar tidak nested)
    if leader_id:
        add_notification(leader_id, tr_db(user_id=leader_id, key="db_guild_request_notif", name=get_user(user_id)['display_name'], guild=guild['name']), "info")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_guild_request_sent")}

def get_guild_requests(guild_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT gr.*, u.display_name, u.username
        FROM guild_requests gr
        JOIN users u ON gr.user_id = u.id
        WHERE gr.guild_id=? AND gr.status='pending'
    """, (guild_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def accept_guild_request(guild_id, leader_id, request_id):
    conn = get_conn()
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_request_accept_only_leader")}
    
    # Cek jumlah member
    count = conn.execute("SELECT COUNT(*) FROM guild_members WHERE guild_id=?", (guild_id,)).fetchone()[0]
    if count >= 20:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_full")}
    
    req = conn.execute("SELECT * FROM guild_requests WHERE id=? AND guild_id=? AND status='pending'", (request_id, guild_id)).fetchone()
    if not req:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_request_not_found")}
    conn.execute("UPDATE guild_requests SET status='accepted' WHERE id=?", (request_id,))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (guild_id, req["user_id"]))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (guild_id, req["user_id"]))
    conn.commit()
    conn.close()
    check_achievements(req["user_id"], "join_guild", 1)
    add_notification(req["user_id"], tr_db(user_id=req["user_id"], key="db_guild_request_accepted_notif", name=guild['name']), "success")
    return {"ok": True, "msg": tr_db(user_id=leader_id, key="db_guild_member_accepted")}

def reject_guild_request(guild_id, leader_id, request_id):
    conn = get_conn()
    guild = conn.execute("SELECT leader_id FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_request_reject_only_leader")}
    conn.execute("UPDATE guild_requests SET status='rejected' WHERE id=? AND guild_id=?", (request_id, guild_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=leader_id, key="db_guild_request_rejected")}

def get_guild(guild_id):
    conn = get_conn()
    g = conn.execute("SELECT * FROM guilds WHERE id=?",
                     (guild_id,)).fetchone()
    if not g:
        conn.close()
        return {}
    members = conn.execute(
        "SELECT u.id,u.display_name,u.level,u.avatar_class,"
        "u.avatar_emoji,u.hp,u.max_hp"
        " FROM users u JOIN guild_members gm ON u.id=gm.user_id"
        " WHERE gm.guild_id=?",
        (guild_id,)).fetchall()
    boss = conn.execute("SELECT * FROM boss_battles WHERE guild_id=? AND status='active'", (guild_id,)).fetchone()
    conn.close()
    return {
        "guild":   dict(g),
        "members": [dict(m) for m in members],
        "boss":    dict(boss) if boss else None,
    }

def get_next_guild_id():
    conn = get_conn()
    # Cari ID terkecil yang tidak terpakai
    used = conn.execute("SELECT id FROM guilds ORDER BY id").fetchall()
    used_ids = {row[0] for row in used}
    next_id = 1
    while next_id in used_ids:
        next_id += 1
    conn.close()
    return next_id

def start_boss(guild_id, boss_id, user_data, participant_ids=None):
    """
    Memulai boss battle dengan peserta tertentu.
    user_data: dict user leader (harus berisi id, level, guild_id)
    participant_ids: list of user_id (termasuk leader). Jika None, hanya leader.
    """
    import json

    # ── FALLBACK: Jika user_data bukan dict, coba ambil dari database ──
    if not isinstance(user_data, dict):
        try:
            uid = int(user_data)
            conn = get_conn()
            row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
            conn.close()
            if row:
                user_data = dict(row)
            else:
                return {"ok": False, "msg": "User tidak ditemukan."}
        except:
            return {"ok": False, "msg": "Data user tidak valid."}
    
    # ── Validasi user_data ──
    if not user_data:
        return {"ok": False, "msg": "Data user kosong."}
    if not isinstance(user_data, dict):
        return {"ok": False, "msg": f"Data user bukan dict: {type(user_data)}"}
    
    user_id = user_data.get("id")
    if not user_id:
        return {"ok": False, "msg": "ID user tidak ditemukan dalam data."}
    try:
        user_id = int(user_id)
    except:
        return {"ok": False, "msg": "ID user tidak valid."}
    if user_id <= 0:
        return {"ok": False, "msg": "ID user harus positif."}
    
    # ── Ambil data boss ──
    boss = BOSSES.get(boss_id)
    if not boss:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_not_found")}
    
    conn = get_conn()
    try:
        # ── CEK LIMIT BOSS PER HARI (GUILD) ──
        from datetime import date
        today = date.today().isoformat()
        guild = conn.execute(
            "SELECT boss_defeated_today, boss_defeated_date FROM guilds WHERE id=?",
            (guild_id,)
        ).fetchone()
        if guild:
            if guild["boss_defeated_date"] == today:
                if guild["boss_defeated_today"] >= 3:
                    conn.close()
                    return {"ok": False, "msg": "Guild sudah mengalahkan 3 boss hari ini. Tunggu besok!"}
            else:
                # Reset counter jika hari berbeda
                conn.execute(
                    "UPDATE guilds SET boss_defeated_today=0, boss_defeated_date=? WHERE id=?",
                    (today, guild_id)
                )
                conn.commit()
        else:
            # Guild tidak ditemukan (seharusnya tidak terjadi)
            conn.close()
            return {"ok": False, "msg": "Guild tidak ditemukan."}

        # ── Cek apakah leader berada di guild yang benar ──
        if user_data.get("guild_id") != guild_id:
            conn.close()
            return {"ok": False, "msg": "Kamu tidak berada di guild ini."}
        
        # ── Cek level leader ──
        if user_data["level"] < boss.get("min_level", 1):
            conn.close()
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_level_too_low", min_lvl=boss['min_level'])}
        
        # ── Cek boss aktif ──
        if conn.execute("SELECT 1 FROM boss_battles WHERE guild_id=? AND status='active'", (guild_id,)).fetchone():
            conn.close()
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_already_active")}
        
        # ── Proses peserta ──
        if participant_ids is None:
            participant_ids = [user_id]
        
        valid_participants = []
        for pid in participant_ids:
            try:
                pid = int(pid)
            except:
                continue
            if pid <= 0:
                continue
            p_row = conn.execute("SELECT id, level, guild_id FROM users WHERE id=?", (pid,)).fetchone()
            if p_row and p_row["guild_id"] == guild_id:
                p_level = p_row["level"]
                if p_level >= boss.get("min_level", 1) and p_level <= boss.get("max_level", 999):
                    valid_participants.append(pid)
        
        # Leader wajib ada
        if user_id not in valid_participants:
            valid_participants.insert(0, user_id)
        
        # Maksimal 5
        valid_participants = valid_participants[:5]
        
        # ── Insert boss battle ──
        tier_crit = {"beginner": 10, "normal": 15, "hard": 25, "elite": 35, "legendary": 50}
        crit_chance = tier_crit.get(boss["tier"], 15)
        
        participants_str = [str(uid) for uid in valid_participants]
        participants_json = json.dumps(participants_str)
        attack_counts_json = json.dumps({str(uid): 0 for uid in valid_participants})
        
        conn.execute(
            "INSERT INTO boss_battles(guild_id,boss_id,boss_name,boss_icon,boss_tier,"
            "boss_hp,boss_max_hp,boss_attack,boss_crit_chance,participants,attack_counts,raid_leader_id)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (guild_id, boss_id, boss["name"], boss["icon"], boss["tier"],
             boss["hp"], boss["hp"], boss["atk"], crit_chance,
             participants_json, attack_counts_json, user_id)
        )
        conn.execute("UPDATE guilds SET quest_id=? WHERE id=?", (boss_id, guild_id))
        conn.commit()
        conn.close()
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_boss_started", icon=boss['icon'], name=boss['name'], tier=boss['tier'].upper())}
    
    except Exception as e:
        conn.rollback()
        conn.close()
        return {"ok": False, "msg": f"Error: {str(e)}"}

@retry_on_lock
def attack_boss(user_id, guild_id, action="light"):
    import random
    import json
    from datetime import datetime, timedelta, date

    conn = None
    try:
        conn = get_conn()
        
        # Ambil data user
        u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            return {"ok": False, "msg": "User not found"}
        u = dict(u)
        if u["hp"] <= 0:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_hp_zero")}
        if u["mp"] < 0:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_mp_invalid")}

        # Ambil data boss
        boss_row = conn.execute(
            "SELECT * FROM boss_battles WHERE guild_id=? AND status='active'", (guild_id,)
        ).fetchone()
        if not boss_row:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_no_active")}
        boss = dict(boss_row)

        # Cek peserta
        participants_data = boss.get("participants")
        participants = json.loads(participants_data) if participants_data else []
        participants = [str(p) for p in participants]
        if str(user_id) not in participants:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_raid_not_participant")}

        # Ambil buff skill
        buff_row = conn.execute(
            "SELECT skill_buff_data FROM users WHERE id=?", (user_id,)
        ).fetchone()
        buffs = json.loads(buff_row["skill_buff_data"]) if buff_row and buff_row["skill_buff_data"] else {}
        shield_active = buffs.get("shield_active", False)

        # Hitung damage maksimum user
        base_damage = 25
        user_max_dmg = int(base_damage + u.get("boss_damage_bonus", 0))
        if u.get("is_admin", 0):
            user_max_dmg *= 10
        if user_max_dmg < 1:
            user_max_dmg = 1

        ultimate_multipliers = {
            "warrior": 3,
            "mage": 4,
            "archer": 3.5,
            "healer": 2.5,
            "rogue": 5
        }
        cls = u.get("avatar_class", "warrior")

        # ── Action handling ──
        if action == "block":
            # ── CEK MP ──
            if u["mp"] < 5:
                return {"ok": False, "msg": tr_db(user_id=user_id, key="db_mp_insufficient_msg", cost=5, mp=u['mp'])}
            # ── KURANGI MP ──
            conn.execute("UPDATE users SET mp = mp - 5 WHERE id=?", (user_id,))
            
            block_strength = u.get("block_strength", 10)
            roll = random.randint(1, 100)
            if roll <= 50:
                reduction = block_strength
            else:
                reduction = random.randint(0, block_strength)
            buffs["block_active"] = True
            buffs["block_reduction"] = reduction
            conn.execute(
                "UPDATE users SET skill_buff_data=? WHERE id=?",
                (json.dumps(buffs), user_id)
            )
            conn.commit()
            conn.close()
            return {
                "ok": True,
                "action": "block",
                "block_reduction": reduction,
                "msg": tr_db(user_id=user_id, key="db_boss_block_success", reduction=reduction)
            }

        if action == "light":
            max_dmg_action = user_max_dmg // 2
            if max_dmg_action < 1:
                max_dmg_action = 1
            mp_cost = 0
        elif action == "heavy":
            max_dmg_action = user_max_dmg
            mp_cost = 5
            if u["mp"] < mp_cost:
                return {"ok": False, "msg": tr_db(user_id=user_id, key="db_mp_insufficient_msg", cost=mp_cost, mp=u['mp'])}
        elif action == "ultimate":
            max_dmg_action = int(user_max_dmg * ultimate_multipliers.get(cls, 3))
            mp_cost = 50
            if u["mp"] < mp_cost:
                return {"ok": False, "msg": tr_db(user_id=user_id, key="db_mp_insufficient_msg", cost=mp_cost, mp=u['mp'])}
            last_used = u.get("ultimate_last_used")
            if last_used:
                try:
                    last_dt = datetime.fromisoformat(last_used)
                    if datetime.now() - last_dt < timedelta(minutes=5):
                        remaining_sec = int((timedelta(minutes=5) - (datetime.now() - last_dt)).total_seconds())
                        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_ultimate_cooldown", seconds=remaining_sec)}
                except:
                    pass
            conn.execute("UPDATE users SET ultimate_last_used=? WHERE id=?", (datetime.now().isoformat(), user_id))
            extra_effect = ""
            if cls == "warrior":
                extra_effect = tr_db(user_id=user_id, key="db_ultimate_warrior_effect")
            elif cls == "mage":
                extra_effect = tr_db(user_id=user_id, key="db_ultimate_mage_effect")
            elif cls == "archer":
                extra_effect = tr_db(user_id=user_id, key="db_ultimate_archer_effect")
            elif cls == "healer":
                new_hp = min(u["max_hp"], u["hp"] + 20)
                conn.execute("UPDATE users SET hp=? WHERE id=?", (new_hp, user_id))
                extra_effect = tr_db(user_id=user_id, key="db_ultimate_healer_effect", heal=20)
            elif cls == "rogue":
                extra_effect = tr_db(user_id=user_id, key="db_ultimate_rogue_effect")
        else:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_unknown_action")}

        if mp_cost > 0:
            conn.execute("UPDATE users SET mp = mp - ? WHERE id=?", (mp_cost, user_id))

        # Critical user
        user_crit = u.get("crit_chance", 10)
        guild = conn.execute("SELECT crit_chance FROM guilds WHERE id=?", (guild_id,)).fetchone()
        if guild:
            user_crit += int(guild["crit_chance"])
        if action == "ultimate" and cls == "rogue":
            user_crit += 20

        roll_user = random.randint(1, 100)
        if roll_user <= user_crit:
            user_damage = max_dmg_action
            user_critical = True
        else:
            user_damage = random.randint(1, max(1, max_dmg_action - 1))
            user_critical = False

        # Update attack_counts
        attack_counts = json.loads(boss["attack_counts"]) if boss.get("attack_counts") else {}
        key = str(user_id)
        attack_counts[key] = attack_counts.get(key, 0) + 1
        conn.execute(
            "UPDATE boss_battles SET attack_counts=? WHERE id=?",
            (json.dumps(attack_counts), boss["id"])
        )

        # Terapkan damage ke boss
        new_boss_hp = max(0.0, boss["boss_hp"] - user_damage)

        # ── Jika boss mati ──
        if new_boss_hp <= 0:
            conn.execute(
                "UPDATE boss_battles SET boss_hp=0, status='defeated', ended_at=? WHERE id=?",
                (local_now().isoformat(), boss["id"])
            )

            # ── Tambah counter guild ──
            today = date.today().isoformat()
            conn.execute(
                """UPDATE guilds 
                   SET boss_defeated_today = boss_defeated_today + 1,
                       boss_defeated_date = ?
                   WHERE id = ?""",
                (today, guild_id)
            )

            bdata = BOSSES.get(boss["boss_id"], {})
            members = conn.execute(
                "SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)
            ).fetchall()
            cnt = max(1, len(members))
            xp_reward = bdata.get("xp", 200) // cnt
            gold_reward = bdata.get("gold", 50) // cnt

            rewarded_members = []
            for m in members:
                uid = str(m["user_id"])
                if attack_counts.get(uid, 0) > 0:
                    rewarded_members.append(m["user_id"])
                    conn.execute("""
                        INSERT INTO boss_rewards(user_id, guild_id, boss_name, boss_tier, xp_reward, gold_reward)
                        VALUES(?,?,?,?,?,?)
                    """, (m["user_id"], guild_id, boss["boss_name"], boss["boss_tier"], xp_reward, gold_reward))

            conn.commit()
            conn.close()
            conn = None

            # Berikan reward setelah koneksi ditutup
            for uid in rewarded_members:
                gain_xp_gold(uid, xp_reward, gold_reward)
                check_achievements(uid, "boss_kill", 1)
                add_notification(uid, tr_db(user_id=uid, key="db_boss_defeated_notif", name=boss['boss_name']), "success")

            return {
                "ok": True,
                "defeated": True,
                "action": action,
                "user_damage": user_damage,
                "user_critical": user_critical,
                "boss_hp_left": 0,
                "extra_effect": extra_effect if action == "ultimate" else "",
                "msg": tr_db(user_id=user_id, key="db_boss_defeated", name=boss['boss_name'])
            }

        # ── Boss serang balik ──
        boss_max_dmg = int(boss["boss_attack"])
        if boss_max_dmg < 1:
            boss_max_dmg = 1
        boss_crit = int(boss.get("boss_crit_chance", 15))
        roll_boss = random.randint(1, 100)
        if roll_boss <= boss_crit:
            boss_damage_raw = boss_max_dmg
            boss_critical = True
        else:
            boss_damage_raw = random.randint(1, max(1, boss_max_dmg - 1))
            boss_critical = False

        # Block
        block_reduction = 0
        if buffs.get("block_active"):
            block_reduction = buffs.get("block_reduction", 0)
            boss_damage_raw = max(0, boss_damage_raw - block_reduction)
            buffs.pop("block_active", None)
            buffs.pop("block_reduction", None)
            conn.execute(
                "UPDATE users SET skill_buff_data=? WHERE id=?",
                (json.dumps(buffs), user_id)
            )

        # Shield Bash
        if shield_active:
            boss_damage_raw = boss_damage_raw // 2
            buffs.pop("shield_active", None)
            conn.execute(
                "UPDATE users SET skill_buff_data=? WHERE id=?",
                (json.dumps(buffs), user_id)
            )

        # Damage ke user
        reduc = u.get("hp_damage_reduction", 0)
        actual = max(0.0, boss_damage_raw - reduc)
        actual_int = int(actual)
        actual_damage = actual_int
        new_hp = max(0, u["hp"] - actual_int)
        new_hp_int = int(new_hp)

        revived = False
        if new_hp_int == 0 and u.get("has_revive"):
            new_hp_int = int(u["max_hp"] * 0.3)
            conn.execute("UPDATE users SET hp=?, has_revive=0 WHERE id=?", (new_hp_int, user_id))
            revived = True
        else:
            conn.execute("UPDATE users SET hp=? WHERE id=?", (new_hp_int, user_id))

        conn.execute("UPDATE boss_battles SET boss_hp=? WHERE id=?", (new_boss_hp, boss["id"]))

        conn.commit()
        conn.close()
        conn = None

        if revived:
            recalculate_all_buffs(user_id)
            add_notification(user_id, tr_db(user_id=user_id, key="db_totem_revive"), "success")

        return {
            "ok": True,
            "defeated": False,
            "action": action,
            "user_damage": user_damage,
            "user_critical": user_critical,
            "boss_hp_left": new_boss_hp,
            "boss_max_hp": boss["boss_max_hp"],
            "boss_damage": boss_damage_raw,
            "boss_critical": boss_critical,
            "actual_damage": actual_damage,
            "shield_used": shield_active,
            "block_reduction": block_reduction,
            "revived": revived,
            "extra_effect": extra_effect if action == "ultimate" else "",
            "mp_cost": mp_cost
        }

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        log_crash(f"attack_boss error: {e}")
        return {"ok": False, "msg": f"Error: {str(e)}"}

def get_unclaimed_boss_rewards(user_id):
    """Ambil daftar reward boss yang belum diklaim oleh user"""
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM boss_rewards 
        WHERE user_id=? AND is_claimed=0 
        ORDER BY created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def claim_boss_reward(reward_id, user_id):
    """Klaim reward, berikan XP dan Gold ke user, tandai sebagai sudah diklaim.
    PENTING: Koneksi harus ditutup sebelum memanggil gain_xp_gold agar tidak terjadi
    'database is locked' karena nested connections.
    """
    # ── Step 1: Baca data reward, lalu TUTUP koneksi ──────────────────────────
    conn = get_conn()
    try:
        reward_row = conn.execute(
            "SELECT * FROM boss_rewards WHERE id=? AND user_id=? AND is_claimed=0",
            (reward_id, user_id)
        ).fetchone()
        if not reward_row:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_boss_reward_invalid")}
        reward = dict(reward_row)   # konversi ke dict sebelum close
    except Exception as e:
        log_crash(f"claim_boss_reward SELECT error: {e}")
        return {"ok": False, "msg": f"Error membaca reward: {e}"}
    finally:
        conn.close()                # ← TUTUP sebelum panggil gain_xp_gold

    # ── Step 2: Berikan reward (gain_xp_gold membuka/menutup koneksinya sendiri) ─
    try:
        result = gain_xp_gold(user_id, reward["xp_reward"], reward["gold_reward"])
    except Exception as e:
        log_crash(f"claim_boss_reward gain_xp_gold error: {e}")
        return {"ok": False, "msg": f"Error saat memberikan reward XP/Gold: {e}"}

    # ── Step 3: Tandai sebagai diklaim (koneksi baru, tidak ada yg nested) ────
    conn2 = get_conn()
    try:
        conn2.execute("UPDATE boss_rewards SET is_claimed=1 WHERE id=?", (reward_id,))
        conn2.commit()
    except Exception as e:
        log_crash(f"claim_boss_reward UPDATE is_claimed error: {e}")
        return {"ok": False, "msg": f"Error menandai reward sebagai diklaim: {e}"}
    finally:
        conn2.close()

    return {
        "ok": True,
        "msg": tr_db(user_id=user_id, key="db_boss_reward_claimed", xp=reward['xp_reward'], gold=reward['gold_reward']),
        "xp_gained": reward["xp_reward"],
        "gold_gained": reward["gold_reward"],
        "leveled_up": result.get("leveled_up", False),
    }

# ── Stats ─────────────────────────────────────────────────────────────────────

def get_stats(user_id):
    conn = get_conn()
    u  = dict(conn.execute(
        "SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
    hd = conn.execute(
        "SELECT COUNT(*) c FROM habits WHERE user_id=? AND done_today=1",
        (user_id,)).fetchone()["c"]
    ht = conn.execute(
        "SELECT COUNT(*) c FROM habits WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    dd = conn.execute(
        "SELECT COUNT(*) c FROM dailies WHERE user_id=? AND done_today=1",
        (user_id,)).fetchone()["c"]
    dt = conn.execute(
        "SELECT COUNT(*) c FROM dailies WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    td = conn.execute(
        "SELECT COUNT(*) c FROM todos WHERE user_id=? AND done=1",
        (user_id,)).fetchone()["c"]
    tt = conn.execute(
        "SELECT COUNT(*) c FROM todos WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    ms = conn.execute(
        "SELECT MAX(streak) s FROM habits WHERE user_id=?",
        (user_id,)).fetchone()["s"] or 0
    ic = conn.execute(
        "SELECT COUNT(*) c FROM inventory WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    pc = conn.execute(
        "SELECT COUNT(*) c FROM user_pets WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    bk = conn.execute(
        "SELECT COUNT(*) c FROM boss_battles bb"
        " JOIN guild_members gm ON bb.guild_id=gm.guild_id"
        " WHERE gm.user_id=? AND bb.status='defeated'",
        (user_id,)).fetchone()["c"]
    log = conn.execute(
        "SELECT * FROM activity_log WHERE user_id=?"
        " ORDER BY created_at DESC LIMIT 30",
        (user_id,)).fetchall()
    wk = conn.execute(
        "SELECT date(created_at) day,"
        "SUM(xp_gained) xp, SUM(gold_gained) gold"
        " FROM activity_log WHERE user_id=?"
        " AND created_at>=date('now','-7 days')"
        " GROUP BY day ORDER BY day",
        (user_id,)).fetchall()
    conn.close()
    return {
        "user": u,
        "habits_done_today": hd, "habits_total": ht,
        "dailies_done_today": dd, "dailies_total": dt,
        "todos_done": td, "todos_total": tt,
        "max_streak": ms, "inv_count": ic, "pet_count": pc,
        "bosses_killed": bk,
        "recent_log": [dict(r) for r in log],
        "weekly": [dict(r) for r in wk],
    }


# ── Sport Stats helper (dipakai get_stats & StatsPage) ───────────────────────
def get_sport_stats(user_id):
    conn = get_conn()
    total_sport = conn.execute(
        "SELECT COUNT(*) c FROM sport_activities WHERE user_id=?",
        (user_id,)).fetchone()["c"]
    done_sport_today = conn.execute(
        "SELECT COUNT(*) c FROM sport_activities WHERE user_id=? AND done_today=1",
        (user_id,)).fetchone()["c"]
    max_sport_streak = conn.execute(
        "SELECT MAX(streak) s FROM sport_activities WHERE user_id=?",
        (user_id,)).fetchone()["s"] or 0
    u = conn.execute(
        "SELECT COALESCE(sport_level,1) as sport_level,"
        " COALESCE(sport_xp,0) as sport_xp,"
        " COALESCE(total_sport_points_earned,0) as total_sport_points_earned"
        " FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return {
        "total_sport": total_sport,
        "done_sport_today": done_sport_today,
        "max_sport_streak": max_sport_streak,
        "sport_level": u["sport_level"] if u else 1,
        "sport_xp": u["sport_xp"] if u else 0,
        "total_sport_points_earned": u["total_sport_points_earned"] if u else 0,
    }


# ── Notifications ─────────────────────────────────────────────────────────────

@retry_on_lock
def add_notification(user_id, message, type_="info"):
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO notifications(user_id, message, type, created_at) VALUES(?,?,?,?)",
            (user_id, message, type_, local_now().isoformat())
        )
        conn.commit()
    finally:
        conn.close()


def get_notifications(user_id, unread_only=True):
    conn = get_conn()
    q = ("SELECT * FROM notifications WHERE user_id=?"
         + (" AND is_read=0" if unread_only else "")
         + " ORDER BY created_at DESC LIMIT 20")
    rows = conn.execute(q, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_read(user_id):
    conn = get_conn()
    conn.execute("UPDATE notifications SET is_read=1 WHERE user_id=?",
                 (user_id,))
    conn.commit()
    conn.close()


@retry_on_lock
def log_activity(user_id, action, detail, xp, gold):
    conn = get_conn()
    conn.execute(
        "INSERT INTO activity_log(user_id, action, detail, xp_gained, gold_gained, created_at) VALUES(?,?,?,?,?,?)",
        (user_id, action, detail, xp, gold, local_now().isoformat())
    )
    conn.commit()
    conn.close()


# ── Avatar / Settings ─────────────────────────────────────────────────────────

AVATAR_CLASSES = {
    "warrior": {"name": "Warrior", "icon": "⚔️",
                "bonus": "HP+20%, Skill: Shield Bash (10 MP)"},
    "mage":    {"name": "Mage",    "icon": "🧙",
                "bonus": "XP+15%, Skill: Arcane Surge (15 MP)"},
    "archer":  {"name": "Archer",  "icon": "🏹",
                "bonus": "Gold+10%, Skill: Gold Shot (10 MP)"},
    "healer":  {"name": "Healer",  "icon": "💊",
                "bonus": "Skill: Regenerate +30 HP (20 MP)"},
    "rogue":   {"name": "Rogue",   "icon": "🗡️",
                "bonus": "Streak bonus, Skill: Shadow Step (15 MP)"},
}

THEMES = {
    # ── Modern Aurora (default, toggle target) ──
    "modern_dark": {
        "label": "🔮 Aurora Dark",
        "primary": "#8b5cf6", "light": "#a78bfa",
        "bg": "#0b0b16", "bg2": "#14122c", "bg3": "#0c1a26",
        "panel": "rgba(26,28,50,0.90)", "border": "rgba(150,140,255,0.22)",
        "accent": "#22d3ee", "accent2": "#8b5cf6", "accent3": "#22d3ee", "glow": "#a78bfa",
        "text": "#eef0ff", "muted": "#9b9fc4",
    },
    "modern_light": {
        "label": "🌤️ Aurora Light",
        "primary": "#7c3aed", "light": "#6d28d9",
        "bg": "#eceffb", "bg2": "#e7e0f8", "bg3": "#e2eff7",
        "panel": "rgba(255,255,255,0.92)", "border": "rgba(124,108,210,0.30)",
        "accent": "#0891b2", "accent2": "#7c3aed", "accent3": "#0891b2", "glow": "#8b5cf6",
        "text": "#1b1633", "muted": "#5c5570",
    },
    "overworld": {
        "label": "🌿 Overworld",
        "primary": "#34d399", "light": "#6ee7b7",
        "bg": "#06120c", "bg2": "#0a2114", "bg3": "#0c1a14",
        "panel": "rgba(20,42,28,0.90)", "border": "rgba(80,255,150,0.22)",
        "accent": "#a3e635", "accent2": "#34d399", "accent3": "#a3e635", "glow": "#6ee7b7",
        "text": "#e6f7ec", "muted": "#8aaa9a",
    },
    "nether": {
        "label": "🔥 Nether",
        "primary": "#f43f5e", "light": "#fb7185",
        "bg": "#13060a", "bg2": "#240a10", "bg3": "#1a0a06",
        "panel": "rgba(44,18,22,0.90)", "border": "rgba(255,96,80,0.22)",
        "accent": "#fb923c", "accent2": "#f43f5e", "accent3": "#fb923c", "glow": "#fb7185",
        "text": "#ffe9ea", "muted": "#b08a8a",
    },
    "the_end": {
        "label": "🌌 The End",
        "primary": "#c026d3", "light": "#e879f9",
        "bg": "#0a0614", "bg2": "#170a28", "bg3": "#10081c",
        "panel": "rgba(30,20,50,0.90)", "border": "rgba(205,125,255,0.22)",
        "accent": "#818cf8", "accent2": "#c026d3", "accent3": "#818cf8", "glow": "#e879f9",
        "text": "#f3eaff", "muted": "#a896b8",
    },
    "ocean": {
        "label": "🌊 Ocean",
        "primary": "#0ea5e9", "light": "#38bdf8",
        "bg": "#04101a", "bg2": "#082033", "bg3": "#06141f",
        "panel": "rgba(16,36,54,0.90)", "border": "rgba(80,200,255,0.22)",
        "accent": "#22d3ee", "accent2": "#0ea5e9", "accent3": "#22d3ee", "glow": "#38bdf8",
        "text": "#e3f4ff", "muted": "#8aa6b8",
    },
    "ancient_city": {
        "label": "🏚️ Ancient City",
        "primary": "#14b8a6", "light": "#2dd4bf",
        "bg": "#06141a", "bg2": "#0a2329", "bg3": "#06181c",
        "panel": "rgba(18,40,44,0.90)", "border": "rgba(60,230,210,0.22)",
        "accent": "#5eead4", "accent2": "#14b8a6", "accent3": "#5eead4", "glow": "#2dd4bf",
        "text": "#e3f8f4", "muted": "#88a8a0",
    },
}

def get_user_theme(user_id):
    u = get_user(user_id)
    return THEMES.get(u.get("theme", "modern_dark"), THEMES["modern_dark"])


def set_user_theme(user_id, key):
    if key in THEMES:
        update_user(user_id, theme=key)
        return {"ok": True}
    return {"ok": False}


def set_avatar(user_id, avatar_class=None, color=None,
               emoji=None, bio=None, display_name=None):
    kw = {}
    if avatar_class and avatar_class in AVATAR_CLASSES:
        kw["avatar_class"] = avatar_class
    if color:
        kw["avatar_color"] = color
    if emoji:
        kw["avatar_emoji"] = emoji
    if bio is not None:
        kw["bio"] = bio
    if display_name:
        kw["display_name"] = display_name
    if kw:
        update_user(user_id, **kw)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_avatar_updated")}

def change_class(user_id, new_class):
    """Ganti class avatar — maksimal sekali sehari."""
    if new_class not in AVATAR_CLASSES:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_class_unknown")}
    u = get_user(user_id)
    last_change = u.get("last_class_change", "")
    today = date.today().isoformat()
    if last_change == today:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_class_change_cooldown")}
    update_user(user_id, avatar_class=new_class, last_class_change=today)
    update_class_passive_buffs(user_id)
    recalculate_all_buffs(user_id)
    apply_hp_multiplier(user_id)
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_class_changed", name=AVATAR_CLASSES[new_class]['name'])}

def apply_hp_multiplier(user_id):
    u = get_user(user_id)
    class_buffs = get_class_passive_buffs(user_id)
    hp_mult = class_buffs.get("hp_multiplier", 1.0)
    base_max_hp = 50 + (u["level"] - 1) * 10
    new_max_hp = int(base_max_hp * hp_mult)
    new_hp = min(u["hp"], new_max_hp)
    update_user(user_id, max_hp=new_max_hp, hp=new_hp)

def set_user_settings(user_id, sound_enabled=None):
    kw = {}
    if sound_enabled is not None:
        kw["sound_enabled"] = int(sound_enabled)
    if kw:
        update_user(user_id, **kw)

# ── Ekspor ke Excel ─────────────────────────────────────────
def export_habits_excel(user_id, filepath):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    habits = get_habits(user_id)
    dailies = get_dailies(user_id)
    todos = get_todos(user_id)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "CraftLife Data"
    
    # Header
    headers = ["Jenis", "Nama", "Kesulitan/Prioritas", "Streak", "Terakhir", "Catatan"]
    ws.append(headers)
    for col in range(1, 7):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="5a8a2e", end_color="5a8a2e", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    for h in habits:
        ws.append(["Habit", h["name"], h["difficulty"], h["streak"], h["last_done"], h["notes"]])
    for d in dailies:
        ws.append(["Daily", d["name"], d["difficulty"], d["streak"], d["last_done"], d["notes"]])
    for t in todos:
        ws.append(["Quest", t["name"], t["priority"], "", "", t["notes"]])
    
    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[col_letter].width = adjusted_width
    
    wb.save(filepath)
    return filepath

# ── Ekspor ke Word ─────────────────────────────────────────
def export_habits_word(user_id, filepath):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    habits = get_habits(user_id)
    dailies = get_dailies(user_id)
    todos = get_todos(user_id)
    
    doc = Document()
    title = doc.add_heading("CraftLife - Data Habits", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Habits
    doc.add_heading("Habits", level=1)
    for h in habits:
        p = doc.add_paragraph()
        p.add_run(f"{h['icon']} {h['name']}  ").bold = True
        p.add_run(f"[{h['difficulty']}]  ")
        p.add_run(f"+{h['xp_reward']} XP, +{h['gold_reward']} Gold  ")
        if h['streak'] > 0:
            p.add_run(f"🔥 Streak: {h['streak']} hari")
        if h['notes']:
            doc.add_paragraph(f"📝 Catatan: {h['notes']}", style="Intense Quote")
    
    # Dailies
    doc.add_heading("Dailies", level=1)
    for d in dailies:
        p = doc.add_paragraph()
        p.add_run(f"{d['icon']} {d['name']}  ").bold = True
        p.add_run(f"[{d['difficulty']}]  ")
        p.add_run(f"+{d['xp_reward']} XP, +{d['gold_reward']} Gold  ")
        if d['streak'] > 0:
            p.add_run(f"🔥 Streak: {d['streak']} hari")
        if d['notes']:
            doc.add_paragraph(f"📝 Catatan: {d['notes']}", style="Intense Quote")
    
    # Todos / Quests
    doc.add_heading("Quests", level=1)
    for t in todos:
        p = doc.add_paragraph()
        p.add_run(f"{t['icon']} {t['name']}  ").bold = True
        p.add_run(f"[{t['priority']}]  ")
        p.add_run(f"+{t['xp_reward']} XP, +{t['gold_reward']} Gold")
        if t['notes']:
            doc.add_paragraph(f"📝 Catatan: {t['notes']}", style="Intense Quote")
    
    doc.save(filepath)
    return filepath

# ── Ekspor ke PDF ─────────────────────────────────────────
def export_habits_pdf(user_id, filepath):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    habits = get_habits(user_id)
    dailies = get_dailies(user_id)
    todos = get_todos(user_id)
    
    doc = SimpleDocTemplate(filepath, pagesize=landscape(A4))
    story = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='Title', parent=styles['Title'], alignment=1, fontSize=16)
    story.append(Paragraph("CraftLife - Data Habits", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Data tabel
    data = [["Jenis", "Nama", "Difficulty/Priority", "Streak", "Last Done", "Notes"]]
    for h in habits:
        data.append(["Habit", h['name'], h['difficulty'], str(h['streak']), h['last_done'] or "-", h['notes'] or "-"])
    for d in dailies:
        data.append(["Daily", d['name'], d['difficulty'], str(d['streak']), d['last_done'] or "-", d['notes'] or "-"])
    for t in todos:
        data.append(["Quest", t['name'], t['priority'], "-", "-", t['notes'] or "-"])
    
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#5a8a2e")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('BACKGROUND', (0,1), (-1,-1), colors.beige),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(table)
    doc.build(story)
    return filepath

def export_habits_csv(user_id, filepath):
    import csv
    habits = get_habits(user_id)
    dailies = get_dailies(user_id)
    todos = get_todos(user_id)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Jenis", "Nama", "Kesulitan", "Streak", "Terakhir", "Catatan"])
        for h in habits:
            writer.writerow(["Habit", h["name"], h["difficulty"], h["streak"], h["last_done"], h["notes"]])
        for d in dailies:
            writer.writerow(["Daily", d["name"], d["difficulty"], d["streak"], d["last_done"], d["notes"]])
        for t in todos:
            writer.writerow(["Quest", t["name"], t["priority"], "", "", t["notes"]])
    return filepath

# ── Friend System ─────────────────────────────────────────
def send_friend_request(user_id, target_username):
    conn = get_conn()
    # Cek apakah pengirim admin
    sender = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if sender and sender["is_admin"]:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_admin_cannot_send")}
    
    target = conn.execute("SELECT id, is_admin FROM users WHERE username=?", (target_username.lower(),)).fetchone()
    if not target:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_user_not_found")}
    if target["is_admin"]:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_admin_target")}
    target = conn.execute("SELECT id FROM users WHERE username=?", (target_username.lower(),)).fetchone()
    if not target:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_user_not_found")}
    if target["id"] == user_id:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_self")}
    existing = conn.execute("SELECT * FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)", 
                            (user_id, target["id"], target["id"], user_id)).fetchone()
    if existing:
        if existing["status"] == "accepted":
            conn.close()
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_already")}
        else:
            conn.close()
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_request_pending")}
    conn.execute("INSERT INTO friends(user_id, friend_id, status, action_user_id) VALUES(?,?,?,?)",
                 (user_id, target["id"], "pending", user_id))
    conn.commit()
    conn.close()
    add_notification(target["id"], tr_db(user_id=target["id"], key="db_friend_request_notif", name=get_user(user_id)['display_name']), "info")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_friend_request_sent")}

def accept_friend_request(user_id, request_id):
    conn = get_conn()
    # Cek apakah penerima admin
    user = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if user and user["is_admin"]:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_accept_admin_cannot")}
    req = conn.execute("SELECT * FROM friends WHERE id=? AND friend_id=? AND status='pending'", (request_id, user_id)).fetchone()
    if not req:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_request_invalid")}
    conn.execute("UPDATE friends SET status='accepted' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    check_achievements(req["user_id"], "friend_count", 1)
    check_achievements(user_id, "friend_count", 1)
    add_notification(req["user_id"], tr_db(user_id=req["user_id"], key="db_friend_accepted_notif", name=get_user(user_id)['display_name']), "success")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_friend_accepted")}

def reject_friend_request(user_id, request_id):
    conn = get_conn()
    conn.execute("DELETE FROM friends WHERE id=? AND friend_id=? AND status='pending'", (request_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_friend_rejected")}

def get_friends(user_id):
    conn = get_conn()
    # Cek jika user admin, langsung return []
    u = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if u and u["is_admin"]:
        conn.close()
        return []
    rows = conn.execute("""
        SELECT u.id, u.display_name, u.username, u.avatar_emoji, u.level
        FROM friends f
        JOIN users u ON (f.user_id = u.id OR f.friend_id = u.id)
        WHERE (f.user_id=? OR f.friend_id=?) AND f.status='accepted' AND u.id != ?
        GROUP BY u.id
    """, (user_id, user_id, user_id)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_friend_requests(user_id):
    conn = get_conn()
    u = conn.execute("SELECT is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    if u and u["is_admin"]:
        conn.close()
        return []
    rows = conn.execute("""
        SELECT f.id, u.display_name, u.username
        FROM friends f
        JOIN users u ON f.user_id = u.id
        WHERE f.friend_id=? AND f.status='pending'
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ========== GUILD KICK MEMBER ==========
def kick_guild_member(guild_id, leader_id, target_user_id):
    conn = get_conn()
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_kick_only_leader")}
    if target_user_id == leader_id:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_kick_self")}
    member = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, target_user_id)).fetchone()
    if not member:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=leader_id, key="db_guild_kick_not_member")}
    conn.execute("DELETE FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, target_user_id))
    conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (target_user_id,))
    conn.commit()
    conn.close()
    add_notification(target_user_id, tr_db(user_id=target_user_id, key="db_guild_kicked_notif", name=guild['name']), "danger")
    return {"ok": True, "msg": tr_db(user_id=leader_id, key="db_guild_kicked")}

def transfer_guild_leadership(guild_id, current_leader_id, new_leader_id):
    """Transfer kepemimpinan guild dari current_leader ke new_leader."""
    conn = get_conn()
    try:
        # Ambil data guild (termasuk name)
        guild = conn.execute(
            "SELECT leader_id, name FROM guilds WHERE id = ?", (guild_id,)
        ).fetchone()
        if not guild or guild["leader_id"] != current_leader_id:
            return {"ok": False, "msg": tr_db(user_id=current_leader_id, key="db_guild_transfer_not_leader")}
        
        # Cek apakah new_leader adalah member guild
        member = conn.execute(
            "SELECT 1 FROM guild_members WHERE guild_id = ? AND user_id = ?",
            (guild_id, new_leader_id)
        ).fetchone()
        if not member:
            return {"ok": False, "msg": tr_db(user_id=current_leader_id, key="db_guild_transfer_not_member")}
        
        # Transfer leadership
        conn.execute(
            "UPDATE guilds SET leader_id = ? WHERE id = ?",
            (new_leader_id, guild_id)
        )
        conn.commit()
        
        # Kirim notifikasi
        add_notification(new_leader_id, tr_db(user_id=new_leader_id, key="db_guild_leader_transfer_notif", name=guild['name']), "success")
        add_notification(current_leader_id, tr_db(user_id=current_leader_id, key="db_guild_transfer_old_notif", name=guild['name'], id=new_leader_id), "info")
    except Exception as e:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=current_leader_id, key="db_guild_transfer_failed", error=str(e))}
    finally:
        conn.close()
    return {"ok": True, "msg": tr_db(user_id=current_leader_id, key="db_guild_transfer_success")}

# ========== GUILD LEADER TRANSFER (saat leader keluar) ==========
def leave_guild_with_transfer(user_id):
    u = get_user(user_id)
    if u.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_leave_admin")}
    u = get_user(user_id)
    gid = u.get("guild_id")
    if not gid:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_leave_not_in")}
    conn = get_conn()
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (gid,)).fetchone()
    if not guild:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_not_found")}
    
    # Jika user adalah leader
    if guild["leader_id"] == user_id:
        # Ambil member lain (kecuali dirinya sendiri)
        members = conn.execute("SELECT user_id FROM guild_members WHERE guild_id=? AND user_id!=?", (gid, user_id)).fetchall()
        if members:
            # Ada member lain: lakukan transfer leader
            conn.execute("INSERT INTO guild_leader_transfers(guild_id, old_leader_id) VALUES(?,?)", (gid, user_id))
            conn.commit()
            conn.execute("DELETE FROM guild_members WHERE user_id=? AND guild_id=?", (user_id, gid))
            conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (user_id,))
            conn.commit()
            for m in members:
                add_notification(m["user_id"], tr_db(user_id=m["user_id"], key="db_guild_leader_left", name=guild['name']), "warning")
            conn.close()
            return {"ok": True, "msg": tr_db(user_id=user_id, key="db_guild_leave_transfer")}
        else:
            # Tidak ada anggota lain: hapus semua data terkait guild, lalu guild
            conn.execute("DELETE FROM guild_members WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM guild_invites WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM guild_requests WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM guild_leader_transfers WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM boss_battles WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM guild_messages WHERE guild_id=?", (gid,))
            conn.execute("DELETE FROM boss_rewards WHERE guild_id=?", (gid,))   # <-- TAMBAHKAN INI
            conn.execute("DELETE FROM guilds WHERE id=?", (gid,))
            conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (user_id,))
            conn.commit()
            conn.close()
            return {"ok": True, "msg": tr_db(user_id=user_id, key="db_guild_leave_disband")}
    else:
        # Bukan leader: keluar biasa
        conn.execute("DELETE FROM guild_members WHERE user_id=? AND guild_id=?", (user_id, gid))
        conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_guild_leave_success")}

def accept_leader_transfer(user_id, transfer_id):
    conn = get_conn()
    trans = conn.execute("SELECT * FROM guild_leader_transfers WHERE id=? AND status='pending'", (transfer_id,)).fetchone()
    if not trans:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_transfer_invalid")}
    member = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (trans["guild_id"], user_id)).fetchone()
    if not member:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_transfer_not_member_accept")}
    conn.execute("UPDATE guilds SET leader_id=? WHERE id=?", (user_id, trans["guild_id"]))
    conn.execute("UPDATE guild_leader_transfers SET status='accepted' WHERE id=?", (transfer_id,))
    conn.commit()
    conn.close()
    add_notification(user_id, tr_db(user_id=user_id, key="db_guild_leader_accepted"), "success")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_guild_transfer_accepted")}

# ========== KICK FRIEND ==========
def remove_friend(user_id, friend_id):
    u = get_user(user_id)
    if u.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_friend_remove_admin")}
    conn = get_conn()
    conn.execute("DELETE FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
                 (user_id, friend_id, friend_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_friend_removed")}

# ========== PRIVATE CHAT ==========
def send_message(sender_id, receiver_id, message, created_at=None):
    sender = get_user(sender_id)
    if sender.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=sender_id, key="db_chat_admin_cannot_send")}
    conn = get_conn()
    if created_at is None:
        created_at = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO messages(sender_id, receiver_id, message, created_at) VALUES(?,?,?,?)",
        (sender_id, receiver_id, message, created_at)
    )
    conn.commit()
    conn.close()
    add_notification(receiver_id, tr_db(user_id=receiver_id, key="db_chat_new_message", name=get_user(sender_id)['display_name']), "info")
    return {"ok": True}

def get_messages(user_id, other_id, limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM messages
        WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?))
        AND (deleted_by IS NULL OR deleted_by NOT LIKE ?)
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, other_id, other_id, user_id, f'%{user_id}%', limit)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

def mark_messages_read(user_id, other_id):
    conn = get_conn()
    conn.execute("UPDATE messages SET is_read=1 WHERE receiver_id=? AND sender_id=?", (user_id, other_id))
    conn.commit()
    conn.close()

def get_unread_count(user_id):
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM messages WHERE receiver_id=? AND is_read=0", (user_id,)).fetchone()[0]
    conn.close()
    return count

def clear_friend_chat(user_id, friend_id):
    """Tandai semua pesan antara user_id dan friend_id sebagai dihapus oleh user_id (soft delete)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, deleted_by FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)",
        (user_id, friend_id, friend_id, user_id)
    ).fetchall()
    for row in rows:
        deleted_by = row["deleted_by"] or ""
        ids = set(deleted_by.split(',')) if deleted_by else set()
        if str(user_id) not in ids:
            ids.add(str(user_id))
            new_deleted_by = ','.join(sorted(ids, key=int))
            conn.execute("UPDATE messages SET deleted_by=? WHERE id=?", (new_deleted_by, row["id"]))
    conn.commit()
    conn.close()

def clear_guild_chat(guild_id):
    """Hapus semua pesan guild (hard delete)."""
    conn = get_conn()
    conn.execute("DELETE FROM guild_messages WHERE guild_id=?", (guild_id,))
    conn.commit()
    conn.close()

# ========== GUILD CHAT ==========
def send_guild_message(guild_id, sender_id, message, created_at=None):
    sender = get_user(sender_id)
    if sender.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=sender_id, key="db_guild_chat_admin_cannot")}
    if created_at is None:
        created_at = datetime.now().isoformat()
    # ── Step 1: Insert pesan & ambil member list, lalu TUTUP koneksi ─────────
    conn = get_conn()
    conn.execute(
        "INSERT INTO guild_messages(guild_id, sender_id, message, created_at) VALUES(?,?,?,?)",
        (guild_id, sender_id, message, created_at)
    )
    conn.commit()
    members = conn.execute(
        "SELECT user_id FROM guild_members WHERE guild_id=? AND user_id!=?",
        (guild_id, sender_id)
    ).fetchall()
    member_ids = [m["user_id"] for m in members]
    conn.close()   # ← TUTUP sebelum panggil get_user / add_notification
    # ── Step 2: Notifikasi (koneksi terpisah, tidak nested) ──────────────────
    sender_name = get_user(sender_id)["display_name"]
    for uid in member_ids:
        add_notification(uid, tr_db(user_id=uid, key="db_guild_chat_message", name=sender_name, msg=message[:50]), "info")
    return {"ok": True}

def get_guild_messages(guild_id, limit=100):
    conn = get_conn()
    rows = conn.execute("""
        SELECT gm.*, u.display_name
        FROM guild_messages gm
        JOIN users u ON gm.sender_id = u.id
        WHERE gm.guild_id=?
        ORDER BY gm.created_at DESC LIMIT ?
    """, (guild_id, limit)).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]

# ── Guild Invites (Undangan dari Leader) ─────────────────────────────────
def get_guild_invites(user_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT gi.*, g.name as guild_name 
        FROM guild_invites gi 
        JOIN guilds g ON gi.guild_id = g.id 
        WHERE gi.user_id=? AND gi.status='pending'
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def accept_invite(user_id, invite_id):
    u = get_user(user_id)
    if u.get("is_admin", 0):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_admin_cannot_guild")}
    conn = get_conn()
    inv = conn.execute("SELECT * FROM guild_invites WHERE id=? AND user_id=? AND status='pending'", (invite_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_invite_invalid")}
    
    # Cek jumlah member
    count = conn.execute("SELECT COUNT(*) FROM guild_members WHERE guild_id=?", (inv["guild_id"],)).fetchone()[0]
    if count >= 20:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_guild_full")}
    
    conn.execute("UPDATE guild_invites SET status='accepted' WHERE id=?", (invite_id,))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (inv["guild_id"], user_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (inv["guild_id"], user_id))
    conn.commit()
    conn.close()
    add_notification(user_id, tr_db(user_id=user_id, key="db_guild_joined"), "success")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_accept_invite_welcome")}

def reject_invite(user_id, invite_id):
    conn = get_conn()
    conn.execute("UPDATE guild_invites SET status='rejected' WHERE id=? AND user_id=?", (invite_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_invite_rejected")}


# ─────────────────────────────────────────────────────────────────────────────── #
def set_security_question(user_id, question, answer):
    """Simpan pertanyaan & jawaban keamanan (jawaban di-hash)"""
    conn = get_conn()
    conn.execute(
        "UPDATE users SET security_question=?, security_answer_hash=? WHERE id=?",
        (question, _hash(answer.strip().lower()), user_id)
    )
    conn.commit()
    conn.close()

def verify_security_answer(user_id, answer):
    """Cek apakah jawaban cocok"""
    conn = get_conn()
    row = conn.execute(
        "SELECT security_answer_hash FROM users WHERE id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    if not row or not row["security_answer_hash"]:
        return False
    return _hash(answer.strip().lower()) == row["security_answer_hash"]

def reset_password_by_security(user_id, new_password):
    """Reset password tanpa perlu email, asumsi sudah verifikasi jawaban"""
    conn = get_conn()
    conn.execute(
        "UPDATE users SET password_hash=? WHERE id=?",
        (_hash(new_password), user_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}


import secrets

def generate_backup_codes(user_id, num_codes=5):
    """Generate backup codes untuk user, simpan hash-nya."""
    conn = get_conn()
    # Hapus kode lama yang belum dipakai
    conn.execute("DELETE FROM backup_codes WHERE user_id=? AND is_used=0", (user_id,))
    codes = []
    for _ in range(num_codes):
        # Generate kode 8 karakter alfanumerik
        raw_code = secrets.token_hex(4).upper()  # 8 karakter
        code_hash = hashlib.sha256(raw_code.encode()).hexdigest()
        conn.execute("INSERT INTO backup_codes(user_id, code_hash) VALUES(?,?)", (user_id, code_hash))
        codes.append(raw_code)
    conn.commit()
    conn.close()
    return codes  # kembalikan kode asli (hanya sekali ini, untuk ditampilkan ke user)

def get_user_backup_codes(user_id, only_unused=True):
    """Ambil daftar backup codes (hash) user."""
    conn = get_conn()
    if only_unused:
        rows = conn.execute("SELECT id, code_hash FROM backup_codes WHERE user_id=? AND is_used=0", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT id, code_hash, is_used FROM backup_codes WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def verify_backup_code(user_id, raw_code):
    """Cek apakah kode cadangan valid dan belum dipakai."""
    code_hash = hashlib.sha256(raw_code.upper().strip().encode()).hexdigest()
    conn = get_conn()
    row = conn.execute("SELECT id FROM backup_codes WHERE user_id=? AND code_hash=? AND is_used=0", (user_id, code_hash)).fetchone()
    if row:
        # Tandai sebagai terpakai
        conn.execute("UPDATE backup_codes SET is_used=1 WHERE id=?", (row["id"],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def reset_password_with_backup_code(user_id, new_password):
    """Reset password setelah verifikasi backup code (fungsi terpisah agar aman)."""
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?", (_hash(new_password), user_id))
    conn.commit()
    conn.close()
    return {"ok": True}

def regenerate_backup_codes(user_id):
    """Generate ulang semua backup codes (menghapus yang lama)."""
    return generate_backup_codes(user_id, num_codes=5)


# --- Economy CRUD --- #
def get_economy_items(user_id, type_filter=None, category_filter=None, search=None):
    """Ambil semua item ekonomi user, dengan filter opsional."""
    conn = get_conn()
    query = "SELECT * FROM economy_items WHERE user_id = ?"
    params = [user_id]
    if type_filter and type_filter in ('income', 'expense'):
        query += " AND type = ?"
        params.append(type_filter)
    if category_filter and category_filter != 'all':
        query += " AND category = ?"
        params.append(category_filter)
    if search:
        query += " AND name LIKE ?"
        params.append(f'%{search}%')
    query += " ORDER BY sort_order, date DESC, created_at DESC"   # sort_order utama
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def add_economy_item(user_id, name, icon, type_, amount, category, date_str, notes='', folder_id=None):
    """Tambah pemasukan/pengeluaran."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Hitung sort_order terakhir untuk user dan folder yang sama (termasuk NULL)
    if folder_id is None:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM economy_items WHERE user_id=? AND folder_id IS NULL",
            (user_id,)
        ).fetchone()[0]
    else:
        max_order = conn.execute(
            "SELECT COALESCE(MAX(sort_order), 0) FROM economy_items WHERE user_id=? AND folder_id=?",
            (user_id, folder_id)
        ).fetchone()[0]
    new_order = max_order + 1

    cur = conn.execute("""
        INSERT INTO economy_items(user_id, name, icon, type, amount, category, date, notes, folder_id, sort_order, updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?, datetime('now'))
    """, (user_id, name, icon, type_, amount, category, date_str, notes, folder_id, new_order))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "id": new_id}

def update_economy_item(item_id, user_id, **kwargs):
    """Update item ekonomi (nama, icon, type, amount, category, date, notes, folder_id)."""
    if not kwargs:
        return
    kwargs['updated_at'] = 'datetime("now")'  # special case
    fields = []
    values = []
    for k, v in kwargs.items():
        if k == 'updated_at':
            fields.append("updated_at = datetime('now')")
        else:
            fields.append(f"{k} = ?")
            values.append(v)
    values.append(item_id)
    values.append(user_id)
    query = f"UPDATE economy_items SET {', '.join(fields)} WHERE id = ? AND user_id = ?"
    conn = get_conn()
    conn.execute(query, values)
    conn.commit()
    conn.close()

def delete_economy_item(user_id, item_id):
    conn = get_conn()
    conn.execute("DELETE FROM economy_items WHERE id = ? AND user_id = ?", (item_id, user_id))
    conn.commit()
    conn.close()

def duplicate_economy_item(user_id, item_id):
    """Duplikasi item ekonomi (tanpa folder_id biar user pilih sendiri)."""
    conn = get_conn()
    original = conn.execute("SELECT * FROM economy_items WHERE id = ? AND user_id = ?", (item_id, user_id)).fetchone()
    if not original:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_redeem_item_fail")}
    d = dict(original)
    d.pop('id')
    d.pop('created_at')
    d.pop('updated_at')
    d['name'] = d['name']  # biarkan sama, user bisa edit nanti
    d['folder_id'] = None
    conn.execute("""
        INSERT INTO economy_items(user_id, name, icon, type, amount, category, date, notes, folder_id)
        VALUES(?,?,?,?,?,?,?,?,?)
    """, (d['user_id'], d['name'], d['icon'], d['type'], d['amount'], d['category'], d['date'], d['notes'], d['folder_id']))
    conn.commit()
    conn.close()
    return {"ok": True}

def get_economy_summary(user_id, year=None, month=None):
    """Ringkasan pemasukan, pengeluaran, saldo per bulan.
       Jika year/month None, ambil bulan berjalan berdasarkan date item.
    """
    conn = get_conn()
    # Ambil data semua item
    rows = conn.execute("SELECT type, amount FROM economy_items WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
    total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
    balance = total_income - total_expense
    return {
        'total_income': total_income,
        'total_expense': total_expense,
        'balance': balance,
    }

def get_economy_count(user_id):
    """Ambil jumlah total transaksi ekonomi user."""
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM economy_items WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row['cnt'] if row else 0

def get_economy_weekly(user_id):
    """Return list of daily income/expense for last 7 days."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT date(date) as day,
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as expense
        FROM economy_items
        WHERE user_id = ? AND date >= date('now', '-6 days')
        GROUP BY date(date)
        ORDER BY day
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_economy_categories(user_id):
    """Ambil daftar kategori unik yang pernah dipakai user."""
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT category FROM economy_items WHERE user_id = ? ORDER BY category", (user_id,)).fetchall()
    conn.close()
    return [r['category'] for r in rows]


def get_full_export_data(user_id):
    """Ambil semua data user untuk keperluan ekspor."""
    user = get_user(user_id)
    stats = get_stats(user_id)
    sport_stats = get_sport_stats(user_id)
    eco_summary = get_economy_summary(user_id)
    eco_weekly = get_economy_weekly(user_id)
    habits = get_habits(user_id)
    dailies = get_dailies(user_id)
    todos = get_todos(user_id)
    sport_activities = get_sport_activities(user_id)
    economy_items = get_economy_items(user_id)
    health_summary = get_health_summary(user_id, days=30)
    health_logs = get_health_logs(user_id, days=30)
    return {
        "user": user,
        "stats": stats,
        "sport_stats": sport_stats,
        "eco_summary": eco_summary,
        "eco_weekly": eco_weekly,
        "habits": habits,
        "dailies": dailies,
        "todos": todos,
        "sport_activities": sport_activities,
        "economy_items": economy_items,
        "health_summary": health_summary,
        "health_logs": health_logs,
    }


# ========== DEBT FUNCTIONS ==========
@retry_on_lock
def add_debt(user_id, name, amount, due_date=None, notes=''):
    conn = get_conn()
    try:
        cur = conn.execute(
            "INSERT INTO debts(user_id, name, amount, due_date, notes) VALUES(?,?,?,?,?)",
            (user_id, name, amount, due_date, notes))
        debt_id = cur.lastrowid
        conn.commit()
        return {"ok": True, "debt_id": debt_id}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def get_debts(user_id, include_paid=False):
    conn = get_conn()
    if include_paid:
        rows = conn.execute("""
            SELECT *, 
                CASE 
                    WHEN due_date IS NOT NULL AND due_date < date('now') THEN 1 
                    ELSE 0 
                END as is_overdue
            FROM debts 
            WHERE user_id=?
            ORDER BY is_paid ASC, due_date ASC, created_at DESC
        """, (user_id,)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM debts WHERE user_id=? AND is_paid=0 ORDER BY due_date ASC, created_at DESC",
            (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ========== SAVINGS FUNCTIONS ==========
@retry_on_lock
def add_saving(user_id, name, icon, target_amount, current_amount, target_date, notes):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        cur = conn.execute("""
            INSERT INTO savings(user_id, name, icon, target_amount, current_amount, target_date, notes)
            VALUES(?,?,?,?,?,?,?)
        """, (user_id, name, icon, target_amount, current_amount, target_date, notes))
        saving_id = cur.lastrowid
        conn.commit()
        return {"ok": True, "saving_id": saving_id}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def get_savings(user_id):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM savings 
        WHERE user_id=?
        ORDER BY target_date ASC, created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def update_saving(saving_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(
        f"UPDATE savings SET {fields}, updated_at=datetime('now') WHERE id=? AND user_id=?",
        list(kwargs.values()) + [saving_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def delete_saving(saving_id, user_id):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn = get_conn()
    conn.execute("DELETE FROM savings WHERE id=? AND user_id=?", (saving_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def add_to_saving(saving_id, user_id, amount):
    """Tambahkan dana ke tabungan (update current_amount)"""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        cur = conn.execute("SELECT current_amount FROM savings WHERE id=? AND user_id=?", (saving_id, user_id))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "msg": "Tabungan tidak ditemukan"}
        new_amount = row["current_amount"] + amount
        conn.execute("UPDATE savings SET current_amount=? WHERE id=?", (new_amount, saving_id))
        conn.commit()
        return {"ok": True, "new_amount": new_amount}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def withdraw_from_saving(saving_id, user_id, amount):
    """Kurangi current_amount tabungan, return new amount"""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        cur = conn.execute("SELECT current_amount FROM savings WHERE id=? AND user_id=?", (saving_id, user_id))
        row = cur.fetchone()
        if not row:
            return {"ok": False, "msg": "Tabungan tidak ditemukan"}
        if row["current_amount"] < amount:
            return {"ok": False, "msg": "Saldo tabungan tidak cukup"}
        new_amount = row["current_amount"] - amount
        conn.execute("UPDATE savings SET current_amount=? WHERE id=?", (new_amount, saving_id))
        conn.commit()
        return {"ok": True, "new_amount": new_amount}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def update_debt(debt_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(
        f"UPDATE debts SET {fields} WHERE id=? AND user_id=?",
        list(kwargs.values()) + [debt_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def delete_debt(debt_id, user_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("DELETE FROM debts WHERE id=? AND user_id=?", (debt_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def mark_debt_paid(debt_id, user_id):
    """
    Tandai hutang sebagai lunas, kurangi saldo ekonomi (pemasukan - pengeluaran),
    buat transaksi expense otomatis, TIDAK mempengaruhi gold.
    """
    # Step 1: Ambil data hutang
    conn = get_conn()
    debt = conn.execute("SELECT * FROM debts WHERE id=? AND user_id=? AND is_paid=0", (debt_id, user_id)).fetchone()
    if not debt:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_debt_not_found")}
    debt = dict(debt)
    conn.close()

    # Step 2: Hitung saldo ekonomi saat ini (total pemasukan - total pengeluaran)
    eco_items = get_economy_items(user_id)
    total_income = sum(i['amount'] for i in eco_items if i['type'] == 'income')
    total_expense = sum(i['amount'] for i in eco_items if i['type'] == 'expense')
    current_balance = total_income - total_expense

    # Step 3: Validasi kecukupan saldo
    if current_balance < debt['amount']:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_debt_insufficient_balance", balance=current_balance)}

    # Step 4: Buat transaksi expense otomatis
    from datetime import date
    today = date.today().isoformat()
    expense_name = f"PELUNASAN HUTANG: {debt['name']}"
    add_economy_item(
        user_id,
        name=expense_name,
        icon="💸",
        type_="expense",
        amount=debt["amount"],
        category="Hutang",
        date_str=today,
        notes=f"Pelunasan hutang {debt['name']} (ID hutang {debt_id})"
    )

    # Step 5: Catat activity log (opsional)
    log_activity(user_id, "debt_paid", tr_db(user_id=user_id, key="log_debt_paid", name=debt['name'], amount=debt['amount']), 0, 0)

    # Step 6: Tandai hutang sebagai lunas
    conn2 = get_conn()
    conn2.execute(
        "UPDATE debts SET is_paid=1, paid_at=? WHERE id=?",
        (datetime.now().isoformat(), debt_id))
    conn2.commit()
    conn2.close()

    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_debt_paid", name=debt['name'], amount=debt['amount'])}

def apply_late_debt_penalty(user_id, debt_id, days_late):
    """Terapkan penalti untuk hutang yang terlambat >3 hari.
       Penalti = 10 * (level/5) gold, minimal 10, maksimal 100.
       Penalti hanya diterapkan sekali per hutang.
       Mengembalikan dict dengan jumlah gold yang hilang.
    """
    conn = get_conn()
    try:
        # Cek hutang
        debt = conn.execute(
            "SELECT is_paid, penalty_applied, name FROM debts WHERE id=? AND user_id=?",
            (debt_id, user_id)
        ).fetchone()
        if not debt or debt["is_paid"] == 1 or debt.get("penalty_applied", 0) == 1:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_debt_penalty_already")}
        
        # Ambil data user dari koneksi yang sama
        u = conn.execute("SELECT id, gold, level FROM users WHERE id=?", (user_id,)).fetchone()
        if not u:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_debt_penalty_user_not_found")}
        
        level = u["level"]
        penalty = max(10, min(100, int(10 * (level / 5))))
        current_gold = u["gold"]
        new_gold = max(0, current_gold - penalty)
        
        # Update gold user dan tandai hutang (pakai koneksi yang sama)
        conn.execute("UPDATE users SET gold=? WHERE id=?", (new_gold, user_id))
        conn.execute("UPDATE debts SET penalty_applied=1, penalty_amount=? WHERE id=?", (penalty, debt_id))
        conn.commit()
    finally:
        conn.close()
    
    # Notifikasi & log (koneksi terpisah, setelah conn ditutup)
    log_activity(user_id, "debt_penalty", tr_db(user_id=user_id, key="log_debt_penalty", gold=penalty), 0, -penalty)
    add_notification(user_id, tr_db(user_id=user_id, key="db_debt_penalty_notif", name=debt['name'], days=days_late, gold=penalty), "danger")
    
    return {"ok": True, "gold_lost": penalty}

def get_overdue_debts_count(user_id):
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(*) as cnt FROM debts 
        WHERE user_id=? AND is_paid=0 
        AND due_date IS NOT NULL AND due_date < date('now')
    """, (user_id,)).fetchone()
    conn.close()
    return row["cnt"] if row else 0

def get_total_unpaid_debt(user_id):
    conn = get_conn()
    row = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM debts WHERE user_id=? AND is_paid=0", (user_id,)).fetchone()
    conn.close()
    return row["total"] if row else 0.0


# ========== FOOD & NUTRITION TRACKER ==========

@retry_on_lock
def get_food_items(user_id, include_default=True):
    """Ambil semua makanan (default + custom milik user)."""
    conn = get_conn()
    if include_default:
        rows = conn.execute("""
            SELECT * FROM food_items 
            WHERE is_custom=0 OR (is_custom=1 AND user_id=?)
            ORDER BY name
        """, (user_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM food_items 
            WHERE user_id=? AND is_custom=1
            ORDER BY name
        """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def add_custom_food(user_id, name, icon, calories, protein, carbs, fat):
    """Tambah makanan custom user."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    cur = conn.execute("""
        INSERT INTO food_items(user_id, name, icon, calories, protein, carbs, fat, is_custom)
        VALUES(?,?,?,?,?,?,?,1)
    """, (user_id, name, icon, calories, protein, carbs, fat))
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "id": new_id}

@retry_on_lock
def delete_food_item(user_id, food_id):
    """Hapus makanan custom (hanya milik sendiri)."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("DELETE FROM food_items WHERE id=? AND user_id=? AND is_custom=1", (food_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def log_food(user_id, food_id, serving, meal_type, log_date, notes=""):
    """Catat konsumsi makanan."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    food = conn.execute("SELECT calories, protein, carbs, fat FROM food_items WHERE id=?", (food_id,)).fetchone()
    if not food:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_food_not_found")}
    calories = food["calories"] * serving
    protein = food["protein"] * serving
    carbs = food["carbs"] * serving
    fat = food["fat"] * serving
    conn.execute("""
        INSERT INTO food_logs(user_id, food_id, serving, calories, protein, carbs, fat, meal_type, log_date, notes)
        VALUES(?,?,?,?,?,?,?,?,?,?)
    """, (user_id, food_id, serving, calories, protein, carbs, fat, meal_type, log_date, notes))
    conn.commit()
    conn.close()
    update_daily_net_calories(user_id, log_date)
    return {"ok": True, "calories": calories, "protein": protein, "carbs": carbs, "fat": fat}

@retry_on_lock
def get_food_logs(user_id, log_date=None):
    """Ambil catatan makanan untuk tanggal tertentu (default: hari ini)."""
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    conn = get_conn()
    rows = conn.execute("""
        SELECT fl.*, fi.name, fi.icon 
        FROM food_logs fl
        JOIN food_items fi ON fl.food_id = fi.id
        WHERE fl.user_id=? AND fl.log_date=?
        ORDER BY fl.meal_type, fl.created_at
    """, (user_id, log_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def delete_food_log(user_id, log_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    row = conn.execute("SELECT log_date FROM food_logs WHERE id=? AND user_id=?", (log_id, user_id)).fetchone()
    if not row:
        conn.close()
        return
    log_date = row["log_date"]
    conn.execute("DELETE FROM food_logs WHERE id=? AND user_id=?", (log_id, user_id))
    conn.commit()
    conn.close()
    update_daily_net_calories(user_id, log_date)

@retry_on_lock
def get_nutrition_summary(user_id, log_date=None):
    """Hitung total kalori, protein, carbs, fat untuk suatu tanggal."""
    logs = get_food_logs(user_id, log_date)
    # Jika get_food_logs mengembalikan dict error (akun terkunci)
    if isinstance(logs, dict) and logs.get("ok") is False:
        return {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    # Jika logs bukan list (misal None atau tipe lain), amankan juga
    if not isinstance(logs, list):
        return {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    total = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
    for log in logs:
        total["calories"] += log["calories"]
        total["protein"] += log["protein"]
        total["carbs"] += log["carbs"]
        total["fat"] += log["fat"]
    return total

@retry_on_lock
def get_nutrition_goals(user_id):
    """Ambil target nutrisi harian user."""
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_nutrition_goals WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    # Default goals
    return {"user_id": user_id, "daily_calories": 2000, "daily_protein": 50, 
            "daily_carbs": 250, "daily_fat": 70}

@retry_on_lock
def update_nutrition_goals(user_id, calories, protein, carbs, fat):
    """Update target nutrisi harian."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("""
        INSERT OR REPLACE INTO user_nutrition_goals(user_id, daily_calories, daily_protein, daily_carbs, daily_fat, updated_at)
        VALUES(?,?,?,?,?,datetime('now'))
    """, (user_id, calories, protein, carbs, fat))
    conn.commit()
    conn.close()
    return {"ok": True}

@retry_on_lock
def get_health_goals(user_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM user_health_goals WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"user_id": user_id, "daily_steps": 10000, "daily_sleep_hours": 7.0, "height_cm": 170, "weight_kg": 70}


@retry_on_lock
def update_health_goals(user_id, daily_steps, daily_sleep_hours, height_cm=None, weight_kg=None):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    current = get_health_goals(user_id)
    height_cm = height_cm if height_cm is not None else current.get("height_cm", 170)
    weight_kg = weight_kg if weight_kg is not None else current.get("weight_kg", 70)
    conn.execute("""
        INSERT OR REPLACE INTO user_health_goals(user_id, daily_steps, daily_sleep_hours, height_cm, weight_kg, updated_at)
        VALUES(?,?,?,?,?,datetime('now'))
    """, (user_id, daily_steps, daily_sleep_hours, height_cm, weight_kg))
    conn.commit()
    conn.close()
    return {"ok": True}

@retry_on_lock
def check_daily_nutrition_bonus(user_id, log_date=None):
    """Jika user mencapai minimal 90% target kalori, beri bonus XP 50 dan Gold 10 (sekali sehari)."""
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    
    # Step 1: Cek apakah sudah dapat bonus hari ini, lalu TUTUP koneksi
    conn = get_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM food_achievements WHERE user_id=? AND achievement_date=? AND bonus_claimed=1",
            (user_id, log_date)
        ).fetchone()
    finally:
        conn.close()
    
    if existing:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_nutrition_bonus_claimed")}
    
    # Step 2: Ambil data nutrisi dan target (koneksi terpisah via fungsi masing-masing)
    summary = get_nutrition_summary(user_id, log_date)
    goals = get_nutrition_goals(user_id)
    if goals["daily_calories"] == 0:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_nutrition_goal_not_set")}
    
    percent = (summary["calories"] / goals["daily_calories"]) * 100
    if percent >= 90:
        xp_bonus = 50
        gold_bonus = 10
        # Step 3: Update user (via update_user yang sudah punya koneksi sendiri)
        user = get_user(user_id)
        new_xp = user["xp"] + xp_bonus
        new_gold = user["gold"] + gold_bonus
        new_lvl = user["level"]
        leveled = False
        needed = new_lvl * 150
        while new_xp >= needed:
            new_xp -= needed
            new_lvl += 1
            leveled = True
            needed = new_lvl * 150
        update_user(user_id, xp=new_xp, level=new_lvl, gold=new_gold,
                    total_xp_earned=user.get("total_xp_earned",0) + xp_bonus,
                    total_gold_earned=user.get("total_gold_earned",0.0) + gold_bonus)
        check_achievements(user_id, "calorie_goal", 1)
        # Step 4: Tandai sudah klaim (koneksi baru setelah semua write selesai)
        conn2 = get_conn()
        try:
            conn2.execute(
                "INSERT OR IGNORE INTO food_achievements(user_id, achievement_date, bonus_claimed) VALUES(?,?,1)",
                (user_id, log_date)
            )
            conn2.commit()
        finally:
            conn2.close()
        add_notification(user_id, tr_db(user_id=user_id, key="db_nutrition_bonus_notif", xp=xp_bonus, gold=gold_bonus), "success")
        return {"ok": True, "xp_gained": xp_bonus, "gold_gained": gold_bonus, "leveled_up": leveled}
    return {"ok": False, "msg": tr_db(user_id=user_id, key="db_nutrition_goal_not_reached", percent=percent)}

@retry_on_lock
def get_weekly_calories(user_id):
    """Ambil total kalori per hari untuk 7 hari terakhir (termasuk hari ini)."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT log_date, SUM(calories) as total_calories
        FROM food_logs
        WHERE user_id=? AND log_date >= date('now', '-6 days')
        GROUP BY log_date
        ORDER BY log_date
    """, (user_id,)).fetchall()
    conn.close()
    # Buat dictionary untuk semua 7 hari
    from datetime import date, timedelta
    result = {}
    today = date.today()
    for i in range(7):
        d = (today - timedelta(days=6-i)).isoformat()
        result[d] = 0
    for row in rows:
        result[row["log_date"]] = row["total_calories"] or 0
    return result

@retry_on_lock
def get_water_goal(user_id):
    conn = get_conn()
    row = conn.execute("SELECT daily_ml FROM user_water_goals WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row["daily_ml"] if row else 2000

@retry_on_lock
def set_water_goal(user_id, daily_ml):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("""
        INSERT OR REPLACE INTO user_water_goals(user_id, daily_ml, updated_at)
        VALUES(?,?,datetime('now'))
    """, (user_id, daily_ml))
    conn.commit()
    conn.close()

@retry_on_lock
def add_water_log(user_id, amount_ml, log_date=None):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    conn = get_conn()
    from database import local_now   
    conn.execute("""
        INSERT INTO water_logs(user_id, amount_ml, log_date, created_at)
        VALUES(?,?,?,?)
    """, (user_id, amount_ml, log_date, local_now().isoformat()))
    conn.commit()
    total = get_water_total(user_id, log_date)
    goal = get_water_goal(user_id)
    if total >= goal:
        check_achievements(user_id, "water_goal", 1)
    conn.close()

@retry_on_lock
def get_water_total(user_id, log_date=None):
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    conn = get_conn()
    row = conn.execute("SELECT COALESCE(SUM(amount_ml),0) as total FROM water_logs WHERE user_id=? AND log_date=?", (user_id, log_date)).fetchone()
    conn.close()
    return row["total"]

@retry_on_lock
def delete_water_log(user_id, log_id):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn = get_conn()
    conn.execute("DELETE FROM water_logs WHERE id=? AND user_id=?", (log_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def get_water_logs(user_id, log_date=None):
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM water_logs WHERE user_id=? AND log_date=? ORDER BY created_at DESC", (user_id, log_date)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def get_recipes(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM recipes WHERE user_id=? ORDER BY name", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def get_recipe_details(recipe_id):
    conn = get_conn()
    recipe = conn.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,)).fetchone()
    if not recipe:
        conn.close()
        return None
    items = conn.execute("""
        SELECT ri.*, fi.name, fi.icon, fi.calories, fi.protein, fi.carbs, fi.fat
        FROM recipe_items ri
        JOIN food_items fi ON ri.food_id = fi.id
        WHERE ri.recipe_id=?
    """, (recipe_id,)).fetchall()
    conn.close()
    return {"recipe": dict(recipe), "items": [dict(i) for i in items]}

@retry_on_lock
def add_recipe(user_id, name, icon, serving_size, notes, food_items):
    """food_items: list of (food_id, quantity)"""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    cur = conn.execute("""
        INSERT INTO recipes(user_id, name, icon, serving_size, notes)
        VALUES(?,?,?,?,?)
    """, (user_id, name, icon, serving_size, notes))
    recipe_id = cur.lastrowid
    for food_id, qty in food_items:
        conn.execute("INSERT INTO recipe_items(recipe_id, food_id, quantity) VALUES(?,?,?)",
                     (recipe_id, food_id, qty))
    conn.commit()
    conn.close()
    return {"ok": True, "recipe_id": recipe_id}

@retry_on_lock
def delete_recipe(user_id, recipe_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("DELETE FROM recipes WHERE id=? AND user_id=?", (recipe_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def log_recipe(user_id, recipe_id, serving_multiplier, meal_type, log_date, notes=""):
    """Catat seluruh bahan resep ke food_logs sekaligus."""
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    details = get_recipe_details(recipe_id)
    if not details:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_recipe_not_found")}
    total_cal = 0
    total_pro = 0
    total_carb = 0
    total_fat = 0
    for item in details["items"]:
        qty = item["quantity"] * serving_multiplier
        total_cal += item["calories"] * qty
        total_pro += item["protein"] * qty
        total_carb += item["carbs"] * qty
        total_fat += item["fat"] * qty
    conn = get_conn()
    for item in details["items"]:
        qty = item["quantity"] * serving_multiplier
        conn.execute("""
            INSERT INTO food_logs(user_id, food_id, serving, calories, protein, carbs, fat, meal_type, log_date, notes)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (user_id, item["food_id"], qty, item["calories"]*qty, item["protein"]*qty, item["carbs"]*qty, item["fat"]*qty, meal_type, log_date, notes))
    conn.commit()
    conn.close()
    return {"ok": True, "calories": total_cal, "protein": total_pro, "carbs": total_carb, "fat": total_fat}

@retry_on_lock
def update_sport_calories(activity_id, user_id, calories_burned, duration_minutes):
    """Update data kalori terbakar untuk aktivitas sport."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("""
        UPDATE sport_activities 
        SET calories_burned=?, duration_minutes=?
        WHERE id=? AND user_id=?
    """, (calories_burned, duration_minutes, activity_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def get_total_calories_burned_today(user_id, log_date=None):
    """Total kalori terbakar dari sport hari ini."""
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    conn = get_conn()
    row = conn.execute("""
        SELECT COALESCE(SUM(calories_burned), 0) as total
        FROM sport_activities
        WHERE user_id=? AND done_today=1 AND last_done=?
    """, (user_id, log_date)).fetchone()
    conn.close()
    return row["total"] if row else 0

def get_food_export_data(user_id, days=30):
    """Ambil data nutrisi dan air per hari untuk export (default 30 hari terakhir)."""
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    data = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        d_str = d.isoformat()
        nutri = get_nutrition_summary(user_id, d_str)
        water = get_water_total(user_id, d_str)
        burned = get_total_calories_burned_today(user_id, d_str)
        data.append({
            "date": d_str,
            "calories": nutri['calories'],
            "protein": nutri['protein'],
            "carbs": nutri['carbs'],
            "fat": nutri['fat'],
            "water_ml": water,
            "calories_burned": burned,
            "net_calories": nutri['calories'] - burned
        })
    return data

def get_food_summary_stats(user_id):
    """Ringkasan statistik nutrisi 30 hari terakhir."""
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=29)
    total_calories = 0
    total_water = 0
    days_with_data = 0
    for i in range(30):
        d = (start_date + timedelta(days=i)).isoformat()
        nutri = get_nutrition_summary(user_id, d)
        water = get_water_total(user_id, d)
        if nutri['calories'] > 0 or water > 0:
            days_with_data += 1
        total_calories += nutri['calories']
        total_water += water
    return {
        "avg_calories": total_calories / 30,
        "total_calories_30d": total_calories,
        "avg_water": total_water / 30,
        "total_water_30d": total_water,
        "days_tracked": days_with_data
    }

# ========== HEALTH TRACKER (steps, sleep, etc.) ==========
@retry_on_lock
def add_health_log(user_id, log_date, steps=0, sleep_hours=0, water_ml=0, weight_kg=None, resting_hr=0, stress_level="normal", mood="normal", notes="", net_calories=None):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}

    try:
        # Hitung net_calories jika tidak diberikan
        if net_calories is None:
            food = conn.execute(
                "SELECT COALESCE(SUM(calories),0) as total FROM food_logs WHERE user_id=? AND log_date=?",
                (user_id, log_date)
            ).fetchone()
            total_food = food["total"] if food else 0
            sport = conn.execute(
                "SELECT COALESCE(SUM(calories_burned),0) as total FROM sport_activities "
                "WHERE user_id=? AND done_today=1 AND last_done=?",
                (user_id, log_date)
            ).fetchone()
            total_burned = sport["total"] if sport else 0
            net_calories = total_food - total_burned

        # Cek apakah baris sudah ada
        existing = conn.execute(
            "SELECT id, weight_kg FROM health_logs WHERE user_id=? AND log_date=?",
            (user_id, log_date)
        ).fetchone()

        if existing:
            # Jika weight_kg tidak diberikan (None), gunakan nilai yang sudah ada
            if weight_kg is None:
                weight_kg = existing["weight_kg"] if existing["weight_kg"] is not None else 0.0
            # Update hanya kolom yang diberikan
            conn.execute("""
                UPDATE health_logs 
                SET steps=?, sleep_hours=?, water_ml=?, weight_kg=?, resting_hr=?, 
                    stress_level=?, mood=?, notes=?, net_calories=?
                WHERE id=?
            """, (steps, sleep_hours, water_ml, weight_kg, resting_hr, stress_level, mood, notes, net_calories, existing["id"]))
        else:
            # Insert baru, default weight_kg 0 jika None
            if weight_kg is None:
                weight_kg = 0.0
            conn.execute("""
                INSERT INTO health_logs(user_id, log_date, steps, sleep_hours, water_ml, weight_kg, resting_hr, stress_level, mood, notes, net_calories)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """, (user_id, log_date, steps, sleep_hours, water_ml, weight_kg, resting_hr, stress_level, mood, notes, net_calories))
        conn.commit()
    finally:
        conn.close()

@retry_on_lock
def get_health_logs(user_id, days=7):
    """Ambil health logs untuk `days` terakhir (termasuk hari ini)"""
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=days-1)
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM health_logs
        WHERE user_id=? AND log_date BETWEEN ? AND ?
        ORDER BY log_date
    """, (user_id, start_date.isoformat(), end_date.isoformat())).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_daily_net_calories(user_id, log_date):
    """Hitung net kalori = total makanan - total kalori terbakar, lalu simpan ke health_logs.
       Hanya perbarui kolom net_calories, tanpa menghapus data lain.
    """
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        # Total kalori dari makanan
        food = conn.execute(
            "SELECT COALESCE(SUM(calories),0) as total FROM food_logs WHERE user_id=? AND log_date=?",
            (user_id, log_date)
        ).fetchone()
        total_food = food["total"] if food else 0

        # Total kalori terbakar dari sport (hanya yang sudah done_today)
        sport = conn.execute(
            "SELECT COALESCE(SUM(calories_burned),0) as total FROM sport_activities "
            "WHERE user_id=? AND done_today=1 AND last_done=?",
            (user_id, log_date)
        ).fetchone()
        total_burned = sport["total"] if sport else 0

        net_cal = total_food - total_burned

        # Cek apakah sudah ada baris untuk tanggal ini
        existing = conn.execute(
            "SELECT id FROM health_logs WHERE user_id=? AND log_date=?",
            (user_id, log_date)
        ).fetchone()

        if existing:
            # UPDATE, hanya kolom net_calories
            conn.execute(
                "UPDATE health_logs SET net_calories=? WHERE id=?",
                (net_cal, existing["id"])
            )
        else:
            # INSERT baru, kolom lain akan bernilai default (0/null)
            conn.execute(
                "INSERT INTO health_logs(user_id, log_date, net_calories) VALUES(?,?,?)",
                (user_id, log_date, net_cal)
            )
        conn.commit()
    finally:
        conn.close()

@retry_on_lock
def get_health_summary(user_id, days=30):
    """Rata-rata health metrics selama `days` hari terakhir, dengan avg water dari water_logs."""
    from datetime import date, timedelta
    start_date = date.today() - timedelta(days=days-1)
    conn = get_conn()

    # 1. Ambil rata-rata steps, sleep, weight, hr dari health_logs
    row = conn.execute("""
        SELECT AVG(steps) as avg_steps,
               AVG(sleep_hours) as avg_sleep,
               AVG(weight_kg) as avg_weight,
               AVG(resting_hr) as avg_hr,
               COUNT(*) as days_recorded
        FROM health_logs
        WHERE user_id=? AND log_date >= ?
    """, (user_id, start_date.isoformat())).fetchone()

    # 2. Ambil rata-rata air per hari dari water_logs (hanya hari yang ada catatan)
    water_row = conn.execute("""
        SELECT AVG(daily_total) as avg_water
        FROM (
            SELECT SUM(amount_ml) as daily_total
            FROM water_logs
            WHERE user_id=? AND log_date >= ?
            GROUP BY log_date
        )
    """, (user_id, start_date.isoformat())).fetchone()
    conn.close()

    avg_water = int(water_row['avg_water'] or 0) if water_row else 0

    if row and row['days_recorded']:
        return {
            'avg_steps': int(row['avg_steps'] or 0),
            'avg_sleep': round(row['avg_sleep'] or 0, 1),
            'avg_water': avg_water,
            'avg_weight': round(row['avg_weight'] or 0, 1),
            'avg_hr': int(row['avg_hr'] or 0),
            'days_recorded': row['days_recorded']
        }
    return {'avg_steps': 0, 'avg_sleep': 0, 'avg_water': 0, 'avg_weight': 0.0, 'avg_hr': 0, 'days_recorded': 0}

# ========== DEBT INSTALLMENT ==========
@retry_on_lock
def pay_debt_installment(debt_id, user_id, amount):
    """
    Membayar sebagian hutang.
    - amount: jumlah yang dibayar (akan dikurangi dari hutang)
    - Membuat transaksi expense di economy_items
    - Jika hutang lunas, tandai is_paid=1
    - Tidak mempengaruhi gold (hanya catatan ekonomi)
    """
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Step 1: Ambil data hutang
    conn = get_conn()
    debt = conn.execute(
        "SELECT id, name, amount, is_paid FROM debts WHERE id=? AND user_id=? AND is_paid=0",
        (debt_id, user_id)
    ).fetchone()
    if not debt:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_debt_not_found")}
    debt = dict(debt)
    conn.close()

    if amount <= 0:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_installment_zero")}
    if amount > debt['amount']:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_installment_exceed", amount=debt['amount'])}

    # Step 2: Catat transaksi expense di economy_items
    from datetime import date
    today = date.today().isoformat()
    expense_name = f"CICILAN HUTANG: {debt['name']} (Rp{amount:.0f})"
    add_economy_item(
        user_id,
        name=expense_name,
        icon="💸",
        type_="expense",
        amount=amount,
        category="Hutang",
        date_str=today,
        notes=f"Cicilan hutang {debt['name']} (ID {debt_id})"
    )

    # Step 3: Update sisa hutang
    remaining = debt['amount'] - amount
    conn2 = get_conn()
    if remaining <= 0.01:
        # Lunas
        conn2.execute(
            "UPDATE debts SET amount=0, is_paid=1, paid_at=? WHERE id=?",
            (datetime.now().isoformat(), debt_id)
        )
    else:
        conn2.execute(
            "UPDATE debts SET amount=? WHERE id=?",
            (remaining, debt_id)
        )
    conn2.commit()
    conn2.close()

    # Step 4: Log aktivitas
    log_activity(user_id, "debt_installment", tr_db(user_id=user_id, key="log_debt_installment", name=debt['name'], amount=amount), 0, 0)

    return {"ok": True, "remaining": remaining, "msg": tr_db(user_id=user_id, key="db_debt_installment", amount=amount, remaining=remaining)}

# ========== ACHIEVEMENT SYSTEM ==========
ACHIEVEMENTS_REBALANCED = [
    # ---- Level ----
    ("Pemula", "Mencapai level 5", "🎯", "level", "level_reach", 5, 150, 75),
    ("Prajurit", "Mencapai level 10", "⚔️", "level", "level_reach", 10, 300, 150),
    ("Ksatria", "Mencapai level 20", "🛡️", "level", "level_reach", 20, 600, 300),
    ("Legenda", "Mencapai level 50", "👑", "level", "level_reach", 50, 2000, 800),

    # ---- Habits ----
    ("Habit Starter", "Selesaikan 10 habit (positif)", "✅", "habit", "habit_complete", 10, 80, 30),
    ("Habit Enthusiast", "Selesaikan 50 habit", "🔥", "habit", "habit_complete", 50, 250, 100),
    ("Habit Master", "Selesaikan 200 habit", "💪", "habit", "habit_complete", 200, 600, 250),
    ("Streak Warrior", "Pertahankan streak habit 7 hari", "⚡", "habit", "habit_streak", 7, 150, 50),
    ("Streak Legend", "Pertahankan streak habit 30 hari", "🏅", "habit", "habit_streak", 30, 600, 200),

    # ---- Dailies ----
    ("Daily Doer", "Selesaikan 20 daily", "📅", "daily", "daily_complete", 20, 100, 40),
    ("Daily Devotee", "Selesaikan 100 daily", "🌟", "daily", "daily_complete", 100, 400, 150),

    # ---- Todos ----
    ("Quest Beginner", "Selesaikan 10 quest", "📜", "todo", "todo_complete", 10, 80, 30),
    ("Quest Champion", "Selesaikan 50 quest", "🏆", "todo", "todo_complete", 50, 300, 100),

    # ---- Sport ----
    ("Sport Rookie", "Kumpulkan 100 sport points", "🏃", "sport", "sport_points", 100, 150, 50),
    ("Sport Athlete", "Kumpulkan 500 sport points", "🏅", "sport", "sport_points", 500, 400, 150),
    ("Sport Legend", "Kumpulkan 2000 sport points", "🏆", "sport", "sport_points", 2000, 1000, 400),
    ("Sport Streak 7", "Sport streak 7 hari", "🔥", "sport", "sport_streak", 7, 150, 60),

    # ---- Economy ----
    ("Saver", "Kumpulkan total 1000 Gold", "💰", "economy", "total_gold", 1000, 150, 75),
    ("Rich Player", "Kumpulkan total 10000 Gold", "💎", "economy", "total_gold", 10000, 600, 300),
    ("Big Spender", "Belanjakan total 5000 Gold di shop", "🛒", "economy", "total_spent", 5000, 300, 100),

    # ---- Pets ----
    ("Pet Lover", "Adopsi 1 pet", "🐾", "pet", "pet_adopt", 1, 80, 30),
    ("Pet Collector", "Adopsi 3 pets", "🐕", "pet", "pet_adopt", 3, 200, 80),
    ("Pet Master", "Adopsi 5 pets", "🐉", "pet", "pet_adopt", 5, 400, 150),

    # ---- Guild & Boss ----
    ("Guild Member", "Bergabung ke guild", "👥", "guild", "join_guild", 1, 150, 75),
    ("Boss Slayer", "Mengalahkan 1 boss", "⚔️", "boss", "boss_kill", 1, 300, 100),
    ("Boss Hunter", "Mengalahkan 5 boss", "🏹", "boss", "boss_kill", 5, 600, 250),

    # ---- Social ----
    ("Friendly", "Miliki 1 teman", "👫", "social", "friend_count", 1, 80, 30),
    ("Popular", "Miliki 5 teman", "🎉", "social", "friend_count", 5, 200, 80),

    # ---- Health & Food ----
    ("Health Tracker", "Catat kesehatan 7 hari berturut-turut", "💚", "health", "health_streak", 7, 150, 60),
    ("Calorie Master", "Mencapai target kalori 10 kali", "🍎", "nutrition", "calorie_goal", 10, 200, 80),
    ("Hydration Hero", "Mencapai target air 20 kali", "💧", "nutrition", "water_goal", 20, 250, 100),

    # ---- Special ----
    ("Completionist", "Selesaikan 1000 tugas total (habit+daily+todo)", "🏆", "special", "total_tasks", 1000, 2500, 1000),
    ("All-Rounder", "Dapatkan minimal 1 achievement dari setiap kategori", "🌟", "special", "category_mastery", 1, 1500, 600),

    # ========== 10 ACHIEVEMENT BARU ==========
    ("Explorer", "Selesaikan 100 quest", "🗺️", "todo", "todo_complete", 100, 300, 100),
    ("Gym Rat", "Kumpulkan 1000 sport points", "🏋️", "sport", "sport_points", 1000, 400, 150),
    ("Millionaire", "Kumpulkan total 50000 Gold", "💰", "economy", "total_gold", 50000, 1000, 500),
    ("Shopaholic", "Belanjakan total 20000 Gold di shop", "🛍️", "economy", "total_spent", 20000, 500, 200),
    ("Pet Breeder", "Adopsi 10 pets", "🐶", "pet", "pet_adopt", 10, 500, 250),
    ("Boss Slayer Elite", "Mengalahkan 20 boss", "⚔️", "boss", "boss_kill", 20, 1000, 400),
    ("Social Butterfly", "Miliki 10 teman", "🦋", "social", "friend_count", 10, 300, 150),
    ("Health Nut", "Catat kesehatan 30 hari berturut-turut", "🥦", "health", "health_streak", 30, 500, 200),
    ("Calorie Crusher", "Mencapai target kalori 50 kali", "🔥", "nutrition", "calorie_goal", 50, 600, 250),
    ("Hydration Champion", "Mencapai target air 50 kali", "💪", "nutrition", "water_goal", 50, 600, 250),
]

def init_achievements():
    """Insert data achievement default jika belum ada."""
    conn = get_conn()
    cur = conn.cursor()
    # Cek apakah sudah ada data
    cur.execute("SELECT COUNT(*) FROM achievements")
    if cur.fetchone()[0] > 0:
        conn.close()
        return
    
    achievements = [
        # ---- Level & XP ----
        ("Pemula", "Mencapai level 5", "🎯", "level", "level_reach", 5, 100, 50),
        ("Prajurit", "Mencapai level 10", "⚔️", "level", "level_reach", 10, 250, 100),
        ("Ksatria", "Mencapai level 20", "🛡️", "level", "level_reach", 20, 500, 200),
        ("Legenda", "Mencapai level 50", "👑", "level", "level_reach", 50, 1500, 500),
        # ---- Habits ----
        ("Habit Starter", "Selesaikan 10 habit (positif)", "✅", "habit", "habit_complete", 10, 50, 20),
        ("Habit Enthusiast", "Selesaikan 50 habit", "🔥", "habit", "habit_complete", 50, 200, 80),
        ("Habit Master", "Selesaikan 200 habit", "💪", "habit", "habit_complete", 200, 500, 200),
        ("Streak Warrior", "Pertahankan streak habit 7 hari", "⚡", "habit", "habit_streak", 7, 100, 30),
        ("Streak Legend", "Pertahankan streak habit 30 hari", "🏅", "habit", "habit_streak", 30, 500, 150),
        # ---- Dailies ----
        ("Daily Doer", "Selesaikan 20 daily", "📅", "daily", "daily_complete", 20, 80, 30),
        ("Daily Devotee", "Selesaikan 100 daily", "🌟", "daily", "daily_complete", 100, 300, 100),
        # ---- Todos ----
        ("Quest Beginner", "Selesaikan 10 quest", "📜", "todo", "todo_complete", 10, 60, 25),
        ("Quest Champion", "Selesaikan 50 quest", "🏆", "todo", "todo_complete", 50, 250, 80),
        # ---- Sport ----
        ("Sport Rookie", "Kumpulkan 100 sport points", "🏃", "sport", "sport_points", 100, 100, 30),
        ("Sport Athlete", "Kumpulkan 500 sport points", "🏅", "sport", "sport_points", 500, 300, 100),
        ("Sport Legend", "Kumpulkan 2000 sport points", "🏆", "sport", "sport_points", 2000, 800, 300),
        ("Sport Streak 7", "Sport streak 7 hari", "🔥", "sport", "sport_streak", 7, 100, 40),
        # ---- Economy ----
        ("Saver", "Kumpulkan total 1000 Gold", "💰", "economy", "total_gold", 1000, 100, 50),
        ("Rich Player", "Kumpulkan total 10000 Gold", "💎", "economy", "total_gold", 10000, 500, 200),
        ("Big Spender", "Belanjakan total 5000 Gold di shop", "🛒", "economy", "total_spent", 5000, 200, 80),
        # ---- Pets ----
        ("Pet Lover", "Adopsi 1 pet", "🐾", "pet", "pet_adopt", 1, 50, 20),
        ("Pet Collector", "Adopsi 3 pets", "🐕", "pet", "pet_adopt", 3, 150, 60),
        ("Pet Master", "Adopsi 5 pets", "🐉", "pet", "pet_adopt", 5, 300, 120),
        # ---- Guild & Boss ----
        ("Guild Member", "Bergabung ke guild", "👥", "guild", "join_guild", 1, 100, 50),
        ("Boss Slayer", "Mengalahkan 1 boss", "⚔️", "boss", "boss_kill", 1, 200, 80),
        ("Boss Hunter", "Mengalahkan 5 boss", "🏹", "boss", "boss_kill", 5, 500, 200),
        # ---- Social ----
        ("Friendly", "Miliki 1 teman", "👫", "social", "friend_count", 1, 50, 20),
        ("Popular", "Miliki 5 teman", "🎉", "social", "friend_count", 5, 150, 60),
        # ---- Health & Food ----
        ("Health Tracker", "Catat kesehatan 7 hari berturut-turut", "💚", "health", "health_streak", 7, 100, 40),
        ("Calorie Master", "Mencapai target kalori 10 kali", "🍎", "nutrition", "calorie_goal", 10, 150, 60),
        ("Hydration Hero", "Mencapai target air 20 kali", "💧", "nutrition", "water_goal", 20, 200, 80),
        # ---- Special ----
        ("Completionist", "Selesaikan 1000 tugas total (habit+daily+todo)", "🏆", "special", "total_tasks", 1000, 2000, 800),
        ("All-Rounder", "Dapatkan minimal 1 achievement dari setiap kategori", "🌟", "special", "category_mastery", 1, 1000, 400),
    ]
    
    for ach in achievements:
        cur.execute("""
            INSERT INTO achievements(name, description, icon, category, requirement_type, requirement_value, xp_reward, gold_reward)
            VALUES(?,?,?,?,?,?,?,?)
        """, ach)
    conn.commit()
    conn.close()
    print(f"[Achievements] {len(achievements)} achievements initialized.")

def migrate_achievements():
    """Update/rebalance achievement yang sudah ada dan tambah yang baru."""
    conn = get_conn()
    cur = conn.cursor()
    for ach in ACHIEVEMENTS_REBALANCED:
        name, desc, icon, category, req_type, req_val, xp, gold = ach
        # Cek apakah achievement sudah ada
        existing = cur.execute(
            "SELECT id, xp_reward, gold_reward, requirement_value FROM achievements WHERE name = ?",
            (name,)
        ).fetchone()
        if existing:
            # Update jika ada perubahan
            if (existing["requirement_value"] != req_val or
                existing["xp_reward"] != xp or
                existing["gold_reward"] != gold):
                cur.execute("""
                    UPDATE achievements
                    SET description=?, icon=?, category=?, requirement_type=?,
                        requirement_value=?, xp_reward=?, gold_reward=?
                    WHERE id=?
                """, (desc, icon, category, req_type, req_val, xp, gold, existing["id"]))
        else:
            # Insert baru
            cur.execute("""
                INSERT INTO achievements(name, description, icon, category, requirement_type,
                                         requirement_value, xp_reward, gold_reward)
                VALUES(?,?,?,?,?,?,?,?)
            """, (name, desc, icon, category, req_type, req_val, xp, gold))
    conn.commit()
    conn.close()
    print(f"[Achievements] Migrated {len(ACHIEVEMENTS_REBALANCED)} achievements.")

def get_achievements_list():
    """Ambil semua data achievement."""
    conn = get_conn()
    rows = conn.execute("SELECT * FROM achievements ORDER BY category, requirement_value").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_achievements(user_id):
    """Ambil data progress user untuk semua achievement."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT a.*, 
               COALESCE(ua.progress, 0) as progress,
               ua.unlocked_at,
               ua.claimed
        FROM achievements a
        LEFT JOIN user_achievements ua ON a.id = ua.achievement_id AND ua.user_id = ?
        ORDER BY a.category, a.requirement_value
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def check_achievements(user_id, event_type, value=1, extra_data=None):
    """Dipanggil setiap kali ada aksi. Update progress achievement.
    Sekarang lebih aman: reward hanya sekali, progress tidak regresif.
    """
    conn = get_conn()
    # Ambil semua achievement yang requirement_type-nya sesuai
    rows = conn.execute("SELECT * FROM achievements WHERE requirement_type = ?", (event_type,)).fetchall()
    if not rows:
        conn.close()
        return []
    
    unlocked_list = []
    for ach in rows:
        ach_id = ach["id"]
        req_val = ach["requirement_value"]
        
        # Ambil progress saat ini
        cur = conn.execute(
            "SELECT progress, unlocked_at, claimed FROM user_achievements WHERE user_id=? AND achievement_id=?",
            (user_id, ach_id)
        ).fetchone()
        progress = cur["progress"] if cur else 0
        already_unlocked = cur and cur["unlocked_at"] is not None
        
        # Hitung progress baru berdasarkan tipe event
        new_progress = progress
        if event_type in ("habit_streak", "sport_streak", "health_streak", "level_reach"):
            # Untuk streak/level, kita simpan nilai maksimum yang pernah dicapai
            new_progress = max(progress, value)
        elif event_type == "total_tasks":
            # value adalah total tasks saat ini
            new_progress = value
        elif event_type == "total_gold":
            new_progress = value
        elif event_type == "total_spent":
            new_progress = value
        else:
            # Default: increment
            new_progress = progress + value
        
        # Simpan progress (selalu update)
        if cur:
            conn.execute(
                "UPDATE user_achievements SET progress=? WHERE user_id=? AND achievement_id=?",
                (new_progress, user_id, ach_id)
            )
        else:
            conn.execute(
                "INSERT INTO user_achievements(user_id, achievement_id, progress) VALUES(?,?,?)",
                (user_id, ach_id, new_progress)
            )
        
        # Cek apakah baru tercapai (belum pernah unlock)
        if not already_unlocked and new_progress >= req_val:
            unlocked_time = datetime.now().isoformat()
            conn.execute(
                "UPDATE user_achievements SET unlocked_at=?, progress=? WHERE user_id=? AND achievement_id=?",
                (unlocked_time, req_val, user_id, ach_id)
            )
            unlocked_list.append(dict(ach))
    
    conn.commit()
    conn.close()
    
    for ach in unlocked_list:
        gain_xp_gold(user_id, ach["xp_reward"], ach["gold_reward"], skip_achievements=True)
        add_notification(user_id, tr_db(user_id=user_id, key="db_achievement_unlocked", icon=ach['icon'], name=ach['name'], xp=ach['xp_reward'], gold=ach['gold_reward']), "success")
        log_activity(user_id, "achievement", tr_db(user_id=user_id, key="log_achievement", name=ach['name']), ach["xp_reward"], ach["gold_reward"])
    return unlocked_list

def claim_achievement_reward(user_id, achievement_id):
    """Klaim reward jika achievement sudah unlocked tapi belum diklaim (opsional)."""
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn = get_conn()
    ua = conn.execute(
        "SELECT claimed, unlocked_at FROM user_achievements WHERE user_id=? AND achievement_id=? AND unlocked_at IS NOT NULL",
        (user_id, achievement_id)
    ).fetchone()
    if not ua or ua["claimed"]:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_achievement_reward_unavailable")}
    
    ach = conn.execute("SELECT xp_reward, gold_reward FROM achievements WHERE id=?", (achievement_id,)).fetchone()
    if not ach:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_achievement_not_found")}
    
    conn.execute("UPDATE user_achievements SET claimed=1 WHERE user_id=? AND achievement_id=?", (user_id, achievement_id))
    conn.commit()
    conn.close()
    
    gain_xp_gold(user_id, ach["xp_reward"], ach["gold_reward"])
    add_notification(user_id, tr_db(user_id=user_id, key="db_achievement_claimed", xp=ach['xp_reward'], gold=ach['gold_reward']), "info")
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_achievement_reward_claimed")}

def update_total_tasks(user_id):
    conn = get_conn()
    conn.execute("UPDATE users SET total_tasks_completed = total_tasks_completed + 1 WHERE id=?", (user_id,))
    new_total = conn.execute("SELECT total_tasks_completed FROM users WHERE id=?", (user_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    check_achievements(user_id, "total_tasks", new_total)

def update_total_spent(user_id, amount):
    conn = get_conn()
    conn.execute("UPDATE users SET total_gold_spent = COALESCE(total_gold_spent,0) + ? WHERE id=?", (amount, user_id))
    new_total = conn.execute("SELECT total_gold_spent FROM users WHERE id=?", (user_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    check_achievements(user_id, "total_spent", new_total)

def update_total_gold_earned(user_id, amount):
    conn = get_conn()
    conn.execute("UPDATE users SET total_gold_earned = total_gold_earned + ? WHERE id=?", (amount, user_id))
    new_total = conn.execute("SELECT total_gold_earned FROM users WHERE id=?", (user_id,)).fetchone()[0]
    conn.commit()
    conn.close()
    check_achievements(user_id, "total_gold", new_total)

def delete_account(user_id, password):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    u = get_user(user_id)
    if not u or _hash(password) != u.get("password_hash", ""):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_delete_account_wrong_password")}
    
    conn = get_conn()
    try:
        # Matikan foreign key sementara agar tidak ada constraint error
        conn.execute("PRAGMA foreign_keys = OFF")
        
        # 1. Hapus semua data yang terkait dengan user_id
        conn.execute("DELETE FROM user_pets WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM inventory WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM economy_items WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM debts WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM savings WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM food_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM water_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM health_logs WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM habits WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM dailies WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM todos WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM sport_activities WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM task_folders WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM activity_log WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM backup_codes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
        conn.execute("DELETE FROM friends WHERE user_id = ? OR friend_id = ?", (user_id, user_id))
        conn.execute("DELETE FROM guild_members WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_invites WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_requests WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_messages WHERE sender_id = ?", (user_id,))
        conn.execute("DELETE FROM boss_rewards WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_achievements WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_nutrition_goals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM food_achievements WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_water_goals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM user_health_goals WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM recipes WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_leader_transfers WHERE old_leader_id = ?", (user_id,))
        
        # 2. Handle jika user adalah leader guild
        guilds = conn.execute("SELECT id FROM guilds WHERE leader_id = ?", (user_id,)).fetchall()
        for guild in guilds:
            other = conn.execute("SELECT user_id FROM guild_members WHERE guild_id = ? LIMIT 1", (guild["id"],)).fetchone()
            if other:
                conn.execute("UPDATE guilds SET leader_id = ? WHERE id = ?", (other["user_id"], guild["id"]))
            else:
                conn.execute("DELETE FROM guilds WHERE id = ?", (guild["id"],))
        
        # 3. Terakhir, hapus user
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_delete_account_failed", error=str(e))}
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()
    
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_delete_account_success")}

# ── INVESTING ──────────────────────────────────────────────────────────────
@retry_on_lock
def add_investment(user_id, name, icon, amount, notes=''):
    """Tambahkan kartu investasi baru. Amount diambil dari saldo ekonomi."""
    # Validasi saldo (maksimal 10% dari saldo)
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    try:
        # Hitung saldo ekonomi saat ini
        rows = conn.execute("SELECT type, amount FROM economy_items WHERE user_id=?", (user_id,)).fetchall()
        total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
        total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
        balance = total_income - total_expense
        if amount <= 0 or amount > balance:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_exceeds_balance", balance=balance)}
        if amount > balance * 0.1:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_max_10", max=balance*0.1)}
    finally:
        conn.close()

    # Kurangi saldo melalui economy_items (buat expense)
    from datetime import date
    add_economy_item(user_id, name=f"Investasi: {name}", icon=icon,
                     type_="expense", amount=amount, category="Investasi",
                     date_str=date.today().isoformat(), notes=notes)
    # Tambahkan ke tabel investments
    conn2 = get_conn()
    cur = conn2.execute("""
        INSERT INTO investments(user_id, name, icon, amount, notes)
        VALUES(?,?,?,?,?)
    """, (user_id, name, icon, amount, notes))
    inv_id = cur.lastrowid
    conn2.commit()
    conn2.close()
    log_activity(user_id, "invest", tr_db(user_id=user_id, key="log_invest", name=name, amount=amount), 0, -amount)
    return {"ok": True, "invest_id": inv_id, "msg": tr_db(user_id=user_id, key="db_investment_success", name=name, amount=amount)}

@retry_on_lock
def add_investment_return(invest_id, user_id, amount):
    """Tambah nilai investasi secara manual sebesar amount (IDR)."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    inv = conn.execute("SELECT amount FROM investments WHERE id=? AND user_id=? AND is_active=1", (invest_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_not_found")}
    new_amount = inv['amount'] + amount
    conn.execute("UPDATE investments SET amount=?, last_update=datetime('now') WHERE id=?", (new_amount, invest_id))
    conn.commit()
    conn.close()
    log_activity(user_id, "invest_return", tr_db(user_id=user_id, key="log_invest_return", amount=amount), 0, 0)
    return {"ok": True, "gain": amount, "new_amount": new_amount}

@retry_on_lock
def get_investments(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM investments WHERE user_id=? AND is_active=1 ORDER BY invested_date DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def delete_investment(invest_id, user_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("UPDATE investments SET is_active=0 WHERE id=? AND user_id=?", (invest_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def update_investment(invest_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE investments SET {fields}, last_update=datetime('now') WHERE id=? AND user_id=?", 
                 list(kwargs.values()) + [invest_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def collect_investment_return(invest_id, user_id, percent=5):
    """Tambah nilai investasi secara manual sebesar persen tertentu (default 5% dari amount saat ini)."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    inv = conn.execute("SELECT amount FROM investments WHERE id=? AND user_id=? AND is_active=1", (invest_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_not_found")}
    gain = inv['amount'] * percent / 100
    if gain <= 0:
        gain = 100  # minimal gain 100 jika amount kecil
    new_amount = inv['amount'] + gain
    conn.execute("UPDATE investments SET amount=?, last_update=datetime('now') WHERE id=?", (new_amount, invest_id))
    conn.commit()
    conn.close()
    log_activity(user_id, "invest_return", f"Return investasi +{gain:.0f}", 0, 0)
    return {"ok": True, "gain": gain, "new_amount": new_amount}

@retry_on_lock
def withdraw_investment(invest_id, user_id):
    """Tarik semua dana investasi, masukkan ke income, lalu nonaktifkan kartu."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    inv = conn.execute("SELECT name, amount FROM investments WHERE id=? AND user_id=? AND is_active=1", (invest_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_not_found")}
    amount = inv['amount']
    if amount <= 0:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_investment_no_funds")}
    # Catat sebagai income
    from datetime import date
    add_economy_item(user_id, name=f"Penarikan Investasi: {inv['name']}", icon="📈",
                     type_="income", amount=amount, category="Investasi",
                     date_str=date.today().isoformat(), notes="Penarikan dana investasi")
    # Nonaktifkan investasi
    conn.execute("UPDATE investments SET is_active=0 WHERE id=?", (invest_id,))
    conn.commit()
    conn.close()
    log_activity(user_id, "invest_withdraw", tr_db(user_id=user_id, key="log_invest_withdraw", name=inv['name'], amount=amount), 0, amount)
    return {"ok": True, "amount": amount, "msg": tr_db(user_id=user_id, key="db_investment_withdrawn", amount=amount)}

# ── SUBSCRIPTION ───────────────────────────────────────────────────────────
@retry_on_lock
def add_subscription(user_id, name, icon, amount, due_date, period, is_recurring, notes=''):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    cur = conn.execute("""
        INSERT INTO subscriptions(user_id, name, icon, amount, due_date, period, is_recurring, notes)
        VALUES(?,?,?,?,?,?,?,?)
    """, (user_id, name, icon, amount, due_date, period, 1 if is_recurring else 0, notes))
    sub_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "subscription_id": sub_id}

@retry_on_lock
def get_subscriptions(user_id, active_only=True):
    conn = get_conn()
    if active_only:
        rows = conn.execute("SELECT * FROM subscriptions WHERE user_id=? AND is_active=1 ORDER BY due_date ASC", (user_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM subscriptions WHERE user_id=? ORDER BY due_date ASC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def delete_subscription(sub_id, user_id):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("UPDATE subscriptions SET is_active=0 WHERE id=? AND user_id=?", (sub_id, user_id))
    conn.commit()
    conn.close()

@retry_on_lock
def update_subscription(sub_id, user_id, **kwargs):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    if not kwargs:
        return
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn = get_conn()
    conn.execute(f"UPDATE subscriptions SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [sub_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def renew_subscription(sub_id, user_id, auto_pay=True):
    """Perpanjang subscription: untuk non-recurring (manual) atau recurring (auto charge)."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    sub = conn.execute("SELECT name, amount, due_date, period, is_recurring FROM subscriptions WHERE id=? AND user_id=? AND is_active=1", (sub_id, user_id)).fetchone()
    if not sub:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_subscription_not_found")}
    sub = dict(sub)
    today = date.today().isoformat()
    if auto_pay and sub['is_recurring']:
        # Cek saldo ekonomi
        rows = conn.execute("SELECT type, amount FROM economy_items WHERE user_id=?", (user_id,)).fetchall()
        total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
        total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
        balance = total_income - total_expense
        if balance < sub['amount']:
            conn.close()
            add_notification(user_id, tr_db(user_id=user_id, key="db_subscription_insufficient_notif", name=sub['name'], amount=sub['amount']), "danger")
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_subscription_insufficient_balance")}
        # Catat expense
        add_economy_item(user_id, name=f"Langganan: {sub['name']}", icon="📅",
                         type_="expense", amount=sub['amount'], category="Subscription",
                         date_str=today, notes=f"Perpanjangan otomatis")
        # Update due_date
        new_due = date.today()
        if sub['period'] == 'monthly':
            from dateutil.relativedelta import relativedelta
            new_due += relativedelta(months=1)
        elif sub['period'] == 'yearly':
            new_due += relativedelta(years=1)
        else:
            new_due = None  # one-time tidak auto renew
        if new_due:
            conn.execute("UPDATE subscriptions SET due_date=?, last_charged=? WHERE id=?", (new_due.isoformat(), today, sub_id))
        else:
            # one-time: nonaktifkan setelah renew (manual)
            conn.execute("UPDATE subscriptions SET is_active=0, last_charged=? WHERE id=?", (today, sub_id))
            add_notification(user_id, tr_db(user_id=user_id, key="db_subscription_renew_warning", name=sub['name']), "warning")
        conn.commit()
        conn.close()
        log_activity(user_id, "subscription", tr_db(user_id=user_id, key="log_subscription_auto", name=sub['name'], amount=sub['amount']), 0, -sub['amount'])
        add_notification(user_id, tr_db(user_id=user_id, key="db_subscription_renewed_auto_notif", name=sub['name'], amount=sub['amount']), "success")
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_subscription_renewed_auto")}
    else:
        # Renew manual (pengguna klik tombol Renew)
        if not auto_pay:
            # Cek saldo dulu
            rows = conn.execute("SELECT type, amount FROM economy_items WHERE user_id=?", (user_id,)).fetchall()
            total_income = sum(r['amount'] for r in rows if r['type'] == 'income')
            total_expense = sum(r['amount'] for r in rows if r['type'] == 'expense')
            balance = total_income - total_expense
            if balance < sub['amount']:
                conn.close()
                return {"ok": False, "msg": tr_db(user_id=user_id, key="db_subscription_insufficient_balance")}
            add_economy_item(user_id, name=f"Langganan: {sub['name']}", icon="📅",
                             type_="expense", amount=sub['amount'], category="Subscription",
                             date_str=today, notes="Perpanjangan manual")
        # Update due_date
        new_due = date.today()
        if sub['period'] == 'monthly':
            from dateutil.relativedelta import relativedelta
            new_due += relativedelta(months=1)
        elif sub['period'] == 'yearly':
            new_due += relativedelta(years=1)
        else:
            new_due = None
        if new_due:
            conn.execute("UPDATE subscriptions SET due_date=?, last_charged=?, is_active=1 WHERE id=?", (new_due.isoformat(), today, sub_id))
        else:
            conn.execute("UPDATE subscriptions SET last_charged=?, is_active=1 WHERE id=?", (today, sub_id))
        conn.commit()
        conn.close()
        log_activity(user_id, "subscription", tr_db(user_id=user_id, key="log_subscription_manual", name=sub['name'], amount=sub['amount']), 0, -sub['amount'])
        add_notification(user_id, tr_db(user_id=user_id, key="db_subscription_renew_manual_success", name=sub['name'], date=new_due), "success")
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_subscription_renewed_manual")}

def check_all_subscriptions(user_id):
    """Cek semua subscription user yang melewati due_date. Untuk recurring auto-charge otomatis."""
    subs = get_subscriptions(user_id, active_only=True)
    today = date.today().isoformat()
    for sub in subs:
        if sub['due_date'] < today:
            if sub['is_recurring']:
                renew_subscription(sub['id'], user_id, auto_pay=True)
            else:
                add_notification(user_id, tr_db(user_id=user_id, key="db_subscription_expired_notif", name=sub['name'], date=sub['due_date']), "warning")

# ========== CURRENCY SETTINGS ========== #
def get_user_currency(user_id):
    conn = get_conn()
    row = conn.execute("SELECT currency FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["currency"] if row else "IDR"

def set_user_currency(user_id, currency):
    conn = get_conn()
    conn.execute("UPDATE users SET currency=? WHERE id=?", (currency, user_id))
    conn.commit()
    conn.close()

# Currency conversion rates (hardcoded, bisa diupdate nanti)
CURRENCY_RATES = {"IDR": 1, "USD": 17800, "EUR": 20700}

def convert_to_idr(amount, from_currency):
    """Konversi dari mata uang user ke IDR"""
    rate = CURRENCY_RATES.get(from_currency, 1)
    return amount * rate

def convert_from_idr(amount_idr, to_currency):
    """Konversi dari IDR ke mata uang user"""
    rate = CURRENCY_RATES.get(to_currency, 1)
    return amount_idr / rate

def get_user_bmi_settings(user_id):
    """Ambil data BMI user (tinggi, berat, usia, gender, aktivitas)."""
    conn = get_conn()
    row = conn.execute(
        "SELECT height_cm, weight_kg, age, gender, activity_factor FROM user_health_goals WHERE user_id=?",
        (user_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        "height_cm": 170,
        "weight_kg": 70,
        "age": 25,
        "gender": "Laki-laki",
        "activity_factor": 1.55
    }

def update_user_bmi_settings(user_id, height_cm, weight_kg, age, gender, activity_factor):
    """Simpan data BMI user."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("""
        INSERT OR REPLACE INTO user_health_goals(user_id, height_cm, weight_kg, age, gender, activity_factor, updated_at)
        VALUES(?,?,?,?,?,?,datetime('now'))
    """, (user_id, height_cm, weight_kg, age, gender, activity_factor))
    conn.commit()
    conn.close()

@retry_on_lock
def log_user_weight(user_id, weight_kg, log_date=None):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    """Catat berat badan user ke health_logs untuk tanggal tertentu (default hari ini)."""
    if log_date is None:
        from datetime import date
        log_date = date.today().isoformat()
    
    conn = get_conn()
    try:
        # Cek apakah sudah ada entry untuk tanggal tersebut
        existing = conn.execute(
            "SELECT id FROM health_logs WHERE user_id=? AND log_date=?",
            (user_id, log_date)
        ).fetchone()
        
        if existing:
            # Update weight_kg pada entry yang sudah ada
            conn.execute(
                "UPDATE health_logs SET weight_kg=? WHERE id=?",
                (weight_kg, existing["id"])
            )
        else:
            # Buat entry baru dengan nilai default lainnya
            conn.execute("""
                INSERT INTO health_logs(user_id, log_date, weight_kg, steps, sleep_hours, water_ml, resting_hr, stress_level, mood, net_calories)
                VALUES(?,?,?,0,0,0,0,'normal','normal',0)
            """, (user_id, log_date, weight_kg))
        conn.commit()
    finally:
        conn.close()

def get_active_pets_info(user_id):
    """Return list of active pets with their details."""
    conn = get_conn()
    rows = conn.execute("""
        SELECT up.pet_id, up.level, up.is_active, p.name, p.icon, p.base_buff
        FROM user_pets up
        JOIN pets_data p ON up.pet_id = p.id
        WHERE up.user_id=? AND up.is_active=1
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_active_pets(user_id):
    conn = get_conn()
    rows = conn.execute("SELECT pet_id, level FROM user_pets WHERE user_id=? AND is_active=1", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def redeem_admin_code(user_id, code):
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    """Untuk kompatibilitas, gunakan redeem_code."""
    return redeem_code(user_id, code)

def add_redeem_code(code, reward_type, reward_value=0, reward_item=None, is_one_time=1):
    """Tambahkan kode redeem baru."""
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO redeem_codes(code, reward_type, reward_value, reward_item, is_one_time) VALUES(?,?,?,?,?)",
            (code, reward_type, reward_value, reward_item, is_one_time)
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": tr_db(lang="id", key="db_redeem_code_exists")}
    finally:
        conn.close()

def redeem_code(user_id, code):
    """Redeem kode dan berikan hadiah."""
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    # Cek apakah kode valid
    row = conn.execute(
        "SELECT * FROM redeem_codes WHERE code = ? AND (used_by IS NULL OR is_one_time = 0)",
        (code.upper().strip(),)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_redeem_invalid")}
    
    code_data = dict(row)
    
    # Jika one-time, tandai sudah dipakai
    if code_data["is_one_time"]:
        conn.execute(
            "UPDATE redeem_codes SET used_by = ?, used_at = ? WHERE id = ?",
            (user_id, datetime.now().isoformat(), code_data["id"])
        )
        conn.commit()
    conn.close()
    
    # Proses hadiah berdasarkan reward_type
    reward_type = code_data["reward_type"]
    reward_value = code_data["reward_value"]
    reward_item = code_data["reward_item"]
    
    if reward_type == "admin":
        # Ubah user menjadi admin (hanya bisa sekali seumur hidup)
        u = get_user(user_id)
        if u.get("is_admin", 0):
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_redeem_admin_already")}
        set_user_admin(user_id, True)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_redeem_admin_success")}
    
    elif reward_type == "xp":
        gain_xp_gold(user_id, reward_value, 0)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_redeem_xp", xp=reward_value), "xp": reward_value}
    
    elif reward_type == "gold":
        gain_xp_gold(user_id, 0, reward_value)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_redeem_gold", gold=reward_value), "gold": reward_value}
    
    elif reward_type == "item":
        # Tambahkan item ke inventory
        item = SHOP_ITEMS.get(reward_item)
        if not item:
            return {"ok": False, "msg": tr_db(user_id=user_id, key="db_redeem_item_fail")}
        conn2 = get_conn()
        ex = conn2.execute(
            "SELECT * FROM inventory WHERE user_id=? AND item_id=?", (user_id, reward_item)
        ).fetchone()
        if ex:
            conn2.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (ex["id"],))
        else:
            conn2.execute(
                "INSERT INTO inventory(user_id, item_id, item_type) VALUES(?,?,?)",
                (user_id, reward_item, item["type"])
            )
        conn2.commit()
        conn2.close()
        recalculate_all_buffs(user_id)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_redeem_item_success", name=item['name'])}
    
    else:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_redeem_unknown")}
    
def set_user_admin(user_id, is_admin):
    conn = get_conn()
    if is_account_locked(user_id):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_account_locked_msg")}
    conn.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
    conn.commit()
    conn.close()

# ========== ADMIN CHEAT FUNCTIONS FOR PETS ==========
@retry_on_lock
def admin_level_up_all_pets(user_id):
    """Naikkan level semua pet milik user sebanyak 1 level (tanpa mengubah EXP)."""
    conn = get_conn()
    try:
        pets = conn.execute("SELECT id, level, exp FROM user_pets WHERE user_id=?", (user_id,)).fetchall()
        for pet in pets:
            new_level = pet["level"] + 1
            # EXP tetap, tidak perlu diubah
            conn.execute("UPDATE user_pets SET level=? WHERE id=?", (new_level, pet["id"]))
        conn.commit()
        # Recalculate buff setelah perubahan
        recalculate_all_buffs(user_id)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_admin_cheat_pets_level_up")}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def admin_add_exp_all_pets(user_id, amount):
    """Tambahkan EXP ke semua pet (amount dalam integer)."""
    conn = get_conn()
    leveled_any = False
    try:
        pets = conn.execute("SELECT id, exp, level FROM user_pets WHERE user_id=?", (user_id,)).fetchall()
        for pet in pets:
            new_exp = pet["exp"] + amount
            new_level = pet["level"]
            needed = new_level * 100
            while new_exp >= needed:
                new_exp -= needed
                new_level += 1
                needed = new_level * 100
                leveled_any = True
            conn.execute("UPDATE user_pets SET exp=?, level=? WHERE id=?", (new_exp, new_level, pet["id"]))
        conn.commit()
        if leveled_any:
            recalculate_all_buffs(user_id)
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_admin_cheat_pets_add_exp", amount=amount)}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

@retry_on_lock
def admin_feed_all_pets(user_id):
    """Isi hunger semua pet menjadi 100 (kenyang)."""
    conn = get_conn()
    try:
        conn.execute("UPDATE user_pets SET hunger=100, last_fed=? WHERE user_id=?", (local_now().isoformat(), user_id))
        conn.commit()
        return {"ok": True, "msg": tr_db(user_id=user_id, key="db_admin_cheat_pets_feed")}
    except Exception as e:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_general_error", error=str(e))}
    finally:
        conn.close()

def get_user_language(user_id):
    conn = get_conn()
    row = conn.execute("SELECT language FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["language"] if row and row["language"] else "id"

def set_user_language(user_id, lang_code):
    conn = get_conn()
    conn.execute("UPDATE users SET language=? WHERE id=?", (lang_code, user_id))
    conn.commit()
    conn.close()

# ── TASK HISTORY ──────────────────────────────────────────────────────────
@retry_on_lock
def log_task_history(user_id, task_type, task_id, action, action_date=None):
    if action_date is None:
        from datetime import date
        action_date = date.today().isoformat()
    conn = get_conn()
    try:
        conn.execute(
            "DELETE FROM task_history WHERE user_id=? AND task_type=? AND task_id=? AND action_date=?",
            (user_id, task_type, task_id, action_date)
        )
        conn.execute(
            "INSERT INTO task_history(user_id, task_type, task_id, action_date, action) VALUES(?,?,?,?,?)",
            (user_id, task_type, task_id, action_date, action)
        )
        conn.commit()
    finally:
        conn.close()

def fill_skipped_history(user_id):
    from datetime import date, timedelta
    conn = get_conn()
    try:
        # Cek apakah ada habits/dailies yang perlu diproses
        for table, ttype in [("habits", "habit"), ("dailies", "daily")]:
            check = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE user_id=? AND last_done IS NOT NULL AND last_done < date('now')",
                (user_id,)
            ).fetchone()[0]
            if check == 0:
                continue
            
            # Ambil data
            if table == "habits":
                rows = conn.execute(f"SELECT id, last_done, streak FROM {table} WHERE user_id=?", (user_id,)).fetchall()
            else:
                rows = conn.execute(f"SELECT id, last_done, streak, fail_streak FROM {table} WHERE user_id=?", (user_id,)).fetchall()
            
            for r in rows:
                last = r["last_done"]
                if not last:
                    continue
                try:
                    last_date = datetime.strptime(last, "%Y-%m-%d").date()
                except ValueError:
                    continue
                current_date = date.today()
                if last_date >= current_date:
                    continue
                
                max_days = 30
                cutoff = current_date - timedelta(days=max_days)
                if last_date < cutoff:
                    last_date = cutoff
                
                d = last_date + timedelta(days=1)
                updates_needed = False
                
                while d < current_date:
                    if QApplication:
                        QApplication.processEvents()
                    d_str = d.isoformat()
                    existing = conn.execute(
                        "SELECT id FROM task_history WHERE user_id=? AND task_type=? AND task_id=? AND action_date=?",
                        (user_id, ttype, r["id"], d_str)
                    ).fetchone()
                    if not existing:
                        conn.execute(
                            "INSERT INTO task_history(user_id, task_type, task_id, action_date, action) VALUES(?,?,?,?,?)",
                            (user_id, ttype, r["id"], d_str, "skip")
                        )
                        updates_needed = True
                    d += timedelta(days=1)
                
                # Update hanya sekali di akhir
                if updates_needed:
                    if ttype == "daily":
                        new_fail = (r["fail_streak"] or 0) + 1
                        conn.execute(
                            f"UPDATE {table} SET streak = 0, fail_streak = ? WHERE id = ?",
                            (new_fail, r["id"])
                        )
                    else:
                        conn.execute(
                            f"UPDATE {table} SET streak = 0 WHERE id = ?",
                            (r["id"],)
                        )
        conn.commit()
    finally:
        conn.close()

def get_task_last_history(user_id, task_type, task_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT action_date, action FROM task_history WHERE user_id=? AND task_type=? AND task_id=? ORDER BY action_date DESC, created_at DESC LIMIT 1",
        (user_id, task_type, task_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_task_history(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM task_history WHERE user_id=? ORDER BY action_date DESC, created_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

@retry_on_lock
def reset_user_progress(user_id):
    """
    Reset semua progres user, tetapi pertahankan struktur task dan folder.
    """
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")

        # ========== 1. Reset kolom progres di users ==========
        conn.execute("""
            UPDATE users SET
                level = 1,
                xp = 0,
                hp = 50,
                max_hp = 50,
                mp = 30,
                max_mp = 30,
                gold = 0,
                gems = 10,
                longest_streak = 0,
                total_habits_done = 0,
                total_dailies_done = 0,
                total_todos_done = 0,
                total_xp_earned = 0,
                total_gold_earned = 0,
                boss_damage_bonus = 0,
                xp_multiplier = 1.0,
                gold_multiplier = 1.0,
                hp_damage_reduction = 0,
                has_revive = 0,
                mp_bonus = 0,
                sport_level = 1,
                sport_xp = 0,
                total_sport_points_earned = 0,
                total_tasks_completed = 0,
                total_gold_spent = 0,
                skill_buff_data = '{}',
                class_passive_buffs = '{}'
            WHERE id = ?
        """, (user_id,))

        # ========== 2. Reset habits, dailies, todos, sport ==========
        conn.execute("""
            UPDATE habits SET
                streak = 0,
                done_today = 0,
                counter_up = 0,
                counter_down = 0,
                last_done = NULL,
                last_action = ''
            WHERE user_id = ?
        """, (user_id,))

        conn.execute("""
            UPDATE dailies SET
                streak = 0,
                done_today = 0,
                last_done = NULL,
                last_action = ''
            WHERE user_id = ?
        """, (user_id,))

        conn.execute("UPDATE todos SET done = 0 WHERE user_id = ?", (user_id,))

        conn.execute("""
            UPDATE sport_activities SET
                streak = 0,
                done_today = 0,
                last_done = NULL
            WHERE user_id = ?
        """, (user_id,))

        # ========== 3. Hapus semua data progres yang punya user_id ==========
        tables_with_user_id = [
            "activity_log", "notifications", "task_history",
            "health_logs", "food_logs", "water_logs",
            "economy_items", "debts", "savings", "investments", "subscriptions",
            "user_pets", "inventory", "user_achievements",
            "boss_rewards", "food_achievements",
            "backup_codes"
        ]
        for table in tables_with_user_id:
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

        # ========== 4. Hapus data dari tabel yang tidak punya user_id ==========
        # guild_messages pakai sender_id
        conn.execute("DELETE FROM guild_messages WHERE sender_id = ?", (user_id,))
        # messages pakai sender_id atau receiver_id
        conn.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
        # guild_invites dan guild_requests punya user_id, tapi kita juga hapus
        conn.execute("DELETE FROM guild_invites WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_requests WHERE user_id = ?", (user_id,))
        # guild_leader_transfers punya old_leader_id
        conn.execute("DELETE FROM guild_leader_transfers WHERE old_leader_id = ?", (user_id,))
        # recipe_items? Kita hapus recipe dulu agar FK tidak error
        conn.execute("DELETE FROM recipe_items WHERE recipe_id IN (SELECT id FROM recipes WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM recipes WHERE user_id = ?", (user_id,))

        # ========== 5. Reset goals ke default ==========
        conn.execute("""
            INSERT OR REPLACE INTO user_nutrition_goals(user_id, daily_calories, daily_protein, daily_carbs, daily_fat)
            VALUES(?, 2000, 50, 250, 70)
        """, (user_id,))

        conn.execute("""
            INSERT OR REPLACE INTO user_water_goals(user_id, daily_ml)
            VALUES(?, 2000)
        """, (user_id,))

        conn.execute("""
            INSERT OR REPLACE INTO user_health_goals(user_id, daily_steps, daily_sleep_hours, height_cm, weight_kg, age, gender, activity_factor)
            VALUES(?, 10000, 7.0, 170, 70, 25, 'Laki-laki', 1.55)
        """, (user_id,))

        # ========== 6. Reset redeem_codes ==========
        conn.execute("UPDATE redeem_codes SET used_by = NULL, used_at = NULL WHERE used_by = ?", (user_id,))

        # ========== 7. Hapus teman? Tidak, biarkan hubungan tetap ==========
        # ========== 8. Security question? Biarkan, tidak direset ==========

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

def reset_progress_keep_assets(user_id):
    """Reset progres, tetapi pertahankan inventory, pets, task, dan folder."""
    conn = get_conn()
    try:
        conn.execute("PRAGMA foreign_keys = OFF")

        # Reset statistik user (sama seperti reset_user_progress)
        conn.execute("""
            UPDATE users SET
                level = 1,
                xp = 0,
                hp = 50,
                max_hp = 50,
                mp = 30,
                max_mp = 30,
                gold = 0,
                gems = 10,
                longest_streak = 0,
                total_habits_done = 0,
                total_dailies_done = 0,
                total_todos_done = 0,
                total_xp_earned = 0,
                total_gold_earned = 0,
                boss_damage_bonus = 0,
                xp_multiplier = 1.0,
                gold_multiplier = 1.0,
                hp_damage_reduction = 0,
                has_revive = 0,
                mp_bonus = 0,
                sport_level = 1,
                sport_xp = 0,
                total_sport_points_earned = 0,
                total_tasks_completed = 0,
                total_gold_spent = 0,
                skill_buff_data = '{}',
                class_passive_buffs = '{}'
            WHERE id = ?
        """, (user_id,))

        # Reset habits, dailies, todos, sport (sama)
        conn.execute("""
            UPDATE habits SET
                streak = 0,
                done_today = 0,
                counter_up = 0,
                counter_down = 0,
                last_done = NULL,
                last_action = ''
            WHERE user_id = ?
        """, (user_id,))

        conn.execute("""
            UPDATE dailies SET
                streak = 0,
                done_today = 0,
                last_done = NULL,
                last_action = ''
            WHERE user_id = ?
        """, (user_id,))

        conn.execute("UPDATE todos SET done = 0 WHERE user_id = ?", (user_id,))

        conn.execute("""
            UPDATE sport_activities SET
                streak = 0,
                done_today = 0,
                last_done = NULL
            WHERE user_id = ?
        """, (user_id,))

        # Hapus data progres (kecuali inventory dan user_pets)
        tables_to_delete = [
            "activity_log", "notifications", "task_history",
            "health_logs", "food_logs", "water_logs",
            "economy_items", "debts", "savings", "investments", "subscriptions",
            "user_achievements",  # achievement direset agar bisa diraih lagi
            "boss_rewards", "food_achievements",
            "backup_codes"
        ]
        for table in tables_to_delete:
            conn.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

        # Hapus data chat, invite, request, recipe
        conn.execute("DELETE FROM guild_messages WHERE sender_id = ?", (user_id,))
        conn.execute("DELETE FROM messages WHERE sender_id = ? OR receiver_id = ?", (user_id, user_id))
        conn.execute("DELETE FROM guild_invites WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_requests WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM guild_leader_transfers WHERE old_leader_id = ?", (user_id,))
        conn.execute("DELETE FROM recipe_items WHERE recipe_id IN (SELECT id FROM recipes WHERE user_id = ?)", (user_id,))
        conn.execute("DELETE FROM recipes WHERE user_id = ?", (user_id,))

        # Reset goals
        conn.execute("""
            INSERT OR REPLACE INTO user_nutrition_goals(user_id, daily_calories, daily_protein, daily_carbs, daily_fat)
            VALUES(?, 2000, 50, 250, 70)
        """, (user_id,))

        conn.execute("""
            INSERT OR REPLACE INTO user_water_goals(user_id, daily_ml)
            VALUES(?, 2000)
        """, (user_id,))

        conn.execute("""
            INSERT OR REPLACE INTO user_health_goals(user_id, daily_steps, daily_sleep_hours, height_cm, weight_kg, age, gender, activity_factor)
            VALUES(?, 10000, 7.0, 170, 70, 25, 'Laki-laki', 1.55)
        """, (user_id,))

        # Reset redeem_codes
        conn.execute("UPDATE redeem_codes SET used_by = NULL, used_at = NULL WHERE used_by = ?", (user_id,))

        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.close()

def perform_rebirth(user_id):
    """Lakukan rebirth: cek syarat, reset progres (kecuali inventory/pet), beri buff permanen."""
    u = get_user(user_id)
    if not u:
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_user_not_found")}

    conn = get_conn()
    # Syarat 1: minimal 10 achievement
    ach_count = conn.execute(
        "SELECT COUNT(*) FROM user_achievements WHERE user_id=? AND unlocked_at IS NOT NULL",
        (user_id,)
    ).fetchone()[0]
    if ach_count < 10:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_rebirth_achievements_required", count=10)}

    # Syarat 2: level >= 25
    if u["level"] < 25:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_rebirth_level_required", level=25)}

    # Syarat 3: minimal 2 pet
    pet_count = conn.execute("SELECT COUNT(*) FROM user_pets WHERE user_id=?", (user_id,)).fetchone()[0]
    if pet_count < 2:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_rebirth_pets_required", pets=2)}

    # Syarat 4: minimal 6 item di inventory
    item_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (user_id,)).fetchone()[0]
    if item_count < 6:
        conn.close()
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_rebirth_items_required", items=6)}
    conn.close()

    # Reset progres (pertahankan inventory, pet, task, folder)
    reset_progress_keep_assets(user_id)

    # Tambah rebirth_count
    conn2 = get_conn()
    conn2.execute("UPDATE users SET rebirth_count = rebirth_count + 1 WHERE id = ?", (user_id,))
    conn2.commit()
    conn2.close()

    # Recalculate buffs untuk mengaplikasikan bonus rebirth
    recalculate_all_buffs(user_id)

    new_count = get_user(user_id).get("rebirth_count", 0)
    add_notification(user_id, tr_db(user_id=user_id, key="db_rebirth_success", count=new_count), "levelup")

    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_rebirth_success", count=new_count), "rebirth_count": new_count}

def get_leaderboard_for_user(user_id):
    """Ambil leaderboard yang hanya menampilkan user sendiri, teman, dan anggota guild."""
    conn = get_conn()
    # Ambil ID teman yang sudah accepted
    friends = conn.execute(
        "SELECT friend_id FROM friends WHERE user_id=? AND status='accepted' "
        "UNION SELECT user_id FROM friends WHERE friend_id=? AND status='accepted'",
        (user_id, user_id)
    ).fetchall()
    friend_ids = [row[0] for row in friends]

    # Ambil guild_id user
    guild_row = conn.execute("SELECT guild_id FROM users WHERE id=?", (user_id,)).fetchone()
    guild_id = guild_row["guild_id"] if guild_row else None

    # Ambil anggota guild jika ada
    guild_member_ids = []
    if guild_id:
        members = conn.execute(
            "SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)
        ).fetchall()
        guild_member_ids = [row[0] for row in members]

    # Gabungkan semua ID unik: user sendiri, teman, anggota guild
    all_ids = set([user_id] + friend_ids + guild_member_ids)
    if not all_ids:
        return []

    # Buat query dengan placeholders
    placeholders = ",".join("?" * len(all_ids))
    query = f"""
        SELECT username, display_name, level, total_xp_earned, gold,
               COALESCE(sport_level, 1) as sport_level,
               (SELECT COUNT(*) FROM user_pets WHERE user_id=users.id) as pet_count,
               COALESCE(rebirth_count, 0) as rebirth_count
        FROM users
        WHERE id IN ({placeholders})
        AND is_admin = 0
        ORDER BY level DESC, total_xp_earned DESC
    """
    rows = conn.execute(query, tuple(all_ids)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def move_item_up(user_id, mode, item_id):
    """Tukar sort_order dengan item sebelumnya."""
    table_map = {...}  # sama
    tbl = table_map[mode]
    conn = get_conn()
    # Ambil item saat ini dan sebelumnya
    current = conn.execute(f"SELECT sort_order, folder_id FROM {tbl} WHERE id=?", (item_id,)).fetchone()
    if not current:
        return
    folder_id = current["folder_id"]
    prev = conn.execute(
        f"SELECT id, sort_order FROM {tbl} WHERE user_id=? AND folder_id IS ? AND sort_order < ? ORDER BY sort_order DESC LIMIT 1",
        (user_id, folder_id, current["sort_order"])
    ).fetchone()
    if prev:
        # Tukar sort_order
        conn.execute(f"UPDATE {tbl} SET sort_order=? WHERE id=?", (prev["sort_order"], item_id))
        conn.execute(f"UPDATE {tbl} SET sort_order=? WHERE id=?", (current["sort_order"], prev["id"]))
        conn.commit()
    conn.close()

def move_item_down(user_id, mode, item_id):
    """Tukar sort_order dengan item berikutnya."""
    # Analog

def move_item_to_folder(user_id, mode, item_id, target_folder_id):
    """Pindahkan item ke folder tertentu (untuk habit/daily/todo/sport/economy) 
       atau ubah meal_type (untuk food_logs)."""
    table_map = {
        "habit": "habits",
        "daily": "dailies",
        "todo": "todos",
        "sport": "sport_activities",
        "economy": "economy_items",
        "food": "food_logs"
    }
    tbl = table_map.get(mode)
    if not tbl:
        return
    
    conn = get_conn()
    now = datetime.now().isoformat()
    
    if mode == "food":
        # target_folder_id sebenarnya adalah meal_type
        valid_meals = ("breakfast", "lunch", "dinner", "snack", None)
        if target_folder_id not in valid_meals:
            target_folder_id = "snack"  # fallback
        conn.execute(
            f"UPDATE {tbl} SET meal_type=? WHERE id=? AND user_id=?",
            (target_folder_id, item_id, user_id)
        )
    else:
        conn.execute(
            f"UPDATE {tbl} SET folder_id=?, created_at=? WHERE id=? AND user_id=?",
            (target_folder_id, now, item_id, user_id)
        )
    
    conn.commit()
    conn.close()

def reorder_item(user_id, mode, item_id, direction, status=None):
    """Tukar sort_order dengan item di atas/bawah dalam folder dan status yang sama.
    status: untuk todo = done, untuk habit/daily/sport = done_today.
    """
    table_map = {
        "habit": "habits",
        "daily": "dailies",
        "todo": "todos",
        "sport": "sport_activities",
        "economy": "economy_items"
    }
    tbl = table_map.get(mode)
    if not tbl:
        return {"ok": False, "msg": "Mode tidak didukung"}

    # Tentukan kolom status berdasarkan mode
    if mode == "todo":
        status_col = "done"
    elif mode in ("habit", "daily", "sport"):
        status_col = "done_today"
    else:
        status_col = None

    conn = get_conn()
    try:
        # Ambil data item saat ini
        if status_col:
            current = conn.execute(
                f"SELECT folder_id, sort_order, {status_col} as status FROM {tbl} WHERE id=? AND user_id=?",
                (item_id, user_id)
            ).fetchone()
        else:
            current = conn.execute(
                f"SELECT folder_id, sort_order FROM {tbl} WHERE id=? AND user_id=?",
                (item_id, user_id)
            ).fetchone()
        if not current:
            return {"ok": False, "msg": "Item tidak ditemukan"}

        folder_id = current["folder_id"]
        current_order = current["sort_order"]
        current_status = current["status"] if status_col else None

        # Gunakan status dari parameter jika diberikan, atau status item saat ini
        target_status = status if status is not None else current_status

        # Cari item target (atas/bawah) dengan status yang sama (jika ada)
        if status_col is not None and target_status is not None:
            params = [user_id, folder_id, target_status, current_order]
            if direction == "up":
                query = f"""SELECT id, sort_order FROM {tbl}
                            WHERE user_id=? AND folder_id IS ? AND {status_col}=? AND sort_order < ?
                            ORDER BY sort_order DESC LIMIT 1"""
            else:
                query = f"""SELECT id, sort_order FROM {tbl}
                            WHERE user_id=? AND folder_id IS ? AND {status_col}=? AND sort_order > ?
                            ORDER BY sort_order ASC LIMIT 1"""
            target = conn.execute(query, tuple(params)).fetchone()
        else:
            # Tanpa status (misal economy)
            params = [user_id, folder_id, current_order]
            if direction == "up":
                query = f"""SELECT id, sort_order FROM {tbl}
                            WHERE user_id=? AND folder_id IS ? AND sort_order < ?
                            ORDER BY sort_order DESC LIMIT 1"""
            else:
                query = f"""SELECT id, sort_order FROM {tbl}
                            WHERE user_id=? AND folder_id IS ? AND sort_order > ?
                            ORDER BY sort_order ASC LIMIT 1"""
            target = conn.execute(query, tuple(params)).fetchone()

        if not target:
            return {"ok": True, "moved": False, "msg": "Sudah di posisi paling ujung"}

        # Tukar sort_order
        conn.execute(
            f"UPDATE {tbl} SET sort_order = ? WHERE id = ? AND user_id = ?",
            (target["sort_order"], item_id, user_id)
        )
        conn.execute(
            f"UPDATE {tbl} SET sort_order = ? WHERE id = ? AND user_id = ?",
            (current_order, target["id"], user_id)
        )
        conn.commit()
        return {"ok": True, "moved": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e)}
    finally:
        conn.close()

def reorder_item_relative(user_id, mode, source_id, target_id):
    """
    Pindahkan source_id ke posisi relatif terhadap target_id dalam folder yang sama.
    Jika source berada di atas target, pindahkan ke bawah target (after).
    Jika source berada di bawah target, pindahkan ke atas target (before).
    """
    table_map = {
        "habit": "habits",
        "daily": "dailies",
        "todo": "todos",
        "sport": "sport_activities",
        "economy": "economy_items"
    }
    tbl = table_map.get(mode)
    if not tbl:
        return {"ok": False}

    conn = get_conn()
    try:
        # Ambil folder_id source dan target
        source = conn.execute(
            f"SELECT folder_id FROM {tbl} WHERE id=? AND user_id=?",
            (source_id, user_id)
        ).fetchone()
        target = conn.execute(
            f"SELECT folder_id FROM {tbl} WHERE id=? AND user_id=?",
            (target_id, user_id)
        ).fetchone()
        if not source or not target or source["folder_id"] != target["folder_id"]:
            return {"ok": False}

        folder_id = source["folder_id"]

        # Ambil semua id item dalam folder, urutkan berdasarkan sort_order
        rows = conn.execute(
            f"SELECT id FROM {tbl} WHERE user_id=? AND folder_id IS ? ORDER BY sort_order",
            (user_id, folder_id)
        ).fetchall()
        item_ids = [r["id"] for r in rows]

        if source_id not in item_ids or target_id not in item_ids:
            return {"ok": False}

        src_idx = item_ids.index(source_id)
        tgt_idx = item_ids.index(target_id)

        if src_idx == tgt_idx:
            return {"ok": True}  # tidak ada perubahan

        # Hapus source dari list
        item_ids.pop(src_idx)

        # Cari indeks target yang baru (setelah source dihapus)
        new_tgt_idx = item_ids.index(target_id)

        if src_idx < tgt_idx:
            # Source berada di atas target → pindahkan ke bawah target
            insert_pos = new_tgt_idx + 1
        else:
            # Source berada di bawah target → pindahkan ke atas target
            insert_pos = new_tgt_idx

        item_ids.insert(insert_pos, source_id)

        # Update ulang sort_order secara berurutan
        for i, item_id in enumerate(item_ids, start=1):
            conn.execute(
                f"UPDATE {tbl} SET sort_order = ? WHERE id = ? AND user_id = ?",
                (i, item_id, user_id)
            )
        conn.commit()
        return {"ok": True}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e)}
    finally:
        conn.close()

# ========== NOTES CRUD ==========
def get_note_folders(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM note_folders WHERE user_id=? ORDER BY name",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_note_folders_tree(user_id):
    """Ambil semua folder user dan bangun struktur tree (nested)."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM note_folders WHERE user_id=? ORDER BY name",
        (user_id,)
    ).fetchall()
    conn.close()

    folders = [dict(r) for r in rows]
    # Bangun mapping id -> node
    node_map = {f["id"]: {**f, "children": []} for f in folders}
    tree = []
    for f in folders:
        node = node_map[f["id"]]
        parent_id = f.get("parent_id")
        if parent_id is None:
            tree.append(node)
        else:
            parent = node_map.get(parent_id)
            if parent:
                parent["children"].append(node)
            else:
                # fallback: jika parent tidak ditemukan, taruh di root
                tree.append(node)
    return tree

def add_note_folder(user_id, name, icon="📁", parent_id=None):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO note_folders(user_id, name, icon, parent_id) VALUES(?,?,?,?)",
        (user_id, name, icon, parent_id)
    )
    folder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "folder_id": folder_id}

def update_note_folder(folder_id, user_id, name=None, icon=None):
    updates = []
    values = []
    if name is not None:
        updates.append("name=?")
        values.append(name)
    if icon is not None:
        updates.append("icon=?")
        values.append(icon)
    if not updates:
        return
    values.append(folder_id)
    values.append(user_id)
    conn = get_conn()
    conn.execute(
        f"UPDATE note_folders SET {', '.join(updates)} WHERE id=? AND user_id=?",
        values
    )
    conn.commit()
    conn.close()

def delete_note_folder(folder_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM note_folders WHERE id=? AND user_id=?", (folder_id, user_id))
    conn.commit()
    conn.close()

def duplicate_note_folder(user_id, folder_id):
    """Duplikasi folder beserta semua subfolder dan isi notes-nya."""
    conn = get_conn()
    try:
        # Ambil data folder asli
        src = conn.execute(
            "SELECT name, icon, parent_id FROM note_folders WHERE id=? AND user_id=?",
            (folder_id, user_id)
        ).fetchone()
        if not src:
            return {"ok": False, "msg": "Folder tidak ditemukan"}
        
        new_name = src["name"]
        icon = src["icon"]
        parent_id = src["parent_id"]

        cur = conn.execute(
            "INSERT INTO note_folders(user_id, name, icon, parent_id) VALUES(?,?,?,?)",
            (user_id, new_name, icon, parent_id)
        )
        new_folder_id = cur.lastrowid

        # Duplikasi semua note dari folder asli ke folder baru
        notes = conn.execute(
            "SELECT title, content, is_archived FROM notes WHERE user_id=? AND folder_id=?",
            (user_id, folder_id)
        ).fetchall()
        for note in notes:
            conn.execute(
                "INSERT INTO notes(user_id, folder_id, title, content, is_archived) VALUES(?,?,?,?,?)",
                (user_id, new_folder_id, note["title"], note["content"], note["is_archived"])
            )

        # Duplikasi subfolder secara rekursif
        subfolders = conn.execute(
            "SELECT id FROM note_folders WHERE user_id=? AND parent_id=?",
            (user_id, folder_id)
        ).fetchall()
        for sub in subfolders:
            _duplicate_subfolder(conn, user_id, sub["id"], new_folder_id)

        conn.commit()
        return {"ok": True, "new_folder_id": new_folder_id, "msg": f"Folder '{new_name}' berhasil diduplikasi!"}
    except Exception as e:
        conn.rollback()
        return {"ok": False, "msg": str(e)}
    finally:
        conn.close()

def _duplicate_subfolder(conn, user_id, src_folder_id, new_parent_id):
    """Fungsi internal rekursif untuk duplikasi subfolder."""
    src = conn.execute(
        "SELECT name, icon FROM note_folders WHERE id=? AND user_id=?",
        (src_folder_id, user_id)
    ).fetchone()
    if not src:
        return
    cur = conn.execute(
        "INSERT INTO note_folders(user_id, name, icon, parent_id) VALUES(?,?,?,?)",
        (user_id, src["name"], src["icon"], new_parent_id)
    )
    new_sub_id = cur.lastrowid

    # Duplikasi notes di subfolder
    notes = conn.execute(
        "SELECT title, content, is_archived FROM notes WHERE user_id=? AND folder_id=?",
        (user_id, src_folder_id)
    ).fetchall()
    for note in notes:
        conn.execute(
            "INSERT INTO notes(user_id, folder_id, title, content, is_archived) VALUES(?,?,?,?,?)",
            (user_id, new_sub_id, note["title"], note["content"], note["is_archived"])
        )

    # Proses sub-sub folder
    subsub = conn.execute(
        "SELECT id FROM note_folders WHERE user_id=? AND parent_id=?",
        (user_id, src_folder_id)
    ).fetchall()
    for s in subsub:
        _duplicate_subfolder(conn, user_id, s["id"], new_sub_id)

def update_note_folder_icon(folder_id, user_id, new_icon):
    conn = get_conn()
    conn.execute(
        "UPDATE note_folders SET icon=? WHERE id=? AND user_id=?",
        (new_icon, folder_id, user_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True}

def get_notes(user_id, folder_id=None, include_archived=False):
    conn = get_conn()
    query = "SELECT * FROM notes WHERE user_id=?"
    params = [user_id]
    if folder_id == -1:
        query += " AND folder_id IS NULL"
    elif folder_id is not None:
        query += " AND folder_id=?"
        params.append(folder_id)
    # jika folder_id is None, tidak ada filter folder
    if not include_archived:
        query += " AND is_archived=0"
    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_note(note_id, user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM notes WHERE id=? AND user_id=?",
        (note_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def add_note(user_id, folder_id, title, content=""):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes(user_id, folder_id, title, content, zoom_level) VALUES(?,?,?,?,?)",
        (user_id, folder_id, title, content, 100)
    )
    note_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "note_id": note_id}

def update_note(note_id, user_id, title=None, content=None, folder_id=None, zoom_level=None):
    updates = []
    values = []
    if title is not None:
        updates.append("title=?")
        values.append(title)
    if content is not None:
        updates.append("content=?")
        values.append(content)
    if folder_id is not None:
        updates.append("folder_id=?")
        values.append(folder_id)
    if zoom_level is not None:
        updates.append("zoom_level=?")
        values.append(zoom_level)
    if not updates:
        return
    updates.append("updated_at=datetime('now')")
    values.append(note_id)
    values.append(user_id)
    conn = get_conn()
    conn.execute(
        f"UPDATE notes SET {', '.join(updates)} WHERE id=? AND user_id=?",
        values
    )
    conn.commit()
    conn.close()

def delete_note(note_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE id=? AND user_id=?", (note_id, user_id))
    conn.commit()
    conn.close()

def archive_note(note_id, user_id, archived):
    conn = get_conn()
    conn.execute(
        "UPDATE notes SET is_archived=?, updated_at=datetime('now') WHERE id=? AND user_id=?",
        (1 if archived else 0, note_id, user_id)
    )
    conn.commit()
    conn.close()

# ========== REMINDERS CRUD ==========
def get_reminders(user_id, active_only=False):
    conn = get_conn()
    query = "SELECT * FROM reminders WHERE user_id=?"
    params = [user_id]
    if active_only:
        query += " AND is_active=1"
    query += " ORDER BY reminder_datetime ASC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_reminder(reminder_id, user_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM reminders WHERE id=? AND user_id=?",
        (reminder_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def add_reminder(user_id, title, description, reminder_datetime, sound_type="default", sound_file=None, repeat_type="none", repeat_days=""):
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO reminders(user_id, title, description, reminder_datetime, sound_type, sound_file, repeat_type, repeat_days)
           VALUES(?,?,?,?,?,?,?,?)""",
        (user_id, title, description, reminder_datetime, sound_type, sound_file, repeat_type, repeat_days)
    )
    reminder_id = cur.lastrowid
    conn.commit()
    conn.close()
    return {"ok": True, "reminder_id": reminder_id}

def update_reminder(reminder_id, user_id, **kwargs):
    fields = []
    values = []
    for key, value in kwargs.items():
        if key in ("title", "description", "reminder_datetime", "sound_type", "sound_file", "is_active", "triggered", "repeat_type", "repeat_days", "repeat_until"):
            fields.append(f"{key}=?")
            values.append(value)
    if not fields:
        return
    values.append(reminder_id)
    values.append(user_id)
    conn = get_conn()
    conn.execute(
        f"UPDATE reminders SET {', '.join(fields)} WHERE id=? AND user_id=?",
        values
    )
    conn.commit()
    conn.close()

def delete_reminder(reminder_id, user_id):
    conn = get_conn()
    conn.execute("DELETE FROM reminders WHERE id=? AND user_id=?", (reminder_id, user_id))
    conn.commit()
    conn.close()

def get_pending_reminders(user_id):
    """Ambil reminder yang harus dipicu (waktu <= sekarang, aktif, belum terpicu)"""
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = conn.execute(
        """SELECT * FROM reminders
           WHERE user_id=? AND is_active=1 AND triggered=0 AND reminder_datetime <= ?
           ORDER BY reminder_datetime ASC""",
        (user_id, now)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def mark_reminder_triggered(reminder_id, user_id):
    conn = get_conn()
    conn.execute(
        "UPDATE reminders SET triggered=1 WHERE id=? AND user_id=?",
        (reminder_id, user_id)
    )
    conn.commit()
    conn.close()

def reset_reminder_triggered(reminder_id, user_id):
    """Reset triggered untuk reminder yang sudah lewat (misal untuk besok)"""
    conn = get_conn()
    conn.execute(
        "UPDATE reminders SET triggered=0 WHERE id=? AND user_id=?",
        (reminder_id, user_id)
    )
    conn.commit()
    conn.close()

def get_next_reminder_datetime(current_dt_str, repeat_type, repeat_days, repeat_until=None):
    """
    Hitung tanggal/waktu berikutnya berdasarkan repeat_type.
    - repeat_type: 'none', 'daily', 'weekly', 'custom'
    - repeat_days: string angka hari (0=Senin, 6=Minggu) dipisah koma, misal "0,2,4"
    - repeat_until: tanggal akhir (YYYY-MM-DD) atau None
    Mengembalikan string datetime baru (YYYY-MM-DD HH:MM:SS) atau None jika tidak ada (sudah melewati repeat_until)
    """
    if repeat_type == 'none':
        return None

    current_dt = datetime.strptime(current_dt_str, "%Y-%m-%d %H:%M:%S")
    time_part = current_dt.strftime("%H:%M:%S")

    # Hitung next date
    if repeat_type == 'daily':
        next_dt = current_dt + timedelta(days=1)
    elif repeat_type == 'weekly':
        next_dt = current_dt + timedelta(days=7)
    elif repeat_type == 'custom':
        if not repeat_days:
            return None
        days_list = [int(d.strip()) for d in repeat_days.split(',') if d.strip()]
        if not days_list:
            return None
        # Cari hari berikutnya yang ada di days_list
        current_weekday = current_dt.weekday()  # 0=Senin, 6=Minggu
        for offset in range(1, 8):
            candidate = current_dt + timedelta(days=offset)
            if candidate.weekday() in days_list:
                next_dt = candidate
                break
        else:
            # Tidak ada hari yang cocok dalam 7 hari ke depan (seharusnya tidak terjadi)
            return None
    else:
        return None

    # Jika repeat_until, cek apakah next_dt melewati batas
    if repeat_until:
        until_date = datetime.strptime(repeat_until, "%Y-%m-%d").date()
        if next_dt.date() > until_date:
            return None

    # Gabungkan dengan waktu dari reminder asli
    next_dt_str = next_dt.strftime("%Y-%m-%d") + " " + time_part
    return next_dt_str

# ═══════════════════════════════════════════════════════════════════
#  CALENDAR NOTES
# ═══════════════════════════════════════════════════════════════════
@retry_on_lock
def get_calendar_notes(user_id, year=None, month=None):
    """Ambil catatan kalender untuk user, opsional filter tahun/bulan."""
    conn = get_conn()
    query = "SELECT note_date, note FROM calendar_notes WHERE user_id = ?"
    params = [user_id]
    if year is not None and month is not None:
        start_date = f"{year:04d}-{month:02d}-01"
        # akhir bulan
        from calendar import monthrange
        last_day = monthrange(year, month)[1]
        end_date = f"{year:04d}-{month:02d}-{last_day:02d}"
        query += " AND note_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    elif year is not None:
        start_date = f"{year:04d}-01-01"
        end_date = f"{year:04d}-12-31"
        query += " AND note_date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return {row["note_date"]: row["note"] for row in rows}

@retry_on_lock
def get_calendar_note(user_id, date_str):
    """Ambil catatan untuk satu tanggal."""
    conn = get_conn()
    row = conn.execute("SELECT note FROM calendar_notes WHERE user_id = ? AND note_date = ?", (user_id, date_str)).fetchone()
    conn.close()
    return row["note"] if row else ""

@retry_on_lock
def save_calendar_note(user_id, date_str, note):
    """Simpan atau update catatan untuk tanggal tertentu."""
    conn = get_conn()
    conn.execute(
        """INSERT INTO calendar_notes(user_id, note_date, note, updated_at)
           VALUES(?,?,?,datetime('now'))
           ON CONFLICT(user_id, note_date) DO UPDATE SET note=excluded.note, updated_at=datetime('now')""",
        (user_id, date_str, note)
    )
    conn.commit()
    conn.close()

@retry_on_lock
def delete_calendar_note(user_id, date_str):
    """Hapus catatan untuk tanggal tertentu."""
    conn = get_conn()
    conn.execute("DELETE FROM calendar_notes WHERE user_id = ? AND note_date = ?", (user_id, date_str))
    conn.commit()
    conn.close()

import threading

_checkpoint_timer = None

def start_periodic_checkpoint(interval=10):
    global _checkpoint_timer
    if _checkpoint_timer:
        return
    _checkpoint_timer = threading.Timer(interval, _do_checkpoint)
    _checkpoint_timer.daemon = True
    _checkpoint_timer.start()

def _do_checkpoint():
    global _checkpoint_timer
    try:
        _c = sqlite3.connect(DB_PATH, timeout=60.0)
        _c.execute("PRAGMA wal_checkpoint(PASSIVE)")
        _c.close()  # koneksi langsung (bukan pooled) -> hindari bocor di thread Timer
    except:
        pass
    _checkpoint_timer = threading.Timer(10, _do_checkpoint)
    _checkpoint_timer.daemon = True
    _checkpoint_timer.start()

def stop_periodic_checkpoint():
    global _checkpoint_timer
    if _checkpoint_timer:
        _checkpoint_timer.cancel()
        _checkpoint_timer = None
    force_checkpoint()

# ========== GET ALL ACTIVE BUFFS ==========
def get_all_active_buffs(user_id):
    """Ambil semua buff aktif user dalam bentuk list of string (Indonesia)."""
    u = get_user(user_id)
    if not u:
        return []
    buffs = []
    
    # 1. XP Multiplier
    if u.get("xp_multiplier", 1.0) > 1.001:
        buffs.append(f"📈 XP Multiplier: x{u['xp_multiplier']:.2f}")
    # 2. Gold Multiplier
    if u.get("gold_multiplier", 1.0) > 1.001:
        buffs.append(f"💰 Gold Multiplier: x{u['gold_multiplier']:.2f}")
    # 3. Boss Damage Bonus
    if u.get("boss_damage_bonus", 0) > 0:
        buffs.append(f"⚔️ Boss Damage: +{u['boss_damage_bonus']:.0f}")
    # 4. HP Damage Reduction
    if u.get("hp_damage_reduction", 0) > 0:
        buffs.append(f"🛡️ HP Reduction: -{u['hp_damage_reduction']:.0f}")
    # 5. MP Bonus
    if u.get("mp_bonus", 0) > 0:
        buffs.append(f"💙 Max MP: +{u['mp_bonus']}")
    # 6. Revive
    if u.get("has_revive", 0):
        buffs.append("🗿 Totem of Life (revive once)")
    # 7. Critical Chance
    if u.get("crit_chance", 10) > 10:
        buffs.append(f"⚡ Critical Chance: +{u['crit_chance']-10}%")
    # 8. Block Chance
    if u.get("block_chance", 20) > 20:
        buffs.append(f"🛡️ Block Chance: +{u['block_chance']-20}%")
    # 9. Block Strength
    if u.get("block_strength", 10) > 10:
        buffs.append(f"🛡️ Block Strength: +{u['block_strength']-10}")
    # 10. Spyglass
    if u.get("has_spyglass", 0):
        buffs.append("🔭 Spyglass (reveal boss stats)")
    
    # 11. Guild buffs
    guild_id = u.get("guild_id")
    if guild_id:
        conn = get_conn()
        g = conn.execute("SELECT buff_xp, buff_gold, buff_damage, crit_chance FROM guilds WHERE id=?", (guild_id,)).fetchone()
        conn.close()
        if g:
            if g["buff_xp"] > 0:
                buffs.append(f"🏰 Guild XP Bonus: +{g['buff_xp']:.0f}%")
            if g["buff_gold"] > 0:
                buffs.append(f"🏰 Guild Gold Bonus: +{g['buff_gold']:.0f}%")
            if g["buff_damage"] > 0:
                buffs.append(f"🏰 Guild Damage: +{g['buff_damage']:.0f}")
            if g["crit_chance"] > 0:
                buffs.append(f"🏰 Guild Crit Chance: +{g['crit_chance']}%")
    
    # 12. Pet aktif
    conn = get_conn()
    active_pet = conn.execute(
        "SELECT pet_id, level FROM user_pets WHERE user_id=? AND is_active=1",
        (user_id,)
    ).fetchone()
    conn.close()
    if active_pet:
        pet = PETS_DATA.get(active_pet["pet_id"], {})
        pet_name = pet.get('name', active_pet["pet_id"])
        bonus = pet.get('bonus', '')
        level = active_pet["level"]
        buffs.append(f"🐾 {pet_name} (Lv.{level}): {bonus}")
    
    # 13. Class passive
    class_buffs = get_class_passive_buffs(user_id)
    if class_buffs.get("hp_multiplier", 1.0) > 1.001:
        hp_bonus = (class_buffs['hp_multiplier']-1)*100
        buffs.append(f"❤️ Class HP Bonus: +{hp_bonus:.0f}%")
    if class_buffs.get("streak_bonus", 0):
        buffs.append("🔥 Class Streak Bonus: +1 streak")
    
    # 14. Skill buffs aktif
    skill_buffs = get_skill_buffs(user_id)
    if skill_buffs.get("shield_active"):
        buffs.append("🛡️ Shield Bash (next boss damage -50%)")
    if skill_buffs.get("xp_multiplier") and skill_buffs.get("xp_remaining", 0) > 0:
        buffs.append(f"✨ Arcane Surge: +30% XP for {skill_buffs['xp_remaining']} habits")
    if skill_buffs.get("gold_multiplier") and skill_buffs.get("gold_remaining", 0) > 0:
        buffs.append(f"🏹 Gold Shot: +50% Gold for {skill_buffs['gold_remaining']} habit")
    if skill_buffs.get("double_streak"):
        buffs.append("🗡️ Shadow Step: +1 streak for next daily")
    
    # 15. Rebirth buff
    rebirth_count = u.get("rebirth_count", 0)
    if rebirth_count > 0:
        buffs.append(f"🌀 Rebirth Bonus: +{rebirth_count*10}% XP, +{rebirth_count*5}% Gold")
    
    return buffs

# ========== PLAYLIST FUNCTIONS ==========
def save_playlist(user_id, name, files):
    """Simpan playlist ke database, kembalikan ID playlist."""
    try:
        conn = get_conn()
        cur = conn.execute(
            "INSERT INTO playlists(user_id, name, tracks, is_favorite) VALUES(?,?,?,?)",
            (user_id, name, json.dumps(files), 0)
        )
        playlist_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"ok": True, "id": playlist_id, "msg": "Playlist berhasil disimpan!"}
    except Exception as e:
        return {"ok": False, "msg": f"Gagal menyimpan playlist: {str(e)}"}

def load_playlist(playlist_id, user_id):
    """Ambil tracks dari playlist."""
    conn = get_conn()
    row = conn.execute(
        "SELECT tracks, name FROM playlists WHERE id=? AND user_id=?",
        (playlist_id, user_id)
    ).fetchone()
    conn.close()
    if row:
        return {"ok": True, "tracks": json.loads(row["tracks"]), "name": row["name"]}
    return {"ok": False}

def create_playlist(user_id, name, is_favorite=0):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO playlists(user_id, name, tracks, is_favorite) VALUES(?,?,?,?)",
        (user_id, name, json.dumps([]), is_favorite)
    )
    playlist_id = cur.lastrowid
    conn.commit()
    conn.close()
    return playlist_id

def get_all_playlists(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, tracks, is_favorite FROM playlists WHERE user_id=? ORDER BY is_favorite DESC, name",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_playlist(user_id, playlist_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, tracks, is_favorite FROM playlists WHERE id=? AND user_id=?",
        (playlist_id, user_id)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def update_playlist_tracks(user_id, playlist_id, tracks):
    conn = get_conn()
    conn.execute(
        "UPDATE playlists SET tracks=? WHERE id=? AND user_id=?",
        (json.dumps(tracks), playlist_id, user_id)
    )
    conn.commit()
    conn.close()

def rename_playlist(user_id, playlist_id, new_name):
    """Ganti nama playlist."""
    conn = get_conn()
    conn.execute(
        "UPDATE playlists SET name=? WHERE id=? AND user_id=?",
        (new_name, playlist_id, user_id)
    )
    conn.commit()
    conn.close()

def delete_playlist(user_id, playlist_id):
    """Hapus playlist (tidak bisa hapus Favorite)."""
    # Cek apakah ini favorite
    playlist = get_playlist(user_id, playlist_id)
    if playlist and playlist['is_favorite']:
        return False  # tidak bisa hapus favorite
    conn = get_conn()
    conn.execute("DELETE FROM playlists WHERE id=? AND user_id=?", (playlist_id, user_id))
    conn.commit()
    conn.close()
    return True

def add_song_to_playlist(user_id, playlist_id, file_path):
    playlist = get_playlist(user_id, playlist_id)
    if not playlist:
        return False
    tracks = json.loads(playlist['tracks'])
    if file_path not in tracks:
        tracks.append(file_path)
        update_playlist_tracks(user_id, playlist_id, tracks)
        return True
    return False

def remove_song_from_playlist(user_id, playlist_id, index):
    playlist = get_playlist(user_id, playlist_id)
    if not playlist:
        return False
    tracks = json.loads(playlist['tracks'])
    if 0 <= index < len(tracks):
        del tracks[index]
        update_playlist_tracks(user_id, playlist_id, tracks)
        return True
    return False

def move_song_to_playlist(user_id, from_playlist_id, to_playlist_id, index):
    from_pl = get_playlist(user_id, from_playlist_id)
    to_pl = get_playlist(user_id, to_playlist_id)
    if not from_pl or not to_pl:
        return False
    from_tracks = json.loads(from_pl['tracks'])
    if index < 0 or index >= len(from_tracks):
        return False
    song = from_tracks.pop(index)
    update_playlist_tracks(user_id, from_playlist_id, from_tracks)
    to_tracks = json.loads(to_pl['tracks'])
    to_tracks.append(song)
    update_playlist_tracks(user_id, to_playlist_id, to_tracks)
    return True

def copy_song_to_playlist(user_id, from_playlist_id, to_playlist_id, index):
    from_pl = get_playlist(user_id, from_playlist_id)
    to_pl = get_playlist(user_id, to_playlist_id)
    if not from_pl or not to_pl:
        return False
    from_tracks = json.loads(from_pl['tracks'])
    if index < 0 or index >= len(from_tracks):
        return False
    song = from_tracks[index]
    to_tracks = json.loads(to_pl['tracks'])
    to_tracks.append(song)
    update_playlist_tracks(user_id, to_playlist_id, to_tracks)
    return True

def lock_account(user_id, password):
    """Lock akun, hanya jika password benar. Kembalikan dict."""
    u = get_user(user_id)
    if not u or _hash(password) != u.get("password_hash", ""):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_old_password_wrong")}
    
    conn = get_conn()
    now = datetime.now().isoformat()
    conn.execute(
        "UPDATE users SET is_locked=1, locked_at=?, last_tracking_date=? WHERE id=?",
        (now, now, user_id)
    )
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_account_locked")}

def unlock_account(user_id, password):
    """Unlock akun, hanya jika password benar."""
    u = get_user(user_id)
    if not u or _hash(password) != u.get("password_hash", ""):
        return {"ok": False, "msg": tr_db(user_id=user_id, key="db_old_password_wrong")}
    
    conn = get_conn()
    conn.execute("UPDATE users SET is_locked=0, locked_at=NULL WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": tr_db(user_id=user_id, key="db_account_unlocked")}

def is_account_locked(user_id):
    conn = get_conn()
    row = conn.execute("SELECT is_locked FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["is_locked"] == 1 if row else False

def calculate_rank(user_id):
    """Hitung rank user berdasarkan overall progress."""
    u = get_user(user_id)
    if not u:
        return {
            "rank": 0,
            "rank_name_key": "rank_pemula",
            "rank_icon": "🥚",
            "rank_desc_key": "rank_desc_pemula",
            "score": 0,
            "progress": 0,
            "next_rank_name_key": "rank_penambang",
            "next_rank_icon": "⛏️",
            "has_next": True,
            "max_score": 100,
            "scores": {},
        }
    
    # Ambil data tambahan
    conn = get_conn()
    
    # Pet count
    pet_count = conn.execute("SELECT COUNT(*) FROM user_pets WHERE user_id=?", (user_id,)).fetchone()[0]
    
    # Item count
    item_count = conn.execute("SELECT COUNT(*) FROM inventory WHERE user_id=?", (user_id,)).fetchone()[0]
    
    # Achievement unlocked
    ach_count = conn.execute(
        "SELECT COUNT(*) FROM user_achievements WHERE user_id=? AND unlocked_at IS NOT NULL",
        (user_id,)
    ).fetchone()[0]
    
    # Boss killed
    boss_killed = conn.execute(
        "SELECT COUNT(*) FROM boss_battles bb "
        "JOIN guild_members gm ON bb.guild_id = gm.guild_id "
        "WHERE gm.user_id=? AND bb.status='defeated'",
        (user_id,)
    ).fetchone()[0]
    
    conn.close()
    
    # Hitung score (masing-masing max 100 poin)
    scores = {}
    
    # Level (max 100 poin, level 50 = 100 poin)
    scores['level'] = min(100, int(u.get('level', 1) * 2))
    
    # Total XP (max 100 poin, 100000 XP = 100 poin)
    total_xp = u.get('total_xp_earned', 0)
    scores['xp'] = min(100, int(total_xp / 1000))
    
    # Gold (max 100 poin, 100000 Gold = 100 poin)
    gold = u.get('gold', 0)
    scores['gold'] = min(100, int(gold / 1000))
    
    # Pet (max 100 poin, 10 pet = 100 poin)
    scores['pet'] = min(100, pet_count * 10)
    
    # Item (max 100 poin, 20 item = 100 poin)
    scores['item'] = min(100, item_count * 5)
    
    # Achievement (max 100 poin, 30 achievement = 100 poin)
    scores['achievement'] = min(100, int(ach_count * 3.33))
    
    # Rebirth (max 100 poin, 10 rebirth = 100 poin)
    rebirth = u.get('rebirth_count', 0)
    scores['rebirth'] = min(100, rebirth * 10)
    
    # Boss (max 100 poin, 10 boss = 100 poin)
    scores['boss'] = min(100, boss_killed * 10)
    
    # Sport Level (max 100 poin, level 20 = 100 poin)
    sport_level = u.get('sport_level', 1)
    scores['sport'] = min(100, sport_level * 5)
    
    # Total score (rata-rata dari semua kategori)
    total_score = int(sum(scores.values()) / len(scores))
    
    # --- 10 Rank ---
    RANKS = [
        {"min_score": 0,  "name_key": "rank_pemula",          "icon": "🥚", "desc_key": "rank_desc_pemula"},
        {"min_score": 10, "name_key": "rank_penambang",       "icon": "⛏️", "desc_key": "rank_desc_penambang"},
        {"min_score": 20, "name_key": "rank_penjelajah",      "icon": "🪓", "desc_key": "rank_desc_penjelajah"},
        {"min_score": 30, "name_key": "rank_petualang",       "icon": "⚔️", "desc_key": "rank_desc_petualang"},
        {"min_score": 40, "name_key": "rank_ksatria",         "icon": "🛡️", "desc_key": "rank_desc_ksatria"},
        {"min_score": 50, "name_key": "rank_veteran",         "icon": "⭐", "desc_key": "rank_desc_veteran"},
        {"min_score": 60, "name_key": "rank_legenda",         "icon": "🌟", "desc_key": "rank_desc_legenda"},
        {"min_score": 70, "name_key": "rank_raja",            "icon": "👑", "desc_key": "rank_desc_raja"},
        {"min_score": 80, "name_key": "rank_penguasa_naga",   "icon": "🐉", "desc_key": "rank_desc_penguasa_naga"},
        {"min_score": 90, "name_key": "rank_dewa",            "icon": "🌌", "desc_key": "rank_desc_dewa"},
    ]

    # Hitung rank saat ini
    current_rank = 0
    for i, rank in enumerate(RANKS):
        if total_score >= rank["min_score"]:
            current_rank = i

    rank_data = RANKS[current_rank]
    
    # Hitung progress ke rank berikutnya
    next_rank = current_rank + 1
    if next_rank < len(RANKS):
        min_score = RANKS[current_rank]["min_score"]
        next_min_score = RANKS[next_rank]["min_score"]
        progress = int(((total_score - min_score) / (next_min_score - min_score)) * 100) if next_min_score > min_score else 100
        next_rank_name_key = RANKS[next_rank]["name_key"]
        next_rank_icon = RANKS[next_rank]["icon"]
        has_next = True
    else:
        progress = 100
        next_rank_name_key = None
        next_rank_icon = "👑"
        has_next = False

    return {
        "rank": current_rank,
        "rank_name_key": rank_data["name_key"],
        "rank_icon": rank_data["icon"],
        "rank_desc_key": rank_data["desc_key"],
        "score": total_score,
        "progress": progress,
        "next_rank_name_key": next_rank_name_key,
        "next_rank_icon": next_rank_icon,
        "has_next": has_next,
        "max_score": 100,
        "scores": scores
    }


# ===========================================================================================================================#
if __name__ == "__main__":
    init_db()
    print("Database OK!")