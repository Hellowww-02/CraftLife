"""Backup tracker ke cloud — diuji.

Yang paling penting di sini bukan "upload berhasil" (itu tidak bisa diuji tanpa
Supabase sungguhan), melainkan tiga hal yang bisa rusak diam-diam:

**Snapshot harus lengkap.** `_sanitize_cloud_personal_snapshot` menuntut
seluruh kunci EXPORT_TABLES; snapshot yang kehilangan satu tabel akan ditolak
saat dipulihkan. Jadi kelengkapan 40 tabel dipaku di sini.

**Admin harus tetap punya cadangan.** `export_tracker_data` menolak admin untuk
menutup vektor curang. Backup itu baca-saja dan bukan vektor itu — tapi kalau
larangannya ikut terbawa, akun admin tidak punya cadangan sama sekali (P6).
Keduanya diuji: ekspor biasa tetap menolak, snapshot backup tetap jalan.

**Restore tidak boleh jadi jalan kehilangan data.** Restore menimpa data
sekarang, jadi backup lokal harus dibuat lebih dulu, dan path yang datang dari
request harus ditolak kalau bukan milik pengguna ini.
"""
from __future__ import annotations

import gzip
import json
import os
import unittest

import importlib
import sys

import database

from tests.harness import TempDatabase


class _FakeCloud:
    """Pengganti klien Supabase: cukup untuk menguji logika di sekitarnya."""

    def __init__(self, user="11111111-2222-3333-4444-555555555555"):
        self.current_cloud_user_id = user
        self.config = type("C", (), {"backup_bucket": "tracker-backups"})()
        self.uploaded = {}
        self.pruned = 0

    def upload_tracker_backup(self, payload):
        path = f"{self.current_cloud_user_id}/craftlife_backup_20261012_000000.json.gz"
        self.uploaded[path] = payload
        return {"path": path, "size_bytes": len(payload)}

    def list_tracker_backups(self):
        return [{"name": p.split("/")[-1], "path": p,
                 "size_bytes": len(b), "created_at": "2026-10-12"}
                for p, b in self.uploaded.items()]

    def prune_tracker_backups(self, keep=14):
        return self.pruned

    def download_storage(self, bucket, path):
        if path not in self.uploaded:
            raise RuntimeError("object not found")
        return self.uploaded[path]


class _FakeSync:
    def __init__(self, ok=True):
        self._ok = ok

    def ensure_session(self, uid):
        return self._ok


class BackupTest(unittest.TestCase):
    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("backup")

        # TempDatabase mengimpor ulang `database` dan memasang DB_PATH di objek
        # BARU. `cloud_api` dan `storage` yang sudah diimpor di puncak modul ini
        # masih memegang yang LAMA — yang menunjuk craftlife.db repo berskema
        # lama. Tanpa rebind di sini, tes gagal dengan "no column named
        # last_backup_at" karena alasan yang tidak ada hubungannya dengan produk.
        self._saved_modules = {m: sys.modules.get(m) for m in ("storage", "cloud_api")}
        for m in ("storage", "cloud_api"):
            sys.modules.pop(m, None)
        self.storage = importlib.import_module("storage")
        self.cloud_api = importlib.import_module("cloud_api")
        self.addCleanup(self._restore)
        self.storage.reset_store()
        self.addCleanup(self.storage.reset_store)

        self.fake = _FakeCloud()
        self.cloud_api.get_cloud_service = lambda: self.fake
        self.cloud_api.get_sync_service = lambda: _FakeSync()

    def _restore(self):
        for m, mod in self._saved_modules.items():
            sys.modules.pop(m, None)
            if mod is not None:
                sys.modules[m] = mod

    def link(self):
        self.cloud_api.is_cloud_linked = lambda uid: True

    # -- snapshot --------------------------------------------------------
    def test_the_snapshot_contains_every_export_table(self):
        """G10: snapshot yang kehilangan satu tabel ditolak saat dipulihkan."""
        self.link()
        snap = self.storage.get_store().build_backup_snapshot(self.uid)
        tables = snap.get("tables") or {}
        missing = [t for t in database.EXPORT_TABLES if t not in tables]
        self.assertEqual(missing, [], f"tabel hilang dari snapshot: {missing}")
        self.assertEqual(len(database.EXPORT_TABLES), 40,
                         "jumlah EXPORT_TABLES berubah — perbarui ekspektasi ini sadar-sadar")

    def test_the_snapshot_survives_a_gzip_round_trip(self):
        self.link()
        payload = self.cloud_api._gzip_snapshot(self.uid)
        self.assertGreater(len(payload), 0)
        restored = json.loads(gzip.decompress(payload).decode("utf-8"))
        self.assertEqual(sorted(restored["tables"]),
                         sorted(self.storage.get_store().build_backup_snapshot(self.uid)["tables"]))

    def test_gzip_actually_shrinks_the_payload(self):
        """Kalau kompresi diam-diam mati, backup akan menembus batas 50 MB."""
        self.link()
        snap = self.storage.get_store().build_backup_snapshot(self.uid)
        raw = json.dumps(snap, ensure_ascii=False, default=str).encode()
        self.assertLess(len(self.cloud_api._gzip_snapshot(self.uid)), len(raw))

    # -- admin -----------------------------------------------------------
    def test_a_plain_export_still_refuses_an_admin(self):
        """P4: larangan lama tidak boleh ikut longgar."""
        conn = self.ctx.raw()
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (self.uid,))
        conn.commit()
        conn.close()
        with self.assertRaises(PermissionError):
            self.ctx.db.export_tracker_data(self.uid)

    def test_but_a_backup_still_works_for_an_admin(self):
        """Tanpa ini, akun admin tidak punya cadangan data sama sekali."""
        conn = self.ctx.raw()
        conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (self.uid,))
        conn.commit()
        conn.close()
        snap = self.storage.get_store().build_backup_snapshot(self.uid)
        self.assertIn("tables", snap)
        self.assertGreater(len(snap["tables"]), 0)

    # -- state -----------------------------------------------------------
    def test_auto_backup_defaults_to_on(self):
        """Mencadangkan data adalah perilaku aman; mematikannya harus sadar."""
        self.assertTrue(self.db.get_maintenance_state(self.uid)["backup_auto"])

    def test_auto_backup_can_be_turned_off_and_back_on(self):
        self.db.set_maintenance_state(self.uid, backup_auto=False)
        self.assertFalse(self.db.get_maintenance_state(self.uid)["backup_auto"])
        self.db.set_maintenance_state(self.uid, backup_auto=True)
        self.assertTrue(self.db.get_maintenance_state(self.uid)["backup_auto"])

    def test_mark_backup_done_records_a_timestamp(self):
        self.assertEqual(self.db.get_maintenance_state(self.uid)["last_backup_at"], "")
        self.db.mark_backup_done(self.uid)
        self.assertNotEqual(self.db.get_maintenance_state(self.uid)["last_backup_at"], "")

    def test_turning_backup_off_does_not_disturb_the_purge_settings(self):
        self.db.set_maintenance_state(self.uid, retention_days=7, auto=False,
                                      schedule="weekly")
        self.db.set_maintenance_state(self.uid, backup_auto=False)
        st = self.db.get_maintenance_state(self.uid)
        self.assertEqual((st["retention_days"], st["auto"], st["schedule"]),
                         (7, False, "weekly"),
                         "menyetel backup ikut mengacak setelan pembersihan")

    # -- create ----------------------------------------------------------
    def test_create_refuses_when_the_account_is_not_linked(self):
        self.cloud_api.is_cloud_linked = lambda uid: False
        self.assertEqual(self.cloud_api.backup_create(self.uid).get("error"), "not_linked")

    def test_create_uploads_and_records_the_timestamp(self):
        self.link()
        out = self.cloud_api.backup_create(self.uid)
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(self.fake.uploaded), 1)
        self.assertNotEqual(self.db.get_maintenance_state(self.uid)["last_backup_at"], "")

    # -- maybe_auto_backup ------------------------------------------------
    def test_auto_backup_skips_when_disabled(self):
        self.link()
        self.db.set_maintenance_state(self.uid, backup_auto=False)
        self.assertEqual(self.cloud_api.maybe_auto_backup(self.uid)["code"], "disabled")
        self.assertEqual(len(self.fake.uploaded), 0)

    def test_auto_backup_skips_when_not_linked(self):
        self.cloud_api.is_cloud_linked = lambda uid: False
        self.assertEqual(self.cloud_api.maybe_auto_backup(self.uid)["code"], "not_linked")

    def test_auto_backup_runs_the_first_time(self):
        self.link()
        out = self.cloud_api.maybe_auto_backup(self.uid)
        self.assertTrue(out["ok"], out)
        self.assertEqual(len(self.fake.uploaded), 1)

    def test_auto_backup_does_not_run_twice_in_a_day(self):
        self.link()
        self.cloud_api.maybe_auto_backup(self.uid)
        second = self.cloud_api.maybe_auto_backup(self.uid)
        self.assertEqual(second["code"], "not_due")
        self.assertEqual(len(self.fake.uploaded), 1,
                         "backup jalan dua kali dalam sehari — akan menghabiskan kuota storage")

    def test_auto_backup_runs_again_after_the_interval(self):
        self.link()
        self.db.mark_backup_done(self.uid, when="datetime('now','-2 days')")
        out = self.cloud_api.maybe_auto_backup(self.uid)
        self.assertTrue(out["ok"], out)

    # -- restore ----------------------------------------------------------
    def test_restore_rejects_a_path_outside_the_users_folder(self):
        """Nama path datang dari request. Tanpa saringan ini, seseorang bisa
        memulihkan dari cadangan milik orang lain."""
        self.link()
        out = self.cloud_api.backup_restore(self.uid, "orang-lain/craftlife_backup_x.json.gz")
        self.assertEqual(out["error"], "path_forbidden")

    def test_restore_rejects_path_traversal(self):
        self.link()
        me = self.fake.current_cloud_user_id
        out = self.cloud_api.backup_restore(self.uid, f"{me}/../../orang-lain/backup.json.gz")
        self.assertEqual(out["error"], "path_forbidden")

    def test_restore_rejects_a_malformed_backup(self):
        self.link()
        me = self.fake.current_cloud_user_id
        bad = f"{me}/craftlife_backup_bad.json.gz"
        self.fake.uploaded[bad] = gzip.compress(b"ini bukan json")
        out = self.cloud_api.backup_restore(self.uid, bad)
        self.assertEqual(out["error"], "backup_malformed")

    def test_restore_makes_a_local_backup_before_overwriting(self):
        """Restore menimpa data sekarang. Kalau backup lokal tidak dibuat lebih
        dulu, restore yang salah jadi kehilangan data permanen (P6)."""
        self.link()
        out = self.cloud_api.backup_create(self.uid)
        self.db.set_maintenance_state(self.uid, retention_days=30)
        result = self.cloud_api.backup_restore(self.uid, out["path"])
        self.assertTrue(result.get("ok"), f"restore gagal: {result}")
        self.assertTrue(result.get("localBackupOk"),
                        f"restore berjalan TANPA backup lokal lebih dulu: {result}")

    # -- routes -----------------------------------------------------------
    def test_the_backup_routes_are_wired(self):
        self.link()
        self.assertIsNotNone(self.cloud_api.handle_get("/api/cloud/backups", self.uid))
        self.assertIsNotNone(
            self.cloud_api.handle_post("/api/cloud/backup", self.uid, {"action": "create"}))

    def test_the_backup_list_is_camel_case(self):
        """C06: klien tidak boleh dibiasakan membaca snake_case dari sebagian
        rute dan camelCase dari yang lain."""
        self.link()
        self.cloud_api.backup_create(self.uid)
        out = self.cloud_api.handle_get("/api/cloud/backups", self.uid)
        self.assertTrue(out["backups"], "daftar backup kosong")
        row = out["backups"][0]
        for field in ("name", "path", "sizeBytes", "createdAt"):
            self.assertIn(field, row, f"field `{field}` hilang dari respons")
        self.assertNotIn("size_bytes", row, "snake_case bocor ke respons")
        self.assertGreater(row["sizeBytes"], 0)

    def test_an_unknown_backup_action_is_rejected(self):
        self.link()
        out = self.cloud_api.handle_post("/api/cloud/backup", self.uid, {"action": "hapus"})
        self.assertEqual(out["error"], "action_invalid")

    def test_list_reports_status_even_when_not_linked(self):
        """UI harus tetap bisa menampilkan 'mati' sebelum pengguna login."""
        self.cloud_api.is_cloud_linked = lambda uid: False
        out = self.cloud_api.handle_get("/api/cloud/backups", self.uid)
        self.assertTrue(out["ok"])
        self.assertIn("backupAuto", out)
        self.assertFalse(out["linked"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
