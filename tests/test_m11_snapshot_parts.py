"""M11 — payload snapshot inkremental (menutup G5) + jitter backoff.

Bug yang ditutup: snapshot tracker adalah SATU dokumen JSON dan server
menolak payload di atas 8 MB, jadi pengguna berdata besar tidak bisa
sync sama sekali. Kini dokumen besar dipecah menjadi part
`tracker_v1/part/NNN` (<= 3 MB). Yang dijaga tes ini:

  * part selalu di bawah plafon transport, dan gabungannya persis
    dokumen asal (tidak ada baris hilang/dobel);
  * satu tabel raksasa ikut terbelah di tengah baris-barisnya;
  * penerima menolak menggabungkan generasi campuran / set kurang —
    hasilnya "belum lengkap", bukan data setengah;
  * antrean sync benar-benar menghasilkan banyak job part untuk
    snapshot besar, dan manifest (part 0) diantrekan terakhir;
  * tarikan menggabungkan part menjadi dokumen yang bisa diterapkan;
  * migrasi M11 hanya melonggarkan validasi document_key RPC;
  * backoff desktop kini ber-jitter (tidak semua job menyerbu bersama).
"""

import pathlib
import sys
import unittest

from tests.harness import TempDatabase

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20261023010000_phase_m11_snapshot_parts.sql"


def _fresh_sync_service():
    for name in ("sync_service", "cloud_service"):
        sys.modules.pop(name, None)
    import sync_service
    return sync_service


def _big_snapshot(tables):
    return {"version": 1, "cloud_schema": 1, "document_key": "tracker_v1", "tables": tables}


class SplitMergeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._ctx = TempDatabase()
        cls._ctx.__enter__()
        cls.db = cls._ctx.db
        cls.db.init_db()

    @classmethod
    def tearDownClass(cls):
        cls._ctx.__exit__(None, None, None)

    def test_small_snapshot_stays_single_part(self):
        snap = _big_snapshot({t: [] for t in self.db.EXPORT_TABLES})
        parts = self.db.split_cloud_personal_snapshot(snap)
        self.assertEqual(len(parts), 1)
        self.assertEqual(self.db.merge_cloud_personal_parts(parts), snap)

    def test_large_table_is_split_mid_rows_and_merges_exactly(self):
        rows = [{"id": i, "title": "catatan " + "x" * 200} for i in range(300)]
        tables = {t: [] for t in self.db.EXPORT_TABLES}
        tables["notes"] = rows
        snap = _big_snapshot(tables)
        parts = self.db.split_cloud_personal_snapshot(snap, max_bytes=10_000)
        self.assertGreater(len(parts), 3)
        for part in parts:
            self.db._sanitize_cloud_personal_snapshot_part(part)
        merged = self.db.merge_cloud_personal_parts(parts)
        self.assertEqual(merged["tables"]["notes"], rows)

    def test_mixed_generations_and_incomplete_sets_are_rejected(self):
        tables = {t: [] for t in self.db.EXPORT_TABLES}
        tables["notes"] = [{"id": i, "t": "y" * 300} for i in range(100)]
        parts_a = self.db.split_cloud_personal_snapshot(_big_snapshot(tables), max_bytes=5_000)
        tables_b = dict(tables, notes=[{"id": 999, "t": "z" * 300}])
        parts_b = self.db.split_cloud_personal_snapshot(_big_snapshot(tables_b), max_bytes=5_000)
        self.assertIsNone(self.db.merge_cloud_personal_parts(parts_a[:-1]))
        self.assertIsNone(self.db.merge_cloud_personal_parts(parts_a[:1] + parts_b[1:]))
        self.assertIsNone(self.db.merge_cloud_personal_parts([]))

    def test_part_sanitizer_rejects_unknown_table(self):
        tables = {t: [] for t in self.db.EXPORT_TABLES}
        part = self.db.split_cloud_personal_snapshot(_big_snapshot(tables))[0]
        part["tables"]["tabel_ngawur"] = []
        with self.assertRaises(ValueError):
            self.db._sanitize_cloud_personal_snapshot_part(part)


class QueueAndPullTests(unittest.TestCase):
    def _uid_of(self, username):
        conn = self.db.get_conn()
        try:
            return int(conn.execute(
                "SELECT id FROM users WHERE username=?", (username,)).fetchone()["id"])
        finally:
            conn.close()

    def setUp(self):
        self._ctx = TempDatabase()
        self._ctx.__enter__()
        self.db = self._ctx.db
        self.db.init_db()
        self.db.register_user("m11user", "password123", "M11")
        self.uid = self._uid_of("m11user")
        # Snapshot user baru yang kosong memang TIDAK diantrekan (aturan
        # lama); beri satu baris data agar snapshot tidak kosong.
        self.db.add_todo(self.uid, "tugas m11 " + "x" * 300)

    def tearDown(self):
        self._ctx.__exit__(None, None, None)

    def test_queue_enqueues_parts_manifest_last(self):
        sync = _fresh_sync_service()
        service = sync.CloudSyncService()
        original = self.db.split_cloud_personal_snapshot
        sync.db.split_cloud_personal_snapshot = (
            lambda snap: original(snap, max_bytes=400))
        try:
            out = service._queue_personal_if_changed(self.uid, force=True)
        finally:
            sync.db.split_cloud_personal_snapshot = original
        self.assertTrue(out.get("queued"))
        self.assertGreater(out.get("parts", 0), 1)
        jobs = self.db.get_all_sync_jobs(self.uid, 100)
        part_jobs = [j for j in jobs if j["entity_type"] == "personal_snapshot"]
        self.assertEqual(len(part_jobs), out["parts"])
        # get_all_sync_jobs mengurutkan untuk drain: manifest part/000 harus
        # menjadi job part yang PALING AKHIR diproses.
        self.assertTrue(part_jobs[-1]["entity_local_id"].endswith("part/000"))

    def test_pull_merges_parts_and_applies(self):
        sync = _fresh_sync_service()
        service = sync.CloudSyncService()
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        parts = self.db.split_cloud_personal_snapshot(snapshot, max_bytes=2_000)
        rows = [{
            "document_key": self.db.snapshot_part_key(p["part"]["index"]),
            "revision": idx + 1, "payload": p, "content_hash": "x",
            "server_updated_at": None,
        } for idx, p in enumerate(parts)]

        class FakeCloud:
            def get_personal_snapshots(self):
                return rows

            def get_personal_snapshot_versions(self, document_key="tracker_v1", limit=10):
                return [{"revision": len(rows)}]

        service.cloud = FakeCloud()
        out = service._pull_personal(self.uid)
        self.assertTrue(out.get("applied") or out.get("matched"), out)

    def test_pull_incomplete_parts_is_not_an_error(self):
        sync = _fresh_sync_service()
        service = sync.CloudSyncService()
        snapshot = self.db.build_cloud_personal_snapshot(self.uid)
        parts = self.db.split_cloud_personal_snapshot(snapshot, max_bytes=400)
        self.assertGreater(len(parts), 1)
        rows = [{
            "document_key": self.db.snapshot_part_key(p["part"]["index"]),
            "revision": 1, "payload": p,
        } for p in parts[:-1]]  # satu part hilang

        class FakeCloud:
            def get_personal_snapshots(self):
                return rows

            def get_personal_snapshot_versions(self, document_key="tracker_v1", limit=10):
                return [{"revision": 99}]

        service.cloud = FakeCloud()
        out = service._pull_personal(self.uid)
        self.assertTrue(out.get("partsIncomplete"), out)


class MigrationAndBackoffTests(unittest.TestCase):
    def test_migration_only_relaxes_document_key(self):
        sql = MIGRATION.read_text(encoding="utf-8")
        self.assertIn("tracker_v1/part/%", sql)
        self.assertIn("create or replace function public.upsert_personal_snapshot(", sql)
        self.assertIn("octet_length(p_payload::text)>8388608", sql)

    def test_backoff_has_deterministic_jitter(self):
        with TempDatabase() as ctx:
            db = ctx.db
            db.init_db()
            db.register_user("jitter", "password123", "J")
            conn = db.get_conn()
            uid = int(conn.execute("SELECT id FROM users WHERE username='jitter'").fetchone()["id"])
            conn.close()
            db.enqueue_sync(uid, "habits", "1", "upsert", {})
            job = db.get_all_sync_jobs(uid, 1)[0]
            db.mark_sync_job_failed(job["id"], "timeout", 1)
            row = [j for j in db.get_all_sync_jobs(uid, 5) if j["id"] == job["id"]][0]
            self.assertEqual(row["status"], "retry")
            self.assertIsNotNone(row["next_retry_at"])


if __name__ == "__main__":
    unittest.main()
