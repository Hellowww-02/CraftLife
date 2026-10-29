"""M04c — sync status and a recoverable conflict surface.

Before this milestone the only conflict UI was a binary "keep local / use cloud"
dialog: the user was asked to throw an entire snapshot away, and the values the
loser held were never listed anywhere. K11 already guarantees the losing side is
stored, not discarded. These tests pin the part that makes that guarantee usable:
a conflict is recorded when it happens, it can be listed, and a single field can
be restored without touching the rest of the row.

Also covered: the merge must NOT report a conflict when the winner's field was
empty, because the loser's value is adopted in that case and nothing is lost.
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


def make_habit(db, uid, name="Kebiasaan", notes=""):
    """`add_habit(user_id, name, ...)` returns None, so read the row back."""
    db.add_habit(uid, name, notes=notes)
    rows = db.get_habits(uid)
    match = [r for r in rows if r["name"] == name]
    return match[-1]


class ConflictLedgerTest(unittest.TestCase):
    """A conflict that resolves silently is still data loss from the user's seat."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("M04c")
        self.record = lambda table, uuid, field, kept, lost, side: \
            self.db.record_sync_conflict(self.uid, table, uuid, field, kept, lost, side)

    def test_a_losing_field_is_recorded_with_both_values(self):
        merged = self.db.merge_tracker_snapshots(
            snapshot(("habits", [row("a" * 32, name="Meditasi", description="lokal",
                                     updated_at="2026-10-08 05:00:00")])),
            snapshot(("habits", [row("a" * 32, name="Meditasi", description="cloud",
                                     updated_at="2026-10-08 09:00:00")])),
            on_conflict=self.record)
        self.assertEqual(merged["tables"]["habits"][0]["description"], "cloud")
        conflicts = self.db.list_sync_conflicts(self.uid)
        self.assertEqual(len(conflicts), 1, f"expected 1 conflict, got {conflicts}")
        c = conflicts[0]
        self.assertEqual((c["table_name"], c["field"], c["kept_side"]), ("habits", "description", "cloud"))
        self.assertEqual((c["kept_value"], c["lost_value"]), ("cloud", "lokal"))

    def test_an_empty_field_on_the_winner_is_not_a_conflict(self):
        """The loser's value is adopted here, so nothing was lost."""
        self.db.merge_tracker_snapshots(
            snapshot(("habits", [row("a" * 32, name="Meditasi", description="lokal",
                                     updated_at="2026-10-08 05:00:00")])),
            snapshot(("habits", [row("a" * 32, name="Meditasi", description=None,
                                     updated_at="2026-10-08 09:00:00")])),
            on_conflict=self.record)
        self.assertEqual(self.db.list_sync_conflicts(self.uid), [])

    def test_a_tie_is_not_a_conflict(self):
        """Ties resolve to local by design; the same value is not a loss."""
        same = {"updated_at": "2026-10-08 09:00:00"}
        self.db.merge_tracker_snapshots(
            snapshot(("habits", [row("a" * 32, name="Lokal", **same)])),
            snapshot(("habits", [row("a" * 32, name="Lokal", **same)])),
            on_conflict=self.record)
        self.assertEqual(self.db.list_sync_conflicts(self.uid), [])

    def test_local_can_lose_too(self):
        """The ledger is symmetric: an older cloud edit can win."""
        self.db.merge_tracker_snapshots(
            snapshot(("habits", [row("a" * 32, name="Lokal", updated_at="2026-10-08 12:00:00")])),
            snapshot(("habits", [row("a" * 32, name="Cloud", updated_at="2026-10-08 06:00:00")])),
            on_conflict=self.record)
        conflicts = self.db.list_sync_conflicts(self.uid)
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["kept_side"], "local")
        self.assertEqual(conflicts[0]["lost_value"], "Cloud")

    def test_restoring_puts_only_that_field_back(self):
        kept = make_habit(self.db, self.uid, notes="versi lama")
        self.record("habits", kept["uuid"], "notes", "versi baru", "versi lama", "cloud")
        conflict_id = self.db.list_sync_conflicts(self.uid)[0]["id"]
        result = self.db.restore_sync_conflict(self.uid, conflict_id)
        self.assertTrue(result["ok"], result)
        after = self.db.get_habits(self.uid)[0]
        self.assertEqual(after["notes"], "versi lama")
        self.assertEqual(after["name"], "Kebiasaan", "the rest of the row must not move")
        self.assertEqual(self.db.list_sync_conflicts(self.uid), [])
        self.assertEqual(len(self.db.list_sync_conflicts(self.uid, include_restored=True)), 1)

    def test_restore_is_rejected_rather_than_crashing(self):
        self.record("habits", "b" * 32, "notes", "baru", "lama", "cloud")
        conflict_id = self.db.list_sync_conflicts(self.uid)[0]["id"]
        self.assertEqual(self.db.restore_sync_conflict(self.uid, conflict_id)["code"], "entity_not_found")

    def test_an_unknown_table_is_refused_not_executed(self):
        """restore builds SQL from the stored table name, so it must be allowlisted."""
        self.record("users", "c" * 32, "password_hash", "baru", "lama", "cloud")
        conflict_id = self.db.list_sync_conflicts(self.uid)[0]["id"]
        self.assertEqual(self.db.restore_sync_conflict(self.uid, conflict_id)["code"], "unsupported_table")

    def test_restoring_twice_is_refused(self):
        kept = make_habit(self.db, self.uid)
        self.record("habits", kept["uuid"], "notes", "baru", "lama", "cloud")
        conflict_id = self.db.list_sync_conflicts(self.uid)[0]["id"]
        self.assertTrue(self.db.restore_sync_conflict(self.uid, conflict_id)["ok"])
        self.assertEqual(self.db.restore_sync_conflict(self.uid, conflict_id)["code"], "already_restored")

    def test_non_string_values_survive_the_round_trip(self):
        kept = make_habit(self.db, self.uid)
        self.record("habits", kept["uuid"], "xp_reward", 7, 3, "cloud")
        conflict_id = self.db.list_sync_conflicts(self.uid)[0]["id"]
        self.assertTrue(self.db.restore_sync_conflict(self.uid, conflict_id)["ok"])
        after = self.db.get_habits(self.uid)[0]
        self.assertEqual(int(after["xp_reward"]), 3, "an integer value must survive the round trip")


class SyncStatusTest(unittest.TestCase):
    """The status panel reads real queue state; it must not invent numbers."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("M04c")

    def test_a_fresh_account_has_nothing_pending(self):
        status = self.db.sync_status_summary(self.uid)
        self.assertEqual(status["pending"], 0)
        self.assertEqual(status["failed"], 0)
        self.assertEqual(status["unresolved_conflicts"], 0)
        self.assertIsNone(status["last_synced_at"])

    def test_a_queued_job_is_counted_as_pending(self):
        self.db.enqueue_entity_append(self.uid, "food_logs", "op-1")
        self.assertEqual(self.db.sync_status_summary(self.uid)["pending"], 1)

    def test_a_conflict_shows_up_in_the_status(self):
        self.db.record_sync_conflict(self.uid, "habits", "a" * 32, "name", "baru", "lama", "cloud")
        self.assertEqual(self.db.sync_status_summary(self.uid)["unresolved_conflicts"], 1)

    def test_an_unpushed_tombstone_is_visible(self):
        habit = make_habit(self.db, self.uid)
        self.db.delete_habit(self.uid, habit["id"])
        self.assertGreaterEqual(self.db.sync_status_summary(self.uid)["pending_tombstones"], 1)


class ChannelBPendingCountTest(unittest.TestCase):
    """Channel B never touches `sync_queue`, so a queue-only count lies.

    Measured before the fix: edit a habit offline and `sync_status_summary`
    reported pending=0 while `build_entity_change_batch` had a row waiting to
    push. The panel therefore printed "All synced" over unsynced work.
    """

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("M04c")

    def test_an_offline_edit_is_counted_as_pending(self):
        make_habit(self.db, self.uid)
        self.assertEqual(self.db.pending_entity_change_count(self.uid), 1)
        self.assertEqual(self.db.sync_status_summary(self.uid)["pending"], 1)

    def test_an_acknowledged_row_stops_being_pending(self):
        habit = make_habit(self.db, self.uid)
        self.db.record_entity_revisions_synced(
            self.uid, "habits", [{"uuid": habit["uuid"], "rev": habit["rev"]}])
        self.assertEqual(self.db.pending_entity_change_count(self.uid), 0)

    def test_editing_after_an_acknowledgement_makes_it_pending_again(self):
        habit = make_habit(self.db, self.uid)
        self.db.record_entity_revisions_synced(
            self.uid, "habits", [{"uuid": habit["uuid"], "rev": habit["rev"]}])
        self.assertEqual(self.db.pending_entity_change_count(self.uid), 0)
        # datetime('now') only resolves to whole seconds, so the test sets
        # updated_at explicitly; the trigger's WHEN guard leaves an explicit
        # value alone, which is the behaviour this relies on.
        self.db.update_habit(habit["id"], self.uid, notes="diubah lagi",
                             updated_at="2030-01-01 00:00:00")
        self.assertEqual(self.db.pending_entity_change_count(self.uid), 1)

    def test_the_watermark_is_the_row_version_that_was_sent(self):
        """`now()` would mask an edit made while the request was in flight."""
        habit = make_habit(self.db, self.uid)
        self.db.record_entity_revisions_synced(
            self.uid, "habits", [{"uuid": habit["uuid"], "rev": habit["rev"]}])
        state = self.ctx.raw().execute(
            "SELECT last_synced_at FROM sync_entity_state WHERE entity_uuid=?",
            (habit["uuid"],)).fetchone()
        self.assertEqual(state["last_synced_at"], habit["updated_at"])

    def test_another_users_rows_are_not_counted(self):
        make_habit(self.db, self.uid)
        other = self.ctx.make_user("Other")
        self.assertEqual(self.db.pending_entity_change_count(other), 0)

    def test_a_recipe_ingredient_is_counted_through_its_parent(self):
        """`recipe_items` has no user_id; ownership comes from the recipe."""
        conn = self.ctx.raw()
        self.addCleanup(conn.close)
        food_id = conn.execute("SELECT id FROM food_items LIMIT 1").fetchone()[0]
        self.db.add_recipe(self.uid, "Nasi Goreng", "🍚", 1, "", [(food_id, 2)])
        self.assertEqual(self.db.pending_entity_change_count(self.uid), 2,
                         "the recipe and its ingredient are both unsynced")


class SyncOutContractTest(unittest.TestCase):
    """`_sync_out` used to call itself and raise RecursionError on every sync."""

    def test_a_failure_without_an_error_gets_a_code(self):
        import cloud_api
        out = cloud_api._sync_out({"ok": False, "code": "device_not_registered"})
        self.assertEqual(out["error"], "device_not_registered")

    def test_an_existing_error_is_left_alone(self):
        import cloud_api
        self.assertEqual(cloud_api._sync_out({"ok": False, "error": "sudah ada"})["error"], "sudah ada")

    def test_success_passes_through(self):
        import cloud_api
        self.assertEqual(cloud_api._sync_out({"ok": True, "pushed": 3})["pushed"], 3)

    def test_the_input_is_not_mutated(self):
        import cloud_api
        original = {"ok": False}
        cloud_api._sync_out(original)
        self.assertEqual(original, {"ok": False})


if __name__ == "__main__":
    unittest.main(verbosity=2)
