"""M04a — Channel A on the client side (roadmap Kanal A, gap G1).

The server half is proven in supabase/tests/m04a_channel_a_test.sql against a
real PostgreSQL. This module covers the Python half: turning local rows into a
batch, and applying a batch with union semantics.

The behaviour that matters, and that the whole-document snapshot did not have:

* a row whose UUID is already present is left completely alone, so replaying an
  outbox is a no-op and a stale device cannot clobber a newer row;
* a foreign key that points at a user-owned entity is resolved through the M03
  UUID rather than the local integer id, because that id differs on every device
  (G3). A row whose parent is not known yet is skipped and retried later rather
  than inserted with a broken reference;
* the client's append-only list and the server's allowlist are the same list,
  pinned against the migration text so they cannot drift (P2).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from tests.harness import TempDatabase

REPO_ROOT = Path(__file__).resolve().parents[1]
CHANNEL_A_MIGRATION = (
    REPO_ROOT / "supabase" / "migrations"
    / "20261007000000_phase_m04a_entity_channel_a.sql"
)

# What measurement found at M04a: autoincrement PK, and no UPDATE anywhere in
# database.py. Tables that merely avoid UPDATE via delete+insert are not
# append-only and belong to Channel B.
MEASURED_APPEND_ONLY = (
    "food_logs",
    "water_logs",
    "health_logs",
    "task_history",
    "pomodoro_sessions",
    "sport_rep_logs",
    "supplies_tx",
)


class AllowListTest(unittest.TestCase):
    """The client list and the server allowlist must be one list, not two."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()

    def test_matches_the_measured_append_only_tables(self):
        self.assertEqual(tuple(self.db.APPEND_ONLY_TABLES), MEASURED_APPEND_ONLY)

    def test_excludes_mutable_tables(self):
        for table in ("habits", "dailies", "todos", "recipes", "notes"):
            self.assertNotIn(table, self.db.APPEND_ONLY_TABLES, table)

    def test_every_entry_is_a_sync_table_with_a_uuid_column(self):
        conn = self.ctx.raw()
        try:
            for table in self.db.APPEND_ONLY_TABLES:
                self.assertIn(table, self.db.SYNC_TABLES, table)
                cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
                self.assertIn("uuid", cols, f"{table} has no uuid column")
        finally:
            conn.close()

    def test_server_allowlist_is_the_same_list(self):
        """Parse the migration, so a one-sided edit fails here."""
        sql = CHANNEL_A_MIGRATION.read_text(encoding="utf-8")
        body = sql.split("public.sync_append_only_tables()")[1]
        body = body.split("$$")[1]
        server = tuple(re.findall(r"'([a-z_]+)'", body))
        self.assertEqual(server, tuple(self.db.APPEND_ONLY_TABLES),
                         "client APPEND_ONLY_TABLES and the SQL allowlist diverged")

    def test_mutable_table_is_refused(self):
        with self.assertRaises(ValueError):
            self.db.build_entity_append_batch(1, "habits")
        with self.assertRaises(ValueError):
            self.db.apply_entity_append_rows(1, "habits", [])
        with self.assertRaises(ValueError):
            self.db.enqueue_entity_append(1, "habits", "x")


class BatchAndApplyTest(unittest.TestCase):
    """Round-tripping rows through the Channel A payload format."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("channel_a_local")
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)
        self.food_id = self.conn.execute(
            "SELECT id FROM food_items LIMIT 1").fetchone()[0]

    def _log_meal(self, date="2026-10-06"):
        self.db.log_food(self.uid, self.food_id, 1, "lunch", date)
        return self.conn.execute(
            "SELECT uuid FROM food_logs WHERE user_id=? ORDER BY id DESC LIMIT 1",
            (self.uid,)).fetchone()[0]

    def test_batch_drops_the_local_id_and_keeps_the_uuid(self):
        self._log_meal()
        batch = self.db.build_entity_append_batch(self.uid, "food_logs")
        self.assertEqual(len(batch), 1)
        self.assertNotIn("id", batch[0], "a local autoincrement id means nothing remotely")
        self.assertIn("uuid", batch[0])

    def test_batch_carries_the_parent_uuid_for_a_foreign_key(self):
        """G3: food_id is a local integer, so the payload must also carry the UUID."""
        self._log_meal()
        row = self.db.build_entity_append_batch(self.uid, "food_logs")[0]
        expected = self.conn.execute(
            "SELECT uuid FROM food_items WHERE id=?", (self.food_id,)).fetchone()[0]
        self.assertEqual(row["food_uuid"], expected)

    def test_batch_can_be_limited_to_one_uuid(self):
        first = self._log_meal("2026-10-05")
        self._log_meal("2026-10-06")
        rows = self.db.build_entity_append_batch(self.uid, "food_logs", only_uuid=first)
        self.assertEqual([r["uuid"] for r in rows], [first])

    def test_apply_inserts_a_row_from_another_device(self):
        self._log_meal()
        remote = self.db.build_entity_append_batch(self.uid, "food_logs")
        self.assertEqual(len(remote), 1, "the fixture must have produced a row")
        self.conn.execute("DELETE FROM food_logs")
        self.conn.commit()
        self.assertEqual(self.ctx.count("food_logs"), 0)

        result = self.db.apply_entity_append_rows(self.uid, "food_logs", remote)
        self.assertEqual(result["inserted"], 1)
        self.assertEqual(self.ctx.count("food_logs"), 1)

    def test_replaying_the_same_batch_is_a_no_op(self):
        """The acceptance criterion: replay the outbox twice, no duplicates."""
        self._log_meal()
        remote = self.db.build_entity_append_batch(self.uid, "food_logs")

        first = self.db.apply_entity_append_rows(self.uid, "food_logs", remote)
        second = self.db.apply_entity_append_rows(self.uid, "food_logs", remote)

        self.assertEqual(first["skipped"], 1)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(second["inserted"], 0)
        self.assertEqual(self.ctx.count("food_logs"), 1)

    def test_union_keeps_both_devices_rows(self):
        """The scenario that lost data under whole-document LWW."""
        local_uuid = self._log_meal("2026-10-06")

        # Another device logged a different meal.
        other = self.db.build_entity_append_batch(self.uid, "food_logs")
        other[0]["uuid"] = "f" * 32
        other[0]["log_date"] = "2026-10-05"

        self.db.apply_entity_append_rows(self.uid, "food_logs", other)

        uuids = {r["uuid"] for r in self.conn.execute("SELECT uuid FROM food_logs")}
        self.assertEqual(uuids, {local_uuid, "f" * 32}, "both devices' rows must survive")

    def test_a_stale_row_never_overwrites_the_existing_one(self):
        self._log_meal()
        kept = self.conn.execute(
            "SELECT uuid, log_date, notes FROM food_logs").fetchone()

        stale = self.db.build_entity_append_batch(self.uid, "food_logs")[0]
        stale["log_date"] = "1999-01-01"
        stale["notes"] = "STALE"
        result = self.db.apply_entity_append_rows(self.uid, "food_logs", [stale])

        self.assertEqual(result["inserted"], 0)
        after = self.conn.execute(
            "SELECT uuid, log_date, notes FROM food_logs").fetchone()
        self.assertEqual(tuple(after), tuple(kept))

    def test_foreign_key_is_resolved_through_the_uuid_not_the_local_id(self):
        """The point of the whole milestone: local ids differ per device."""
        self._log_meal()
        remote = self.db.build_entity_append_batch(self.uid, "food_logs")
        original_food_id = remote[0]["food_id"]

        # Simulate the other device: the same food exists under a DIFFERENT local
        # id but the same M03 UUID.
        food = self.conn.execute(
            "SELECT uuid, name, calories, protein, carbs, fat FROM food_items WHERE id=?",
            (original_food_id,)).fetchone()
        self.conn.execute("DELETE FROM food_logs")
        self.conn.execute("DELETE FROM food_items WHERE id=?", (original_food_id,))
        self.conn.execute(
            "INSERT INTO food_items(uuid,name,calories,protein,carbs,fat,is_custom) "
            "VALUES(?,?,?,?,?,?,1)", tuple(food))
        self.conn.commit()
        new_food_id = self.conn.execute(
            "SELECT id FROM food_items WHERE uuid=?", (food["uuid"],)).fetchone()[0]
        self.assertNotEqual(new_food_id, original_food_id,
                            "the fixture must actually move the local id")

        result = self.db.apply_entity_append_rows(self.uid, "food_logs", remote)
        self.assertEqual(result["inserted"], 1)
        stored = self.conn.execute("SELECT food_id FROM food_logs").fetchone()[0]
        self.assertEqual(stored, new_food_id,
                         "food_id must be re-resolved locally, not copied")

    def test_a_row_whose_parent_is_unknown_is_skipped_not_broken(self):
        self._log_meal()
        remote = self.db.build_entity_append_batch(self.uid, "food_logs")
        # An incoming row this device has not seen, whose parent is also unknown
        # here. A known UUID would be skipped before the FK is ever resolved.
        remote[0]["uuid"] = "c" * 32
        remote[0]["food_uuid"] = "d" * 32

        result = self.db.apply_entity_append_rows(self.uid, "food_logs", remote)
        self.assertEqual(result["unresolved"], 1)
        self.assertEqual(result["inserted"], 0)
        # Only the row this device already had; the unresolvable one was refused.
        self.assertEqual(self.ctx.count("food_logs"), 1)
        self.assertEqual(self.ctx.foreign_key_violations(), [])

    def test_an_incoming_row_is_attributed_to_the_local_user(self):
        self._log_meal()
        remote = self.db.build_entity_append_batch(self.uid, "food_logs")
        remote[0]["uuid"] = "e" * 32
        remote[0]["user_id"] = 999_999  # the other device's local user id

        self.db.apply_entity_append_rows(self.uid, "food_logs", remote)
        owner = self.conn.execute(
            "SELECT user_id FROM food_logs WHERE uuid=?", ("e" * 32,)).fetchone()[0]
        self.assertEqual(owner, self.uid)

    def test_rows_without_a_uuid_are_ignored(self):
        result = self.db.apply_entity_append_rows(
            self.uid, "food_logs", [{"log_date": "2026-10-06"}, "not-a-dict", None])
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(self.ctx.count("food_logs"), 0)


class QueueIntegrationTest(unittest.TestCase):
    """Channel A reuses the existing outbox, dedupe included."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("queue_user")

    def test_enqueue_uses_the_event_append_entity_type(self):
        self.db.enqueue_entity_append(self.uid, "food_logs", "a" * 32)
        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["entity_type"], "event_append")
        self.assertEqual(jobs[0]["operation"], "append")

    def test_enqueueing_the_same_row_twice_reuses_one_job(self):
        self.db.enqueue_entity_append(self.uid, "food_logs", "a" * 32)
        first = self.db.get_pending_sync_jobs(self.uid)[0]["id"]
        self.db.enqueue_entity_append(self.uid, "food_logs", "a" * 32)
        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual(len(jobs), 1, "the existing dedupe must apply")
        self.assertEqual(jobs[0]["id"], first)

    def test_drain_order_puts_parents_before_children(self):
        """FK dependencies must be satisfied before their dependents are sent."""
        self.db.enqueue_sync(self.uid, "gallery_photo", 1, "upload", {})
        self.db.enqueue_sync(self.uid, "event_append", "u1", "append", {})
        self.db.enqueue_sync(self.uid, "profile", None, "upsert", {})
        self.db.enqueue_sync(self.uid, "personal_snapshot", "tracker_v1", "upsert", {})

        order = [j["entity_type"] for j in self.db.get_pending_sync_jobs(self.uid)]
        self.assertEqual(order, ["profile", "personal_snapshot",
                                 "event_append", "gallery_photo"])

    def test_drain_order_is_stable_for_an_unknown_entity_type(self):
        """An entity type added later must not jump the queue unpredictably."""
        self.db.enqueue_sync(self.uid, "gallery_photo", 1, "upload", {})
        self.db.enqueue_sync(self.uid, "something_new", 1, "do", {})
        self.db.enqueue_sync(self.uid, "profile", None, "upsert", {})
        order = [j["entity_type"] for j in self.db.get_pending_sync_jobs(self.uid)]
        self.assertEqual(order[0], "profile")
        self.assertEqual(order[-1], "gallery_photo")
        self.assertIn("something_new", order)


if __name__ == "__main__":
    unittest.main()
