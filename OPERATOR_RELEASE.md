# Operator: publishing the CraftLife v2.0.0 release ("Three Platforms, One Life")

**One release, one runbook.** This single document covers every deliverable of
v2.0.0: the **desktop** zip (auto-update channel), the **Android** Play Store
submission, and the **cloud** (Supabase) operations. Same-release revisions
(rev-B, rev-C, …) keep version `2.0.0`: new commit, **move** the tag, and
revise — never duplicate — this runbook and the release-notes narrative.

## 0. Version anchors

All anchors must read `2.0.0` before anything ships (K22):

| Anchor | Location | Required value |
|--------|----------|----------------|
| Python | `updater.py` → `APP_VERSION` | `"2.0.0"` |
| npm (web) | `web/package.json` → `version` | `"2.0.0"` |
| npm (core) | `packages/craftlife-core/package.json` → `version` | `"2.0.0"` |
| npm (mobile) | `CraftLife-Android/package.json` → `version` | `"2.0.0"` |
| Expo | `CraftLife-Android/app.json` → `expo.version` / `android.versionCode` | `"2.0.0"` / `200` |

Pinned by the `version-anchors` gate and `tests/version.test.ts`.

## 1. Preconditions (both platforms)

- [ ] Desktop repo clean at the release commit; tag `v2.0.0` placed on it.
- [ ] `python3 scripts/verify_gates.py` → 17 passed / 0 failed / 1 skipped.
- [ ] Android: `npx tsc --noEmit` → 0 errors; `npx vitest run` → all green.
- [ ] Supabase: migrations through `20261023030000_fix_spin_pet_loop_variable.sql`
      pushed (`npx supabase db push`), then `npx supabase db lint --linked` → `[]`.
- [ ] **Never** ship `.env`, `craftlife.db*`, `logs/`, or `backups/` in any
      archive (release §10.6 rule).

---

## 2. Part A — Desktop (Windows auto-update channel)

### A1. Build (`--onedir`)

```powershell
# from the repo root on the Windows build machine:
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

Required output: `dist/CraftLife/` containing **`CraftLife.exe`** + libs.
Do not use `--optimize 2` or `--strip` (the AI SDK crashes on missing
docstrings).

### A2. Zip the CONTENTS (not the folder)

From inside `dist/CraftLife/`, compress everything into `craftlife-2.0.0.zip`
— the archive root must contain `CraftLife.exe` directly (the updater
verifies this and aborts otherwise). **Never include:** `.env`,
`craftlife.db*` (`-wal`/`-shm`), `_update_state.json`, `_update_apply.log`,
`backups/`, `logs/`, `_update_staging/`.

Mandatory quick check:

```powershell
tar -tf craftlife-2.0.0.zip | Select-String -Pattern "^CraftLife.exe$|^dist/CraftLife/CraftLife.exe$"
```

### A3. Checksum

```powershell
(Get-FileHash craftlife-2.0.0.zip -Algorithm SHA256).Hash.ToLower()
```

Put the hash into the release body.

### A4. GitHub Release

1. **Target:** the default branch at the release commit (tag `v2.0.0`).
2. **Tag:** `v2.0.0` exactly. Forbidden variants: `v.2.0.0`, `2.0.0`.
3. **Title:** `CraftLife v2.0.0 — "Three Platforms, One Life"`.
4. **Body:** `RELEASE_NOTES_v2.0.0.md` plus the SHA-256 line.
5. **Attach:** `craftlife-2.0.0.zip` (exactly one zip).
6. Mark as **Latest** and publish.

### A5. Post-publish verification

- [ ] `/releases/latest` redirects to the v2.0.0 asset page.
- [ ] An installed 1.7.x client detects the update, downloads, verifies
      SHA-256, applies on restart, and shows `/api/version` = `2.0.0`.
- [ ] No `.env` or database inside the shipped zip.

### A6. Rollback (desktop)

Publish a hotfix `2.0.1` rather than re-tagging if users already updated.
Local installs keep their data — never ship anything that touches
`craftlife.db`.

---

## 3. Part B — Android (Play Store + public source)

### B1. Upload key (ONE TIME, before the first Play upload)

```powershell
cd D:\CL\CraftLife-Android\android
keytool -genkeypair -v -storetype PKCS12 -keystore craftlife-upload.keystore -alias craftlife-upload -keyalg RSA -keysize 2048 -validity 10000
copy keystore.properties.example keystore.properties  # then fill in real passwords
```

- Back up `craftlife-upload.keystore` + passwords in a password manager.
  Losing them means a Google upload-key reset request.
- **Never commit** `keystore.properties` or `*.keystore` (`.gitignore` guards
  this). Enroll in **Play App Signing** at first upload.

### B2. Release build (AAB)

```powershell
cd D:\CL\CraftLife-Android
npm install
cd android
.\gradlew.bat :app:bundleRelease
```

Output: `android\app\build\outputs\bundle\release\app-release.aab`.
The bundle must be signed with the **upload key** (Play rejects a
debug-signed bundle). `versionCode 200` must increase for every later upload.

### B3. Play Console submission

- Create the app (`app.craftlife.mobile`); upload the AAB to **Internal
  testing** first, promote after the physical-phone verification pass.
- **Data safety form:** use `PLAY_DATA_SAFETY_v2.0.0.md` (this repo) —
  every answer maps to what the code actually collects.
- Store listing assets: `assets/icon.png` (1024) is the source icon.

### B4. Publish the source

The Android project lives in its own repository:
**https://github.com/Hellowww-02/CraftLife-Android-Version**
— push the project there and attach `RELEASE_NOTES_v2.0.0.md` (the Android
copy, inside the project) to the GitHub Release for that repo.

### B5. Verify / Rollback (Android)

- [ ] Internal build installs on a physical phone; login, sync, spin, chat
      smoke pass.
- [ ] Halt the Play rollout on any blocker; ship a fixed build with a higher
      `versionCode`.

---

## 4. Part C — Cloud (Supabase)

- Apply migrations with `npx supabase db push` — never edit a shipped
  migration; fix forward with a new one (precedent: `20261023020000`,
  `20261023030000`).
- `npx supabase db lint --linked` must return `[]` after every push.
- Push notifications need `FCM_SERVICE_ACCOUNT` as an Edge Function secret
  (see `supabase/functions/send-push/`); without it, push is an honest no-op.

---

## 5. Release file map (operator awareness)

Desktop: version anchors (`updater.py`, three `package.json`), release docs
(`RELEASE_NOTES_v2.0.0.md`, this runbook, `PLAY_DATA_SAFETY_v2.0.0.md`), and
the M01–M14 phase history — see `git log` and
`UPDATE_ROADMAP_M01_M14_ANDROID_CLOUD_SYNC.md`.
Android: `package.json`, `app.json`, `assets/` (icon/adaptive/splash),
`android/app/build.gradle` (release signing), `android/keystore.properties.example`,
`src/features/menu.ts` (More hub parity). Full per-change lists live in the
chat reports; parity evidence in `VERIFIKASI_M12.md`, QA in `QA_M13.md`.
