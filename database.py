"""
CraftLife — database.py  v2.1  (fixed & complete)
Works both in VSCode and as PyInstaller .exe
"""
import sqlite3, hashlib, os, sys
from datetime import datetime, date

# ── Path auto-detect (VSCode + .exe) ─────────────────────────────────────────
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "craftlife.db")


def get_conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    c.execute("PRAGMA journal_mode = WAL")
    return c


def _safe_alter(cur, table, col, defn):
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
    except Exception:
        pass

def migrate_party_to_guild():
    conn = get_conn()
    c = conn.cursor()
    # 1. Rename tabel
    try: c.execute("ALTER TABLE parties RENAME TO guilds")
    except: pass
    try: c.execute("ALTER TABLE party_members RENAME TO guild_members")
    except: pass
    try: c.execute("ALTER TABLE boss_battles RENAME COLUMN party_id TO guild_id")
    except: pass
    try: c.execute("ALTER TABLE users RENAME COLUMN party_id TO guild_id")
    except: pass
    try:
        c.execute("ALTER TABLE guild_members RENAME COLUMN party_id TO guild_id")
    except Exception:
        pass

    # 2. Tambah kolom untuk guild level
    for col, defn in [("level", "INTEGER DEFAULT 1"),
                      ("exp", "INTEGER DEFAULT 0"),
                      ("buff_xp", "REAL DEFAULT 0"),
                      ("buff_gold", "REAL DEFAULT 0"),
                      ("buff_damage", "REAL DEFAULT 0")]:
        try: c.execute(f"ALTER TABLE guilds ADD COLUMN {col} {defn}")
        except: pass

    # Tambah kolom untuk user_pets jika belum ada
    for col, defn in [("level", "INTEGER DEFAULT 1"),
                    ("exp", "INTEGER DEFAULT 0"),
                    ("hunger", "INTEGER DEFAULT 100"),
                    ("last_fed", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE user_pets ADD COLUMN {col} {defn}")
        except Exception:
            pass

    # 3. Buat tabel guild_invites jika belum
    c.execute("""CREATE TABLE IF NOT EXISTS guild_invites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(guild_id) REFERENCES guilds(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

def init_db():
    conn = get_conn()
    c = conn.cursor()

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
        party_id INTEGER,
        last_login TEXT,
        theme TEXT DEFAULT 'overworld',
        sound_enabled INTEGER DEFAULT 1,
        created_at TEXT DEFAULT(datetime('now'))
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

    c.execute("""CREATE TABLE IF NOT EXISTS parties(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        leader_id INTEGER,
        quest_id TEXT,
        created_at TEXT DEFAULT(datetime('now'))
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS party_members(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id INTEGER,
        user_id INTEGER,
        joined_at TEXT DEFAULT(datetime('now')),
        FOREIGN KEY(party_id) REFERENCES parties(id),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS boss_battles(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        party_id INTEGER,
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
        FOREIGN KEY(party_id) REFERENCES parties(id)
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

    # Safe migration for older databases
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
    ]
    for col, defn in migrate_cols:
        _safe_alter(c, "users", col, defn)

    conn.commit()
    conn.close()
    # Panggil migrasi di akhir (sebelum print)
    migrate_party_to_guild()   # fungsi baru
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
                     (datetime.now().isoformat(), row["id"]))
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


def update_user(user_id, **kw):
    if not kw:
        return
    fields = ", ".join(f"{k}=?" for k in kw)
    conn = get_conn()
    conn.execute(f"UPDATE users SET {fields} WHERE id=?",
                 list(kw.values()) + [user_id])
    conn.commit()
    conn.close()


def recalculate_all_buffs(user_id):
    # 1. Hitung buff dari item
    inv = get_inventory(user_id)
    owned = {i["item_id"] for i in inv}
    dmg = 0.0; xp_pct = 0.0; gold_pct = 0.0; reduc = 0.0; mp = 0; revive = 0
    for iid in owned:
        b = SHOP_ITEMS.get(iid, {}).get("buff", {})
        dmg      += b.get("boss_dmg", 0)
        xp_pct   += b.get("xp_pct",  0) / 100
        gold_pct += b.get("gold_pct", 0) / 100
        reduc    += b.get("hp_reduc", 0)
        mp       += b.get("mp_bonus", 0)
        if b.get("revive"):
            revive = 1

    # 2. Tambah buff dari pet aktif
    conn = get_conn()
    active_pet = conn.execute("SELECT * FROM user_pets WHERE user_id=? AND is_active=1", (user_id,)).fetchone()
    if active_pet:
        pid = active_pet["pet_id"]
        base = PETS_DATA.get(pid, {}).get("base_buff", {})
        level = active_pet["level"]
        scale = 1 + (level-1) * 0.02   # +2% per level
        xp_pct   += base.get("xp_pct", 0) * scale / 100
        gold_pct += base.get("gold_pct", 0) * scale / 100
        dmg      += base.get("boss_dmg", 0) * scale
        reduc    += base.get("hp_reduc", 0) * scale

    # 3. Tambah buff dari guild
    u = get_user(user_id)
    gid = u.get("guild_id")
    if gid:
        guild = conn.execute("SELECT buff_xp, buff_gold, buff_damage FROM guilds WHERE id=?", (gid,)).fetchone()
        if guild:
            xp_pct   += guild["buff_xp"] / 100
            gold_pct += guild["buff_gold"] / 100
            dmg      += guild["buff_damage"]
    conn.close()

    update_user(user_id,
                boss_damage_bonus=dmg,
                xp_multiplier=round(1.0 + xp_pct, 4),
                gold_multiplier=round(1.0 + gold_pct, 4),
                hp_damage_reduction=reduc,
                mp_bonus=mp,
                has_revive=revive)


# ── XP / Gold / HP ────────────────────────────────────────────────────────────

def gain_xp_gold(user_id, xp_base, gold_base):
    u = get_user(user_id)
    xp   = int(xp_base  * u.get("xp_multiplier",  1.0))
    gold = gold_base * u.get("gold_multiplier", 1.0)
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
        update_user(user_id, max_hp=mhp, hp=mhp, max_mp=mmp, mp=mmp)
        add_notification(user_id, f"🎉 Level Up! Kamu sekarang Level {new_lvl}!", "levelup")
        needed = new_lvl * 150
    update_user(user_id,
                xp=new_xp, level=new_lvl, gold=new_gold,
                total_xp_earned=u.get("total_xp_earned", 0) + xp,
                total_gold_earned=u.get("total_gold_earned", 0.0) + gold)
    # Catat aktivitas (PASTIKAN SELALU DIPANGGIL)
    log_activity(user_id, "reward", f"+{xp} XP, +{gold:.1f} Gold", xp, gold)
    # Jika user punya guild, tambahkan EXP guild
    u2 = get_user(user_id)
    if u2.get("guild_id"):
        add_guild_exp(u2["guild_id"], xp_base // 5)
    # SELALU RETURN dictionary
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
    cls   = u.get("avatar_class", "warrior")
    skill = CLASS_SKILLS.get(cls, {})
    cost  = skill.get("mp_cost", 10)
    if u["mp"] < cost:
        return {"ok": False,
                "msg": f"MP tidak cukup! Butuh {cost} MP, kamu punya {u['mp']} MP."}
    update_user(user_id, mp=u["mp"] - cost)
    if cls == "healer":
        new_hp = min(u["max_hp"], u["hp"] + 30)
        update_user(user_id, hp=new_hp)
        return {"ok": True, "msg": "💚 Regenerate! +30 HP dipulihkan."}
    msgs = {
        "warrior": "🛡️ Shield Bash aktif! Damage boss -50% satu kali.",
        "mage":    "✨ Arcane Surge! +50% XP untuk 3 habit berikutnya.",
        "archer":  "🏹 Gold Shot! +100% Gold dari habit berikutnya.",
        "rogue":   "🗡️ Shadow Step! Double streak daily berikutnya.",
    }
    msg = msgs.get(cls, "Skill digunakan!")
    add_notification(user_id, msg, "info")
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


def complete_habit(user_id, habit_id, direction="up"):
    conn = get_conn()
    h = conn.execute("SELECT * FROM habits WHERE id=? AND user_id=?", (habit_id, user_id)).fetchone()
    if not h:
        conn.close()
        return {"ok": False}
    today = date.today().isoformat()
    # Jika sudah done_today, tolak action apa pun (baik up maupun down)
    if h["done_today"]:
        conn.close()
        return {"ok": False, "msg": "Kamu sudah melakukan action untuk habit ini hari ini!"}
    new_streak = h["streak"] + 1 if direction == "up" else 0
    conn.execute("UPDATE habits SET done_today=1, streak=?, last_done=?, counter_up=counter_up+?, counter_down=counter_down+? WHERE id=?",
                 (new_streak, today, 1 if direction=="up" else 0, 1 if direction=="down" else 0, habit_id))
    conn.execute("UPDATE users SET total_habits_done=total_habits_done+1 WHERE id=?", (user_id,))
    conn.commit()
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
    conn = get_conn()
    g = conn.execute("SELECT * FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not g:
        conn.close()
        return
    new_exp = g["exp"] + amount
    new_level = g["level"]
    needed = new_level * 500
    leveled = False
    while new_exp >= needed:
        new_exp -= needed
        new_level += 1
        leveled = True
        needed = new_level * 500
    if leveled:
        buff_xp = new_level * 2
        buff_gold = new_level * 1
        buff_damage = new_level * 1
        conn.execute("UPDATE guilds SET level=?, exp=?, buff_xp=?, buff_gold=?, buff_damage=? WHERE id=?", 
                     (new_level, new_exp, buff_xp, buff_gold, buff_damage, guild_id))
        members = conn.execute("SELECT user_id FROM guild_members WHERE guild_id=?", (guild_id,)).fetchall()
        for m in members:
            add_notification(m["user_id"], f"🏆 Guild {g['name']} naik level {new_level}!", "levelup")
            recalculate_all_buffs(m["user_id"])
    else:
        conn.execute("UPDATE guilds SET exp=? WHERE id=?", (new_exp, guild_id))
    conn.commit()
    conn.close()

def delete_habit(user_id, habit_id):
    conn = get_conn()
    conn.execute("DELETE FROM habits WHERE id=? AND user_id=?",
                 (habit_id, user_id))
    conn.commit()
    conn.close()


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


def complete_daily(user_id, daily_id):
    conn = get_conn()
    d = conn.execute(
        "SELECT * FROM dailies WHERE id=? AND user_id=?",
        (daily_id, user_id)).fetchone()
    if not d or d["done_today"]:
        conn.close()
        return {"ok": False, "msg": "Sudah selesai!"}
    today = date.today().isoformat()
    conn.execute(
        "UPDATE dailies SET done_today=1,streak=streak+1,last_done=? WHERE id=?",
        (today, daily_id))
    conn.execute(
        "UPDATE users SET total_dailies_done=total_dailies_done+1 WHERE id=?",
        (user_id,))
    conn.commit()
    conn.close()
    restore_mp(user_id, 5)
    return gain_xp_gold(user_id, d["xp_reward"], d["gold_reward"])

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


def complete_todo(user_id, todo_id):
    conn = get_conn()
    t = conn.execute(
        "SELECT * FROM todos WHERE id=? AND user_id=?",
        (todo_id, user_id)).fetchone()
    if not t or t["done"]:
        conn.close()
        return {"ok": False}
    conn.execute("UPDATE todos SET done=1 WHERE id=?", (todo_id,))
    conn.execute(
        "UPDATE users SET total_todos_done=total_todos_done+1 WHERE id=?",
        (user_id,))
    conn.commit()
    conn.close()
    restore_mp(user_id, 4)
    return gain_xp_gold(user_id, t["xp_reward"], t["gold_reward"])

def delete_todo(user_id, todo_id):
    conn = get_conn()
    conn.execute("DELETE FROM todos WHERE id=? AND user_id=?",
                 (todo_id, user_id))
    conn.commit()
    conn.close()


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
    "wolf":     {"name": "Wolf",     "icon": "🐺", "cost": 80,
                 "bonus": "+5 XP per habit"},
    "cat":      {"name": "Cat",      "icon": "🐱", "cost": 60,
                 "bonus": "-10% HP loss"},
    "parrot":   {"name": "Parrot",   "icon": "🦜", "cost": 70,
                 "bonus": "+3 Gold per task"},
    "panda":    {"name": "Panda",    "icon": "🐼", "cost": 120,
                 "bonus": "+15 XP per daily"},
    "fox":      {"name": "Fox",      "icon": "🦊", "cost": 90,
                 "bonus": "+8% Gold bonus"},
    "bee":      {"name": "Bee",      "icon": "🐝", "cost": 55,
                 "bonus": "Honey restores HP"},
    "dragon":   {"name": "Dragon",   "icon": "🐉", "cost": 300,
                 "bonus": "+25 XP on all tasks"},
    "turtle":   {"name": "Turtle",   "icon": "🐢", "cost": 65,
                 "bonus": "+2 HP per day"},
    "axolotl":  {"name": "Axolotl",  "icon": "🦎", "cost": 100,
                 "bonus": "+5 HP regeneration"},
    "enderman": {"name": "Enderman", "icon": "👾", "cost": 200,
                 "bonus": "+20% XP rare bonus"},
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

def feed_pet(user_id, pet_id):
    pet = get_user_pet_by_id(user_id, pet_id)  # kita buat fungsi helper, atau query langsung
    if not pet:
        return {"ok": False, "msg": "Pet tidak ditemukan!"}
    u = get_user(user_id)
    cost = 10  # biaya makan 10 gold
    if u["gold"] < cost:
        return {"ok": False, "msg": f"Gold tidak cukup! Butuh {cost} G untuk memberi makan."}
    new_hunger = min(100, pet["hunger"] + 30)
    exp_gain = 0
    conn = get_conn()
    conn.execute("UPDATE user_pets SET hunger=?, last_fed=? WHERE id=?", (new_hunger, datetime.now().isoformat(), pet["id"]))
    add_pet_exp(conn, pet["id"], exp_gain)
    conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
    conn.commit()
    conn.close()
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": f"🍖 {PETS_DATA[pet_id]['name']} kenyang! +{exp_gain} EXP pet. ({cost} G)"}

def train_pet(user_id, pet_id):
    pet = get_user_pet_by_id(user_id, pet_id)
    if not pet:
        return {"ok": False, "msg": "Pet tidak ditemukan!"}
    if pet["hunger"] < 20:
        return {"ok": False, "msg": "Pet lapar! Beri makan dulu."}
    u = get_user(user_id)
    cost = 5  # biaya latih 5 gold
    if u["gold"] < cost:
        return {"ok": False, "msg": f"Gold tidak cukup! Butuh {cost} G untuk latih."}
    new_hunger = max(0, pet["hunger"] - 20)
    exp_gain = 15
    conn = get_conn()
    conn.execute("UPDATE user_pets SET hunger=? WHERE id=?", (new_hunger, pet["id"]))
    add_pet_exp(conn, pet["id"], exp_gain)
    conn.execute("UPDATE users SET gold=gold-? WHERE id=?", (cost, user_id))
    conn.commit()
    conn.close()
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": f"🏋️ {PETS_DATA[pet_id]['name']} latihan! +{exp_gain} EXP pet. ({cost} G)"}

def add_pet_exp(conn, pet_row_id, amount):
    pet = conn.execute("SELECT * FROM user_pets WHERE id=?", (pet_row_id,)).fetchone()
    new_exp = pet["exp"] + amount
    new_level = pet["level"]
    needed = pet["level"] * 100
    while new_exp >= needed:
        new_exp -= needed
        new_level += 1
        needed = new_level * 100
    conn.execute("UPDATE user_pets SET exp=?, level=? WHERE id=?", (new_exp, new_level, pet_row_id))

def get_user_pet_by_id(user_id, pet_id):
    conn = get_conn()
    pet = conn.execute("SELECT * FROM user_pets WHERE user_id=? AND pet_id=?", (user_id, pet_id)).fetchone()
    conn.close()
    return pet

# ── Party / Boss ──────────────────────────────────────────────────────────────

def create_guild(leader_id, name, description=""):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO guilds(name,description,leader_id) VALUES(?,?,?)",
        (name, description, leader_id))
    gid = cur.lastrowid
    conn.execute(
        "INSERT INTO guild_members(guild_id,user_id) VALUES(?,?)",
        (gid, leader_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (gid, leader_id))
    conn.commit()
    conn.close()
    return {"ok": True, "guild_id": gid,
            "msg": f"Guild '{name}' dibuat! ID: {gid}"}


def join_guild(user_id, guild_id):
    conn = get_conn()
    g = conn.execute("SELECT * FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not g:
        conn.close()
        return {"ok": False, "msg": "Guild tidak ditemukan!"}
    # Cek apakah sudah menjadi member
    existing = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, user_id)).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "msg": "Kamu sudah menjadi anggota guild ini!"}
    conn.execute("INSERT INTO guild_members(guild_id, user_id) VALUES(?,?)", (guild_id, user_id))
    conn.execute("UPDATE users SET guild_id=? WHERE id=?", (guild_id, user_id))
    conn.commit()
    conn.close()
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": f"Berhasil bergabung ke {g['name']}!"}


def leave_guild(user_id):
    u = get_user(user_id)
    gid = u.get("guild_id")
    if not gid:
        return {"ok": False, "msg": "Kamu tidak di dalam guild."}
    conn = get_conn()
    conn.execute(
        "DELETE FROM guild_members WHERE user_id=? AND guild_id=?",
        (user_id, gid))
    conn.execute("UPDATE users SET guild_id=NULL WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"ok": True, "msg": "Kamu telah keluar dari guild."}


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

def send_invite(guild_id, leader_id, target_username):
    conn = get_conn()
    guild = conn.execute("SELECT leader_id, name FROM guilds WHERE id=?", (guild_id,)).fetchone()
    if not guild or guild["leader_id"] != leader_id:
        conn.close()
        return {"ok": False, "msg": "Hanya leader yang bisa mengundang!"}
    target = conn.execute("SELECT id FROM users WHERE username=?", (target_username.lower(),)).fetchone()
    if not target:
        conn.close()
        return {"ok": False, "msg": "User tidak ditemukan!"}
    if target["id"] == leader_id:
        conn.close()
        return {"ok": False, "msg": "Tidak bisa mengundang diri sendiri!"}
    existing = conn.execute("SELECT 1 FROM guild_members WHERE guild_id=? AND user_id=?", (guild_id, target["id"])).fetchone()
    if existing:
        conn.close()
        return {"ok": False, "msg": "User sudah menjadi anggota!"}
    pending = conn.execute("SELECT 1 FROM guild_invites WHERE guild_id=? AND user_id=? AND status='pending'", (guild_id, target["id"])).fetchone()
    if pending:
        conn.close()
        return {"ok": False, "msg": "Undangan sudah terkirim!"}
    conn.execute("INSERT INTO guild_invites(guild_id, user_id) VALUES(?,?)", (guild_id, target["id"]))
    conn.commit()
    conn.close()
    add_notification(target["id"], f"📩 Kamu diundang ke guild '{guild['name']}' oleh leader. Cek menu Guild.", "info")
    return {"ok": True, "msg": f"Undangan dikirim ke {target_username}!"}

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


def attack_boss(user_id, guild_id, base_damage=25):
    u = get_user(user_id)
    # ── FIX: Hard HP check ────────────────────────────────────────────────────
    if u["hp"] <= 0:
        return {
            "ok": False,
            "msg": ("❌ HP kamu 0! Tidak bisa menyerang.\n"
                    "Gunakan Golden Apple di Shop atau skill Healer."),
        }
    conn = get_conn()
    boss = conn.execute(
        "SELECT * FROM boss_battles WHERE guild_id=? AND status='active'",
        (guild_id,)).fetchone()
    if not boss:
        conn.close()
        return {"ok": False, "msg": "Tidak ada boss aktif!"}

    total_dmg = base_damage + u.get("boss_damage_bonus", 0)
    new_hp    = max(0.0, boss["boss_hp"] - total_dmg)

    if new_hp <= 0:
        conn.execute(
            "UPDATE boss_battles SET boss_hp=0,status='defeated',"
            "ended_at=? WHERE id=?",
            (datetime.now().isoformat(), boss["id"]))
        bdata = BOSSES.get(boss["boss_id"], {})
        members = conn.execute(
            "SELECT user_id FROM guild_members WHERE guild_id=?",
            (guild_id,)).fetchall()
        cnt = max(1, len(members))
        conn.commit()
        conn.close()
        for m in members:
            gain_xp_gold(m["user_id"],
                         bdata.get("xp", 200) // cnt,
                         bdata.get("gold", 50) // cnt)
            add_notification(
                m["user_id"],
                f"🏆 {boss['boss_name']} dikalahkan! Reward dibagi!",
                "success")
        return {"ok": True, "defeated": True, "total_dmg": total_dmg,
                "msg": (f"🏆 {boss['boss_name']} dikalahkan!\n"
                        f"+{bdata.get('xp',200)//cnt} XP, "
                        f"+{bdata.get('gold',50)//cnt} Gold!")}
    conn.execute("UPDATE boss_battles SET boss_hp=? WHERE id=?",
                 (new_hp, boss["id"]))
    conn.commit()
    conn.close()
    lr = lose_hp(user_id, boss["boss_attack"])
    return {"ok": True, "defeated": False, "remaining_hp": new_hp,
            "boss_max_hp": boss["boss_max_hp"], "total_dmg": total_dmg,
            "hp_lost": boss["boss_attack"],
            "revived": lr.get("revived", False)}


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


# ── Notifications ─────────────────────────────────────────────────────────────

def add_notification(user_id, message, type_="info"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO notifications(user_id,message,type) VALUES(?,?,?)",
        (user_id, message, type_))
    conn.commit()
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
    recalculate_all_buffs(user_id)
    return {"ok": True, "msg": f"Class berhasil diubah menjadi {AVATAR_CLASSES[new_class]['name']}!"}

def set_user_settings(user_id, sound_enabled=None):
    kw = {}
    if sound_enabled is not None:
        kw["sound_enabled"] = int(sound_enabled)
    if kw:
        update_user(user_id, **kw)


if __name__ == "__main__":
    init_db()
    print("Database OK!")