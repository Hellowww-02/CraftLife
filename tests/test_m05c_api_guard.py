"""M05c — rate limiting, audit logging, dan debug endpoint diuji lewat socket.

Unit test di `test_m05c_rules_guard.py` membuktikan komponen-komponennya benar.
Yang diuji di sini adalah **sambungannya**: bahwa limiter benar-benar dipasang
sebelum auth, bahwa jejak benar-benar tertulis untuk operasi mutating, dan bahwa
debug endpoint benar-benar hilang di Rules API sementara tetap ada di desktop.

Yang terakhir itu penting dua arah. "Tidak ada debug endpoint" saja tidak cukup
— kalau desktop ikut kehilangannya, itu regresi P4 terhadap aplikasi yang
sedang dikirim.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import unittest
import urllib.error
import urllib.request

import rules_guard
from tests.harness import LiveApiServer

SECRET = "test-jwt-secret-bukan-rahasia-produksi"
SUB_A = "aaaaaaaa-0000-0000-0000-0000000000c1"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_jwt(sub: str) -> str:
    now = int(time.time())
    payload = {"sub": sub, "aud": "authenticated", "iat": now, "nbf": now,
               "exp": now + 3600, "role": "authenticated"}
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{b64url(sig)}"


class GuardedApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("m05c_guard")
        cls._server.__enter__()
        cls.db = cls._server.db
        cls.base = cls._server.base
        cls.uid = cls._server.uid
        conn = cls.db.get_conn()
        conn.execute("UPDATE users SET cloud_user_id=? WHERE id=?", (SUB_A, cls.uid))
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (cls.uid,))
        conn.commit()
        conn.close()
        cls._saved = {k: os.environ.get(k) for k in
                      ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API",
                       "CRAFTLIFE_RATE_LIMIT_RPM", "CRAFTLIFE_RATE_LIMIT_BURST",
                       "CRAFTLIFE_AUDIT_LOG")}

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        rules_guard.reset_limiter()
        cls._server.__exit__(None, None, None)

    def setUp(self):
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        os.environ["CRAFTLIFE_AUDIT_LOG"] = "1"
        rules_guard.reset_limiter()

    def tearDown(self):
        for key in ("CRAFTLIFE_RULES_API", "CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_AUDIT_LOG",
                    "CRAFTLIFE_RATE_LIMIT_RPM", "CRAFTLIFE_RATE_LIMIT_BURST"):
            os.environ.pop(key, None)
        rules_guard.reset_limiter()

    def request(self, path, token=None, method="GET", body=None):
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(f"{self.base}{path}", headers=headers,
                                     data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, json.loads(resp.read().decode()), dict(resp.headers)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                parsed = None
            return exc.code, parsed, dict(exc.headers)

    # -- rate limiting ---------------------------------------------------
    def test_exceeding_the_limit_returns_429_with_retry_after(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "60"
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "3"
        rules_guard.reset_limiter()
        token = make_jwt(SUB_A)
        codes = [self.request("/api/habits", token)[0] for _ in range(8)]
        self.assertIn(429, codes, f"tidak ada satu pun 429; kode: {codes}")
        # Header Retry-After harus ada supaya client bisa backoff, bukan menebak.
        for _ in range(8):
            status, _body, headers = self.request("/api/habits", token)
            if status == 429:
                self.assertIn("Retry-After", headers)
                break
        else:
            self.fail("429 kedua tidak tercapai")

    def test_an_unauthenticated_flood_is_also_limited(self):
        """Batas dipasang sebelum auth: tanpa identitas pun tetap dibatasi."""
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "60"
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "2"
        rules_guard.reset_limiter()
        # Bukan /api/health: route itu sengaja dikecualikan dari batas.
        codes = [self.request("/api/habits")[0] for _ in range(6)]
        self.assertIn(429, codes, f"flood tanpa identitas tidak dibatasi; kode: {codes}")

    def test_health_is_never_rate_limited(self):
        """/api/health dipakai smoke test; kalau ikut dibatasi, pemantau
        akan menyimpulkan layanan mati justru saat layanan sedang sibuk."""
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "60"
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1"
        rules_guard.reset_limiter()
        codes = [self.request("/api/health")[0] for _ in range(6)]
        self.assertNotIn(429, codes)

    # -- information disclosure -----------------------------------------
    def test_the_database_path_is_not_disclosed_in_strict_mode(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        status, body, _h = self.request("/api/version", make_jwt(SUB_A))
        self.assertEqual(status, 200, body)
        self.assertNotIn("dbPath", body or {},
                         "path absolut database bocor ke client internet-facing")
        # M14: dulu mengunci literal "1.7.4" — maksud test ini adalah
        # "versi yang dilaporkan server == APP_VERSION resmi", jadi baca
        # dari updater, jangan kunci angka rilisnya.
        import updater as _updater
        self.assertEqual(body.get("version"), _updater.APP_VERSION)

    # -- debug endpoint --------------------------------------------------
    def test_the_debug_endpoint_is_gone_in_strict_mode(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        token = make_jwt(SUB_A)
        status, _body, _h = self.request("/api/admin/debug", token, method="POST",
                                         body={"action": "add_gold", "amount": 99999})
        self.assertEqual(status, 404,
                         "debug endpoint masih hidup di Rules API — admin bisa "
                         "memberi diri sendiri gold lewat HTTP")

    # -- audit log -------------------------------------------------------
    def test_a_mutating_request_is_audited(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        token = make_jwt(SUB_A)
        self.request("/api/habits", token, method="POST", body={"name": "Jejak"})
        rows = rules_guard.recent_audit(self.db, self.uid)
        self.assertTrue(any(r["method"] == "POST" for r in rows),
                        f"POST tidak tercatat; jejak: {rows}")

    def test_an_unauthorised_request_is_audited(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        self.request("/api/habits")            # tanpa token -> 401
        rows = rules_guard.recent_audit(self.db)
        self.assertTrue(any(r["status"] == 401 for r in rows),
                        f"401 tidak tercatat; jejak: {rows}")

    def test_a_successful_get_is_not_audited(self):
        """Mencatat setiap GET yang berhasil akan menenggelamkan jejak yang
        justru penting, dan mengubah tabel jejak jadi salinan access log."""
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        conn = self.db.get_conn()
        conn.execute("DELETE FROM rules_audit_log")
        conn.commit()
        conn.close()
        token = make_jwt(SUB_A)
        self.request("/api/habits", token)
        self.assertEqual(rules_guard.recent_audit(self.db, self.uid), [])

    def test_the_audit_trail_never_contains_a_request_body(self):
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1000"
        rules_guard.reset_limiter()
        token = make_jwt(SUB_A)
        secret_value = "ZZSECRETBODYVALUE"
        self.request("/api/habits", token, method="POST",
                     body={"name": secret_value, "notes": secret_value})
        conn = self.db.get_conn()
        try:
            blob = " ".join(str(dict(r)) for r in conn.execute("SELECT * FROM rules_audit_log"))
        finally:
            conn.close()
        self.assertNotIn(secret_value, blob)


class DesktopUnaffectedTest(unittest.TestCase):
    """P4: semua penjaga ini tidak boleh menyentuh desktop."""

    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("m05c_desktop")
        cls._server.__enter__()
        cls.db = cls._server.db
        cls.base = cls._server.base
        cls.uid = cls._server.uid
        conn = cls.db.get_conn()
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (cls.uid,))
        conn.commit()
        conn.close()
        cls._saved = {k: os.environ.get(k) for k in
                      ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API", "CRAFTLIFE_AUDIT_LOG",
                       "CRAFTLIFE_RATE_LIMIT_RPM", "CRAFTLIFE_RATE_LIMIT_BURST")}

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        rules_guard.reset_limiter()
        cls._server.__exit__(None, None, None)

    def setUp(self):
        os.environ.pop("CRAFTLIFE_JWT_SECRET", None)
        os.environ["CRAFTLIFE_RULES_API"] = "0"
        os.environ["CRAFTLIFE_RATE_LIMIT_RPM"] = "60"
        os.environ["CRAFTLIFE_RATE_LIMIT_BURST"] = "1"
        rules_guard.reset_limiter()

    def tearDown(self):
        for key in ("CRAFTLIFE_RULES_API", "CRAFTLIFE_RATE_LIMIT_RPM",
                    "CRAFTLIFE_RATE_LIMIT_BURST"):
            os.environ.pop(key, None)
        rules_guard.reset_limiter()

    def get(self, path, method="GET", body=None):
        headers = {"Accept": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        if data:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(f"{self.base}{path}", headers=headers,
                                     data=data, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                return exc.code, json.loads(raw)
            except (ValueError, TypeError):
                return exc.code, None

    def test_no_request_is_rate_limited_on_desktop(self):
        codes = [self.get("/api/habits")[0] for _ in range(10)]
        self.assertNotIn(429, codes, f"desktop terkena rate limit; kode: {codes}")

    def test_the_database_path_is_still_shown_on_desktop(self):
        status, body = self.get("/api/version")
        self.assertEqual(status, 200)
        self.assertIn("dbPath", body or {},
                      "desktop kehilangan dbPath yang selama ini dipakai pengguna")

    def test_the_debug_endpoint_still_works_on_desktop(self):
        status, body = self.get("/api/admin/debug", method="POST",
                                body={"action": "add_gold", "amount": 10})
        self.assertNotEqual(status, 404,
                            f"debug endpoint hilang di desktop; body: {body}")

    def test_nothing_is_written_to_the_audit_log_on_desktop(self):
        self.get("/api/habits", method="POST", body={"name": "Desktop"})
        self.assertEqual(rules_guard.recent_audit(self.db), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
