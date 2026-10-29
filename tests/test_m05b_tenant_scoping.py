"""M05b — tenant scoping: JWT user A tidak boleh membaca data user B.

Kriteria penerimaan M05 dari roadmap: *"JWT user A → tidak pernah membaca data
user B (test RLS + scoping)"*. M05a sudah memastikan identitas diambil dari
token; tahap ini memastikan identitas itu benar-benar **dipakai** oleh setiap
query di baliknya.

Metodenya empiris, bukan membaca 29 ribu baris. Setiap tabel yang punya kolom
``user_id`` diisi satu baris ber-sentinel unik milik user B, lalu sebagai user A
(setelah JWT diverifikasi) seluruh route GET yang dipakai client web dipanggil
dan badan responsnya dipindai untuk sentinel itu. Route yang membocorkan akan
menunjukkan dirinya sendiri.

Probe ini sudah dibuktikan tidak buta: merusak filter `user_id` di
`get_habits()` membuat tepat dua route terdeteksi bocor (`/api/habits` dan
`/api/bootstrap`), dan memulihkannya mengembalikan nol.

Batasan yang dinyatakan jujur
-----------------------------
1. Hanya route **GET**. Jalur POST/PUT/DELETE belum dipindai di sini.
2. Hanya menangkap data yang muncul **apa adanya** di respons. Route yang
   membocorkan jumlah baris atau id tanpa membawa string sentinel tidak terlihat.
3. Sejumlah tabel tidak bisa diisi otomatis karena FK/CHECK/NOT NULL dan
   karenanya **tidak teruji**. Daftarnya dicetak, bukan disembunyikan, dan
   `MINIMUM_SEEDED_TABLES` mencegah cakupan menyusut tanpa disadari.
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
TAG = "ZZQXSENTINELB"

# Lantai cakupan. Diukur 2026-10-11: 58 tabel terisi oleh seeder generik, plus
# domain yang diisi lewat helper. Kalau angka ini turun, sesuatu telah berubah
# dan harus diselidiki — bukan diam-diam menerima cakupan yang lebih sempit.
MINIMUM_SEEDED_TABLES = 55
MINIMUM_ROUTES = 250


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


def seed_via_helpers(db, uid):
    """Isi domain yang helper-nya tahu bentuk baris yang sah.

    Signature di bawah dibaca dari database.py, bukan dikira-kira — beberapa
    nama yang tampak wajar (`add_economy_transaction`, `add_savings_goal`)
    ternyata tidak ada.
    """
    attempts = [
        ("habits", lambda: db.add_habit(uid, f"{TAG}habit")),
        ("notes", lambda: db.add_note(uid, None, f"{TAG}note", "isi")),
        ("todos", lambda: db.add_todo(uid, f"{TAG}todo")),
        ("recipes", lambda: db.add_recipe(uid, f"{TAG}resep", "🍚", 1, "", [])),
        ("reminders", lambda: db.add_reminder(uid, f"{TAG}reminder", "desc", "2026-12-31 09:00:00")),
        ("economy_items", lambda: db.add_economy_item(
            uid, f"{TAG}tx", "💰", "income", 1000, "lain", "2026-10-11")),
        ("debts", lambda: db.add_debt(uid, f"{TAG}hutang", 5000)),
        ("savings", lambda: db.add_saving(uid, f"{TAG}tabungan", "🎯", 10000, 0, "2026-12-31", "")),
    ]
    done = []
    for label, fn in attempts:
        try:
            fn()
            done.append(label)
        except Exception:
            pass
    return done


def seed_all_user_tables(db, uid):
    """Satu baris ber-sentinel ke setiap tabel ber-`user_id`.

    Mengembalikan (terisi, gagal). Kegagalan dikembalikan, bukan ditelan: tabel
    yang tidak terisi berarti tidak teruji dan harus terlihat di laporan.
    """
    conn = db.get_conn()
    tables = [r["name"] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    filled, failed = [], []
    for table in tables:
        cols = [dict(r) for r in conn.execute(f"PRAGMA table_info({table})")]
        names = [c["name"] for c in cols]
        if "user_id" not in names:
            continue
        columns, values, has_text = ["user_id"], [uid], False
        skip = False
        # food_items bersifat HIBRIDA: is_custom=0 adalah katalog bawaan yang
        # memang dibagikan ke semua orang (1.074 makanan default), is_custom=1
        # adalah milik user. Default kolomnya 0, jadi tanpa override ini baris
        # sentinel masuk sebagai katalog bersama dan `/api/food/items` yang
        # MENGEMBALIKANNYA justru benar — probe-nya yang salah, bukan produknya.
        # "Memperbaiki" query itu akan merusak katalog makanan semua pengguna.
        if table == "food_items" and "is_custom" in names:
            columns.append("is_custom")
            values.append(1)
        for c in cols:
            n, t = c["name"], c["type"].upper()
            if n in ("user_id", "id") or n in columns:
                continue
            # Kolom dengan CHECK tidak bisa ditebak nilainya; lewati tabelnya
            # daripada memasukkan baris yang pasti ditolak.
            if "CHECK" in str(c).upper():
                skip = True
                break
            if c["dflt_value"] is None and c["notnull"]:
                columns.append(n)
                if t.startswith(("INT", "BOOL")):
                    values.append(1)
                elif t.startswith(("REAL", "FLOA", "DOUB", "NUM", "DEC")):
                    values.append(1.0)
                else:
                    values.append(f"{TAG}{n}")
                    has_text = True
            elif t.startswith(("TEXT", "VARCHAR", "CHAR")) and c["dflt_value"] is None:
                columns.append(n)
                values.append(f"{TAG}{n}")
                has_text = True
        if skip:
            failed.append(f"{table}: punya CHECK constraint")
            continue
        if not has_text:
            failed.append(f"{table}: tidak ada kolom teks untuk sentinel")
            continue
        try:
            conn.execute(
                f"INSERT INTO {table}({','.join(columns)}) "
                f"VALUES({','.join(['?'] * len(values))})", values)
            filled.append(table)
        except Exception as exc:
            failed.append(f"{table}: {type(exc).__name__}")
    conn.commit()
    conn.close()
    return filled, failed


class TenantScopingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_api_routes import collect_client_routes
        cls.probed, _prefix, cls.literals = collect_client_routes()

        cls._server = LiveApiServer("m05b_a")
        cls._server.__enter__()
        cls.db = cls._server.db
        cls.base = cls._server.base
        cls.uid_a = cls._server.uid

        # User B adalah korban yang datanya tidak boleh terlihat.
        cls.uid_b = cls._server.ctx.make_user("m05b_b")
        cls.helper_domains = seed_via_helpers(cls.db, cls.uid_b)
        cls.seeded, cls.unseeded = seed_all_user_tables(cls.db, cls.uid_b)

        conn = cls.db.get_conn()
        conn.execute("UPDATE users SET cloud_user_id=? WHERE id=?", (SUB_A, cls.uid_a))
        conn.commit()
        conn.close()

        cls._saved = {k: os.environ.get(k) for k in
                      ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API")}
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        cls.token = make_jwt(SUB_A)

        # Satu kali sapuan, hasilnya dipakai semua tes di bawah.
        cls.leaks, cls.errors, cls.clean = [], [], 0
        for path in sorted(cls.probed):
            req = urllib.request.Request(
                f"{cls.base}{path}",
                headers={"Accept": "application/json",
                         "Authorization": f"Bearer {cls.token}"})
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    body, status = resp.read().decode("utf-8", errors="replace"), resp.status
            except urllib.error.HTTPError as exc:
                body, status = exc.read().decode("utf-8", errors="replace"), exc.code
            except Exception as exc:
                cls.errors.append(f"{path} -> {type(exc).__name__}")
                continue
            if TAG in body:
                cls.leaks.append(path)
            else:
                cls.clean += 1

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._server.__exit__(None, None, None)

    # -- inti kriteria penerimaan ---------------------------------------
    def test_no_route_returns_another_users_data(self):
        self.assertEqual(
            self.leaks, [],
            "route berikut mengembalikan data milik user lain: " + ", ".join(self.leaks))

    # -- cakupan tidak boleh menyusut diam-diam --------------------------
    def test_the_route_scan_found_a_realistic_number_of_routes(self):
        self.assertGreaterEqual(len(self.probed), MINIMUM_ROUTES,
                                "penyapu route menemukan terlalu sedikit — probe-nya yang rusak")

    def test_enough_tables_were_seeded_to_mean_anything(self):
        self.assertGreaterEqual(len(self.seeded), MINIMUM_SEEDED_TABLES,
                                f"hanya {len(self.seeded)} tabel terisi; cakupan menyusut")

    def test_the_helper_domains_were_actually_seeded(self):
        """Tanpa ini, 'nol bocor' bisa berarti 'nol data'."""
        for domain in ("habits", "notes", "todos", "recipes", "economy_items", "debts"):
            self.assertIn(domain, self.helper_domains,
                          f"domain {domain} tidak terisi — kebocorannya tidak akan terlihat")

    def test_every_probed_route_answered(self):
        self.assertEqual(self.errors, [],
                         "route ini error saat dipindai: " + ", ".join(self.errors[:10]))

    def test_the_sentinel_is_actually_in_the_database(self):
        """Bukti bahwa sentinel benar-benar tersimpan untuk user B."""
        conn = self.db.get_conn()
        try:
            row = conn.execute(
                "SELECT name FROM habits WHERE user_id=? AND name LIKE ?",
                (self.uid_b, f"{TAG}%")).fetchone()
        finally:
            conn.close()
        self.assertIsNotNone(row, "sentinel tidak pernah masuk ke database")

    # -- diagnostik yang dicetak, bukan disembunyikan --------------------
    def test_report_untested_tables(self):
        """Bukan kegagalan: laporan tabel yang tidak bisa diuji otomatis."""
        if self.unseeded:
            print(f"\n[M05b] {len(self.unseeded)} tabel tidak teruji karena FK/CHECK/NOT NULL:")
            for entry in self.unseeded:
                print("   ", entry)


if __name__ == "__main__":
    unittest.main(verbosity=2)
