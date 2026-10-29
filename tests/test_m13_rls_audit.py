"""M13 — audit RLS ulang (statis, atas SEMUA migrasi Supabase).

Aturan yang dijaga:
1. Setiap tabel `public.*` yang dibuat migrasi harus mengaktifkan RLS.
2. Tidak boleh ada policy permisif `using (true)` / `with check (true)`
   untuk role publik — akses lewat RPC service_role saja.
3. Setiap fungsi `security definer` harus mengunci `search_path`.
4. Tidak ada `grant ... to anon` atas tabel.

Audit ini statis karena sandbox tidak punya Postgres; bukti eksekusi
live tetap milik `supabase db lint`/push pengguna (temuan M09b kemarin
membuktikan lint live memang menangkap yang lolos dari audit teks).
"""
from __future__ import annotations

import pathlib
import re
import unittest

MIGRATIONS = pathlib.Path(__file__).resolve().parents[1] / "supabase" / "migrations"


def all_sql() -> str:
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(MIGRATIONS.glob("*.sql"))
    )


class RlsAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = all_sql()
        cls.low = cls.sql.lower()

    def test_every_created_table_enables_rls(self):
        created = set(re.findall(
            r"create table if not exists public\.(\w+)", self.low))
        created |= set(re.findall(r"create table public\.(\w+)", self.low))
        enabled = set(re.findall(
            r"alter table public\.(\w+) enable row level security", self.low))
        missing = created - enabled
        self.assertEqual(missing, set(),
                         f"tabel tanpa RLS: {sorted(missing)}")

    def test_no_permissive_true_policies(self):
        # using(true) HANYA boleh untuk SELECT ke pengguna terautentikasi
        # pada tabel bersama berikut (dengan alasannya):
        # - katalog referensi: achievement_definitions, shop_items_server,
        #   recipes_server, pets_server, talents_server, bosses_server,
        #   app_releases (daftar rilis memang publik utk update checker)
        # - direktori sosial: user_presence (status online), online_guilds
        #   + online_guild_members (guild harus bisa DICARI untuk di-join)
        # Semuanya baca-saja; tidak ada with check(true) yang diizinkan,
        # dan data personal (user_id=auth.uid()) tidak pernah masuk sini.
        shared_read = {
            "achievement_definitions", "shop_items_server", "recipes_server",
            "app_releases", "pets_server", "talents_server", "bosses_server",
            "user_presence", "online_guilds", "online_guild_members",
        }
        offenders = []
        for m in re.finditer(
                r"create policy\s+\w+\s+on\s+public\.(\w+)([^;]*);", self.low):
            table, rest = m.group(1), re.sub(r"\s+", "", m.group(2))
            if "using(true)" not in rest and "withcheck(true)" not in rest:
                continue
            if table in shared_read and "forselect" in rest \
                    and "withcheck(true)" not in rest:
                continue
            offenders.append((table, m.group(2).strip()[:60]))
        self.assertEqual(offenders, [], f"policy permisif liar: {offenders}")

    def test_security_definer_functions_pin_search_path(self):
        # Pasangan per fungsi: blok dari 'create or replace function' sampai
        # '$$' pertama sesudahnya harus memuat security definer + search_path
        # secara bersamaan bila salah satunya ada.
        blocks = re.split(r"create or replace function", self.low)[1:]
        offenders = []
        for block in blocks:
            head = block[: block.find("$$") if "$$" in block else 800]
            if "security definer" in head and "set search_path" not in head:
                name = head.strip().split("(")[0].strip()
                offenders.append(name)
        self.assertEqual(offenders, [], f"definer tanpa search_path: {offenders}")

    def test_no_anon_table_grants(self):
        bad = re.findall(r"grant[^;]*on[^;]*to\s+anon", self.low)
        self.assertEqual(bad, [], f"grant ke anon: {bad}")

    def test_migration_count_expected(self):
        files = sorted(MIGRATIONS.glob("*.sql"))
        self.assertGreaterEqual(len(files), 26)
