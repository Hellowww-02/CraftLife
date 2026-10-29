"""M03 — row-level sync prerequisites (UPDATE_ROADMAP M03, G3 + G4).

M03 adds four columns to every table that participates in personal sync:

``uuid``        stable identity that survives an integer-PK remap on import (G3)
``rev``         per-row revision counter, consumed by M04
``updated_at``  last-write timestamp for row-level LWW, consumed by M04
``deleted_at``  tombstone so a delete can propagate instead of resurrecting (G4)

The columns are read by nothing yet, so the whole milestone must be provably
inert. Three things therefore carry the weight of the acceptance criteria:

* fresh AND legacy databases gain the columns without losing a row;
* uuid is unique and never NULL, and stays put across repeated init_db();
* every M02 test still passes (that is the zero-regression proof, and it lives
  in the suite as a whole rather than in this file).

The SQLite constraints that shaped the implementation are asserted here too, so
a future "simplification" that reintroduces them fails loudly:
``ADD COLUMN ... UNIQUE`` is rejected outright, and ``ADD COLUMN ... DEFAULT
(datetime('now'))`` succeeds on an EMPTY table but fails on one that already has
rows — the exact shape that would pass CI on a fresh database and break on every
user's real one.
"""
from __future__ import annotations

import json
import sqlite3
import unittest

from tests.harness import TempDatabase
from tests.legacy_fixture import build_legacy_db

SYNC_COLUMNS = ("uuid", "rev", "updated_at", "deleted_at")


def columns_of(conn, table):
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}


def uuid_stats(conn, table):
    """(row_count, null_count, distinct_uuid_count) for one table."""
    rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    nulls = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE uuid IS NULL").fetchone()[0]
    distinct = conn.execute(f"SELECT COUNT(DISTINCT uuid) FROM {table}").fetchone()[0]
    return rows, nulls, distinct


class FreshSyncSchemaTest(unittest.TestCase):
    """A brand-new database must come out of init_db() already sync-ready."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)
        self.tables = list(self.db.SYNC_TABLES)

    def test_sync_tables_cover_every_export_table_plus_debt_notes(self):
        """The target list is EXPORT_TABLES + debt_notes, and nothing else."""
        self.assertEqual(set(self.tables), set(self.db.EXPORT_TABLES) | {"debt_notes"})
        self.assertEqual(len(self.tables), 41)

    def test_every_sync_table_has_all_four_columns(self):
        missing = {
            t: [c for c in SYNC_COLUMNS if c not in columns_of(self.conn, t)]
            for t in self.tables
        }
        missing = {t: cols for t, cols in missing.items() if cols}
        self.assertEqual(missing, {})

    def test_no_sync_column_declares_a_non_constant_default(self):
        """Guard the trap that would only fire on a real user's database.

        SQLite accepts ``ALTER TABLE ... ADD COLUMN x TEXT DEFAULT
        (datetime('now'))`` on an EMPTY table and rejects it on one that already
        holds rows ("Cannot add a column with non-constant default"). Since
        _safe_alter swallows the exception, the column would simply not exist on
        every existing installation while a fresh CI database looked fine.
        Asserting it here, at the declaration, is the only place the mistake is
        visible before it ships.
        """
        for column, definition in self.db.SYNC_COLUMNS:
            upper = definition.upper()
            if "DEFAULT" not in upper:
                continue
            tail = upper.split("DEFAULT", 1)[1].strip()
            self.assertNotIn(
                "(",
                tail,
                f"SYNC_COLUMNS {column} uses an expression default {definition!r}; "
                f"ALTER TABLE rejects it on a populated table",
            )

    def test_uuid_is_never_null_and_never_duplicated(self):
        offenders = {}
        total_rows = total_distinct = 0
        for t in self.tables:
            rows, nulls, distinct = uuid_stats(self.conn, t)
            total_rows += rows
            total_distinct += distinct
            if nulls or rows != distinct:
                offenders[t] = (rows, nulls, distinct)
        self.assertEqual(offenders, {})
        self.assertEqual(total_rows, total_distinct)
        # A fresh database seeds food_items; if that ever changes to zero rows
        # this test would be vacuous, so assert the population is real.
        self.assertGreater(total_rows, 0)

    def test_every_uuid_is_a_32_char_lowercase_hex_string(self):
        for t in self.tables:
            bad = self.conn.execute(
                f"SELECT uuid FROM {t} WHERE uuid IS NOT NULL "
                f"AND (length(uuid) <> 32 OR uuid <> lower(uuid) "
                f"OR uuid GLOB '*[^0-9a-f]*')"
            ).fetchall()
            self.assertEqual([r["uuid"] for r in bad], [], f"malformed uuid in {t}")

    def test_unique_indexes_and_triggers_are_installed_for_every_table(self):
        objects = {
            (r["type"], r["name"])
            for r in self.conn.execute("SELECT type, name FROM sqlite_master")
        }
        for t in self.tables:
            self.assertIn(("index", f"idx_{t}_uuid"), objects, f"no unique uuid index on {t}")
            self.assertIn(("trigger", f"trg_{t}_sync_defaults"), objects, f"no trigger on {t}")

    def test_uuid_index_is_actually_unique(self):
        """CREATE UNIQUE INDEX, because ADD COLUMN ... UNIQUE is rejected."""
        sql = self.conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_habits_uuid'"
        ).fetchone()["sql"]
        self.assertIn("UNIQUE", sql.upper())

    def test_a_new_row_receives_uuid_rev_and_updated_at(self):
        uid = self.ctx.make_user("trigger_user")
        self.assertIsNone(self.db.add_habit(uid, "Habit baru"))
        row = self.conn.execute(
            "SELECT uuid, rev, updated_at, deleted_at FROM habits WHERE user_id=?", (uid,)
        ).fetchone()
        self.assertIsNotNone(row["uuid"])
        self.assertEqual(len(row["uuid"]), 32)
        self.assertEqual(row["rev"], 0)
        self.assertIsNotNone(row["updated_at"], "trigger must stamp updated_at")
        self.assertIsNone(row["deleted_at"], "a live row carries no tombstone")

    def test_trigger_does_not_overwrite_a_uuid_the_caller_supplied(self):
        """M04 will insert rows carrying a uuid from another device."""
        uid = self.ctx.make_user("caller_uuid")
        self.conn.execute(
            "INSERT INTO habits(user_id, name, uuid) VALUES(?,?,?)",
            (uid, "Supplied", "a" * 32),
        )
        self.conn.commit()
        got = self.conn.execute(
            "SELECT uuid FROM habits WHERE user_id=?", (uid,)
        ).fetchone()["uuid"]
        self.assertEqual(got, "a" * 32)

    def test_duplicate_uuid_is_rejected(self):
        uid = self.ctx.make_user("dup_user")
        self.conn.execute(
            "INSERT INTO habits(user_id, name, uuid) VALUES(?,?,?)", (uid, "One", "b" * 32)
        )
        self.conn.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO habits(user_id, name, uuid) VALUES(?,?,?)", (uid, "Two", "b" * 32)
            )
        self.conn.rollback()

    def test_recipe_items_gets_uuid_but_no_per_user_indexes(self):
        """recipe_items has no user_id (it is scoped through recipe_id)."""
        self.assertNotIn("user_id", columns_of(self.conn, "recipe_items"))
        names = {
            r["name"]
            for r in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='recipe_items'"
            )
        }
        self.assertIn("idx_recipe_items_uuid", names)
        self.assertNotIn("idx_recipe_items_user_deleted", names)
        self.assertNotIn("idx_recipe_items_user_updated", names)

    def test_tables_with_user_id_get_both_companion_indexes(self):
        for t in self.tables:
            if "user_id" not in columns_of(self.conn, t):
                continue
            names = {
                r["name"]
                for r in self.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?", (t,)
                )
            }
            self.assertIn(f"idx_{t}_user_deleted", names, t)
            self.assertIn(f"idx_{t}_user_updated", names, t)

    def test_updated_at_is_populated_for_every_existing_row(self):
        """Row-level LWW has nothing to compare if this is NULL."""
        for t in self.tables:
            nulls = self.conn.execute(
                f"SELECT COUNT(*) FROM {t} WHERE updated_at IS NULL"
            ).fetchone()[0]
            self.assertEqual(nulls, 0, f"{t} has {nulls} rows with NULL updated_at")

    def test_integer_primary_keys_are_untouched(self):
        """P4: uuid is a companion column, never a replacement for the PK."""
        uid = self.ctx.make_user("pk_user")
        self.db.add_habit(uid, "Habit PK")
        before = {
            r["id"]: r["name"] for r in self.conn.execute("SELECT id, name FROM habits")
        }
        self.db.init_db()
        after = {
            r["id"]: r["name"] for r in self.conn.execute("SELECT id, name FROM habits")
        }
        self.assertEqual(before, after)

    def test_repeated_init_db_keeps_uuids_stable(self):
        """The backfill must be a no-op once every row has a uuid."""
        tables = ("habits", "food_items", "dailies", "todos")
        probe = "SELECT GROUP_CONCAT(uuid) FROM (SELECT uuid FROM {} ORDER BY id)"
        first = {t: self.conn.execute(probe.format(t)).fetchone()[0] for t in tables}
        self.db.init_db()
        self.db.init_db()
        second = {t: self.conn.execute(probe.format(t)).fetchone()[0] for t in tables}
        self.assertEqual(first, second)
        self.assertEqual(self.ctx.integrity_check(), "ok")
        self.assertEqual(self.ctx.foreign_key_violations(), [])

    def test_users_is_deliberately_outside_the_sync_set(self):
        """Progression is server-authoritative, so `users` is not row-synced.

        Pinned so that adding it later is a conscious decision rather than an
        accident of editing a list.
        """
        self.assertNotIn("users", self.db.SYNC_TABLES)
        self.assertNotIn("uuid", columns_of(self.conn, "users"))


class LegacySyncMigrationTest(unittest.TestCase):
    """The columns must appear on a real old database without losing rows."""

    def setUp(self):
        self._fixture = TempDatabase()
        fixture = self._fixture.__enter__()
        self.addCleanup(self._fixture.__exit__, None, None, None)
        self.seed_counts = build_legacy_db(fixture.db_path)

        self._ctx = TempDatabase(seed_from=fixture.db_path)
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)

    def _migrate(self):
        self.db.init_db()

    def test_fixture_starts_without_any_sync_column(self):
        """If the fixture already had them, this whole class proves nothing."""
        tables = list(self.db.SYNC_TABLES)
        for t in ("habits", "dailies", "todos"):
            present = columns_of(self.conn, t)
            self.assertNotIn("uuid", present, f"{t} already has uuid — fixture is not legacy")
            self.assertNotIn("rev", present, t)
            self.assertNotIn("deleted_at", present, t)
        self.assertTrue(tables)

    def test_migration_adds_the_columns_to_a_populated_database(self):
        """The case a fresh database cannot exercise: tables that already hold rows."""
        self._migrate()
        missing = {
            t: [c for c in SYNC_COLUMNS if c not in columns_of(self.conn, t)]
            for t in self.db.SYNC_TABLES
        }
        self.assertEqual({t: c for t, c in missing.items() if c}, {})

    def test_legacy_rows_survive_the_migration(self):
        self._migrate()
        for table, before in self.seed_counts.items():
            self.assertEqual(
                self.ctx.count(table), before, f"{table} lost rows during migration"
            )

    def test_legacy_progression_values_are_unchanged(self):
        row = self.conn.execute(
            "SELECT level, xp, gold FROM users WHERE username='legacy_hero'"
        ).fetchone()
        before = tuple(row)
        self._migrate()
        after = tuple(
            self.conn.execute(
                "SELECT level, xp, gold FROM users WHERE username='legacy_hero'"
            ).fetchone()
        )
        self.assertEqual(before, after)

    def test_legacy_rows_receive_unique_uuids(self):
        self._migrate()
        synced = set(self.db.SYNC_TABLES)
        checked = 0
        for t, before in self.seed_counts.items():
            if t not in synced:
                # `users` is row-synced by no one (progression is
                # server-authoritative), so it legitimately has no uuid.
                continue
            rows, nulls, distinct = uuid_stats(self.conn, t)
            self.assertEqual(rows, before, t)
            self.assertEqual(nulls, 0, f"{t} left {nulls} rows without a uuid")
            self.assertEqual(distinct, rows, f"{t} has duplicate uuids")
            checked += 1
        self.assertGreater(checked, 0, "the fixture seeded no sync-covered table")

    def test_migration_is_repeatable_without_error(self):
        self._migrate()
        self._migrate()
        self._migrate()
        self.assertEqual(self.ctx.integrity_check(), "ok")
        self.assertEqual(self.ctx.foreign_key_violations(), [])


class CloudCompatibilityGuardTest(unittest.TestCase):
    """G10 is deliberately still open, and these tests pin why.

    Adding ``debt_notes`` to EXPORT_TABLES looks like a one-line fix but was
    measured to break cloud sync in both directions:

    * ``_sanitize_cloud_personal_snapshot`` demands the table set match
      EXPORT_TABLES exactly, so a pre-M03 cloud document (40 tables) is rejected
      with ``ValueError: incomplete cloud tracker snapshot: debt_notes`` —
      restore-from-cloud dies for every existing user (P4/P6);
    * relaxing that guard to "missing table means empty" is worse, because
      ``import_tracker_data`` clears local tracker tables first, so an empty
      list would silently delete every local debt_note.

    Closing G10 properly needs per-table preservation on the import path plus
    ``cloud_schema`` versioning, which is M04 work. These tests keep the gap
    visible instead of letting it reopen quietly.
    """

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("cloud_user")
        self.db.add_habit(self.uid, "Synced habit")

    def test_export_tables_is_still_forty_and_excludes_debt_notes(self):
        self.assertEqual(len(self.db.EXPORT_TABLES), 40)
        self.assertNotIn("debt_notes", self.db.EXPORT_TABLES)
        self.assertIn("debts", self.db.EXPORT_TABLES)

    def test_debt_notes_still_gets_the_sync_columns(self):
        """Deferred from the export, not skipped: the prerequisite is in place."""
        conn = self.ctx.raw()
        try:
            self.assertEqual(
                [c for c in SYNC_COLUMNS if c not in columns_of(conn, "debt_notes")], []
            )
        finally:
            conn.close()

    def test_snapshot_does_not_carry_debt_notes(self):
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        self.assertEqual(len(snapshot["tables"]), 40)
        self.assertNotIn("debt_notes", snapshot["tables"])

    def test_snapshot_round_trips_through_the_sanitizer(self):
        """A pre-M03 document must still be acceptable to a post-M03 client."""
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        cleaned = self.db._sanitize_cloud_personal_snapshot(json.loads(json.dumps(snapshot)))
        self.assertEqual(set(cleaned["tables"]), set(self.db.EXPORT_TABLES))

    def test_sync_columns_do_travel_inside_existing_tables(self):
        """The columns ride along on the 40 tables, so M04 has them available."""
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        habit = snapshot["tables"]["habits"][0]
        for column in SYNC_COLUMNS:
            self.assertIn(column, habit)


if __name__ == "__main__":
    unittest.main()
