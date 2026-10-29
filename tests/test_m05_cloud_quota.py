"""Egress: empat perbaikan agar free tier tidak jebol dan 402 tidak mematikan.

MASALAH YANG DITUTUP
--------------------
Project Supabase pengguna mencapai 80% kuota egress free tier, dan Supabase
memperingatkan akan menjawab 402 lalu membatasi project. Penyebabnya bukan
kuota yang terlalu kecil — ada pemborosan nyata di kode:

* `sync_service.py` memanggil `fetch_entities(table)` TANPA `since`, padahal
  RPC-nya menerima `p_since`. Akibatnya seluruh riwayat 7 tabel append-only
  diunduh ulang **setiap 60 detik** (`cloud_config.sync_interval_seconds = 60`),
  dan tabel append-only tidak pernah menyusut — jadi biayanya naik selamanya.
* `_pull_personal` mengunduh payload dokumen penuh hanya untuk sampai ke cabang
  "unchanged", padahal ada `get_personal_snapshot_versions()` yang mengambil
  kolom metadata saja.
* Tidak ada penanganan 402 di mana pun (`grep 402` di cloud_service.py,
  cloud_api.py, sync_service.py: nol hasil), jadi aplikasi tidak tahu
  project-nya dibatasi.
* `mark_sync_job_failed` selalu mengembalikan job ke 'retry' tanpa batas dan
  tanpa status mati, jadi job yang tidak akan pernah berhasil dicoba selamanya.

Angkanya: 5 GB / 30 hari / 1440 siklus ≈ 118 KB per siklus. Begitu satu tarikan
penuh melewati itu, loop 60 detik matematis tidak sanggup di free tier.
"""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone

from tests.harness import TempDatabase

UID = 11


def _fresh_sync_service():
    """Impor ulang sync_service agar terikat ke modul `database` yang baru.

    `TempDatabase.__enter__` hanya me-rebind `database`; ia TIDAK mempurge
    `_DB_DEPENDENTS` (itu tugas `LiveApiServer`). Tanpa pop di sini,
    `import sync_service` mengembalikan modul lama yang masih menunjuk
    direktori sementara milik tes sebelumnya — sudah dihapus.
    """
    for name in ("sync_service", "cloud_service"):
        sys.modules.pop(name, None)
    import sync_service
    return sync_service


class _FakeCloud:
    """Merekam apa yang diminta, supaya bisa dibuktikan apa yang TIDAK diminta."""

    def __init__(self):
        self.fetch_entities_calls = []
        self.get_snapshots_calls = 0
        self.get_versions_calls = 0
        self.rows = []
        self.versions = [{"revision": 5}]
        self.authenticated = True

    def fetch_entities(self, table_name, since=None, limit=5000):
        self.fetch_entities_calls.append({"table": table_name, "since": since})
        return {"rows": list(self.rows)}

    def get_personal_snapshots(self):
        self.get_snapshots_calls += 1
        return [{"document_key": "tracker_v1", "revision": 5, "payload": {}}]

    def get_personal_snapshot_versions(self, document_key="tracker_v1", limit=10):
        self.get_versions_calls += 1
        return list(self.versions)

    def append_entities(self, *a, **kw):
        return {"inserted": 0}


class ClassifierTest(unittest.TestCase):
    """Deteksi 402 tidak boleh bergantung pada kelas exception tertentu."""

    def test_status_via_attribute(self):
        from cloud_service import classify_cloud_error
        err = type("E", (Exception,), {"status_code": 402})()
        self.assertEqual(classify_cloud_error(err), "quota")

    def test_status_via_response_object(self):
        from cloud_service import classify_cloud_error

        class Resp:
            status_code = 402

        err = Exception("HTTP error 402: Payment Required")
        err.response = Resp()
        self.assertEqual(classify_cloud_error(err), "quota")

    def test_status_from_message_text_only(self):
        from cloud_service import classify_cloud_error
        self.assertEqual(classify_cloud_error(Exception("status 429 too many")),
                         "rate_limited")

    def test_auth_is_distinguished_from_quota(self):
        from cloud_service import classify_cloud_error
        self.assertEqual(classify_cloud_error(type("E", (Exception,), {"code": "401"})()),
                         "auth")

    def test_ordinary_network_error_is_not_misclassified(self):
        """PENTING: koneksi putus bukan kuota. Salah klasifikasi = data hilang."""
        from cloud_service import classify_cloud_error
        for msg in ("connection refused", "timed out", "Temporary failure in name resolution"):
            self.assertIsNone(classify_cloud_error(Exception(msg)), msg)

    def test_none_is_safe(self):
        from cloud_service import classify_cloud_error
        self.assertIsNone(classify_cloud_error(None))


class QuotaScanTest(unittest.TestCase):
    def test_finds_quota_nested_in_channel_results(self):
        from sync_service import CloudSyncService as C
        found = C._quota_seen({
            "channel_a": {"errors": {"food_logs": "HTTP 402: Payment Required"}},
            "channel_b": {"available": True},
        })
        self.assertEqual(found, "quota")

    def test_clean_results_report_nothing(self):
        from sync_service import CloudSyncService as C
        self.assertIsNone(C._quota_seen({"channel_a": {"errors": {"x": "timeout"}}}))


class ChannelAIncrementalTest(unittest.TestCase):
    """Fix 1: Kanal A menarik yang baru saja, bukan seluruh riwayat."""

    def setUp(self):
        self.ctx = TempDatabase()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        # Pengguna nyata: _sync_channel_a memanggil get_or_create_cloud_device
        # yang punya FK ke users(id). UID karangan membuat FK gagal.
        self.uid = self.ctx.make_user("quota_a")

    def test_watermark_roundtrip(self):
        self.assertIsNone(self.db.get_channel_a_watermark(self.uid, "food_logs"))
        self.db.set_channel_a_watermark(self.uid, "food_logs", "2026-10-12T08:00:00+00:00")
        self.assertEqual(self.db.get_channel_a_watermark(self.uid, "food_logs"),
                         "2026-10-12T08:00:00+00:00")

    def test_watermark_upsert_does_not_duplicate(self):
        for value in ("2026-10-12T08:00:00+00:00", "2026-10-12T09:00:00+00:00"):
            self.db.set_channel_a_watermark(self.uid, "food_logs", value)
        conn = self.db.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM cloud_channel_a_state WHERE local_user_id=?",
                         (self.uid,)).fetchone()[0]
        conn.close()
        self.assertEqual(n, 1, "watermark menduplikasi baris")

    def test_since_is_none_before_the_first_pull(self):
        self.assertIsNone(self.db.channel_a_since(self.uid, "food_logs"))

    def test_since_backs_off_by_the_overlap(self):
        """Overlap melindungi baris yang persis di batas limit."""
        self.db.set_channel_a_watermark(self.uid, "food_logs", "2026-10-12T08:00:00+00:00")
        since = self.db.channel_a_since(self.uid, "food_logs")
        self.assertIsNotNone(since)
        parsed = datetime.fromisoformat(since)
        expected = datetime.fromisoformat("2026-10-12T08:00:00+00:00") - timedelta(
            seconds=self.db.CHANNEL_A_OVERLAP_SECONDS)
        self.assertEqual(parsed, expected)

    def test_a_corrupt_watermark_falls_back_to_a_full_pull(self):
        """Penanda rusak tidak boleh membuat sync gagal selamanya."""
        self.db.set_channel_a_watermark(self.uid, "food_logs", "bukan-tanggal")
        self.assertIsNone(self.db.channel_a_since(self.uid, "food_logs"))

    def test_sync_passes_the_watermark_as_since(self):
        """Kontrak intinya: begitu ada watermark, tarikan berikutnya tidak penuh."""
        sync_service = _fresh_sync_service()
        svc = sync_service.CloudSyncService()
        fake = _FakeCloud()
        svc.cloud = fake
        table = self.db.APPEND_ONLY_TABLES[0]
        self.db.set_channel_a_watermark(self.uid, table, "2026-10-12T10:00:00+00:00")

        svc._sync_channel_a(self.uid)
        call = next(c for c in fake.fetch_entities_calls if c["table"] == table)
        self.assertIsNotNone(call["since"],
                             "watermark ada tapi tarikan masih penuh — inilah "
                             "pemborosan egress yang sedang ditutup")
        self.assertEqual(call["since"], self.db.channel_a_since(self.uid, table))

    def test_first_pull_with_no_watermark_is_full(self):
        sync_service = _fresh_sync_service()
        svc = sync_service.CloudSyncService()
        fake = _FakeCloud()
        svc.cloud = fake
        table = self.db.APPEND_ONLY_TABLES[0]
        svc._sync_channel_a(self.uid)
        call = next(c for c in fake.fetch_entities_calls if c["table"] == table)
        self.assertIsNone(call["since"],
                          "tanpa watermark tarikan pertama harus penuh, atau "
                          "riwayat lama tidak akan pernah sampai")

    def test_a_failed_fetch_does_not_advance_the_watermark(self):
        """Kalau tarikan gagal, watermark tidak boleh maju.

        Ini sifat keselamatan, bukan detail: memajukan watermark saat fetch
        gagal akan membuat baris yang belum pernah diterima tidak pernah
        ditarik lagi — data hilang diam-diam, dan P6 melarangnya.

        Catatan: baris dengan kolom tak dikenal BUKAN kasus gagal.
        `apply_entity_append_rows` menyaring ke kolom yang dikenal tabel
        (`insert_cols = [c for c in cols if c in values]`), jadi baris seperti
        itu tetap tersimpan dan watermark memang boleh maju.
        """
        sync_service = _fresh_sync_service()
        svc = sync_service.CloudSyncService()
        table = self.db.APPEND_ONLY_TABLES[0]

        class _Broken(_FakeCloud):
            def fetch_entities(self, table_name, since=None, limit=5000):
                if table_name == table:
                    raise RuntimeError("connection reset")
                return super().fetch_entities(table_name, since, limit)

        svc.cloud = _Broken()
        svc._sync_channel_a(self.uid)
        self.assertIsNone(self.db.get_channel_a_watermark(self.uid, table),
                          "watermark maju padahal tarikannya gagal")


class SnapshotVersionCheckTest(unittest.TestCase):
    """Fix 2: cek revisi dulu, unduh payload hanya kalau berubah."""

    def setUp(self):
        self.ctx = TempDatabase()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("quota_snap")
        sync_service = _fresh_sync_service()
        self.svc = sync_service.CloudSyncService()
        self.fake = _FakeCloud()
        self.svc.cloud = self.fake

    def _prime_state(self, remote_revision):
        conn = self.db.get_conn()
        conn.execute(
            "INSERT INTO cloud_personal_sync_state(local_user_id, document_key,"
            " remote_revision, conflict_status) VALUES(?,?,?,'none')"
            " ON CONFLICT(local_user_id, document_key)"
            " DO UPDATE SET remote_revision=excluded.remote_revision,"
            " conflict_status=excluded.conflict_status",
            (self.uid, "tracker_v1", remote_revision))
        conn.commit()
        conn.close()

    def test_unchanged_revision_skips_the_download(self):
        self._prime_state(5)
        self.fake.versions = [{"revision": 5}]
        result = self.svc._pull_personal(self.uid)
        self.assertTrue(result.get("unchanged"))
        self.assertTrue(result.get("skippedDownload"))
        self.assertEqual(self.fake.get_snapshots_calls, 0,
                         "payload penuh masih diunduh padahal revisi tidak naik")
        self.assertEqual(self.fake.get_versions_calls, 1)

    def test_newer_revision_still_downloads(self):
        self._prime_state(5)
        self.fake.versions = [{"revision": 6}]
        self.svc._pull_personal(self.uid)
        self.assertEqual(self.fake.get_snapshots_calls, 1,
                         "revisi naik tapi payload tidak diunduh — data akan tertinggal")

    def test_first_sync_downloads_even_without_state(self):
        self.fake.versions = [{"revision": 1}]
        try:
            self.svc._pull_personal(self.uid)
        except ValueError:
            # Payload palsu ini kosong, dan `_sanitize_cloud_personal_snapshot`
            # menuntut seluruh 40 kunci EXPORT_TABLES — itu G10, sudah ada
            # sebelum perubahan ini dan sengaja tidak disentuh di sini. Yang
            # diuji tes ini adalah APAKAH unduhan terjadi, dan itu sudah
            # tercatat di penghitung sebelum error hilirnya muncul.
            pass
        self.assertEqual(self.fake.get_snapshots_calls, 1,
                         "sync pertama tidak boleh mengambil jalan pintas")

    def test_pending_conflict_never_takes_the_shortcut(self):
        self._prime_state(5)
        conn = self.db.get_conn()
        conn.execute("UPDATE cloud_personal_sync_state SET conflict_status='needs_resolution'"
                     " WHERE local_user_id=? AND document_key='tracker_v1'", (self.uid,))
        conn.commit()
        conn.close()
        self.svc._pull_personal(self.uid)
        self.assertEqual(self.fake.get_snapshots_calls, 1,
                         "konflik yang menunggu harus tetap melihat payload")

    def test_a_broken_version_check_falls_back_to_downloading(self):
        """Kegagalan cek versi tidak boleh menghentikan sync."""
        self._prime_state(5)

        def boom(*a, **kw):
            raise RuntimeError("rpc tidak tersedia")

        self.fake.get_personal_snapshot_versions = boom
        self.svc._pull_personal(self.uid)
        self.assertEqual(self.fake.get_snapshots_calls, 1)


class SuspensionTest(unittest.TestCase):
    """Fix 3: berhenti menembak project yang dibatasi."""

    def setUp(self):
        self.ctx = TempDatabase()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()

    def test_not_suspended_by_default(self):
        active, reason = self.db.cloud_suspension_active(UID)
        self.assertFalse(active)
        self.assertEqual(reason, "")

    def test_suspension_is_active_right_after_it_is_set(self):
        self.db.set_cloud_suspended(UID, "quota")
        active, reason = self.db.cloud_suspension_active(UID)
        self.assertTrue(active)
        self.assertEqual(reason, "quota")

    def test_suspension_survives_a_non_utc_timezone(self):
        """Regresi nyata yang ditemukan tes ini sendiri.

        SQLite `datetime('now')` menulis UTC tanpa penanda zona, sementara
        `datetime.now()` mengembalikan waktu lokal. Di zona Asia/Jakarta
        selisihnya 7 jam, jadi penangguhan langsung dianggap kedaluwarsa dan
        aplikasi TIDAK PERNAH berhenti menembak project yang dibatasi —
        seluruh Fix 3 jadi sia-sia. Tes ini dijalankan penuh di lingkungan
        ber-TZ UTC, sehingga tanpa pemaksaan UTC ia tetap hijau; karena itu
        zonanya dipindah secara eksplisit di sini.
        """
        import os
        import time

        self.db.set_cloud_suspended(UID, "quota")
        saved = os.environ.get("TZ")
        os.environ["TZ"] = "Asia/Jakarta"
        try:
            time.tzset()
            active, reason = self.db.cloud_suspension_active(UID)
            self.assertTrue(
                active,
                "penangguhan dianggap kedaluwarsa di zona non-UTC — "
                "perbandingan waktu lokal vs UTC")
            self.assertEqual(reason, "quota")
        finally:
            if saved is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = saved
            time.tzset()

    def test_suspension_expires_after_the_probe_window(self):
        self.db.set_cloud_suspended(UID, "quota")
        later = datetime.now() + timedelta(seconds=self.db.CLOUD_SUSPEND_PROBE_SECONDS + 60)
        active, reason = self.db.cloud_suspension_active(UID, now=later)
        self.assertFalse(active, "masa tunggu sudah lewat tapi masih menahan")
        self.assertEqual(reason, "quota")

    def test_clearing_removes_it(self):
        self.db.set_cloud_suspended(UID, "quota")
        self.db.clear_cloud_suspended(UID)
        active, _ = self.db.cloud_suspension_active(UID)
        self.assertFalse(active)

    def test_sync_now_does_not_touch_the_network_while_suspended(self):
        self.db.set_cloud_suspended(UID, "quota")
        sync_service = _fresh_sync_service()
        svc = sync_service.CloudSyncService()
        fake = _FakeCloud()
        svc.cloud = fake
        result = svc.sync_now(UID)
        self.assertEqual(result.get("code"), "cloud_suspended")
        self.assertEqual(fake.fetch_entities_calls, [],
                         "masih mengirim permintaan padahal sedang ditangguhkan")
        self.assertEqual(fake.get_snapshots_calls, 0)

    def test_force_retry_bypasses_the_wait(self):
        """Pengguna yang menekan tombol sync harus didengar."""
        self.db.set_cloud_suspended(UID, "quota")
        sync_service = _fresh_sync_service()
        svc = sync_service.CloudSyncService()
        fake = _FakeCloud()
        svc.cloud = fake
        svc.ensure_session = lambda uid: False
        result = svc.sync_now(UID, force_retry=True)
        self.assertNotEqual(result.get("code"), "cloud_suspended",
                            "force_retry masih ditahan oleh penangguhan")


class RetryCapTest(unittest.TestCase):
    """Fix 4: job dengan error permanen mati; error jaringan tidak."""

    def setUp(self):
        self.ctx = TempDatabase()
        self.ctx.__enter__()
        self.addCleanup(self.ctx.__exit__, None, None, None)
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user("quota_retry")
        conn = self.db.get_conn()
        conn.execute("INSERT INTO sync_queue(local_user_id,entity_type,entity_local_id,"
                     "operation,payload,status) VALUES(?,?,?,?,?,?)",
                     (self.uid, "notes", "1", "upsert", "{}", "pending"))
        conn.commit()
        self.job_id = conn.execute("SELECT id FROM sync_queue WHERE local_user_id=?",
                                   (self.uid,)).fetchone()[0]
        conn.close()

    def _status(self):
        conn = self.db.get_conn()
        row = conn.execute("SELECT status, retry_count FROM sync_queue WHERE id=?",
                           (self.job_id,)).fetchone()
        conn.close()
        return row["status"], int(row["retry_count"])

    def test_permanent_error_eventually_kills_the_job(self):
        for attempt in range(1, self.db.MAX_PERMANENT_RETRIES + 1):
            self.db.mark_sync_job_failed(self.job_id, "HTTP 402 Payment Required", attempt)
        status, _ = self._status()
        self.assertEqual(status, "failed",
                         "job dengan error permanen masih dicoba selamanya")

    def test_permanent_error_still_retries_below_the_cap(self):
        self.db.mark_sync_job_failed(self.job_id, "HTTP 402 Payment Required", 1)
        status, _ = self._status()
        self.assertEqual(status, "retry", "terlalu cepat dimatikan")

    def test_network_error_never_kills_the_job(self):
        """P6: mematikan job karena koneksi putus berarti kehilangan data."""
        for attempt in range(1, 40):
            self.db.mark_sync_job_failed(self.job_id, "connection refused", attempt)
        status, retries = self._status()
        self.assertEqual(status, "retry",
                         "job jaringan dimatikan setelah 40 percobaan — data bisa hilang")
        self.assertEqual(retries, 39)

    def test_permanent_markers_are_recognised(self):
        for text in ("402", "401", "403", "quota exceeded", "account_unavailable",
                     "unsupported_table", "invalid_jwt"):
            self.assertTrue(self.db.is_permanent_sync_error(text), text)

    def test_network_markers_are_not_permanent(self):
        for text in ("connection refused", "timed out", "temporary failure",
                     "database is locked"):
            self.assertFalse(self.db.is_permanent_sync_error(text), text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
