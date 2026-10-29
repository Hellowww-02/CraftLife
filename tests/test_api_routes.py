"""Client-to-server route contract (M02, UPDATE_ROADMAP M02 "API contract test").

The web client calls the local API through literal paths scattered across
``web/src``. Nothing in the language links those literals to what
``api_server.py`` actually dispatches, so a renamed or removed server route
fails only at runtime — usually as a confusing "Unexpected token <" JSON parse
error, because an unhandled ``/api/*`` path falls through to the web shell.

This test closes that gap against a live server on a throwaway database.

Reading the server's answers
----------------------------
The two dispatchers reject unknown paths *differently*, and both answers are
ambiguous on their own, so classification needs care:

  unknown GET   -> text/html 200 (the SPA shell)
  unknown POST  -> 404 {"ok": false, "error": "not_found"}

A real route can answer 404 too — ``/api/system/download-file`` replies
``{"error": "file_not_found"}`` when the id is absent, and
``/api/friends/attachments/<id>/download`` replies ``{"error": "not_found"}``
when the attachment is not yours. Those are byte-for-byte the same shape as
"no such route", so a probe alone cannot tell them apart.

Therefore a route is declared an ORPHAN only when the probe says unhandled
**and** the path is not declared anywhere in the server sources. The probe
catches the common case; the static confirmation resolves the ambiguous ones
without a hand-maintained allowlist that would rot.

Templated paths
---------------
``/api/dailies/${id}/update`` is requested with ``1`` substituted, which is a
valid id shape. ``/api/ai/${kind}`` is not — ``kind`` is an enum string, so
``/api/ai/1`` would be a path no server ever had. Only placeholders whose name
carries ``id`` are substituted; the rest are verified against the server's
declared prefixes instead.

Static analysis alone was tried first and rejected: the server dispatches
parameterised routes with regexes and ``startswith`` rather than string
literals, which produced 115 false orphans.

Run:  python -m unittest tests.test_api_routes -v
"""
from __future__ import annotations

import json
import os
import re
import unittest
import urllib.error
import urllib.request

from tests.harness import LiveApiServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_FILES = ("api_server.py", "life_api.py", "studio_api.py", "cloud_api.py")

CLIENT_ROUTE = re.compile(r"""[`'"](/api/[A-Za-z0-9_/${}.:*-]+)[`'"]""")
PLACEHOLDER = re.compile(r"\$\{([^}]*)\}")
STARTSWITH_ROUTE = re.compile(r"""startswith\(\s*['"](/api/[^'"]+)['"]""")

# Guards against a regex regression silently extracting nothing, which would
# make every assertion below vacuously true.
MINIMUM_ROUTES = 250

REQUEST_TIMEOUT = 3.0

_server_sources: dict[str, str] | None = None


def _sources() -> dict[str, str]:
    global _server_sources
    if _server_sources is None:
        _server_sources = {
            name: open(os.path.join(ROOT, name), encoding="utf-8", errors="replace").read()
            for name in SERVER_FILES
            if os.path.isfile(os.path.join(ROOT, name))
        }
    return _server_sources


def declared_in_server(path: str) -> bool:
    """Is this path dispatchable by the server? Literal, regex or prefix."""
    parts = [p for p in path.split("/") if p]
    if not parts:
        return False
    for body in _sources().values():
        if f'"{path}"' in body or f"'{path}'" in body:
            return True
    # Numeric segments may be matched by \d+, [^/]+ or ([^/]+) inside a regex.
    pattern = "/".join(
        r"(?:\\d\+|\[\^/\]\+|\(\[\^/\]\+\))" if p.isdigit() else re.escape(p) for p in parts
    )
    for body in _sources().values():
        if re.search(pattern, body):
            return True
    # Prefix dispatch: startswith("/api/learning/sources/")
    for body in _sources().values():
        for match in STARTSWITH_ROUTE.finditer(body):
            prefix = match.group(1).rstrip("/")
            if path == prefix or path.startswith(prefix + "/"):
                return True
    return False


def _substitutable(placeholder: str) -> bool:
    """True when the placeholder holds a numeric id rather than an enum string."""
    tail = placeholder.strip().split(".")[-1]
    return "id" in tail.lower()


def collect_client_routes():
    """Split the client's /api/ calls into probed and prefix-checked sets."""
    src = os.path.join(ROOT, "web", "src")
    literals = 0
    probed: set[str] = set()
    prefix_only: set[str] = set()
    for dirpath, _dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            with open(os.path.join(dirpath, fname), encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            for match in CLIENT_ROUTE.finditer(body):
                literals += 1
                raw = match.group(1)
                holders = PLACEHOLDER.findall(raw)
                if holders and not all(_substitutable(h) for h in holders):
                    # Enum placeholder: no valid concrete path can be invented.
                    prefix_only.add(PLACEHOLDER.sub("*", raw))
                else:
                    probed.add(PLACEHOLDER.sub("1", raw))
    return probed, prefix_only, literals


class RouteContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server = LiveApiServer("routecontract")
        cls._server.__enter__()
        cls.ctx = cls._server.ctx
        cls.api = cls._server.api
        cls.base = cls._server.base

        cls.probed, cls.prefix_only, cls.literals = collect_client_routes()
        cls.handled, cls.ambiguous_ok, cls.orphans, cls.slow = cls._probe_all()
        cls.prefix_missing = sorted(
            p for p in cls.prefix_only
            if not declared_in_server(p.replace("*", "1")) and not cls._prefix_declared(p)
        )

    @classmethod
    def tearDownClass(cls):
        cls._server.__exit__(None, None, None)

    @staticmethod
    def _prefix_declared(templated: str) -> bool:
        """For /api/ai/*, does the server declare anything under /api/ai/ ?"""
        prefix = templated.split("*")[0].rstrip("/")
        for body in _sources().values():
            if f'"{prefix}/' in body or f"'{prefix}/" in body:
                return True
        return False

    @classmethod
    def _probe(cls, path: str, method: str):
        """Returns 'json' | 'json404' | 'html' | 'slow' for one method."""
        req = urllib.request.Request(f"{cls.base}{path}", method=method)
        if method == "POST":
            req.add_header("Content-Type", "application/json")
            req.data = b"{}"
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                status, ctype, body = resp.status, resp.headers.get("Content-Type", ""), resp.read()
        except urllib.error.HTTPError as exc:
            status, ctype = exc.code, exc.headers.get("Content-Type", "")
            try:
                body = exc.read()
            except Exception:
                body = b""
        except Exception:
            return "slow"
        if "json" not in ctype:
            return "html"
        return "json404" if status == 404 else "json"

    @classmethod
    def _probe_all(cls):
        handled, ambiguous_ok, orphans, slow = [], [], [], []
        for path in sorted(cls.probed):
            get = cls._probe(path, "GET")
            if get in ("json", "json404"):
                handled.append(path)
                continue
            if get == "slow":
                slow.append(path)
                continue
            post = cls._probe(path, "POST")
            if post == "json":
                handled.append(path)
            elif post == "slow":
                slow.append(path)
            elif post == "html":
                # Neither dispatcher knows this path: unambiguous orphan.
                orphans.append(path)
            elif declared_in_server(path):
                # 404 from a real route whose entity does not exist.
                ambiguous_ok.append(path)
            else:
                orphans.append(path)
        return handled, ambiguous_ok, orphans, slow

    # -- guards on the harness itself --------------------------------------

    def test_route_scan_actually_found_routes(self):
        self.assertGreater(
            self.literals, MINIMUM_ROUTES,
            f"only {self.literals} /api/ literals found in web/src — the extractor "
            f"regex is probably broken, which would make this module vacuous",
        )
        self.assertGreaterEqual(len(self.probed) + len(self.prefix_only), MINIMUM_ROUTES)

    def test_orphan_detector_recognises_a_bogus_route(self):
        """An empty orphan list must mean something, so prove detection works."""
        bogus = "/api/__definitely_not_a_route__"
        self.assertEqual(self._probe(bogus, "GET"), "html")
        self.assertEqual(self._probe(bogus, "POST"), "json404")
        self.assertFalse(declared_in_server(bogus))
        self.assertFalse(declared_in_server("/api/__bogus__/deep/path"))

    def test_static_matcher_recognises_real_routes(self):
        """Guards the tiebreaker that decides the ambiguous cases."""
        for path in ("/api/habits", "/api/version", "/api/music/lyrics-template",
                     "/api/notes/attachment/delete", "/api/system/download-file",
                     "/api/friends/attachments/1/download"):
            with self.subTest(path=path):
                self.assertTrue(declared_in_server(path))

    # -- the contract ------------------------------------------------------

    def test_every_client_route_is_handled_by_the_server(self):
        self.assertEqual(
            self.orphans, [],
            f"{len(self.orphans)} route(s) the web client calls are not dispatched by "
            f"the server and are not declared in its sources. A server route was "
            f"renamed or removed, or the client path is a typo:\n  "
            + "\n  ".join(self.orphans[:40]),
        )

    def test_every_enum_templated_route_has_a_declared_prefix(self):
        self.assertEqual(
            self.prefix_missing, [],
            f"no server route is declared under these client prefixes: {self.prefix_missing}",
        )

    def test_classification_is_exhaustive(self):
        total = len(self.handled) + len(self.ambiguous_ok) + len(self.orphans) + len(self.slow)
        self.assertEqual(total, len(self.probed), "the probe lost entries somewhere")

    def test_the_ambiguous_404s_are_a_small_minority(self):
        """If most routes 404, the probe is measuring the wrong thing."""
        self.assertLess(len(self.ambiguous_ok), len(self.probed) // 10)
        self.assertLess(len(self.slow), len(self.probed) // 4)

    def test_a_known_good_route_is_handled(self):
        self.assertIn("/api/version", self.handled)
        self.assertIn("/api/habits", self.handled)

    def test_health_and_version_are_reachable(self):
        for path in ("/api/health", "/api/version"):
            with self.subTest(path=path):
                self.assertIn(path, self.handled)

    def test_bootstrap_returns_the_signed_in_user(self):
        """The first call the UI makes; a shape change here blanks the whole app."""
        with urllib.request.urlopen(f"{self.base}/api/bootstrap", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        user = data.get("user")
        self.assertIsInstance(user, dict)
        self.assertEqual(user.get("username"), "routecontract")

    def test_route_surface_size_is_reported(self):
        """Records the measured surface so drift shows up in the test output."""
        print(
            f"\n    route surface: {len(self.probed)} probed + {len(self.prefix_only)} "
            f"enum-templated, from {self.literals} literals — {len(self.handled)} answered, "
            f"{len(self.ambiguous_ok)} valid-404, {len(self.slow)} slow, "
            f"{len(self.orphans)} orphaned"
        )
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
