#!/usr/bin/env python3
"""CraftLife §7 verification gates — one runner for local use and CI.

UPDATE_RULES.md §7 lists ten gates that must all pass before a phase is called
done. Scattering them across a CI YAML makes them hard to run locally and easy
to drift from the rule text, so they are implemented once here and the workflow
just calls this file.

    python3 scripts/verify_gates.py              # all gates
    python3 scripts/verify_gates.py --only i18n  # one gate
    python3 scripts/verify_gates.py --list       # show gate names

Exit code is 0 only when every gate passes. A gate that cannot run in the
current environment reports SKIP with a reason and does NOT fail the run, so a
developer without Node can still check the Python half; CI runs everything.

Gates 11 and 12 are additions beyond §7: the version anchors (roadmap K22) and
the no-secrets rule (§9). Both have already bitten this project once.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PY_MODULES = [
    "api_server.py", "database.py", "studio_api.py", "life_api.py",
    "learning_helper.py", "music_downloader.py", "translations.py", "updater.py",
]

I18N_TARGETS = [
    os.path.join("packages", "craftlife-core", "src", "i18n", "messages.json"),
    os.path.join("web", "public", "i18n", "messages.json"),
]

# Files that must never be committed (UPDATE_RULES.md §9).
FORBIDDEN_TRACKED = re.compile(r"(^|/)\.env$|(^|/)craftlife\.db|(^|/)logs/")


def run(cmd, cwd=ROOT, timeout=1800):
    """Run a command, returning (exit_code, combined_output)."""
    proc = subprocess.run(
        cmd, cwd=cwd, shell=isinstance(cmd, str),
        capture_output=True, text=True, timeout=timeout,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def have(cmd):
    from shutil import which
    return which(cmd) is not None


# ---------------------------------------------------------------------------
# Gate 1 — Python syntax
# ---------------------------------------------------------------------------
def gate_python_syntax():
    missing = [m for m in PY_MODULES if not os.path.isfile(os.path.join(ROOT, m))]
    if missing:
        return False, f"missing modules: {missing}"
    code, out = run([sys.executable, "-m", "py_compile", *PY_MODULES])
    if code != 0:
        return False, out.strip()[-800:]
    return True, f"{len(PY_MODULES)} modules compile clean"


# ---------------------------------------------------------------------------
# Gate 2 — TypeScript
# ---------------------------------------------------------------------------
def gate_types():
    if not have("npm"):
        return None, "npm not installed"
    code, out = run(["npm", "run", "typecheck"], timeout=900)
    if code != 0:
        return False, out.strip()[-1200:]
    return True, "core tsc + web tsc: 0 errors"


# ---------------------------------------------------------------------------
# Gate 3 — Build, recording asset hash + size as §7 requires
# ---------------------------------------------------------------------------
def gate_build():
    if not have("npm"):
        return None, "npm not installed"
    code, out = run(["npx", "vite", "build"], cwd=os.path.join(ROOT, "web"), timeout=1200)
    if code != 0:
        return False, out.strip()[-1200:]

    dist = os.path.join(ROOT, "web", "dist")
    index_html = os.path.join(dist, "index.html")
    if not os.path.isfile(index_html):
        return False, "build reported success but web/dist/index.html is missing"

    # Report the chunk index.html actually loads. The build code-splits lazy
    # views and emits more than one index-*.js, and the others are not the
    # entry point — measuring the wrong one produced a meaningless number.
    with open(index_html, encoding="utf-8") as fh:
        entry = re.search(r'assets/([A-Za-z0-9_.-]+\.js)', fh.read())
    if not entry:
        return False, "no entry chunk referenced from web/dist/index.html"
    name = entry.group(1)
    if not os.path.isfile(os.path.join(dist, "assets", name)):
        return False, f"entry chunk {name} missing from web/dist/assets"

    # Take the size from vite's own log line rather than recomputing it. Vite's
    # kB figure uses its own convention and gzip level; recomputing gives a
    # slightly different number that cannot be compared with the sizes recorded
    # by earlier phases. §7 asks for a comparable hash + size.
    line = next((l for l in out.splitlines() if f"assets/{name}" in l), "")
    m = re.search(r"([\d.]+)\s*kB\s*│\s*gzip:\s*([\d.]+)\s*kB", line)
    if m:
        size = f"{m.group(1)} kB / gzip {m.group(2)} kB"
    else:
        raw = os.path.getsize(os.path.join(dist, "assets", name))
        size = f"{raw/1024:.2f} kB (vite log line not parsed)"

    js_count = len([f for f in os.listdir(os.path.join(dist, "assets")) if f.endswith(".js")])
    return True, f"entry {name} {size} ({js_count} chunks total)"


# ---------------------------------------------------------------------------
# Gate 4 — i18n: regenerate, compare counts, and scan for missing keys
# ---------------------------------------------------------------------------
def _used_i18n_keys():
    """Every COMPLETE key literal passed to t() in web/src, plus the server allowlist.

    Also returns the dynamic prefixes — call sites like ``t('food_meal_' + m, m)``
    whose real key only exists at runtime. Those cannot be checked for exact
    equality, so the caller instead asserts that each prefix resolves to at
    least one catalogue entry. Ignoring them entirely would hide a renamed
    prefix; asserting the prefix is non-empty keeps the scan honest without
    producing false failures.
    """
    # Negative lookahead: a quote followed by `+` is a prefix, not a whole key.
    complete = re.compile(r"""\bt\(\s*['"]([a-zA-Z0-9_.]+)['"](?!\s*\+)""")
    dynamic = re.compile(r"""\bt\(\s*['"]([a-zA-Z0-9_.]+)['"]\s*\+""")

    keys, prefixes = set(), set()
    src = os.path.join(ROOT, "web", "src")
    for dirpath, _dirs, files in os.walk(src):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            with open(os.path.join(dirpath, fname), encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            keys.update(complete.findall(body))
            prefixes.update(dynamic.findall(body))

    # Keys the server is allowed to translate on behalf of the client.
    #
    # Parsed with ast, not regex. WEB_I18N_KEYS is a single ~4,260-entry list
    # spread over very long lines; a regex that stops at the first bracket
    # silently reads only the first couple of hundred entries and the gate
    # then passes without checking the rest. ast reads the real literal.
    api = os.path.join(ROOT, "api_server.py")
    with open(api, encoding="utf-8", errors="replace") as fh:
        tree = ast.parse(fh.read(), filename="api_server.py")
    allow: set[str] = set()
    for node in ast.walk(tree):
        targets = getattr(node, "targets", None)
        if not targets:
            continue
        if not any(getattr(t, "id", None) == "WEB_I18N_KEYS" for t in targets):
            continue
        value = node.value
        if isinstance(value, ast.Call):  # frozenset([...]) / set([...])
            value = value.args[0] if value.args else None
        if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            allow.update(
                e.value for e in value.elts
                if isinstance(e, ast.Constant) and isinstance(e.value, str)
            )
    return keys, prefixes, allow


def gate_i18n():
    code, out = run([sys.executable, os.path.join("scripts", "export_i18n.py")])
    if code != 0:
        return False, out.strip()[-600:]

    counts = {}
    catalogues = {}
    for rel in I18N_TARGETS:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            data = json.load(fh)
        catalogues[rel] = data
        counts[rel] = {lang: len(m) for lang, m in data.items()}

    distinct = {json.dumps(v, sort_keys=True) for v in counts.values()}
    if len(distinct) != 1:
        return False, f"i18n targets disagree: {counts}"
    counts_only = list(counts.values())[0]
    if len(set(counts_only.values())) != 1:
        return False, f"id/en key counts differ within a target: {counts_only}"

    used, prefixes, allow = _used_i18n_keys()

    # Guard the extractor: WEB_I18N_KEYS holds several hundred entries, so an
    # empty result means the regex stopped matching the declaration — which
    # would make the allowlist half of this gate pass without checking anything.
    if len(allow) < 1000:
        return False, (f"only {len(allow)} key(s) parsed out of WEB_I18N_KEYS (expected ~4,200); "
                       f"extraction regex no longer matches its declaration in api_server.py")

    ref = catalogues[I18N_TARGETS[0]]
    problems = []
    for lang, mapping in ref.items():
        miss_ui = sorted(used - set(mapping))
        miss_srv = sorted(allow - set(mapping))
        if miss_ui:
            problems.append(f"{lang}: {len(miss_ui)} key(s) used by web/src but absent "
                            f"(e.g. {miss_ui[:5]})")
        if miss_srv:
            problems.append(f"{lang}: {len(miss_srv)} key(s) in WEB_I18N_KEYS but absent "
                            f"(e.g. {miss_srv[:5]})")
        dead = sorted(p for p in prefixes if not any(k.startswith(p) for k in mapping))
        if dead:
            problems.append(f"{lang}: {len(dead)} dynamic key prefix(es) resolve to nothing "
                            f"(e.g. {dead[:5]})")
    if problems:
        return False, " | ".join(problems)

    return True, (f"{counts_only} across {len(I18N_TARGETS)} targets; {len(used)} keys used "
                  f"by web/src + {len(prefixes)} dynamic prefixes + {len(allow)} allowlisted, "
                  f"0 missing")


# ---------------------------------------------------------------------------
# Gates 5-8 — the test suite
# ---------------------------------------------------------------------------
def _unittest(module):
    code, out = run([sys.executable, "-m", "unittest", module, "-v"], timeout=900)
    tail = "\n".join(l for l in out.splitlines()
                     if l.startswith(("Ran ", "OK", "FAILED", "ERROR:", "FAIL:")))
    return code, (tail or out.strip()[-600:])


def gate_database():
    code, out = _unittest("tests.test_database_schema")
    return (code == 0), out


def gate_database_legacy():
    code, out = _unittest("tests.test_database_legacy")
    return (code == 0), out


def gate_api():
    code, out = _unittest("tests.test_api_contract")
    return (code == 0), out


def gate_api_routes():
    """Probes every route the web client calls against the live server."""
    code, out = _unittest("tests.test_api_routes")
    surface = next((l.strip() for l in out.splitlines() if "route surface" in l), "")
    tail = "\n".join(l for l in out.splitlines() if l.startswith(("Ran ", "OK", "FAILED")))
    return (code == 0), " · ".join(x for x in (tail, surface) if x)


def gate_sync():
    code, out = _unittest("tests.test_sync_engine")
    if code != 0:
        return False, out
    code2, out2 = _unittest("tests.test_sync_conflict")
    return (code2 == 0), out + " | " + out2


def gate_frontend():
    if not have("npm"):
        return None, "npm not installed"
    code, out = run(["npm", "run", "test"], timeout=900)
    tail = "\n".join(l.strip() for l in out.splitlines()
                     if "Test Files" in l or "Tests " in l or "FAIL" in l)
    return (code == 0), (tail or out.strip()[-600:])


def gate_regression():
    """Re-run everything, as §7 requires for earlier phases."""
    code, out = run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                    timeout=1800)
    tail = "\n".join(l for l in out.splitlines() if l.startswith(("Ran ", "OK", "FAILED")))
    return (code == 0), (tail or out.strip()[-600:])


# ---------------------------------------------------------------------------
# Gate 9 — live smoke: /api/health, /api/version, version matches APP_VERSION
# ---------------------------------------------------------------------------
SMOKE_SCRIPT = r"""
import json, os, socket, sys, tempfile, urllib.request
sys.path.insert(0, os.environ["CRAFTLIFE_ROOT"])
os.chdir(tempfile.mkdtemp(prefix="craftlife-smoke-"))
sys.path.insert(0, os.path.join(os.environ["CRAFTLIFE_ROOT"], "tests"))
from harness import TempDatabase
import importlib

ctx = TempDatabase()
ctx.__enter__()
ctx.db.init_db()
uid = ctx.make_user("smokeuser")
api = importlib.import_module("api_server")
api.db.DB_PATH = ctx.db_path
api._state.update({"user_id": None, "token": None, "username": None})
api._ensure_user()

s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
httpd, base = api.start_server("127.0.0.1", port)
try:
    health = json.load(urllib.request.urlopen(base + "/api/health", timeout=15))
    version = json.load(urllib.request.urlopen(base + "/api/version", timeout=15))
finally:
    httpd.shutdown(); httpd.server_close()
    ctx.__exit__(None, None, None)

if not health.get("ok"):
    print("FAIL /api/health ->", health); sys.exit(1)
if not version.get("ok"):
    print("FAIL /api/version ->", version); sys.exit(1)
print(json.dumps({"health_ok": health.get("ok"), "version": version.get("version")}))
"""


def gate_smoke():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_updater_ver", os.path.join(ROOT, "updater.py"))
    with open(os.path.join(ROOT, "updater.py"), encoding="utf-8") as fh:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', fh.read())
    app_version = m.group(1) if m else None

    env = dict(os.environ, CRAFTLIFE_ROOT=ROOT)
    proc = subprocess.run([sys.executable, "-c", SMOKE_SCRIPT],
                          capture_output=True, text=True, env=env, timeout=300)
    if proc.returncode != 0:
        return False, (proc.stdout + proc.stderr).strip()[-800:]
    try:
        result = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return False, f"unreadable smoke output: {proc.stdout.strip()[-400:]}"
    if result.get("version") != app_version:
        return False, (f"/api/version says {result.get('version')} but updater.py "
                       f"APP_VERSION is {app_version}")
    return True, f"/api/health ok, /api/version={result['version']} == APP_VERSION"


# ---------------------------------------------------------------------------
# Gate 10 — cleanup: integrity_check, no test rows, users.currency sane
# ---------------------------------------------------------------------------
CLEANUP_SCRIPT = r"""
import os, sys, tempfile
sys.path.insert(0, os.environ["CRAFTLIFE_ROOT"])
os.chdir(tempfile.mkdtemp(prefix="craftlife-cleanup-"))
from tests.harness import TempDatabase

ctx = TempDatabase()
ctx.__enter__()
try:
    ctx.db.init_db()
    uid = ctx.make_user("cleanup_probe")
    ctx.db.add_habit(uid, "cleanup probe habit")
    integrity = ctx.integrity_check()
    violations = ctx.foreign_key_violations()
    conn = ctx.raw()
    try:
        currency = conn.execute(
            "SELECT currency FROM users WHERE id=?", (uid,)).fetchone()[0]
        # No row from a previous run may leak into a fresh database.
        leftovers = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username LIKE 'tester%'"
        ).fetchone()[0]
    finally:
        conn.close()
finally:
    ctx.__exit__(None, None, None)

problems = []
if integrity != "ok":
    problems.append(f"integrity_check={integrity}")
if violations:
    problems.append(f"{len(violations)} foreign key violation(s)")
if currency != "IDR":
    problems.append(f"users.currency default is {currency!r}, expected 'IDR'")
if leftovers:
    problems.append(f"{leftovers} leftover test row(s)")
if problems:
    print("FAIL " + "; ".join(problems)); sys.exit(1)
print("integrity ok, 0 FK violations, currency=IDR, 0 leftover test rows")
"""


def gate_cleanup():
    env = dict(os.environ, CRAFTLIFE_ROOT=ROOT)
    proc = subprocess.run([sys.executable, "-c", CLEANUP_SCRIPT],
                          capture_output=True, text=True, env=env, timeout=300)
    # database.py logs progress to stdout/stderr; the verdict is the last line
    # this script itself prints, so read stdout only and ignore the noise.
    lines = [l for l in proc.stdout.strip().splitlines() if l.strip()]
    last = lines[-1] if lines else "(no output)"
    if proc.returncode != 0 and not last.startswith("FAIL"):
        last = (proc.stderr.strip().splitlines() or [last])[-1]
    return (proc.returncode == 0), last


# ---------------------------------------------------------------------------
# Gate 11 — version anchors identical (roadmap K22)
# ---------------------------------------------------------------------------
def gate_version_anchors():
    with open(os.path.join(ROOT, "updater.py"), encoding="utf-8") as fh:
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', fh.read())
    if not m:
        return False, "APP_VERSION not found in updater.py"
    anchors = {"updater.py APP_VERSION": m.group(1)}
    for rel, label in (("web/package.json", "web/package.json version"),
                       ("packages/craftlife-core/package.json", "@craftlife/core version")):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
            anchors[label] = json.load(fh)["version"]
    if len(set(anchors.values())) != 1:
        return False, f"anchors disagree: {anchors}"
    return True, f"all {len(anchors)} anchors = {m.group(1)}"


# ---------------------------------------------------------------------------
# Gate 12 — no secrets or user databases tracked (UPDATE_RULES.md §9)
# ---------------------------------------------------------------------------
def gate_no_secrets():
    code, out = run(["git", "ls-files"])
    if code != 0:
        return None, "not a git checkout"
    bad = [p for p in out.splitlines() if FORBIDDEN_TRACKED.search(p)]
    if bad:
        return False, f"forbidden files are tracked: {bad}"
    return True, "no .env / craftlife.db* / logs/ tracked by git"


# ---------------------------------------------------------------------------
# Gate 13 — Supabase SQL actually executes and its pgTAP tests pass (M04)
# ---------------------------------------------------------------------------
def gate_supabase_sql():
    """Apply every migration and run every pgTAP test on a local PostgreSQL.

    Server-side SQL that has never been executed is not verified SQL, so the M04
    merge functions are proven against a real server instead of being reviewed by
    eye. The Supabase-only surface they depend on (auth.uid(), storage.*, the
    roles, the realtime publication) is reproduced by
    scripts/pg_harness/shim.sql, which is a test harness and is never applied to
    a real project.

    Reports SKIP — never PASS — when PostgreSQL is not installed, so the absence
    of a database cannot read as a green gate.
    """
    harness = os.path.join(ROOT, "scripts", "pg_harness", "run.py")
    if not os.path.exists(harness):
        return None, "pg harness missing"
    code, out = run([sys.executable, "scripts/pg_harness/run.py"], timeout=900)
    lines = [ln for ln in out.splitlines() if ln.strip()]
    if code == 3:
        return None, "PostgreSQL unavailable — " + (lines[-1] if lines else "no reason given")
    if code != 0:
        return False, " · ".join(lines[-4:]) or f"harness exited {code}"
    summary = [ln for ln in lines if ln.startswith(("migrations:", "pgTAP:"))]
    return True, " · ".join(summary) or (lines[-1] if lines else "ok")


def gate_design():
    """M06 — token desain satu sumber, dan DESIGN.md tidak boleh basi.

    ``--check`` melakukan tiga hal sekaligus: memastikan ``tokens.json`` identik
    dengan hasil ekstraksi ulang (jadi mengedit CSS atau db.THEMES tanpa
    regenerasi akan ketahuan), memastikan 12 tema masih lengkap, dan memastikan
    audit lintas-sumber bersih. Deviasi yang memang dibiarkan (utang kontras,
    --ct-t) dilaporkan sebagai warning dan tidak menggagalkan gate — yang
    menggagalkan adalah inkonsistensi, bukan cacat yang sudah diketahui.
    """
    doc = os.path.join(ROOT, "DESIGN.md")
    if not os.path.exists(doc):
        return False, "DESIGN.md tidak ada"
    code, out = run([sys.executable, "scripts/export_design_tokens.py", "--check"], timeout=180)
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
    if code != 0:
        return False, " · ".join(lines[-3:]) or f"exit {code}"
    summary = [ln for ln in lines if ln.startswith("CHECK OK")]
    return True, summary[0] if summary else (lines[-1] if lines else "ok")


def gate_types_mobile():
    """M07 — typecheck klien Android.

    Proyek Android sengaja hidup DI LUAR repo ini (lihat CraftLife-Android/
    README.md): toolchain, pipeline rilis, dan kadensnya berbeda, dan
    mencampurnya akan mengotori arsip rilis desktop. Jadi gate ini menyeberang
    ke folder saudaranya.

    Dibuat gate terpisah, bukan digabung ke `types`, karena dependency tree-nya
    sendiri. Kalau digabung, satu `npm install` yang belum dijalankan akan
    terlihat sebagai kegagalan typecheck web — dua masalah berbeda.

    SKIP (bukan PASS) kalau foldernya atau node_modules-nya belum ada, supaya
    ketiadaan dependency tidak terbaca hijau.
    """
    if not have("npm"):
        return None, "npm not installed"
    android = os.path.join(os.path.dirname(ROOT), "CraftLife-Android")
    if not os.path.isdir(android):
        return None, "CraftLife-Android/ belum ada (folder saudara repo ini)"
    if not os.path.exists(os.path.join(android, "node_modules")):
        return None, "CraftLife-Android dependencies belum terpasang"
    code, out = run(["npx", "tsc", "--noEmit"], cwd=android, timeout=600)
    if code != 0:
        return False, out.strip()[-1200:] or f"tsc exited {code}"
    return True, "CraftLife-Android tsc: 0 errors"


GATES = [
    ("python-syntax",   "§7 Python syntax — py_compile all entry modules", gate_python_syntax),
    ("types",           "§7 Types — tsc --noEmit (core + web)",            gate_types),
    ("build",           "§7 Build — vite build, record hash + size",       gate_build),
    ("i18n",            "§7 i18n — export, parity, 0 used keys missing",   gate_i18n),
    ("database",        "§7 Database — fresh-DB harness",                  gate_database),
    ("database-legacy", "§7 Database — legacy-DB harness",                 gate_database_legacy),
    ("api",             "§7 API — live server contract tests",             gate_api),
    ("api-routes",      "§7 API — every client route is dispatched",       gate_api_routes),
    ("sync",            "§7/§M04 — sync engine + conflict harness",        gate_sync),
    ("supabase-sql",    "§M04 — migrations + pgTAP on a local PostgreSQL",  gate_supabase_sql),
    ("frontend",        "§7 Frontend — vitest unit tests",                 gate_frontend),
    ("regression",      "§7 Regression — whole suite",                     gate_regression),
    ("smoke",           "§7 Live smoke — /api/health, /api/version",       gate_smoke),
    ("cleanup",         "§7 Cleanup — integrity, no test rows, currency",  gate_cleanup),
    ("version-anchors", "K22 — APP_VERSION == package.json versions",      gate_version_anchors),
    ("design",          "§M06 — token JSON sinkron + DESIGN.md ada",       gate_design),
    ("types-mobile",    "§M07 — tsc --noEmit di CraftLife-Android/",       gate_types_mobile),
    ("no-secrets",      "§9 — .env / *.db / logs never tracked",           gate_no_secrets),
]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run the CraftLife §7 verification gates.")
    ap.add_argument("--only", help="comma-separated gate names")
    ap.add_argument("--skip", help="comma-separated gate names to omit")
    ap.add_argument("--list", action="store_true", help="list gates and exit")
    args = ap.parse_args(argv)

    if args.list:
        for name, desc, _ in GATES:
            print(f"{name:16} {desc}")
        return 0

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    skip = {s.strip() for s in args.skip.split(",")} if args.skip else set()

    results = []
    for name, desc, fn in GATES:
        if only and name not in only:
            continue
        if name in skip:
            continue
        print(f"\n=== {name} — {desc}", flush=True)
        try:
            ok, detail = fn()
        except subprocess.TimeoutExpired:
            ok, detail = False, "TIMEOUT"
        except Exception as exc:  # a gate must never take the runner down
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append((name, ok, detail))
        mark = {True: "PASS", False: "FAIL", None: "SKIP"}[ok]
        print(f"    [{mark}] {detail}", flush=True)

    width = max(len(n) for n, _, _ in results) if results else 10
    print("\n" + "=" * 78)
    print("CRAFTLIFE §7 GATE SUMMARY".ljust(78))
    print("=" * 78)
    for name, ok, detail in results:
        mark = {True: "PASS", False: "FAIL", None: "SKIP"}[ok]
        print(f"  {mark:4}  {name.ljust(width)}  {detail[:78 - width - 9]}")
    failed = [n for n, ok, _ in results if ok is False]
    skipped = [n for n, ok, _ in results if ok is None]
    print("-" * 78)
    print(f"  {len(results) - len(failed) - len(skipped)} passed, "
          f"{len(failed)} failed, {len(skipped)} skipped")
    if failed:
        print(f"  FAILED: {', '.join(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
