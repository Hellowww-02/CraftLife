"""M05a — identity layer untuk Rules API.

Sebagian besar tes di sini adalah *vektor serangan*, bukan jalur bahagia.
Fungsi verifikasi JWT hanya berharga kalau ia menolak hal-hal yang seharusnya
ditolak, jadi setiap penolakan dipaku secara eksplisit: alg-confusion, token
kedaluwarsa, secret kosong, signature yang diutak-atik, dan penerbit/audiens
yang salah.

Bagian terakhir memaku satu sifat yang paling mudah hilang tanpa disadari:
identitas harus per-request. `_state["user_id"]` di api_server bersifat global
proses, dan begitu layanan ini melayani dua user sekaligus, global berarti
keduanya saling menimpa.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import unittest

import rules_auth
from rules_auth import AuthError

SECRET = "test-jwt-secret-bukan-rahasia-produksi"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def mint(payload: dict, secret: str = SECRET, *, alg: str = "HS256",
         header_extra: dict | None = None, signature: bytes | None = None,
         drop_segment: bool = False) -> str:
    """Buat JWT untuk pengujian. `signature` bisa dipaksa untuk memalsukan."""
    header = {"alg": alg, "typ": "JWT"}
    if header_extra:
        header.update(header_extra)
    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
    if signature is None:
        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    token = f"{header_b64}.{payload_b64}.{b64url(signature)}"
    return token.rsplit(".", 1)[0] if drop_segment else token


def valid_payload(**overrides) -> dict:
    now = int(time.time())
    base = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "iss": "https://example.supabase.co/auth/v1",
        "aud": "authenticated",
        "iat": now,
        "nbf": now,
        "exp": now + 3600,
        "role": "authenticated",
    }
    base.update(overrides)
    return base


class EnvIsolationMixin:
    """Pastikan konfigurasi env dari lingkungan sekitar tidak membocor ke tes."""

    ENV_KEYS = ("CRAFTLIFE_JWT_SECRET", "SUPABASE_JWT_SECRET", "CRAFTLIFE_JWT_ISSUER",
                "CRAFTLIFE_JWT_AUDIENCE", "CRAFTLIFE_JWT_LEEWAY", "CRAFTLIFE_RULES_API")

    def setUp(self):
        for key in self.ENV_KEYS:
            self.addCleanup(os.environ.pop, key, None)
            os.environ.pop(key, None)
        rules_auth.clear_request_identity()
        self.addCleanup(rules_auth.clear_request_identity)


class ValidTokenTest(EnvIsolationMixin, unittest.TestCase):
    def test_a_well_formed_token_returns_its_claims(self):
        claims = rules_auth.verify_jwt(mint(valid_payload()), SECRET)
        self.assertEqual(claims["sub"], "11111111-1111-1111-1111-111111111111")
        self.assertEqual(claims["role"], "authenticated")

    def test_the_bearer_scheme_is_parsed(self):
        token = mint(valid_payload())
        self.assertEqual(rules_auth.bearer_token(f"Bearer {token}"), token)
        self.assertEqual(rules_auth.bearer_token(f"bearer {token}"), token)

    def test_audience_may_be_a_list(self):
        """RFC 7519 §4.1.3 mengizinkan aud berupa daftar."""
        os.environ["CRAFTLIFE_JWT_AUDIENCE"] = "authenticated"
        claims = rules_auth.verify_jwt(
            mint(valid_payload(aud=["authenticated", "custom"])), SECRET)
        self.assertEqual(claims["sub"], valid_payload()["sub"])


class AttackVectorTest(EnvIsolationMixin, unittest.TestCase):
    """Setiap tes di bawah ini adalah sesuatu yang harus DITOLAK."""

    def assertRejected(self, token: str, code: str, secret: str = SECRET):
        with self.assertRaises(AuthError) as ctx:
            rules_auth.verify_jwt(token, secret)
        self.assertEqual(ctx.exception.code, code)

    def test_a_token_signed_with_a_different_secret_is_rejected(self):
        self.assertRejected(mint(valid_payload(), secret="secret-penyerang"),
                            "invalid_signature")

    def test_a_tampered_payload_is_rejected(self):
        token = mint(valid_payload())
        header, _, sig = token.split(".")
        forged = b64url(json.dumps(valid_payload(sub="22222222-2222-2222-2222-222222222222"),
                                   separators=(",", ":")).encode())
        self.assertRejected(f"{header}.{forged}.{sig}", "invalid_signature")

    def test_alg_none_is_rejected(self):
        """Serangan klasik: buang signature dan nyatakan alg=none."""
        header = b64url(json.dumps({"alg": "none", "typ": "JWT"}, separators=(",", ":")).encode())
        payload = b64url(json.dumps(valid_payload(), separators=(",", ":")).encode())
        self.assertRejected(f"{header}.{payload}.", "unsupported_alg")

    def test_asymmetric_alg_is_rejected_before_the_signature_is_read(self):
        """Alg-confusion: penyerang berharap server memakai key publik sebagai
        secret HMAC. Ditolak di pemeriksaan alg, bukan di perbandingan signature."""
        self.assertRejected(mint(valid_payload(), alg="RS256"), "unsupported_alg")

    def test_hs512_is_rejected_too(self):
        self.assertRejected(mint(valid_payload(), alg="HS512"), "unsupported_alg")

    def test_an_expired_token_is_rejected(self):
        stale = valid_payload(exp=int(time.time()) - 3600, iat=int(time.time()) - 7200)
        self.assertRejected(mint(stale), "token_expired")

    def test_a_token_from_the_future_is_rejected(self):
        future = valid_payload(nbf=int(time.time()) + 3600)
        self.assertRejected(mint(future), "token_not_yet_valid")

    def test_a_token_just_past_expiry_within_leeway_is_still_accepted(self):
        """Leeway ada untuk selisih jam, bukan untuk menghidupkan token lama."""
        os.environ["CRAFTLIFE_JWT_LEEWAY"] = "30"
        edge = valid_payload(exp=int(time.time()) - 5)
        self.assertEqual(rules_auth.verify_jwt(mint(edge), SECRET)["sub"], edge["sub"])

    def test_a_token_without_exp_is_rejected(self):
        payload = valid_payload()
        del payload["exp"]
        self.assertRejected(mint(payload), "missing_exp")

    def test_a_wrong_issuer_is_rejected(self):
        os.environ["CRAFTLIFE_JWT_ISSUER"] = "https://example.supabase.co/auth/v1"
        self.assertRejected(mint(valid_payload(iss="https://penyerang.example/auth/v1")),
                            "invalid_issuer")

    def test_a_wrong_audience_is_rejected(self):
        os.environ["CRAFTLIFE_JWT_AUDIENCE"] = "authenticated"
        self.assertRejected(mint(valid_payload(aud="anon")), "invalid_audience")

    def test_a_token_without_sub_is_rejected(self):
        payload = valid_payload()
        del payload["sub"]
        self.assertRejected(mint(payload), "missing_sub")

    def test_a_two_segment_token_is_rejected(self):
        self.assertRejected(mint(valid_payload(), drop_segment=True), "malformed_token")

    def test_a_header_that_is_not_json_is_rejected(self):
        self.assertRejected(f"{b64url(b'bukan-json')}.e30.abc", "malformed_token")

    def test_an_empty_secret_never_verifies(self):
        """HMAC dengan key kosong tetap menghasilkan signature yang sah, jadi
        secret kosong = siapa pun bisa memalsukan token."""
        forged = mint(valid_payload(), secret="")
        with self.assertRaises(AuthError) as ctx:
            rules_auth.verify_jwt(forged, "")
        self.assertEqual(ctx.exception.code, "jwt_secret_missing")

    def test_a_missing_secret_from_the_environment_is_also_refused(self):
        with self.assertRaises(AuthError) as ctx:
            rules_auth.verify_jwt(mint(valid_payload()))
        self.assertEqual(ctx.exception.code, "jwt_secret_missing")

    def test_error_messages_never_leak_the_secret(self):
        for token in (mint(valid_payload(), secret="lain"), mint(valid_payload(), alg="none")):
            with self.assertRaises(AuthError) as ctx:
                rules_auth.verify_jwt(token, SECRET)
            self.assertNotIn(SECRET, str(ctx.exception))
            self.assertNotIn(SECRET, ctx.exception.detail)


class AuthorizationHeaderTest(EnvIsolationMixin, unittest.TestCase):
    def test_a_missing_header_is_reported_as_missing_token(self):
        with self.assertRaises(AuthError) as ctx:
            rules_auth.authenticate(None)
        self.assertEqual(ctx.exception.code, "token_missing")

    def test_a_non_bearer_scheme_is_not_accepted(self):
        self.assertIsNone(rules_auth.bearer_token("Basic dXNlcjpwYXNz"))

    def test_a_bearer_header_with_no_token_is_not_accepted(self):
        self.assertIsNone(rules_auth.bearer_token("Bearer "))

    def test_a_valid_header_authenticates(self):
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        claims = rules_auth.authenticate(f"Bearer {mint(valid_payload())}")
        self.assertEqual(rules_auth.auth_uid(claims), valid_payload()["sub"])


class LocalUserMappingTest(EnvIsolationMixin, unittest.TestCase):
    def test_a_linked_sub_resolves_to_a_local_uid(self):
        table = {valid_payload()["sub"]: 7}
        self.assertEqual(rules_auth.resolve_local_user(valid_payload(), table.get), 7)

    def test_an_unlinked_sub_resolves_to_none(self):
        """Akun cloud yang belum ditautkan tidak boleh jadi user anonim."""
        self.assertIsNone(rules_auth.resolve_local_user(valid_payload(), lambda _: None))

    def test_a_lookup_that_raises_is_treated_as_unlinked(self):
        def boom(_):
            raise RuntimeError("db mati")
        self.assertIsNone(rules_auth.resolve_local_user(valid_payload(), boom))


class PerRequestIdentityTest(EnvIsolationMixin, unittest.TestCase):
    """Identitas harus per-request, bukan global proses."""

    def test_identity_can_be_set_and_read(self):
        rules_auth.set_request_identity(3, {"sub": "abc"})
        self.assertEqual(rules_auth.current_uid(), 3)
        self.assertEqual(rules_auth.current_claims()["sub"], "abc")

    def test_clearing_removes_it(self):
        rules_auth.set_request_identity(3)
        rules_auth.clear_request_identity()
        self.assertIsNone(rules_auth.current_uid())

    def test_two_threads_do_not_overwrite_each_other(self):
        """Inilah alasan ContextVar dipakai, bukan variabel modul."""
        import threading
        seen = {}
        barrier = threading.Barrier(2)

        def worker(uid):
            rules_auth.set_request_identity(uid)
            barrier.wait(timeout=5)          # pastikan keduanya sudah set
            time.sleep(0.02)                 # beri waktu saling menimpa bila global
            seen[uid] = rules_auth.current_uid()

        threads = [threading.Thread(target=worker, args=(u,)) for u in (1, 2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)
        self.assertEqual(seen, {1: 1, 2: 2},
                         "identitas bocor antar request — ini global, bukan per-request")


class StrictModeTest(EnvIsolationMixin, unittest.TestCase):
    """Strict mati secara default supaya desktop tidak berubah perilaku (P1/P4)."""

    def test_off_when_no_secret_is_configured(self):
        self.assertFalse(rules_auth.is_strict())

    def test_on_when_a_secret_is_configured(self):
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        self.assertTrue(rules_auth.is_strict())

    def test_an_explicit_flag_wins_over_the_secret(self):
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        os.environ["CRAFTLIFE_RULES_API"] = "0"
        self.assertFalse(rules_auth.is_strict())

    def test_an_explicit_flag_can_force_strict_on(self):
        os.environ["CRAFTLIFE_RULES_API"] = "true"
        self.assertTrue(rules_auth.is_strict())

    def test_an_unrecognised_flag_falls_back_to_the_secret(self):
        os.environ["CRAFTLIFE_RULES_API"] = "mungkin"
        self.assertFalse(rules_auth.is_strict())


if __name__ == "__main__":
    unittest.main(verbosity=2)
