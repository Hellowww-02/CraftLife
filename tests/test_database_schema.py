"""Fresh-database harness (UPDATE_ROADMAP M02).

Proves the claim in UPDATE_RULES.md §6: ``init_db()`` must complete against a
brand-new database, be idempotent, and leave the schema internally consistent.

Run:  python -m unittest tests.test_database_schema -v
"""
from __future__ import annotations

import unittest

from tests.harness import TempDatabase

# Migration scratch tables that are intentionally renamed away during init_db()
# and therefore never persist. See database.py:1618 / :1643.
SCRATCH_TABLES = {"playlists_new"}


class FreshDatabaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = TempDatabase()
        cls.ctx = cls._ctx.__enter__()
        cls.db = cls.ctx.db
        cls.db.init_db()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    # -- structure -------------------------------------------------------
    def test_init_db_completes_on_fresh_database(self):
        # Reaching this point at all is the assertion: setUpClass ran init_db()
        # against an empty file without raising.
        self.assertTrue(len(self.ctx.table_names()) > 0)

    def test_every_declared_table_is_created(self):
        """Self-maintaining drift check.

        Compares the CREATE TABLE statements in database.py with the tables that
        actually exist, so a table that is declared but never created (or the
        reverse) fails the build instead of surfacing later as a missing feature.
        """
        declared = self.ctx.declared_tables() - SCRATCH_TABLES
        actual = self.ctx.table_names()
        self.assertEqual(
            declared,
            actual,
            "declared vs created table sets differ; "
            f"missing={sorted(declared - actual)} unexpected={sorted(actual - declared)}",
        )

    def test_table_count_is_in_expected_range(self):
        n = len(self.ctx.table_names())
        self.assertGreaterEqual(n, 100, "table count dropped unexpectedly")
        self.assertLess(n, 400, "table count exploded unexpectedly")

    def test_scratch_table_does_not_persist(self):
        self.assertNotIn("playlists_new", self.ctx.table_names())
        self.assertIn("playlists", self.ctx.table_names())

    def test_indexes_exist(self):
        conn = self.ctx.raw()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            ).fetchall()
        finally:
            conn.close()
        self.assertGreater(len(rows), 50, "expected a substantial set of idx_* indexes")

    # -- integrity -------------------------------------------------------
    def test_integrity_check_ok(self):
        self.assertEqual(self.ctx.integrity_check(), "ok")

    def test_no_foreign_key_violations(self):
        self.assertEqual(self.ctx.foreign_key_violations(), [])

    # -- seed data -------------------------------------------------------
    def test_seed_data_present(self):
        for table, minimum in (("food_items", 1000), ("achievements", 70), ("redeem_codes", 20)):
            with self.subTest(table=table):
                self.assertGreaterEqual(
                    self.ctx.count(table),
                    minimum,
                    f"{table} was not seeded as expected",
                )

    def test_food_catalogue_has_no_duplicate_names(self):
        conn = self.ctx.raw()
        try:
            row = conn.execute(
                "SELECT COUNT(*) - COUNT(DISTINCT name) FROM food_items"
            ).fetchone()
        finally:
            conn.close()
        self.assertEqual(row[0], 0, "food_items contains duplicate names")

    # -- sync prerequisites ---------------------------------------------
    def test_export_tables_all_exist(self):
        """EXPORT_TABLES drives the cloud snapshot; a missing table breaks sync."""
        export_tables = set(self.db.EXPORT_TABLES)
        actual = self.ctx.table_names()
        missing = sorted(export_tables - actual)
        self.assertEqual(missing, [], f"EXPORT_TABLES references missing tables: {missing}")

    def test_export_tables_is_a_stable_tuple_of_strings(self):
        self.assertGreater(len(self.db.EXPORT_TABLES), 30)
        for name in self.db.EXPORT_TABLES:
            self.assertIsInstance(name, str)


class IdempotenceTest(unittest.TestCase):
    """UPDATE_RULES.md §6: running init_db() twice must not error."""

    def test_init_db_twice_is_idempotent(self):
        with TempDatabase() as ctx:
            ctx.db.init_db()
            tables_first = ctx.table_names()
            foods_first = ctx.count("food_items")
            achievements_first = ctx.count("achievements")

            # Second run must not raise, must not duplicate seed rows, and must
            # not change the table set.
            ctx.db.init_db()

            self.assertEqual(ctx.table_names(), tables_first)
            self.assertEqual(ctx.count("food_items"), foods_first)
            self.assertEqual(ctx.count("achievements"), achievements_first)
            self.assertEqual(ctx.integrity_check(), "ok")
            self.assertEqual(ctx.foreign_key_violations(), [])

    def test_init_db_three_times_preserves_user_data(self):
        """A third run must not wipe rows a user created between runs."""
        with TempDatabase() as ctx:
            ctx.db.init_db()
            uid = ctx.make_user("keeper")
            ctx.db.init_db()
            ctx.db.init_db()

            user = ctx.db.get_user(uid)
            self.assertIsNotNone(user, "user row disappeared across repeated init_db()")
            self.assertEqual(user["username"], "keeper")


if __name__ == "__main__":
    unittest.main(verbosity=2)


class ForeignKeyEnforcementTest(unittest.TestCase):
    """Foreign keys must actually be enforced after init_db().

    This was silently false. ``init_db()`` turns foreign keys off for the
    migration and then tried to turn them back on, but SQLite IGNORES
    ``PRAGMA foreign_keys`` executed inside a transaction — no error, no
    warning. The connection is pooled, so the whole process ran with FK off:
    every ON DELETE CASCADE was dead and no constraint was enforced.

    The same pattern existed in six ``finally`` blocks that restore the pragma
    after an import. All of them now go through ``_foreign_keys_on()``, which
    ends any open transaction first. These tests pin the invariant, because a
    pragma that fails silently will regress silently too.
    """

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("fk_user")

    def test_foreign_keys_are_on_after_init_db(self):
        self.assertEqual(
            self.db.get_conn().execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_cascade_delete_actually_runs(self):
        conn = self.ctx.raw()
        try:
            rid = conn.execute(
                "INSERT INTO recipes(user_id, name) VALUES(?,?) RETURNING id",
                (self.uid, "Resep")).fetchone()[0]
            conn.execute(
                "INSERT INTO recipe_items(recipe_id, food_id, quantity) "
                "SELECT ?, id, 1 FROM food_items LIMIT 1", (rid,))
            conn.commit()
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM recipe_items WHERE recipe_id=?",
                             (rid,)).fetchone()[0], 1)
        finally:
            conn.close()

        # Through the application connection, which has foreign_keys = ON.
        app = self.db.get_conn()
        app.execute("DELETE FROM recipes WHERE id=?", (rid,))
        app.commit()
        self.assertEqual(
            app.execute("SELECT COUNT(*) FROM recipe_items WHERE recipe_id=?",
                        (rid,)).fetchone()[0], 0,
            "ON DELETE CASCADE did not run — foreign keys are off again")

    def test_a_dangling_foreign_key_is_rejected(self):
        app = self.db.get_conn()
        with self.assertRaises(Exception):
            app.execute(
                "INSERT INTO recipe_items(recipe_id, food_id, quantity) "
                "VALUES(99999999, 1, 1)")
            app.commit()
        app.rollback()

    def test_cascade_children_are_tombstoned_for_sync(self):
        """Ties the fix to M04b: with FK off, the child's deletion was invisible
        to the sync ledger, so the other device kept an orphan."""
        conn = self.ctx.raw()
        try:
            rid = conn.execute(
                "INSERT INTO recipes(user_id, name) VALUES(?,?) RETURNING id",
                (self.uid, "Resep")).fetchone()[0]
            conn.execute(
                "INSERT INTO recipe_items(recipe_id, food_id, quantity) "
                "SELECT ?, id, 1 FROM food_items LIMIT 1", (rid,))
            conn.commit()
        finally:
            conn.close()

        app = self.db.get_conn()
        app.execute("DELETE FROM recipes WHERE id=?", (rid,))
        app.commit()
        tables = {r["table_name"] for r in app.execute(
            "SELECT table_name FROM sync_tombstones")}
        self.assertIn("recipes", tables)
        self.assertIn("recipe_items", tables,
                      "the cascaded child must be tombstoned too")

    def test_foreign_keys_survive_a_cloud_snapshot_apply(self):
        """import_tracker_data() also toggles the pragma; it must restore it."""
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        self.db.apply_cloud_personal_snapshot(self.uid, snapshot)
        self.assertEqual(
            self.db.get_conn().execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_the_database_is_left_without_fk_violations(self):
        self.assertEqual(self.ctx.foreign_key_violations(), [])
