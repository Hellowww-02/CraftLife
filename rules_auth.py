"""M05a — identity layer untuk CraftLife Rules API.

Kenapa modul ini ada
--------------------
Sebelum M05, `api_server._auth_ok()` menerima sebuah token string yang
dibandingkan dengan token proses, dan `_ensure_user()` mengambil *user pertama
di tabel* bila tidak ada yang dikonfigurasi:

    if token and given and given != token:
        return False
    return True

Untuk aplikasi desktop satu pengguna di loopback itu masuk akal. Untuk layanan
multi-tenant yang internet-facing (K16) itu berarti: tanpa header apa pun,
sebuah request tetap dilayani sebagai user #1.

Modul ini menambahkan dua hal yang tidak bisa ditawar untuk multi-tenant:

1. **Verifikasi JWT yang sebenarnya** — signature, `exp`, `nbf`, `iss`, `aud`,
   dan penolakan tegas terhadap alg-confusion (`alg: none`, atau menukar HS256
   dengan algoritma asimetris supaya "secret"-nya jadi key publik).
2. **Identitas per-request**, bukan per-proses. `contextvars` dipakai supaya dua
   request dari dua user berbeda di thread/async yang sama tidak saling
   menimpa.

Yang sengaja TIDAK berubah
--------------------------
Desktop tetap 100% in-process dan local-only (P1). Strict mode **mati secara
default**; ia hanya aktif bila secret JWT dikonfigurasi. Selama secret tidak
di-set, tidak ada satu pun jalur desktop yang berubah perilaku (P4).

Batasan yang harus dinyatakan jujur
-----------------------------------
Hanya HS256 yang didukung, karena itu satu-satunya yang bisa diverifikasi
dengan pustaka standar (§8 melarang dependensi baru). Proyek Supabase baru
memakai kunci asimetris (ES256/RS256 via JWKS); memverifikasinya butuh
kriptografi kurva eliptik yang tidak ada di stdlib. Kalau secret proyek Anda
asimetris, modul ini akan menolaknya dengan kode `unsupported_alg` — bukan
menerimanya diam-diam.
"""
from __future__ import annotations

import base64
import contextvars
import hashlib
import hmac
import json
import os
import time
from typing import Any

# Identitas user lokal untuk request yang sedang berjalan. Sengaja ContextVar,
# bukan variabel modul: `_state["user_id"]` di api_server bersifat global proses
# dan akan membuat dua user saling menimpa begitu layanan ini multi-tenant.
_current_uid: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "craftlife_current_uid", default=None)

# Klaim JWT mentah, untuk audit logging (M05c) dan pemetaan device.
_current_claims: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "craftlife_current_claims", default=None)

SUPPORTED_ALG = "HS256"


class AuthError(Exception):
    """Kegagalan autentikasi dengan kode stabil yang bisa dipetakan ke i18n.

    Pesan sengaja tidak pernah memuat secret, signature, atau isi token: string
    ini bisa berakhir di log atau di badan respons.
    """

    def __init__(self, code: str, detail: str = ""):
        super().__init__(code)
        self.code = code
        self.detail = detail[:200]


# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

def jwt_secret() -> str | None:
    """Secret JWT Supabase (Settings → API → JWT Secret).

    Hanya dibaca dari lingkungan. Tidak pernah dari file yang ter-commit, dan
    tidak pernah punya nilai bawaan — secret dengan nilai bawaan adalah secret
    yang bocor.
    """
    value = os.environ.get("CRAFTLIFE_JWT_SECRET") or os.environ.get("SUPABASE_JWT_SECRET")
    return value.strip() if value and value.strip() else None


def jwt_issuer() -> str | None:
    return os.environ.get("CRAFTLIFE_JWT_ISSUER") or None


def jwt_audience() -> str | None:
    # Supabase memakai "authenticated" sebagai aud untuk token user login.
    return os.environ.get("CRAFTLIFE_JWT_AUDIENCE") or None


def clock_skew_seconds() -> int:
    """Toleransi selisih jam antara server dan Supabase, dalam detik."""
    raw = os.environ.get("CRAFTLIFE_JWT_LEEWAY", "30")
    try:
        return max(0, min(int(raw), 300))
    except (TypeError, ValueError):
        return 30


def is_strict() -> bool:
    """True bila layanan ini berjalan sebagai Rules API multi-tenant.

    Strict ON  → request tanpa JWT valid ditolak 401.
    Strict OFF → perilaku desktop lama, tidak berubah sedikit pun (P1/P4).
    """
    flag = (os.environ.get("CRAFTLIFE_RULES_API") or "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if flag in ("0", "false", "no", "off"):
        return False
    # Tidak dinyatakan eksplisit: strict mengikuti ada/tidaknya secret. Tanpa
    # secret tidak ada yang bisa diverifikasi, jadi memaksa strict hanya akan
    # mengunci semua orang di luar.
    return jwt_secret() is not None


# ---------------------------------------------------------------------------
# Verifikasi token
# ---------------------------------------------------------------------------

def _b64url_decode(segment: str) -> bytes:
    """Decode base64url tanpa padding, seperti yang dipakai JWT."""
    padding = "=" * (-len(segment) % 4)
    try:
        return base64.urlsafe_b64decode(segment + padding)
    except (ValueError, TypeError) as exc:
        raise AuthError("malformed_token", "base64url segment tidak valid") from exc


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def verify_jwt(token: str, secret: str | None = None, *,
               now: float | None = None) -> dict[str, Any]:
    """Verifikasi sebuah JWT HS256 dan kembalikan klaimnya.

    Melempar ``AuthError`` dengan kode stabil bila token tidak sah. Fungsi ini
    murni: tidak menyentuh database, tidak menulis state, sehingga seluruh
    permukaan keamanannya bisa diuji tanpa harness.
    """
    if secret is None:
        secret = jwt_secret()
    if not secret:
        # Jangan pernah memverifikasi dengan secret kosong: HMAC dengan key ""
        # tetap menghasilkan signature yang valid dan bisa dipalsukan siapa pun.
        raise AuthError("jwt_secret_missing", "server tidak dikonfigurasi untuk memverifikasi JWT")
    if not token or not isinstance(token, str):
        raise AuthError("token_missing")

    parts = token.split(".")
    if len(parts) != 3:
        raise AuthError("malformed_token", "JWT harus terdiri dari 3 segmen")
    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(_b64url_decode(header_b64))
    except (ValueError, TypeError) as exc:
        raise AuthError("malformed_token", "header bukan JSON") from exc
    if not isinstance(header, dict):
        raise AuthError("malformed_token", "header bukan objek")

    # Alg-confusion adalah serangan utama pada JWT. Hanya HS256 yang diterima;
    # "none" dan seluruh algoritma asimetris ditolak di sini, sebelum signature
    # disentuh, supaya tidak ada jalur yang membandingkannya dengan key publik.
    alg = header.get("alg")
    if alg != SUPPORTED_ALG:
        raise AuthError("unsupported_alg", f"algoritma yang diterima hanya {SUPPORTED_ALG}")
    if "typ" in header and str(header["typ"]).lower() not in ("jwt", ""):
        raise AuthError("unsupported_typ")

    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    try:
        provided = _b64url_decode(signature_b64)
    except AuthError:
        raise AuthError("invalid_signature")
    # Perbandingan waktu-konstan: `==` pada bytes bocor lewat waktu respons.
    if not hmac.compare_digest(expected, provided):
        raise AuthError("invalid_signature")

    try:
        claims = json.loads(_b64url_decode(payload_b64))
    except (ValueError, TypeError) as exc:
        raise AuthError("malformed_token", "payload bukan JSON") from exc
    if not isinstance(claims, dict):
        raise AuthError("malformed_token", "payload bukan objek")

    current = time.time() if now is None else float(now)
    leeway = clock_skew_seconds()

    exp = claims.get("exp")
    if exp is None:
        raise AuthError("missing_exp", "token tanpa kedaluwarsa tidak diterima")
    try:
        if current > float(exp) + leeway:
            raise AuthError("token_expired")
    except (TypeError, ValueError) as exc:
        raise AuthError("malformed_token", "exp bukan angka") from exc

    nbf = claims.get("nbf")
    if nbf is not None:
        try:
            if current + leeway < float(nbf):
                raise AuthError("token_not_yet_valid")
        except (TypeError, ValueError) as exc:
            raise AuthError("malformed_token", "nbf bukan angka") from exc

    issuer = jwt_issuer()
    if issuer and claims.get("iss") != issuer:
        raise AuthError("invalid_issuer")

    audience = jwt_audience()
    if audience:
        aud = claims.get("aud")
        # `aud` boleh string atau daftar string (RFC 7519 §4.1.3).
        ok = aud == audience or (isinstance(aud, list) and audience in aud)
        if not ok:
            raise AuthError("invalid_audience")

    if not claims.get("sub"):
        raise AuthError("missing_sub", "token tanpa subjek tidak bisa dipetakan ke user")

    return claims


def bearer_token(authorization_header: str | None) -> str | None:
    """Ambil token dari header Authorization. Hanya skema Bearer yang diterima."""
    if not authorization_header:
        return None
    scheme, _, rest = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not rest.strip():
        return None
    return rest.strip()


# ---------------------------------------------------------------------------
# Identitas per-request
# ---------------------------------------------------------------------------

def set_request_identity(uid: int | None, claims: dict | None = None) -> None:
    _current_uid.set(uid)
    _current_claims.set(claims)


def current_uid() -> int | None:
    return _current_uid.get()


def current_claims() -> dict | None:
    return _current_claims.get()


def clear_request_identity() -> None:
    _current_uid.set(None)
    _current_claims.set(None)


def authenticate(authorization_header: str | None) -> dict[str, Any]:
    """Titik masuk untuk satu request. Kembalikan klaim, atau lempar AuthError.

    Sengaja tidak menelan exception: pemanggil yang memutuskan apakah sebuah
    kegagalan jadi 401 (strict) atau diabaikan (desktop local-only).
    """
    token = bearer_token(authorization_header)
    if not token:
        raise AuthError("token_missing", "header Authorization: Bearer <jwt> wajib diisi")
    claims = verify_jwt(token)
    return claims


def auth_uid(claims: dict) -> str:
    """UUID auth Supabase (`sub`) — kunci untuk memetakan ke user lokal."""
    return str(claims.get("sub") or "")


def resolve_local_user(claims: dict, lookup=None) -> int | None:
    """Petakan `sub` JWT ke id user lokal (integer).

    ``lookup`` disuntikkan supaya fungsi ini tetap murni dan bisa diuji tanpa
    database. Default-nya membaca `users.cloud_user_id`, yaitu kolom yang sudah
    dipakai `get_local_user_id_for_cloud()`.

    Mengembalikan None bila akun cloud itu belum pernah ditautkan ke akun lokal
    — pemanggil yang memutuskan apakah itu 401 (strict) atau ditolak.
    """
    sub = auth_uid(claims)
    if not sub:
        return None
    if lookup is None:
        import database as db
        lookup = db.get_local_user_id_for_cloud
    try:
        uid = lookup(sub)
    except Exception:
        return None
    return int(uid) if uid is not None else None

