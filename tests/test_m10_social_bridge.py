"""M10 — jembatan sosial cloud untuk Android + token push.

Yang dijaga tes ini:
  * migrasi device_push_tokens benar-benar mengunci token per pemilik
    (RLS + RPC memakai auth.uid(), bukan user_id dari client);
  * route cloud_api menolak/bersikap jujur saat user belum tertaut cloud
    (linked:false, BUKAN berpura-pura berhasil);
  * push-token tanpa token ditolak sebelum menyentuh cloud;
  * aksi guild online diteruskan ke RPC cloud_service yang benar (kick,
    role, transfer, ban adalah hak server — client hanya meneruskan).
"""

import pathlib
import unittest
from unittest import mock

import cloud_api

ROOT = pathlib.Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "supabase" / "migrations" / "20261023000000_phase_m10_push_tokens.sql"


class FakeStore:
    def __init__(self, linked=True):
        self._linked = linked

    def get_cloud_user_link(self, uid):
        return {"cloud_user_id": "cloud-user-1"} if self._linked else None


class FakeSync:
    def ensure_session(self, uid):
        return True


class FakeCloud:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def _call(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name == "get_my_online_guild_summary":
                return {"guild_id": "g1", "name": "Naga"}
            if name == "get_online_guilds":
                return [{"id": "g1", "name": "Naga"}]
            if name == "get_online_guild_members":
                return [{"user_id": "u2", "role": "member"}]
            if name == "get_online_guild_messages":
                return [{"id": "m1", "body": "halo"}]
            if name == "get_online_guild_message_reactions":
                return {"m1": {"👍": 1}}
            if name == "get_social_notifications":
                return [
                    {"id": "n1", "is_read": False, "type": "friend"},
                    {"id": "n2", "is_read": True, "type": "guild"},
                ]
            return {"ok": True}

        return _call


def _patched(linked=True):
    cloud = FakeCloud()
    return cloud, (
        mock.patch.object(cloud_api, "get_store", lambda: FakeStore(linked)),
        mock.patch.object(cloud_api, "get_sync_service", lambda: FakeSync()),
        mock.patch.object(cloud_api, "get_cloud_service", lambda: cloud),
    )


class MigrationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = MIGRATION.read_text(encoding="utf-8")

    def test_table_and_owner_rls(self):
        self.assertIn("create table if not exists public.device_push_tokens", self.sql)
        self.assertIn("enable row level security", self.sql)
        self.assertIn("user_id = auth.uid()", self.sql)
        self.assertIn("unique (user_id, token)", self.sql)

    def test_register_rpc_uses_auth_uid_not_client_input(self):
        self.assertIn("function public.register_push_token", self.sql)
        self.assertIn("values (auth.uid()", self.sql)
        self.assertIn("grant execute on function public.register_push_token(text, text, text) to authenticated", self.sql)
        self.assertIn("from public, anon", self.sql)


class BridgeTests(unittest.TestCase):
    def test_guild_online_unlinked_is_honest(self):
        _cloud, patches = _patched(linked=False)
        with patches[0], patches[1], patches[2]:
            out = cloud_api.handle_get("/api/cloud/guild-online", 7)
        self.assertTrue(out["ok"])
        self.assertFalse(out["linked"])
        self.assertEqual(out["members"], [])

    def test_guild_online_shapes_payload(self):
        _cloud, patches = _patched()
        with patches[0], patches[1], patches[2]:
            out = cloud_api.handle_get("/api/cloud/guild-online", 7)
        self.assertTrue(out["linked"])
        self.assertEqual(out["summary"]["name"], "Naga")
        self.assertEqual(out["members"][0]["role"], "member")
        self.assertEqual(out["messageReactions"], {"m1": {"👍": 1}})

    def test_notifications_unread_count(self):
        _cloud, patches = _patched()
        with patches[0], patches[1], patches[2]:
            out = cloud_api.handle_get("/api/cloud/notifications", 7)
        self.assertEqual(out["unread"], 1)
        self.assertEqual(len(out["notifications"]), 2)

    def test_push_token_requires_token_then_registers(self):
        cloud, patches = _patched()
        with patches[0], patches[1], patches[2]:
            bad = cloud_api.handle_post("/api/cloud/push-token", 7, {})
            good = cloud_api.handle_post(
                "/api/cloud/push-token", 7, {"token": "fcm-123", "platform": "android"})
        self.assertEqual(bad["error"], "token_required")
        self.assertTrue(good["ok"])
        name, args, _kwargs = cloud.calls[-1]
        self.assertEqual(name, "register_push_token")
        self.assertEqual(args[0], "fcm-123")

    def test_guild_actions_dispatch_to_cloud_rpc_wrappers(self):
        cloud, patches = _patched()
        cases = [
            ("kick", {"guildId": "g1", "userId": "u2"}, "kick_online_guild_member"),
            ("role", {"guildId": "g1", "userId": "u2", "role": "officer"}, "set_online_guild_role"),
            ("transfer", {"guildId": "g1", "userId": "u2"}, "transfer_online_guild_leader"),
            ("ban", {"guildId": "g1", "userId": "u2", "reason": "spam"}, "ban_online_guild_member"),
            ("message", {"guildId": "g1", "text": "halo guild"}, "send_online_guild_message"),
            ("boss-claim", {"battleId": "b1"}, "claim_online_guild_boss_reward"),
        ]
        with patches[0], patches[1], patches[2]:
            for action, body, _expected in cases:
                out = cloud_api.handle_post(f"/api/cloud/guild-online/{action}", 7, body)
                self.assertTrue(out["ok"], action)
            unknown = cloud_api.handle_post("/api/cloud/guild-online/ngawur", 7, {})
        names = [c[0] for c in cloud.calls]
        for _action, _body, expected in cases:
            self.assertIn(expected, names)
        self.assertEqual(unknown["error"], "unknown_action")

    def test_guild_create_requires_name(self):
        _cloud, patches = _patched()
        with patches[0], patches[1], patches[2]:
            out = cloud_api.handle_post("/api/cloud/guild-online/create", 7, {"name": "  "})
        self.assertEqual(out["error"], "name_required")


if __name__ == "__main__":
    unittest.main()
