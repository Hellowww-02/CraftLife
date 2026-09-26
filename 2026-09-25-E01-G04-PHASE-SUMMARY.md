# Rekap Commit Phase E+F+G (E01–G04) → v1.6.7 "Performance & Polish" — 2026-09-25

Tiga batch susulan dalam rilis v1.6.7 yang belum dirilis (versi tetap `1.6.7`,
tag dipindah tiap batch, §5). Batch D01–D05 dilaporkan terpisah (commit
`e11a3d9`); dokumen ini mencakup E01–E04 + F01–F04 + G01–G04.

| Batch | Commit | Isi |
|-------|--------|-----|
| E+F (digabung atas permintaan maintainer) | `6ed2163` (25 files, +506/−42) | Palet Pro, Notification Center, sleep timer, focus trap, +100 item katalog, sortir nutrisi |
| G | `45e6390` (12 files, +101/−15) | Snooze pengingat, pin catatan, cari teman |
| Docs | (commit dokumentasi ini) | Laporan ini + rapihan release notes + header UPDATE_RULES |

## Format 1 — i18n key baru (final): +12 (4.442 → 4.454)

| Update | +Key | Total | Area |
|--------|-----|-------|------|
| E01 | 0 | 4.442 | Palet (pakai-ulang 5 key lama; nilai `web_palette_placeholder` diubah ID+EN) |
| E02 | 0 | 4.442 | Lonceng (pakai-ulang `notif_title`/`notif_empty`/`notif_mark_all`) |
| E03 | 1 | 4.443 | Sleep timer |
| E04 | 0 | 4.443 | Focus trap (tanpa string baru) |
| F01+F02 | 0 | 4.443 | 100 item (nama inline di tuple) |
| F03 | 4 | 4.447 | Sortir nutrisi |
| G01 | 4 | 4.451 | Snooze pengingat |
| G02 | 2 | 4.453 | Pin catatan |
| G03 | 1 | 4.454 | Cari teman |

Key baru (semua ID+EN serentak, export + copy 2× `messages.json` tiap batch):

| Key | id | en | Dipakai di |
|---|---|---|---|
| `sleep_timer` | Timer tidur | Sleep timer | Tooltip tombol Timer `MusicView` |
| `food_sort` | Urut | Sort | Label dropdown sortir `NutritionView` |
| `food_sort_name` | Nama A–Z | Name A–Z | Opsi sortir |
| `food_sort_cal` | Kalori terendah | Lowest calories | Opsi sortir |
| `food_sort_pro` | Protein tertinggi | Highest protein | Opsi sortir |
| `reminder_snooze` | Tunda | Snooze | Label grup + tooltip chip `RemindersView` |
| `reminder_snooze_10m` | 10 mnt | 10 min | Chip +10 menit |
| `reminder_snooze_1h` | 1 jam | 1 hour | Chip +1 jam |
| `reminder_snooze_tomorrow` | Besok | Tomorrow | Chip +24 jam |
| `note_pin` | Sematkan | Pin | Tooltip tombol pin |
| `note_unpin` | Lepas sematan | Unpin | Tooltip tombol lepas |
| `friends_search` | Cari teman… | Search friends… | Placeholder + aria-label `FriendsView` |

## Format 2 — File ditimpa (final, 26)

- E01: `web/src/components/CommandPalette.tsx` (tulis ulang: ↑↓/Enter,
  Ctrl+1–9, seksi Pages/Actions, aksi Habit/Daily/Quest, ARIA listbox),
  `translations.py`, 2× `messages.json`.
- E02: `web/src/components/Navbar.tsx` (lonceng + badge + dropdown +
  tandai dibaca + Esc; state & polling yang mati dihidupkan lagi).
- E03: `web/src/music/MusicPlayerContext.tsx` (`sleepLeftSec` +
  `setSleepTimer`, cleanup di `stopAll`/unmount),
  `web/src/components/views/MusicView.tsx` (tombol Timer + countdown).
- E04: 13 dialog (`TaskTemplate`, `Rank`, `DashboardWidgets`,
  `FolderIconPicker`, `QuickAdd`, `LevelUpModal`, `LoveBucket/Event/Memory`,
  `PlaylistIcon`, `Shortcuts`, `YearWrapped`, `CommandPalette`) —
  impor hook + `ref` panel.
- F01+F02: `food_data.py` (+100 tuple, CRLF dipertahankan).
- F03: `web/src/components/views/NutritionView.tsx` (sortir + chip porsi).
- G01: `web/src/components/views/RemindersView.tsx` (handler + chip tunda).
- G02: `database.py` (kolom `pinned` + param `update_note`),
  `life_api.py` (teruskan `pinned`), `web/src/context/GameContext.tsx`
  (param opsional `pinned`), `web/src/components/views/NotesView.tsx`
  (tombol pin + pinned-first).
- G03: `web/src/components/views/FriendsView.tsx` (kotak cari + filter).
- Amend tiap batch: `updater.py` (entri changelog, versi tetap),
  `README.md`, `RELEASE_NOTES_v1.6.7.md`, `UPDATE_RULES.md` (header fase).

## Format 3 — File baru (final, 1 + dokumen ini)

- `web/src/hooks/useFocusTrap.ts` — kunci Tab di dalam dialog (E04).
- `2026-09-25-E01-G04-PHASE-SUMMARY.md` — dokumen ini.

## Format 4 — Endpoint & perintah

Endpoint baru: **tidak ada**. Jalur pakai-ulang: `toggleDaily`/`toggleQuest`
(E01), `POST /api/notifications/read` via `studio.markNotifications` — yang
terbukti tak dipakai TSX manapun sebelum E02 (G02: parameter opsional
`pinned` di `POST /api/notes/:id/update`; G01: route update reminder yang ada).

Perintah verifikasi (tiap batch): `python3 scripts/export_i18n.py` + copy →
keys naik sesuai tabel; `npx tsc --noEmit` → 0 errors;
`npm run build` → bersih; uji scratch-DB untuk F (774→874, custom/log utuh,
`integrity_check=ok`, `init_db()` 2×) dan G02 (kolom + toggle + partial-safe);
`v167_harness/check.py`, `v165_harness/check.py`, regresi 41 file sekuensial,
`smoke_c09.py`.

## Format 5 — Kesimpulan per update

- E01: palet Ctrl+K full-keyboard + aksi tugas sekali klik.
- E02: lonceng notifikasi hidup lagi (badge, riwayat, tandai dibaca).
- E03: timer tidur musik 15/30/60 + countdown, auto-pause.
- E04: Tab terkunci di 13 dialog + role ARIA.
- F01+F02: katalog 774 → 874 (50 makanan + 50 minuman), nol duplikat,
  makro lolos cek konsistensi v165; DB lama otomatis menerima 100 item.
- F03: sortir grid nutrisi + preset porsi ½×/1×/2×.
- G01: tunda pengingat 10 mnt/1 jam/Besok (repeat & suara utuh).
- G02: sematkan catatan + pinned-first (kolom aditif idempoten).
- G03: saring daftar teman sambil mengetik (nol API call).
- Nol fitur dikurangi di semua update.

## Format 6 — Migrasi

- SQLite: 1 kolom aditif (`notes.pinned` via `_safe_alter`, idempoten,
  default 0) + seed 100 item katalog (INSERT-jika-nama-belum-ada, UPDATE
  kanonik). Tanpa perubahan skema lain; DB lama & baru identik.
- Supabase: **none** (tanpa migrasi cloud).

## Format 7 — Konsolidasi + bukti + operator

- Total: +12 key → **4.454** (identik 4 sumber, 0 hilang);
  26 file ditimpa, 1 hook baru (+ dokumen ini); 0 endpoint baru;
  1 kolom aditif; Supabase none.
- Bukti akhir (batch G): `py_compile` semua `.py` OK · `tsc` 0 ·
  build `index-CVSbplQF.js` 454.21 kB (gzip 142.33), 24 chunk view ·
  v167 **29/29** · v165 **13/13** · regresi **41/41 file** ·
  smoke **31/31** · tree bersih.
- Tag `v1.6.7` (annotated) dipindah ke commit terbaru tiap batch (§5).
- Jujur: verifikasi = tsc + build + harness (standar repo); uji klik
  manual di browser tidak dilakukan di sandbox (tak ada browser).
- Operator: `git push origin main` + `git push origin v1.6.7 --force`,
  build exe, zip isi `dist/CraftLife/` di root (`craftlife-1.6.7.zip`) +
  sha256, GitHub Release tag tepat `v1.6.7` berisi
  `RELEASE_NOTES_v1.6.7.md`.
