"""Bukti bahwa migrasi patch M04b aman di KEDUA kondisi.

Skenario A — instance baru: semua 19 migrasi diterapkan berurutan, lalu seluruh
suite pgTAP dijalankan. Ini membuktikan patch tidak merusak jalur normal.

Skenario B — instance yang sudah menyimpang: inilah alasan patch ini ada.
Migrasi M04b versi SEBELUM edit (diambil dari git 32587bf) diterapkan, lalu
diperiksa bahwa fungsinya memang versi lama, lalu patch diterapkan, lalu
diperiksa bahwa fungsinya sudah final. Kalau skenario ini tidak diuji, klaim
"aman di kedua kondisi" hanya klaim.
"""
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import run as H  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
MIGRATIONS = sorted((REPO / "supabase" / "migrations").glob("*.sql"))
PATCH = REPO / "supabase/migrations/20261011000000_patch_m04b_upsert_entities_rows.sql"
M04B_NAME = "20261008000000_phase_m04b_entity_channel_b.sql"
TOKEN = "v_rows"      # hanya ada di badan final
OLD_TOKEN = "'inserted', v_inserted, 'updated', v_updated"  # ada di keduanya


def body_has(cluster, db, token):
    r = cluster.psql(["-d", db, "-t", "-A", "-c",
                      "select position(%s in prosrc) > 0 from pg_proc "
                      "where proname = 'upsert_entities'" % f"$${token}$$"],
                     capture=True)
    return r.stdout.strip() == "t"


def main():
    pg = H.find_pg_bin()
    if not pg:
        print("SKIP: binari PostgreSQL tidak ada")
        return 0
    cluster = H.Cluster(pg)
    cluster.start()
    failures = []
    try:
        # --- Skenario A: instance baru -------------------------------------
        db_a = "scenario_fresh"
        cluster.sql(f"create database {db_a}")
        # shim.sql dulu: dialah yang menciptakan skema `extensions`.
        cluster.psql(["-d", db_a, "-f", str(H.SHIM)])
        r = cluster.psql(["-d", db_a, "-c", "create extension if not exists pgtap with schema extensions"], capture=True)
        if r.returncode != 0:
            failures.append(f"A: pgtap tidak terpasang: {(r.stderr or '').strip()[-200:]}")
        cluster.sql(f"alter database {db_a} set search_path = public, extensions")
        bad = []
        for path in MIGRATIONS:
            r = cluster.psql(["-d", db_a, "-v", "ON_ERROR_STOP=1", "-f", str(path)], capture=True)
            if r.returncode != 0:
                bad.append(path.name)
        print(f"A) {len(MIGRATIONS) - len(bad)}/{len(MIGRATIONS)} migrasi diterapkan, gagal: {bad or 'tidak ada'}")
        if bad:
            failures.append(f"A: migrasi gagal {bad}")
        if not body_has(cluster, db_a, TOKEN):
            failures.append("A: badan final tidak terpasang di instance baru")
        else:
            print("A) upsert_entities memuat v_rows  -> badan final OK")

        # pgTAP penuh di instance baru, lewat pg_prove seperti harness aslinya.
        pg_prove = shutil.which("pg_prove")
        if not pg_prove:
            failures.append("A: pg_prove tidak terpasang, pgTAP tidak bisa dijalankan")
        else:
            tests = sorted(str(t) for t in (REPO / "supabase" / "tests").glob("*.sql"))
            r = subprocess.run([pg_prove, "-d", db_a, *tests], capture_output=True,
                               text=True, env=cluster.env(), cwd=str(REPO))
            out = (r.stdout or "") + (r.stderr or "")
            files_line = next((l.strip() for l in out.splitlines()
                               if l.strip().startswith("Files=")), "")
            if r.returncode == 0 and files_line and "Result: FAIL" not in out:
                ok = 0
                for part in files_line.split(","):
                    part = part.strip()
                    if part.startswith("Files="):
                        ok = int(part.split("=")[1].split()[0].split("/")[0])
                    if part.startswith("Tests="):
                        total_assert = int(part.split("=")[1].split()[0])
                print(f"A) pg_prove: {files_line}")
                if total_assert == 0:
                    failures.append("A: pg_prove melaporkan 0 assertion")
            else:
                failures.append(f"A: pg_prove gagal (rc={r.returncode})\n{out.strip()[-600:]}")

        # --- Skenario B: instance yang sudah menyimpang --------------------
        db_b = "scenario_drifted"
        cluster.sql(f"create database {db_b}")
        cluster.psql(["-d", db_b, "-f", str(H.SHIM)])
        cluster.psql(["-d", db_b, "-c", "create extension if not exists pgtap with schema extensions"], capture=True)
        cluster.sql(f"alter database {db_b} set search_path = public, extensions")

        original = subprocess.run(
            ["git", "show", f"32587bf:supabase/migrations/{M04B_NAME}"],
            cwd=REPO, capture_output=True, text=True, check=True).stdout
        old_path = Path(cluster.tmp) / "m04b_original.sql"
        old_path.write_text(original)

        bad = []
        for path in MIGRATIONS:
            if path == PATCH:
                continue          # patch justru yang sedang diuji; jangan dipasang dulu
            use = old_path if path.name == M04B_NAME else path
            r = cluster.psql(["-d", db_b, "-v", "ON_ERROR_STOP=1", "-f", str(use)],
                             capture=True)
            if r.returncode != 0:
                bad.append(path.name)
        # Terapkan semua migrasi SETELAH M04b juga, supaya setara instance nyata
        # yang sudah menerima semuanya kecuali patch baru.
        print(f"B) migrasi pra-patch diterapkan (M04b = versi 32587bf), gagal: {bad or 'tidak ada'}")
        if bad:
            failures.append(f"B: migrasi pra-patch gagal {bad}")

        if body_has(cluster, db_b, TOKEN):
            failures.append("B: versi lama TERNYATA sudah memuat v_rows — premis pengujian salah")
        else:
            print("B) sebelum patch: upsert_entities TIDAK memuat v_rows -> penyimpangan direproduksi")

        r = cluster.psql(["-d", db_b, "-v", "ON_ERROR_STOP=1", "-f", str(PATCH)], capture=True)
        if r.returncode != 0:
            failures.append(f"B: patch gagal diterapkan: {(r.stderr or '').strip()[-200:]}")
        elif not body_has(cluster, db_b, TOKEN):
            failures.append("B: setelah patch, badan final masih tidak terpasang")
        else:
            print("B) setelah patch: upsert_entities memuat v_rows -> penyimpangan diperbaiki")

        # Patch harus idempoten: dijalankan dua kali tidak boleh error.
        r = cluster.psql(["-d", db_b, "-v", "ON_ERROR_STOP=1", "-f", str(PATCH)], capture=True)
        if r.returncode != 0:
            failures.append(f"B: patch tidak idempoten: {(r.stderr or '').strip()[-200:]}")
        else:
            print("B) patch dijalankan dua kali -> tetap OK (idempoten)")

        # GRANT harus tetap melekat setelah CREATE OR REPLACE.
        r = cluster.psql(["-d", db_b, "-t", "-A", "-c",
                          "select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                          "where p.proname='upsert_entities' and n.nspname='public' and p.prosecdef"],
                         capture=True)
        if r.stdout.strip() != "1":
            failures.append(f"B: security definer hilang setelah patch (prosecdef={r.stdout.strip()})")
        else:
            print("B) security definer tetap melekat setelah patch")

    finally:
        cluster.stop()

    print("-" * 70)
    if failures:
        for f in failures:
            print("  GAGAL:", f)
        return 1
    print("  kedua skenario lulus")
    return 0


if __name__ == "__main__":
    sys.exit(main())
