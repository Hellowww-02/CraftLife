"""M05 butir 3 — adapter Postgres diuji ke PostgreSQL nyata, bukan diejek.

Butir roadmapnya: *"Ganti store SQLite → Postgres, satu domain pada satu waktu."*
M05d membangun lapisannya dan dengan jujur menulis bahwa adapter Postgresnya
tidak ada. `storage_postgres.py` membayarnya; file ini membuktikannya.

Kenapa tes ini tidak memakai mock
---------------------------------
Sebuah adapter SQL yang diuji terhadap mock hanya membuktikan bahwa mock-nya
cocok dengan harapan penulisnya. Di sini server PostgreSQL 17 sungguhan
dinyalakan lewat harness yang sama dengan gate `supabase-sql`, skema dibuat, dan
setiap operasi dijalankan. Kalau SQL-nya salah sintaks, tes ini yang tahu.

Paritas, bukan sekadar "jalan"
------------------------------
Untuk operasi yang juga ada di SQLite, hasilnya **dibandingkan** dengan backend
SQLite: nilai default maintenance, penolakan jadwal yang tidak sah, kode-kode
`restore_sync_conflict`, dan bentuk snapshot. Adapter yang menyimpang diam-diam
akan tertangkap di sini.

Yang diuji soal "opsional" (P1)
-------------------------------
Postgres tidak boleh menjadi dependensi wajib. Tiga tes menguncinya: modul
tetap bisa diimpor tanpa `pg8000`, `from_env()` mengembalikan None saat tidak
dikonfigurasi, dan `storage.get_store()` tetap SQLite secara default.
"""
from __future__ import annotations

import builtins
import importlib
import os
import pathlib
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "pg_harness"))

UID = 7
OTHER = 8

try:
    import pg8000  # noqa: F401
    HAVE_DRIVER = True
except ImportError:
    HAVE_DRIVER = False

try:
    import run as H
    HAVE_PG = bool(H.find_pg_bin())
except Exception:
    HAVE_PG = False


class OptionalDependencyTest(unittest.TestCase):
    """P1: Postgres tidak pernah menjadi dependensi wajib."""

    def test_module_imports_without_the_driver_installed(self):
        """Menyembunyikan pg8000 tidak boleh membuat import gagal."""
        real = builtins.__import__

        def fake(name, *a, **kw):
            if name.split(".")[0] == "pg8000":
                raise ImportError("disembunyikan oleh tes")
            return real(name, *a, **kw)

        for mod in ("storage_postgres",):
            sys.modules.pop(mod, None)
        builtins.__import__ = fake
        try:
            mod = importlib.import_module("storage_postgres")
            self.assertTrue(hasattr(mod, "PostgresCloudStorage"))
        finally:
            builtins.__import__ = real
            sys.modules.pop("storage_postgres", None)
            importlib.import_module("storage_postgres")

    def test_constructing_without_the_driver_names_the_package(self):
        """Gagalnya harus menyebut pg8000, bukan traceback misterius."""
        import storage_postgres as sp
        real = builtins.__import__

        def fake(name, *a, **kw):
            if name.split(".")[0] == "pg8000":
                raise ImportError("disembunyikan oleh tes")
            return real(name, *a, **kw)

        builtins.__import__ = fake
        try:
            with self.assertRaises(RuntimeError) as cm:
                sp.PostgresCloudStorage()
        finally:
            builtins.__import__ = real
        self.assertIn("pg8000", str(cm.exception))

    def test_from_env_returns_none_when_not_configured(self):
        import storage_postgres as sp
        saved = os.environ.pop("CRAFTLIFE_STORAGE_BACKEND", None)
        try:
            self.assertIsNone(sp.from_env())
        finally:
            if saved is not None:
                os.environ["CRAFTLIFE_STORAGE_BACKEND"] = saved

    def test_default_store_is_still_sqlite(self):
        import storage
        from storage import SqliteCloudStorage
        storage.reset_store()
        self.addCleanup(storage.reset_store)
        self.assertIsInstance(storage.get_store(), SqliteCloudStorage)

    def test_set_store_accepts_the_postgres_class(self):
        """ABC-nya lengkap, jadi kelasnya bisa dipasang sebagai store."""
        import storage
        import storage_postgres as sp
        self.assertTrue(issubclass(sp.PostgresCloudStorage, storage.CloudStorage))
        missing = storage.CloudStorage.__abstractmethods__ - set(
            n for n in dir(sp.PostgresCloudStorage) if not n.startswith("_"))
        self.assertEqual(missing, set(), f"op belum diimplementasikan: {missing}")


@unittest.skipUnless(HAVE_DRIVER, "pg8000 tidak terpasang")
@unittest.skipUnless(HAVE_PG, "binari PostgreSQL tidak tersedia")
class PostgresBackendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import storage_postgres as sp
        cls.sp = sp
        cls.cluster = H.Cluster(H.find_pg_bin())
        cls.cluster.start()
        cls.store = sp.PostgresCloudStorage(
            unix_sock=os.path.join(cls.cluster.sock, ".s.PGSQL." + str(cls.cluster.port)),
            database=cls.cluster.db, user=cls.cluster.user)
        # Tabel target restore. Sengaja dibuat di tes, bukan di ensure_schema:
        # tabel SYNC_TABLES milik domain tracker, bukan domain cloud.
        cls.store._exec(
            "CREATE TABLE IF NOT EXISTS notes(id SERIAL PRIMARY KEY, uuid TEXT,"
            " user_id INTEGER, content TEXT, updated_at TEXT)")

    @classmethod
    def tearDownClass(cls):
        cls.store.close()
        cls.cluster.stop()

    def setUp(self):
        """Setiap tes mulai dari keadaan bersih.

        Cluster-nya dipakai bersama seumur kelas, jadi tanpa ini satu tes
        mewarisi baris tes lain — persis yang membuat tes wallet gagal setelah
        tes restore menjalankan lebih dulu.
        """
        for t in ("cloud_user_links", "cloud_device_state", "cloud_wallet_cache",
                  "cloud_inventory_cache", "maintenance_state", "sync_conflicts",
                  "sync_queue", "sync_tombstones", "sync_entities", "love_spaces",
                  "love_space_photos", "relationship_mirror", "notes",
                  "personal_snapshots"):
            self.store._exec(f"DELETE FROM {t}")

    # -- identitas & tautan ------------------------------------------------
    def test_get_user_is_empty_dict_when_absent(self):
        self.assertEqual(self.store.get_user(9999), {})

    def test_cloud_user_link_roundtrip(self):
        self.assertEqual(self.store.get_cloud_user_link(UID), {})
        self.store._exec(
            "INSERT INTO cloud_user_links(local_user_id, cloud_user_id, email, status)"
            " VALUES(%s,%s,%s,%s)", (UID, "uuid-awan", "a@b.c", "linked"))
        row = self.store.get_cloud_user_link(UID)
        self.assertEqual(row["cloud_user_id"], "uuid-awan")
        self.assertEqual(row["status"], "linked")

    def test_device_is_created_once_and_is_stable(self):
        first = self.store.get_or_create_cloud_device(UID, "1.7.4")
        second = self.store.get_or_create_cloud_device(UID, "9.9.9")
        self.assertEqual(first["device_id"], second["device_id"],
                         "device_id berubah pada panggilan kedua — tidak stabil")
        self.assertEqual(second["app_version"], "1.7.4",
                         "panggilan kedua menimpa app_version")

    def test_rename_and_register_device(self):
        self.store.get_or_create_cloud_device(UID)
        self.store.rename_local_cloud_device(UID, "HP Android")
        self.assertEqual(self.store.get_or_create_cloud_device(UID)["device_name"],
                         "HP Android")
        self.store.mark_cloud_device_registered(UID)
        row = self.store.get_or_create_cloud_device(UID)
        self.assertTrue(row["registered_at"], "registered_at tidak terisi")
        self.assertTrue(row["last_seen_at"], "last_seen_at tidak terisi")

    # -- maintenance: paritas dengan SQLite --------------------------------
    def test_maintenance_defaults_match_sqlite(self):
        """Kedua backend harus menjawab sama untuk pengguna tanpa baris."""
        from tests.harness import TempDatabase
        ctx = TempDatabase()
        ctx.__enter__()
        # addCleanup butuh argumen exception-nya; tanpa itu __exit__ gagal dan
        # koneksi SQLite-nya bocor.
        self.addCleanup(ctx.__exit__, None, None, None)
        # ctx.db adalah modul `database` BARU hasil rebind harness; memakai
        # `import database` di sini akan memegang objek yang sudah basi.
        ctx.db.init_db()
        sqlite_state = ctx.db.get_maintenance_state(4242)
        pg_state = self.store.get_maintenance_state(4242)
        self.assertEqual(pg_state, sqlite_state,
                         "nilai default maintenance berbeda antar backend")
        self.assertEqual(pg_state["retention_days"], 30)
        self.assertTrue(pg_state["backup_auto"])

    def test_invalid_schedule_rejected_the_same_way(self):
        with self.assertRaises(ValueError) as cm:
            self.store.set_maintenance_state(UID, schedule="tahunan")
        self.assertEqual(str(cm.exception), "schedule_invalid")

    def test_retention_zero_is_preserved_not_defaulted(self):
        """P62: retention 0 berarti nonaktif dan tidak boleh jadi 30."""
        self.store.set_maintenance_state(UID, retention_days=0, auto=False)
        state = self.store.get_maintenance_state(UID)
        self.assertEqual(state["retention_days"], 0)
        self.assertFalse(state["auto"])

    def test_partial_update_does_not_clobber(self):
        """§8.1: field yang tidak dikirim tidak boleh menghapus yang lama."""
        self.store.set_maintenance_state(UID, retention_days=14, schedule="weekly",
                                         auto=True)
        self.store.set_maintenance_state(UID, backup_auto=False)
        state = self.store.get_maintenance_state(UID)
        self.assertEqual(state["retention_days"], 14, "retention_days terhapus")
        self.assertEqual(state["schedule"], "weekly", "schedule terhapus")
        self.assertFalse(state["backup_auto"])

    def test_mark_backup_done_is_idempotent(self):
        self.store.mark_backup_done(UID, "2026-10-12 01:02:03")
        self.store.mark_backup_done(UID, "2026-10-12 04:05:06")
        state = self.store.get_maintenance_state(UID)
        self.assertEqual(state["last_backup_at"], "2026-10-12 04:05:06")
        n = self.store._one("SELECT COUNT(*) AS c FROM maintenance_state"
                            " WHERE user_id=%s", (UID,))["c"]
        self.assertEqual(int(n), 1, "mark_backup_done menduplikasi baris")

    # -- cache cloud -------------------------------------------------------
    def test_wallet_roundtrip_and_update(self):
        self.assertIsNone(self.store.get_cloud_wallet(UID))
        self.store.save_cloud_wallet(UID, {"xp": 10, "gold": 20, "gems": 1, "level": 2})
        w = self.store.get_cloud_wallet(UID)
        self.assertEqual((w["xp"], w["gold"], w["gems"], w["level"]), (10, 20, 1, 2))
        self.store.save_cloud_wallet(UID, {"xp": 99, "gold": 0, "gems": 0, "level": 3})
        w = self.store.get_cloud_wallet(UID)
        self.assertEqual(w["xp"], 99, "upsert tidak memperbarui")
        n = self.store._one("SELECT COUNT(*) AS c FROM cloud_wallet_cache"
                            " WHERE user_id=%s", (UID,))["c"]
        self.assertEqual(int(n), 1)

    def test_inventory_replaces_rather_than_appends(self):
        self.store.save_cloud_inventory(UID, [{"item_key": "pedang", "qty": 1}])
        self.store.save_cloud_inventory(UID, [{"item_key": "perisai", "qty": 2,
                                               "equipped": True, "enchant_level": 3}])
        rows = self.store.get_cloud_inventory_cache(UID)
        self.assertEqual([r["item_key"] for r in rows], ["perisai"],
                         "save_cloud_inventory menambah, bukan mengganti")
        self.assertEqual(rows[0]["equipped"], 1)
        self.assertEqual(rows[0]["enchant_level"], 3)

    # -- konflik sync ------------------------------------------------------
    def _add_conflict(self, cid, table="notes", field="content", restored=None,
                      detected="2026-10-01 00:00:00"):
        self.store._exec(
            "INSERT INTO sync_conflicts(local_user_id,table_name,entity_uuid,field,"
            "kept_value,lost_value,kept_side,detected_at,restored_at)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (UID, table, cid, field, "baru", "lama", "local", detected, restored))
        return self.store._one(
            "SELECT id FROM sync_conflicts WHERE entity_uuid=%s", (cid,))["id"]

    def test_conflict_list_hides_restored_unless_asked(self):
        self.store._exec("DELETE FROM sync_conflicts WHERE local_user_id=%s", (UID,))
        self._add_conflict("c-aktif")
        self._add_conflict("c-lama", restored="2026-10-02 00:00:00")
        self.assertEqual(len(self.store.list_sync_conflicts(UID)), 1)
        self.assertEqual(len(self.store.list_sync_conflicts(UID, include_restored=True)), 2)

    def test_restore_returns_the_documented_codes(self):
        self.store._exec("DELETE FROM sync_conflicts WHERE local_user_id=%s", (UID,))
        self.assertEqual(
            self.store.restore_sync_conflict(UID, 987654)["code"], "conflict_not_found")

        cid = self._add_conflict("c-field-aneh", field="kolom_yang_tidak_ada")
        self.assertEqual(self.store.restore_sync_conflict(UID, cid)["code"],
                         "unknown_field")

        cid = self._add_conflict("c-tak-ada-baris")
        self.assertEqual(self.store.restore_sync_conflict(UID, cid)["code"],
                         "entity_not_found")

    def test_restore_writes_the_losing_value_back(self):
        self.store._exec("DELETE FROM notes")
        self.store._exec("DELETE FROM sync_conflicts WHERE local_user_id=%s", (UID,))
        self.store._exec(
            "INSERT INTO notes(uuid, user_id, content, updated_at)"
            " VALUES(%s,%s,%s,%s)", ("u-1", UID, "nilai baru", "2026-10-01 00:00:00"))
        cid = self._add_conflict("u-1")
        res = self.store.restore_sync_conflict(UID, cid)
        self.assertTrue(res["ok"], res)
        self.assertEqual(res["value"], "lama")
        row = self.store._one("SELECT content FROM notes WHERE uuid='u-1'")
        self.assertEqual(row["content"], "lama", "nilai yang kalah tidak ditulis balik")
        again = self.store.restore_sync_conflict(UID, cid)
        self.assertEqual(again["code"], "already_restored")

    def test_restore_refuses_a_table_outside_sync_tables(self):
        self.store._exec("DELETE FROM sync_conflicts WHERE local_user_id=%s", (UID,))
        cid = self._add_conflict("c-bukan-sync", table="cloud_wallet_cache")
        self.assertEqual(self.store.restore_sync_conflict(UID, cid)["code"],
                         "unsupported_table")

    # -- sync status -------------------------------------------------------
    def test_sync_status_counts_queue_conflicts_and_entities(self):
        self.store._exec("DELETE FROM sync_queue WHERE local_user_id=%s", (UID,))
        self.store._exec("DELETE FROM sync_tombstones WHERE local_user_id=%s", (UID,))
        self.store._exec("DELETE FROM sync_entities WHERE local_user_id=%s", (UID,))
        self.store._exec("DELETE FROM sync_conflicts WHERE local_user_id=%s", (UID,))
        for status in ("pending", "pending", "retry", "done"):
            self.store._exec(
                "INSERT INTO sync_queue(local_user_id,entity_type,operation,status,"
                "retry_count,last_error,next_retry_at) VALUES(%s,'notes','upsert',%s,0,'','')",
                (UID, status))
        self.store._exec("INSERT INTO sync_entities(local_user_id,entity_uuid,"
                         "table_name,revision,acknowledged) VALUES(%s,'e1','notes',1,FALSE)",
                         (UID,))
        self.store._exec("INSERT INTO sync_tombstones(local_user_id,table_name,"
                         "entity_uuid,deleted_at,pushed_at) VALUES(%s,'notes','t1','x',NULL)",
                         (UID,))
        self._add_conflict("c-status")
        s = self.store.sync_status_summary(UID)
        self.assertEqual(s["pending"], 3, "2 antrean + 1 entitas belum diakui")
        self.assertEqual(s["retry"], 1)
        self.assertEqual(s["done"], 1)
        self.assertEqual(s["unresolvedConflicts"], 1)
        self.assertEqual(s["pendingTombstones"], 1)

    # -- love space --------------------------------------------------------
    def test_love_space_photo_uses_the_users_own_space(self):
        self.assertIsNone(self.store.get_cloud_love_space_id(UID))
        self.store._exec("INSERT INTO love_spaces(local_user_id, cloud_space_id)"
                         " VALUES(%s,%s)", (UID, "space-1"))
        self.assertEqual(self.store.get_cloud_love_space_id(UID), "space-1")
        res = self.store.add_love_space_photo(UID, "BASE64", "image/png", 10, 20,
                                              caption="liburan")
        self.assertTrue(res["ok"])
        row = self.store._one("SELECT * FROM love_space_photos WHERE id=%s",
                              (res["photoId"],))
        self.assertEqual(row["space_id"], "space-1")
        self.assertEqual(row["caption"], "liburan")

    def test_love_mirror_is_idempotent(self):
        """§8.2: memicu dua kali tidak boleh menduplikasi."""
        self.store.mirror_cloud_love_profile(UID, {"nickname": "ayang"})
        self.store.mirror_cloud_love_profile(UID, {"nickname": "ayang2"})
        rows = self.store._rows(
            "SELECT * FROM relationship_mirror WHERE local_user_id=%s"
            " AND record_type='profile'", (UID,))
        self.assertEqual(len(rows), 1, "mirror profil menduplikasi baris")
        self.assertIn("ayang2", rows[0]["payload"])

        self.store.mirror_cloud_love_record(UID, "memories", {"id": 5, "t": "a"})
        self.store.mirror_cloud_love_record(UID, "memories", {"id": 5, "t": "b"})
        rows = self.store._rows(
            "SELECT * FROM relationship_mirror WHERE local_user_id=%s"
            " AND record_type='memories'", (UID,))
        self.assertEqual(len(rows), 1)

    # -- snapshot & backup -------------------------------------------------
    def test_snapshot_contains_every_declared_table(self):
        snap = self.store.build_backup_snapshot(UID)
        self.assertEqual(set(snap["tables"]), set(self.store.SNAPSHOT_TABLES))
        self.assertEqual(snap["localUserId"], UID)
        self.assertTrue(snap["createdAt"])

    def test_incomplete_snapshot_is_refused(self):
        snap = self.store.build_backup_snapshot(UID)
        del snap["tables"]["cloud_wallet_cache"]
        with self.assertRaises(ValueError) as cm:
            self.store.import_backup_snapshot(UID, snap)
        self.assertIn("cloud_wallet_cache", str(cm.exception))

    def test_restore_takes_a_local_backup_first(self):
        """P6: tidak ada restore tanpa jalan kembali."""
        before = self.store.restore_backup_count()
        self.store.import_backup_snapshot(UID, self.store.build_backup_snapshot(UID))
        self.assertEqual(self.store.restore_backup_count(), before + 1,
                         "restore berjalan tanpa membuat cadangan lokal")

    def test_restore_actually_puts_data_back(self):
        self.store.save_cloud_wallet(UID, {"xp": 111, "gold": 222, "gems": 3, "level": 4})
        snap = self.store.build_backup_snapshot(UID)
        self.store._exec("DELETE FROM cloud_wallet_cache WHERE user_id=%s", (UID,))
        self.assertIsNone(self.store.get_cloud_wallet(UID), "prasyarat: data dihapus")
        self.store.import_backup_snapshot(UID, snap)
        w = self.store.get_cloud_wallet(UID)
        self.assertIsNotNone(w, "restore tidak mengembalikan wallet")
        self.assertEqual(w["xp"], 111)
        self.assertEqual(w["gold"], 222)


if __name__ == "__main__":
    unittest.main(verbosity=2)
