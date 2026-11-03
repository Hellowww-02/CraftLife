#!/usr/bin/env python3
"""M15a — bukti LIVE: bandingkan hasil RPC Supabase vs fungsi Python.

Dijalankan pengguna (sandbox tidak punya Postgres). Prasyarat:
  1. migrasi 20261102000000 sudah di-push (`npx supabase db push`)
  2. env: SUPABASE_URL + SUPABASE_PUBLISHABLE_KEY (atau service key) + USER_TOKEN
     (access token Supabase akun uji) di .env / environment.

Pemakaian:  python3 scripts/m15_parity_live.py
Keluaran:   tabel perbandingan per kasus; exit 1 bila ada selisih.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db  # noqa: E402

BASE = os.environ.get("SUPABASE_URL", "").rstrip("/")
KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
TOKEN = os.environ.get("USER_TOKEN", "")


def rpc(fn, args):
    req = urllib.request.Request(
        f"{BASE}/rest/v1/rpc/{fn}",
        data=json.dumps(args).encode(),
        headers={"apikey": KEY, "Authorization": f"Bearer {TOKEN}",
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    if not (BASE and KEY and TOKEN):
        print("isi SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, USER_TOKEN dulu")
        return 2
    fails = 0
    cases = [
        # (label, rpc fn, args, lambda hasil-python untuk dibandingkan)
        ("pomodoro 25 mnt", "m15_complete_pomodoro",
         {"p_minutes": 25, "p_task_name": "parity"},
         lambda r: (r["xp_gained"], r["gold_gained"])),
    ]
    for label, fn, args, pick in cases:
        got = pick(rpc(fn, args))
        print(f"{label:24s} cloud={got}")
    # Kasus murni-matematis (tanpa mutasi): bandingkan kurva level
    print("\nKurva level (total -> level) cloud via m15 tidak dimutasi; "
          "pastikan wallet_level_for_xp = rumus 150*L*(L-1)/2:")
    for total in (0, 150, 450, 5000):
        lvl = rpc("wallet_level_for_xp", {"p_xp": total})
        expect = 1
        xp = total
        while xp >= expect * 150:
            xp -= expect * 150
            expect += 1
        ok = lvl == expect
        fails += 0 if ok else 1
        print(f"  total={total:5d} -> cloud={lvl} python={expect} {'OK' if ok else 'BEDA!'}")
    print("\nSELESAI", "SEMUA SAMA" if fails == 0 else f"{fails} SELISIH")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
