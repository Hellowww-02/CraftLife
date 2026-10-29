"""Shared test harness for CraftLife.

Zero third-party dependencies: everything here runs on the Python standard
library so the suite can be executed with ``python -m unittest`` on a bare
checkout (UPDATE_RULES.md §8 — avoid unnecessary dependencies).

The important detail this module exists to handle: ``database.py`` computes
``DB_PATH`` once at import time and ``get_conn()`` caches a pooled connection
per thread. Tests therefore have to redirect ``DB_PATH`` *and* drop the cached
connection before the database is touched, otherwise a test silently reads or
writes the developer's real ``craftlife.db``.
"""
from __future__ import annotations

import importlib
import os
import shutil
import sqlite3
import sys
import tempfile
from typing import Any

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _reset_pooled_connection(db: Any) -> None:
    """Drop the per-thread cached connection so DB_PATH changes take effect."""
    local = getattr(db, "_db_conn_local", None)
    if local is None:
        return
    conn = getattr(local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
    try:
        local.conn = None
    except Exception:
        pass


class TempDatabase:
    """An isolated CraftLife SQLite database in a throwaway directory.

    Usage::

        with TempDatabase() as ctx:
            ctx.db.init_db()
            ...

    The process working directory is moved into the temporary directory for the
    lifetime of the context so stray artifacts (``crash.log``, ``db_error.log``)
    cannot land in the repository.
    """

    def __init__(self, seed_from: str | None = None):
        self.seed_from = seed_from
        self.tmpdir = ""
        self.db_path = ""
        self.db: Any = None
        self._cwd = ""

    def __enter__(self) -> "TempDatabase":
        self.tmpdir = tempfile.mkdtemp(prefix="craftlife-test-")
        self.db_path = os.path.join(self.tmpdir, "craftlife.db")
        if self.seed_from:
            shutil.copy2(self.seed_from, self.db_path)

        self._cwd = os.getcwd()
        os.chdir(self.tmpdir)

        # A fresh interpreter-level import each time keeps module state (cached
        # connections, lru_caches) from leaking between tests.
        for mod in [m for m in list(sys.modules) if m == "database" or m.startswith("database.")]:
            del sys.modules[mod]
        self.db = importlib.import_module("database")
        self.db.DB_PATH = self.db_path
        _reset_pooled_connection(self.db)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self.db is not None:
                _reset_pooled_connection(self.db)
        finally:
            os.chdir(self._cwd)
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- helpers ---------------------------------------------------------
    def raw(self) -> sqlite3.Connection:
        """A plain connection that bypasses the pooled wrapper."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def table_names(self) -> set[str]:
        conn = self.raw()
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return {r[0] for r in rows}
        finally:
            conn.close()

    def declared_tables(self) -> set[str]:
        """Table names appearing in CREATE TABLE statements in database.py."""
        import re

        with open(os.path.join(REPO_ROOT, "database.py"), encoding="utf-8") as fh:
            src = fh.read()
        return set(re.findall(r"CREATE TABLE IF NOT EXISTS ([a-z_0-9]+)", src))

    def integrity_check(self) -> str:
        conn = self.raw()
        try:
            return conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()

    def foreign_key_violations(self) -> list:
        conn = self.raw()
        try:
            return conn.execute("PRAGMA foreign_key_check").fetchall()
        finally:
            conn.close()

    def count(self, table: str) -> int:
        conn = self.raw()
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        finally:
            conn.close()

    def make_user(self, username: str = "tester", password: str = "password123") -> int:
        """Create a user and return its local integer id.

        ``register_user`` reports only ``{"ok": True}`` (no id), so the id is
        read back from the users table.
        """
        result = self.db.register_user(username, password, display_name="Tester")
        if not result.get("ok"):
            raise AssertionError(f"register_user failed: {result}")
        conn = self.raw()
        try:
            row = conn.execute(
                "SELECT id FROM users WHERE username=?", (username.lower().strip(),)
            ).fetchone()
        finally:
            conn.close()
        if not row:
            raise AssertionError("register_user did not produce a user row")
        return int(row[0])


_SENTINEL = object()

# Every module that does `import database`. They each keep their own reference
# to the database module object, so purging only `api_server` leaves the others
# pointing at the previous TempDatabase's deleted file — which surfaces as
# "unable to open database file" from deep inside a request handler.
_DB_DEPENDENTS = (
    "api_server", "life_api", "studio_api",
    "cloud_api", "cloud_service", "sync_service",
    # M05d: lapisan penyimpanan memegang referensi modul `database`, sama seperti
    # domain di atasnya. Tanpa entri ini, cloud_api yang diimpor ulang akan
    # menarik storage LAMA yang masih menunjuk DB_PATH yang sudah dihapus.
    "storage",
)


def _purge_db_dependents() -> None:
    for name in _DB_DEPENDENTS:
        sys.modules.pop(name, None)


class LiveApiServer:
    """Boots the real ``api_server`` against a throwaway database.

    Three traps make this worth centralising rather than repeating per module:

    ``api_server.start_server`` is a **module-level singleton** — it returns the
    existing ``_httpd`` when one is set, ignoring the port it was handed. So a
    second test module that imports the cached module gets a dead server and a
    base URL nothing is listening on, and every request times out.

    ``TempDatabase`` re-imports ``database`` to get clean module state, but
    ``life_api``/``studio_api``/``cloud_api`` keep their *old* reference and so
    still read the previous (deleted) DB_PATH. Every module that imports
    ``database`` is therefore purged here, so they all rebind to the same fresh
    instance.

    ``start_server`` also warms the update cache by spawning a daemon thread
    that calls ``updater.check_for_update()`` — a real network request to
    GitHub. Tests must not depend on the network, so that is stubbed out. It is
    also slow: without the stub the route probe took 49s instead of 3s.
    """

    def __init__(self, username: str = "apitester"):
        self.username = username
        self._saved_modules = {}
        self._saved_update = None

    def __enter__(self) -> "LiveApiServer":
        import importlib
        import socket as _socket

        self.ctx = TempDatabase()
        self.ctx.__enter__()
        self.db = self.ctx.db
        self.db.init_db()
        self.uid = self.ctx.make_user(self.username)

        # Rebind every database consumer to the fresh database instance.
        for name in _DB_DEPENDENTS:
            if name in sys.modules:
                self._saved_modules[name] = sys.modules[name]
        _purge_db_dependents()
        self.api = importlib.import_module("api_server")

        # No network during tests.
        self._saved_update = self.api._update_cached_info
        self.api._update_cached_info = lambda: None

        self.api.db.DB_PATH = self.ctx.db_path
        self.api._state.update({"user_id": None, "token": None, "username": None})
        self.api._ensure_user()

        with _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.httpd, self.base = self.api.start_server("127.0.0.1", port)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        if self._saved_update is not None:
            self.api._update_cached_info = self._saved_update
        # Drop the modules so nobody inherits a dead singleton or a stale
        # database reference, then restore whatever was there before.
        _purge_db_dependents()
        sys.modules.update(self._saved_modules)
        self._saved_modules = {}
        self.ctx.__exit__(exc_type, exc, tb)
