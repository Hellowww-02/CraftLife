"""Conflict-resolution behaviour of the personal snapshot sync.

Written in M02 to document and pin the whole-document personal sync, including
the data-loss path identified in the Phase 0 audit as risk R1 / gap G1. M04b
closed that gap, and this module was updated to pin the new behaviour.

Two kinds of test live here:

1. ``CurrentBehaviourTest`` — asserts what the code does today. Two of these
   originally pinned the DEFECT on purpose, so that fixing it would be a
   deliberate, reviewed change rather than an accident. They now assert the
   merged behaviour instead.
2. ``DesiredBehaviourTest`` — what M04 was required to deliver. It carried
   ``@unittest.expectedFailure`` while G1 was open; M04b made it pass, so the
   decorator was removed and these are now ordinary required tests.

Run:  python -m unittest tests.test_sync_conflict -v
"""
from __future__ import annotations

import unittest

from tests.harness import TempDatabase


class SnapshotConflictBase(unittest.TestCase):
    """Builds the two-device scenario the audit describes."""

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("conflictuser")

        # A real food row so log_food() has a valid foreign key.
        conn = self.ctx.raw()
        try:
            self.food_id = conn.execute("SELECT id FROM food_items LIMIT 1").fetchone()[0]
        finally:
            conn.close()

    def tearDown(self):
        self._ctx.__exit__(None, None, None)

    # -- helpers ---------------------------------------------------------
    def habit_names(self) -> set[str]:
        conn = self.ctx.raw()
        try:
            rows = conn.execute("SELECT name FROM habits WHERE user_id=?", (self.uid,)).fetchall()
            return {r["name"] for r in rows}
        finally:
            conn.close()

    def food_log_count(self) -> int:
        conn = self.ctx.raw()
        try:
            return conn.execute(
                "SELECT COUNT(*) FROM food_logs WHERE user_id=?", (self.uid,)
            ).fetchone()[0]
        finally:
            conn.close()


class CurrentBehaviourTest(SnapshotConflictBase):
    """What the whole-document snapshot sync does today."""

    def test_snapshot_round_trip_preserves_data(self):
        """Baseline: pushing then pulling an unchanged device is lossless."""
        self.db.add_habit(self.uid, "Meditasi")
        self.db.log_food(self.uid, self.food_id, 1, "breakfast", "2026-10-06")

        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        applied = self.db.apply_cloud_personal_snapshot(self.uid, snapshot)

        self.assertTrue(applied["ok"])
        self.assertIn("Meditasi", self.habit_names())
        self.assertEqual(self.food_log_count(), 1)

    def test_snapshot_hash_is_stable_across_rebuilds(self):
        """Row order must not create phantom revisions (the whole point of the
        canonical-JSON hash)."""
        self.db.add_habit(self.uid, "Meditasi")
        self.db.add_habit(self.uid, "Olahraga")
        h1 = self.db.cloud_personal_snapshot_hash(self.db.build_cloud_personal_snapshot(self.uid))
        h2 = self.db.cloud_personal_snapshot_hash(self.db.build_cloud_personal_snapshot(self.uid))
        self.assertEqual(h1, h2)

    def test_snapshot_hash_changes_when_data_changes(self):
        self.db.add_habit(self.uid, "Meditasi")
        h1 = self.db.cloud_personal_snapshot_hash(self.db.build_cloud_personal_snapshot(self.uid))
        self.db.add_habit(self.uid, "Olahraga")
        h2 = self.db.cloud_personal_snapshot_hash(self.db.build_cloud_personal_snapshot(self.uid))
        self.assertNotEqual(h1, h2)

    def test_empty_snapshot_is_detected(self):
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        self.assertTrue(self.db.cloud_personal_snapshot_is_empty(snapshot))

        self.db.add_habit(self.uid, "Meditasi")
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        self.assertFalse(self.db.cloud_personal_snapshot_is_empty(snapshot))

    def test_applying_a_stale_snapshot_preserves_newer_local_rows(self):
        """G1 / R1 — the data-loss path, closed by M04b.

        Device A pushes a snapshot. Device B then records a meal offline. Before
        M04b the transport was a whole document, so resolving the conflict as
        "use cloud" replaced device B's data wholesale and the meal was gone.

        The snapshot channel is now a merge (K6/K14): it is still used for
        backup/import/recovery, but applying it unions rows by uuid instead of
        replacing the document. This test pins that the offline meal survives.
        """
        # Device A's state, as pushed to the cloud.
        self.db.add_habit(self.uid, "Meditasi")
        cloud_snapshot = self.db.build_cloud_personal_snapshot(self.uid)

        # Device B works offline and records a meal that is NOT in the snapshot.
        self.db.log_food(self.uid, self.food_id, 1, "lunch", "2026-10-06")
        self.assertEqual(self.food_log_count(), 1)

        self.db.apply_cloud_personal_snapshot(self.uid, cloud_snapshot)

        # Both sides survive: the habit from the snapshot and the offline meal.
        self.assertIn("Meditasi", self.habit_names())
        self.assertEqual(
            self.food_log_count(),
            1,
            "a stale snapshot must not discard rows the other device created; "
            "if this fails, the row-level merge has regressed to a whole-document "
            "replace (G1 is open again).",
        )

    def test_local_backup_payload_is_a_safety_net_not_the_only_one(self):
        """The backup still records the pre-merge state, but it is no longer the
        only place the losing side survives — M04b made that a merge, not a
        replacement."""
        self.db.add_habit(self.uid, "Meditasi")
        cloud_snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        self.db.log_food(self.uid, self.food_id, 1, "lunch", "2026-10-06")

        applied = self.db.apply_cloud_personal_snapshot(self.uid, cloud_snapshot)
        backup = applied.get("local_backup") or {}
        tables = backup.get("tables") or {}

        # The meal is in the live table now, and the backup still captured it.
        self.assertEqual(self.food_log_count(), 1)
        self.assertGreaterEqual(len(tables.get("food_logs") or []), 1)



class DesiredBehaviourTest(SnapshotConflictBase):
    """What M04 was required to deliver — and now does.

    This class was marked ``@unittest.expectedFailure`` while G1 was open, so
    that CI stayed green and the gap stayed visible. M04b landed the row-level
    merge and it reported "unexpected success", which was the signal to adopt
    these as the real contract. The decorator is therefore gone: these are
    ordinary, required-to-pass tests now.
    """

    def test_concurrent_edits_on_two_devices_both_survive(self):
        # Device A pushes a snapshot containing one habit.
        self.db.add_habit(self.uid, "Meditasi")
        cloud_snapshot = self.db.build_cloud_personal_snapshot(self.uid)

        # Device B records a meal offline.
        self.db.log_food(self.uid, self.food_id, 1, "lunch", "2026-10-06")

        # Pulling the cloud snapshot must merge, not replace.
        self.db.apply_cloud_personal_snapshot(self.uid, cloud_snapshot)

        # Desired: BOTH the cloud habit and the local meal survive.
        self.assertIn("Meditasi", self.habit_names())
        self.assertEqual(self.food_log_count(), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
