# CraftLife

<div align="center">

**Offline-first desktop RPG for real life: habits, health, money, learning, and optional cloud social.**

Python + SQLite is the brain. React (Vite + Tailwind) is the skin, hosted in PyQt6 `QWebEngineView`. Supabase is optional.

![Release](https://img.shields.io/badge/release-v1.4.0-5a8a2e?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6_WebEngine-6.x-41CD52?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

UI language: **English** and **Indonesian** (Settings, no restart).

[Quick start](#quick-start) · [Architecture](#architecture) · [Features](#features) · [Cloud](#optional-cloud-supabase) · [Build & release](#windows-build-and-github-release) · [FAQ](#faq)

</div>

---

## What this release is

**CraftLife v1.4.0** is a Windows-first desktop app. You can use every local module with no internet and no cloud account.

| Area | Status |
|------|--------|
| Local SQLite tracker, RPG, notes, health, economy | Ready |
| Hybrid React UI in WebEngine (`web/dist` via `http://127.0.0.1:8765`) | Ready |
| Legacy PyQt widgets | Kept — set `CRAFTLIFE_WEB_UI=0` |
| Cloud Phases 1–4 + reward ledger / shop migrations **in this repo** | Source ready; **you** apply them on your Supabase project |
| Push notifications while the app is closed | Not in this release |
| Pixel-identical PyQt skins | Not a goal — **action parity** (same buttons / APIs as PyQt) |

Game rules stay in Python (`database.py`). TypeScript does not implement RPG math. The Google AI Studio zip on branch `Referention` is **UI reference only** — do not merge that branch into `main` for features.

---

## Architecture

```text
CraftLife.exe  (or python MainPyQt6.py)
  ├─ PyQt6 shell     login / tray / QWebEngineView
  ├─ api_server.py   http://127.0.0.1:8765  →  database.py (SQLite)
  │                    life_api.py  studio_api.py  cloud_api.py
  └─ web/dist        React UI (users never need Node)
```

```text
Developers
  py api_server.py          # API + (after npm run build) static UI
  cd web && npm run dev     # Vite :3000 for hot reload only
  py MainPyQt6.py           # after build, the window loads :8765, not Vite
```

| Mode | How |
|------|-----|
| Frozen exe | Serves `web/dist`. No Node on the user PC. |
| Source after `npm run build` | Same: port **8765**. |
| Source + Vite | Port **3000** for UI only; API must still run. |
| Legacy widgets | `CRAFTLIFE_WEB_UI=0` |
| Web login screen | `CRAFTLIFE_WEB_LOGIN=1` |

React never talks to Supabase directly. No service-role key, no `sb_secret_*` in the web bundle.

---

## Design principles

1. **Local first** — SQLite WAL is always available.
2. **Cloud optional** — missing `.env` does not disable local features; Settings still shows the cloud form with a clear “not configured” message.
3. **No fake success** — online social actions succeed only after the server confirms.
4. **Server authority** for Friends, Couple, online Guild, online PvP, attachments, and cloud reward claims (RPC + RLS).
5. **Private storage** — cloud buckets are never public.
6. **Conflicts are explicit** — personal snapshot clashes: keep local or restore cloud. Never silent overwrite.
7. **Safe retries** — idempotency keys / stable cloud IDs.
8. **Both languages** — new UI strings exist in Indonesian and English (`translations.py` + web i18n).

---

## Features

### Character and dashboard

Level, XP, HP, MP, Gold, gems, streaks, classes, talents, rebirth, titles, command palette (Ctrl+K), toasts, level-up modal.

### Habits, Dailies, Quests

Positive/negative habits, recurring dailies (fail, freeze), one-time quests, difficulty rewards, folders, templates (`morning_routine`, `morning_routine_d`, `project_launch_t`, …), duplicate, notes.

### Body

Sport log, complete, duplicate, templates, calories. Food database, meals, macros, water goal. Health logs (steps, sleep, weight, mood). Pomodoro sessions, give-up, test alarm.

### Economy and supplies

Income/expense, debts and installments, savings (add / withdraw), investments, subscriptions (renew), IOU notes, currency display. Supplies stock in/out/adjust.

### Studio

Learning notebooks, sources, Gemini chat (key stored in Python, not in React). Quiz, flashcards, FAQ, timeline, summary, mind map, study guide. Notes with folders, archive, duplicate, LaTeX preview via Python. Music library, playlists, yt-dlp search/download (local files only). Calendar, Indonesian holidays, day notes, year jump, reminders with sounds.

### RPG

Shop, inventory, equip, craft, enchant. Pets (adopt, feed, train, equip). Solo and guild bosses. Achievements and redeem codes. Admin debug panel only if `is_admin`.

### Social

Friends (request, accept/reject, remove, profile dialog). Couple request / respond / cancel / end. Love Space (check-in, memories, bucket, events, weekly review, cycle, photo meta). Guild create/join/leave, invite, kick, leadership transfer, description, chat, custom boss. PvP challenge / respond / claim. Notification center (navbar bell). Leaderboard.

### Settings and account

Local login, register, switch account, stay logged in. Password, lock, security question, backup codes. Cloud link, sync, conflict, devices, migrate local. Language, sound, high contrast, font scale, currency. Tracker SQLite export/import. Check for updates.

---

## System requirements

| | Minimum | Recommended |
|--|---------|-------------|
| OS | Windows 10 x64 | Windows 11 x64 |
| Python (source) | 3.10 | 3.11 / 3.12 |
| Node (developers only) | 20+ | 20+ |
| RAM | 4 GB | 8 GB+ |
| Disk | 500 MB | 2 GB+ (learning / music cache) |
| Display | 1080×700 | 1280×720+ |
| Internet | Optional | Required for cloud, Gemini, TTS, yt-dlp |

Linux/macOS may run from source; codecs, tray, and packaging differ. Windows is the supported release target.

CraftLife is **not** a medical device. Health and cycle tools are personal trackers only.

---

## Quick start

Cloud is not required.

```powershell
git clone https://github.com/Hellowww-02/CraftLife.git
cd CraftLife
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

First UI build (developers):

```powershell
cd web
npm install
npm run build
cd ..
python MainPyQt6.py
```

Do **not** run `npm audit fix --force` (it can jump Vite to an incompatible major).

Hot reload:

```powershell
python api_server.py
# other terminal
cd web
npm run dev
```

The frozen/production window must load **8765**, not Vite `:3000`, or you get `ERR_CONNECTION_REFUSED`.

---

## Optional AI (Learning)

Set a Gemini API key **inside the app** (Learning settings). Keys stay in SQLite / Python, never in the React bundle, and are excluded from personal cloud snapshots.

Never commit keys. Provider privacy policies apply to any text you send. Learning notebooks still work offline without Gemini.

---

## Optional cloud (Supabase)

There is no `SUPABASE_SETUP.md` in this tree; this section is the operator guide.

### Desktop `.env` (beside `MainPyQt6.py` or `CraftLife.exe`, never inside `_internal`)

```env
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=sb_publishable_...
CRAFTLIFE_CLOUD_ENABLED=true
CRAFTLIFE_SYNC_INTERVAL_SECONDS=60
```

**Never** put in the desktop `.env` or git:

```text
sb_secret_*
SUPABASE_SERVICE_ROLE_KEY
database password
CHAT_MAINTENANCE_SECRET
SMTP / CLI tokens
```

`.env` is gitignored.

### Auth

Email/password, **require verification**, set Site URL and redirect allowlist for your release domain (not leftover localhost if you ship an exe).

Passwords are not stored in SQLite. Refresh tokens use OS `keyring`.

### Apply migrations in this exact order

```text
20260812000000_initial_social_cloud.sql
20260812010000_fix_profiles_insert_policy.sql
20260813000000_social_realtime_pvp_guild.sql
20260813120000_personal_realtime_sync.sql
20260813180000_phase4a_love_space_shared.sql
20260813210000_phase4b1_chat_core.sql
20260813220000_phase4b2_b3_chat_attachments.sql
20260813230000_phase4c_guild_complete.sql
20260813235900_phase4d_e_final.sql
20260814000000_phase5a_reward_ledger.sql
20260818000000_phase5b_inventory_shop_craft.sql
20260821000000_phase4f_couple_profile_both.sql
20260821010000_app_updates.sql
```

Do not rename an applied migration. Staging first. Then Alice / Bob / Carol RLS tests (Carol must not read Alice–Bob chat, Love Space, guild internals, snapshots, or devices).

Reward ledger and shop/inventory SQL **exist in the repo**. They are live only after you apply them. Until then, wallet/inventory stay **local-authoritative**.

### Link in the app

Settings → Cloud & Sync → create account → verify email → Sign in & link → Migrate local data → Sync now. The cloud form is shown even if `.env` is missing.

---

## Source of truth

| Feature | Unlinked | Linked (after migrations) |
|---------|----------|---------------------------|
| Habits, dailies, quests, notes, health, economy, sport, reminders | SQLite | SQLite + `tracker_v1` personal snapshot |
| Profile | SQLite | Cloud profile + cache |
| Friends, Couple, Love Space, chat, PvP, Guild | Local fallback | Supabase RPC + RLS + cache |
| Shop / inventory / craft | SQLite | Cloud shop RPCs **if** 5a/5b applied |
| Music files, reminder sound paths | Local disk | Never uploaded |

`tracker_v1`: private document, ~36 tables, 8 MB cap, SHA-256, keep-local or restore-cloud.

---

## Project layout

```text
CraftLife/
├── MainPyQt6.py          Desktop shell (WebEngine + unused PyQt pages kept)
├── web_shell.py          QWebEngineView host
├── api_server.py         Local HTTP API
├── life_api.py           Sport, economy, notes, calendar, health, pomodoro
├── studio_api.py         Learning, music, love, guild, friends, notifications
├── cloud_api.py          Cloud HTTP surface for the UI
├── database.py           SQLite schema and game logic
├── translations.py       en / id
├── updater.py            APP_VERSION 1.4.0 — GitHub Releases or Supabase
├── cloud_config.py / cloud_service.py / sync_service.py
├── food_data.py  holidays.py  mathtools.py  learning_helper.py  music_downloader.py
├── CraftLife.spec        PyInstaller
├── scripts/build.ps1     Windows onedir (ASCII; PowerShell 5.1)
├── web/                  React 18 + Vite + Tailwind (no Node for end users)
└── supabase/migrations/  Apply on your project; do not skip files
```

Ignored: `.venv`, `web/node_modules`, `web/dist`, `.env`, `craftlife.db`, `logs/`, `dist/`, `build/`.

GitHub branches:

| Branch | Role |
|--------|------|
| `main` | Product |
| `New-Update` | Hybrid UI / API drops before merge to main |
| `Supabase-Update` | Cloud client files |
| `Utilities-Update` | Scripts, updater, spec |
| `Update-Road` | Docs |
| `Referention` | Design zip only — **do not merge for features** |

Do not upload nested `web/src` via GitHub’s “Add file” dialog; use `git push`.

---

## Data locations

| Mode | Database |
|------|----------|
| `python MainPyQt6.py` | `craftlife.db` next to sources |
| Frozen exe | `%APPDATA%\CraftLife\craftlife.db` |

`.env` stays **beside the exe**, not in `_internal`. Never ship a user’s database or `.env` in a GitHub Release zip.

Backup before updates. Export/import tracker from Settings uses SQLite (`export_tracker_data` / import), not React `localStorage`.

---

## Security

- Local passwords: PBKDF2-HMAC-SHA256, salt, lockout, backup codes, optional lock.
- Cloud: TLS, Auth, RLS, private buckets `profile-photos`, `love-space-photos`, `chat-attachments`.
- Direct Chat is **not E2EE**. Do not advertise it as such.
- Health, finance, cycle, and learning data are sensitive: trusted device, disk encryption, no public screenshots of keys.

---

## Windows build and GitHub Release

From repo root (PowerShell 5.1). `scripts/build.ps1` is ASCII-only.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

The script: `npm run build` → PyInstaller `CraftLife.spec` → copies `web/dist` next to the exe. Users run `dist\CraftLife\CraftLife.exe`. Fallback: `CRAFTLIFE_WEB_UI=0`.

Do **not** use PyInstaller `--optimize 2` or `--strip` (Gemini SDK can crash on missing docstrings). Do **not** run `copy_qtwebengine.py` unless you explicitly need it.

### Auto-updater zip — not the Code tab

`updater.py` reads **GitHub Releases** (`/releases/latest`) when `UPDATE_SOURCE` is `"github"`, or Supabase Storage `app-updates` when `"supabase"` (default in source).

1. Zip the **contents** of `dist\CraftLife\` as `craftlife-1.4.1.zip` (no `.env`, no `craftlife.db`).
2. Repo → **Releases** → Draft → tag `v1.4.1` (must be **newer** than `APP_VERSION` `1.4.0`) → attach the zip → publish.
3. Do not put the zip under `web/` or the git tree.

---

## Updating an install

1. Quit CraftLife.  
2. Backup `.env` and the database.  
3. Replace application files only.  
4. Never overwrite `%APPDATA%\CraftLife\craftlife.db`.  
5. Apply new SQL on staging, then production.

---

## Tests (smoke)

```powershell
python -m py_compile MainPyQt6.py database.py api_server.py life_api.py studio_api.py cloud_api.py web_shell.py updater.py
python -c "import database as db; db.init_db(); c=db.get_conn(); print(c.execute('pragma integrity_check').fetchone()[0])"
```

Expect `ok`. After UI changes, `cd web && npm run build` must produce `web/dist/index.html`.

---

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| `ERR_CONNECTION_REFUSED` on `:3000` | Build UI and use API **8765**; do not point WebEngine at Vite in production. |
| Blank “UI React belum di-build” | `cd web && npm install && npm run build`. |
| `build.ps1` parse errors (`P8`, `do`) | Use the ASCII `scripts/build.ps1` from this repo (no em-dash / smart quotes). |
| Cloud “not configured” | `.env` beside exe/source; restart. |
| `PGRST205` profiles | Migrations not applied. |
| `otp_expired` | Auth Site URL / allowlist; new verification mail. |
| `QtWebEngineProcess.exe` missing | `pip install PyQt6-WebEngine` and rebuild. |
| Database locked | One CraftLife process; do not write the DB from another tool. |
| Music silent | File exists, OS codec, output device, Mutagen. |

---

## Known limitations

- Chat is TLS + RLS, not E2EE.
- No push while the process is closed.
- Device UUID revoke ≠ global Auth session revoke.
- Attachment cleanup Edge Function must be scheduled by the operator.
- Very large trackers may hit the 8 MB snapshot cap.
- Linux/macOS packaging is unsupported in this release.

---

## Roadmap

**In this repository (code):** cloud phases 1–4, couple 4f, app_updates, reward ledger 5a, shop/inventory 5b.

**Still operator / later:** apply those migrations live; scheduled purge; closed-app push; malware scanning; full anti-cheat beyond server-scored productivity.

---

## Contributing

```bash
git clone https://github.com/Hellowww-02/CraftLife.git
git checkout -b feature/short-name
```

Keep RPG logic in Python. Do not restore zip `server.ts`. Do not commit secrets. Update **id** and **en** strings together. Prefer `New-Update` → `main` for hybrid UI; never feature-merge `Referention`.

---

## FAQ

**Need internet?** No, for local modules.  
**Need Supabase?** Only for multi-device sync and online social.  
**Publishable key in the exe?** Intended for clients; RLS is mandatory. Never service role.  
**Does a new exe wipe data?** Not if `%APPDATA%\CraftLife` is preserved.  
**Upload `web/` on github.com?** Nested folders fail in the upload UI — use `git push`. Same path = replace.

---

## License

[MIT](LICENSE) © 2026 CraftLife. Provided “AS IS”, without warranty.

Minecraft and other marks belong to their owners. CraftLife is independent and not affiliated with Mojang or Microsoft.

---

## Support

https://github.com/Hellowww-02/CraftLife/issues

Include OS, CraftLife version, source vs exe, local vs cloud, exact error. **Never** attach `.env`, `craftlife.db`, or keys.

---

<div align="center">

**Complete real quests. Keep your data. Level up your life.**

</div>
