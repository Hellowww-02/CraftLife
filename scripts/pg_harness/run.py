#!/usr/bin/env python3
"""Run the real Supabase migrations and pgTAP tests on local PostgreSQL.

Supabase-specific surface (auth.uid(), storage.*, the roles, the realtime
publication) is reproduced by scripts/pg_harness/shim.sql, which is a test
harness and must never be applied to a real project.

This exists because server-side SQL that has never been executed is not
verified SQL. Before this harness, supabase/tests/*.sql could only run against a
live Supabase project, so in practice they never ran at all.

Exit codes
    0  every migration applied and every test file passed
    1  a migration failed, or a test failed
    3  PostgreSQL is not available in this environment (the caller should SKIP,
       never report PASS)

Usage
    python3 scripts/pg_harness/run.py            # full run
    python3 scripts/pg_harness/run.py --keep     # leave the cluster up, print psql command
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHIM = Path(__file__).resolve().parent / "shim.sql"
MIGRATIONS = sorted(glob.glob(str(REPO_ROOT / "supabase" / "migrations" / "*.sql")))
TESTS = sorted(glob.glob(str(REPO_ROOT / "supabase" / "tests" / "*.sql")))

UNAVAILABLE = 3


def find_pg_bin() -> str | None:
    """Locate the PostgreSQL server binaries, on PATH or in the Debian layout."""
    if shutil.which("initdb") and shutil.which("pg_ctl"):
        return str(Path(shutil.which("initdb")).parent)
    for base in sorted(glob.glob("/usr/lib/postgresql/*/bin"), reverse=True):
        if os.path.exists(os.path.join(base, "initdb")):
            return base
    return None


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Cluster:
    def __init__(self, pg_bin: str, keep: bool = False):
        self.pg_bin = pg_bin
        self.keep = keep
        self.tmp = tempfile.mkdtemp(prefix="craftlife-pg-")
        self.data = os.path.join(self.tmp, "data")
        self.sock = os.path.join(self.tmp, "sock")
        os.makedirs(self.sock, exist_ok=True)
        self.port = free_port()
        self.user = "craftlife"
        self.db = "craftlife"
        self.log = os.path.join(self.tmp, "postgres.log")
        self.started = False

    def _pg(self, name: str) -> str:
        return os.path.join(self.pg_bin, name)

    def env(self) -> dict:
        env = dict(os.environ)
        env.update({
            "PGHOST": self.sock,
            "PGPORT": str(self.port),
            "PGUSER": self.user,
            "PGDATABASE": self.db,
            "PGCONNECT_TIMEOUT": "10",
        })
        return env

    def start(self) -> None:
        self._run([self._pg("initdb"), "-D", self.data, "-U", self.user,
                   "--auth=trust", "-E", "UTF8"], capture=True)
        self._run([self._pg("pg_ctl"), "-D", self.data, "-l", self.log, "-w",
                   "-o", f"-p {self.port} -k {self.sock} -c listen_addresses=''",
                   "start"], capture=True)
        self.started = True
        self._run([self._pg("createdb"), self.db])

    def _run(self, cmd: list[str], capture: bool = False, **kw) -> subprocess.CompletedProcess:
        env = self.env() if self.started else dict(os.environ)
        return subprocess.run(cmd, env=env, cwd=self.tmp,
                              capture_output=capture, text=True, **kw)

    def psql(self, args: list[str], **kw) -> subprocess.CompletedProcess:
        return self._run([self._pg("psql"), "-X", "-q", *args], **kw)

    def sql(self, statement: str) -> subprocess.CompletedProcess:
        return self.psql(["-v", "ON_ERROR_STOP=1", "-c", statement], capture=True)

    def file(self, path: str) -> subprocess.CompletedProcess:
        return self.psql(["-v", "ON_ERROR_STOP=1", "-f", path], capture=True)

    def stop(self) -> None:
        if self.started and not self.keep:
            subprocess.run([self._pg("pg_ctl"), "-D", self.data, "-m", "immediate", "stop"],
                           capture_output=True, text=True, env=self.env())
        if not self.keep:
            shutil.rmtree(self.tmp, ignore_errors=True)

    def connect_hint(self) -> str:
        return (f"{self._pg('psql')} -h {self.sock} -p {self.port} "
                f"-U {self.user} -d {self.db}")


def apply_migrations(cluster: Cluster) -> tuple[int, list[str]]:
    cluster.sql("create extension if not exists pgtap with schema extensions")
    cluster.psql(["-f", str(SHIM)])
    # The pgTAP tests call plan()/has_table() unqualified; Supabase puts
    # `extensions` on the default search_path, vanilla PostgreSQL does not.
    cluster.sql(f"alter database {cluster.db} set search_path = public, extensions")

    failures = []
    applied = 0
    for path in MIGRATIONS:
        result = cluster.file(path)
        if result.returncode != 0:
            failures.append(f"{os.path.basename(path)}: {result.stderr.strip().splitlines()[-1] if result.stderr else 'unknown error'}")
        else:
            applied += 1
    return applied, failures


def run_tests(cluster: Cluster) -> tuple[int, int, list[str]]:
    """Return (files_passed, total_assertions, failures) via pg_prove."""
    if not TESTS:
        return 0, 0, ["no test files found in supabase/tests/"]
    pg_prove = shutil.which("pg_prove")
    if not pg_prove:
        return 0, 0, ["pg_prove not installed (apt-get install postgresql-<ver>-pgtap)"]

    env = cluster.env()
    result = subprocess.run(
        [pg_prove, "-d", cluster.db, *TESTS],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT),
    )
    out = result.stdout + result.stderr

    total = 0
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("Files="):
            for part in line.split(","):
                part = part.strip()
                if part.startswith("Tests="):
                    total = int(part.split("=")[1].split()[0])

    failed_files = [ln.split()[0] for ln in out.splitlines()
                    if " (Wstat:" in ln or ln.strip().endswith("Dubious, test returned 1")]
    if result.returncode != 0 and not failed_files:
        failed_files = ["pg_prove exited %d" % result.returncode]
    return (len(TESTS) - len(failed_files)), total, failed_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="leave the cluster running and print the psql command")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    def say(msg: str) -> None:
        if not args.quiet:
            print(msg, flush=True)

    pg_bin = find_pg_bin()
    if not pg_bin:
        say("PostgreSQL server binaries not found — cannot execute the Supabase "
            "migrations. Install with: apt-get install postgresql postgresql-contrib")
        return UNAVAILABLE

    say(f"PostgreSQL binaries: {pg_bin}")
    cluster = Cluster(pg_bin, keep=args.keep)
    try:
        cluster.start()
    except subprocess.CalledProcessError as exc:
        say(f"failed to start a PostgreSQL cluster: {exc}")
        cluster.stop()
        return 1
    except Exception as exc:  # noqa: BLE001 - report and clean up
        say(f"failed to start a PostgreSQL cluster: {exc}")
        cluster.stop()
        return 1

    say(f"cluster up on port {cluster.port}")
    try:
        applied, failures = apply_migrations(cluster)
        say(f"migrations: {applied}/{len(MIGRATIONS)} applied")
        for failure in failures:
            say(f"  FAILED  {failure}")

        if failures:
            return 1

        files_ok, assertions, failed_files = run_tests(cluster)
        say(f"pgTAP: {files_ok}/{len(TESTS)} files passed, {assertions} assertions")
        for failure in failed_files:
            say(f"  FAILED  {failure}")

        if args.keep:
            say(f"\ncluster left running:\n  {cluster.connect_hint()}")
        return 0 if not failed_files else 1
    finally:
        cluster.stop()


if __name__ == "__main__":
    sys.exit(main())
