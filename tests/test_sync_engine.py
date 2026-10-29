"""Sync queue behaviour (UPDATE_ROADMAP M02).

Covers the outbox primitives that both the desktop sync engine and the future
Android client depend on: enqueue, dedupe, backoff, retry, drain and per-user
scoping. These are the functions M03/M04 extend, so pinning their current
behaviour now is what makes that refactor safe.

Run:  python -m unittest tests.test_sync_engine -v
"""
from __future__ import annotations

import json
import unittest
from datetime import datetime

from tests.harness import TempDatabase


class SyncQueueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = TempDatabase()
        cls.ctx = cls._ctx.__enter__()
        cls.db = cls.ctx.db
        cls.db.init_db()
        cls.uid = cls.ctx.make_user("synctester")

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def setUp(self):
        # Start every test from an empty queue so ordering assertions hold.
        conn = self.ctx.raw()
        try:
            conn.execute("DELETE FROM sync_queue")
            conn.commit()
        finally:
            conn.close()

    # -- enqueue ---------------------------------------------------------
    def test_enqueue_creates_a_pending_job(self):
        result = self.db.enqueue_sync(self.uid, "profile", "1", "upsert", {"a": 1})
        self.assertTrue(result["ok"])
        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["entity_type"], "profile")
        self.assertEqual(jobs[0]["operation"], "upsert")
        self.assertEqual(jobs[0]["status"], "pending")
        self.assertEqual(json.loads(jobs[0]["payload"]), {"a": 1})

    def test_enqueue_is_idempotent_for_identical_pending_job(self):
        """UPDATE_RULES.md §8.2 — creating a record twice must not duplicate it."""
        first = self.db.enqueue_sync(self.uid, "profile", "1", "upsert", {"v": 1})
        second = self.db.enqueue_sync(self.uid, "profile", "1", "upsert", {"v": 2})
        self.assertEqual(first["job_id"], second["job_id"], "dedupe failed: two rows created")

        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual(len(jobs), 1)
        # The newer payload must win, otherwise the cloud receives stale data.
        self.assertEqual(json.loads(jobs[0]["payload"]), {"v": 2})

    def test_enqueue_different_operation_is_a_separate_job(self):
        self.db.enqueue_sync(self.uid, "profile_photo", "1", "upload")
        self.db.enqueue_sync(self.uid, "profile_photo", "1", "delete")
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid)), 2)

    def test_enqueue_distinguishes_entity_ids(self):
        self.db.enqueue_sync(self.uid, "gallery_photo", "1", "upload")
        self.db.enqueue_sync(self.uid, "gallery_photo", "2", "upload")
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid)), 2)

    def test_enqueue_handles_null_entity_id(self):
        result = self.db.enqueue_sync(self.uid, "love_space_bundle", None, "migrate")
        self.assertTrue(result["ok"])
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid)), 1)

    def test_enqueue_after_done_creates_a_new_job(self):
        """A completed job must not suppress a later legitimate change."""
        first = self.db.enqueue_sync(self.uid, "profile", "1", "upsert", {"v": 1})
        self.db.mark_sync_job_done(first["job_id"])
        second = self.db.enqueue_sync(self.uid, "profile", "1", "upsert", {"v": 2})
        self.assertNotEqual(first["job_id"], second["job_id"])
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid)), 1)

    # -- completion & failure -------------------------------------------
    def test_mark_done_removes_job_from_pending(self):
        job = self.db.enqueue_sync(self.uid, "profile", "1", "upsert")["job_id"]
        self.db.mark_sync_job_done(job)
        self.assertEqual(self.db.get_pending_sync_jobs(self.uid), [])
        self.assertEqual(self.db.sync_queue_summary(self.uid), {"done": 1})

    def test_mark_failed_puts_job_into_backoff(self):
        job = self.db.enqueue_sync(self.uid, "shop_buy", "x", "buy")["job_id"]
        self.db.mark_sync_job_failed(job, "network down", 1)

        # Backed-off jobs are deliberately hidden from the normal drain so the
        # engine does not hammer a failing endpoint.
        self.assertEqual(self.db.get_pending_sync_jobs(self.uid), [])
        # ... but they remain visible to the UI inspector and to a forced retry.
        self.assertEqual(len(self.db.get_all_sync_jobs(self.uid)), 1)

        summary = self.db.sync_queue_summary(self.uid)
        self.assertEqual(summary, {"retry": 1})

    def test_failure_records_the_error_message(self):
        job = self.db.enqueue_sync(self.uid, "craft", "y", "craft")["job_id"]
        self.db.mark_sync_job_failed(job, "insufficient_balance", 1)
        samples = self.db.get_sync_failed_samples(self.uid)
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]["err"], "insufficient_balance")
        self.assertEqual(samples[0]["retry_count"], 1)

    def test_error_message_is_truncated(self):
        """§8.3 — never let an unbounded server error string into the local row."""
        job = self.db.enqueue_sync(self.uid, "profile", "1", "upsert")["job_id"]
        self.db.mark_sync_job_failed(job, "x" * 5000, 1)
        samples = self.db.get_sync_failed_samples(self.uid)
        conn = self.ctx.raw()
        try:
            row = conn.execute(
                "SELECT length(last_error) AS n FROM sync_queue WHERE id=?", (job,)
            ).fetchone()
        finally:
            conn.close()
        self.assertLessEqual(row["n"], 1000)
        self.assertEqual(len(samples), 1)

    def test_backoff_grows_with_retry_count(self):
        """Property test: each additional failure waits longer, and is capped."""
        delays = []
        for attempt in range(0, 9):
            conn = self.ctx.raw()
            try:
                conn.execute("DELETE FROM sync_queue")
                conn.commit()
            finally:
                conn.close()
            job = self.db.enqueue_sync(self.uid, "profile", "1", "upsert")["job_id"]
            self.db.mark_sync_job_failed(job, "err", attempt)
            conn = self.ctx.raw()
            try:
                row = conn.execute(
                    "SELECT next_retry_at FROM sync_queue WHERE id=?", (job,)
                ).fetchone()
            finally:
                conn.close()
            delays.append(datetime.fromisoformat(row["next_retry_at"]))

        # Strictly increasing up to the cap, then flat.
        for i in range(1, 6):
            self.assertGreater(delays[i], delays[i - 1], f"backoff did not grow at attempt {i}")
        # M11: di plafon kini ada jitter deterministik per job (+0..20%)
        # supaya job yang gagal bersamaan tidak menyerbu server bersamaan.
        # Yang dipaku sekarang: ketiganya tetap di pita plafon yang sama,
        # bukan lagi detik yang persis sama.
        cap_lo = min(delays[6], delays[7], delays[8])
        cap_hi = max(delays[6], delays[7], delays[8])
        self.assertLessEqual((cap_hi - cap_lo).total_seconds(), 3600 * 0.21,
                             "capped backoff should stay within the jitter band")

    # -- manual retry ----------------------------------------------------
    def test_reset_backoff_makes_jobs_drainable_again(self):
        job = self.db.enqueue_sync(self.uid, "profile", "1", "upsert")["job_id"]
        self.db.mark_sync_job_failed(job, "err", 2)
        self.assertEqual(self.db.get_pending_sync_jobs(self.uid), [])

        result = self.db.reset_sync_backoff(self.uid)
        self.assertEqual(result, {"ok": True, "reset": 1})

        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["status"], "pending")
        self.assertIsNone(jobs[0]["next_retry_at"])

    def test_reset_backoff_reports_zero_when_nothing_is_backed_off(self):
        self.assertEqual(self.db.reset_sync_backoff(self.uid), {"ok": True, "reset": 0})

    # -- housekeeping ----------------------------------------------------
    def test_clear_done_only_removes_completed_jobs(self):
        a = self.db.enqueue_sync(self.uid, "profile", "1", "upsert")["job_id"]
        self.db.enqueue_sync(self.uid, "craft", "2", "craft")
        self.db.mark_sync_job_done(a)

        result = self.db.clear_sync_queue_done(self.uid)
        self.assertEqual(result, {"ok": True, "cleared": 1})

        remaining = self.db.get_all_sync_jobs(self.uid)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["entity_type"], "craft")

    def test_drain_order_is_fifo_by_creation(self):
        for entity in ("alpha", "bravo", "charlie"):
            self.db.enqueue_sync(self.uid, entity, "1", "upsert")
        jobs = self.db.get_pending_sync_jobs(self.uid)
        self.assertEqual([j["entity_type"] for j in jobs], ["alpha", "bravo", "charlie"])

    def test_limit_is_respected(self):
        for i in range(10):
            self.db.enqueue_sync(self.uid, "entity", str(i), "upsert")
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid, limit=3)), 3)

    # -- isolation -------------------------------------------------------
    def test_jobs_are_scoped_per_user(self):
        """A second local account must never see or drain another's queue."""
        other = self.ctx.make_user("otheruser")
        self.db.enqueue_sync(self.uid, "profile", "1", "upsert")

        self.assertEqual(self.db.get_pending_sync_jobs(other), [])
        self.assertEqual(self.db.sync_queue_summary(other), {})
        self.assertEqual(self.db.reset_sync_backoff(other), {"ok": True, "reset": 0})
        self.assertEqual(len(self.db.get_pending_sync_jobs(self.uid)), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
