"""M07 — SQL Android diuji di SQLite sungguhan.

Masalahnya: expo-sqlite adalah modul native. Tanpa emulator, satu-satunya cara
"menguji" store Android adalah membaca kodenya — dan itu bukan pengujian.

Jalan keluarnya: SQLite adalah SQLite. `sqlite3` di stdlib Python memakai mesin
yang sama, dan placeholder `?`-nya identik dengan expo-sqlite. Jadi tes ini
mengekstrak DDL dan kueri *dari file TypeScript yang dikirim ke perangkat*,
lalu menjalankannya apa adanya di basis data nyata.

Yang diuji adalah SQL yang benar-benar shipped, bukan salinannya. Kalau seseorang
mengubah kueri di `sqliteStore.ts`, ekstraksi di sini ikut berubah — dan kalau
kueri itu rusak, tes ini gagal.
"""

from __future__ import annotations

import os
import re
import sqlite3
import unittest

ANDROID = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "CraftLife-Android",
)
SCHEMA_TS = os.path.join(ANDROID, "src", "db", "schema.ts")
STORE_TS = os.path.join(ANDROID, "src", "sync", "sqliteStore.ts")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def extract_schema_sql() -> str:
    """Ambil isi template literal SCHEMA_SQL dari schema.ts."""
    src = _read(SCHEMA_TS)
    m = re.search(r"export const SCHEMA_SQL = `(.*?)`;", src, re.S)
    if not m:
        raise AssertionError("SCHEMA_SQL tidak ditemukan di schema.ts")
    return m.group(1)


def extract_schema_tables() -> list:
    src = _read(SCHEMA_TS)
    m = re.search(r"export const SCHEMA_TABLES = \[(.*?)\] as const;", src, re.S)
    if not m:
        raise AssertionError("SCHEMA_TABLES tidak ditemukan di schema.ts")
    return re.findall(r'"([a-z_]+)"', m.group(1))


def extract_query(store_src: str, marker: str) -> str:
    """Ambil template literal SQL pertama yang muncul setelah `marker`."""
    idx = store_src.index(marker)
    m = re.search(r"`(.*?)`", store_src[idx:], re.S)
    if not m:
        raise AssertionError(f"kueri untuk {marker!r} tidak ditemukan")
    return m.group(1)


def extract_column_list(store_src: str) -> str:
    m = re.search(r"const ROW_COLUMNS = \[(.*?)\]\.join", store_src, re.S)
    if not m:
        raise AssertionError("ROW_COLUMNS tidak ditemukan di sqliteStore.ts")
    return ", ".join(re.findall(r'"([a-z_]+)"', m.group(1)))


STORE_SRC = _read(STORE_TS) if os.path.exists(STORE_TS) else ""


@unittest.skipUnless(os.path.isdir(ANDROID), "CraftLife-Android/ tidak ada")
class AndroidSqlTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.schema = extract_schema_sql()
        self.db.executescript(self.schema)

    def tearDown(self):
        self.db.close()

    # ---------------------------------------------------------------- #
    # Ekstraksinya sendiri harus terbukti, bukan diam-diam kosong
    # ---------------------------------------------------------------- #
    def test_extraction_is_not_vacuous(self):
        self.assertGreater(len(self.schema), 200, "SCHEMA_SQL terlalu pendek")
        self.assertEqual(len(extract_schema_tables()), 4)
        self.assertGreater(len(STORE_SRC), 1000, "sqliteStore.ts tidak terbaca")

    def test_schema_creates_every_declared_table(self):
        declared = set(extract_schema_tables())
        actual = {
            r[0]
            for r in self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        self.assertTrue(declared <= actual, f"tabel hilang: {declared - actual}")

    def test_outbox_columns_match_desktop_sync_queue(self):
        """Kolom outbox Android harus sama dengan sync_queue desktop.

        Kalau berbeda, dua klien menyimpan pekerjaan sync dalam bentuk berbeda
        dan reconciling-nya jadi tebak-tebakan.
        """
        android = {
            r["name"]
            for r in self.db.execute("PRAGMA table_info(sync_outbox)").fetchall()
        }
        # sync_queue desktop punya local_user_id + FK ke users; outbox Android
        # tidak punya tabel users lokal, jadi FK-nya memang tidak ada. Sisanya
        # harus identik.
        expected = {
            "id", "local_user_id", "entity_type", "entity_local_id", "operation",
            "payload", "status", "retry_count", "next_retry_at", "last_error",
            "created_at", "updated_at",
        }
        self.assertEqual(android, expected)

    # ---------------------------------------------------------------- #
    # Kueri yang shipped, dijalankan apa adanya
    # ---------------------------------------------------------------- #
    def test_due_query_respects_next_retry_at(self):
        q = extract_query(STORE_SRC, "async due(").replace("${ROW_COLUMNS}", extract_column_list(STORE_SRC))
        self.db.execute(
            "INSERT INTO sync_outbox (local_user_id, entity_type, operation, status, next_retry_at) "
            "VALUES (1,'habits','upsert','pending',NULL)"
        )
        self.db.execute(
            "INSERT INTO sync_outbox (local_user_id, entity_type, operation, status, next_retry_at) "
            "VALUES (1,'habits','upsert','retry','2026-10-13 09:00:00')"
        )
        self.db.commit()

        now = self.db.execute(q, ["2026-10-13 04:00:00", 25]).fetchall()
        self.assertEqual(len(now), 1, "baris yang belum jatuh tempo ikut terkirim")

        later = self.db.execute(q, ["2026-10-13 10:00:00", 25]).fetchall()
        self.assertEqual(len(later), 2)

    def test_due_query_excludes_done_and_dead(self):
        q = extract_query(STORE_SRC, "async due(").replace("${ROW_COLUMNS}", extract_column_list(STORE_SRC))
        for status in ("pending", "retry", "done", "dead"):
            self.db.execute(
                "INSERT INTO sync_outbox (local_user_id, entity_type, operation, status) "
                "VALUES (1,'habits','upsert',?)",
                (status,),
            )
        self.db.commit()
        rows = self.db.execute(q, ["2026-10-13 04:00:00", 25]).fetchall()
        self.assertEqual(sorted(r["status"] for r in rows), ["pending", "retry"])

    def test_find_pending_handles_null_entity_local_id(self):
        """`= NULL` tidak pernah benar di SQL. Kalau kueri memakai `=`, entitas
        tanpa id lokal tidak akan pernah ter-dedup dan outbox membengkak."""
        q = extract_query(STORE_SRC, "entityLocalId === null").replace(
            "${ROW_COLUMNS}", extract_column_list(STORE_SRC)
        )
        self.db.execute(
            "INSERT INTO sync_outbox (local_user_id, entity_type, entity_local_id, operation, status) "
            "VALUES (1,'settings',NULL,'upsert','pending')"
        )
        self.db.commit()
        found = self.db.execute(q, [1, "settings"]).fetchall()
        self.assertEqual(len(found), 1, "baris ber-entity_local_id NULL tidak ketemu")

    def test_find_pending_query_with_id(self):
        q = extract_query(STORE_SRC, ": await this.db.getFirstAsync").replace(
            "${ROW_COLUMNS}", extract_column_list(STORE_SRC)
        )
        self.db.execute(
            "INSERT INTO sync_outbox (local_user_id, entity_type, entity_local_id, operation, status) "
            "VALUES (1,'habits','42','upsert','pending')"
        )
        self.db.commit()
        self.assertEqual(len(self.db.execute(q, [1, "habits", "42"]).fetchall()), 1)
        self.assertEqual(len(self.db.execute(q, [1, "habits", "99"]).fetchall()), 0)

    def test_update_statement_is_valid_sql(self):
        """UPDATE dibangun dinamis dari whitelist. Uji bentuk nyatanya."""
        self.db.execute(
            "INSERT INTO sync_outbox (local_user_id, entity_type, operation, status) "
            "VALUES (1,'habits','upsert','pending')"
        )
        self.db.commit()
        cols = extract_column_list(STORE_SRC)
        allowed = [c for c in cols.split(", ") if c != "id"]
        patch = {"status": "dead", "retry_count": 3, "last_error": "402 quota"}
        self.assertTrue(set(patch) <= set(allowed), "kolom patch di luar whitelist")
        set_clause = ", ".join(f"{k} = ?" for k in patch)
        self.db.execute(
            f"UPDATE sync_outbox SET {set_clause} WHERE id = ?",
            [*patch.values(), 1],
        )
        self.db.commit()
        row = self.db.execute("SELECT status, retry_count, last_error FROM sync_outbox WHERE id=1").fetchone()
        self.assertEqual(row["status"], "dead")
        self.assertEqual(row["retry_count"], 3)

    def test_watermark_and_cache_primary_keys_enforce_one_row(self):
        """Cache dan watermark memakai PK majemuk; upsert harus menimpa."""
        for table, cols in (
            ("entity_cache", "local_user_id, entity_type, entity_local_id, payload"),
            ("sync_watermark", "local_user_id, entity_type, last_server_updated_at"),
        ):
            placeholders = ", ".join("?" for _ in cols.split(", "))
            value_col = cols.split(", ")[-1]
            for value in ("A", "B"):
                self.db.execute(
                    f"INSERT INTO {table} ({cols}) VALUES ({placeholders}) "
                    f"ON CONFLICT DO UPDATE SET {value_col} = excluded.{value_col}",
                    (1, "habits", *([] if table == "sync_watermark" else ["42"]), value)
                    if table == "entity_cache"
                    else (1, "habits", value),
                )
            self.db.commit()
            n = self.db.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
            self.assertEqual(n, 1, f"{table} menyimpan duplikat")
            got = self.db.execute(f"SELECT {value_col} AS v FROM {table}").fetchone()["v"]
            self.assertEqual(got, "B", f"{table} tidak tertimpa oleh nilai terbaru")


if __name__ == "__main__":
    unittest.main()
