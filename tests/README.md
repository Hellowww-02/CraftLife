# CraftLife test suite (M02)

Established by milestone **M02** to satisfy roadmap decision **K20**: *no refactor
starts until a test suite exists to catch the regressions a refactor causes.*
Before M02 this repository had **0** Python tests and **0** frontend tests.

## Running it

```bash
# Everything — the §7 gates and both suites, one command
python3 scripts/verify_gates.py

# Just the Python suite
python3 -m unittest discover -s tests -t .

# One module, verbose
python3 -m unittest tests.test_sync_engine -v

# Frontend unit tests (both workspaces: @craftlife/core and web)
npm install && npm run test

# All three npm test scripts
npm run test:py      # Python
npm run test         # vitest, core then web
npm run test:all     # both
```

`scripts/verify_gates.py --list` prints every gate; `--only` and `--skip` take
comma-separated gate names.

## Python suite

Standard-library `unittest` only. No third-party test dependency was added
(UPDATE_RULES.md §8 — avoid unnecessary dependencies).

| Module | Tests | What it pins down |
|---|---|---|
| `test_database_schema.py` | 19 | `init_db()` on a fresh database: table set, indexes, `integrity_check`, FK violations, seed data, idempotency — plus `ForeignKeyEnforcementTest`, which pins that `PRAGMA foreign_keys` is actually ON for the pooled connection and that `ON DELETE CASCADE` runs |
| `test_database_legacy.py` | 16 (4 skip) | Migration of an **old** database to the current schema, with rows preserved |
| `test_m03_sync_schema.py` | 27 | M03 row-level sync prerequisites: the four sync columns on all 41 synced tables (fresh **and** legacy), uuid unique/never NULL/trigger-filled, integer PKs untouched, and the guards that pin why G10 is deliberately still open |
| `test_m04_channel_a.py` | 20 | M04a append-only channel: the 7-table allowlist, append batch building, drain order, dedup on replay |
| `test_m04_channel_b.py` | 33 | M04b row-level merge (`merge_tracker_snapshots`, pure), the `updated_at` and tombstone triggers on all 41 tables, the tombstone/GC lifecycle, `recipe_items` ownership through its parent recipe, and that the server-acknowledged `rev` is recorded as the next `base_rev` |
| `test_m04c.py` | 23 | M04c sync status and the recoverable conflict surface: conflicts are recorded with both values, an empty field on the winner is *not* a conflict, one field can be restored without moving the rest of the row, and `_sync_out` no longer recurses |
| `test_sync_engine.py` | 17 | Sync queue: enqueue, dedup, ordering, backoff, retry, reset, scoping |
| `test_sync_conflict.py` | 7 | Two-device snapshot conflict; the M04 `xfail` was removed once both channels landed |
| `test_api_contract.py` | 11 | A live `api_server` on a real socket: auth, response shapes, route inventory, i18n |
| `test_api_routes.py` | 11 | Every `/api/...` path the web client calls is actually dispatched by the server |
| `test_i18n.py` | 9 | Bilingual catalogue integrity (P7) |
| `test_cloud_backup.py` | 24 | Cloud tracker backup: the snapshot must carry all 40 export tables (an incomplete one is rejected on restore), an admin must still get a backup even though a plain export refuses them, restore must make a local backup before overwriting, and a path from the request must be refused unless it is inside the caller's own folder |
| `test_data_maintenance.py` | 42 | The Data Maintenance feature, tested as the three promises its own UI makes: a backup file must really exist on disk, master data (habits/food/water/economy/notes) must survive, and history inside the retention window must survive. Plus every retention/schedule option the UI offers, and the auto-purge trigger pinned to its single caller |
| `test_m05d_store.py` | 19 | M05d storage boundary, pinned by AST: `cloud_api.py` must hold zero references to `database`. Plus the proof the layer is real rather than indirection - a second in-memory implementation serves the cloud handlers without SQLite and without editing the domain. Signature parity keeps the interface from going stale against `database.py` |
| `test_m05c_rules_guard.py` | 27 | M05c token bucket: burst, refill rate, per-key independence, bounded memory, and a 16-thread test that fails if the bucket over-admits. Plus the audit-log contract, pinned structurally: the schema has no column that could hold a request body |
| `test_m05c_api_guard.py` | 13 | The M05c wiring over a live socket: 429 + Retry-After, unauthenticated floods limited, `/api/health` exempt, `dbPath` hidden, `/api/admin/debug` gone in strict mode but still working on desktop, mutating requests audited, successful GETs not |
| `test_m05b_tenant_scoping.py` | 7 | M05b cross-tenant scoping on the READ path: every `user_id` table is seeded with a sentinel row for user B, then all 301 client GET routes are called as user A and scanned for it. Pins a coverage floor so the sweep cannot silently shrink, and prints the tables it could not seed |
| `test_m05b_write_scoping.py` | 8 | The same question on the WRITE path. Victim B is seeded first so `id=1` is B's row, then all 258 client POST routes are fired as user A and B's rows compared byte-for-byte afterwards. 232 answer 2xx, so the mutation paths really run. The four tables that do change are allowlisted with their justification (`friends` is reciprocal by design, pinned at `database.py:7086`), a companion test fails if the allowlist grows, and `test_accepting_someone_elses_friend_request_is_refused` proves the ownership filter directly |
| `test_m05a_rules_auth.py` | 35 | M05a JWT verification as attack vectors: alg-confusion, tampered payload, expiry/nbf/iss/aud, empty secret never verifies, error messages never leak the secret, and per-request identity via ContextVar |
| `test_m05a_api_auth.py` | 12 | The M05 acceptance criteria against a live socket: no/invalid/expired/unlinked JWT → 401, user A never sees user B's habits, `/api/health` stays public, and desktop behaviour is unchanged with strict off |
| `test_m05_postgres_store.py` | 27 | M05 work item 3 paid off: the Postgres backend for the storage layer, run against a real PostgreSQL 17 from the same harness the `supabase-sql` gate uses — no mocks, so broken SQL fails here. Covers all 22 operations, compares maintenance defaults and `restore_sync_conflict` codes against SQLite for parity, and pins the P1 requirement that Postgres stays optional (module imports without `pg8000`, `from_env()` returns None unconfigured, default store stays SQLite) |
| `test_m05_container.py` | 15 | M05 work item 1 without Docker, which is not installed here: every file in the Dockerfile `COPY` list exists and no local module the server imports is left behind, `requirements-server.txt` covers every module-level bare third-party import (AST-derived) and invents no packages, and — the part that matters — the entrypoint is copied to an empty directory and actually started, then probed in strict mode: `/api/health` public for the HEALTHCHECK, anonymous requests 401, a valid JWT served with the real `APP_VERSION`, and `dbPath` hidden |
| `test_m05_cloud_quota.py` | 33 | Egress and quota handling. Pins the four fixes: Channel A pulls incrementally via `since` instead of re-downloading all 7 append-only tables every 60 seconds, `_pull_personal` checks the revision before downloading the payload, 402/429 suspends sync so the app stops hitting a restricted project, and jobs with permanent errors die while network errors keep retrying (P6). Each fix was verified to fail when reverted. One of them found a real bug: the suspension window compared a SQLite UTC timestamp against Python local time, so outside UTC the suspension expired instantly and Fix 3 never engaged — pinned by a test that moves TZ to Asia/Jakarta |
| `test_m06_design_tokens.py` | 19 | M06 design contract. Runs the real exporter against `web/src/index.css` and `database.THEMES` (nothing mocked) and pins: `tokens.json` cannot drift from its sources, all 12 themes carry a full 16-field palette, every `var(--ct-*)` resolves or has a fallback, and the SignatureKit group cannot shrink. Contrast is **computed** from the real hex values, not assumed — which is how it found 5 themes below 4.5:1. Those 5 ratios are pinned as documented debt rather than silently "fixed", since changing a colour is a visual change and M06 is required to have none. Anti-vacuity proven three ways: tamper the JSON (2 fail), delete a theme (6 fail), rename a CSS class (3 fail) |
| `test_m07_android_sql.py` | 9 | Android SQL proven on a real SQLite engine. `expo-sqlite` is a native module, so without an emulator the only "test" would be reading the code. Instead this extracts the DDL and queries from `CraftLife-Android/src/db/schema.ts` and `sqliteStore.ts` and executes them verbatim under stdlib `sqlite3` — same engine, same `?` placeholders — so the SQL that ships is the SQL that is tested. Pins the outbox columns against desktop `sync_queue`, `next_retry_at` gating, and the `IS NULL` handling that `= NULL` would silently break. Anti-vacuity: breaking two queries gives 3 failures |
| **Total** | **484** | |

### The harness — `tests/harness.py`

`TempDatabase` is the context manager every Python test uses. It handles three
traps in this codebase that otherwise make tests silently test the wrong thing:

* `database.py get_db_path()` has **no** environment override, so `DB_PATH` is
  patched after import.
* `get_conn()` caches a pooled connection **per thread** in
  `_db_conn_local.conn`. Overriding `DB_PATH` alone leaves the old connection
  live; the harness closes and clears it.
* `database.py` writes `crash.log` / `db_error.log` relative to the working
  directory, so the harness `chdir`s into its temp dir to keep the repo clean.

`TempDatabase(seed_from=path)` copies an existing database file, which is how
the legacy tests work.

### The legacy harness — `tests/legacy_fixture.py`

UPDATE_RULES.md §6 requires schema changes to be verified against a legacy
database. §9 forbids committing user databases. So the fixture is
**reconstructed** rather than shipped — and it is reconstructed from the real
schema of the oldest `database.py` in this repository:

```
commit be3e2f6   (2026-05-12)
```

Using real history matters. A hand-invented "old" table can describe a state
that never existed, and then the test proves nothing. Two facts the real
history settled:

* `notes` **did not exist** in be3e2f6, so a genuine legacy database gets it
  created fresh with every current column.
* `users` had `party_id`, not `guild_id`, and `theme` defaulted to
  `'overworld'` rather than today's `'modern_dark'`.

To exercise a **real** archive instead:

```bash
CRAFTLIFE_LEGACY_DB=/path/to/an/old/craftlife.db \
  python3 -m unittest tests.test_database_legacy -v
```

Without that variable the real-archive tests **skip loudly** — the reason is
printed, so the gap is visible in CI output instead of looking green.
`LegacyHarnessSelfTest` asserts the skip is explicit and that the synthetic
harness never skips.

### The one expected failure

`test_sync_conflict.DesiredBehaviourTest` is marked `@unittest.expectedFailure`
on purpose. It encodes what M04 must deliver: concurrent edits on two devices
both surviving a sync. Today's whole-document last-writer-wins snapshot does not
provide that, so the test is expected to fail and CI stays green. When M04 lands
row-level merge it will report **"unexpected success"** — that is the signal to
delete the decorator and adopt the test as the real contract.

## Frontend suite

Vitest, `environment: "node"`. Every module under test is deliberately pure —
no React, no fetch, no clock reads — so no DOM environment is needed and no
jsdom/testing-library dependency is added.

`packages/craftlife-core`:

| File | Tests | What it pins down |
|---|---|---|
| `src/utils/__tests__/currency.test.ts` | 25 | Money rules (P2): symbols, IDR conversion, PyQt-parity formatting, dual-locale input parsing |
| `src/utils/__tests__/serverClock.test.ts` | 8 | `computeDateKey()` — which *day* it is for every daily reset |

`web`:

| File | Tests | What it pins down |
|---|---|---|
| `src/components/learning/__tests__/shellState.test.ts` | 30 | Layout clamping plus migration of three historical preference formats out of localStorage |
| `src/components/love/__tests__/cycleUtils.test.ts` | 53 | Cycle length, averages, prediction confidence, fertile window, form validation |
| **Total** | **116** | |

These modules were chosen first because they are pure and load-bearing.
`serverClock` decides when daily quests, streaks and shop restocks roll over;
`currency` is the single source of truth for money across desktop, web and
(from M07) Android; `cycleUtils` produces health information shown to the user,
where an off-by-one is not cosmetic; `shellState` migrates preferences that
already exist on users' machines. React components and `GameContext` still need
a DOM environment and are left to a later milestone alongside the component
work.

## CI

`.github/workflows/ci.yml` provisions Python 3.13 + Node 20, runs `npm ci`,
then calls `scripts/verify_gates.py`. The gates are implemented in Python
rather than in YAML so that CI and a developer's laptop cannot drift apart.

The workflow additionally fails if:

* `package-lock.json` is out of date (P8 — reproducible builds),
* the working tree is dirty after install,
* **any gate mutated a tracked file** — a verification step must not change the
  repository it is verifying.

Gates that cannot run in the current environment report `SKIP` with a reason.
They never report `PASS`, so a green run always means the check executed.

## Known gaps — recorded, not hidden

| Gap | Status |
|---|---|
| Real-archive legacy migration | Skipped in CI; needs `CRAFTLIFE_LEGACY_DB`. Synthetic be3e2f6 fixture covers the path. |
| `users.party_id` → `users.guild_id` | **No migration exists.** `boss_battles` got one (`database.py:1646`); `users` never did, and there is no `_safe_alter` for `guild_id`, while 11+ queries read `users.guild_id`. Pinned by `test_legacy_users_table_has_no_guild_id_column`. M03 did the schema work but deliberately left this one alone at the owner's instruction; it is still open. |
| `debt_notes` not synced (G10) | **Open on purpose.** Its M03 columns are installed, but adding it to `EXPORT_TABLES` was measured to break cloud sync: `_sanitize_cloud_personal_snapshot` demands the table set match `EXPORT_TABLES` exactly, so a pre-M03 cloud document is rejected with `incomplete cloud tracker snapshot: debt_notes` and restore-from-cloud dies for every existing user. The obvious workaround is worse — `import_tracker_data` clears local tracker tables first, so "missing table means empty" would silently delete every local debt note. Needs per-table preservation on import plus `cloud_schema` versioning, i.e. M04. Pinned by `CloudCompatibilityGuardTest`. |
| Personal snapshot size (G5) | **Made worse by M03, deliberately.** The four sync columns add ~111 bytes per row — measured +44.8% on a 5,000-row test snapshot. At the 200,000-row ceiling that projects to +21.2 MB against the 8 MB hard cap, so a heavy user could start failing sync before M04 replaces the whole-document snapshot with row-level deltas. |
| Unknown `/api/*` routes | Return the SPA HTML with status **200**, not a JSON 404 — the API server doubles as the static host. Pinned by `test_unknown_api_route_falls_through_to_the_spa` so it cannot change silently. |
| Desktop shell (`web_shell.py`) | Untestable here: PyQt6 is not installed in this environment. The `QWebEngineScript` token injection has not been exercised at runtime. |
| Cloud sync against live Supabase | Not covered — no credentials, and none should exist in CI. |
