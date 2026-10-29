"""M05c — rate limiting, audit logging, dan gerbang debug endpoint.

Dua sifat yang paling mudah salah di sini dan karena itu dipaku secara
eksplisit:

**Rate limiter tidak boleh over-admit di bawah konkurensi.** Bucket yang tidak
thread-safe akan meloloskan lebih banyak request daripada batasnya tepat ketika
beban tinggi — yaitu satu-satunya saat ia dibutuhkan. Ada tes yang menembak dari
banyak thread dan menghitung total yang lolos.

**Audit tidak boleh menyimpan isi request.** Body bisa berisi kata sandi, token,
dan data kesehatan. Itu dipaku secara struktural: tabelnya memang tidak punya
kolom untuk itu, dan tesnya memeriksa skema, bukan hanya perilakunya.
"""
from __future__ import annotations

import os
import threading
import time
import unittest

import rules_guard
from rules_guard import RateLimiter

from tests.harness import TempDatabase


class EnvIsolationMixin:
    KEYS = ("CRAFTLIFE_RATE_LIMIT_RPM", "CRAFTLIFE_RATE_LIMIT_BURST",
            "CRAFTLIFE_AUDIT_LOG", "CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API")

    def setUp(self):
        for key in self.KEYS:
            self.addCleanup(os.environ.pop, key, None)
            os.environ.pop(key, None)
        rules_guard.reset_limiter()
        self.addCleanup(rules_guard.reset_limiter)


class TokenBucketTest(EnvIsolationMixin, unittest.TestCase):
    def test_allows_up_to_the_burst(self):
        limiter = RateLimiter(rpm=60, burst=5)
        self.assertEqual([limiter.allow("k", now=0.0)[0] for _ in range(5)],
                         [True] * 5)

    def test_rejects_once_the_bucket_is_empty(self):
        limiter = RateLimiter(rpm=60, burst=3)
        for _ in range(3):
            limiter.allow("k", now=0.0)
        allowed, retry_after = limiter.allow("k", now=0.0)
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0, "penolakan tanpa retry_after memaksa client menebak")

    def test_the_bucket_refills_at_the_configured_rate(self):
        limiter = RateLimiter(rpm=60, burst=2)      # 1 token/detik
        limiter.allow("k", now=0.0)
        limiter.allow("k", now=0.0)
        self.assertFalse(limiter.allow("k", now=0.0)[0])
        self.assertTrue(limiter.allow("k", now=1.0)[0], "satu detik kemudian harus ada 1 token")

    def test_refill_never_exceeds_the_burst(self):
        limiter = RateLimiter(rpm=6000, burst=4)    # 100 token/detik
        for _ in range(4):
            limiter.allow("k", now=0.0)
        # Setelah sejam penuh, ember tetap tidak boleh melebihi 4.
        self.assertEqual(limiter.remaining("k", now=3600.0), 4)

    def test_retry_after_shrinks_as_time_passes(self):
        limiter = RateLimiter(rpm=60, burst=1)
        limiter.allow("k", now=0.0)
        first = limiter.allow("k", now=0.0)[1]
        later = limiter.allow("k", now=0.5)[1]
        self.assertLess(later, first)

    def test_keys_are_independent(self):
        limiter = RateLimiter(rpm=60, burst=1)
        self.assertTrue(limiter.allow("a", now=0.0)[0])
        self.assertFalse(limiter.allow("a", now=0.0)[0])
        self.assertTrue(limiter.allow("b", now=0.0)[0], "satu user tidak boleh membatasi user lain")

    def test_memory_stays_bounded(self):
        limiter = RateLimiter(rpm=60, burst=2, max_keys=50)
        for i in range(400):
            limiter.allow(f"k{i}", now=float(i))
        self.assertLessEqual(len(limiter._buckets), 400)
        self.assertLess(len(limiter._buckets), 400,
                        "tidak ada satu pun kunci basi yang dibuang")

    def test_concurrent_requests_are_not_over_admitted(self):
        """Bucket tanpa lock akan meloloskan lebih dari batasnya di sini."""
        burst, rpm = 20, 600                     # 20 token, isi 10/detik
        limiter = RateLimiter(rpm=rpm, burst=burst)
        admitted = []
        lock = threading.Lock()
        start = threading.Barrier(16)

        def worker():
            start.wait(timeout=10)
            local = 0
            for _ in range(50):
                if limiter.allow("shared")[0]:
                    local += 1
            with lock:
                admitted.append(local)

        threads = [threading.Thread(target=worker) for _ in range(16)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        total = sum(admitted)
        # 16 × 50 = 800 percobaan dalam <1 detik: yang lolos tidak boleh jauh
        # melebihi burst + sedikit isi ulang.
        self.assertLessEqual(total, burst + 20,
                             f"{total} request lolos dari ember berukuran {burst} — limiter bocor")
        self.assertGreater(total, 0)


class ConfigTest(EnvIsolationMixin, unittest.TestCase):
    def test_defaults(self):
        self.assertEqual(rules_guard.rate_limit_rpm(), 300)
        self.assertEqual(rules_guard.rate_limit_burst(), 60)

    def test_environment_overrides(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "120"
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "10"
        self.assertEqual(rules_guard.rate_limit_rpm(), 120)
        self.assertEqual(rules_guard.rate_limit_burst(), 10)

    def test_a_garbage_value_falls_back_rather_than_crashing(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "banyak"
        self.assertEqual(rules_guard.rate_limit_rpm(), 300)

    def test_an_absurd_value_is_clamped(self):
        """Batas 0 akan mengunci semua orang; batas jutaan tidak membatasi apa pun."""
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "0"
        self.assertEqual(rules_guard.rate_limit_rpm(), 1)
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "999999999"
        self.assertEqual(rules_guard.rate_limit_rpm(), 100_000)

    def test_rate_key_prefers_identity_over_ip(self):
        self.assertEqual(rules_guard.rate_key(7, "10.0.0.1"), "u:7")
        self.assertEqual(rules_guard.rate_key(None, "10.0.0.1"), "ip:10.0.0.1")
        self.assertEqual(rules_guard.rate_key(None, None), "ip:unknown")


class PolicyGateTest(EnvIsolationMixin, unittest.TestCase):
    """Semua penjaga mati di desktop (P1/P4), nyala di Rules API."""

    def test_debug_endpoints_allowed_on_desktop(self):
        self.assertTrue(rules_guard.debug_endpoints_allowed())

    def test_debug_endpoints_blocked_in_strict_mode(self):
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        self.assertFalse(rules_guard.debug_endpoints_allowed())

    def test_internals_hidden_in_strict_mode(self):
        self.assertTrue(rules_guard.expose_internals())
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        self.assertFalse(rules_guard.expose_internals())

    def test_audit_follows_strict_mode(self):
        self.assertFalse(rules_guard.audit_enabled())
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        self.assertTrue(rules_guard.audit_enabled())

    def test_audit_can_be_forced_off(self):
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "0"
        self.assertFalse(rules_guard.audit_enabled())


class AuditLogTest(EnvIsolationMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("m05c")

    def test_the_table_exists_after_init_db(self):
        names = {r["name"] for r in self.ctx.raw().execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertIn("rules_audit_log", names)

    def test_nothing_is_recorded_while_audit_is_off(self):
        self.assertFalse(rules_guard.record_audit(
            self.db, local_user_id=self.uid, method="POST", path="/api/x", status=200))
        self.assertEqual(rules_guard.recent_audit(self.db), [])

    def test_a_request_is_recorded_when_audit_is_on(self):
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        self.assertTrue(rules_guard.record_audit(
            self.db, local_user_id=self.uid, method="POST", path="/api/habits",
            status=201, ip="10.0.0.9", user_agent="CraftLifeDesktop/1.7.4"))
        rows = rules_guard.recent_audit(self.db)
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["method"], rows[0]["path"], rows[0]["status"]),
                         ("POST", "/api/habits", 201))

    def test_a_rejected_anonymous_request_is_still_recorded(self):
        """Justru yang paling perlu tercatat: siapa yang ditolak, dan dari mana."""
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        rules_guard.record_audit(self.db, local_user_id=None, method="GET",
                                 path="/api/habits", status=401, ip="203.0.113.7")
        rows = rules_guard.recent_audit(self.db)
        self.assertIsNone(rows[0]["local_user_id"])
        self.assertEqual(rows[0]["status"], 401)

    def test_the_user_agent_is_hashed_not_stored(self):
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        rules_guard.record_audit(self.db, local_user_id=self.uid, method="GET",
                                 path="/api/x", status=200, user_agent="Mozilla/5.0 rahasia")
        row = rules_guard.recent_audit(self.db)[0]
        self.assertNotIn("Mozilla", str(row["user_agent_hash"]))
        self.assertEqual(len(row["user_agent_hash"]), 16)

    def test_the_schema_has_no_column_for_a_request_body(self):
        """Dipaku secara struktural: tidak ada tempat untuk menaruh body."""
        cols = {r["name"] for r in self.ctx.raw().execute(
            "PRAGMA table_info(rules_audit_log)")}
        for forbidden in ("body", "payload", "request_body", "content", "data"):
            self.assertNotIn(forbidden, cols)

    def test_an_overlong_path_is_truncated_not_rejected(self):
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        rules_guard.record_audit(self.db, local_user_id=self.uid, method="GET",
                                 path="/api/" + "x" * 5000, status=200)
        self.assertLessEqual(len(rules_guard.recent_audit(self.db)[0]["path"]), 300)

    def test_a_broken_database_returns_false_instead_of_raising(self):
        """Kegagalan audit tidak boleh membuat request pengguna gagal."""
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"

        class Broken:
            def get_conn(self):
                raise RuntimeError("db mati")

        self.assertFalse(rules_guard.record_audit(
            Broken(), local_user_id=1, method="GET", path="/x", status=200))

    def test_recent_audit_can_be_scoped_to_one_user(self):
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        other = self.ctx.make_user("m05c_other")
        rules_guard.record_audit(self.db, local_user_id=self.uid, method="GET",
                                 path="/api/a", status=200)
        rules_guard.record_audit(self.db, local_user_id=other, method="GET",
                                 path="/api/b", status=200)
        self.assertEqual(len(rules_guard.recent_audit(self.db, self.uid)), 1)
        self.assertEqual(rules_guard.recent_audit(self.db, self.uid)[0]["path"], "/api/a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
