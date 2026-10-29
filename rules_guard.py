"""M05c — penjaga runtime untuk CraftLife Rules API.

Tiga hal yang diukur tidak ada sebelum tahap ini, dan semuanya jadi berbahaya
begitu layanan ini internet-facing (R5):

1. **Rate limiting** — tidak ada sama sekali. Satu client yang loop bisa
   membanjiri server dan, karena setiap request menyentuh SQLite, mengunci
   database untuk semua orang.
2. **Audit logging** — tidak ada. Tanpa jejak, insiden tidak bisa diselidiki.
3. **Debug endpoint** — `/api/admin/debug` memberi XP/gold lewat HTTP, dijaga
   flag `is_admin` lokal. Di desktop itu alat cheat milik pengguna sendiri; di
   layanan multi-tenant itu jalur untuk memberi diri sendiri mata uang.

Prinsip yang sama dengan M05a: semua ini **mati di desktop**. Strict mode
mengikuti `rules_auth.is_strict()`, jadi selama `CRAFTLIFE_JWT_SECRET` tidak
di-set, tidak ada satu pun jalur local-only yang berubah perilaku (P1/P4).

Yang sengaja TIDAK dilakukan
---------------------------
- **Rate limiter ini in-memory, per-proses.** Untuk satu kontainer itu cukup.
  Begitu Rules API dijalankan lebih dari satu replika, batasnya menjadi
  "N × konfigurasi" dan butuh store bersama (Redis/Postgres). Itu keputusan
  deployment (M05e), bukan sesuatu yang boleh dipalsukan di sini.
- **Isi request tidak pernah dicatat.** Body bisa berisi kata sandi, token, dan
  data kesehatan. Yang dicatat hanya method, path, status, dan identitas.
- **User-Agent tidak disimpan mentah**, hanya hash-nya, supaya jejak tetap bisa
  dikorelasikan tanpa menyimpan sidik jari client.
"""
from __future__ import annotations

import hashlib
import os
import threading
import time

from rules_auth import is_strict

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

def rate_limit_rpm() -> int:
    """Request per menit per kunci (user, atau IP bila belum terautentikasi)."""
    return _int_env("CRAFTLIFE_RATE_LIMIT_RPM", 300, minimum=1, maximum=100_000)


def rate_limit_burst() -> int:
    """Ukuran ember: seberapa banyak lonjakan sesaat yang masih diterima."""
    return _int_env("CRAFTLIFE_RATE_LIMIT_BURST", 60, minimum=1, maximum=10_000)


def audit_enabled() -> bool:
    """Audit log menyala bersama strict mode, kecuali dimatikan eksplisit."""
    flag = (os.environ.get("CRAFTLIFE_AUDIT_LOG") or "").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    if flag in ("1", "true", "yes", "on"):
        return True
    return is_strict()


def debug_endpoints_allowed() -> bool:
    """Debug endpoint hanya ada di desktop.

    Di Rules API tidak ada "admin" yang sah: memberi diri sendiri XP/gold lewat
    HTTP bertentangan dengan K9 (nilai ekonomi hanya ditulis server lewat
    reward_ledger), apa pun flag lokal yang diklaim pemanggil.
    """
    return not is_strict()


def expose_internals() -> bool:
    """Bolehkah respons membocorkan detail internal seperti path database?"""
    return not is_strict()


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(minimum, min(int(raw), maximum))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Rate limiting — token bucket
# ---------------------------------------------------------------------------

class RateLimiter:
    """Token bucket per kunci, aman untuk banyak thread.

    Sengaja sederhana dan tanpa dependensi: ember berisi token yang diisi ulang
    secara laju tetap, satu request mengambil satu token. Lonjakan sesaat
    diterima sampai sebesar `burst`, setelah itu ditolak dengan `retry_after`
    yang bisa dipakai client untuk backoff.

    Kunci yang sudah lama tidak dipakai dibuang, supaya tabel tidak tumbuh tanpa
    batas hanya karena banyak IP berbeda pernah mengetuk.
    """

    def __init__(self, rpm: int | None = None, burst: int | None = None,
                 max_keys: int = 20_000):
        self._rpm = rpm if rpm is not None else rate_limit_rpm()
        self._burst = burst if burst is not None else rate_limit_burst()
        self._max_keys = max_keys
        self._refill_per_sec = self._rpm / 60.0
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, *, now: float | None = None,
              cost: float = 1.0) -> tuple[bool, float]:
        """Kembalikan (diizinkan, retry_after_detik)."""
        current = time.monotonic() if now is None else float(now)
        with self._lock:
            self._evict_stale(current)
            bucket = self._buckets.get(key)
            if bucket is None:
                # [token, waktu_terakhir_diisi]
                bucket = [float(self._burst), current]
                self._buckets[key] = bucket

            elapsed = max(0.0, current - bucket[1])
            bucket[0] = min(float(self._burst), bucket[0] + elapsed * self._refill_per_sec)
            bucket[1] = current

            if bucket[0] >= cost:
                bucket[0] -= cost
                return True, 0.0
            shortage = cost - bucket[0]
            return False, shortage / self._refill_per_sec if self._refill_per_sec else 60.0

    def remaining(self, key: str, *, now: float | None = None) -> int:
        """Perkiraan token tersisa, untuk header X-RateLimit-Remaining."""
        current = time.monotonic() if now is None else float(now)
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return int(self._burst)
            elapsed = max(0.0, current - bucket[1])
            return int(min(float(self._burst), bucket[0] + elapsed * self._refill_per_sec))

    def _evict_stale(self, current: float) -> None:
        if len(self._buckets) < self._max_keys:
            return
        # Ember yang sudah penuh tidak menahan informasi apa pun; buang yang
        # paling lama disentuh supaya memori ada batasnya.
        stale = sorted(self._buckets.items(), key=lambda kv: kv[1][1])
        for key, bucket in stale[: max(1, len(self._buckets) // 4)]:
            if min(float(self._burst), bucket[0] +
                   max(0.0, current - bucket[1]) * self._refill_per_sec) >= self._burst - 1e-9:
                del self._buckets[key]


_default_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_limiter() -> RateLimiter:
    global _default_limiter
    with _limiter_lock:
        if _default_limiter is None:
            _default_limiter = RateLimiter()
        return _default_limiter


def reset_limiter() -> None:
    """Untuk tes: buang limiter agar konfigurasi env dibaca ulang."""
    global _default_limiter
    with _limiter_lock:
        _default_limiter = None


def rate_key(uid, ip: str | None) -> str:
    """Kunci batas: identitas user bila ada, kalau tidak alamat IP.

    Memakai IP saja akan menghukum satu kantor NAT secara kolektif; memakai user
    saja membuat request tanpa identitas tidak terbatas sama sekali. Jadi:
    identitas dulu, IP sebagai jaring pengaman.
    """
    if uid:
        return f"u:{uid}"
    return f"ip:{ip or 'unknown'}"


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------

def _hash(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]


def record_audit(db, *, local_user_id, method: str, path: str,
                 status: int, ip: str | None = None,
                 user_agent: str | None = None) -> bool:
    """Tulis satu baris jejak. Tidak pernah melempar ke pemanggil.

    Kegagalan audit tidak boleh membuat request pengguna gagal — tapi juga tidak
    boleh diam: kembalikan False supaya pemanggil bisa menghitungnya.

    Isi request sengaja tidak disimpan. Path dipotong, karena path bisa memuat
    id panjang dan tidak ada nilai dalam menyimpan 4 KB URL di tabel jejak.
    """
    if not audit_enabled():
        return False
    try:
        conn = db.get_conn()
        try:
            conn.execute(
                "INSERT INTO rules_audit_log"
                "(local_user_id, method, path, status, ip, user_agent_hash, created_at) "
                "VALUES(?,?,?,?,?,?,datetime('now'))",
                (int(local_user_id) if local_user_id else None,
                 str(method)[:8], str(path)[:300], int(status),
                 str(ip)[:45] if ip else None, _hash(user_agent)))
            conn.commit()
        finally:
            conn.close()
        return True
    except Exception:
        return False


def recent_audit(db, local_user_id=None, limit: int = 50) -> list[dict]:
    """Baca jejak terbaru — untuk diagnostik operator, bukan untuk client."""
    conn = db.get_conn()
    try:
        if local_user_id is None:
            rows = conn.execute(
                "SELECT * FROM rules_audit_log ORDER BY id DESC LIMIT ?",
                (int(limit),)).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM rules_audit_log WHERE local_user_id=? ORDER BY id DESC LIMIT ?",
                (int(local_user_id), int(limit))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
