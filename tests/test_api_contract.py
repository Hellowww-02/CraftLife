"""Live API contract smoke tests (UPDATE_RULES.md §7, UPDATE_ROADMAP M02).

Boots the real ``api_server`` against a throwaway database on an ephemeral port
and asserts response shapes, so the 234-route contract the web client depends
on cannot drift silently.

Run:  python -m unittest tests.test_api_contract -v
"""
from __future__ import annotations

import json
import sys
import unittest
import urllib.error
import urllib.request

from tests.harness import LiveApiServer, REPO_ROOT


class ApiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("apitester")
        cls._server.__enter__()
        cls.api = cls._server.api
        cls.ctx = cls._server.ctx
        cls.db = cls._server.db
        cls.uid = cls._server.uid
        cls.base = cls._server.base
        cls.httpd = cls._server.httpd

    @classmethod
    def tearDownClass(cls):
        cls._server.__exit__(None, None, None)

    # -- helpers ---------------------------------------------------------
    def get(self, path: str):
        """Returns (status, parsed_json_or_None)."""
        req = urllib.request.Request(f"{self.base}{path}", headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8")
                status = resp.status
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            status = exc.code
        try:
            return status, json.loads(body)
        except (ValueError, TypeError):
            return status, None

    # -- liveness --------------------------------------------------------
    def test_health_is_public_and_ok(self):
        status, data = self.get("/api/health")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)

    def test_version_matches_app_version(self):
        status, data = self.get("/api/version")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)

        sys.path.insert(0, REPO_ROOT)
        import updater

        reported = json.dumps(data)
        self.assertIn(
            updater.APP_VERSION,
            reported,
            f"/api/version does not report APP_VERSION {updater.APP_VERSION}: {data}",
        )

    def test_unknown_api_route_falls_through_to_the_spa(self):
        """Documents ACTUAL behaviour: unmatched paths are served the built web
        UI, because api_server doubles as the static host for web/dist.

        Consequence worth knowing: a typo'd /api/... route answers 200 + HTML,
        so the client sees a JSON parse error rather than a clean 404. Pinned
        here so the behaviour cannot change by accident.
        """
        status, data = self.get("/api/definitely-not-a-real-route")
        self.assertEqual(status, 200)
        self.assertIsNone(data, "expected non-JSON (SPA HTML), got JSON")

        req = urllib.request.Request(f"{self.base}/api/definitely-not-a-real-route")
        with urllib.request.urlopen(req, timeout=15) as resp:
            ctype = resp.headers.get("Content-Type", "")
            body = resp.read().decode("utf-8", errors="replace")
        self.assertIn("text/html", ctype)
        self.assertIn("<!doctype html>", body.lower())

    # -- i18n ------------------------------------------------------------
    def test_i18n_is_public_and_bilingual(self):
        """§7 — /api/i18n must serve both languages without auth."""
        for lang in ("id", "en"):
            with self.subTest(lang=lang):
                status, data = self.get(f"/api/i18n?lang={lang}")
                self.assertEqual(status, 200)
                self.assertIsInstance(data, dict)
                messages = data.get("messages") or {}
                self.assertGreater(len(messages), 4000, f"{lang} catalogue looks truncated")

    def test_i18n_languages_differ(self):
        _, id_data = self.get("/api/i18n?lang=id")
        _, en_data = self.get("/api/i18n?lang=en")
        id_msgs = id_data.get("messages") or {}
        en_msgs = en_data.get("messages") or {}
        self.assertEqual(set(id_msgs.keys()), set(en_msgs.keys()))
        # Not a hard requirement for every key, but the catalogues as a whole
        # must not be identical or one language is not really translated.
        self.assertNotEqual(id_msgs, en_msgs)

    def test_newly_registered_fx_keys_are_served(self):
        """Regression guard for the P7 gap the M02 suite found: the LED/FX
        settings labels must exist in both languages."""
        for lang in ("id", "en"):
            with self.subTest(lang=lang):
                _, data = self.get(f"/api/i18n?lang={lang}")
                messages = data.get("messages") or {}
                for key in ("settings_fx_title", "settings_fx_ambient", "settings_fx_ambient_desc"):
                    self.assertIn(key, messages, f"{key} missing from {lang}")
                    self.assertTrue(str(messages[key]).strip(), f"{key} empty in {lang}")

    # -- authenticated surface ------------------------------------------
    def test_profile_talents_endpoint_shape(self):
        """There is no bare /api/profile; the profile page consumes sub-routes."""
        status, data = self.get("/api/profile/talents")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        self.assertTrue(data.get("ok"))
        self.assertIn("talents", data)

    def test_avatar_class_catalogue_shape(self):
        status, data = self.get("/api/catalog/avatar-classes")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        classes = data.get("classes")
        self.assertIsInstance(classes, list)
        self.assertGreater(len(classes), 0, "avatar class catalogue is empty")
        for entry in classes:
            self.assertIn("key", entry)

    def test_habits_endpoint_shape(self):
        status, data = self.get("/api/habits")
        self.assertEqual(status, 200)
        self.assertIsInstance(data, dict)
        self.assertTrue(data.get("ok"))
        # The web client iterates data.habits; changing this breaks the page.
        self.assertIsInstance(data.get("habits"), list)

    def test_response_is_json_content_type(self):
        req = urllib.request.Request(f"{self.base}/api/health", headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            ctype = resp.headers.get("Content-Type", "")
        self.assertIn("application/json", ctype)

    def test_server_is_bound_to_loopback(self):
        """The local API must not be reachable from the network."""
        host = self.httpd.server_address[0]
        self.assertIn(host, ("127.0.0.1", "localhost"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
