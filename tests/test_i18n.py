"""i18n consistency gate (UPDATE_ROADMAP M02, UPDATE_RULES.md §3 point 1 / §7).

translations.py is the single source of truth (P2). The two generated JSON
files must contain exactly the same keys in both languages, and every key the
frontend actually uses must exist in both `id` and `en`.

Run:  python -m unittest tests.test_i18n -v
"""
from __future__ import annotations

import json
import os
import re
import sys
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

CORE_JSON = os.path.join(REPO_ROOT, "packages", "craftlife-core", "src", "i18n", "messages.json")
PUBLIC_JSON = os.path.join(REPO_ROOT, "web", "public", "i18n", "messages.json")
WEB_SRC = os.path.join(REPO_ROOT, "web", "src")


def load_catalogue(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class CatalogueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core = load_catalogue(CORE_JSON)
        cls.public = load_catalogue(PUBLIC_JSON)

    def test_both_catalogues_exist(self):
        for path in (CORE_JSON, PUBLIC_JSON):
            with self.subTest(path=path):
                self.assertTrue(os.path.isfile(path), f"missing generated catalogue: {path}")

    def test_both_languages_present(self):
        for name, cat in (("core", self.core), ("public", self.public)):
            with self.subTest(catalogue=name):
                self.assertEqual(set(cat.keys()), {"id", "en"})

    def test_id_and_en_have_identical_key_sets(self):
        for name, cat in (("core", self.core), ("public", self.public)):
            with self.subTest(catalogue=name):
                self.assertEqual(
                    set(cat["id"].keys()),
                    set(cat["en"].keys()),
                    "id/en key sets diverged",
                )

    def test_core_and_public_are_identical(self):
        """The two generated files must never drift apart."""
        self.assertEqual(self.core, self.public)

    def test_no_empty_translations(self):
        for lang in ("id", "en"):
            empty = [k for k, v in self.core[lang].items() if not str(v).strip()]
            self.assertEqual(empty, [], f"{lang} has empty values: {empty[:10]}")

    def test_key_count_matches_translations_py(self):
        """The generated files must reflect translations.py, not a stale export."""
        from translations import TRANSLATIONS

        expected = {
            k
            for k, pair in TRANSLATIONS.items()
            if isinstance(pair, (tuple, list)) and len(pair) >= 2
        }
        self.assertEqual(
            set(self.core["id"].keys()),
            expected,
            "messages.json is out of sync with translations.py — "
            "run: python3 scripts/export_i18n.py",
        )

    def test_key_count_is_in_expected_range(self):
        n = len(self.core["id"])
        self.assertGreaterEqual(n, 4000, "key count dropped unexpectedly")
        self.assertLess(n, 20000, "key count exploded unexpectedly")


class UsageTest(unittest.TestCase):
    """Every key the frontend references must exist in both languages."""

    @classmethod
    def setUpClass(cls):
        cls.core = load_catalogue(CORE_JSON)
        cls.used = cls._collect_used_keys()

    @staticmethod
    def _collect_used_keys() -> set[str]:
        """Keys passed to t('...') / i18n lookups in the web source.

        Deliberately conservative: only quoted literals in the first argument
        position are collected. Literals ending in ``_`` are dynamic key
        prefixes built by concatenation (e.g. ``t('task_difficulty_' + d, …)``)
        and are excluded, because the complete keys they expand to are checked
        separately where they appear as literals.
        """
        pattern = re.compile(r"""\bt\(\s*(['"])([A-Za-z0-9_.\-]+)\1""")
        keys: set[str] = set()
        for root, _dirs, files in os.walk(WEB_SRC):
            for name in files:
                if not name.endswith((".ts", ".tsx")):
                    continue
                with open(os.path.join(root, name), encoding="utf-8") as fh:
                    for m in pattern.finditer(fh.read()):
                        key = m.group(2)
                        if not key.endswith("_"):
                            keys.add(key)
        return keys

    def test_used_keys_exist_in_both_languages(self):
        if not self.used:
            self.skipTest("no t('key') literals found to check")
        for lang in ("id", "en"):
            missing = sorted(self.used - set(self.core[lang].keys()))
            self.assertEqual(
                missing,
                [],
                f"{len(missing)} key(s) used by web/src are missing from '{lang}': {missing[:15]}",
            )

    def test_we_actually_found_keys_to_check(self):
        """Guards against the usage scan silently matching nothing."""
        self.assertGreater(len(self.used), 100, "usage scan found suspiciously few keys")


if __name__ == "__main__":
    unittest.main(verbosity=2)
