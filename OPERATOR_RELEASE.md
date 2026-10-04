# Operator: publishing the CraftLife v1.7.4 release ("Spin & Spectrum")

Concrete steps to publish the release so **existing users auto-update**
(PyQt desktop + web UI). Prerequisites: the L10 finalize commit is in and
**both** version anchors are already bumped to `1.7.4`:

| Anchor | Location | Required value |
|--------|----------|----------------|
| Python | `updater.py` → `APP_VERSION` | `"1.7.4"` |
| npm | `web/package.json` → `version` | `"1.7.4"` |

If either anchor lags, bump it, rebuild, and re-tag before publishing.
Same-release revisions (rev-B, rev-C, …) keep version `1.7.4`: new commit,
**move** the tag, and revise (never duplicate) the README / release-notes
narrative.

## 0. Preconditions checklist

- [ ] Repo clean: `git status --porcelain` empty.
- [ ] `python -m py_compile database.py api_server.py updater.py food_data.py translations.py` → exit 0.
- [ ] `cd web && ./node_modules/.bin/tsc --noEmit` → 0 errors.
- [ ] `./node_modules/.bin/vite build` → clean; record main chunk hash + size.
- [ ] `python3 scripts/export_i18n.py` → key count recorded (4,613 at rev-C) and copied to `web/public/i18n/messages.json`.
- [ ] Live smoke on `CRAFTLIFE_API_PORT=8899` (`/api/version` must answer `1.7.4`).
- [ ] Publish access to `Hellowww-02/CraftLife` (GitHub Releases).

## 1. Windows build (`--onedir`)

```powershell
# from the repo root on the Windows build machine:
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

Required output: `dist/CraftLife/` containing **`CraftLife.exe`** + libs.
The official zip layout is: the **contents** of `dist/CraftLife/` at the
**zip root**. Do not use `--optimize 2` or `--strip` (the AI SDK crashes on
missing docstrings).

## 2. Zip the CONTENTS (not the folder)

From inside `dist/CraftLife/`, compress everything into:

```text
craftlife-1.7.4.zip
```

**NEVER include:** `.env`, `craftlife.db*` (`-wal`/`-shm`), `_update_state.json`,
`_update_apply.log`, `backups/`, `logs/`, `_update_staging/`.

Mandatory quick check (the updater aborts if the exe is missing):

```powershell
tar -tf craftlife-1.7.4.zip | Select-String -Pattern "^CraftLife.exe$|^dist/CraftLife/CraftLife.exe$"
```

## 3. Checksum

```powershell
(Get-FileHash craftlife-1.7.4.zip -Algorithm SHA256).Hash.ToLower()
```

Put the hash into the release body.

## 4. GitHub Release

1. **Target:** the default branch at the release commit (`v1.7.4` tag —
   at rev-C: `3121d6b`).
2. **Tag:** `v1.7.4` — exactly this. Forbidden variants: `v.1.7.4`, `1.7.4`.
3. **Title:** `CraftLife v1.7.4 — "Spin & Spectrum"`.
4. **Body:** the contents of `RELEASE_NOTES_v1.7.4.md` plus the SHA-256 line.
5. **Attach:** `craftlife-1.7.4.zip` (exactly one zip).
6. Mark as **Latest** and publish.

## 5. Post-publish verification

- [ ] `/releases/latest` redirects to the v1.7.4 asset page.
- [ ] An installed 1.7.2 client detects the update on launch, downloads,
      verifies SHA-256, applies on restart, and shows `/api/version` = `1.7.4`.
- [ ] Spot-check the new surfaces: pet Spin tab, Forge (anvil) tab, Crafting
      table, perimeter ambient LEDs + Settings → Visual Effects toggle.
- [ ] No `.env` or database inside the shipped zip (re-verify the listing).

## 6. Rollback

Delete the GitHub release + tag, restore the previous tag
(`v1.7.2` → `c244b78`), and republish the old asset. Local installs keep
their data — never ship anything that touches `craftlife.db`.

## 7. What v1.7.4 changed on disk (operator awareness)

**Overwritten (behavior-relevant):** `database.py` (PETS_DATA v2 + gacha +
training + skills + item rebalance), `api_server.py` (pet spin/skill/odds/
pokedex routes, redeem pet handler), `translations.py` + both
`messages.json` copies (4,613 keys), `updater.py` + `web/package.json`
(version 1.7.4), plus web views: `App.tsx`, `ShopView.tsx`, `CraftView.tsx`,
`PetsView.tsx`, `SettingsView.tsx`, `LeaderboardView.tsx`,
`AchievementsView.tsx`, `FriendsView.tsx`, `GuildView.tsx`,
`NotesView.tsx`, `LearningView.tsx`, `LoginView.tsx`,
`DashboardWidgetsDialog.tsx`, `SignatureKit.tsx`, `GameContext.tsx`,
`types.ts`, `charts.tsx`, `index.css`.

**New files:** `web/src/components/ui/AmbientLeds.tsx`,
`web/src/components/views/EnchantForge.tsx`,
`RELEASE_NOTES_v1.7.4.md`, `UPDATE_ROADMAP_L01_L10_v1.7.4.md`, this runbook.

**Removed:** `web/src/components/ui/LedStrip.tsx` (replaced by AmbientLeds).

**SQLite (auto, idempotent):** new table `pet_spin_state`; new column
`user_pets.skill_used_at`. No Supabase migration required for any v1.7.4
feature.
