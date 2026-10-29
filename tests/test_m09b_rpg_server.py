"""M09b — Talents, achievements, boss rewards server-authoritative + P10.

Bukti yang dikumpulkan di sini:

1. Kontrak migrasi: katalog server (talents/bosses) sama dengan data
   desktop, RPC memvalidasi dengan aturan yang sama seperti jalur lokal,
   klaim achievement mensyaratkan catatan unlock server, dan constraint
   sumber ledger diperluas — termasuk source 'pet_spin' dari M09a yang
   sebelumnya belum masuk daftar (tertangkap saat audit M09b; test
   penjaga di bawah memindai SEMUA migrasi agar tidak terulang).

2. Perilaku desktop: unlock talent dan klaim reward boss mengantre
   perintah Kanal C dengan payload yang benar (client tidak mengirim
   jumlah reward), cermin talent cloud idempoten, dan UI tidak lagi
   punya jalur adopsi pet berbayar (P10).
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.harness import TempDatabase

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIG = os.path.join(ROOT, "supabase", "migrations",
                   "20261022010000_phase_m09b_talents_achievements_boss_server.sql")


def _sql(path=MIG) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class M09bMigrationContractTest(unittest.TestCase):
    def test_ledger_sources_extended_for_m09a_and_boss(self):
        sql = _sql()
        self.assertIn("'pet_spin','boss_local'", sql)
        # Seluruh sumber lama harus tetap diizinkan (tidak ada yang dicabut).
        for src in ("productivity", "pvp", "guild_boss", "achievement", "quest",
                    "shop_refund", "shop_purchase", "craft_spend", "admin_adjustment"):
            self.assertIn(f"'{src}'", sql)

    def test_all_ledger_sources_used_anywhere_are_allowed(self):
        """Penjaga: sumber ledger yang dipakai migrasi mana pun harus ada di
        daftar final. Inilah yang luput di M09a ('pet_spin')."""
        mig_dir = os.path.join(ROOT, "supabase", "migrations")
        files = sorted(f for f in os.listdir(mig_dir) if f.endswith(".sql"))
        allowed: set[str] = set()
        used: set[str] = set()
        for name in files:
            text = _sql(os.path.join(mig_dir, name))
            for m in re.finditer(
                    r"add constraint reward_ledger_source_check\s*check \(source in \(([^)]*)\)\)",
                    text, re.S):
                allowed = set(re.findall(r"'([a-z_]+)'", m.group(1)))
            # spend_gold(p_user, amount, 'source', ...) — argumen ketiga.
            for m in re.finditer(r"spend_gold\([^)]*?'([a-z_]+)'", text, re.S):
                used.add(m.group(1))
            # Insert ledger langsung: values (auth.uid(), 'source', ...).
            for m in re.finditer(
                    r"insert into public\.reward_ledger\(user_id, source,[^)]*\)\s*values \([^,]+, '([a-z_]+)'",
                    text, re.S):
                used.add(m.group(1))
        self.assertTrue(allowed, "constraint ledger tidak ditemukan")
        self.assertTrue(used, "tidak ada sumber ledger yang terdeteksi")
        self.assertEqual(used - allowed, set(),
                         f"sumber dipakai tapi tidak diizinkan: {used - allowed}")

    def test_talent_and_boss_seeds_match_desktop(self):
        import database as db_mod
        sql = _sql()
        tin = [ln for ln in sql.splitlines()
               if ln.startswith("insert into public.talents_server")]
        self.assertEqual(len(tin), len(db_mod.TALENTS))
        for key, meta in db_mod.TALENTS.items():
            line = next((ln for ln in tin if f"('{key}'" in ln), None)
            self.assertIsNotNone(line, key)
            self.assertIn(f"'{meta['class']}',{int(meta['tier'])}", line)
        bin_ = [ln for ln in sql.splitlines()
                if ln.startswith("insert into public.bosses_server")]
        self.assertEqual(len(bin_), len(db_mod.BOSSES))
        for key, meta in db_mod.BOSSES.items():
            line = next((ln for ln in bin_ if f"('{key}'" in ln), None)
            self.assertIsNotNone(line, key)
            self.assertIn(f"{int(meta.get('xp') or 0)},{int(meta.get('gold') or 0)})", line)

    def test_unlock_talent_rules_mirror_local(self):
        sql = _sql()
        for needle in ("unknown_talent", "talent_class_mismatch", "talent_no_points",
                       "talent_level_required", "talent_prereq_required",
                       "v_level // 5", "def.tier * 5", "avatar_class"):
            self.assertIn(needle, sql)

    def test_claim_requires_server_unlock_record(self):
        sql = _sql()
        self.assertIn("achievement_not_unlocked", sql)
        self.assertIn("set claimed_at = now()", sql)
        self.assertIn("create or replace function public.claim_achievement_reward_cloud", sql)

    def test_boss_claim_uses_catalog_and_idempotency(self):
        sql = _sql()
        self.assertIn("def.xp // v_cnt", sql)
        self.assertIn("least(coalesce(p_member_count, 1), 100)", sql)
        self.assertIn("unique (user_id, idempotency_key)", sql)
        self.assertIn("'boss_local'", sql)

    def test_security_shape(self):
        sql = _sql()
        for table in ("talents_server", "bosses_server", "cloud_user_talents",
                      "cloud_user_achievements", "cloud_boss_reward_claims"):
            self.assertIn(f"alter table public.{table} enable row level security", sql)
            self.assertIn(f"revoke insert, update, delete on public.{table} from authenticated, anon, public", sql)
        self.assertIn("grant execute on function public.unlock_talent_cloud(text) to authenticated", sql)
        self.assertIn("grant execute on function public.claim_boss_reward_cloud(text, integer, text) to authenticated", sql)


class _DbBase(unittest.TestCase):
    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.db = self.ctx.db
        self.db.init_db()
        res = self.db.register_user("m09buser", "password123")
        self.assertTrue(res.get("ok"), res)
        conn = self.db.get_conn()
        self.uid = conn.execute(
            "SELECT id FROM users WHERE username='m09buser'").fetchone()["id"]
        conn.execute("UPDATE users SET level=10, gold=5000 WHERE id=?", (self.uid,))
        # Tautan cloud palsu: cukup agar _queue_cloud_econ mau mengantre.
        conn.execute(
            "INSERT INTO cloud_user_links(local_user_id, cloud_user_id, email) VALUES(?,?,?)",
            (self.uid, "00000000-0000-0000-0000-0000000000aa", "m09b@example.com"))
        conn.commit(); conn.close()

    def tearDown(self):
        self._ctx.__exit__(None, None, None)

    def _jobs(self, entity):
        return [j for j in self.db.get_pending_sync_jobs(self.uid, 100)
                if j["entity_type"] == entity]


class M09bQueueTest(_DbBase):
    def test_init_db_idempotent_and_member_count_column(self):
        self.db.init_db()  # kedua kali: tidak boleh error
        conn = self.db.get_conn()
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(boss_rewards)")]
        tables = {r["name"] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertIn("member_count", cols)
        self.assertIn("cloud_talents_cache", tables)

    def test_unlock_talent_queues_cloud_command(self):
        key = next(k for k, v in self.db.TALENTS.items()
                   if v["class"] == "warrior" and v["tier"] == 1)
        out = self.db.unlock_talent(self.uid, key)
        self.assertTrue(out["ok"], out)
        jobs = self._jobs("talent_unlock")
        self.assertEqual(len(jobs), 1)
        payload = json.loads(jobs[0]["payload"])
        self.assertEqual(payload["talent_key"], key)
        self.assertIn("idempotency_key", payload)

    def test_claim_boss_reward_queues_catalog_command(self):
        conn = self.db.get_conn()
        gid = conn.execute(
            "INSERT INTO guilds(name, leader_id) VALUES('M09B Guild', ?)",
            (self.uid,)).lastrowid
        rid = conn.execute(
            "INSERT INTO boss_rewards(user_id, guild_id, boss_name, boss_tier,"
            " xp_reward, gold_reward, member_count) VALUES(?,?, 'Zombie', 'beginner', 20, 5, 4)",
            (self.uid, gid)).lastrowid
        conn.commit(); conn.close()
        out = self.db.claim_boss_reward(rid, self.uid)
        self.assertTrue(out["ok"], out)
        jobs = self._jobs("boss_reward")
        self.assertEqual(len(jobs), 1)
        payload = json.loads(jobs[0]["payload"])
        # Client mengirim kunci + jumlah member, BUKAN jumlah reward.
        self.assertEqual(payload["boss_key"], "zombie")
        self.assertEqual(payload["member_count"], 4)
        self.assertNotIn("xp_reward", payload)
        self.assertNotIn("gold_reward", payload)


class M09bTalentMirrorTest(_DbBase):
    def test_apply_cloud_talents_idempotent_and_spent_recomputed(self):
        payload = {"talents": ["warrior_t1_skin", "warrior_t1_power"]}
        self.db.apply_cloud_talents(self.uid, payload)
        self.db.apply_cloud_talents(self.uid, payload)
        state = self.db.get_talent_state(self.uid)
        self.assertEqual(state["unlocked"],
                         {"warrior_t1_skin", "warrior_t1_power"})
        conn = self.db.get_conn()
        spent = conn.execute(
            "SELECT talent_points_spent FROM users WHERE id=?",
            (self.uid,)).fetchone()["talent_points_spent"]
        conn.close()
        self.assertEqual(spent, 2)

    def test_talents_cache_roundtrip(self):
        self.db.save_cloud_talents(self.uid, {"talents": ["mage_t1_focus"]})
        self.assertEqual(self.db.get_cloud_talents_cache(self.uid),
                         ["mage_t1_focus"])


class _FakeCloud:
    authenticated = True

    def __init__(self):
        self.calls = []

    def record_achievement_unlock_cloud(self, key):
        self.calls.append(("record", key))
        return {"ok": True}

    def claim_achievement_reward_cloud(self, key, claim_key):
        self.calls.append(("claim", key))
        return {"id": "ledger-1"}

    def unlock_talent_cloud(self, key):
        self.calls.append(("talent", key))
        return {"ok": True}

    def claim_boss_reward_cloud(self, boss_key, member_count, idem):
        self.calls.append(("boss", boss_key, member_count))
        return {"ok": True}


class M09bSyncHandlerTest(_DbBase):
    def _service_with_fake(self):
        for name in ("sync_service", "cloud_service"):
            sys.modules.pop(name, None)
        import sync_service
        svc = sync_service.CloudSyncService.__new__(sync_service.CloudSyncService)
        svc.cloud = _FakeCloud()
        return svc

    def test_achievement_claim_records_unlock_before_claiming(self):
        self.db.enqueue_sync(self.uid, "achievement_claim", "Pemula", "claim",
                             {"achievement_key": "Pemula", "claim_key": "ck-1"})
        svc = self._service_with_fake()
        svc._process_queue(self.uid)
        self.assertEqual(svc.cloud.calls,
                         [("record", "Pemula"), ("claim", "Pemula")])
        self.assertEqual(self._jobs("achievement_claim"), [])

    def test_talent_and_boss_handlers_dispatch(self):
        self.db.enqueue_sync(self.uid, "talent_unlock", "", "unlock",
                             {"talent_key": "warrior_t1_skin",
                              "idempotency_key": "t-1"})
        self.db.enqueue_sync(self.uid, "boss_reward", "", "claim",
                             {"boss_key": "zombie", "member_count": 4,
                              "idempotency_key": "b-1"})
        svc = self._service_with_fake()
        svc._process_queue(self.uid)
        self.assertIn(("talent", "warrior_t1_skin"), svc.cloud.calls)
        self.assertIn(("boss", "zombie", 4), svc.cloud.calls)
        self.assertEqual(self._jobs("talent_unlock"), [])
        self.assertEqual(self._jobs("boss_reward"), [])


class M09bP10UiTest(unittest.TestCase):
    def test_pyqt_shop_has_no_adopt_path(self):
        with open(os.path.join(ROOT, "MainPyQt6.py"), encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("def _adopt(", src)
        self.assertNotIn("shop_adopt", src)
        self.assertNotIn("db.adopt_pet(", src)

    def test_web_has_no_adopt_path(self):
        for rel in ("web/src/api/rpg.ts", "web/src/context/GameContext.tsx",
                    "web/src/components/views/ShopView.tsx"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                self.assertNotIn("adoptPet", fh.read(), rel)
        # Fungsi lokal & route lama tetap ada (bukan UI; kompatibilitas).
        import database as db_mod
        self.assertTrue(callable(db_mod.adopt_pet))


if __name__ == "__main__":
    unittest.main()


class IntegerDivisionFixTests(unittest.TestCase):
    """Migrasi 20261022010000 memakai `//` (operator Python) di SQL.

    Postgres tidak mengenalnya ("operator does not exist: integer //
    integer", ketahuan lewat db lint). Karena migrasi itu sudah terpasang,
    perbaikannya adalah migrasi 20261023020000 yang mengganti tiga fungsi
    dengan div(). Tes ini memaku keduanya: file lama tidak diubah, dan
    file perbaikan tidak boleh membawa `//` di kode (komentar dikecualikan).
    """

    FIX = os.path.join(ROOT, "supabase", "migrations",
                       "20261023020000_fix_m09b_integer_division.sql")

    def test_fix_redefines_three_functions_with_div(self):
        sql = open(self.FIX, encoding="utf-8").read()
        for name in ("unlock_talent_cloud", "fetch_cloud_talents", "claim_boss_reward_cloud"):
            self.assertIn(f"create or replace function public.{name}", sql)
        self.assertIn("div(coalesce(v_level,1), 5)", sql)
        self.assertIn("div(def.xp, v_cnt)", sql)
        self.assertIn("div(def.gold, v_cnt)", sql)

    def test_spin_loop_variable_fix_exists(self):
        path = os.path.join(ROOT, "supabase", "migrations",
                            "20261023030000_fix_spin_pet_loop_variable.sql")
        sql = open(path, encoding="utf-8").read()
        self.assertIn("create or replace function public.spin_pet_cloud", sql)
        self.assertIn("for v_i in 1..6 loop", sql)
        self.assertNotIn("  i integer;", sql)
        self.assertNotIn("for i in", sql)

    def test_fix_has_no_python_floor_division_in_code(self):
        for line in open(self.FIX, encoding="utf-8").read().splitlines():
            code = line.split("--", 1)[0]
            self.assertNotIn(" // ", code, line)
