# REKAP COMMIT PHASE P47–P63 — RILIS v1.6.0 "Quality of Life"

**Tanggal:** 2026-09-11 · **Cakupan:** P47–P63 (17 perbaikan user, 3 di antaranya fatal) · **Versi:** 1.5.0 → **1.6.0**

Sumber otoritatif: `UPDATE_ROADMAP_P47_P63.md` · Log per fase: `UPDATES/2026-09-09-P47-*.md` s.d. `2026-09-11-P62-*.md`.

---

## 1. Translate keys (`translations.py`)

**3.694 → 3.757 key (+63)** — semua id+en, diekspor via `scripts/export_i18n.py` ke `web/src/i18n/messages.json` + `web/public/i18n/messages.json`, dan terdaftar di `WEB_I18N_KEYS` (api_server). Tambahan terbesar: P54 lampiran catatan, P58 lirik (10), P62 maintenance (15).

## 2. File yang dioverwrite (salin seluruhnya ke laptop — 39 file)

**Backend (10):** `MainPyQt6.py` (P57 stop-audio saat logout; CRLF), `api_server.py` (serve attachment/icon, upload targets, +63 key, auto-purge thread), `database.py` (5 migrasi SQLite + semua fungsi baru; CRLF), `life_api.py` (attachment), `mathtools.py` (P55 LaTeX), `studio_api.py` (redeem/chat/count/lyrics/couple/cleanup), `sync_service.py` (P61 pull_social_now), `translations.py`, `updater.py` (**APP_VERSION 1.6.0**), `web_shell.py` (P57 closeEvent stop-audio).

**Frontend (27):** `web/package.json` (version 1.6.0) · `web/src/App.tsx` (MusicPlayerProvider + music h-full) · `web/src/api/client.ts` · `web/src/api/life.ts` · `web/src/api/studio.ts` · `web/src/components/MoneyInput.tsx` · `web/src/components/Navbar.tsx` (MiniPlayer) · `web/src/components/TaskFolderBar.tsx` (edit folder) · `web/src/components/charts.tsx` (height trend) · views: `FriendsView, GuildView, HealthFoodView, LearningView, LoveSpaceView, MusicView, NotesView, NutritionView, PomodoroView, ProfileView, SettingsView, ShopView, SportView` · `web/src/context/GameContext.tsx` · `web/src/i18n/messages.json` + `web/public/i18n/messages.json` · `web/src/types.ts`.

**Dokumentasi (2):** `README.md` (badge v1.6.0, What's New 17 item, i18n 3.757) · `UPDATES/*` (16 log fase + dokumen ini).

## 3. File baru (8)

| File | Fase | Isi |
|---|---|---|
| `web/src/components/NumberInput.tsx` | P49 | Input angka dengan state kosong (backspace mulus) |
| `web/src/components/notes/NoteAttachments.tsx` | P54 | UI lampiran catatan (upload/paste/drag, preview, hapus) |
| `web/src/data/mathSymbols.ts` | P55 | Palet simbol matematika 7 kategori (MATH_PALETTE) |
| `web/src/components/FolderIconPicker.tsx` | P56 | Grid pemilih ikon folder (68 emoji + reset) |
| `web/src/music/MusicPlayerContext.tsx` | P57 | **Music engine global** — state + satu `<audio>` di App root + `window.craftlifeStopAllAudio` |
| `web/src/components/MiniPlayer.tsx` | P57 | Chip player di Navbar (judul + play/pause/next + shuffle/repeat) |
| `web/src/components/music/LyricsDrawer.tsx` | P58 | Drawer lirik: badge sumber, offset ±0.5s, import, simpan/hapus |
| `web/src/components/music/PlaylistIconDialog.tsx` | P59 | Dialog icon playlist (emoji grid / foto komputer) |

(+ `UPDATE_ROADMAP_P47_P63.md` dan `UPDATES/` sebagai dokumentasi.)

## 4. Perintah baru

Tidak ada perintah runtime baru. Build rilis tetap: `scripts\build.ps1` (sudah menjalankan `export_i18n.py` + `npm run build` + PyInstaller).

## 5. Kesimpulan per fase

| Fase | Item | Hasil |
|---|---|---|
| P47 | #15 redeem (fatal) | Seed order fixed; `redeem_code_redemptions` per-user; admin code + password bekerja |
| P48 | #4 chat dobel (fatal) | `addNotebookChat` murni lokal; 1 request = 1 jawaban |
| P49 | #11 input nominal | `NumberInput` di semua input angka |
| P50 | #13 tema | Tema persist via server (`user_themes`) |
| P51 | #14 warna avatar | `users.avatar_color` dipakai di chip profil/navbar + sistem admin ikut dibenahi |
| P52 | #12 tren tinggi | Kolom `health_logs.height_cm`; chart 7 hari real |
| P53 | #10 duplikat note | Same folder + sort_order, tanpa "(copy)" |
| P54 | #1 lampiran note | ≤5 MB, whitelist, file lokal `craftlife_attachments/<uid>/`, cascade delete |
| P55 | #2 LaTeX | 21 konversi + palet Σ + preview live |
| P56 | #3 ikon folder + tambahan | Dialog edit nama+ikon; **fix jumlah soal quiz/flashcards** (counter dihormati); soal essay + skor; **resize panel Learning drag kursor** (revisi); slider mobile dipertahankan |
| P57 | #5 + #17 musik | Player global + MiniPlayer; stop-audio saat logout & close (web + PyQt) |
| P58 | #6 lirik | Skor durasi vs live/remix; live per detik + offset; import .lrc/.txt; simpan per track (`song_lyrics`) |
| P59 | #7 icon playlist + tambahan | Emoji/foto (resize 512px, tabel `playlist_icons`); **indikator shuffle/repeat ON/OFF** |
| P60 | #8 layout musik | Satu scroll utama, deck selalu terlihat, fit page |
| P61 | #9 couple (fatal) | Fix crash 500 closure `lang`; mirror cloud→lokal via `pull_social_now`; push couple→cloud; badge status + kartu pasangan |
| P62 | #16 pembersihan DB | `maintenance_state` retensi 30 hari; dry-run; backup dulu; VACUUM; auto bulanan background |
| P63 | finalisasi | Versi 1.6.0 (updater + package.json), README, dokumen ini, verifikasi penuh |

## 6. Migrasi

**SQLite (auto saat aplikasi dibuka — tidak perlu manual):**
- `redeem_code_redemptions` (P47) · `health_logs.height_cm` + `user_health_goals.height_cm` (P52) · `note_attachments` (P54) · `song_lyrics` (P58) · `playlists.icon` + `playlist_icons` (P59) · `maintenance_state` (P62)

**Supabase: TIDAK ADA** — semua perbaikan lokal; couple memakai skema cloud 4f yang sudah ada.

## 7. Verifikasi rilis (P63, dijalankan ulang menyeluruh)

- `py_compile` seluruh modul inti ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean ✅
- Konsistensi i18n: `translations.py` ↔ `WEB_I18N_KEYS` ↔ `messages.json` = **3.757 key** (id+en) ✅
- Smoke live: register → bootstrap → redeem `WELCOME100` → notes duplicate → music lyrics ✅
- (Rincian terakhir di log `2026-09-11-P63-finalize-v1.6.0.md`.)

## 8. Langkah operator (laptop, untuk rilis)

1. Salin seluruh file poin 2 & 3 ke repo lokal → `npm install && npm run build` di `web/`.
2. Jalankan aplikasi sekali (migrasi SQLite auto).
3. Rilis: `powershell -File scripts\build.ps1` → zip **tanpa** `.env` & `craftlife.db*` → GitHub Release **`v1.6.0`** (lihat `README.md` → "Windows Build & Release" / "Shipping an auto-update").
