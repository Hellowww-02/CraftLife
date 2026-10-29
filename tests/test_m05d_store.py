"""M05d — lapisan penyimpanan diuji.

Yang paling menentukan di sini bukan "delegasi bekerja" — itu sepele. Yang
menentukan adalah **substituabilitas**: apakah implementasi KEDUA bisa melayani
`cloud_api` tanpa SQLite dan tanpa menyunting `cloud_api.py`. Sebuah abstraksi
yang bocor (satu panggilan `database` yang lolos, satu bentuk data yang
diasumsikan) akan gagal di tes itu, bukan di produksi nanti.

Tiga pin lain yang tidak kalah penting:

**Batas.** AST atas `cloud_api.py` harus nol referensi ke nama `db`. Kalau ada
yang menambahkan `database.foo()` lagi, build gagal — bukan review yang harus
menangkapnya.

**Paritas signature.** Signature setiap metode `CloudStorage` dibandingkan
dengan fungsi `database` yang sepadan. Tanpa ini, `database.py` bisa berubah
dan antarmuka menjadi basi diam-diam: delegasi tetap jalan hari ini, dan
implementasi lain dibangun di atas kontrak yang sudah tidak benar.

**Kelengkapan.** Himpunan operasi yang dideklarasikan harus sama dengan
himpunan yang benar-benar dipakai domain. Metode yang dideklarasikan tapi tidak
pernah dipakai adalah beban; operasi yang dipakai tapi tidak dideklarasikan
adalah kebocoran.
"""
from __future__ import annotations

import ast
import importlib
import inspect
import sys
import unittest
from pathlib import Path

import cloud_api
import database
import storage
from storage import CloudStorage, SqliteCloudStorage

from tests.harness import TempDatabase

ROOT = Path(__file__).resolve().parents[1]
CLOUD_API = ROOT / "cloud_api.py"


def _store_calls_in_cloud_api():
    """Himpunan nama operasi yang dipanggil domain lewat get_store()."""
    tree = ast.parse(CLOUD_API.read_text())
    names = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Call)
                and getattr(node.func.value.func, "id", "") == "get_store"):
            names.add(node.func.attr)
    return names


class FakeCloudStorage(CloudStorage):
    """Implementasi KEDUA, murni in-memory. Tidak menyentuh SQLite.

    Keberadaan kelas ini — dan kenyataan bahwa `cloud_api` melayaninya tanpa
    diubah — adalah bukti bahwa lapisan itu nyata.
    """

    def __init__(self):
        self.calls = []
        self.summary = {"pending": 3, "last_synced_at": "2026-10-11T00:00:00Z"}
        self.conflicts = [{"id": 99, "table_name": "habits", "field": "name"}]
        self.link = None

    def _log(self, name, *args):
        self.calls.append((name, args))

    def get_user(self, user_id):
        self._log("get_user", user_id)
        return {"id": user_id, "username": "fake"}

    def get_cloud_user_link(self, local_user_id):
        self._log("get_cloud_user_link", local_user_id)
        return self.link

    def get_cloud_service_state(self, local_user_id):
        self._log("get_cloud_service_state", local_user_id)
        return {}

    def cloud_suspension_active(self, local_user_id, now=None):
        self._log("cloud_suspension_active", local_user_id)
        return False, ""

    def get_or_create_cloud_device(self, local_user_id, app_version="1.0-phase3"):
        self._log("get_or_create_cloud_device", local_user_id)
        return {"id": "dev-1", "name": "FakeDevice"}

    def mark_cloud_device_registered(self, local_user_id, registered_at=None,
                                     last_seen_at=None):
        self._log("mark_cloud_device_registered", local_user_id)
        return True

    def rename_local_cloud_device(self, local_user_id, name):
        self._log("rename_local_cloud_device", local_user_id, name)
        return True

    def sync_status_summary(self, local_user_id):
        self._log("sync_status_summary", local_user_id)
        return dict(self.summary)

    def list_sync_conflicts(self, local_user_id, limit=50, include_restored=False):
        self._log("list_sync_conflicts", local_user_id, limit)
        return list(self.conflicts)

    def restore_sync_conflict(self, local_user_id, conflict_id):
        self._log("restore_sync_conflict", local_user_id, conflict_id)
        return {"ok": True}

    def get_cloud_wallet(self, user_id):
        self._log("get_cloud_wallet", user_id)
        return None

    def save_cloud_wallet(self, user_id, data):
        self._log("save_cloud_wallet", user_id)
        return True

    def get_cloud_inventory_cache(self, user_id):
        self._log("get_cloud_inventory_cache", user_id)
        return None

    def save_cloud_inventory(self, user_id, rows):
        self._log("save_cloud_inventory", user_id)
        return True

    def save_cloud_pets(self, user_id, payload):
        self._log("save_cloud_pets", user_id)
        return True

    def apply_cloud_spin_result(self, user_id, result, payload=None):
        self._log("apply_cloud_spin_result", user_id)
        return {"ok": True}

    def save_cloud_talents(self, user_id, payload):
        self._log("save_cloud_talents", user_id)
        return True

    def apply_cloud_talents(self, user_id, payload):
        self._log("apply_cloud_talents", user_id)
        return {"ok": True}

    def get_cloud_love_space_id(self, local_user_id):
        self._log("get_cloud_love_space_id", local_user_id)
        return None

    def mirror_cloud_love_record(self, local_user_id, record_type, row):
        self._log("mirror_cloud_love_record", local_user_id, record_type)
        return True

    def mirror_cloud_love_profile(self, local_user_id, row):
        self._log("mirror_cloud_love_profile", local_user_id)
        return True

    def add_love_space_photo(self, requester_user_id, image_data, mime_type,
                             width, height, caption='', photo_date=None,
                             visibility='private'):
        self._log("add_love_space_photo", requester_user_id)
        return {"id": 1}

    def get_maintenance_state(self, user_id):
        self._log("get_maintenance_state", user_id)
        return {"retention_days": 30, "auto": True, "last_purge_at": "",
                "schedule": "monthly", "backup_auto": True, "last_backup_at": ""}

    def set_maintenance_state(self, user_id, retention_days=None, auto=None,
                              schedule=None, backup_auto=None):
        self._log("set_maintenance_state", user_id, backup_auto)
        return None

    def mark_backup_done(self, user_id, when=None):
        self._log("mark_backup_done", user_id)
        return None

    def build_backup_snapshot(self, user_id):
        self._log("build_backup_snapshot", user_id)
        return {"version": 1, "tables": {"habits": []}}

    def import_backup_snapshot(self, user_id, data):
        self._log("import_backup_snapshot", user_id)
        return None

    def local_backup_before_restore(self):
        self._log("local_backup_before_restore")
        return "/tmp/fake_backup.db"


class BoundaryTest(unittest.TestCase):
    def test_cloud_api_no_longer_references_the_database_module(self):
        tree = ast.parse(CLOUD_API.read_text())
        refs = [n.lineno for n in ast.walk(tree)
                if isinstance(n, ast.Name) and n.id == "db"]
        self.assertEqual(refs, [], f"cloud_api.py masih menyentuh `db` di baris {refs}")

    def test_cloud_api_does_not_import_database(self):
        tree = ast.parse(CLOUD_API.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "database",
                                        "domain tidak boleh mengimpor database lagi")
            if isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "database")

    def test_every_storage_call_goes_through_get_store(self):
        names = _store_calls_in_cloud_api()
        self.assertGreaterEqual(len(names), 16,
                                f"hanya {len(names)} operasi lewat store; batas bocor")

    def test_declared_operations_match_operations_actually_used(self):
        declared = set(CloudStorage.__abstractmethods__)
        used = _store_calls_in_cloud_api()
        self.assertEqual(declared, used,
                         f"dideklarasikan tapi tak dipakai: {declared - used}; "
                         f"dipakai tapi tak dideklarasikan: {used - declared}")


class SignatureParityTest(unittest.TestCase):
    """Antarmuka tidak boleh basi terhadap database.py."""

    # Lapisan penyimpanan BOLEH menamai operasi berbeda dari fungsi yang
    # dilayaninya — itu justru gunanya abstraksi. Untuk yang dinamai ulang,
    # yang dipaku adalah targetnya tetap ada; paritas signature hanya berlaku
    # untuk operasi yang namanya memang sama.
    RENAMED = {
        "build_backup_snapshot": "build_cloud_personal_snapshot",
        "import_backup_snapshot": "import_tracker_data",
        "local_backup_before_restore": "backup_database",
    }

    def test_every_renamed_operation_still_points_at_a_real_function(self):
        missing = [f"{k} -> database.{v}" for k, v in self.RENAMED.items()
                   if not hasattr(database, v)]
        self.assertEqual(missing, [], f"target hilang: {missing}")

    def test_every_method_signature_matches_the_sqlite_function(self):
        mismatches = []
        for name in sorted(CloudStorage.__abstractmethods__):
            if name in self.RENAMED:
                continue
            target = getattr(database, name, None)
            if target is None:
                mismatches.append(f"{name}: database.{name} tidak ada")
                continue
            # Method terikat memuat `self`; fungsi modul tidak. Buang parameter
            # pertama sebelum membandingkan, kalau tidak setiap metode "menyimpang".
            a_params = list(inspect.signature(getattr(CloudStorage, name)).parameters.values())[1:]
            a = str(inspect.Signature(a_params))
            b = str(inspect.signature(target))
            if a != b:
                mismatches.append(f"{name}: antarmuka {a} vs database {b}")
        self.assertEqual(mismatches, [], "signature menyimpang:\n  " + "\n  ".join(mismatches))

    def test_sqlite_storage_is_concrete(self):
        store = SqliteCloudStorage()
        self.assertIsInstance(store, CloudStorage)

    def test_set_store_rejects_anything_else(self):
        storage.reset_store()
        self.addCleanup(storage.reset_store)
        with self.assertRaises(TypeError):
            storage.set_store(object())

    def test_get_store_defaults_to_sqlite_and_reset_restores_it(self):
        storage.reset_store()
        self.addCleanup(storage.reset_store)
        self.assertIsInstance(storage.get_store(), SqliteCloudStorage)
        storage.set_store(FakeCloudStorage())
        self.assertIsInstance(storage.get_store(), FakeCloudStorage)
        storage.reset_store()
        self.assertIsInstance(storage.get_store(), SqliteCloudStorage)


class SubstitutabilityTest(unittest.TestCase):
    """Domain dilayani implementasi in-memory, TANPA SQLite dan tanpa diubah."""

    def setUp(self):
        storage.reset_store()
        self.addCleanup(storage.reset_store)
        self.fake = FakeCloudStorage()
        storage.set_store(self.fake)
        self._sync = cloud_api.get_sync_service
        self._cloud = cloud_api.get_cloud_service

        class _NoSession:
            def ensure_session(self, uid):
                return False

            def cloud_status(self, uid):
                return {}

        cloud_api.get_sync_service = lambda: _NoSession()
        cloud_api.get_cloud_service = lambda: _NoSession()
        self.addCleanup(setattr, cloud_api, "get_sync_service", self._sync)
        self.addCleanup(setattr, cloud_api, "get_cloud_service", self._cloud)

    def test_sync_status_is_served_by_the_fake(self):
        out = cloud_api.handle_get("/api/cloud/sync-status", 42)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["pending"], 3)
        self.assertIn(("sync_status_summary", (42,)), self.fake.calls)

    def test_conflicts_are_served_by_the_fake(self):
        out = cloud_api.handle_get("/api/cloud/conflicts", 42)
        self.assertTrue(out["ok"], out)
        self.assertEqual(out["conflicts"][0]["table_name"], "habits")
        self.assertIn(("list_sync_conflicts", (42, 50)), self.fake.calls)

    def test_the_handler_never_touched_a_real_database(self):
        """Kalau ada satu panggilan database yang lolos, tes di atas akan
        membaca data sungguhan dan nilai `pending` tidak akan 3."""
        cloud_api.handle_get("/api/cloud/sync-status", 42)
        cloud_api.handle_get("/api/cloud/conflicts", 42)
        self.assertTrue(self.fake.calls, "domain tidak memanggil penyimpanan sama sekali")


class SqliteDelegationTest(unittest.TestCase):
    """Implementasi default harus benar-benar setara memanggil database.

    Jebakan yang harus ditangani di sini: `TempDatabase` mengimpor ulang modul
    `database` dan memasang `DB_PATH` di objek BARU itu. `storage` yang sudah
    diimpor di puncak file ini masih memegang modul yang LAMA, jadi tanpa
    re-bind di bawah, setiap perbandingan membandingkan database kosong dengan
    dirinya sendiri dan lulus tanpa membuktikan apa pun.
    """

    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.addCleanup(self._ctx.__exit__, None, None, None)
        self.ctx.db.init_db()
        self.uid = self.ctx.make_user("m05d")

        self._saved_storage = sys.modules.get("storage")
        sys.modules.pop("storage", None)
        self.storage = importlib.import_module("storage")
        self.addCleanup(self._restore_storage)
        self.store = self.storage.SqliteCloudStorage()

    def _restore_storage(self):
        sys.modules.pop("storage", None)
        if self._saved_storage is not None:
            sys.modules["storage"] = self._saved_storage

    def test_the_store_is_bound_to_the_fresh_database_module(self):
        """Pengawal untuk tes di bawah: kalau ini gagal, sisanya vakum."""
        self.assertIs(self.storage.db, self.ctx.db,
                      "storage masih memegang modul database yang lama")

    def test_get_user_returns_the_real_row(self):
        row = self.store.get_user(self.uid)
        self.assertEqual(row.get("username"), "m05d")
        self.assertEqual(row, self.ctx.db.get_user(self.uid))

    def test_get_cloud_user_link_matches_a_direct_call(self):
        self.assertEqual(self.store.get_cloud_user_link(self.uid),
                         self.ctx.db.get_cloud_user_link(self.uid))

    def test_get_or_create_cloud_device_writes_a_row(self):
        device = self.store.get_or_create_cloud_device(self.uid)
        self.assertTrue(device.get("device_id"), device)
        rows = self.ctx.raw().execute(
            "SELECT device_id FROM cloud_device_state WHERE local_user_id=?",
            (self.uid,)).fetchall()
        self.assertEqual(len(rows), 1, "baris perangkat tidak tersimpan")
        self.assertEqual(rows[0]["device_id"], device["device_id"])

    def test_get_or_create_cloud_device_is_stable_across_calls(self):
        first = self.store.get_or_create_cloud_device(self.uid)
        second = self.store.get_or_create_cloud_device(self.uid)
        self.assertEqual(first["device_id"], second["device_id"],
                         "device_id berubah antar panggilan — sinkronisasi akan "
                         "mengira ini perangkat baru setiap kali")

    def test_sync_status_summary_matches_a_direct_call(self):
        self.assertEqual(self.store.sync_status_summary(self.uid),
                         self.ctx.db.sync_status_summary(self.uid))

    def test_list_sync_conflicts_matches_a_direct_call(self):
        self.assertEqual(self.store.list_sync_conflicts(self.uid, 50),
                         self.ctx.db.list_sync_conflicts(self.uid, 50))

    def test_wallet_round_trip_through_the_store(self):
        self.store.save_cloud_wallet(self.uid, {"gold": 10})
        self.assertEqual(self.store.get_cloud_wallet(self.uid),
                         self.ctx.db.get_cloud_wallet(self.uid))


if __name__ == "__main__":
    unittest.main(verbosity=2)
