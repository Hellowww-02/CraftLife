"""M05e (Jalan A) — ukur permukaan deployment yang sebenarnya.

Dengan keputusan Jalan A, Android bicara langsung ke Supabase dan tidak ada
server Python yang perlu di-hosting. Konsekuensinya: pertanyaan "di mana
servernya?" diganti pertanyaan yang lebih penting dan bisa diukur —

    **Data mana yang bisa Android ambil dari Supabase, dan mana yang hanya
    hidup di SQLite lokal?**

Setiap fitur yang datanya hanya ada di SQLite lokal tidak akan ikut pindah ke
HP. Itu bukan keputusan hosting; itu lubang data, dan lebih baik diketahui
sekarang daripada setelah aplikasi Android-nya jadi.

Skrip ini mengukur, tidak menebak. Semua angka diambil dari sumber sebenarnya:
CREATE TABLE di database.py, DDL di supabase/migrations/, dan literal rute di
web/src. Tidak ada daftar yang ditulis tangan.

    python3 scripts/m05e_surface.py
"""
from __future__ import annotations

import pathlib
import re
import sys
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parents[1]


def local_tables() -> set[str]:
    src = (REPO / "database.py").read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_0-9]+)", src))


def cloud_tables() -> set[str]:
    out: set[str] = set()
    for path in sorted((REPO / "supabase" / "migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8", errors="replace")
        out |= set(re.findall(r"create table(?: if not exists)? (?:public\.)?([a-z_0-9]+)",
                              sql, re.I))
    # `shim.sql` adalah harness lokal, bukan bagian dari Supabase sungguhan.
    return {t for t in out if not t.startswith(("pg_", "auth_", "storage_"))}


def cloud_rpcs() -> set[str]:
    out: set[str] = set()
    for path in sorted((REPO / "supabase" / "migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8", errors="replace")
        out |= set(re.findall(r"create or replace function (?:public\.)?([a-z_0-9]+)\s*\(",
                              sql, re.I))
    return out


def cloud_policies() -> int:
    n = 0
    for path in sorted((REPO / "supabase" / "migrations").glob("*.sql")):
        sql = path.read_text(encoding="utf-8", errors="replace")
        n += len(re.findall(r"create policy ", sql, re.I))
    return n


def client_routes() -> list[str]:
    """Literal rute yang dipanggil klien web, dikumpulkan dari web/src."""
    found: set[str] = set()
    for path in (REPO / "web" / "src").rglob("*.ts*"):
        src = path.read_text(encoding="utf-8", errors="replace")
        found |= set(re.findall(r'["\'`](/api/[a-zA-Z0-9/_${}.\-]+)', src))
    return sorted(found)


def domain_of(route: str) -> str:
    parts = [p for p in route.split("/") if p]
    return parts[1] if len(parts) > 1 else "(root)"


def main() -> int:
    lt, ct = local_tables(), cloud_tables()
    rpcs = cloud_rpcs()
    routes = client_routes()

    both = sorted(lt & ct)
    local_only = sorted(lt - ct)
    cloud_only = sorted(ct - lt)

    by_domain: dict[str, int] = defaultdict(int)
    for r in routes:
        by_domain[domain_of(r)] += 1

    print("=" * 74)
    print("M05e — PERMUKAAN DEPLOYMENT (Jalan A: Android -> Supabase langsung)")
    print("=" * 74)
    print(f"  tabel SQLite lokal        : {len(lt)}")
    print(f"  tabel Supabase            : {len(ct)}")
    print(f"  RPC security-definer      : {len(rpcs)}")
    print(f"  policy RLS                : {cloud_policies()}")
    print(f"  literal rute di web/src   : {len(routes)}")
    print()
    print(f"  ADA DI KEDUANYA           : {len(both)}  <- bisa disinkronkan")
    print(f"  HANYA DI SQLite LOKAL     : {len(local_only)}  <- TIDAK ikut ke Android")
    print(f"  HANYA DI Supabase         : {len(cloud_only)}  <- tidak dipakai desktop")
    print()
    print("-" * 74)
    print(f"tabel HANYA LOKAL ({len(local_only)}) — data ini tidak akan ada di HP:")
    for i in range(0, len(local_only), 4):
        print("   " + "  ".join(f"{t:<26}" for t in local_only[i:i + 4]))
    print()
    print("-" * 74)
    print(f"tabel ADA DI KEDUANYA ({len(both)}):")
    for i in range(0, len(both), 4):
        print("   " + "  ".join(f"{t:<26}" for t in both[i:i + 4]))
    print()
    print("-" * 74)
    print(f"rute klien per domain ({len(routes)} literal):")
    for dom, n in sorted(by_domain.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"   {dom:<22} {n:>4}")
    print()
    print("=" * 74)
    if not local_only:
        print("  semua tabel lokal punya padanan cloud")
    else:
        pct = 100 * len(both) / len(lt) if lt else 0
        print(f"  cakupan cloud: {len(both)}/{len(lt)} tabel lokal ({pct:.0f}%)")
        print(f"  {len(local_only)} tabel perlu keputusan: disinkronkan, ditinggal,")
        print("  atau memang khusus desktop.")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())
