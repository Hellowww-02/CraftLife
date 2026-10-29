"""M09a — Pet gacha server-authoritative.

Dua lapis bukti:

1. Kontrak migrasi (statis): migrasi M09a harus memindahkan keputusan spin
   ke server dengan konstanta yang PERSIS sama seperti jalur lokal
   (`SPIN_COST`, `SPIN_ODDS`, pity, EXP duplikat) dan pola keamanan
   Phase 5A/5B (ledger + idempotency + RLS + grant authenticated saja).
   Spin yang diundi client adalah bug yang ditutup fase ini, jadi angka
   yang menyimpang di SQL harus menggagalkan test.

2. Cermin lokal (perilaku): `apply_cloud_spin_result` menerapkan hasil
   server ke tabel lokal tanpa mengundi apa pun — nilai absolut dari
   `fetch_cloud_pets` membuat penerapan ulang aman, gold lokal terpotong
   sekali per spin segar dan tidak pada putar-ulang idempoten.
"""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.harness import TempDatabase

MIGRATION = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "supabase", "migrations", "20261022000000_phase_m09a_pet_gacha_server.sql")


def _sql() -> str:
    with open(MIGRATION, encoding="utf-8") as fh:
        return fh.read()


class M09aMigrationContractTest(unittest.TestCase):
    def test_tables_and_spin_log_exist(self):
        sql = _sql()
        for table in ("pets_server", "cloud_user_pets",
                      "cloud_pet_spin_state", "cloud_pet_spins"):
            self.assertIn(f"create table if not exists public.{table}", sql)
        # Log spin adalah jangkar idempotency: satu key per user sekali.
        self.assertIn("unique (user_id, idempotency_key)", sql)

    def test_spin_constants_match_local_rules(self):
        sql = _sql()
        # SPIN_ODDS lokal: common 34 / rare 26 / epic 18 / legendary 12 /
        # mythic 8 / secret 2, urutan PET_RANKS yang sama.
        self.assertIn("array['common','rare','epic','legendary','mythic','secret']", sql)
        self.assertIn("array[34,26,18,12,8,2]", sql)
        self.assertIn("v_cost integer := 120", sql)          # SPIN_COST
        self.assertIn("v_dupe_exp integer := 60", sql)       # 0.5 * 120 (K2)
        self.assertIn("st.since_legendary + 1 >= 30", sql)   # PITY_LEGENDARY
        self.assertIn("st.since_epic + 1 >= 10", sql)        # PITY_EPIC
        # Level-up pet lokal: butuh level*100 EXP (add_pet_exp).
        self.assertIn("while v_exp >= v_level * 100 loop", sql)

    def test_spin_charges_through_ledger_and_replays(self):
        sql = _sql()
        self.assertIn("public.spend_gold(uid, v_cost, 'pet_spin', v_pet, 'petspin:' || p_idem)", sql)
        self.assertIn("'replay', true", sql)
        self.assertIn("raise exception 'missing_idempotency_key'", sql)
        self.assertIn("for update", sql)  # serialisasi pity per pengguna
        self.assertIn("public.current_profile_active()", sql)

    def test_security_shape_matches_phase5(self):
        sql = _sql()
        self.assertIn("security definer set search_path=public", sql)
        for table in ("pets_server", "cloud_user_pets",
                      "cloud_pet_spin_state", "cloud_pet_spins"):
            self.assertIn(f"alter table public.{table} enable row level security", sql)
            self.assertIn(f"revoke insert, update, delete on public.{table} from authenticated, anon, public", sql)
        self.assertIn("revoke execute on function public.spin_pet_cloud(text) from public, anon", sql)
        self.assertIn("grant execute on function public.spin_pet_cloud(text) to authenticated", sql)
        self.assertIn("grant execute on function public.fetch_cloud_pets() to authenticated", sql)

    def test_seed_covers_every_local_pet_with_same_rank(self):
        import database as db_mod
        sql = _sql()
        inserts = [ln for ln in sql.splitlines()
                   if ln.startswith("insert into public.pets_server")]
        self.assertEqual(len(inserts), len(db_mod.PETS_DATA))
        for pet_key, meta in db_mod.PETS_DATA.items():
            line = next((ln for ln in inserts if f"('{pet_key}'" in ln), None)
            self.assertIsNotNone(line, f"seed hilang: {pet_key}")
            self.assertIn(f"'{meta['rank']}'", line)


class _MirrorBase(unittest.TestCase):
    def setUp(self):
        self._ctx = TempDatabase()
        self.ctx = self._ctx.__enter__()
        self.db = self.ctx.db
        self.db.init_db()
        res = self.db.register_user("m09auser", "password123")
        self.assertTrue(res.get("ok"), res)
        conn = self.db.get_conn()
        self.uid = conn.execute(
            "SELECT id FROM users WHERE username='m09auser'").fetchone()["id"]
        conn.execute("UPDATE users SET gold=1000 WHERE id=?", (self.uid,))
        conn.commit(); conn.close()

    def tearDown(self):
        self._ctx.__exit__(None, None, None)

    def _gold(self) -> float:
        conn = self.db.get_conn()
        gold = conn.execute("SELECT gold FROM users WHERE id=?",
                            (self.uid,)).fetchone()["gold"]
        conn.close()
        return gold


class M09aApplySpinResultTest(_MirrorBase):
    def test_new_pet_mirrored_and_gold_debited_once(self):
        result = {"pet_id": "cat", "rank": "common", "is_new": True,
                  "dupe_exp": 0, "cost": 120, "spins_total": 1,
                  "since_epic": 1, "since_legendary": 1}
        out = self.db.apply_cloud_spin_result(self.uid, result)
        self.assertTrue(out["ok"])
        pets = self.db.get_user_pets(self.uid)
        self.assertEqual([p["pet_id"] for p in pets], ["cat"])
        # Terpotong 120 (biaya spin); bonus achievement pet_adopt boleh
        # menambah kembali, sama seperti spin_pet lokal.
        self.assertTrue(880 <= self._gold() < 1000, self._gold())
        state = self.db.get_spin_state(self.uid)
        self.assertEqual(state, {"spins_total": 1, "since_epic": 1,
                                 "since_legendary": 1})

    def test_replay_does_not_debit_or_duplicate(self):
        result = {"pet_id": "cat", "rank": "common", "is_new": True,
                  "dupe_exp": 0, "cost": 120, "spins_total": 1,
                  "since_epic": 1, "since_legendary": 1}
        self.db.apply_cloud_spin_result(self.uid, result)
        gold_after_first = self._gold()
        replay = dict(result, replay=True)
        self.db.apply_cloud_spin_result(self.uid, replay)
        self.assertEqual(len(self.db.get_user_pets(self.uid)), 1)
        self.assertEqual(self._gold(), gold_after_first)

    def test_dupe_uses_absolute_cloud_values(self):
        first = {"pet_id": "cat", "rank": "common", "is_new": True,
                 "dupe_exp": 0, "cost": 120}
        self.db.apply_cloud_spin_result(self.uid, first)
        payload = {"pets": [{"pet_key": "cat", "level": 2, "exp": 40,
                             "hunger": 90, "happiness": 60, "is_active": False}],
                   "spin_state": {"spins_total": 2, "since_epic": 2,
                                  "since_legendary": 2}}
        dupe = {"pet_id": "cat", "rank": "common", "is_new": False,
                "dupe_exp": 60, "cost": 120}
        self.db.apply_cloud_spin_result(self.uid, dupe, payload)
        self.db.apply_cloud_spin_result(self.uid, dupe, payload)  # ulang: absolut
        pet = self.db.get_user_pets(self.uid)[0]
        self.assertEqual((pet["level"], pet["exp"]), (2, 40))
        self.assertEqual((pet["hunger"], pet["happiness"]), (90, 60))

    def test_invalid_result_rejected(self):
        out = self.db.apply_cloud_spin_result(self.uid, {"rank": "common"})
        self.assertFalse(out["ok"])
        self.assertEqual(self.db.get_user_pets(self.uid), [])
        self.assertEqual(self._gold(), 1000)


class M09aCloudPetsCacheTest(_MirrorBase):
    def test_save_and_read_cache(self):
        payload = {"pets": [{"pet_key": "bee", "level": 3, "exp": 10,
                             "hunger": 80, "happiness": 70, "is_active": True}],
                   "spin_state": {"spins_total": 5, "since_epic": 2,
                                  "since_legendary": 5}}
        self.db.save_cloud_pets(self.uid, payload)
        rows = self.db.get_cloud_pets_cache(self.uid)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pet_key"], "bee")
        self.assertEqual(rows[0]["level"], 3)
        self.assertEqual(rows[0]["is_active"], 1)
        self.assertEqual(self.db.get_cloud_pet_spin_state_cache(self.uid),
                         {"spins_total": 5, "since_epic": 2, "since_legendary": 5})

    def test_empty_cache_defaults(self):
        self.assertEqual(self.db.get_cloud_pets_cache(self.uid), [])
        self.assertEqual(self.db.get_cloud_pet_spin_state_cache(self.uid),
                         {"spins_total": 0, "since_epic": 0, "since_legendary": 0})


class _FakeCloud:
    def __init__(self, result, payload):
        self._result = result
        self._payload = payload
        self.spin_keys = []

    def spin_pet_cloud(self, idem):
        self.spin_keys.append(idem)
        return dict(self._result)

    def fetch_cloud_pets(self):
        return dict(self._payload)


class _FakeStore:
    def __init__(self, db):
        self._db = db
        self.saved = []

    def save_cloud_pets(self, user_id, payload):
        self.saved.append(payload)
        return self._db.save_cloud_pets(user_id, payload)

    def apply_cloud_spin_result(self, user_id, result, payload=None):
        return self._db.apply_cloud_spin_result(user_id, result, payload)


class M09aCloudApiSpinTest(_MirrorBase):
    def test_pets_cloud_spin_mirrors_without_local_roll(self):
        import cloud_api
        payload = {"pets": [{"pet_key": "cat", "level": 1, "exp": 0,
                             "hunger": 100, "happiness": 50, "is_active": False}],
                   "spin_state": {"spins_total": 1, "since_epic": 1,
                                  "since_legendary": 1}}
        result = {"pet_id": "cat", "rank": "common", "is_new": True,
                  "dupe_exp": 0, "cost": 120, "gold": 880}
        fake_cloud = _FakeCloud(result, payload)
        fake_store = _FakeStore(self.db)
        old_cloud, old_store = cloud_api.get_cloud_service, cloud_api.get_store
        cloud_api.get_cloud_service = lambda: fake_cloud
        cloud_api.get_store = lambda: fake_store
        try:
            out = cloud_api.pets_cloud_spin(self.uid, "idem-1")
        finally:
            cloud_api.get_cloud_service, cloud_api.get_store = old_cloud, old_store
        self.assertTrue(out["ok"])
        self.assertTrue(out["cloud"])
        self.assertEqual(out["pet_id"], "cat")
        self.assertEqual(fake_cloud.spin_keys, ["idem-1"])
        self.assertEqual([p["pet_id"] for p in self.db.get_user_pets(self.uid)], ["cat"])
        self.assertTrue(880 <= self._gold() < 1000, self._gold())


if __name__ == "__main__":
    unittest.main()
