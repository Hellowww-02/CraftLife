"""M05 butir 3 — backend Postgres untuk lapisan penyimpanan domain cloud.

M05d menaruh 22 nama operasi di satu tempat (`storage.CloudStorage`) dan dengan
jujur mencatat batasnya sendiri: *"tidak ada adapter Postgres di sini ... Adapter
itu, dan keputusan penyimpanannya, milik M05e."* File ini membayar utang itu.

Kenapa sekarang bisa, padahal dulu tidak
----------------------------------------
Docstring M05d menyebut "§8 melarang dependensi baru". **Itu salah kutip, dan
sudah diperbaiki di `storage.py`.** §8 UPDATE_RULES.md adalah *Implementation
rules (engineering)* — delapan aturan soal partial update, idempotency,
sanitasi, formatter, CSS, a11y, performa, dan komentar. Tidak ada satu kata pun
tentang dependensi. Aturan yang benar-benar mengikat di sini adalah **P1**:
*"cloud (Supabase) stays optional and never becomes a hard dependency."*

Jadi syaratnya bukan "jangan pakai Postgres", melainkan **jangan sampai wajib**.
File ini memenuhinya:

* `pg8000` diimpor di dalam `__init__`, bukan di tingkat modul. Mengimpor
  `storage` atau `storage_postgres` tanpa driver terpasang tidak pernah gagal.
* Kegagalan muncul sebagai `RuntimeError` yang menyebut nama paketnya, saat
  adapter benar-benar diminta.
* `storage.get_store()` tetap mengembalikan `SqliteCloudStorage` kecuali seseorang
  memanggil `set_store()` secara eksplisit. Desktop tidak bergeser sedikit pun.
* `requirements.txt` mencatat `pg8000` di bagian opsional, bukan wajib.

Cakupan, dinyatakan apa adanya
------------------------------
Roadmap menulis *"satu domain pada satu waktu mengikuti pemisahan 4 modul"*.
Domain yang dikerjakan di sini adalah **cloud** — persis 22 operasi yang
dipakai `cloud_api.py`. Tiga modul lain (`api_server`, `life_api`, `studio_api`)
tetap di SQLite, dan itu sesuai butirnya, bukan pengabaian.

Skema Postgres di sini **mencerminkan tabel domain cloud milik SQLite**, bukan
skema sosial Supabase yang 56 tabel itu. Keduanya melayani tujuan berbeda:
Supabase adalah sumber resmi data bersama, adapter ini adalah tempat server
menyimpan keadaan per-pengguna.

Tiga operasi SQLite menyentuh hal yang tidak ada padanannya di Postgres, dan
ketiganya diperlakukan jujur, bukan disamarkan:

* `local_backup_before_restore` — SQLite menyalin *file*. Postgres tidak punya
  file untuk disalin, jadi adapter membuat salinan logis ke tabel bertanda
  waktu. Sifatnya sama (bisa kembali), caranya berbeda.
* `sync_status_summary` — versi SQLite menghitung `pending_entities` dari 34
  tabel Kanal B lewat `pending_entity_change_count`. Adapter menghitungnya dari
  tabel `sync_entities` miliknya sendiri.
* `mirror_cloud_love_record` — versi SQLite menulis ke 7 tabel relationship
  dengan kolom spesifik. Adapter menyimpan baris cloud apa adanya sebagai JSON
  bertype, idempoten, tanpa menduplikasi 7 skema tabel.

Semua 22 operasi diuji dengan menjalankan **operasi yang sama di kedua backend**
dan membandingkan hasilnya — lihat `tests/test_m05_postgres_store.py`.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone

from storage import CloudStorage

_SCHEDULE_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}

#: Tabel yang boleh disentuh `restore_sync_conflict`. Disalin dari
#: `database.SYNC_TABLES` saat runtime, bukan ditulis ulang di sini.
def _sync_tables() -> set:
    import database as db
    return set(getattr(db, "SYNC_TABLES", ()) or ())


def _now() -> str:
    """Format teks yang sama dengan `datetime('now')` milik SQLite."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


DDL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT, display_name TEXT,
    is_admin INTEGER DEFAULT 0, cloud_user_id TEXT, created_at TEXT,
    gold DOUBLE PRECISION DEFAULT 0, talent_points_spent INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cloud_user_links (
    local_user_id INTEGER PRIMARY KEY,
    cloud_user_id TEXT, email TEXT, status TEXT, linked_at TEXT, last_sync_at TEXT
);
CREATE TABLE IF NOT EXISTS cloud_device_state (
    local_user_id INTEGER PRIMARY KEY,
    device_id TEXT, device_name TEXT, platform TEXT, app_version TEXT,
    registered_at TEXT, last_seen_at TEXT
);
CREATE TABLE IF NOT EXISTS cloud_wallet_cache (
    user_id INTEGER PRIMARY KEY,
    xp INTEGER, gold INTEGER, gems INTEGER, level INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS cloud_inventory_cache (
    id SERIAL PRIMARY KEY,
    user_id INTEGER, item_key TEXT, qty INTEGER, equipped INTEGER,
    enchant_level INTEGER, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS cloud_pets_cache (
    id SERIAL PRIMARY KEY,
    user_id INTEGER, pet_key TEXT, level INTEGER, exp INTEGER,
    hunger INTEGER, happiness INTEGER, is_active INTEGER, updated_at TEXT,
    UNIQUE(user_id, pet_key)
);
CREATE TABLE IF NOT EXISTS cloud_pet_spin_state_cache (
    user_id INTEGER PRIMARY KEY,
    spins_total INTEGER, since_epic INTEGER, since_legendary INTEGER,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS user_pets (
    id SERIAL PRIMARY KEY,
    user_id INTEGER, pet_id TEXT, is_active INTEGER DEFAULT 0,
    happiness INTEGER DEFAULT 50, level INTEGER DEFAULT 1, exp INTEGER DEFAULT 0,
    hunger INTEGER DEFAULT 100, last_fed TEXT, adopted_at TEXT
);
CREATE TABLE IF NOT EXISTS pet_spin_state (
    user_id INTEGER PRIMARY KEY,
    spins_total INTEGER DEFAULT 0, since_epic INTEGER DEFAULT 0,
    since_legendary INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS cloud_talents_cache (
    id SERIAL PRIMARY KEY,
    user_id INTEGER, talent_key TEXT, updated_at TEXT,
    UNIQUE(user_id, talent_key)
);
CREATE TABLE IF NOT EXISTS user_talents (
    user_id INTEGER, talent_key TEXT,
    PRIMARY KEY (user_id, talent_key)
);
CREATE TABLE IF NOT EXISTS maintenance_state (
    user_id INTEGER PRIMARY KEY,
    retention_days INTEGER DEFAULT 30, auto INTEGER DEFAULT 1,
    last_purge_at TEXT, schedule TEXT DEFAULT 'monthly',
    last_backup_at TEXT, backup_auto INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sync_conflicts (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, table_name TEXT, entity_uuid TEXT, field TEXT,
    kept_value TEXT, lost_value TEXT, kept_side TEXT,
    detected_at TEXT, restored_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_queue (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, entity_type TEXT, operation TEXT, status TEXT,
    retry_count INTEGER DEFAULT 0, last_error TEXT, next_retry_at TEXT
);
CREATE TABLE IF NOT EXISTS sync_tombstones (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, table_name TEXT, entity_uuid TEXT,
    deleted_at TEXT, pushed_at TEXT
);
CREATE TABLE IF NOT EXISTS cloud_personal_sync_state (
    local_user_id INTEGER PRIMARY KEY,
    last_pushed_at TEXT, last_pulled_at TEXT, remote_revision BIGINT DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sync_entities (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, entity_uuid TEXT, table_name TEXT,
    revision BIGINT DEFAULT 0, acknowledged BOOLEAN DEFAULT FALSE
);
CREATE TABLE IF NOT EXISTS love_spaces (
    id SERIAL PRIMARY KEY, local_user_id INTEGER, cloud_space_id TEXT
);
CREATE TABLE IF NOT EXISTS love_space_photos (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, space_id TEXT, image_data TEXT, mime_type TEXT,
    width INTEGER, height INTEGER, caption TEXT, photo_date TEXT, visibility TEXT
);
CREATE TABLE IF NOT EXISTS relationship_mirror (
    id SERIAL PRIMARY KEY,
    local_user_id INTEGER, record_type TEXT, row_id TEXT, payload TEXT,
    updated_at TEXT,
    UNIQUE (local_user_id, record_type, row_id)
);
CREATE TABLE IF NOT EXISTS personal_snapshots (
    local_user_id INTEGER PRIMARY KEY, payload TEXT, revision BIGINT DEFAULT 1
);
CREATE TABLE IF NOT EXISTS cloud_service_state (
    local_user_id INTEGER PRIMARY KEY,
    suspended_reason TEXT, suspended_at TEXT, last_probe_at TEXT
);
"""


class PostgresCloudStorage(CloudStorage):
    """Backend Postgres untuk 22 operasi domain cloud.

    Murni SQL. Tidak ada delegasi ke `database.py` — kalau ada, tes paritas
    hanya akan membandingkan SQLite dengan dirinya sendiri dan tidak membuktikan
    apa pun.
    """

    def __init__(self, host=None, port=None, database=None, user=None,
                 password=None, unix_sock=None):
        try:
            import pg8000.dbapi as pg
        except ImportError as exc:  # pragma: no cover - bergantung lingkungan
            raise RuntimeError(
                "pg8000 tidak terpasang; adapter Postgres bersifat OPSIONAL "
                "(P1). Pasang dengan `pip install pg8000`, atau biarkan "
                "SqliteCloudStorage sebagai default."
            ) from exc
        self._pg = pg
        # Socket Unix didahulukan kalau diberikan: harness PostgreSQL di
        # scripts/pg_harness memulai server dengan listen_addresses='' sehingga
        # TCP memang tidak dibuka, dan itu bukan sesuatu yang boleh dipalsukan
        # di sini.
        sock = unix_sock or os.environ.get("CRAFTLIFE_PG_UNIX")
        if sock:
            self.conn = pg.connect(
                unix_sock=sock,
                database=database or os.environ.get("CRAFTLIFE_PG_DB", "craftlife"),
                user=user or os.environ.get("CRAFTLIFE_PG_USER", "craftlife"))
        else:
            self.conn = pg.connect(
                host=host or os.environ.get("CRAFTLIFE_PG_HOST", "localhost"),
                port=int(port or os.environ.get("CRAFTLIFE_PG_PORT", 5432)),
                database=database or os.environ.get("CRAFTLIFE_PG_DB", "craftlife"),
                user=user or os.environ.get("CRAFTLIFE_PG_USER", "craftlife"),
                password=password if password is not None
                else os.environ.get("CRAFTLIFE_PG_PASSWORD", ""),
            )
        self.conn.autocommit = False
        self.ensure_schema()

    # ---------------------------------------------------------------- util
    def ensure_schema(self):
        cur = self.conn.cursor()
        for stmt in [s.strip() for s in DDL.split(";") if s.strip()]:
            cur.execute(stmt)
        self.conn.commit()
        cur.close()

    def _rows(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        out = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        return out

    def _one(self, sql, params=()):
        rows = self._rows(sql, params)
        return rows[0] if rows else None

    def _exec(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(sql, params)
        n = cur.rowcount
        self.conn.commit()
        cur.close()
        return n

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass

    # -- identitas & tautan ------------------------------------------------
    def get_user(self, user_id):
        row = self._one("SELECT * FROM users WHERE id=%s", (user_id,))
        return row if row else {}

    def get_cloud_user_link(self, local_user_id):
        row = self._one("SELECT * FROM cloud_user_links WHERE local_user_id=%s",
                        (local_user_id,))
        return row if row else {}

    def get_or_create_cloud_device(self, local_user_id, app_version="1.0-phase3"):
        row = self._one("SELECT * FROM cloud_device_state WHERE local_user_id=%s",
                        (local_user_id,))
        if row:
            return row
        name = (os.environ.get("COMPUTERNAME") or os.environ.get("HOSTNAME")
                or "CraftLife Desktop")[:120]
        platform_name = (sys.platform or "desktop")[:80]
        device_id = str(uuid.uuid4())
        self._exec(
            "INSERT INTO cloud_device_state(local_user_id, device_id, device_name,"
            " platform, app_version) VALUES(%s,%s,%s,%s,%s)",
            (local_user_id, device_id, name, platform_name, str(app_version)[:40]))
        return {"local_user_id": local_user_id, "device_id": device_id,
                "device_name": name, "platform": platform_name,
                "app_version": str(app_version)[:40]}

    def mark_cloud_device_registered(self, local_user_id, registered_at=None,
                                     last_seen_at=None):
        self._exec(
            "UPDATE cloud_device_state SET registered_at=COALESCE(%s, registered_at, %s),"
            " last_seen_at=COALESCE(%s, %s) WHERE local_user_id=%s",
            (registered_at, _now(), last_seen_at, _now(), local_user_id))

    def rename_local_cloud_device(self, local_user_id, name):
        self._exec("UPDATE cloud_device_state SET device_name=%s WHERE local_user_id=%s",
                   (str(name)[:120], local_user_id))

    # -- sync --------------------------------------------------------------
    def sync_status_summary(self, local_user_id):
        counts = {r["status"]: r["c"] for r in self._rows(
            "SELECT status, COUNT(*) AS c FROM sync_queue WHERE local_user_id=%s"
            " GROUP BY status", (local_user_id,))}
        failed_jobs = [
            {"entity_type": r["entity_type"], "operation": r["operation"],
             "retry_count": r["retry_count"],
             "last_error": (r["last_error"] or "")[:200],
             "next_retry_at": r["next_retry_at"]}
            for r in self._rows(
                "SELECT entity_type, operation, retry_count, last_error, next_retry_at"
                " FROM sync_queue WHERE local_user_id=%s AND status='retry'"
                " ORDER BY next_retry_at LIMIT 10", (local_user_id,))]
        unresolved = self._one(
            "SELECT COUNT(*) AS c FROM sync_conflicts WHERE local_user_id=%s"
            " AND restored_at IS NULL", (local_user_id,))["c"]
        tomb = self._one(
            "SELECT COUNT(*) AS c FROM sync_tombstones WHERE local_user_id=%s"
            " AND pushed_at IS NULL", (local_user_id,))["c"]
        # Versi SQLite memanggil pending_entity_change_count() yang menyapu 34
        # tabel Kanal B. Backend ini punya tabel sync_entities sendiri, jadi
        # dihitung dari situ.
        pending_entities = self._one(
            "SELECT COUNT(*) AS c FROM sync_entities WHERE local_user_id=%s"
            " AND NOT acknowledged", (local_user_id,))["c"]
        state = self._one(
            "SELECT last_pushed_at, last_pulled_at FROM cloud_personal_sync_state"
            " WHERE local_user_id=%s", (local_user_id,)) or {}
        return {
            "pending": int(counts.get("pending") or 0) + int(pending_entities),
            "retry": int(counts.get("retry") or 0),
            "done": int(counts.get("done") or 0),
            "failed": int(counts.get("failed") or 0),
            "queue_failed_samples": failed_jobs,
            "unresolvedConflicts": int(unresolved),
            "pendingTombstones": int(tomb),
            "lastSyncAt": state.get("last_pushed_at") or "",
            "lastPulledAt": state.get("last_pulled_at") or "",
        }

    def list_sync_conflicts(self, local_user_id, limit=50, include_restored=False):
        sql = ("SELECT * FROM sync_conflicts WHERE local_user_id=%s"
               + ("" if include_restored else " AND restored_at IS NULL")
               + " ORDER BY (restored_at IS NOT NULL), detected_at DESC, id DESC"
                 " LIMIT %s")
        return self._rows(sql, (local_user_id, int(limit)))

    def restore_sync_conflict(self, local_user_id, conflict_id):
        row = self._one("SELECT * FROM sync_conflicts WHERE id=%s AND local_user_id=%s",
                        (int(conflict_id), local_user_id))
        if row is None:
            return {"ok": False, "code": "conflict_not_found"}
        if row["restored_at"]:
            return {"ok": False, "code": "already_restored"}
        table_name = row["table_name"]
        if table_name not in _sync_tables():
            return {"ok": False, "code": "unsupported_table"}
        cols = {r["column_name"] for r in self._rows(
            "SELECT column_name FROM information_schema.columns"
            " WHERE table_schema='public' AND table_name=%s", (table_name,))}
        field = row["field"]
        if field not in cols:
            return {"ok": False, "code": "unknown_field"}
        # Dicari lewat uuid DAN user_id, persis seperti versi SQLite: tanpa
        # user_id, restore bisa menulis ke baris milik pengguna lain.
        # Nama kolomnya `user_id` (bukan `local_user_id`) karena itulah yang
        # dipakai tabel-tabel di SYNC_TABLES.
        target = self._one(
            f"SELECT id FROM {table_name} WHERE uuid=%s AND user_id=%s",
            (row["entity_uuid"], local_user_id))
        if target is None:
            return {"ok": False, "code": "entity_not_found"}
        self._exec(
            f"UPDATE {table_name} SET {field}=%s, updated_at=%s WHERE id=%s",
            (row["lost_value"], _now(), target["id"]))
        self._exec("UPDATE sync_conflicts SET restored_at=%s WHERE id=%s",
                   (_now(), int(conflict_id)))
        return {"ok": True, "table": table_name, "field": field,
                "value": row["lost_value"]}

    # -- cache cloud -------------------------------------------------------
    def get_cloud_wallet(self, user_id):
        return self._one("SELECT * FROM cloud_wallet_cache WHERE user_id=%s", (user_id,))

    def save_cloud_wallet(self, user_id, data):
        self._exec(
            "INSERT INTO cloud_wallet_cache(user_id,xp,gold,gems,level,updated_at)"
            " VALUES(%s,%s,%s,%s,%s,%s)"
            " ON CONFLICT(user_id) DO UPDATE SET xp=EXCLUDED.xp, gold=EXCLUDED.gold,"
            " gems=EXCLUDED.gems, level=EXCLUDED.level, updated_at=EXCLUDED.updated_at",
            (user_id, int(data.get("xp", 0) or 0), int(data.get("gold", 0) or 0),
             int(data.get("gems", 0) or 0), int(data.get("level", 1) or 1), _now()))

    def get_cloud_inventory_cache(self, user_id):
        return self._rows(
            "SELECT * FROM cloud_inventory_cache WHERE user_id=%s ORDER BY item_key",
            (user_id,))

    def save_cloud_inventory(self, user_id, rows):
        self._exec("DELETE FROM cloud_inventory_cache WHERE user_id=%s", (user_id,))
        for r in rows or []:
            self._exec(
                "INSERT INTO cloud_inventory_cache(user_id,item_key,qty,equipped,"
                "enchant_level,updated_at) VALUES(%s,%s,%s,%s,%s,%s)",
                (user_id, r.get("item_key"), int(r.get("qty") or 0),
                 1 if r.get("equipped") else 0, int(r.get("enchant_level") or 0),
                 _now()))

    # M09a: padanan Postgres untuk cache pet + cermin hasil spin server.
    # Logika tabel meniru `database.py` persis (nilai absolut dari
    # fetch_cloud_pets, potongan gold sekali per spin segar). Efek domain
    # (check_achievements/recalculate_all_buffs) TIDAK dijalankan backend
    # ini — ia memang tidak memuat logika domain database.py; deployment
    # Postgres penuh belum pernah dijalankan (lihat catatan M05d).
    def save_cloud_pets(self, user_id, payload):
        payload = payload or {}
        self._exec("DELETE FROM cloud_pets_cache WHERE user_id=%s", (user_id,))
        for r in payload.get("pets") or []:
            self._exec(
                "INSERT INTO cloud_pets_cache(user_id,pet_key,level,exp,hunger,"
                "happiness,is_active,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",
                (user_id, r.get("pet_key"), int(r.get("level") or 1),
                 int(r.get("exp") or 0), int(r.get("hunger") or 100),
                 int(r.get("happiness") or 50), 1 if r.get("is_active") else 0,
                 _now()))
        state = payload.get("spin_state") or {}
        self._exec(
            "INSERT INTO cloud_pet_spin_state_cache(user_id,spins_total,"
            "since_epic,since_legendary,updated_at) VALUES(%s,%s,%s,%s,%s) "
            "ON CONFLICT(user_id) DO UPDATE SET spins_total=EXCLUDED.spins_total,"
            "since_epic=EXCLUDED.since_epic, since_legendary=EXCLUDED.since_legendary,"
            "updated_at=EXCLUDED.updated_at",
            (user_id, int(state.get("spins_total") or 0),
             int(state.get("since_epic") or 0), int(state.get("since_legendary") or 0),
             _now()))

    def apply_cloud_spin_result(self, user_id, result, payload=None):
        result = result or {}
        pet_id = result.get("pet_id")
        if not pet_id:
            return {"ok": False, "msg": "invalid_spin_result"}
        payload = payload or {}
        cloud_row = None
        for r in payload.get("pets") or []:
            if r.get("pet_key") == pet_id:
                cloud_row = r
                break
        is_new = bool(result.get("is_new"))
        replay = bool(result.get("replay"))
        owned = self._one(
            "SELECT id FROM user_pets WHERE user_id=%s AND pet_id=%s",
            (user_id, pet_id))
        if owned:
            if cloud_row:
                self._exec(
                    "UPDATE user_pets SET level=%s, exp=%s, hunger=%s, happiness=%s WHERE id=%s",
                    (int(cloud_row.get("level") or 1), int(cloud_row.get("exp") or 0),
                     int(cloud_row.get("hunger") or 100),
                     int(cloud_row.get("happiness") or 50), owned["id"]))
            elif int(result.get("dupe_exp") or 0):
                pet = self._one("SELECT exp, level FROM user_pets WHERE id=%s",
                                (owned["id"],))
                exp = int(pet["exp"] or 0) + int(result["dupe_exp"])
                level = int(pet["level"] or 1)
                while exp >= level * 100:
                    exp -= level * 100
                    level += 1
                self._exec("UPDATE user_pets SET exp=%s, level=%s WHERE id=%s",
                           (exp, level, owned["id"]))
        else:
            self._exec(
                "INSERT INTO user_pets(user_id, pet_id, hunger, happiness, level, exp)"
                " VALUES(%s,%s,%s,%s,%s,%s)",
                (user_id, pet_id, int((cloud_row or {}).get("hunger") or 100),
                 int((cloud_row or {}).get("happiness") or 50),
                 int((cloud_row or {}).get("level") or 1),
                 int((cloud_row or {}).get("exp") or 0)))
        state = payload.get("spin_state") or {}
        if state or result.get("spins_total") is not None:
            self._exec(
                "INSERT INTO pet_spin_state(user_id, spins_total, since_epic, since_legendary)"
                " VALUES(%s,%s,%s,%s) ON CONFLICT(user_id) DO UPDATE SET"
                " spins_total=EXCLUDED.spins_total, since_epic=EXCLUDED.since_epic,"
                " since_legendary=EXCLUDED.since_legendary",
                (user_id, int(state.get("spins_total", result.get("spins_total") or 0)),
                 int(state.get("since_epic", result.get("since_epic") or 0)),
                 int(state.get("since_legendary", result.get("since_legendary") or 0))))
        if not replay:
            self._exec("UPDATE users SET gold=GREATEST(0, COALESCE(gold,0)-%s) WHERE id=%s",
                       (int(result.get("cost") or 120), user_id))
        return {"ok": True, "pet_id": pet_id, "is_new": is_new}

    # M09b: padanan Postgres cache/cermin talent (logika meniru database.py).
    def save_cloud_talents(self, user_id, payload):
        payload = payload or {}
        self._exec("DELETE FROM cloud_talents_cache WHERE user_id=%s", (user_id,))
        for key in payload.get("talents") or []:
            self._exec(
                "INSERT INTO cloud_talents_cache(user_id,talent_key,updated_at)"
                " VALUES(%s,%s,%s) ON CONFLICT(user_id,talent_key) DO NOTHING",
                (user_id, key, _now()))

    def apply_cloud_talents(self, user_id, payload):
        keys = (payload or {}).get("talents") or []
        for key in keys:
            self._exec(
                "INSERT INTO user_talents(user_id, talent_key) VALUES(%s,%s)"
                " ON CONFLICT(user_id,talent_key) DO NOTHING",
                (user_id, key))
        self._exec(
            "UPDATE users SET talent_points_spent="
            "(SELECT COUNT(*) FROM user_talents WHERE user_id=%s) WHERE id=%s",
            (user_id, user_id))
        return {"ok": True, "applied": len(keys)}

    # -- love space --------------------------------------------------------
    def get_cloud_love_space_id(self, local_user_id):
        row = self._one("SELECT cloud_space_id FROM love_spaces WHERE local_user_id=%s",
                        (local_user_id,))
        return (row or {}).get("cloud_space_id")

    def add_love_space_photo(self, requester_user_id, image_data, mime_type,
                             width, height, caption="", photo_date=None,
                             visibility="private"):
        space_id = self.get_cloud_love_space_id(requester_user_id)
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO love_space_photos(local_user_id,space_id,image_data,mime_type,"
            "width,height,caption,photo_date,visibility)"
            " VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (requester_user_id, space_id, image_data, mime_type, int(width or 0),
             int(height or 0), (caption or "")[:200], photo_date, visibility))
        photo_id = cur.fetchone()[0]
        self.conn.commit()
        cur.close()
        return {"ok": True, "photoId": photo_id}

    def mirror_cloud_love_profile(self, local_user_id, row):
        payload = json.dumps(row or {}, ensure_ascii=False, default=str)
        self._exec(
            "INSERT INTO relationship_mirror(local_user_id,record_type,row_id,payload,"
            "updated_at) VALUES(%s,'profile','profile',%s,%s)"
            " ON CONFLICT(local_user_id,record_type,row_id)"
            " DO UPDATE SET payload=EXCLUDED.payload, updated_at=EXCLUDED.updated_at",
            (local_user_id, payload, _now()))

    def mirror_cloud_love_record(self, local_user_id, record_type, row):
        payload = json.dumps(row or {}, ensure_ascii=False, default=str)
        row_id = str((row or {}).get("id") or (row or {}).get("uuid") or "single")
        self._exec(
            "INSERT INTO relationship_mirror(local_user_id,record_type,row_id,payload,"
            "updated_at) VALUES(%s,%s,%s,%s,%s)"
            " ON CONFLICT(local_user_id,record_type,row_id)"
            " DO UPDATE SET payload=EXCLUDED.payload, updated_at=EXCLUDED.updated_at",
            (local_user_id, str(record_type), row_id, payload, _now()))

    # -- maintenance & backup ---------------------------------------------
    def get_maintenance_state(self, user_id):
        row = self._one("SELECT * FROM maintenance_state WHERE user_id=%s", (user_id,))
        if not row:
            # Nilai default disalin dari database.get_maintenance_state supaya
            # kedua backend menjawab sama untuk pengguna yang belum punya baris.
            return {"retention_days": 30, "auto": True, "last_purge_at": "",
                    "schedule": "monthly", "backup_auto": True, "last_backup_at": ""}
        rd = row["retention_days"] if row["retention_days"] is not None else 30
        sched = row["schedule"] or "monthly"
        if sched not in _SCHEDULE_DAYS:
            sched = "monthly"
        return {"retention_days": int(rd), "auto": bool(row["auto"]),
                "last_purge_at": row["last_purge_at"] or "", "schedule": sched,
                "backup_auto": bool(row["backup_auto"])
                if row["backup_auto"] is not None else True,
                "last_backup_at": row["last_backup_at"] or ""}

    def set_maintenance_state(self, user_id, retention_days=None, auto=None,
                              schedule=None, backup_auto=None):
        if schedule is not None:
            schedule = str(schedule).strip().lower()
            if schedule not in _SCHEDULE_DAYS:
                raise ValueError("schedule_invalid")
        if (retention_days is None and auto is None and schedule is None
                and backup_auto is None):
            return
        if not self._one("SELECT user_id FROM maintenance_state WHERE user_id=%s",
                         (user_id,)):
            self._exec(
                "INSERT INTO maintenance_state(user_id,retention_days,auto,schedule,"
                "backup_auto) VALUES(%s,%s,%s,%s,%s)",
                (user_id, int(retention_days) if retention_days is not None else 30,
                 1 if (auto if auto is not None else True) else 0,
                 schedule or "monthly",
                 1 if (backup_auto if backup_auto is not None else True) else 0))
            return
        sets, params = [], []
        if retention_days is not None:
            sets.append("retention_days=%s"); params.append(int(retention_days))
        if auto is not None:
            sets.append("auto=%s"); params.append(1 if auto else 0)
        if schedule is not None:
            sets.append("schedule=%s"); params.append(schedule)
        if backup_auto is not None:
            sets.append("backup_auto=%s"); params.append(1 if backup_auto else 0)
        params.append(user_id)
        self._exec(f"UPDATE maintenance_state SET {','.join(sets)} WHERE user_id=%s",
                   tuple(params))

    def mark_backup_done(self, user_id, when=None):
        self._exec(
            "INSERT INTO maintenance_state(user_id,last_backup_at) VALUES(%s,%s)"
            " ON CONFLICT(user_id) DO UPDATE SET last_backup_at=EXCLUDED.last_backup_at",
            (user_id, when or _now()))

    #: Tabel yang ikut dalam snapshot backend ini. Sengaja eksplisit: daftar
    #: inilah yang menentukan apa yang bisa dipulihkan.
    SNAPSHOT_TABLES = ("cloud_user_links", "cloud_device_state", "cloud_wallet_cache",
                       "cloud_inventory_cache", "maintenance_state", "sync_conflicts",
                       "love_spaces", "love_space_photos", "relationship_mirror")

    def build_backup_snapshot(self, local_user_id):
        tables = {}
        for t in self.SNAPSHOT_TABLES:
            key = "user_id" if t in ("cloud_wallet_cache", "cloud_inventory_cache",
                                     "maintenance_state") else "local_user_id"
            tables[t] = self._rows(f"SELECT * FROM {t} WHERE {key}=%s", (local_user_id,))
        return {"localUserId": local_user_id, "createdAt": _now(), "tables": tables}

    def import_backup_snapshot(self, local_user_id, snapshot):
        tables = (snapshot or {}).get("tables") or {}
        missing = [t for t in self.SNAPSHOT_TABLES if t not in tables]
        if missing:
            raise ValueError("incomplete snapshot: " + ", ".join(sorted(missing)))
        self.local_backup_before_restore()
        for t in self.SNAPSHOT_TABLES:
            key = "user_id" if t in ("cloud_wallet_cache", "cloud_inventory_cache",
                                     "maintenance_state") else "local_user_id"
            self._exec(f"DELETE FROM {t} WHERE {key}=%s", (local_user_id,))
            for row in tables[t]:
                cols = [c for c in row if c != "id"]
                if not cols:
                    continue
                self._exec(
                    f"INSERT INTO {t}({','.join(cols)})"
                    f" VALUES({','.join(['%s'] * len(cols))})",
                    tuple(row[c] for c in cols))
        return {"ok": True, "tables": len(self.SNAPSHOT_TABLES)}

    def local_backup_before_restore(self):
        """Salinan logis sebelum restore — padanan `backup_database()` SQLite.

        Signature-nya tanpa `user_id` (ditetapkan ABC), jadi yang disalin adalah
        **seluruh** baris tabel snapshot, bukan satu pengguna. Itu memang lebih
        luas dari yang dibutuhkan, dan lebih aman: restore tidak pernah
        mengurangi cakupan cadangan.
        """
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dump = {t: self._rows(f"SELECT * FROM {t}") for t in self.SNAPSHOT_TABLES}
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM information_schema.tables"
                    " WHERE table_schema='public' AND table_name='restore_backups'")
        if not cur.fetchone()[0]:
            cur.execute("CREATE TABLE restore_backups(id SERIAL PRIMARY KEY,"
                        " taken_at TEXT, payload TEXT)")
        cur.execute("INSERT INTO restore_backups(taken_at, payload) VALUES(%s,%s)",
                    (_now(), json.dumps({"stamp": stamp, "tables": dump},
                                        ensure_ascii=False, default=str)))
        self.conn.commit()
        cur.close()
        return True

    # -- status layanan cloud (kuota) --------------------------------------
    def get_cloud_service_state(self, local_user_id):
        row = self._one("SELECT * FROM cloud_service_state WHERE local_user_id=%s",
                        (local_user_id,))
        return row if row else {}

    def set_cloud_suspended(self, local_user_id, reason):
        self._exec(
            "INSERT INTO cloud_service_state(local_user_id,suspended_reason,suspended_at)"
            " VALUES(%s,%s,%s)"
            " ON CONFLICT(local_user_id) DO UPDATE SET"
            " suspended_reason=EXCLUDED.suspended_reason,"
            " suspended_at=EXCLUDED.suspended_at",
            (local_user_id, str(reason or "")[:200], _now()))

    def clear_cloud_suspended(self, local_user_id):
        self._exec("DELETE FROM cloud_service_state WHERE local_user_id=%s",
                   (local_user_id,))

    def cloud_suspension_active(self, local_user_id, now=None):
        row = self.get_cloud_service_state(local_user_id)
        reason = str(row.get("suspended_reason") or "")
        if not reason:
            return False, ""
        mark = str(row.get("suspended_at") or "")
        try:
            parsed = datetime.fromisoformat(mark.replace("Z", "+00:00"))
            now_dt = now or (datetime.now(timezone.utc) if parsed.tzinfo
                             else datetime.now())
            elapsed = (now_dt - parsed).total_seconds()
        except Exception:
            # Penanda rusak: jangan kunci pengguna selamanya.
            return False, reason
        return elapsed < 3600, reason

    def mark_cloud_probe(self, local_user_id):
        self._exec(
            "INSERT INTO cloud_service_state(local_user_id,last_probe_at) VALUES(%s,%s)"
            " ON CONFLICT(local_user_id) DO UPDATE SET"
            " last_probe_at=EXCLUDED.last_probe_at",
            (local_user_id, _now()))

    def restore_backup_count(self):
        """Berapa salinan logis yang tersedia — dipakai tes, bukan oleh UI."""
        try:
            row = self._one("SELECT COUNT(*) AS c FROM restore_backups")
        except Exception:
            return 0
        return int((row or {}).get("c") or 0)


def from_env():
    """Bangun adapter dari env, atau None kalau tidak dikonfigurasi.

    Tidak pernah melempar karena driver hilang — mengembalikan None supaya
    pemanggil bisa jatuh kembali ke SQLite. Itulah bentuk "opsional" P1.
    """
    if not os.environ.get("CRAFTLIFE_STORAGE_BACKEND", "").lower().startswith("pg"):
        return None
    try:
        return PostgresCloudStorage()
    except RuntimeError:
        return None
