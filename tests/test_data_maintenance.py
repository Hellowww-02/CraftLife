"""Fitur Pemeliharaan Data (Settings → Pemeliharaan Data) — diuji end-to-end.

Fitur ini menghapus data pengguna, jadi ia diuji sebagai **janji**, bukan sebagai
kode. Tiga janji tertulis di UI-nya sendiri, dan ketiganya dipaku di sini:

  "Backup DB dibuat otomatis sebelum membersihkan"
      -> file backup harus BENAR-BENAR ADA di disk, bukan cuma path di laporan.

  "Data master (tugas, kesehatan, keuangan, catatan) TIDAK disentuh"
      -> habits / food_logs / water_logs / economy_items / notes harus utuh.

  "Hanya riwayat tracker ... yang dihapus"
      -> baris yang masih dalam retensi harus SELAMAT. Kalau purge ikut
         menghapus riwayat baru, heatmap dan streak pengguna rusak diam-diam.

Semua lewat HTTP sungguhan, karena itu jalur yang sama dengan yang diklik
pengguna. Menguji fungsi database-nya saja akan melewatkan seluruh lapisan
`studio_api` — tempat bug bentuk-respons biasanya bersembunyi.

Satu keterbatasan yang dipaku secara eksplisit di `AutoPurgeTriggerTest`,
karena lebih baik tercatat sebagai batas yang diketahui daripada ditemukan
nanti sebagai bug.
"""
from __future__ import annotations

import ast
import json
import os
import pathlib
import unittest
import urllib.error
import urllib.request

from tests.harness import LiveApiServer

OLD = "datetime('now','-60 days')"
NEW = "datetime('now','-1 hour')"

# (tabel, kolom user, kolom waktu) — disalin dari database._tracker_purge_specs()
PURGE_TABLES = {
    "task_history": ("user_id", "created_at"),
    "activity_log": ("user_id", "created_at"),
    "pomodoro_sessions": ("user_id", "completed_at"),
    "sport_rep_logs": ("user_id", "created_at"),
    "music_play_history": ("user_id", "played_at"),
    "boss_rewards": ("user_id", "created_at"),
    "notifications": ("user_id", "created_at"),
    "trash_bin": ("user_id", "deleted_at"),
    "chat_attachments_cache": ("local_user_id", "created_at"),
}

MASTER_SEEDS = [
    ("habits", "INSERT INTO habits(user_id,name,created_at) VALUES(?,?,'2020-01-01')",
     ("HabitTua",)),
    ("food_logs", "INSERT INTO food_logs(user_id,food_id,calories,log_date,created_at) "
                  "VALUES(?,1,100,'2020-01-01','2020-01-01')", ()),
    ("water_logs", "INSERT INTO water_logs(user_id,amount_ml,log_date,created_at) "
                   "VALUES(?,250,'2020-01-01','2020-01-01')", ()),
    ("economy_items", "INSERT INTO economy_items(user_id,name,type,amount,date,created_at) "
                      "VALUES(?,'TxTua','income',100,'2020-01-01','2020-01-01')", ()),
    ("notes", "INSERT INTO notes(user_id,title,content,created_at) "
              "VALUES(?,'NoteTua','isi','2020-01-01')", ()),
]


def _dummy(typ: str, name: str):
    t = (typ or "").upper()
    if "INT" in t or "REAL" in t or "NUM" in t or "DOUB" in t:
        return 1
    if "BLOB" in t:
        return b"x"
    return f"x_{name}"[:40]


class _MaintenanceBase:
    """Boot server + seed data. Bukan TestCase, supaya tesnya tidak terhitung tiga kali."""

    @classmethod
    def setUpClass(cls):
        cls._srv = LiveApiServer("maintenance")
        cls._srv.__enter__()
        cls.db = cls._srv.db
        cls.uid = cls._srv.uid
        cls.base = cls._srv.base

        r = cls._srv.ctx.raw()
        cls.seeded = list(PURGE_TABLES)
        for _table, sql, extra in MASTER_SEEDS:
            r.execute(sql, (cls.uid,) + extra)
        r.commit()
        r.close()
        # Baris purge di-seed ulang di setUp supaya tiap tes mulai bersih.
        cls._seed_purge_rows(cls)

    @classmethod
    def tearDownClass(cls):
        cls._srv.__exit__(None, None, None)

    # -- helpers ---------------------------------------------------------
    def setUp(self):
        """Setiap tes mulai dari kondisi yang sama.

        Tanpa ini, tes purge kedua dan ketiga berjalan di atas sisa tes pertama
        — tidak ada lagi baris tua untuk dihapus, dan tesnya gagal karena alasan
        yang tidak ada hubungannya dengan produk.
        """
        r = self._srv.ctx.raw()
        for tbl, (ucol, _tcol) in PURGE_TABLES.items():
            r.execute(f"DELETE FROM {tbl} WHERE {ucol}=?", (self.uid,))
        r.commit()
        r.close()
        self._seed_purge_rows()

    def _seed_purge_rows(self):
        r = self._srv.ctx.raw()
        for tbl, (ucol, tcol) in PURGE_TABLES.items():
            info = r.execute(f"PRAGMA table_info({tbl})").fetchall()
            for when in (OLD, OLD, OLD, NEW, NEW):
                names, params = [], []
                for _cid, name, typ, notnull, dflt, pk in info:
                    if pk:
                        continue
                    if name == ucol:
                        names.append(name)
                        params.append(self.uid)
                    elif name == tcol:
                        names.append(name)
                    elif notnull and dflt is None:
                        names.append(name)
                        params.append(_dummy(typ, name))
                vals = [when if n == tcol else "?" for n in names]
                r.execute(f"INSERT INTO {tbl}({','.join(names)}) VALUES({','.join(vals)})",
                          params)
        r.commit()
        r.close()

    def call(self, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"{self.base}/api/settings/cleanup", data=data,
            method="POST" if data else "GET",
            headers={"Content-Type": "application/json", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, {"_raw": raw[:200]}

    def count(self, table, where="1=1"):
        r = self._srv.ctx.raw()
        try:
            return r.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]
        finally:
            r.close()

    def set_state(self, **kw):
        self.call({"action": "set", **kw})

    # -- 1. status -------------------------------------------------------
    def test_status_reports_every_field_the_ui_reads(self):
        status, body = self.call()
        self.assertEqual(status, 200, body)
        cleanup = (body or {}).get("cleanup") or {}
        for field in ("retentionDays", "auto", "lastPurgeAt", "schedule",
                      "totalRows", "dbSizeBytes", "tableSizes", "dbTotalBytes"):
            self.assertIn(field, cleanup, f"UI membaca `{field}` tapi tidak dikirim")

    def test_table_sizes_are_populated(self):
        """Panel 'Ukuran per tabel' kosong total kalau ini gagal."""
        _s, body = self.call()
        sizes = ((body or {}).get("cleanup") or {}).get("tableSizes") or []
        self.assertGreater(len(sizes), 50, f"hanya {len(sizes)} tabel dilaporkan")
        for row in sizes[:5]:
            self.assertIn("name", row)
            self.assertIn("bytes", row)
            self.assertIn("rows", row)

    # -- 2. retention ----------------------------------------------------
    def test_every_retention_option_the_ui_offers_is_accepted(self):
        for days in (1, 7, 30, 90, 0):
            _s, body = self.call({"action": "set", "retentionDays": days})
            state = ((body or {}).get("result") or {}).get("state") or {}
            self.assertEqual(state.get("retentionDays"), days,
                             f"retentionDays={days} tidak tersimpan")

    def test_an_invalid_retention_is_rejected(self):
        for bad in (999, -5, "abc"):
            _s, body = self.call({"action": "set", "retentionDays": bad})
            self.assertEqual(((body or {}).get("result") or {}).get("msg"),
                             "retention_invalid", f"{bad!r} seharusnya ditolak")

    def test_retention_zero_survives_a_round_trip(self):
        """0 berarti 'mati'. Kalau diperlakukan sebagai falsy lalu jadi 30,
        pengguna yang mematikan pembersihan justru mendapatkannya menyala."""
        self.set_state(retentionDays=0)
        _s, body = self.call()
        self.assertEqual(((body or {}).get("cleanup") or {}).get("retentionDays"), 0)

    # -- 3. auto + schedule ---------------------------------------------
    def test_auto_toggle_persists(self):
        for value in (True, False):
            _s, body = self.call({"action": "set", "auto": value})
            self.assertEqual(((body or {}).get("result") or {}).get("state", {}).get("auto"),
                             value)

    def test_every_schedule_option_is_accepted_and_bogus_is_rejected(self):
        for schedule in ("daily", "weekly", "monthly"):
            _s, body = self.call({"action": "set", "schedule": schedule})
            self.assertEqual(((body or {}).get("result") or {}).get("state", {}).get("schedule"),
                             schedule)
        _s, body = self.call({"action": "set", "schedule": "tahunan"})
        self.assertEqual(((body or {}).get("result") or {}).get("msg"), "schedule_invalid")

    # -- 4. checkpoint + vacuum -----------------------------------------
    def test_checkpoint_reports_bytes_and_succeeds(self):
        _s, body = self.call({"action": "checkpoint"})
        report = ((body or {}).get("result") or {}).get("report") or {}
        self.assertTrue(report.get("ok"), f"checkpoint gagal: {report}")
        self.assertGreater(report.get("beforeBytes", 0), 0)

    def test_vacuum_succeeds(self):
        _s, body = self.call({"action": "vacuum"})
        report = ((body or {}).get("result") or {}).get("report") or {}
        self.assertTrue(report.get("ok"), f"vacuum gagal: {report.get('error')}")

    # -- 5. guard rails --------------------------------------------------
    def test_run_refuses_when_retention_is_off(self):
        self.set_state(retentionDays=0)
        _s, body = self.call({"action": "run"})
        self.assertEqual(((body or {}).get("result") or {}).get("msg"), "cleanup_disabled")

    def test_an_unknown_action_is_rejected(self):
        _s, body = self.call({"action": "hapus_semua"})
        self.assertEqual(((body or {}).get("result") or {}).get("msg"), "action_invalid")


class MaintenanceTest(_MaintenanceBase, unittest.TestCase):
    """Operasi yang tidak merusak data — aman dijalankan lebih dulu."""


class PurgePromiseTest(_MaintenanceBase, unittest.TestCase):
    """Tiga janji yang tertulis di UI, diuji sebagai janji."""

    def run_purge(self):
        self.set_state(retentionDays=30)
        _s, body = self.call({"action": "run"})
        return ((body or {}).get("result") or {}).get("report") or {}

    def test_a_backup_file_really_exists_on_disk(self):
        report = self.run_purge()
        path = report.get("backupPath")
        self.assertTrue(path, "UI menjanjikan backup otomatis, tapi backupPath kosong")
        self.assertTrue(os.path.exists(path), f"backupPath={path} tapi filenya tidak ada")
        self.assertGreater(os.path.getsize(path), 1024,
                           "file backup ada tapi kosong — bukan backup")

    def test_master_data_is_untouched(self):
        before = {t: self.count(t) for t, _s, _e in MASTER_SEEDS}
        self.run_purge()
        for table, count in before.items():
            self.assertEqual(self.count(table), count,
                             f"JANJI DILANGGAR: data master `{table}` ikut terhapus")

    def test_only_rows_outside_retention_are_deleted(self):
        before = {t: self.count(t) for t in PURGE_TABLES}
        report = self.run_purge()
        self.assertGreater(report.get("totalDeleted", 0), 0, "tidak ada yang dihapus")
        for table, (_ucol, tcol) in PURGE_TABLES.items():
            self.assertEqual(
                self.count(table, f"{tcol} < datetime('now','-30 days')"), 0,
                f"`{table}`: baris tua masih tersisa — purge tidak membersihkannya")
            self.assertEqual(
                self.count(table), before[table] - 3,
                f"`{table}`: riwayat yang masih dalam retensi ikut terhapus")


class AutoPurgeTest(_MaintenanceBase, unittest.TestCase):
    def test_disabled_when_auto_is_off(self):
        self.set_state(auto=False, retentionDays=30)
        self.assertEqual(self.db.maybe_auto_purge(self.uid).get("code"), "disabled")

    def test_disabled_when_retention_is_off(self):
        self.set_state(auto=True, retentionDays=0)
        self.assertEqual(self.db.maybe_auto_purge(self.uid).get("code"), "disabled")

    def test_not_due_right_after_a_purge(self):
        self.set_state(auto=True, retentionDays=30, schedule="monthly")
        self.run_purge_if_needed()
        self.assertEqual(self.db.maybe_auto_purge(self.uid).get("code"), "not_due")

    def test_due_once_the_interval_has_passed(self):
        self.set_state(auto=True, retentionDays=30, schedule="monthly")
        r = self._srv.ctx.raw()
        r.execute("UPDATE maintenance_state SET last_purge_at=datetime('now','-40 days') "
                  "WHERE user_id=?", (self.uid,))
        r.commit()
        r.close()
        out = self.db.maybe_auto_purge(self.uid)
        self.assertTrue(out.get("ok"), f"auto-purge tidak jalan meski jatuh tempo: {out}")

    def run_purge_if_needed(self):
        self.set_state(retentionDays=30)
        self.call({"action": "run"})


class AutoPurgeTriggerTest(unittest.TestCase):
    """Kapan auto-purge sebenarnya dipicu — dipaku supaya tidak bergeser diam-diam.

    KETERBATASAN YANG DIKETAHUI, bukan bug yang disembunyikan: jadwal hanya
    diperiksa saat `configure()`, yaitu sekali per login desktop. Aplikasi yang
    dibiarkan menyala berminggu-minggu tanpa login ulang tidak akan memeriksa
    ulang jadwalnya, jadi "Harian" pada praktiknya berarti "tiap kali login".
    Untuk aplikasi desktop yang dibuka-tutup tiap hari itu setara; untuk yang
    dibiarkan menyala terus, tidak. Tes di bawah memastikan pemicunya ada, dan
    mendokumentasikan bahwa hanya ada satu.
    """

    ROOT = pathlib.Path(__file__).resolve().parents[1]

    def test_the_function_still_has_a_caller(self):
        """Tanpa pemanggil, seluruh fitur 'Bersihkan otomatis' jadi hiasan."""
        hits = []
        for py in self.ROOT.glob("*.py"):
            tree = ast.parse(py.read_text(encoding="utf-8", errors="replace"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "maybe_auto_purge":
                    hits.append(py.name)
        callers = [h for h in hits if h != "database.py"]
        self.assertEqual(len(callers), 1,
                         f"pemanggil maybe_auto_purge berubah: {callers or 'TIDAK ADA'}")

    def test_the_only_caller_is_configure_in_api_server(self):
        src = (self.ROOT / "api_server.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("db.maybe_auto_purge", src)
        self.assertIn("def configure(", src)
        # configure() hanya dipanggil dari desktop; pastikan itu tetap benar
        # supaya keterbatasan di atas tidak melebar tanpa disadari.
        main_src = (self.ROOT / "MainPyQt6.py").read_text(encoding="utf-8", errors="replace")
        self.assertIn("api_server.configure(", main_src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
