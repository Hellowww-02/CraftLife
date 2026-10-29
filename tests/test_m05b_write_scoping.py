"""M05b-II — tenant isolation untuk jalur TULIS (POST).

Sapuan M05b asli membuktikan JWT user A tidak pernah **membaca** data user B,
tapi hanya untuk route GET — file itu sendiri menyatakan batasnya: *"Hanya
route GET. Jalur POST/PUT/DELETE belum dipindai di sini."* Kriteria penerimaan
M05 tidak menyebut GET; ia menyebut *"tidak pernah membaca data user B"*, dan
rute yang bisa **menimpa atau menghapus** data orang lain jauh lebih berbahaya
daripada rute yang membocorkannya.

Yang diukur, bukan yang dikira-kira
-----------------------------------
Di `web/src` klien memakai tiga helper: `apiGet` (80 pemakaian), `apiPost`
(294), `apiUploadFile` (12). Jadi permukaan tulisnya jauh lebih besar daripada
permukaan bacanya. File ini menyapu yang POST.

Metodenya tidak menebak payload. Data user B diisikan lebih dulu, sehingga di
kebanyakan tabel **baris pertama (id=1) adalah milik B**. Placeholder `${...id}`
di rute klien lalu disubstitusi `1` — persis seperti sapuan GET — yang berarti
rute yang mengambil id dari path benar-benar diarahkan ke data korban, bukan ke
baris kosong.

Klaimnya sempit dan bisa diuji: setelah semua POST ditembakkan sebagai user A,
baris milik user B tidak berubah **kecuali** pada efek timbal-balik yang memang
dirancang begitu (lihat `EXPECTED_CROSS_USER_EFFECTS`).

Sapuan pertama melaporkan 4 tabel berubah dan nyaris kucatat sebagai celah.
Ternyata bukan: `database.py:7086` memfilter `WHERE id=? AND friend_id=?`, jadi
A hanya bisa menerima permintaan pertemanan yang memang ditujukan kepadanya, dan
`check_achievements()` memang dipanggil untuk kedua belah pihak karena
pertemanan itu timbal balik. **Yang salah adalah tesnya, bukan produknya** — jadi
efek itu di-allowlist dengan alasannya, dan properti keamanan yang sebenarnya
(A tidak bisa menerima permintaan milik orang lain) diuji tersendiri di
`test_accepting_someone_elses_friend_request_is_refused`.

Batasan yang dinyatakan jujur
-----------------------------
1. Payload generik (`{}` atau `{id:1}`), jadi banyak rute menjawab 4xx karena
   validasi — rute itu **tidak benar-benar teruji**, dan jumlahnya dilaporkan,
   bukan disembunyikan. `MINIMUM_EXERCISED` mencegah cakupan menyusut diam-diam.
2. Hanya POST + upload. PUT/DELETE/PATCH tidak dipakai klien ini (0 pemakaian).
3. Yang diassert adalah data B utuh. Rute yang menolak karena alasan lain tetap
   lolos — itu jeda cakupan, bukan bukti aman.
"""
from __future__ import annotations

import json
import os
import re
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from tests.harness import LiveApiServer
from tests.test_api_routes import CLIENT_ROUTE, PLACEHOLDER
from tests.test_m05b_tenant_scoping import (
    SECRET, SUB_A, TAG, make_jwt, seed_all_user_tables, seed_via_helpers,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Lantai cakupan: berapa rute POST yang harus benar-benar tereksekusi (2xx)
# supaya sapuan ini berarti. Diukur saat file ini ditulis; kalau turun, artinya
# ada rute yang mulai menolak dan perlu diselidiki — bukan diterima diam-diam.
MINIMUM_EXERCISED = 40
MINIMUM_POST_ROUTES = 150

# Efek lintas-user yang MEMANG dirancang begitu. Setiap entri punya alasan dan
# rute penyebab yang terukur; kalau tabel di luar daftar ini ikut berubah, atau
# daftarnya perlu bertambah, itu harus diselidiki — bukan didiamkan.
EXPECTED_CROSS_USER_EFFECTS = {
    # A menerima permintaan pertemanan dari B. Pertemanan itu timbal balik:
    # database.py:7093-7094 memanggil check_achievements() untuk KEDUA pihak,
    # dan :7095 memberi notifikasi ke pemohon. Baris `friends` milik B berubah
    # dari 'pending' menjadi 'accepted' — itu inti dari menerima.
    "friends", "user_achievements", "activity_log",
    # `/api/friends/1/accept` -> "Achievement Unlocked" untuk B, dan
    # `/api/social/messages` -> "New message from ..." karena B penerimanya.
    "notifications",
}


def collect_write_routes() -> tuple[set[str], set[str]]:
    """(rute POST yang bisa ditembak, rute dengan placeholder enum)."""
    post: set[str] = set()
    prefix_only: set[str] = set()
    src = os.path.join(ROOT, "web", "src")
    for dirpath, _dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            with open(os.path.join(dirpath, fname), encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            # `apiPost('/api/x', …)` dan `apiUploadFile('/api/y', …)`.
            for m in re.finditer(r"api(?:Post|UploadFile)\s*(?:<[^>]*>)?\s*\(\s*", body):
                tail = body[m.end():m.end() + 200]
                hit = CLIENT_ROUTE.match(tail)
                if not hit:
                    continue
                raw = hit.group(1)
                holders = PLACEHOLDER.findall(raw)
                if holders and not all("id" in h.strip().split(".")[-1].lower() for h in holders):
                    prefix_only.add(PLACEHOLDER.sub("*", raw))
                else:
                    post.add(PLACEHOLDER.sub("1", raw))
    return post, prefix_only


class WritePathIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes, cls.prefix_only = collect_write_routes()

        cls._server = LiveApiServer("m05b_w_a")
        cls._server.__enter__()

        cls.db = cls._server.db
        cls.base = cls._server.base
        cls.uid_a = cls._server.uid

        # KORBAN diisi LEBIH DULU. Ini yang membuat id=1 milik B di kebanyakan
        # tabel, sehingga substitusi placeholder benar-benar menyasar data B.
        cls.uid_b = cls._server.ctx.make_user("m05b_w_b")
        # Pihak ketiga, untuk menguji bahwa A tidak bisa menyentuh permintaan
        # yang tidak menyebut namanya sama sekali.
        cls.ctx_c = cls._server.ctx.make_user("m05b_w_c")
        cls.helper_domains = seed_via_helpers(cls.db, cls.uid_b)
        cls.seeded, cls.unseeded = seed_all_user_tables(cls.db, cls.uid_b)
        cls.first_ids = cls._snapshot_ids()

        conn = cls.db.get_conn()
        conn.execute("UPDATE users SET cloud_user_id=? WHERE id=?", (SUB_A, cls.uid_a))
        conn.commit()
        conn.close()

        cls._saved = {k: os.environ.get(k) for k in
                      ("CRAFTLIFE_JWT_SECRET", "CRAFTLIFE_RULES_API")}
        os.environ["CRAFTLIFE_JWT_SECRET"] = SECRET
        os.environ["CRAFTLIFE_RULES_API"] = "1"
        cls.token = make_jwt(SUB_A)

        cls.before = cls._dump_user_b()
        cls.exercised, cls.rejected, cls.errors = [], [], []
        cls._fire_all()
        cls.after = cls._dump_user_b()

    # ---------------------------------------------------------------- util
    @classmethod
    def _conn(cls):
        return cls.db.get_conn()

    @classmethod
    def _user_tables(cls):
        conn = cls._conn()
        out = []
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            cols = [c["name"] for c in conn.execute(f"PRAGMA table_info({r['name']})")]
            if "user_id" in cols:
                out.append((r["name"], cols))
        conn.close()
        return out

    @classmethod
    def _snapshot_ids(cls):
        """id terkecil milik B per tabel — bukti bahwa id=1 memang milik B."""
        conn = cls._conn()
        out = {}
        for name, _cols in cls._user_tables():
            try:
                row = conn.execute(
                    f"SELECT MIN(id) AS m FROM {name} WHERE user_id=?", (cls.uid_b,)).fetchone()
                if row and row["m"] is not None:
                    out[name] = row["m"]
            except Exception:
                pass
        conn.close()
        return out

    @classmethod
    def _dump_user_b(cls):
        """Seluruh baris B di setiap tabel ber-`user_id`, deterministik."""
        conn = cls._conn()
        dump = {}
        for name, cols in cls._user_tables():
            order = "id" if "id" in cols else cols[0]
            try:
                rows = conn.execute(
                    f"SELECT * FROM {name} WHERE user_id=? ORDER BY {order}",
                    (cls.uid_b,)).fetchall()
            except Exception:
                continue
            dump[name] = [tuple(r) for r in rows]
        conn.close()
        return dump

    @classmethod
    def _fire(cls, path: str):
        body = json.dumps({"id": 1, "password": ""}).encode()
        req = urllib.request.Request(
            f"{cls.base}{path}", data=body, method="POST",
            headers={"Accept": "application/json",
                     "Content-Type": "application/json",
                     "Authorization": f"Bearer {cls.token}"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return path, resp.status
        except urllib.error.HTTPError as exc:
            return path, exc.code
        except Exception as exc:
            return path, f"ERR:{type(exc).__name__}"

    @classmethod
    def _fire_all(cls):
        with ThreadPoolExecutor(max_workers=8) as pool:
            for path, status in pool.map(cls._fire, sorted(cls.routes)):
                if isinstance(status, int) and 200 <= status < 300:
                    cls.exercised.append(path)
                elif isinstance(status, int):
                    cls.rejected.append(f"{path} {status}")
                else:
                    cls.errors.append(f"{path} {status}")

    @classmethod
    def tearDownClass(cls):
        for key, value in cls._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        cls._server.__exit__(None, None, None)

    # ------------------------------------------- inti kriteria penerimaan
    def test_no_write_route_touches_another_users_rows(self):
        changed = {t: (len(b), len(a)) for t, (b, a) in
                   ((t, (self.before[t], self.after[t])) for t in self.before)
                   if b != a}
        unexpected = {t: n for t, n in changed.items()
                      if t not in EXPECTED_CROSS_USER_EFFECTS}
        self.assertEqual(
            unexpected, {},
            "rute POST mengubah data user lain di luar efek timbal-balik yang "
            "diharapkan (tabel: jumlah sebelum -> sesudah): "
            + ", ".join(f"{t}: {n[0]}->{n[1]}" for t, n in unexpected.items()))

    def test_the_expected_effects_are_exactly_the_ones_measured(self):
        """Allowlist tidak boleh melebar tanpa disadari.

        Kalau suatu hari tabel kelima ikut berubah, tes utama di atas tetap
        hijau selama tabel itu ada di allowlist — tes inilah yang menangkapnya.
        """
        changed = {t for t in self.before if self.before[t] != self.after[t]}
        self.assertEqual(
            changed, set(EXPECTED_CROSS_USER_EFFECTS),
            "kumpulan tabel yang tersentuh berbeda dari yang diukur saat "
            "allowlist ini ditulis; perbarui alasannya atau perbaiki produknya")

    def test_accepting_someone_elses_friend_request_is_refused(self):
        """Properti keamanan yang sebenarnya, diuji langsung.

        Allowlist di atas hanya sah karena A boleh menyentuh baris yang
        menyebut namanya. Kalau filter `friend_id=user_id` di database.py:7086
        hilang, A bisa menerima — dan mengubah — permintaan milik siapa pun.
        """
        conn = self.db.get_conn()
        uid_c = self.ctx_c
        conn.execute("INSERT INTO friends(user_id, friend_id, status) VALUES(?,?,?)",
                     (self.uid_b, uid_c, "pending"))
        conn.commit()
        row_id = conn.execute(
            "SELECT id FROM friends WHERE user_id=? AND friend_id=?",
            (self.uid_b, uid_c)).fetchone()["id"]
        before = conn.execute("SELECT status FROM friends WHERE id=?", (row_id,)).fetchone()[0]
        conn.close()

        path, status = self._fire(f"/api/friends/{row_id}/accept")
        conn = self.db.get_conn()
        after = conn.execute("SELECT status FROM friends WHERE id=?", (row_id,)).fetchone()[0]
        conn.close()
        self.assertEqual(status, 200, f"{path} menjawab {status}")
        self.assertEqual(
            after, before,
            f"A berhasil mengubah permintaan pertemanan milik B "
            f"(id={row_id}): status {before} -> {after}")

    # --------------------------------------------- cakupan tidak menyusut
    def test_enough_write_routes_were_found(self):
        self.assertGreaterEqual(len(self.routes), MINIMUM_POST_ROUTES,
                                f"hanya {len(self.routes)} rute POST ditemukan — "
                                "pemindai mungkin rusak")

    def test_enough_routes_actually_executed(self):
        """2xx = jalur mutasi benar-benar dijalankan, bukan ditolak validasi."""
        self.assertGreaterEqual(
            len(self.exercised), MINIMUM_EXERCISED,
            f"hanya {len(self.exercised)} rute POST menjawab 2xx; sisanya "
            f"{len(self.rejected)} ditolak — sapuan ini hampir tidak menguji apa pun")

    # ------------------------------------------------- probe tidak buta
    def test_victim_data_actually_existed_before_the_sweep(self):
        """Tanpa data B, `before == after` akan benar secara kosong."""
        filled = {t: len(rows) for t, rows in self.before.items() if rows}
        self.assertTrue(filled, "tidak ada satu pun baris milik user B — tes ini kosong")
        self.assertGreaterEqual(len(filled), 20,
                                f"hanya {len(filled)} tabel punya data B")

    def test_id_one_really_belongs_to_the_victim(self):
        """Substitusi placeholder `1` hanya berarti kalau id=1 milik B."""
        ones = [t for t, v in self.first_ids.items() if v == 1]
        self.assertGreaterEqual(len(ones), 10,
                                f"hanya {len(ones)} tabel di mana id terkecil B = 1; "
                                "rute ber-id mungkin tidak menyasar data korban")

    # -------------------------------------------------------- laporan
    def test_report_coverage(self):
        print(f"\n[m05b-II] rute POST ditemukan : {len(self.routes)}")
        print(f"[m05b-II] prefix enum (dilewati): {len(self.prefix_only)}")
        print(f"[m05b-II] tereksekusi (2xx)     : {len(self.exercised)}")
        print(f"[m05b-II] ditolak (4xx/5xx)     : {len(self.rejected)}")
        print(f"[m05b-II] error jaringan        : {len(self.errors)}")
        print(f"[m05b-II] tabel B berdata       : "
              f"{sum(1 for v in self.before.values() if v)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
