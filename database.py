"""
CraftLife — database.py  v2.1  (fixed & complete)
Works both in VSCode and as PyInstaller .exe
"""
import sqlite3, hashlib, os, sys
from datetime import datetime, date
import pytz

import time
import functools

import traceback

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
    tz = pytz.timezone('Asia/Jakarta')  # Ganti sesuai zona user? Bisa juga ambil otomatis
    # Atau ambil zona waktu sistem:
    import tzlocal
    tz = tzlocal.get_localzone()
    return datetime.now(tz)

# ── Path auto-detect (VSCode + .exe) ─────────────────────────────────────────
import sys, os
from pathlib import Path

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

def get_conn():
    c = sqlite3.connect(DB_PATH, timeout=60.0)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    c.execute("PRAGMA busy_timeout = 60000")
    c.execute("PRAGMA synchronous = NORMAL")
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
               (SELECT COUNT(*) FROM user_pets WHERE user_id=users.id) as pet_count
        FROM users
        ORDER BY level DESC, total_xp_earned DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def init_db():
    conn = get_conn()
    c = conn.cursor()

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
        theme TEXT DEFAULT 'overworld', 
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

    # Tabel boss_battles dengan foreign key ke guilds (bukan parties)
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

    # --- MIGRASI: Perbaiki tabel boss_battles jika masih pakai party_id ---
    try:
        c.execute("PRAGMA table_info(boss_battles)")
        columns = [row[1] for row in c.fetchall()]
        if 'party_id' in columns:
            print("Migrasi boss_battles: party_id -> guild_id")
            # Buat tabel sementara dengan struktur benar (tanpa foreign key ke parties)
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
            # Salin data, ubah party_id menjadi guild_id
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

    # --- Safe migration untuk kolom tambahan (tidak berubah) ---
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
        ("theme","TEXT DEFAULT 'overworld'"),
        ("sound_enabled","INTEGER DEFAULT 1"),
        ("last_class_change", "TEXT"),
        ("reset_code", "TEXT"),
        ("reset_expiry", "TEXT"),
        ("sport_level", "INTEGER DEFAULT 1"),
        ("sport_xp", "INTEGER DEFAULT 0"),
        ("total_sport_points_earned", "INTEGER DEFAULT 0"),
        ("skill_buff_data", "TEXT DEFAULT '{}'"),
        ("class_passive_buffs", "TEXT DEFAULT '{}'"),
    ]
    for col, defn in migrate_cols:
        _safe_alter(c, "users", col, defn)
        _safe_alter(c, "habits", "last_action", "TEXT DEFAULT ''")
        _safe_alter(c, "dailies", "last_action", "TEXT DEFAULT ''")
        _safe_alter(c, "users", "security_question", "TEXT")
        _safe_alter(c, "users", "security_answer_hash", "TEXT")

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

    # Migrate: tambah folder_id ke tabel yang perlu
    _safe_alter(c, "habits",          "folder_id", "INTEGER")
    _safe_alter(c, "dailies",         "folder_id", "INTEGER")
    _safe_alter(c, "todos",           "folder_id", "INTEGER")
    _safe_alter(c, "sport_activities","folder_id", "INTEGER")
    _safe_alter(c, "economy_items", "folder_id", "INTEGER")

    # Nyalakan kembali foreign key
    c.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()
    print(f"[DB] Ready: {DB_PATH}")


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
        return {"ok": True, "msg": "Registrasi berhasil! Selamat datang, Minecrafter! ⛏️"}
    except sqlite3.IntegrityError:
        return {"ok": False, "msg": "Username sudah dipakai orang lain!"}
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
    return {"ok": False, "msg": "Username atau password salah!"}


def change_password(user_id, old_pw, new_pw):
    u = get_user(user_id)
    if _hash(old_pw) != u.get("password_hash", ""):
        return {"ok": False, "msg": "Password lama salah!"}
    conn = get_conn()
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (_hash(new_pw), user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Password berhasil diubah!"}


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
        for iid in owned:
            b = SHOP_ITEMS.get(iid, {}).get("buff", {})
            dmg += b.get("boss_dmg", 0)
            xp_pct += b.get("xp_pct", 0) / 100
            gold_pct += b.get("gold_pct", 0) / 100
            reduc += b.get("hp_reduc", 0)
            mp += b.get("mp_bonus", 0)
            if b.get("revive"):
                revive = 1

        # Pet aktif
        active_pet = conn.execute("SELECT pet_id, level FROM user_pets WHERE user_id=? AND is_active=1", (user_id,)).fetchone()
        if active_pet:
            pid = active_pet["pet_id"]
            base = PETS_DATA.get(pid, {}).get("base_buff", {})
            level = active_pet["level"]
            scale = 1 + (level - 1) * 0.02
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
            has_revive=?
            WHERE id=?""",
            (dmg, round(1.0 + xp_pct, 4), round(1.0 + gold_pct, 4),
             reduc, mp, new_max_mp, current_mp, revive, user_id))
        conn.commit()
    finally:
        conn.close()


# ── XP / Gold / HP ────────────────────────────────────────────────────────────

@retry_on_lock
def gain_xp_gold(user_id, xp_base, gold_base):
    u = get_user(user_id)
    if not u:
        return {"ok": False, "msg": "User tidak ditemukan", "leveled_up": False}
    
    print(f"[DEBUG] XP multiplier: {u.get('xp_multiplier', 1.0)}")
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
    
    total_xp_mult = u.get("xp_multiplier", 1.0) * skill_xp_mult
    total_gold_mult = u.get("gold_multiplier", 1.0) * skill_gold_mult
    
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
        add_notification(user_id, f"🎉 Level Up! Kamu sekarang Level {new_lvl}!", "levelup")
        apply_hp_multiplier(user_id)
        needed = new_lvl * 150
    update_user(user_id,
                xp=new_xp, level=new_lvl, gold=new_gold,
                total_xp_earned=u.get("total_xp_earned", 0) + xp,
                total_gold_earned=u.get("total_gold_earned", 0.0) + gold)
    log_activity(user_id, "reward", f"+{xp} XP, +{gold:.1f} Gold", xp, gold)
    u2 = get_user(user_id)
    if u2.get("guild_id"):
        add_guild_exp(u2["guild_id"], xp_base // 5)
    return {"ok": True, "leveled_up": leveled, "new_level": new_lvl,
            "new_xp": new_xp, "xp_gained": xp, "gold_gained": gold}


def lose_hp(user_id, amount):
    u = get_user(user_id)
    reduc  = u.get("hp_damage_reduction", 0)
    actual = max(0.0, amount - reduc)
    new_hp = max(0, u["hp"] - actual)
    if new_hp == 0 and u.get("has_revive"):
        new_hp = int(u["max_hp"] * 0.3)
        update_user(user_id, hp=new_hp, has_revive=0)
        recalculate_all_buffs(user_id)
        add_notification(user_id,
                         "🗿 Totem of Life menyelamatkanmu! HP dipulihkan 30%.",
                         "success")
        return {"revived": True, "new_hp": new_hp}
    update_user(user_id, hp=new_hp)
    if new_hp == 0:
        add_notification(user_id,
                         "💀 HP habis! Pulihkan HP sebelum ikut boss battle.",
                         "danger")
    return {"revived": False, "new_hp": new_hp}


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
                "desc": "+50% XP untuk 3 habit berikutnya"},
    "archer":  {"name": "Gold Shot",    "icon": "🏹",
                "mp_cost": 10,
                "desc": "+100% Gold dari habit berikutnya"},
    "healer":  {"name": "Regenerate",   "icon": "💚",
                "mp_cost": 20,
                "desc": "Pulihkan 30 HP sekarang juga"},
    "rogue":   {"name": "Shadow Step",  "icon": "🗡️",
                "mp_cost": 15,
                "desc": "Double streak daily berikutnya"},
}


def use_class_skill(user_id):
    u = get_user(user_id)
    cls = u.get("avatar_class", "warrior")
    skill = CLASS_SKILLS.get(cls, {})
    cost = skill.get("mp_cost", 10)
    if u["mp"] < cost:
        return {"ok": False, "msg": f"MP tidak cukup! Butuh {cost} MP, kamu punya {u['mp']} MP."}
    
    # Kurangi MP
    update_user(user_id, mp=u["mp"] - cost)
    
    # Handle skill Healer (langsung effect)
    if cls == "healer":
        new_hp = min(u["max_hp"], u["hp"] + 30)
        update_user(user_id, hp=new_hp)
        return {"ok": True, "msg": "💚 Regenerate! +30 HP dipulihkan."}
    
    # Skill lain: simpan buff state
    result = apply_skill_effect(user_id, cls)
    if result["ok"]:
        add_notification(user_id, result["msg"], "info")
    return result

import json

def get_skill_buffs(user_id):
    """Ambil data buff skill user dari database (JSON)"""
    conn = get_conn()
    row = conn.execute("SELECT skill_buff_data FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["skill_buff_data"]:
        return json.loads(row["skill_buff_data"])
    return {}

def set_skill_buffs(user_id, buffs):
    """Simpan data buff skill user ke database"""
    conn = get_conn()
    conn.execute("UPDATE users SET skill_buff_data=? WHERE id=?", (json.dumps(buffs), user_id))
    conn.commit()
    conn.close()

def get_class_passive_buffs(user_id):
    conn = get_conn()
    row = conn.execute("SELECT class_passive_buffs FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row and row["class_passive_buffs"]:
        return json.loads(row["class_passive_buffs"])
    return {}

def set_class_passive_buffs(user_id, buffs):
    conn = get_conn()
    conn.execute("UPDATE users SET class_passive_buffs=? WHERE id=?", (json.dumps(buffs), user_id))
    conn.commit()
    conn.close()

def update_class_passive_buffs(user_id):
    """Hitung ulang buff pasif berdasarkan class avatar"""
    u = get_user(user_id)
    cls = u.get("avatar_class", "warrior")
    buffs = {}
    if cls == "warrior":
        buffs = {"hp_multiplier": 1.20, "hp_bonus": 0}  # +20% HP
    elif cls == "mage":
        buffs = {"xp_multiplier": 1.15}  # +15% XP
    elif cls == "archer":
        buffs = {"gold_multiplier": 1.10}  # +10% Gold
    elif cls == "rogue":
        buffs = {"streak_bonus": 1}  # +1 streak awal? nanti di daily
    # Healer tidak punya buff pasif (skill sudah)
    set_class_passive_buffs(user_id, buffs)
    # Recalculate total buffs (panggil fungsi yang sudah ada)
    recalculate_all_buffs(user_id)

def apply_skill_effect(user_id, skill_name):
    """Terapkan efek skill ke user (simpan state)"""
    buffs = get_skill_buffs(user_id)
    if skill_name == "warrior":
        buffs["shield_active"] = True
        msg = "🛡️ Shield Bash aktif! Damage boss berikutnya -50%."
    elif skill_name == "mage":
        buffs["xp_multiplier"] = 1.5   # +50%
        buffs["xp_remaining"] = 3      # 3 habit berikutnya
        msg = "✨ Arcane Surge! +50% XP untuk 3 habit berikutnya."
    elif skill_name == "archer":
        buffs["gold_multiplier"] = 2.0  # +100%
        buffs["gold_remaining"] = 1     # 1 habit berikutnya
        msg = "🏹 Gold Shot! +100% Gold dari habit berikutnya."
    elif skill_name == "rogue":
        buffs["double_streak"] = True
        msg = "🗡️ Shadow Step! Double streak daily berikutnya."
    else:
        return {"ok": False, "msg": "Skill tidak dikenal"}
    
    set_skill_buffs(user_id, buffs)
    return {"ok": True, "msg": msg}

# ── Habits ────────────────────────────────────────────────────────────────────

_XP  = {"trivial": 8,  "easy": 15, "medium": 25, "hard": 40, "epic": 60}
_GLD = {"trivial": 2,  "easy": 3,  "medium": 5,  "hard": 8,  "epic": 12}


def get_habits(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM habits WHERE user_id=? ORDER BY created_at",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_habit(user_id, name, icon="⚔️", difficulty="medium",
              positive=1, negative=0, notes=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO habits(user_id,name,icon,difficulty,"
        "xp_reward,gold_reward,positive,negative,notes)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, name, icon, difficulty,
         _XP.get(difficulty, 25), _GLD.get(difficulty, 5),
         positive, negative, notes))
    conn.commit()
    conn.close()

def update_habit(habit_id, user_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE habits SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [habit_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_habit(user_id, habit_id, direction="up"):
    conn = get_conn()
    try:
        h = conn.execute("SELECT * FROM habits WHERE id=? AND user_id=?", (habit_id, user_id)).fetchone()
        if not h:
            return {"ok": False}
        today = date.today().isoformat()
        if h["done_today"]:
            return {"ok": False, "msg": "Kamu sudah melakukan action untuk habit ini hari ini!"}
        new_streak = h["streak"] + 1 if direction == "up" else 0
        conn.execute("""UPDATE habits SET done_today=1, streak=?, last_done=?, last_action=?, 
                        counter_up=counter_up+?, counter_down=counter_down+? WHERE id=?""",
                     (new_streak, today, direction, 1 if direction=="up" else 0, 1 if direction=="down" else 0, habit_id))
        conn.execute("UPDATE users SET total_habits_done=total_habits_done+1 WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()

    if direction == "up":
        restore_mp(user_id, 3)
        u = get_user(user_id)
        if new_streak > u.get("longest_streak", 0):
            update_user(user_id, longest_streak=new_streak)
        return gain_xp_gold(user_id, h["xp_reward"], h["gold_reward"])
    else:
        lose_hp(user_id, 5)
        return {"ok": True, "lost_hp": 5}

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
        conn.execute(
            "UPDATE guilds SET level=?, exp=?, buff_xp=?, buff_gold=?, buff_damage=? WHERE id=?",
            (new_level, new_exp, buff_xp, buff_gold, buff_damage, guild_id))
        members = conn.execute("SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)).fetchall()
        member_ids = [m["user_id"] for m in members]
    else:
        conn.execute("UPDATE guilds SET exp=? WHERE id=?", (new_exp, guild_id))
    conn.commit()
    conn.close()   # ← TUTUP dulu sebelum panggil add_notification / recalculate_all_buffs

    # ── Step 2: Notifikasi & recalc buff (koneksi terpisah, tidak nested) ─────
    if leveled:
        for uid in member_ids:
            add_notification(uid, f"🏆 Guild {g['name']} naik level {new_level}!", "levelup")
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
    conn.close()


# ── Dailies ───────────────────────────────────────────────────────────────────

def get_dailies(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM dailies WHERE user_id=? ORDER BY created_at",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_daily(user_id, name, icon="📅", difficulty="medium", notes=""):
    xd  = {"easy": 20, "medium": 30, "hard": 50, "epic": 75}
    gd  = {"easy": 4,  "medium": 6,  "hard": 10, "epic": 15}
    conn = get_conn()
    conn.execute(
        "INSERT INTO dailies(user_id,name,icon,difficulty,"
        "xp_reward,gold_reward,notes) VALUES(?,?,?,?,?,?,?)",
        (user_id, name, icon, difficulty,
         xd.get(difficulty, 30), gd.get(difficulty, 6), notes))
    conn.commit()
    conn.close()

def update_daily(daily_id, user_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE dailies SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [daily_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_daily(user_id, daily_id):
    # ── Step 1: Baca data daily & tutup koneksi ───────────────────────────────
    conn = get_conn()
    try:
        d = conn.execute("SELECT * FROM dailies WHERE id=? AND user_id=?", (daily_id, user_id)).fetchone()
        if not d or d["done_today"]:
            return {"ok": False, "msg": "Sudah selesai!"}
        d = dict(d)
    finally:
        conn.close()   # TUTUP dulu sebelum panggil get/set_skill_buffs

    today = date.today().isoformat()

    # ── Step 2: Ambil & update buff skill (koneksi terpisah, tidak nested) ────
    buffs = get_skill_buffs(user_id)
    streak_bonus = 2 if buffs.get("double_streak") else 1
    if buffs.get("double_streak"):
        buffs.pop("double_streak", None)
        set_skill_buffs(user_id, buffs)
    new_streak = d["streak"] + streak_bonus

    # ── Step 3: Update daily (koneksi baru) ───────────────────────────────────
    conn2 = get_conn()
    try:
        conn2.execute(
            "UPDATE dailies SET done_today=1, streak=?, last_done=?, last_action='up' WHERE id=?",
            (new_streak, today, daily_id))
        conn2.execute(
            "UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?",
            (user_id,))
        conn2.commit()
    finally:
        conn2.close()

    restore_mp(user_id, 5)
    return gain_xp_gold(user_id, d["xp_reward"], d["gold_reward"])

@retry_on_lock
def fail_daily(user_id, daily_id):
    conn = get_conn()
    d = conn.execute("SELECT * FROM dailies WHERE id=? AND user_id=?", (daily_id, user_id)).fetchone()
    if not d or d["done_today"]:
        conn.close()
        return {"ok": False, "msg": "Kamu sudah melakukan action untuk daily ini hari ini!"}
    today = date.today().isoformat()
    conn.execute("UPDATE dailies SET done_today=1, streak=0, last_done=?, last_action='down' WHERE id=?", (today, daily_id))
    conn.execute("UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    lose_hp(user_id, 5)
    return {"ok": True, "lost_hp": 5}

def delete_daily(user_id, daily_id):
    conn = get_conn()
    conn.execute("DELETE FROM dailies WHERE id=? AND user_id=?",
                 (daily_id, user_id))
    conn.commit()
    conn.close()


# ── Todos ─────────────────────────────────────────────────────────────────────

def get_todos(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM todos WHERE user_id=?"
        " ORDER BY done ASC, created_at DESC",
        (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_todo(user_id, name, priority="medium", icon="📜",
             due_date=None, notes=""):
    xp = {"trivial": 10, "easy": 20, "medium": 40, "hard": 60}
    gp = {"trivial": 2,  "easy": 4,  "medium": 8,  "hard": 14}
    conn = get_conn()
    conn.execute(
        "INSERT INTO todos(user_id,name,icon,priority,"
        "xp_reward,gold_reward,due_date,notes) VALUES(?,?,?,?,?,?,?,?)",
        (user_id, name, icon, priority,
         xp.get(priority, 40), gp.get(priority, 8), due_date, notes))
    conn.commit()
    conn.close()

def update_todo(todo_id, user_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k}=?" for k in kwargs)
    conn.execute(f"UPDATE todos SET {fields} WHERE id=? AND user_id=?", list(kwargs.values()) + [todo_id, user_id])
    conn.commit()
    conn.close()

@retry_on_lock
def complete_todo(user_id, todo_id):
    conn = get_conn()
    try:
        t = conn.execute("SELECT * FROM todos WHERE id=? AND user_id=?", (todo_id, user_id)).fetchone()
        if not t or t["done"]:
            return {"ok": False}
        conn.execute("UPDATE todos SET done=1 WHERE id=?", (todo_id,))
        conn.execute("UPDATE users SET total_todos_done=total_todos_done+1 WHERE id=?", (user_id,))
        conn.commit()
    finally:
        conn.close()
    restore_mp(user_id, 4)
    return gain_xp_gold(user_id, t["xp_reward"], t["gold_reward"])

def delete_todo(user_id, todo_id):
    conn = get_conn()
    conn.execute("DELETE FROM todos WHERE id=? AND user_id=?",
                 (todo_id, user_id))
    conn.commit()
    conn.close()

# ═══════════════════════════════════════════════════════════════════════════════
# ── SPORT TRACK ───────────────────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

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
        return {"ok": False, "msg": "Folder tidak ditemukan."}

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
    """Pindahkan item ke folder tertentu (None = ungrouped)."""
    table_map = {"habit": "habits", "daily": "dailies",
                 "todo": "todos", "sport": "sport_activities"}
    tbl = table_map.get(mode)
    if not tbl:
        return
    conn = get_conn()
    conn.execute(f"UPDATE {tbl} SET folder_id=? WHERE id=? AND user_id=?",
                 (folder_id, item_id, user_id))
    conn.commit()
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
            "SELECT * FROM sport_activities WHERE user_id=? AND sport_type=?"
            " ORDER BY created_at", (user_id, sport_type)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM sport_activities WHERE user_id=?"
            " ORDER BY sport_type, created_at", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_sport_activity(user_id, name, sport_type="running", icon="🏃",
                       difficulty="medium", notes=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO sport_activities"
        "(user_id,name,sport_type,icon,difficulty,"
        "xp_reward,gold_reward,sport_points_reward,notes)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (user_id, name, sport_type, icon, difficulty,
         _SP_XP.get(difficulty, 25), _SP_GLD.get(difficulty, 5),
         _SP_PTS.get(difficulty, 15), notes))
    conn.commit()
    conn.close()


def update_sport_activity(activity_id, user_id, **kwargs):
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


def delete_sport_activity(user_id, activity_id):
    conn = get_conn()
    conn.execute("DELETE FROM sport_activities WHERE id=? AND user_id=?",
                 (activity_id, user_id))
    conn.commit()
    conn.close()


@retry_on_lock
def complete_sport_activity(user_id, activity_id):
    conn = get_conn()
    try:
        a = conn.execute("SELECT * FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id)).fetchone()
        if not a:
            return {"ok": False, "msg": "Aktivitas tidak ditemukan!"}
        if a["done_today"]:
            return {"ok": False, "msg": "Kamu sudah menyelesaikan aktivitas ini hari ini!"}
        today = date.today().isoformat()
        conn.execute("UPDATE sport_activities SET done_today=1, streak=streak+1, last_done=? WHERE id=?", (today, activity_id))
        conn.commit()
    finally:
        conn.close()
    result = gain_xp_gold(user_id, a["xp_reward"], a["gold_reward"])
    sp_result = gain_sport_points(user_id, a["sport_points_reward"])
    result["sport_points_gained"] = a["sport_points_reward"]
    result["sport_leveled_up"] = sp_result.get("leveled_up", False)
    result["new_sport_level"] = sp_result.get("new_sport_level", 1)
    result["new_sport_xp"] = sp_result.get("new_sport_xp", 0)
    return result


def gain_sport_points(user_id, points):
    """Tambahkan sport points & hitung sport level.
    Sport level TIDAK mempengaruhi main level/XP user sama sekali.
    Formula naik level: butuh level*100 sport points.
    """
    conn = get_conn()
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
        add_notification(
            user_id,
            f"🏅 Sport Level Up! Kamu sekarang Sport Level {new_sport_lvl}!",
            "levelup")

    return {"ok": True, "leveled_up": leveled,
            "new_sport_level": new_sport_lvl,
            "new_sport_xp": new_sport_xp}

# ── Duplikasi ─────────────────────────────────────────
def duplicate_habit(user_id, habit_id):
    conn = get_conn()
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
    a = conn.execute("SELECT * FROM sport_activities WHERE id=? AND user_id=?", (activity_id, user_id)).fetchone()
    if not a:
        conn.close()
        return {"ok": False, "msg": "Aktivitas tidak ditemukan!"}
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
    "wooden_sword":    {"name": "Wooden Sword",    "icon": "🗡️", "cost": 25,
                        "type": "weapon",    "desc": "Starter blade",
                        "buff": {"boss_dmg": 2},
                        "buff_desc": "+2 Boss Damage"},
    "enchanted_bow":   {"name": "Enchanted Bow",   "icon": "🏹", "cost": 90,
                        "type": "weapon",    "desc": "Ranged power",
                        "buff": {"boss_dmg": 8},
                        "buff_desc": "+8 Boss Damage"},
    "trident":         {"name": "Trident",         "icon": "🔱", "cost": 180,
                        "type": "weapon",    "desc": "Legendary weapon",
                        "buff": {"boss_dmg": 15},
                        "buff_desc": "+15 Boss Damage"},
    "shield":          {"name": "Shield",          "icon": "🛡️", "cost": 60,
                        "type": "armor",     "desc": "Reduces HP damage",
                        "buff": {"hp_reduc": 5},
                        "buff_desc": "-5 per HP hit taken"},
    "golden_boots":    {"name": "Golden Boots",    "icon": "👢", "cost": 70,
                        "type": "armor",     "desc": "Swift & rich",
                        "buff": {"gold_pct": 10},
                        "buff_desc": "+10% Gold earned"},
    "diamond_armor":   {"name": "Diamond Armor",   "icon": "💎", "cost": 150,
                        "type": "armor",     "desc": "Max protection",
                        "buff": {"hp_reduc": 20},
                        "buff_desc": "-20 per HP hit taken"},
    "elytra":          {"name": "Elytra Wings",    "icon": "🪽", "cost": 250,
                        "type": "armor",     "desc": "Glide & grow",
                        "buff": {"xp_pct": 10},
                        "buff_desc": "+10% XP all sources"},
    "iron_pickaxe":    {"name": "Iron Pickaxe",    "icon": "⛏️", "cost": 50,
                        "type": "tool",      "desc": "Mine habits faster",
                        "buff": {"xp_pct": 10},
                        "buff_desc": "+10% XP from habits"},
    "compass":         {"name": "Compass",         "icon": "🧭", "cost": 40,
                        "type": "tool",      "desc": "Navigate to gold",
                        "buff": {"gold_pct": 5},
                        "buff_desc": "+5% Gold earned"},
    "spyglass":        {"name": "Spyglass",        "icon": "🔭", "cost": 45,
                        "type": "tool",      "desc": "Scout ahead",
                        "buff": {},
                        "buff_desc": "Reveal boss stats"},
    "ender_pearl":     {"name": "Ender Pearl",     "icon": "🔮", "cost": 120,
                        "type": "special",   "desc": "Teleport magic",
                        "buff": {"mp_bonus": 15},
                        "buff_desc": "+15 Max MP"},
    "blaze_rod":       {"name": "Blaze Rod",       "icon": "🔥", "cost": 80,
                        "type": "special",   "desc": "Nether fire",
                        "buff": {"boss_dmg": 5},
                        "buff_desc": "+5 Boss Damage"},
    "golden_apple":    {"name": "Golden Apple",    "icon": "🍎", "cost": 30,
                        "type": "consumable","desc": "Restore 20 HP",
                        "buff": {},
                        "buff_desc": "Use: +20 HP sekarang"},
    "enchanted_apple": {"name": "Enchanted Apple", "icon": "🍏", "cost": 120,
                        "type": "consumable","desc": "Restore 50 HP",
                        "buff": {},
                        "buff_desc": "Use: +50 HP sekarang"},
    "totem":           {"name": "Totem of Life",   "icon": "🗿", "cost": 200,
                        "type": "legendary", "desc": "Auto-revive from death",
                        "buff": {"revive": True},
                        "buff_desc": "Auto-revive sekali di 30% HP"},
    "nether_star":     {"name": "Nether Star",     "icon": "⭐", "cost": 300,
                        "type": "legendary",
                        "desc": "Power of the Nether",
                        "buff": {"xp_pct": 15, "gold_pct": 15, "boss_dmg": 10},
                        "buff_desc": "+15% XP, +15% Gold, +10 Boss DMG"},
    "beacon":          {"name": "Beacon",          "icon": "🏮", "cost": 500,
                        "type": "legendary", "desc": "Strongest relic",
                        "buff": {"xp_pct": 20, "gold_pct": 20,
                                 "boss_dmg": 20, "hp_reduc": 10},
                        "buff_desc": "+20% XP, +20% Gold, +20 DMG, -10 HP taken"},
}

PETS_DATA = {
    "wolf":     {"name": "Wolf", "icon": "🐺", "cost": 80,
                 "bonus": "+5 XP per habit",
                 "base_buff": {"xp_pct": 5}},
    "cat":      {"name": "Cat", "icon": "🐱", "cost": 60,
                 "bonus": "-10% HP loss",
                 "base_buff": {"hp_reduc": 2}},
    "parrot":   {"name": "Parrot", "icon": "🦜", "cost": 70,
                 "bonus": "+3 Gold per task",
                 "base_buff": {"gold_pct": 5}},
    "panda":    {"name": "Panda", "icon": "🐼", "cost": 120,
                 "bonus": "+15 XP per daily",
                 "base_buff": {"xp_pct": 8}},
    "fox":      {"name": "Fox", "icon": "🦊", "cost": 90,
                 "bonus": "+8% Gold bonus",
                 "base_buff": {"gold_pct": 8}},
    "bee":      {"name": "Bee", "icon": "🐝", "cost": 55,
                 "bonus": "Honey restores HP",
                 "base_buff": {"hp_reduc": 1}},
    "dragon":   {"name": "Dragon", "icon": "🐉", "cost": 300,
                 "bonus": "+25 XP on all tasks",
                 "base_buff": {"xp_pct": 15, "boss_dmg": 5}},
    "turtle":   {"name": "Turtle", "icon": "🐢", "cost": 65,
                 "bonus": "+2 HP per day",
                 "base_buff": {"hp_reduc": 3}},
    "axolotl":  {"name": "Axolotl", "icon": "🦎", "cost": 100,
                 "bonus": "+5 HP regeneration",
                 "base_buff": {"hp_reduc": 2}},
    "enderman": {"name": "Enderman", "icon": "👾", "cost": 200,
                 "bonus": "+20% XP rare bonus",
                 "base_buff": {"xp_pct": 10, "gold_pct": 5, "boss_dmg": 3}},
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
        return {"ok": False, "msg": "Item tidak ditemukan!"}
    u = get_user(user_id)
    if u["gold"] < item["cost"]:
        return {"ok": False,
                "msg": f"Gold tidak cukup! Butuh {item['cost']} G."}
    conn = get_conn()
    ex = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=?",
        (user_id, item_id)).fetchone()
    if ex and item["type"] not in ("consumable",):
        conn.close()
        return {"ok": False, "msg": "Item sudah dimiliki!"}
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
    recalculate_all_buffs(user_id)
    log_activity(user_id, "buy", f"Membeli {item['name']}", 0, -item["cost"])
    return {"ok": True,
            "msg": (f"{item['icon']} {item['name']} berhasil dibeli!\n"
                    f"✨ Buff aktif: {item['buff_desc']}")}


def use_item(user_id, item_id):
    item = SHOP_ITEMS.get(item_id)
    if not item or item["type"] != "consumable":
        return {"ok": False}
    conn = get_conn()
    inv = conn.execute(
        "SELECT * FROM inventory WHERE user_id=? AND item_id=? AND quantity>0",
        (user_id, item_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": "Item tidak tersedia di inventory!"}
    hp_map = {"golden_apple": 20, "enchanted_apple": 50}
    restore = hp_map.get(item_id, 0)
    if restore:
        conn.execute(
            "UPDATE users SET hp=MIN(max_hp, hp+?) WHERE id=?",
            (restore, user_id))
        conn.execute(
            "UPDATE inventory SET quantity=quantity-1 WHERE id=?",
            (inv["id"],))
        conn.commit()
        conn.close()
        return {"ok": True, "msg": f"{item['icon']} +{restore} HP dipulihkan!"}
    conn.close()
    return {"ok": False}


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
        return {"ok": False, "msg": "Pet tidak ditemukan!"}
    u = get_user(user_id)
    if u["gold"] < pet["cost"]:
        return {"ok": False, "msg": f"Gold tidak cukup! Butuh {pet['cost']} G."}
    conn = get_conn()
    if conn.execute("SELECT 1 FROM user_pets WHERE user_id=? AND pet_id=?", (user_id, pet_id)).fetchone():
        conn.close()
        return {"ok": False, "msg": "Pet sudah diadopsi!"}
    conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (pet["cost"], user_id))
    conn.execute("INSERT INTO user_pets(user_id, pet_id, hunger, happiness) VALUES(?,?,100,50)", (user_id, pet_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": f"{pet['icon']} {pet['name']} berhasil diadopsi!"}

def equip_pet(user_id, pet_id):
    conn = get_conn()
    conn.execute("UPDATE user_pets SET is_active=0 WHERE user_id=?", (user_id,))
    conn.execute("UPDATE user_pets SET is_active=1 WHERE user_id=? AND pet_id=?", (user_id, pet_id))
    conn.commit()
    conn.close()
    recalculate_all_buffs(user_id)   # fungsi baru, lihat di bawah
    return {"ok": True, "msg": f"Pet {pet_id} diaktifkan!"}

@retry_on_lock
def feed_pet(user_id, pet_id):
    pet = get_user_pet_by_id(user_id, pet_id)
    if not pet:
        return {"ok": False, "msg": "Pet tidak ditemukan!"}
    u = get_user(user_id)
    cost = 10
    if u["gold"] < cost:
        return {"ok": False, "msg": f"Gold tidak cukup! Butuh {cost} G."}
    new_hunger = min(100, pet["hunger"] + 30)
    conn = get_conn()
    try:
        conn.execute("UPDATE user_pets SET hunger=?, last_fed=? WHERE id=?", (new_hunger, local_now().isoformat(), pet["id"]))
        conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
        conn.commit()
    finally:
        conn.close()
    return {"ok": True, "msg": f"🍖 {PETS_DATA[pet_id]['name']} kenyang! ({cost} G)"}

@retry_on_lock
def train_pet(user_id, pet_id):
    pet = get_user_pet_by_id(user_id, pet_id)
    if not pet:
        return {"ok": False, "msg": "Pet tidak ditemukan!"}
    if pet["hunger"] < 20:
        return {"ok": False, "msg": "Pet lapar! Beri makan dulu."}
    u = get_user(user_id)
    cost = 5
    if u["gold"] < cost:
        return {"ok": False, "msg": f"Gold tidak cukup! Butuh {cost} G."}
    new_hunger = max(0, pet["hunger"] - 20)
    conn = get_conn()
    leveled = False
    try:
        conn.execute("UPDATE user_pets SET hunger=? WHERE id=?", (new_hunger, pet["id"]))
        leveled = add_pet_exp(conn, pet["id"], 15)
        conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
        conn.commit()
    finally:
        conn.close()
    if leveled:
        recalculate_all_buffs(user_id)
    return {"ok": True, "msg": f"🏋️ {PETS_DATA[pet_id]['name']} latihan! +15 EXP pet. ({cost} G)"}

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
    conn = get_conn()
    gid = get_next_guild_id()
    conn.execute("INSERT INTO guilds(id, name, description, leader_id) VALUES(?,?,?,?)",
                 (gid, name, description, leader_id))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (gid, leader_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (gid, leader_id))
    conn.commit()
    conn.close()
    return {"ok": True, "guild_id": gid, "msg": f"Guild '{name}' dibuat! ID: {gid}"}


# ── Guild Request Join ───────────────────────────────────
def send_guild_request(user_id, guild_id):
    conn = get_conn()
    guild = conn.execute("SELECT id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild:
        conn.close()
        return {"ok": False, "msg": "Guild tidak ditemukan!"}
    # Cek apakah sudah member
    existing = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "msg": "Kamu sudah menjadi anggota guild ini!"}
    # Cek apakah sudah ada request pending
    pending = conn.execute("SELECT 1 FROM guild_requests WHERE guild_id=? AND user_id=? AND status='pending'", (guild_id, user_id)).fetchone()
    if pending:
        conn.close()
        return {"ok": False, "msg": "Permintaanmu sudah terkirim, tunggu respon leader."}
    conn.execute("INSERT INTO guild_requests(guild_id, user_id) VALUES(?,?)", (guild_id, user_id))
    conn.commit()
    # Notifikasi ke leader
    leader = conn.execute("SELECT leader_id FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if leader:
        add_notification(leader["leader_id"], f"📩 {get_user(user_id)['display_name']} ingin bergabung ke guild {guild['name']}. Cek menu Guild!", "info")
    conn.close()
    return {"ok": True, "msg": "Permintaan bergabung telah dikirim ke leader!"}

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
    # Cek leader dan ambil nama guild
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": "Hanya leader yang bisa menerima permintaan!"}
    req = conn.execute("SELECT * FROM guild_requests WHERE id=? AND guild_id=? AND status='pending'", (request_id, guild_id)).fetchone()
    if not req:
        conn.close()
        return {"ok": False, "msg": "Permintaan tidak ditemukan!"}
    conn.execute("UPDATE guild_requests SET status='accepted' WHERE id=?", (request_id,))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (guild_id, req["user_id"]))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (guild_id, req["user_id"]))
    conn.commit()
    conn.close()
    # Gunakan guild['name'] yang sudah pasti ada
    add_notification(req["user_id"], f"✅ Permintaanmu ke guild {guild['name']} diterima! Selamat bergabung!", "success")
    return {"ok": True, "msg": "Pemain diterima!"}

def reject_guild_request(guild_id, leader_id, request_id):
    conn = get_conn()
    guild = conn.execute("SELECT leader_id FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": "Hanya leader yang bisa menolak!"}
    conn.execute("UPDATE guild_requests SET status='rejected' WHERE id=? AND guild_id=?", (request_id, guild_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Permintaan ditolak."}

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

def start_boss(guild_id, boss_id, user_level=1):
    boss = BOSSES.get(boss_id)
    if not boss:
        return {"ok": False, "msg": "Boss tidak ditemukan!"}
    if user_level < boss.get("min_level", 1):
        return {"ok": False,
                "msg": (f"Level terlalu rendah! "
                        f"Butuh Level {boss['min_level']}.")}
    conn = get_conn()
    if conn.execute(
            "SELECT 1 FROM boss_battles"
            " WHERE guild_id=? AND status='active'",
            (guild_id,)).fetchone():
        conn.close()
        return {"ok": False, "msg": "Sudah ada boss aktif!"}
    conn.execute(
        "INSERT INTO boss_battles"
        "(guild_id,boss_id,boss_name,boss_icon,boss_tier,"
        "boss_hp,boss_max_hp,boss_attack)"
        " VALUES(?,?,?,?,?,?,?,?)",
        (guild_id, boss_id, boss["name"], boss["icon"], boss["tier"],
         boss["hp"], boss["hp"], boss["atk"]))
    conn.execute("UPDATE guilds SET quest_id=? WHERE id=?",
                 (boss_id, guild_id))
    conn.commit()
    conn.close()
    return {"ok": True,
            "msg": (f"{boss['icon']} {boss['name']} muncul! "
                    f"Tier: {boss['tier'].upper()}")}


@retry_on_lock
def attack_boss(user_id, guild_id, base_damage=25):
    u = get_user(user_id)
    if u["hp"] <= 0:
        return {"ok": False, "msg": "HP 0! Tidak bisa menyerang."}

    # ── Step 1: Baca data boss, tutup koneksi ─────────────────────────────────
    try:
        conn = get_conn()
        boss_row = conn.execute(
            "SELECT * FROM boss_battles WHERE guild_id=? AND status='active'", (guild_id,)
        ).fetchone()
        conn.close()
    except Exception as e:
        log_crash(f"attack_boss SELECT boss error: {e}")
        return {"ok": False, "msg": f"Error internal: {str(e)}"}

    if not boss_row:
        return {"ok": False, "msg": "Tidak ada boss aktif!"}
    boss = dict(boss_row)

    # ── Step 2: Cek & terapkan buff Shield Bash (conn sudah tutup) ───────────
    total_dmg = base_damage + u.get("boss_damage_bonus", 0)
    boss_attack = boss["boss_attack"]
    buffs = get_skill_buffs(user_id)
    if buffs.get("shield_active"):
        boss_attack = boss_attack // 2
        buffs.pop("shield_active", None)
        set_skill_buffs(user_id, buffs)
        add_notification(user_id, "🛡️ Shield Bash melindungimu! Damage boss berkurang 50%.", "info")

    new_hp = max(0.0, boss["boss_hp"] - total_dmg)

    # ── Step 3a: Boss mati ────────────────────────────────────────────────────
    if new_hp <= 0:
        try:
            conn = get_conn()
            conn.execute(
                "UPDATE boss_battles SET boss_hp=0, status='defeated', ended_at=? WHERE id=?",
                (local_now().isoformat(), boss["id"]))
            bdata = BOSSES.get(boss["boss_id"], {})
            members = conn.execute(
                "SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)
            ).fetchall()
            cnt = max(1, len(members))
            xp_reward  = bdata.get("xp",   200) // cnt
            gold_reward = bdata.get("gold",  50) // cnt
            for m in members:
                conn.execute("""
                    INSERT INTO boss_rewards(user_id, guild_id, boss_name, boss_tier, xp_reward, gold_reward)
                    VALUES(?,?,?,?,?,?)
                """, (m["user_id"], guild_id, boss["boss_name"], boss["boss_tier"], xp_reward, gold_reward))
            member_ids = [m["user_id"] for m in members]
            conn.commit()
            conn.close()   # ← TUTUP sebelum panggil add_notification
        except Exception as e:
            log_crash(f"attack_boss boss-death update error: {e}")
            return {"ok": False, "msg": f"Error internal: {str(e)}"}

        for uid in member_ids:
            add_notification(uid,
                f"🏆 Boss {boss['boss_name']} telah dikalahkan! Klik 'Klaim Reward' di halaman Guild.",
                "success")
        return {"ok": True, "defeated": True, "total_dmg": total_dmg,
                "msg": f"🏆 {boss['boss_name']} dikalahkan! Kumpulkan rewardmu di halaman Guild."}

    # ── Step 3b: Boss belum mati — update HP ─────────────────────────────────
    try:
        conn = get_conn()
        conn.execute("UPDATE boss_battles SET boss_hp=? WHERE id=?", (new_hp, boss["id"]))
        conn.commit()
        conn.close()   # ← TUTUP sebelum panggil lose_hp
    except Exception as e:
        log_crash(f"attack_boss update HP error: {e}")
        return {"ok": False, "msg": f"Error internal: {str(e)}"}

    lr = lose_hp(user_id, boss_attack)
    return {"ok": True, "defeated": False, "remaining_hp": new_hp,
            "boss_max_hp": boss["boss_max_hp"], "total_dmg": total_dmg,
            "hp_lost": boss_attack, "revived": lr.get("revived", False)}

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
            return {"ok": False, "msg": "Reward tidak valid atau sudah diklaim."}
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
        "msg": f"✅ Kamu mendapat +{reward['xp_reward']} XP, +{reward['gold_reward']} Gold!",
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
        conn.execute("INSERT INTO notifications(user_id,message,type) VALUES(?,?,?)", (user_id, message, type_))
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
        "INSERT INTO activity_log"
        "(user_id,action,detail,xp_gained,gold_gained)"
        " VALUES(?,?,?,?,?)",
        (user_id, action, detail, xp, gold))
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
    "overworld": {
        "label": "🌿 Overworld",
        "primary": "#5a8a2e", "light": "#7bbf3e",
        "bg": "#1a1a1a", "panel": "#2d2d2d", "border": "#444",
        "accent": "#80c000", "text": "#e8e8e8", "muted": "#888",
    },
    "nether": {
        "label": "🔥 Nether",
        "primary": "#8a2e1a", "light": "#d04020",
        "bg": "#150808", "panel": "#2a1010", "border": "#4a200a",
        "accent": "#ff6a00", "text": "#f0d8d0", "muted": "#a07070",
    },
    "the_end": {
        "label": "🌌 The End",
        "primary": "#5a2e8a", "light": "#9a50e0",
        "bg": "#0a0810", "panel": "#1a1025", "border": "#3a2060",
        "accent": "#c040ff", "text": "#e0d8f0", "muted": "#907090",
    },
    "ocean": {
        "label": "🌊 Ocean",
        "primary": "#1a6a8a", "light": "#20a0c8",
        "bg": "#050c14", "panel": "#0d1e2a", "border": "#1a3a50",
        "accent": "#00c8e8", "text": "#d0eaf8", "muted": "#608aaa",
    },
    "ancient_city": {
        "label": "🏚️ Ancient City",
        "primary": "#1a5050", "light": "#20a090",
        "bg": "#050c0c", "panel": "#0d1e1e", "border": "#1a3535",
        "accent": "#00e0c0", "text": "#c8f0e8", "muted": "#5a8a80",
    },
}


def get_user_theme(user_id):
    u = get_user(user_id)
    return THEMES.get(u.get("theme", "overworld"), THEMES["overworld"])


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
    return {"ok": True, "msg": "Avatar diperbarui!"}

def change_class(user_id, new_class):
    """Ganti class avatar — maksimal sekali sehari."""
    if new_class not in AVATAR_CLASSES:
        return {"ok": False, "msg": "Class tidak dikenal!"}
    u = get_user(user_id)
    last_change = u.get("last_class_change", "")
    today = date.today().isoformat()
    if last_change == today:
        return {"ok": False, "msg": "Kamu sudah mengganti class hari ini. Coba lagi besok! ⏳"}
    update_user(user_id, avatar_class=new_class, last_class_change=today)
    update_class_passive_buffs(user_id)
    recalculate_all_buffs(user_id)
    apply_hp_multiplier(user_id)
    return {"ok": True, "msg": f"Class berhasil diubah menjadi {AVATAR_CLASSES[new_class]['name']}!"}

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
    from docx.shared import Inches, Pt
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
    target = conn.execute("SELECT id FROM users WHERE username=?", (target_username.lower(),)).fetchone()
    if not target:
        conn.close()
        return {"ok": False, "msg": "User tidak ditemukan!"}
    if target["id"] == user_id:
        conn.close()
        return {"ok": False, "msg": "Tidak bisa berteman dengan diri sendiri!"}
    existing = conn.execute("SELECT * FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)", 
                            (user_id, target["id"], target["id"], user_id)).fetchone()
    if existing:
        if existing["status"] == "accepted":
            conn.close()
            return {"ok": False, "msg": "Kamu sudah berteman dengan user ini!"}
        else:
            conn.close()
            return {"ok": False, "msg": "Permintaan pertemanan sudah terkirim!"}
    conn.execute("INSERT INTO friends(user_id, friend_id, status, action_user_id) VALUES(?,?,?,?)",
                 (user_id, target["id"], "pending", user_id))
    conn.commit()
    conn.close()
    add_notification(target["id"], f"📨 {get_user(user_id)['display_name']} mengirim permintaan pertemanan!", "info")
    return {"ok": True, "msg": "Permintaan pertemanan dikirim!"}

def accept_friend_request(user_id, request_id):
    conn = get_conn()
    req = conn.execute("SELECT * FROM friends WHERE id=? AND friend_id=? AND status='pending'", (request_id, user_id)).fetchone()
    if not req:
        conn.close()
        return {"ok": False, "msg": "Permintaan tidak valid!"}
    conn.execute("UPDATE friends SET status='accepted' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()
    add_notification(req["user_id"], f"✅ {get_user(user_id)['display_name']} menerima permintaan pertemananmu!", "success")
    return {"ok": True, "msg": "Pertemanan diterima!"}

def reject_friend_request(user_id, request_id):
    conn = get_conn()
    conn.execute("DELETE FROM friends WHERE id=? AND friend_id=? AND status='pending'", (request_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Permintaan ditolak."}

def get_friends(user_id):
    conn = get_conn()
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
        return {"ok": False, "msg": "Hanya leader yang bisa mengeluarkan anggota!"}
    if target_user_id == leader_id:
        conn.close()
        return {"ok": False, "msg": "Tidak bisa mengeluarkan diri sendiri!"}
    member = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, target_user_id)).fetchone()
    if not member:
        conn.close()
        return {"ok": False, "msg": "User bukan anggota guild ini!"}
    conn.execute("DELETE FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, target_user_id))
    conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (target_user_id,))
    conn.commit()
    conn.close()
    add_notification(target_user_id, f"⚠️ Kamu dikeluarkan dari guild {guild['name']} oleh leader.", "danger")
    return {"ok": True, "msg": "Anggota berhasil dikeluarkan!"}

# ========== GUILD LEADER TRANSFER (saat leader keluar) ==========
def leave_guild_with_transfer(user_id):
    u = get_user(user_id)
    gid = u.get("guild_id")
    if not gid:
        return {"ok": False, "msg": "Kamu tidak di dalam guild."}
    conn = get_conn()
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (gid,)).fetchone()
    if not guild:
        conn.close()
        return {"ok": False, "msg": "Guild tidak ditemukan."}
    
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
                add_notification(m["user_id"], f"👑 Leader guild {guild['name']} keluar! Klik 'Terima' untuk menjadi leader baru (cepat!).", "warning")
            conn.close()
            return {"ok": True, "msg": "Kamu keluar dari guild. Member lain akan memilih leader baru."}
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
            return {"ok": True, "msg": "Kamu keluar dari guild. Guild dibubarkan karena tidak ada anggota lain."}
    else:
        # Bukan leader: keluar biasa
        conn.execute("DELETE FROM guild_members WHERE user_id=? AND guild_id=?", (user_id, gid))
        conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return {"ok": True, "msg": "Kamu telah keluar dari guild."}

def accept_leader_transfer(user_id, transfer_id):
    conn = get_conn()
    trans = conn.execute("SELECT * FROM guild_leader_transfers WHERE id=? AND status='pending'", (transfer_id,)).fetchone()
    if not trans:
        conn.close()
        return {"ok": False, "msg": "Transfer tidak valid atau sudah kadaluarsa."}
    member = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (trans["guild_id"], user_id)).fetchone()
    if not member:
        conn.close()
        return {"ok": False, "msg": "Kamu bukan anggota guild ini."}
    conn.execute("UPDATE guilds SET leader_id=? WHERE id=?", (user_id, trans["guild_id"]))
    conn.execute("UPDATE guild_leader_transfers SET status='accepted' WHERE id=?", (transfer_id,))
    conn.commit()
    conn.close()
    add_notification(user_id, f"👑 Kamu sekarang adalah leader guild!", "success")
    return {"ok": True, "msg": "Kamu menjadi leader baru!"}

# ========== KICK FRIEND ==========
def remove_friend(user_id, friend_id):
    conn = get_conn()
    conn.execute("DELETE FROM friends WHERE (user_id=? AND friend_id=?) OR (user_id=? AND friend_id=?)",
                 (user_id, friend_id, friend_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Teman berhasil dihapus."}

# ========== PRIVATE CHAT ==========
def send_message(sender_id, receiver_id, message, created_at=None):
    conn = get_conn()
    if created_at is None:
        created_at = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO messages(sender_id, receiver_id, message, created_at) VALUES(?,?,?,?)",
        (sender_id, receiver_id, message, created_at)
    )
    conn.commit()
    conn.close()
    add_notification(receiver_id, f"💬 Pesan baru dari {get_user(sender_id)['display_name']}", "info")
    return {"ok": True}

def get_messages(user_id, other_id, limit=50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT * FROM messages
        WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?)
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, other_id, other_id, user_id, limit)).fetchall()
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

# ========== GUILD CHAT ==========
def send_guild_message(guild_id, sender_id, message, created_at=None):
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
        add_notification(uid, f"💬 Guild: {sender_name}: {message[:50]}", "info")
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
    conn = get_conn()
    inv = conn.execute("SELECT * FROM guild_invites WHERE id=? AND user_id=? AND status='pending'", (invite_id, user_id)).fetchone()
    if not inv:
        conn.close()
        return {"ok": False, "msg": "Undangan tidak valid."}
    conn.execute("UPDATE guild_invites SET status='accepted' WHERE id=?", (invite_id,))
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (inv["guild_id"], user_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (inv["guild_id"], user_id))
    conn.commit()
    conn.close()
    add_notification(user_id, "✅ Kamu sekarang bergabung ke guild!", "success")
    return {"ok": True, "msg": "Selamat bergabung!"}

def reject_invite(user_id, invite_id):
    conn = get_conn()
    conn.execute("UPDATE guild_invites SET status='rejected' WHERE id=? AND user_id=?", (invite_id, user_id))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Undangan ditolak."}


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
import hashlib

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
    query += " ORDER BY date DESC, created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_economy_item(user_id, name, icon, type_, amount, category, date_str, notes='', folder_id=None):
    """Tambah pemasukan/pengeluaran."""
    conn = get_conn()
    cur = conn.execute("""
        INSERT INTO economy_items(user_id, name, icon, type, amount, category, date, notes, folder_id, updated_at)
        VALUES(?,?,?,?,?,?,?,?,?, datetime('now'))
    """, (user_id, name, icon, type_, amount, category, date_str, notes, folder_id))
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
        return {"ok": False, "msg": "Item tidak ditemukan"}
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
    }


# ===========================================================================================================================#
if __name__ == "__main__":
    init_db()
    print("Database OK!")