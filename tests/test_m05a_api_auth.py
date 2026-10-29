"""M05a — kriteria penerimaan Rules API diuji terhadap server yang benar-benar hidup.

Roadmap M05 menuntut: *"Route tanpa JWT valid → 401"* dan *"JWT user A → tidak
pernah membaca data user B"*. Keduanya diuji di sini lewat socket sungguhan,
bukan dengan memanggil fungsinya langsung — karena yang berisiko salah justru
sambungan antara verifier dan dispatcher, bukan verifier-nya.

Yang sama pentingnya: bagian terakhir memaku bahwa **mode desktop tidak berubah
sama sekali** saat strict mati (P1/P4). Tanpa tes itu, "menambah auth" bisa
diam-diam berarti "merusak aplikasi yang sedang dikirim".
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

from tests.harness import LiveApiServer

SECRET = "test-jwt-secret-bukan-rahasia-produksi"
SUB_A = "aaaaaaaa-0000-0000-0000-0000000000a1"
SUB_B = "bbbbbbbb-0000-0000-0000-0000000000b2"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def make_jwt(sub: str, secret: str = SECRET, **overrides) -> str:
    now = int(time.time())
    payload = {"sub": sub, "iss": "https://example.supabase.co/auth/v1",
               "aud": "authenticated", "iat": now, "nbf": now, "exp": now + 3600,
               "role": "authenticated"}
    payload.update(overrides)
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    return f"{header}.{body}.{b64url(sig)}"


class RulesApiAuthTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("m05a")
        cls._server.__enter__()
        cls.api = cls._server.api
        cls.db = cls._server.db
        cls.base = cls._server.base
        cls.uid_a = cls._server.uid

        # User kedua, untuk membuktikan token A tidak bisa membaca data B.
        cls.uid_b = cls._server.ctx.make_user("m05a_other")
        cls.db.add_habit(cls.uid_b, "Habit Milik B")

        # Tautkan akun cloud ke akun lokal — inilah yang dilakukan sign-in.
        conn = cls.db.get_conn()
        conn.execute("UPDATE users SET cloud_user_id=? WHERE id=?", (SUB_A, cls.uid_a))
        conn.commit()
        conn.close()

        cls._saved_env = {k: os.environ.get(k) for k in
                          ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API")}

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._server.__exit__(None, None, None)

    def setUp(self):
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        os.environ["CRAFTLIFE_RULES_API"] = "1"

    def tearDown(self):
        os.environ.pop("CRAFTLIFE_RULES_API", None)
        os.environ.pop("CRAFTLIFE_JWT_SECRET", None)

    def get(self, path: str, token: str | None = None):
        headers = {"Accept": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(f"{self.base}{path}", headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            try:
                return exc.code, json.loads(body)
            except (ValueError, TypeError):
                return exc.code, None

    # -- kriteria penerimaan: tanpa JWT valid → 401 ---------------------
    def test_a_route_without_any_token_is_401(self):
        status, body = self.get("/api/me")
        self.assertEqual(status, 401, body)
        self.assertFalse((body or {}).get("ok", True))

    def test_a_garbage_token_is_401(self):
        status, _ = self.get("/api/me", token="bukan.jwt.asli")
        self.assertEqual(status, 401)

    def test_a_token_signed_with_the_wrong_secret_is_401(self):
        status, _ = self.get("/api/me", token=make_jwt(SUB_A, secret="secret-penyerang"))
        self.assertEqual(status, 401)

    def test_an_expired_token_is_401(self):
        stale = make_jwt(SUB_A, exp=int(time.time()) - 3600)
        status, _ = self.get("/api/me", stale)
        self.assertEqual(status, 401)

    def test_a_valid_token_for_an_unlinked_cloud_account_is_401(self):
        """SUB_B sah secara kriptografis tapi tidak tertaut ke akun lokal mana pun.
        Jatuh ke user pertama di sini = kebocoran lintas-tenant."""
        status, _ = self.get("/api/me", make_jwt(SUB_B))
        self.assertEqual(status, 401)

    def test_a_valid_linked_token_is_accepted(self):
        status, body = self.get("/api/me", make_jwt(SUB_A))
        self.assertEqual(status, 200, body)
        self.assertTrue((body or {}).get("ok", False))

    # -- kriteria penerimaan: A tidak pernah membaca data B -------------
    def test_user_a_never_sees_user_b_habits(self):
        status, body = self.get("/api/habits", make_jwt(SUB_A))
        self.assertEqual(status, 200, body)
        names = [h.get("title") for h in (body or {}).get("habits", [])]
        self.assertNotIn("Habit Milik B", names,
                         "token user A mengembalikan habit user B — scoping bocor")

    def test_the_identity_is_the_token_subject_not_the_first_user(self):
        status, body = self.get("/api/me", make_jwt(SUB_A))
        self.assertEqual(status, 200)
        user = (body or {}).get("user") or {}
        self.assertEqual(str(user.get("id")), str(self.uid_a))

    # -- health tetap publik -------------------------------------------
    def test_health_stays_public_in_strict_mode(self):
        status, body = self.get("/api/health")
        self.assertEqual(status, 200, body)


class DesktopUnchangedTest(unittest.TestCase):
    """P1/P4: strict mati → tidak ada satu pun jalur desktop yang berubah."""

    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("m05a_desktop")
        cls._server.__enter__()
        cls.base = cls._server.base
        cls.uid = cls._server.uid
        cls.db = cls._server.db
        cls.db.add_habit(cls.uid, "Habit Desktop")
        cls._saved = {k: os.environ.get(k) for k in
                      ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API")}

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._server.__exit__(None, None, None)

    def setUp(self):
        # Mode desktop: tidak ada secret, strict dimatikan eksplisit.
        os.environ.pop("CRAFTLIFE_JWT_SECRET", None)
        os.environ["CRAFTLIFE_RULES_API"] = "0"

    def tearDown(self):
        os.environ.pop("CRAFTLIFE_RULES_API", None)

    def get(self, path: str):
        req = urllib.request.Request(f"{self.base}{path}", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            return exc.code, None

    def test_a_request_without_any_token_still_works(self):
        """Inilah perilaku desktop yang harus dipertahankan: loopback, satu user."""
        status, body = self.get("/api/habits")
        self.assertEqual(status, 200, body)

    def test_the_local_habit_is_still_visible(self):
        status, body = self.get("/api/habits")
        names = [h.get("title") for h in (body or {}).get("habits", [])]
        self.assertIn("Habit Desktop", names)

    def test_health_still_works(self):
        status, _ = self.get("/api/health")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
