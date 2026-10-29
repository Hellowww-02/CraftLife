"""M05e (Jalan A) — bukti bahwa permukaan Supabase cukup untuk klien langsung.

Jalan A berarti Android bicara ke Supabase tanpa server Python di tengah. Itu
hanya sah kalau dua hal benar, dan keduanya bisa DIPERIKSA, bukan diasumsikan:

1. **Cukup.** Setiap operasi yang dibutuhkan klien punya jalan: tabel dengan
   RLS milik-pengguna, atau RPC yang di-grant ke peran `authenticated`.
2. **Aman.** Operasi yang boleh mengubah nilai ekonomi TIDAK boleh bisa
   dipanggil klien. Kalau `spend_gold` bisa dipanggil dari HP, siapa pun bisa
   memberi diri sendiri gold — persis yang dijaga K9.

Skrip ini menjalankan keduanya di PostgreSQL nyata lewat harness, memakai
`has_function_privilege` — jadi hasilnya adalah apa yang akan dilihat Postgres
saat klien sungguhan mengetuk, bukan apa yang tertulis di komentar migrasi.

    python3 scripts/pg_harness/verify_m05e_surface.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run as H  # noqa: E402

# Operasi yang HARUS bisa dipanggil klien langsung supaya Jalan A layak.
MUST_BE_CALLABLE = [
    # sinkronisasi data pribadi
    "upsert_personal_snapshot",
    "get_personal_snapshot_version",
    "upsert_entities",
    "push_tombstones",
    "fetch_tombstones",
    "fetch_entity_revisions",
    # sosial
    "send_direct_message_v2",
    "send_online_guild_message_v2",
    "start_online_guild_boss_v2",
    "send_friend_request",
    "respond_friend_request",
]

# Operasi yang HARUS ditolak untuk klien: nilainya ekonomi atau administratif.
MUST_BE_DENIED = [
    "spend_gold",
    "admin_reverse_ledger",
]

# Tabel yang harus terlindungi RLS — tanpa RLS, klien bisa membaca data siapa pun.
MUST_HAVE_RLS = [
    "personal_snapshots",
    "personal_snapshot_versions",
    "sync_entities",
    "sync_entity_revisions",
    "conversations",
    "messages",
    "online_guilds",
    "online_guild_messages",
    "reward_ledger",
    "profiles",
]


def q(cluster, db, sql):
    r = cluster.psql(["-d", db, "-t", "-A", "-c", sql], capture=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "").strip()[-300:])
    return [ln for ln in (r.stdout or "").splitlines() if ln.strip()]


def main() -> int:
    pg = H.find_pg_bin()
    if not pg:
        print("SKIP: binari PostgreSQL tidak ada")
        return 0
    cluster = H.Cluster(pg)
    cluster.start()
    failures = []
    try:
        db = cluster.db
        applied, bad = H.apply_migrations(cluster)
        # Hanya untuk memeriksa bahwa tes ini bisa GAGAL. Tidak dipakai di
        # jalur normal; dipakai oleh cek non-vakuitas.
        import os as _os
        _inject = _os.environ.get("M05E_INJECT")
        if _inject:
            r = cluster.sql(_inject)
            print(f"[injeksi tes: {_inject[:70]}...] rc={r.returncode}")
        print(f"migrasi: {applied} diterapkan, gagal: {bad or 'tidak ada'}")
        if bad:
            failures.append(f"migrasi gagal: {bad}")
            return report(failures)

        # --- 1. hak EXECUTE -------------------------------------------------
        rows = q(cluster, db, """
            select p.proname,
                   has_function_privilege('authenticated', p.oid, 'EXECUTE')
            from pg_proc p join pg_namespace n on n.oid = p.pronamespace
            where n.nspname = 'public'
            order by p.proname
        """)
        perms = {}
        for line in rows:
            name, allowed = line.split("|")
            perms.setdefault(name, allowed == "t")
            perms[name] = perms[name] or allowed == "t"

        print(f"\nfungsi di skema public: {len(perms)}")
        callable_n = sum(1 for v in perms.values() if v)
        print(f"  bisa dipanggil `authenticated`: {callable_n}")
        print(f"  ditolak untuk `authenticated` : {len(perms) - callable_n}")

        print(f"\nHARUS bisa dipanggil klien ({len(MUST_BE_CALLABLE)}):")
        for fn in MUST_BE_CALLABLE:
            if fn not in perms:
                print(f"  ?  {fn:<38} TIDAK ADA")
                failures.append(f"{fn}: fungsi tidak ada")
            elif perms[fn]:
                print(f"  ✓  {fn:<38} callable")
            else:
                print(f"  ✗  {fn:<38} DITOLAK — klien tidak bisa memakainya")
                failures.append(f"{fn}: ditolak untuk authenticated")

        print(f"\nHARUS ditolak untuk klien ({len(MUST_BE_DENIED)}):")
        for fn in MUST_BE_DENIED:
            if fn not in perms:
                print(f"  ?  {fn:<38} TIDAK ADA")
                continue
            if perms[fn]:
                print(f"  ✗  {fn:<38} BISA DIPANGGIL KLIEN — bahaya K9")
                failures.append(f"{fn}: seharusnya ditolak, tapi callable")
            else:
                print(f"  ✓  {fn:<38} ditolak")

        # --- 2. RLS ---------------------------------------------------------
        print(f"\nRLS harus aktif ({len(MUST_HAVE_RLS)} tabel):")
        rls = {ln.split("|")[0]: ln.split("|")[1] == "t"
               for ln in q(cluster, db, """
                   select c.relname, c.relrowsecurity
                   from pg_class c join pg_namespace n on n.oid = c.relnamespace
                   where n.nspname = 'public' and c.relkind = 'r'
               """)}
        for tbl in MUST_HAVE_RLS:
            if tbl not in rls:
                print(f"  ?  {tbl:<30} TIDAK ADA")
                failures.append(f"{tbl}: tabel tidak ada")
            elif rls[tbl]:
                print(f"  ✓  {tbl:<30} RLS aktif")
            else:
                print(f"  ✗  {tbl:<30} RLS MATI — klien bisa baca data orang lain")
                failures.append(f"{tbl}: RLS tidak aktif")

        # --- 3. setiap tabel publik punya minimal satu policy --------------
        no_policy = q(cluster, db, """
            select c.relname
            from pg_class c join pg_namespace n on n.oid = c.relnamespace
            where n.nspname = 'public' and c.relkind = 'r' and c.relrowsecurity
              and not exists (
                select 1 from pg_policies p
                where p.schemaname = 'public' and p.tablename = c.relname)
            order by c.relname
        """)
        print(f"\ntabel ber-RLS tanpa satu pun policy: {len(no_policy)}")
        for t in no_policy:
            print(f"  !  {t}  (RLS aktif tanpa policy = tidak ada yang bisa akses)")

    finally:
        cluster.stop()
    return report(failures)


def report(failures) -> int:
    print("\n" + "=" * 70)
    if failures:
        for f in failures:
            print("  GAGAL:", f)
        return 1
    print("  permukaan Supabase cukup DAN aman untuk klien langsung (Jalan A)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
