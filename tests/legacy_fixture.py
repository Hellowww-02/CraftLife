"""Builds a LEGACY CraftLife database from the real historical schema (M02).

Why this exists
---------------
UPDATE_RULES.md §6 requires schema changes to be verified against a legacy
database, and §9 forbids committing real user databases. So this module
*reconstructs* an old schema instead of shipping a file.

The DDL below is NOT invented. It is copied verbatim from the oldest
``database.py`` in this repository's history:

    commit be3e2f6  (2026-05-12)

That makes the fixture a real shipped shape rather than a guess, which matters:
a hand-made "old" table can easily describe a state that never existed, and
then the test proves nothing. Two consequences of using the real history:

* ``notes`` did not exist at all in be3e2f6 — so a genuine legacy database
  gets it created fresh, complete with every current column.
* ``users`` had ``party_id`` and no ``guild_id``, and ``theme`` defaulted to
  ``'overworld'`` rather than today's ``'modern_dark'``.
* ``todos`` used ``name``; today's schema uses ``title``.

Columns that later versions added via ``_safe_alter`` (``database.py:176``) are
deliberately absent — repairing them is exactly what init_db() must do.

For a real archive rather than a reconstruction, use ``CRAFTLIFE_LEGACY_DB``.
See tests/test_database_legacy.py.
"""
from __future__ import annotations

import sqlite3

# ---------------------------------------------------------------------------
# Schema of commit be3e2f6, verbatim (CRLF stripped).
# ---------------------------------------------------------------------------

_LEGACY_USERS = """
CREATE TABLE users(
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
)
"""

_LEGACY_HABITS = """
CREATE TABLE habits(
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
)
"""

_LEGACY_DAILIES = """
CREATE TABLE dailies(
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
)
"""

_LEGACY_TODOS = """
CREATE TABLE todos(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '✅',
    priority TEXT DEFAULT 'medium',
    xp_reward INTEGER DEFAULT 20,
    gold_reward REAL DEFAULT 4,
    done INTEGER DEFAULT 0,
    due_date TEXT,
    notes TEXT DEFAULT '',
    created_at TEXT DEFAULT(datetime('now')),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
)
"""

_STATEMENTS = [_LEGACY_USERS, _LEGACY_HABITS, _LEGACY_DAILIES, _LEGACY_TODOS]

SEEDED_TABLES = ("users", "habits", "dailies", "todos")


def build_legacy_db(path: str) -> dict[str, int]:
    """Create a be3e2f6-shaped database at ``path`` with real user rows.

    Returns {table: row_count} so the caller can assert preservation (P6).
    """
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        for ddl in _STATEMENTS:
            conn.execute(ddl)

        conn.execute(
            "INSERT INTO users(username, password_hash, display_name, level, xp, "
            "gold, gems, hp, max_hp, mp, max_mp, theme, sound_enabled) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("legacy_hero", "pbkdf2:sha256:600000$legacy$ffffffffffffffff",
             "Hero Lama", 7, 3400, 1250.5, 42, 50, 50, 30, 30, "overworld", 1),
        )
        conn.execute(
            "INSERT INTO users(username, password_hash, display_name, level, xp, "
            "gold, gems) VALUES(?,?,?,?,?,?,?)",
            ("legacy_friend", "pbkdf2:sha256:600000$legacy$eeeeeeeeeeeeeeee",
             "Teman Lama", 3, 900, 20.0, 10),
        )

        conn.execute(
            "INSERT INTO habits(user_id, name, icon, difficulty, xp_reward, "
            "gold_reward, streak, done_today) VALUES(?,?,?,?,?,?,?,?)",
            (1, "Legacy morning run", "🏃", "hard", 40, 8.0, 63, 1),
        )
        conn.execute(
            "INSERT INTO habits(user_id, name, streak, done_today) VALUES(?,?,?,?)",
            (1, "Legacy reading", 12, 0),
        )

        conn.execute(
            "INSERT INTO dailies(user_id, name, streak, done_today) VALUES(?,?,?,?)",
            (1, "Legacy daily stretch", 5, 1),
        )
        conn.execute(
            "INSERT INTO todos(user_id, name, priority, done) VALUES(?,?,?,?)",
            (1, "Legacy errand", "high", 0),
        )

        conn.commit()
        return {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in SEEDED_TABLES
        }
    finally:
        conn.close()


def column_map(path: str) -> dict[str, set[str]]:
    """{table: {column, …}} for every user table in the database."""
    conn = sqlite3.connect(path)
    try:
        result: dict[str, set[str]] = {}
        for (table,) in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall():
            result[table] = {c[1] for c in conn.execute(f"PRAGMA table_info({table})")}
        return result
    finally:
        conn.close()


def column_gap(path: str, fresh_columns: dict[str, set[str]]) -> dict[str, list[str]]:
    """{table: [columns a fresh db has but this one lacks]}.

    Self-maintaining: it derives the expectation from a freshly built database,
    so nobody has to keep a hardcoded column list in step with the schema.
    """
    have = column_map(path)
    gap: dict[str, list[str]] = {}
    for table, cols in fresh_columns.items():
        if table not in have:
            gap[table] = sorted(cols)
            continue
        missing = sorted(cols - have[table])
        if missing:
            gap[table] = missing
    return gap
