"""M05d — lapisan penyimpanan, dimulai dari domain cloud.

MASALAH YANG DITUTUP
--------------------
`cloud_api.py` memanggil `database.<fungsi>` langsung di 25 tempat. Selama
aplikasi ini hanya punya satu penyimpanan, itu tidak salah — hanya saja
menutup pintu: menukar SQLite ke Postgres untuk sisi server berarti menyunting
setiap pemanggilan di seluruh basis kode, sekaligus, dalam satu perubahan yang
tidak bisa diuji per bagian. Itu persis R3 (monolit 17k baris) bertemu R5
(menjadi internet-facing).

Lapisan ini menaruh nama operasi di satu tempat. Domain menyebut
`store.get_cloud_user_link(uid)`, bukan `database.get_cloud_user_link(uid)`.
Siapa pun yang mengimplementasikan `CloudStorage` bisa melayani domain itu.

YANG DIVERIFIKASI, DAN YANG TIDAK
---------------------------------
**Terverifikasi:** antarmuka ini nyata, bukan sekadar pengalihan. Buktinya ada
implementasi KEDUA di `tests/test_m05d_store.py` (penyimpanan in-memory) yang
melayani handler `cloud_api` tanpa SQLite sama sekali — dan `cloud_api.py`
tidak disentuh untuk membuatnya jalan. Sebuah abstraksi yang bocor akan gagal
di situ, bukan di produksi.

**TIDAK terverifikasi saat M05d, dan sekarang sudah dibayar:** tidak ada adapter
Postgres di sini, dan tidak pernah dijalankan. Adapter itu sekarang ada di
`storage_postgres.py`, diuji terhadap PostgreSQL 17 nyata di
`tests/test_m05_postgres_store.py`.

Koreksi atas catatan lama: teks sebelumnya menulis *"§8 melarang dependensi
baru"*. **Itu salah kutip.** §8 UPDATE_RULES.md adalah *Implementation rules
(engineering)* — delapan aturan soal partial update, idempotency, sanitasi,
formatter, CSS, a11y, performa, dan komentar; tidak satu pun menyebut
dependensi. Aturan yang benar-benar mengikat adalah **P1**: *"cloud (Supabase)
stays optional and never becomes a hard dependency."* Jadi `pg8000` boleh ada,
asal tidak wajib — dan memang diimpor di dalam `__init__`, bukan di tingkat
modul, sehingga mengimpor `storage` tanpa driver terpasang tetap berhasil.

`SqliteCloudStorage` murni delegasi. Tidak ada satu pun perubahan perilaku:
setiap metode memanggil fungsi `database` yang sama dengan argumen yang sama.
Itu disengaja — P4 menuntut desktop tidak bergeser sedikit pun.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod

import database as db


class CloudStorage(ABC):
    """Operasi persistensi yang dibutuhkan domain cloud.

    Signature setiap metode disalin persis dari `database.py` (diperiksa lewat
    `inspect.signature`, bukan ditulis dari ingatan), supaya `SqliteCloudStorage`
    bisa meneruskan argumen apa adanya dan implementasi lain tahu kontraknya.

    Sengaja TIDAK ada di sini: `get_cloud_service()` dan `get_sync_service()`.
    Keduanya klien jaringan, bukan penyimpanan. Mencampurnya ke lapisan ini
    akan membuat abstraksi penyimpanan diam-diam ikut melakukan I/O jaringan.
    """

    # -- identitas & tautan ------------------------------------------------
    @abstractmethod
    def get_user(self, user_id):
        """Baris pengguna lokal, atau None."""

    @abstractmethod
    def get_cloud_user_link(self, local_user_id):
        """Baris `cloud_user_links`, atau None bila belum ditautkan."""

    # -- perangkat ---------------------------------------------------------
    @abstractmethod
    def get_or_create_cloud_device(self, local_user_id, app_version="1.0-phase3"):
        """Baris perangkat lokal; dibuat bila belum ada."""

    @abstractmethod
    def mark_cloud_device_registered(self, local_user_id, registered_at=None,
                                     last_seen_at=None):
        """Catat bahwa perangkat sudah dikenal sisi cloud."""

    @abstractmethod
    def rename_local_cloud_device(self, local_user_id, name):
        """Ubah nama tampilan perangkat."""

    # -- status sinkronisasi ----------------------------------------------
    @abstractmethod
    def sync_status_summary(self, local_user_id):
        """Ringkasan status sync untuk panel UI."""

    @abstractmethod
    def list_sync_conflicts(self, local_user_id, limit=50, include_restored=False):
        """Konflik yang terdeteksi, terbaru dulu."""

    @abstractmethod
    def restore_sync_conflict(self, local_user_id, conflict_id):
        """Pulihkan sisi yang kalah dari sebuah konflik."""

    # -- cache dompet & inventaris ----------------------------------------
    @abstractmethod
    def get_cloud_wallet(self, user_id):
        """Cache dompet cloud, atau None."""

    @abstractmethod
    def save_cloud_wallet(self, user_id, data):
        """Tulis cache dompet cloud."""

    @abstractmethod
    def get_cloud_inventory_cache(self, user_id):
        """Cache inventaris cloud, atau None."""

    @abstractmethod
    def save_cloud_inventory(self, user_id, rows):
        """Tulis cache inventaris cloud."""

    @abstractmethod
    def save_cloud_pets(self, user_id, payload):
        """M09a: tulis cache koleksi pet cloud."""

    @abstractmethod
    def apply_cloud_spin_result(self, user_id, result, payload=None):
        """M09a: cerminkan hasil spin server ke tabel pet lokal."""

    @abstractmethod
    def save_cloud_talents(self, user_id, payload):
        """M09b: tulis cache talent cloud."""

    @abstractmethod
    def apply_cloud_talents(self, user_id, payload):
        """M09b: cerminkan talent cloud ke user_talents lokal."""

    # -- love space --------------------------------------------------------
    @abstractmethod
    def get_cloud_love_space_id(self, local_user_id):
        """ID love space sisi cloud, atau None."""

    @abstractmethod
    def mirror_cloud_love_record(self, local_user_id, record_type, row):
        """Cerminkan satu catatan love space dari cloud ke lokal."""

    @abstractmethod
    def mirror_cloud_love_profile(self, local_user_id, row):
        """Cerminkan profil love space dari cloud ke lokal."""

    @abstractmethod
    def add_love_space_photo(self, requester_user_id, image_data, mime_type,
                             width, height, caption='', photo_date=None,
                             visibility='private'):
        """Simpan foto love space."""


    # -- pemeliharaan data & backup cloud (P6) ---------------------------
    @abstractmethod
    def get_maintenance_state(self, user_id):
        """Status retensi, auto-clean, dan auto-backup pengguna."""

    @abstractmethod
    def set_maintenance_state(self, user_id, retention_days=None, auto=None,
                              schedule=None, backup_auto=None):
        """Ubah salah satu setelan pemeliharaan; yang None tidak disentuh."""

    @abstractmethod
    def mark_backup_done(self, user_id, when=None):
        """Catat kapan backup cloud terakhir berhasil."""

    @abstractmethod
    def build_backup_snapshot(self, user_id):
        """Snapshot seluruh tabel tracker, siap dikompresi dan diunggah.

        `allow_admin` dinyalakan di sini secara sengaja: backup itu baca-saja
        dan tidak menulis apa pun, jadi ia bukan vektor curang yang dijaga oleh
        larangan ekspor admin. Tanpa ini akun admin tidak punya cadangan sama
        sekali, dan itu melanggar P6.
        """

    @abstractmethod
    def import_backup_snapshot(self, user_id, data):
        """Tulis ulang data tracker dari sebuah snapshot. MERUSAK data sekarang."""

    @abstractmethod
    def local_backup_before_restore(self):
        """Salin file database lokal sebelum restore, supaya bisa kembali."""

    # -- status layanan cloud (kuota / penangguhan) ------------------------
    # Hanya dua op ini yang ada di ABC, karena hanya keduanya yang dipanggil
    # dari cloud_api.py. Penulisan status (set/clear/mark) dilakukan sync_service.py
    # yang memang memakai `database` langsung — memasukkannya ke sini akan
    # memaksa cloud_api memanggil sesuatu yang tidak dibutuhkannya hanya
    # supaya tes batas M05d tetap seimbang.
    @abstractmethod
    def get_cloud_service_state(self, local_user_id):
        """Baris status layanan cloud, atau {} bila belum ada."""


    @abstractmethod
    def cloud_suspension_active(self, local_user_id, now=None):
        """(aktif, alasan) — aktif True selama masa tunggu belum lewat."""




class SqliteCloudStorage(CloudStorage):
    """Implementasi default: delegasi langsung ke `database.py`.

    Tidak ada logika di sini, dan itu memang maksudnya. Setiap metode adalah
    satu panggilan terusan. Menaruh logika di lapisan ini akan menciptakan
    dua tempat yang harus benar secara bersamaan.
    """

    def get_user(self, user_id):
        return db.get_user(user_id)

    def get_cloud_user_link(self, local_user_id):
        return db.get_cloud_user_link(local_user_id)

    def get_or_create_cloud_device(self, local_user_id, app_version="1.0-phase3"):
        return db.get_or_create_cloud_device(local_user_id, app_version)

    def mark_cloud_device_registered(self, local_user_id, registered_at=None,
                                     last_seen_at=None):
        return db.mark_cloud_device_registered(local_user_id, registered_at, last_seen_at)

    def rename_local_cloud_device(self, local_user_id, name):
        return db.rename_local_cloud_device(local_user_id, name)

    def sync_status_summary(self, local_user_id):
        return db.sync_status_summary(local_user_id)

    def list_sync_conflicts(self, local_user_id, limit=50, include_restored=False):
        return db.list_sync_conflicts(local_user_id, limit, include_restored)

    def restore_sync_conflict(self, local_user_id, conflict_id):
        return db.restore_sync_conflict(local_user_id, conflict_id)

    def get_cloud_wallet(self, user_id):
        return db.get_cloud_wallet(user_id)

    def save_cloud_wallet(self, user_id, data):
        return db.save_cloud_wallet(user_id, data)

    def get_cloud_inventory_cache(self, user_id):
        return db.get_cloud_inventory_cache(user_id)

    def save_cloud_inventory(self, user_id, rows):
        return db.save_cloud_inventory(user_id, rows)

    def save_cloud_pets(self, user_id, payload):
        return db.save_cloud_pets(user_id, payload)

    def apply_cloud_spin_result(self, user_id, result, payload=None):
        return db.apply_cloud_spin_result(user_id, result, payload)

    def save_cloud_talents(self, user_id, payload):
        return db.save_cloud_talents(user_id, payload)

    def apply_cloud_talents(self, user_id, payload):
        return db.apply_cloud_talents(user_id, payload)

    def get_cloud_love_space_id(self, local_user_id):
        return db.get_cloud_love_space_id(local_user_id)

    def mirror_cloud_love_record(self, local_user_id, record_type, row):
        return db.mirror_cloud_love_record(local_user_id, record_type, row)

    def mirror_cloud_love_profile(self, local_user_id, row):
        return db.mirror_cloud_love_profile(local_user_id, row)

    def add_love_space_photo(self, requester_user_id, image_data, mime_type,
                             width, height, caption='', photo_date=None,
                             visibility='private'):
        return db.add_love_space_photo(requester_user_id, image_data, mime_type,
                                       width, height, caption, photo_date, visibility)

    def get_maintenance_state(self, user_id):
        return db.get_maintenance_state(user_id)

    def set_maintenance_state(self, user_id, retention_days=None, auto=None,
                              schedule=None, backup_auto=None):
        return db.set_maintenance_state(user_id, retention_days, auto, schedule,
                                        backup_auto)

    def mark_backup_done(self, user_id, when=None):
        return db.mark_backup_done(user_id, when)

    def build_backup_snapshot(self, user_id):
        return db.build_cloud_personal_snapshot(user_id, allow_admin=True)

    def import_backup_snapshot(self, user_id, data):
        return db.import_tracker_data(user_id, data)

    def local_backup_before_restore(self):
        return db.backup_database()

    def get_cloud_service_state(self, local_user_id):
        return db.get_cloud_service_state(local_user_id)



    def cloud_suspension_active(self, local_user_id, now=None):
        return db.cloud_suspension_active(local_user_id, now)


# ---------------------------------------------------------------------------
# Titik akses
# ---------------------------------------------------------------------------

_store: CloudStorage | None = None
_lock = threading.Lock()


def get_store() -> CloudStorage:
    """Penyimpanan aktif. SQLite secara default.

    Sengaja fungsi, bukan objek module-level yang diimpor langsung: pemanggil
    harus melewatkannya tiap kali supaya implementasi bisa ditukar saat proses
    berjalan (untuk tes, dan untuk adapter masa depan) tanpa memuat ulang modul.
    """
    global _store
    with _lock:
        if _store is None:
            _store = SqliteCloudStorage()
        return _store


def set_store(store: CloudStorage) -> None:
    """Pasang implementasi lain. Hanya untuk tes dan adapter masa depan."""
    global _store
    if not isinstance(store, CloudStorage):
        raise TypeError(f"{type(store).__name__} bukan CloudStorage")
    with _lock:
        _store = store


def reset_store() -> None:
    """Kembalikan ke default. Dipanggil oleh tearDown tes."""
    global _store
    with _lock:
        _store = None
