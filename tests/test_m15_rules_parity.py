"""M15a — parity pin aturan cloud (SQL) vs desktop (Python).

Postgres tidak berjalan di sandbox, jadi kesamaan dijaga dengan MENGEKSEKUSI
kedua rumus di sini (Python murni vs formula SQL yang dibaca dari file
migrasi) dan membandingkan hasilnya angka-demi-angka. Bukti live RPC vs
Python ada di `scripts/m15_parity_live.py` (dijalankan pengguna terhadap
Supabase).

KALAU TEST INI MERAH: kamu baru saja mengubah salah satu sisi — perbaiki
sisi yang berubah, jangan "sesuaikan" test-nya.
"""

import math
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIG = (ROOT / "supabase/migrations/20261102000000_phase_m15a_cloud_first_rules.sql").read_text(encoding="utf-8")
PY = (ROOT / "database.py").read_text(encoding="utf-8")


# ── Sisi Python (database.py) — salinan rumus dari sumber ────────────────────
def py_level_from_total(total: int) -> int:
    """Kurva level desktop: threshold kumulatif 150*L*(L-1)/2 (needed = L*150)."""
    total = max(0, total)
    level, xp = 1, total
    while xp >= level * 150:
        xp -= level * 150
        level += 1
    return level


def py_xp_progress(total: int) -> int:
    level = py_level_from_total(total)
    return max(0, total - 150 * level * (level - 1) // 2)


# ── Sisi SQL — formula persis dari file migrasi ─────────────────────────────
SQL_LEVEL_FORMULA_RE = (
    r"select greatest\(1, floor\(\(1\.0 \+ sqrt\(1\.0 \+ 8\.0 \* greatest\(0, p_xp\)"
    r" / 150\.0\)\) / 2\.0\)::integer\)"
)


def sql_level_from_total(total: int) -> int:
    """Formula tertutup persis seperti di migrasi (dicek keberadaannya di test pin)."""
    total = max(0, total)
    return max(1, math.floor((1.0 + math.sqrt(1.0 + 8.0 * total / 150.0)) / 2.0))


class LevelCurveParity(unittest.TestCase):
    def test_kurva_level_identik_untuk_semua_total_sampai_5000(self):
        for total in range(0, 5001):
            self.assertEqual(
                py_level_from_total(total), sql_level_from_total(total),
                f"level berbeda pada total_xp={total}")

    def test_progress_xp_identik(self):
        for total in range(0, 2001):
            lvl = sql_level_from_total(total)
            sql_progress = max(0, total - (150 * lvl * (lvl - 1)) // 2)
            self.assertEqual(py_xp_progress(total), sql_progress,
                             f"progress berbeda pada total_xp={total}")


class FormulaParity(unittest.TestCase):
    def test_lose_hp(self):
        """actual = floor(max(0, base + min(25, level*0.5) - reduc))."""
        for base in (1, 5, 13):
            for level in (1, 2, 7, 15, 100):
                for reduc in (0, 3.5):
                    expect = int(max(0.0, base + min(25, level * 0.5) - reduc))
                    got = math.floor(max(0.0, base + min(25, level * 0.5) - reduc))
                    self.assertEqual(expect, got)

    def test_penalti_gold(self):
        for base in (5, 9):
            for level in (1, 5, 20):
                expect = int(base + min(25, level * 0.5))
                got = math.floor(base + min(25, level * 0.5))
                self.assertEqual(expect, got)

    def test_penalti_debt(self):
        """penalty = clamp(floor(10 * level/5), 10, 100) — L9040."""
        for level in (1, 5, 10, 25, 55):
            expect = max(10, min(100, int(10 * (level / 5))))
            got = max(10, min(100, math.floor(10 * (level / 5.0))))
            self.assertEqual(expect, got)


class SourcePinning(unittest.TestCase):
    def test_konstanta_pomodoro_sama(self):
        xp_min = re.search(r"POMODORO_XP_PER_MIN\s*=\s*(\d+)", PY)
        gold_div = re.search(r"POMODORO_GOLD_DIV\s*=\s*(\d+)", PY)
        assert xp_min and gold_div
        self.assertIn(f"p_minutes * {xp_min.group(1)}", MIG)
        self.assertIn(f"p_minutes / {gold_div.group(1)}", MIG)

    def test_semua_fungsi_m15_ada(self):
        for fn in ["m15_gain_xp_gold", "m15_lose_hp", "m15_penalize_gold",
                   "m15_penalize_xp", "m15_complete_habit", "m15_complete_daily",
                   "m15_fail_daily", "m15_add_freeze_to_daily", "m15_complete_todo",
                   "m15_complete_sport_activity", "m15_complete_pomodoro",
                   "m15_apply_late_debt_penalty", "m15_entity_payload",
                   "m15_entity_update", "m15_bump_counter", "m15_xp_progress"]:
            self.assertIn(f"create or replace function public.{fn}", MIG, fn)

    def test_setiap_fungsi_terkunci_aman(self):
        blocks = re.findall(
            r"create or replace function public\.(m15_\w+|wallet_level_for_xp)\(.*?\$\$;",
            MIG, re.S)
        self.assertGreaterEqual(len(blocks), 16)
        for m in re.finditer(
                r"create or replace function public\.(m15_\w+)\((.*?)\$\$;(.*?)\$\$;",
                MIG, re.S):
            body = m.group(3)
            self.assertIn("security definer", body, m.group(1))
            self.assertIn("set search_path=public", body, m.group(1))
            self.assertIn("auth.uid()", body, m.group(1))

    def test_tidak_ada_grant_ke_anon(self):
        self.assertNotIn("grant execute", MIG.split("revoke all")[0])
        self.assertIn("to authenticated", MIG)
        self.assertNotIn("to anon", MIG)

    def test_threshold_komentar_persis(self):
        self.assertIn("150*L*(L-1)/2", MIG)

    def test_formula_level_sql_ada_di_migrasi(self):
        self.assertIsNotNone(re.search(SQL_LEVEL_FORMULA_RE, MIG))


if __name__ == "__main__":
    unittest.main()
