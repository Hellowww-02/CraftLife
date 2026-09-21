# CraftLife — Update Rules

**Canonical operating procedure for every CraftLife update session.**
This document is the single source of truth for *how* changes are planned, executed, verified, reported and
released. It supersedes any ad-hoc instruction given earlier in a chat session.

| | |
|---|---|
| **Applies to** | CraftLife (`/home/user/CraftLife`) — desktop (PyQt6 + WebEngine), local API, React UI, SQLite, optional Supabase cloud |
| **Current version** | `v1.6.3` “Quality of Life+” (commit phase `A01–A14` + fix `A15`) |
| **Owner** | Project maintainer |
| **Status of this file** | Living document — update it whenever the process itself changes |

---

## 0. How to use this document

1. Start a new update session and point the assistant at this file first
   (`Read UPDATE_RULES.md and follow it for this session`).
2. State the request in plain language: area, symptom, expected behaviour, and any hard constraints
   (e.g. “only the left rail — do not touch the centre panel”).
3. The assistant answers in **Indonesian**, but every repository artifact it writes is **English** (§2).
4. Work continues until the requested scope is complete, verified and reported — not until “code is written”.
5. Copy-paste starter for a new session:

```text
Repo: /home/user/CraftLife   (CraftLife v1.6.3, commit phase A01–A14 + A15)
Read and follow UPDATE_RULES.md for this session.
Request: <what you want fixed or built>, <acceptance criteria>, <scope limits>.
Deliverable: complete the work, verify it, then report the Ten-Point Phase Report (§3) and the
in-chat delivery items 1–6 (§4) — concrete, not summaries.
```

---

## 1. Principles

| # | Principle | Meaning in practice |
|---|-----------|---------------------|
| P1 | **Local-first** | Everything works offline on SQLite; cloud (Supabase) stays optional and never becomes a hard dependency |
| P2 | **Single source of truth** | Game rules live in `database.py`; money formatting lives in `web/src/utils/currency.ts`; UI strings live in `translations.py`. Never create a second implementation |
| P3 | **Scope discipline** | Change exactly what was asked. Do not refactor, restyle or “improve” adjacent areas; if a neighbouring bug is found, report it and ask |
| P4 | **Zero regression** | Every feature that worked before must still work. Prefer additive changes (new columns, new endpoints, optional parameters) |
| P5 | **Evidence over adjectives** | “Fixed” is claimed only with command output, counts, hashes or test results |
| P6 | **Never lose user data** | Migrations are idempotent and non-destructive; updates must not overwrite `craftlife.db`, `.env` or user settings |
| P7 | **Bilingual by default** | Every user-facing string ships in **Indonesian and English** |
| P8 | **Reproducible releases** | One commit phase, one tag, documented operator steps, deterministic builds |

---

## 2. Working language

| Channel | Language |
|---------|----------|
| Chat with the maintainer | **Indonesian** |
| `README.md`, `RELEASE_NOTES_*.md`, `UPDATE_RULES.md`, code comments intended for the public, commit messages | **English** |
| Internal phase reports / roadmaps (`UPDATE_ROADMAP_*.md`, `20xx-xx-xx-Axx-*.md`, `*-PHASE-SUMMARY.md`) | May remain Indonesian; translate on request |

New public-facing text is written **in English first**; translations are not a later “nice to have”.

---

## 3. The Ten-Point Phase Report (mandatory)

Every phase — and every individual update inside a phase — must be able to answer all ten points.
Points 1–6 are also shown **verbatim in chat** (§4); points 7–10 are duties that must be *done*, not only listed.

| # | Item | Requirement |
|---|------|-------------|
| **1** | **New strings → `translations.py`** | Every new user-facing label, button, message, tooltip or error code gets a key with **both** `id` and `en` values. Then `python3 scripts/export_i18n.py` and copy to `web/public/i18n/messages.json`. Report the actual keys, not a count alone |
| **2** | **Files to overwrite** | Explicit list of every existing file that is modified, with a one-line reason each |
| **3** | **New files** | Explicit list of files created (code, migrations, documentation), with purpose |
| **4** | **New commands / endpoints / env vars** | New or changed API routes, new env vars, new scripts, and the exact command lines used to run/verify them |
| **5** | **Per-update conclusion** | What changed, which bug/request it closes, what the user sees differently. Written so a non-developer understands the benefit |
| **6** | **New Supabase migrations** | If none: state it explicitly. If any: file name, what it does, and that it is **optional** for local-only users. SQLite auto-migrations are always described here too |
| **7** | **One consolidated conclusion** | At the end of the whole commit phase: a single consolidated report of items 1–6 across all phases, in one place |
| **8** | **Update `updater.py` every phase** | Append a dated entry to the changelog header; bump `APP_VERSION` when the phase closes a release |
| **9** | **Update `README.md` every phase** | Keep the version narrative, status tables, feature lists, i18n counts and release history consistent with reality |
| **10** | **Write Release Notes** | A `RELEASE_NOTES_<version>.md` ready for a GitHub Release: highlights, per-area changes, migrations, operator steps, verification summary |

---

## 4. In-chat delivery format (Items 1–6, and 7 when a phase closes)

At **every** update — not only at the end of a phase — the chat reply contains these sections, with concrete
content (real keys, real file names, real commands, real numbers), in Indonesian:

```text
Format 1 — Key i18n baru          : table of key | id | en | where used
Format 2 — File yang ditimpa      : numbered list, one-line reason each
Format 3 — File baru              : numbered list, purpose each
Format 4 — Perintah / endpoint    : new routes, env vars, exact commands (including how to verify)
Format 5 — Kesimpulan             : what changed, what it fixes, what the user sees
Format 6 — Migrasi                : SQLite auto-apply (what columns/tables) · Supabase (file or "none")
Format 7 — (phase close only)     : consolidated items 1–6 across the whole commit phase
```

Rules for this section:

- The delivery is **in the chat**; a markdown file may accompany it but never replaces it.
- No condensed “see above” tables: the reader must be able to act on the chat message alone.
- Numbers must be the real measured ones (e.g. `tsc: 0 errors`, `4,325 keys`, `23/23 tests`, build hash + size).
- If something was **not** verified, say so explicitly. Silent optimism is a defect.

---

## 5. Versioning, commits and tags

| Topic | Rule |
|-------|------|
| Version scheme | `MAJOR.MINOR.PATCH`. A commit phase that combines several feature areas bumps **MINOR**; a follow-up fix inside the same release keeps the version and adds a new commit |
| Single commit phase | A multi-area effort (e.g. `A01–A14`) is delivered as **one commit** with a descriptive conventional message (`feat(release): …`, `fix(area): …`, `docs(readme): …`) |
| Tags | Annotated tag `vX.Y.Z` on the release commit. When a follow-up fix belongs to the same release, **move the tag** to the newest commit so `git checkout vX.Y.Z` contains the fix — and say so in the report |
| Commit identity | Use explicit `-c user.name="CraftLife Release" -c user.email="release@craftlife.local"` when the repo has no configured identity |
| Working tree | Every phase ends with a clean tree (`git status --porcelain` empty). Runtime artifacts (`craftlife.db*`, `logs/`, `_update_state.json`, `learning_audio/`) are never committed |
| Pushing | The workspace repo has no remote; the report states exactly which files the maintainer must upload and how |

---

## 6. Migration policy

**SQLite (always automatic).** Schema changes are added to `init_db()` using the idempotent `_safe_alter`
helper, so both **existing** and **brand-new** databases end up identical. Order matters: create tables
*before* creating indexes that reference them. After changing the schema:

1. Run the app (or the DB harness) against a **fresh** database → `init_db()` must complete.
2. Run it against a **copy of a legacy** database → new columns must appear, old rows preserved.
3. Run `init_db()` **twice** → no error (idempotence).

**Supabase (optional, cloud users only).** Each cloud-affecting phase ships a numbered
`supabase/migrations/<timestamp>_<phase>_<topic>.sql`. The report must state clearly that skipping it never
breaks the local app. Core migrations stay in their original order; never rename an applied migration.

---

## 7. Verification gates (all must pass before a phase is called done)

| Gate | Command / check | Pass criterion |
|------|-----------------|----------------|
| Python syntax | `python -m py_compile api_server.py database.py studio_api.py life_api.py learning_helper.py music_downloader.py translations.py updater.py` | exit 0 for all modules |
| Types | `npx tsc --noEmit` (in `web/`) | 0 errors |
| Build | `npx vite build` (in `web/`) | clean build; record asset hash + size |
| i18n sync | `python3 scripts/export_i18n.py` + copy to `web/public/i18n/messages.json`, then scan `web/src` for used keys | identical key counts in all sources; **0** used keys missing in `id` or `en` |
| Database | harness against fresh **and** legacy DB copies | schema correct, idempotent, data preserved |
| API | live server tests (`:8899`) with real payloads | correct response shapes, correct i18n error codes |
| Frontend | unit + SSR/DOM harness bundles | all green; no `{placeholder}` leaks; no duplicate components |
| Regression | re-run the harnesses of earlier phases (A11/A12/A13/A15 …) | unchanged or improved results |
| Live smoke | `/api/health`, `/api/version`, asset URLs | 200, version matches `APP_VERSION` |
| Cleanup | check test tables, `PRAGMA integrity_check`, `users.currency` | 0 test rows, `ok`, original settings restored |

A failing gate is fixed **before** reporting — never reported as “known issue” without the maintainer’s
explicit agreement.

---

## 8. Implementation rules (engineering)

1. **Partial updates must not clobber.** Endpoints that accept optional fields update only the fields
   actually sent (pattern: `None` = leave unchanged). A missing field must never wipe stored data.
2. **Idempotent side effects.** Anything that creates a record (reminders, promotions, sync entries) must be
   safe to trigger twice — reuse a stable reference (`source_ref`, cloud ids) instead of duplicating rows.
3. **Sanitise input, escape output.** Trim and clamp values server-side (length, range, whitelist); never
   trust the client. Icons/emoji are trimmed and capped; markup from user text is escaped by React.
4. **One formatter, one source.** Money through `formatMoney`; dates through the existing helpers; never
   introduce a parallel implementation in a component.
5. **CSS layering.** `ct-*` classes in `index.css` are declared **without** `@layer`, so they beat Tailwind
   utilities. Do not mix conflicting display/size utilities on the same element: add a modifier class
   (`.is-row`, `.is-sm`) instead of `!important`.
6. **Accessibility is part of “done”**: interactive elements need `title`/`aria-label`, active state needs
   `aria-current`, focus must stay visible.
7. **Performance guardrails**: no `backdrop-filter` over the animated scene (R10 anti-flicker), no idle paint
   animation, no extra API call when opening a page that already has the data.
8. **Comments explain “why”, not “what”** — especially the reason a fix exists (the bug it prevents).

---

## 9. Repository hygiene

- Never commit or release: `.env`, API keys, service-role keys, `craftlife.db*`, `logs/`, `backups/`,
  `learning_audio/`, `_update_staging/`, `_update_state.json`.
- `.gitignore` must stay ahead of runtime artifacts.
- Release archives contain **only** what an end user needs (see §10).
- Documentation is part of the deliverable: if behaviour changed, `README.md` changes in the same phase.

---

## 10. Release packaging & auto-update (lessons recorded after A15)

Current state and the rules that follow from it:

1. **Archive layout.** The release `.zip` must contain the **contents of `dist/CraftLife/`** at its root
   (`CraftLife.exe`, `_internal/`, `web/`). It must **not** contain `build/`, `.env`, `craftlife.db*`,
   `logs/`, `backups/`, `learning_audio/` or `_update_staging/`.
   *Why:* the shipped 1.6.x archives have `build/` + `dist/` at the root, so the updater cannot find
   `CraftLife.exe` and the automatic update silently copies the wrong folders.
2. **Updater robustness.** `_flatten_staging()` must recognise `dist/CraftLife/` (and legacy layouts); if
   `CraftLife.exe` is absent after staging, the updater must **abort with a clear error** instead of copying
   anything.
3. **Checksums.** Attach a `sha256` for the archive so the existing verification path actually runs.
4. **Tag naming.** Use `vX.Y.Z` (no stray dot, e.g. `v.1.6.3` is wrong).
5. **Post-update evidence.** Write `_update_apply.log` during the robocopy/batch step and re-read the running
   version afterwards, so success/failure is provable.
6. **Never ship the developer’s `.env`** — rotate any key that has ever been inside a public archive.

---

## 11. Handoff checklist (end of every session)

- [ ] Scope delivered exactly as requested (nothing more, nothing less)
- [ ] All ten points (§3) satisfied; items 1–6 delivered in chat (§4)
- [ ] Verification gates (§7) all green, with the real numbers quoted
- [ ] `translations.py` + both `messages.json` files updated and identical
- [ ] `updater.py` changelog entry added; `APP_VERSION` correct for the release
- [ ] `README.md` consistent with the shipped version; release history accurate
- [ ] `RELEASE_NOTES_<version>.md` written or updated
- [ ] Commit created (single phase commit), tag placed, working tree clean
- [ ] Maintainer instructions provided: which files to copy/upload, which commands to run, which migrations
      to apply, what to check afterwards

---

## Appendix A — Ringkasan bahasa Indonesia (untuk referensi cepat)

1. **Bahasa:** balasan untuk pemilik proyek memakai **Indonesia**; semua berkas publik di repo
   (README, Release Notes, RULES) memakai **bahasa Inggris**.
2. **Format 10 poin** wajib tiap pembaruan: (1) string baru → key di `translations.py`; (2) daftar file yang
   ditimpa; (3) daftar file baru; (4) perintah/endpoint/env baru; (5) kesimpulan tiap pembaruan;
   (6) migrasi Supabase (atau “tidak ada”); (7) satu kesimpulan gabungan di akhir commit phase;
   (8) `updater.py` selalu diperbarui tiap fase; (9) `README.md` selalu diperbarui tiap fase (“REVISI”);
   (10) tulis Release Notes untuk GitHub Release.
3. **Format 1–6 dibuktikan langsung di chat** (nyata: key asli, daftar file, perintah, angka hasil uji) —
   bukan ringkasan, bukan hanya file.
4. **Satu commit phase**, satu tag rilis; perbaikan susulan memindahkan tag ke commit terbaru.
5. **Verifikasi wajib lulus** sebelum menyatakan selesai: `py_compile`, `tsc`, `vite build`, sinkronisasi i18n,
   uji DB (baru + lama), uji API, harness FE, regresi fase sebelumnya, smoke live, dan pembersihan data uji.
6. **Migrasi SQLite otomatis** (idempoten, aman untuk DB lama); migrasi Supabase selalu **opsional**.
7. **Paket rilis**: isi `dist/CraftLife/` di root zip, tanpa `build/`, `.env`, dan database pengguna;
   sertakan checksum; tag memakai `vX.Y.Z`.
