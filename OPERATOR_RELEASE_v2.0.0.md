# Operator: publishing the CraftLife v2.0.0 release ("Three Platforms, One Life")

This runbook covers **both** deliverables of v2.0.0: the desktop zip
(auto-update channel, same as 1.7.x) and the first Android Play Store
submission. Version anchors must all read `2.0.0` before anything ships:

| Anchor | Location | Required value |
|--------|----------|----------------|
| Python | `updater.py` → `APP_VERSION` | `"2.0.0"` |
| npm (web) | `web/package.json` → `version` | `"2.0.0"` |
| npm (core) | `packages/craftlife-core/package.json` → `version` | `"2.0.0"` |
| npm (mobile) | `CraftLife-Android/package.json` → `version` | `"2.0.0"` |
| Expo | `CraftLife-Android/app.json` → `expo.version` / `android.versionCode` | `"2.0.0"` / `200` |

Anchored by the `version-anchors` gate and `tests/version.test.ts` (K22).

## 0. Preconditions checklist
- [ ] Desktop repo clean at the M14 commit; tag `v2.0.0` placed on it.
- [ ] `python3 scripts/verify_gates.py` → 17 passed / 0 failed / 1 skipped.
- [ ] Android: `npx tsc --noEmit` → 0; `npx vitest run` → all green.
- [ ] Supabase: all migrations through `20261023030000` pushed
      (`npx supabase db push`), then `npx supabase db lint --linked` → `[]`.
- [ ] `.env` files are NOT in any archive (release §10.6 rule).

## 1. Desktop build & publish (auto-update channel)
Follow `OPERATOR_RELEASE.md` §§1–6 unchanged (PyInstaller `--onedir`,
zip the CONTENTS of `dist/CraftLife/`, sha256 checksum, GitHub Release
tagged `v2.0.0`, `RELEASE_NOTES_v2.0.0.md` as the release body). Verify
afterwards: a 1.7.4 install offers 2.0.0, downloads, and `_update_apply.log`
proves the swap; `/api/version` answers `2.0.0`.

## 2. Android upload key (ONE TIME, before first Play upload)
```powershell
cd D:\CL\CraftLife-Android\android
keytool -genkeypair -v -storetype PKCS12 -keystore craftlife-upload.keystore -alias craftlife-upload -keyalg RSA -keysize 2048 -validity 10000
copy keystore.properties.example keystore.properties  # then fill in real passwords
```
- Back up `craftlife-upload.keystore` + passwords in a password manager.
  Losing them means a Google upload-key reset request.
- **Never commit** `keystore.properties` or `*.keystore` (see `.gitignore`).
- Enroll in **Play App Signing** at first upload (recommended default).

## 3. Android release build (AAB)
```powershell
cd D:\CL\CraftLife-Android
npm install
cd android
.\gradlew.bat :app:bundleRelease
```
Output: `android\app\build\outputs\bundle\release\app-release.aab`.
Sanity checks before uploading:
```powershell
.\gradlew.bat :app:assembleRelease   # optional installable check build
```
- Confirm the AAB is signed with the upload key (not debug):
  Play Console will reject a debug-signed bundle outright.
- `versionCode 200` must increase for every subsequent upload.

## 4. Play Console submission
- Create the app (`app.craftlife.mobile`), upload the AAB to **Internal
  testing** first; promote after the physical-phone verification pass.
- **Data safety form:** use `PLAY_DATA_SAFETY_v2.0.0.md` (this repo) —
  it maps every collected data type to what the code actually does.
- Content rating, target audience, privacy policy URL: operator supplies.
- Store listing assets: `assets/icon.png` (1024) is the source icon;
  screenshots come from the physical-phone pass.

## 5. Verify (post-publish)
- [ ] Desktop 1.7.4 → auto-update → 2.0.0, data intact.
- [ ] Play internal build installs on a physical phone; login, sync,
      spin, chat smoke pass (consolidated M12+M13 device checklist).
- [ ] Supabase dashboard: no new RPC errors after real spin/sync traffic.

## 6. Rollback
- Desktop: re-point the GitHub Release to the previous tag; the updater
  only moves forward on version compare, so publish `2.0.1` hotfix rather
  than re-tagging if users already updated.
- Android: halt the Play rollout; ship a fixed build with a higher
  `versionCode`.
- Cloud: migrations are additive/replace-only; never edit a shipped
  migration — fix forward with a new one (precedent: `20261023020000`,
  `20261023030000`).

## Changed-file summary for this release
Desktop repo: see the M14 commit (version anchors, release docs).
Android (copied by hand to `D:\CL`): `package.json`, `app.json`,
`assets/icon.png`, `assets/adaptive-icon.png`, `assets/splash-icon.png`,
`android/app/build.gradle`, `android/keystore.properties.example`,
`.gitignore`. Full per-phase lists live in the chat reports + git log.
