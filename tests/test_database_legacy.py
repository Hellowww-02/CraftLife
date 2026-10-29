"""Legacy-database migration harness (UPDATE_RULES.md §6, UPDATE_ROADMAP M02).

Two harnesses live here:

``SyntheticLegacyMigrationTest``
    Always runs, including in CI. Reconstructs the schema of the oldest
    ``database.py`` in this repository (commit be3e2f6, 2026-05-12) and proves
    that init_db() brings it to the current schema without losing rows.
    See tests/legacy_fixture.py.

``LegacyMigrationTest``
    Runs only when a real archive is supplied via ``CRAFTLIFE_LEGACY_DB``.
    A real fixture is never committed (UPDATE_RULES.md §9: no user databases in
    git). Without one it SKIPS LOUDLY so the gap stays visible in CI output
    instead of looking green.

The core assertion is self-maintaining: the expectation is a freshly built
database, so no hardcoded column list has to be kept in step with the schema.
"""
from __future__ import annotations

import os
import unittest

from tests.harness import TempDatabase
from tests.legacy_fixture import build_legacy_db, column_gap, column_map

LEGACY_DB = os.environ.get("CRAFTLIFE_LEGACY_DB", "").strip()
HAS_FIXTURE = bool(LEGACY_DB and os.path.isfile(LEGACY_DB))


@unittest.skipUnless(
    HAS_FIXTURE,
    "no legacy database supplied — set CRAFTLIFE_LEGACY_DB=/path/to/craftlife.db "
    "to exercise a REAL archive as required by UPDATE_RULES.md §6",
)
class LegacyMigrationTest(unittest.TestCase):
    """The real-archive harness. Complements the synthetic one; never a substitute."""

    @classmethod
    def setUpClass(cls):
        cls._fresh_ctx = TempDatabase()
        fresh = cls._fresh_ctx.__enter__()
        fresh.db.init_db()
        cls.fresh_schema = column_map(fresh.db_path)
        cls._fresh_ctx.__exit__(None, None, None)

    def setUp(self):
        self._ctx = TempDatabase(seed_from=LEGACY_DB)
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.before_counts = {t: self.ctx.count(t) for t in self.ctx.table_names()}

    def test_init_db_completes_on_legacy_database(self):
        self.db.init_db()
        self.assertEqual(self.ctx.integrity_check(), "ok")

    def test_init_db_is_idempotent_on_legacy_database(self):
        self.db.init_db()
        first = column_map(self.ctx.db_path)
        self.db.init_db()
        self.assertEqual(column_map(self.ctx.db_path), first)
        self.assertEqual(self.ctx.integrity_check(), "ok")
        self.assertEqual(self.ctx.foreign_key_violations(), [])

    def test_legacy_schema_gains_every_current_column(self):
        """§6: an old database must end up matching a new one."""
        self.db.init_db()
        self.assertEqual(
            column_gap(self.ctx.db_path, self.fresh_schema),
            {},
            "legacy database did not reach the current schema; a _safe_alter is "
            "missing or runs before the table it patches exists",
        )

    def test_existing_rows_are_preserved(self):
        """P6 — never lose user data."""
        self.db.init_db()
        for table, before in self.before_counts.items():
            with self.subTest(table=table):
                self.assertGreaterEqual(
                    self.ctx.count(table), before,
                    f"{table} lost rows during migration",
                )


class SyntheticLegacyMigrationTest(unittest.TestCase):
    """The part of §6 that must never be skipped. Runs with no external fixture."""

    @classmethod
    def setUpClass(cls):
        cls._fresh_ctx = TempDatabase()
        fresh = cls._fresh_ctx.__enter__()
        fresh.db.init_db()
        cls.fresh_schema = column_map(fresh.db_path)
        cls._fresh_ctx.__exit__(None, None, None)

    def setUp(self):
        # Build the legacy file in its own temp dir; the working copy is seeded
        # FROM it by file copy, so the fixture itself is never mutated. It must
        # outlive the test, hence addCleanup rather than an inline __exit__.
        self._fixture = TempDatabase()
        fixture = self._fixture.__enter__()
        self.addCleanup(self._fixture.__exit__, None, None, None)
        self.seed_counts = build_legacy_db(fixture.db_path)

        self._ctx = TempDatabase(seed_from=fixture.db_path)
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db

    # -- fixture self-validation -------------------------------------------

    def test_fixture_really_is_behind_the_current_schema(self):
        """If the fixture is no longer "old", every test below proves nothing."""
        gap = column_gap(self.ctx.db_path, self.fresh_schema)
        self.assertIn("users", gap)
        # Columns be3e2f6 genuinely lacked, all added later by _safe_alter.
        for column in ("currency", "is_admin", "login_streak", "security_question"):
            self.assertIn(column, gap["users"])
        # And it carries the column that was later renamed.
        legacy_users = column_map(self.ctx.db_path)["users"]
        self.assertIn("party_id", legacy_users)
        self.assertNotIn("guild_id", legacy_users)

    def test_fixture_is_missing_tables_a_current_database_has(self):
        """be3e2f6 predates most of the app — proves the fixture is really old."""
        have = set(column_map(self.ctx.db_path))
        for table in ("notes", "note_folders", "food_items", "achievements"):
            self.assertNotIn(table, have, f"{table} should not exist in be3e2f6")

    # -- migration behaviour -----------------------------------------------

    def test_init_db_completes_and_database_stays_intact(self):
        self.db.init_db()
        self.assertEqual(self.ctx.integrity_check(), "ok")
        self.assertEqual(self.ctx.foreign_key_violations(), [])

    def test_migration_creates_every_current_table(self):
        self.db.init_db()
        self.assertEqual(
            set(self.fresh_schema) - set(column_map(self.ctx.db_path)),
            set(),
            "tables present on a fresh database are absent after migration",
        )

    def test_migration_is_idempotent_on_a_legacy_database(self):
        self.db.init_db()
        first = column_map(self.ctx.db_path)
        counts_first = {t: self.ctx.count(t) for t in ("users", "habits", "dailies", "todos")}
        self.db.init_db()
        self.db.init_db()
        self.assertEqual(column_map(self.ctx.db_path), first)
        for table, n in counts_first.items():
            with self.subTest(table=table):
                self.assertEqual(self.ctx.count(table), n)
        self.assertEqual(self.ctx.integrity_check(), "ok")

    def test_pre_migration_rows_survive(self):
        """P6 — a user upgrading must not lose their data."""
        self.db.init_db()
        for table, before in self.seed_counts.items():
            with self.subTest(table=table):
                self.assertEqual(
                    self.ctx.count(table), before,
                    f"{table} changed row count during migration",
                )

    def test_migrated_rows_keep_their_values(self):
        self.db.init_db()
        conn = self.ctx.raw()
        try:
            row = conn.execute(
                "SELECT username, display_name, level, xp, gold, gems, hp, theme "
                "FROM users WHERE username=?", ("legacy_hero",),
            ).fetchone()
            habit = conn.execute(
                "SELECT name, icon, difficulty, streak, done_today FROM habits WHERE name=?",
                ("Legacy morning run",),
            ).fetchone()
            todo = conn.execute(
                "SELECT name, priority, done FROM todos WHERE name=?", ("Legacy errand",),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row, "legacy user vanished during migration")
        # ctx.raw() sets row_factory=sqlite3.Row, so compare tuple(row).
        self.assertEqual(
            tuple(row)[:7],
            ("legacy_hero", "Hero Lama", 7, 3400, 1250.5, 42, 50),
        )
        # The stored theme is the user's own choice — migration must NOT rewrite it.
        self.assertEqual(row[7], "overworld")
        self.assertEqual(tuple(habit), ("Legacy morning run", "🏃", "hard", 63, 1))
        self.assertEqual(tuple(todo), ("Legacy errand", "high", 0))

    def test_new_columns_are_added_to_old_rows_with_their_defaults(self):
        """ALTER TABLE ADD COLUMN must not leave pre-existing rows unusable."""
        self.db.init_db()
        conn = self.ctx.raw()
        try:
            row = conn.execute(
                "SELECT currency, is_admin, login_streak, onboarding_done, font_scale "
                "FROM users WHERE username=?", ("legacy_hero",),
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], "IDR")     # P2: money defaults to the home currency
        self.assertEqual(row[1], 0)         # never silently grant admin
        self.assertEqual(row[2], 0)
        self.assertEqual(row[3], 0)
        self.assertEqual(row[4], 100)

    def test_migrated_database_accepts_new_writes(self):
        """The point of migrating: the app must actually work afterwards.

        add_habit/get_habits touch columns that only exist on an old database
        after _safe_alter has run (folder_id, sort_order), so this exercises the
        migration instead of just reading the schema back.
        """
        self.db.init_db()
        uid = self.ctx.make_user("post_migration_user")

        result = self.db.add_habit(uid, "Post migration habit", "📖", "medium")
        # add_habit returns None on success, {"ok": False, ...} on failure.
        if isinstance(result, dict):
            self.assertTrue(result.get("ok"), f"add_habit refused: {result}")

        rows = self.db.get_habits(uid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Post migration habit")
        self.assertEqual(rows[0]["icon"], "📖")

        conn = self.ctx.raw()
        try:
            kept = conn.execute("SELECT COUNT(*) FROM habits WHERE user_id=1").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(kept, self.seed_counts["habits"])

    def test_legacy_users_table_has_no_guild_id_column(self):
        """Records a REAL gap found by this harness — see the report.

        be3e2f6 shipped ``users.party_id``. ``boss_battles`` got an explicit
        party_id -> guild_id migration (database.py:1646); ``users`` never did,
        and there is no ``_safe_alter(c, "users", "guild_id", ...)``. So a
        database from that era keeps ``party_id`` and never gains ``guild_id``,
        while 11+ queries read ``users.guild_id``.

        This asserts the CURRENT behaviour so the gap stays visible. If someone
        fixes it, this test fails and should be rewritten to assert the fix.
        """
        self.db.init_db()
        users = column_map(self.ctx.db_path)["users"]
        self.assertIn("party_id", users, "be3e2f6 fixture should still carry party_id")
        self.assertNotIn(
            "guild_id", users,
            "users.guild_id is now migrated from party_id — update this test to "
            "assert the migration instead of the gap",
        )


class LegacyHarnessSelfTest(unittest.TestCase):
    """Guards the harness so a silent skip cannot be mistaken for coverage."""

    def test_synthetic_harness_always_runs(self):
        self.assertFalse(
            getattr(SyntheticLegacyMigrationTest, "__unittest_skip__", False),
            "the synthetic legacy harness must run in CI, never skip",
        )

    def test_real_fixture_gap_is_reported_when_absent(self):
        if HAS_FIXTURE:
            self.skipTest("real legacy fixture present; nothing to warn about")
        self.assertTrue(
            LegacyMigrationTest.__unittest_skip__,
            "real-archive tests must be explicitly skipped, not silently absent",
        )
        self.assertIn("CRAFTLIFE_LEGACY_DB", LegacyMigrationTest.__unittest_skip_why__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
