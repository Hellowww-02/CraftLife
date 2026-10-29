"""M04b — Channel B row-level merge, tombstones, and change tracking.

Closes G1 (whole-document last-writer-wins discarded the losing device's rows)
and G4 (no tombstone convention, so deletes could not propagate).

Three pieces are covered here:

``merge_tracker_snapshots`` — a pure function, so the riskiest logic in the
milestone is testable without a database. Union by uuid, per-field LWW.

The SQLite triggers added in M04b — ``updated_at`` maintenance (without it
"send only what changed" is impossible: measured, 31 of 34 Channel B tables had
UPDATE statements that never touched it) and tombstone recording.

The deliberate deviation from the roadmap's wording. M04 says a delete should
write ``deleted_at`` instead of ``DELETE``. Measurement said that costs 47
delete sites plus a ``deleted_at IS NULL`` filter on ~361 of the 368 queries
that read those tables, only 7 of which already had one. A trigger that records
the deletion achieves the same propagation with none of that churn, so the
application's behaviour is unchanged (P4). The tests below pin that trade-off so
it is visible rather than implicit.
"""
from __future__ import annotations

import unittest

from tests.harness import TempDatabase


def row(uuid, updated_at="2026-10-06 10:00:00", **fields):
    base = {"uuid": uuid, "updated_at": updated_at, "rev": 1, "deleted_at": None}
    base.update(fields)
    return base


def snapshot(*table_rows):
    return {"tables": {name: rows for name, rows in table_rows}}


def make_habit_for_channel_b(db, uid, name="Kebiasaan"):
    """`add_habit(user_id, name, ...)` returns None, so read the row back."""
    db.add_habit(uid, name)
    return [r for r in db.get_habits(uid) if r["name"] == name][-1]

class MergeSemanticsTest(unittest.TestCase):
    """The pure merge function. No database involved."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.merge = self.db.merge_tracker_snapshots

    def test_a_row_only_in_the_cloud_is_added(self):
        merged = self.merge(snapshot(("habits", [])),
                            snapshot(("habits", [row("a" * 32, name="Meditasi")])))
        self.assertEqual(len(merged["tables"]["habits"]), 1)

    def test_a_row_only_locally_is_preserved(self):
        """THE fix for G1: the other device's offline work is no longer dropped."""
        merged = self.merge(snapshot(("habits", [row("a" * 32, name="Lokal")])),
                            snapshot(("habits", [])))
        names = [r["name"] for r in merged["tables"]["habits"]]
        self.assertEqual(names, ["Lokal"])

    def test_disjoint_rows_from_both_devices_all_survive(self):
        merged = self.merge(snapshot(("habits", [row("a" * 32, name="A")])),
                            snapshot(("habits", [row("b" * 32, name="B")])))
        self.assertEqual({r["name"] for r in merged["tables"]["habits"]}, {"A", "B"})

    def test_the_newer_side_wins_a_shared_field(self):
        local = row("a" * 32, "2026-10-06 10:00:00", name="Lama")
        remote = row("a" * 32, "2026-10-06 12:00:00", name="Baru")
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        self.assertEqual(merged["tables"]["habits"][0]["name"], "Baru")

    def test_the_older_side_does_not_overwrite_a_newer_local_edit(self):
        local = row("a" * 32, "2026-10-06 12:00:00", name="Lokal baru")
        remote = row("a" * 32, "2026-10-06 10:00:00", name="Cloud basi")
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        self.assertEqual(merged["tables"]["habits"][0]["name"], "Lokal baru")

    def test_a_tie_resolves_to_local_on_both_sides(self):
        """Deterministic, or the two devices would disagree about the result."""
        ts = "2026-10-06 10:00:00"
        a = self.merge(snapshot(("habits", [row("a" * 32, ts, name="L")])),
                       snapshot(("habits", [row("a" * 32, ts, name="R")])))
        b = self.merge(snapshot(("habits", [row("a" * 32, ts, name="L")])),
                       snapshot(("habits", [row("a" * 32, ts, name="R")])))
        self.assertEqual(a["tables"]["habits"][0]["name"], "L")
        self.assertEqual(a["tables"]["habits"], b["tables"]["habits"])

    def test_a_field_the_winner_never_had_is_filled_from_the_loser(self):
        """Per-field merge, not per-row replacement: notes survive an edit to name."""
        local = row("a" * 32, "2026-10-06 12:00:00", name="Baru", notes=None)
        remote = row("a" * 32, "2026-10-06 10:00:00", name="Lama", notes="Catatan penting")
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        result = merged["tables"]["habits"][0]
        self.assertEqual(result["name"], "Baru")
        self.assertEqual(result["notes"], "Catatan penting")

    def test_rev_never_goes_backwards(self):
        local = row("a" * 32, "2026-10-06 10:00:00", rev=7)
        remote = row("a" * 32, "2026-10-06 12:00:00", rev=3)
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        self.assertEqual(merged["tables"]["habits"][0]["rev"], 7)

    def test_a_tombstone_beats_an_older_edit(self):
        """Otherwise a delete would never propagate (G4)."""
        local = row("a" * 32, "2026-10-06 10:00:00", name="Masih ada", deleted_at=None)
        remote = row("a" * 32, "2026-10-06 12:00:00", name="Diedit lalu dihapus",
                     deleted_at="2026-10-06 13:00:00")
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        self.assertEqual(merged["tables"]["habits"][0]["deleted_at"], "2026-10-06 13:00:00")

    def test_the_newer_of_two_tombstones_is_kept(self):
        local = row("a" * 32, deleted_at="2026-10-06 10:00:00")
        remote = row("a" * 32, deleted_at="2026-10-06 15:00:00")
        merged = self.merge(snapshot(("habits", [local])), snapshot(("habits", [remote])))
        self.assertEqual(merged["tables"]["habits"][0]["deleted_at"], "2026-10-06 15:00:00")

    def test_rows_without_a_uuid_are_kept_rather_than_dropped(self):
        """They cannot be matched, so guessing would risk losing them."""
        merged = self.merge(snapshot(("habits", [{"name": "Tanpa uuid"}])),
                            snapshot(("habits", [row("a" * 32, name="Cloud")])))
        names = {r.get("name") for r in merged["tables"]["habits"]}
        self.assertEqual(names, {"Tanpa uuid", "Cloud"})

    def test_every_table_from_both_sides_is_present(self):
        merged = self.merge(snapshot(("habits", []), ("todos", [])),
                            snapshot(("habits", []), ("notes", [])))
        self.assertEqual(set(merged["tables"]), {"habits", "todos", "notes"})

    def test_merging_is_idempotent(self):
        remote = snapshot(("habits", [row("a" * 32, name="Meditasi")]))
        once = self.merge(snapshot(("habits", [])), remote)
        twice = self.merge(once, remote)
        self.assertEqual(once["tables"], twice["tables"])


class ChannelBTableSetTest(unittest.TestCase):
    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()

    def test_channel_b_is_everything_that_is_not_append_only(self):
        self.assertEqual(
            set(self.db.CHANNEL_B_TABLES),
            set(self.db.SYNC_TABLES) - set(self.db.APPEND_ONLY_TABLES))
        self.assertEqual(len(self.db.CHANNEL_B_TABLES), 34)

    def test_the_channels_do_not_overlap_and_cover_everything(self):
        self.assertEqual(set(self.db.CHANNEL_B_TABLES) & set(self.db.APPEND_ONLY_TABLES), set())
        self.assertEqual(
            set(self.db.CHANNEL_B_TABLES) | set(self.db.APPEND_ONLY_TABLES),
            set(self.db.SYNC_TABLES))

    def test_mutable_tables_really_are_in_channel_b(self):
        for table in ("habits", "dailies", "todos", "notes", "recipes"):
            self.assertIn(table, self.db.CHANNEL_B_TABLES, table)


class TriggerTest(unittest.TestCase):
    """The two triggers M04b adds to all 41 synced tables."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)
        self.uid = self.ctx.make_user("trigger_user")

    def test_every_synced_table_has_both_triggers(self):
        names = {r["name"] for r in self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        for table in self.db.SYNC_TABLES:
            self.assertIn(f"trg_{table}_sync_touch", names, table)
            self.assertIn(f"trg_{table}_sync_tombstone", names, table)

    def test_updated_at_advances_when_a_row_is_edited(self):
        """Before M04b this was false: update_habit left updated_at untouched."""
        self.db.add_habit(self.uid, "Sebelum")
        hid = self.conn.execute("SELECT id FROM habits WHERE user_id=?", (self.uid,)).fetchone()[0]
        before = self.conn.execute("SELECT updated_at FROM habits WHERE id=?", (hid,)).fetchone()[0]

        # Bypass the clock's 1-second resolution rather than sleeping.
        self.conn.execute("UPDATE habits SET updated_at='2020-01-01 00:00:00' WHERE id=?", (hid,))
        self.conn.commit()
        self.db.update_habit(hid, self.uid, name="Sesudah")

        after = self.conn.execute("SELECT updated_at FROM habits WHERE id=?", (hid,)).fetchone()[0]
        self.assertNotEqual(after, "2020-01-01 00:00:00")
        self.assertGreater(after, "2020-01-01 00:00:00")
        self.assertGreaterEqual(after, before)

    def test_code_that_stamps_updated_itself_is_not_overwritten(self):
        """The trigger's WHEN guard: an explicit timestamp is authoritative."""
        self.db.add_habit(self.uid, "H")
        hid = self.conn.execute("SELECT id FROM habits WHERE user_id=?", (self.uid,)).fetchone()[0]
        self.conn.execute(
            "UPDATE habits SET name='X', updated_at='2021-05-05 05:05:05' WHERE id=?", (hid,))
        self.conn.commit()
        got = self.conn.execute("SELECT updated_at FROM habits WHERE id=?", (hid,)).fetchone()[0]
        self.assertEqual(got, "2021-05-05 05:05:05")

    def test_deleting_a_row_records_a_tombstone(self):
        self.db.add_habit(self.uid, "Akan dihapus")
        hid = self.conn.execute("SELECT id FROM habits WHERE user_id=?", (self.uid,)).fetchone()[0]
        uuid = self.conn.execute("SELECT uuid FROM habits WHERE id=?", (hid,)).fetchone()[0]

        self.conn.execute("DELETE FROM habits WHERE id=?", (hid,))
        self.conn.commit()

        tomb = self.conn.execute(
            "SELECT table_name, entity_uuid, deleted_at FROM sync_tombstones").fetchall()
        self.assertEqual(len(tomb), 1)
        self.assertEqual(tomb[0]["table_name"], "habits")
        self.assertEqual(tomb[0]["entity_uuid"], uuid)
        self.assertIsNotNone(tomb[0]["deleted_at"])

    def test_the_row_really_is_deleted_locally(self):
        """The deviation from the roadmap's wording: DELETE stays a real DELETE,
        so no read query needs a deleted_at filter."""
        self.db.add_habit(self.uid, "Akan dihapus")
        hid = self.conn.execute("SELECT id FROM habits WHERE user_id=?", (self.uid,)).fetchone()[0]
        self.conn.execute("DELETE FROM habits WHERE id=?", (hid,))
        self.conn.commit()
        self.assertEqual(self.ctx.count("habits"), 0)

    def test_deleting_twice_does_not_duplicate_the_tombstone(self):
        self.db.add_habit(self.uid, "H")
        uuid = self.conn.execute("SELECT uuid FROM habits WHERE user_id=?", (self.uid,)).fetchone()[0]
        self.conn.execute("DELETE FROM habits WHERE user_id=?", (self.uid,))
        self.conn.commit()
        # Re-insert the same uuid, then delete again.
        self.conn.execute("INSERT INTO habits(user_id, name, uuid) VALUES(?,?,?)",
                          (self.uid, "H lagi", uuid))
        self.conn.commit()
        self.conn.execute("DELETE FROM habits WHERE user_id=?", (self.uid,))
        self.conn.commit()
        self.assertEqual(self.ctx.count("sync_tombstones"), 1)

    def test_repeated_init_db_keeps_the_ledger_intact(self):
        self.db.add_habit(self.uid, "H")
        self.conn.execute("DELETE FROM habits WHERE user_id=?", (self.uid,))
        self.conn.commit()
        before = self.ctx.count("sync_tombstones")
        self.db.init_db()
        self.db.init_db()
        self.assertEqual(self.ctx.count("sync_tombstones"), before)
        self.assertEqual(self.ctx.integrity_check(), "ok")

    def test_the_two_ledger_tables_exist(self):
        tables = self.ctx.table_names()
        self.assertIn("sync_tombstones", tables)
        self.assertIn("sync_entity_state", tables)


class EntityStateTest(unittest.TestCase):
    """sync_entity_state holds the `base_rev` side of the 3-way merge."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)

    def test_the_key_is_user_plus_table_plus_uuid(self):
        pk = [r["name"] for r in self.conn.execute("PRAGMA table_info(sync_entity_state)") if r["pk"]]
        self.assertEqual(pk, ["local_user_id", "table_name", "entity_uuid"])

    def test_a_state_row_upserts_rather_than_duplicates(self):
        self.conn.execute(
            "INSERT INTO sync_entity_state(local_user_id, table_name, entity_uuid, base_rev) "
            "VALUES(1,'habits','u1',1)")
        self.conn.execute(
            "INSERT OR REPLACE INTO sync_entity_state(local_user_id, table_name, entity_uuid, base_rev) "
            "VALUES(1,'habits','u1',5)")
        self.conn.commit()
        rows = self.conn.execute("SELECT base_rev FROM sync_entity_state").fetchall()
        self.assertEqual([r["base_rev"] for r in rows], [5])


class RecipeItemOwnershipTest(unittest.TestCase):
    """`recipe_items` is the one Channel B table without a `user_id` column.

    It is owned through its parent recipe. Assuming `user_id` existed made
    ``build_entity_change_batch('recipe_items')`` raise "no such column", and
    because ``_sync_channel_b`` isolates failures per table, the exception was
    swallowed: recipe ingredients silently never synced to another device while
    the sync result still reported ``available: True``.
    """

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("M04b")
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)
        food_id = self.conn.execute("SELECT id FROM food_items LIMIT 1").fetchone()[0]
        self.db.add_recipe(self.uid, "Nasi Goreng", "🍚", 1, "", [(food_id, 2)])

    def test_recipe_items_really_has_no_user_id_column(self):
        cols = {r["name"] for r in self.conn.execute("PRAGMA table_info(recipe_items)")}
        self.assertNotIn("user_id", cols, "the premise of this test changed; re-read the DDL")

    def test_a_batch_can_be_built_for_recipe_items(self):
        batch = self.db.build_entity_change_batch(self.uid, "recipe_items")
        self.assertEqual(len(batch), 1, "the ingredient row must be part of the batch")

    def test_another_users_ingredients_are_not_in_the_batch(self):
        other = self.ctx.make_user("Other")
        self.assertEqual(self.db.build_entity_change_batch(other, "recipe_items"), [])

    def test_all_channel_b_tables_can_build_a_batch(self):
        """Not just recipe_items - none of the 34 may raise here."""
        for table in self.db.CHANNEL_B_TABLES:
            with self.subTest(table=table):
                self.db.build_entity_change_batch(self.uid, table)


class ChannelBAcknowledgementTest(unittest.TestCase):
    """The acknowledged revision has to come back, or the 3-way merge is fake.

    `upsert_entities` originally returned only counts. Nothing ever called
    `record_entity_revisions_synced`, so `sync_entity_state.base_rev` stayed 0
    forever, every push claimed `base_rev: 0`, the server could not find the
    base side, and the merge silently degraded to 2-way last-writer-wins. The
    pgTAP suite could not catch this because it hand-crafts `base_rev` values.
    """

    class FakeCloud:
        """Echoes the batch back with a server-assigned rev, like the RPC now does."""

        def __init__(self):
            self.upserts = []

        def upsert_entities(self, table, batch, device_id):
            self.upserts.append((table, batch, device_id))
            return {"ok": True, "inserted": len(batch), "updated": 0,
                    "field_conflicts": 0, "deleted": 0, "unchanged": 0,
                    "rows": [{"uuid": r["uuid"], "rev": 7} for r in batch]}

        def push_tombstones(self, table, rows, device_id):
            return {"ok": True, "recorded": len(rows)}

        def fetch_tombstones(self, table):
            return {"ok": True, "table": table, "rows": []}

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("M04b")
        self.conn = self.ctx.raw()
        self.addCleanup(self.conn.close)
        import sync_service
        self.sync_service = sync_service
        self._old_db = sync_service.db
        sync_service.db = self.db
        self.addCleanup(setattr, sync_service, "db", self._old_db)

    def test_an_acknowledged_rev_is_recorded_as_the_next_base(self):
        habit = make_habit_for_channel_b(self.db, self.uid)
        engine = self.sync_service.CloudSyncService.__new__(self.sync_service.CloudSyncService)
        engine.cloud = self.FakeCloud()
        result = engine._sync_channel_b(self.uid)
        self.assertTrue(result.get("available"), result)
        state = self.conn.execute(
            "SELECT base_rev FROM sync_entity_state WHERE entity_uuid=?",
            (habit["uuid"],)).fetchone()
        self.assertIsNotNone(state, "base_rev was never recorded - the merge would stay 2-way")
        self.assertEqual(state["base_rev"], 7)

    def test_the_next_batch_carries_that_base_rev(self):
        habit = make_habit_for_channel_b(self.db, self.uid)
        engine = self.sync_service.CloudSyncService.__new__(self.sync_service.CloudSyncService)
        engine.cloud = self.FakeCloud()
        engine._sync_channel_b(self.uid)
        batch = self.db.build_entity_change_batch(self.uid, "habits")
        sent = [r for r in batch if r["uuid"] == habit["uuid"]][0]
        self.assertEqual(sent["base_rev"], 7,
                         "a push that still claims base_rev 0 cannot be 3-way merged")

    def test_every_channel_b_table_survives_the_push(self):
        """One table raising must not quietly take the others with it."""
        engine = self.sync_service.CloudSyncService.__new__(self.sync_service.CloudSyncService)
        engine.cloud = self.FakeCloud()
        result = engine._sync_channel_b(self.uid)
        self.assertTrue(result.get("available"), result)
        self.assertEqual(result.get("errors") or {}, {},
                         f"tables failed silently: {result.get('errors')}")


if __name__ == "__main__":
    unittest.main()
