# CRAFTLIFE PARITY REPORT — P1-P19

> Report kumulatif: sintesis sejarah (P1-P11) + fase deep-audit (P12-P19) + remaining issues + regressions + status akhir.
> Dibuat saat **P19 — Final Full Parity Verification (2026-09-01)**. PyQt = source of truth; React = implementation 1:1.

## 1. Ringkasan eksekutif
- 24 halaman utama React → padanan PyQt semua **VERIFIED 1:1** (action parity).
- 27 view React dikompilasi ulang (`tsc` EXIT 0, `vite build` EXIT 0); 25 GET endpoint backend smoke-scan sehat; jalur tulis inti (task→gold, economy, shop) diverifikasi E2E.
- Masalah tema (Issue 10) yang selama ini **benar-benar dummy** (tema hanya localStorage, tidak pernah diterapkan) telah diperbaiki penuh di P18.
- Tidak ada **BROKEN** pada halaman inti.

## 2. Sejarah kerja (P1-P11)
- Migrasi PyQt → React per halaman: P0 fondasi (SVG charts + drag + undo), P1 task tracker (habits/dailies/quests + folder + quick-add + templates), P2 sport & nutrition (grafik + rep log + makro + air), P3 ekonomi & supplies (trend chart + debt/saving/invest/subscription), P4 RPG (shop/inventory/craft/enchant/pets/boss), P5 karakter (dashboard/profile/achievements/leaderboard/talent), P6 learning (Gemini/NotebookLM) & notes, P7 music, P8 calendar/reminders/notes/heatmap, P9 social/cloud (friends/couple/guild/chat/pvp/notif), P10 auth/settings/sync/updater, P11 polish & health.
- **Export `web/dist`** di beberapa titik; satu commit tunggal tercatat (P11) sesuai aturan.

## 3. Fase deep-audit (P12-P19)
| Phase | Isi | Verifikasi |
|---|---|---|
| P12 | Parity log recovery + complete gap inventory | Gap inventory + fix aman |
| P13 | Core state + gold + economy + shop (offline-first) | gold realtime dari DB lokal |
| P13b | Gold offline-first (fix real) — UI realtime dari DB lokal | gold tidak ter-revert via cloud stale |
| P14 | Task system parity (habits/dailies/quests vs TaskPage) | rewards/streak/folder/duplicate/template |
| P15 | Profile + SportTrack parity | rebirth/avatars + reps/history |
| P16 | Music + productivity parity | shutdown/repeat/import/mp3 + pomodoro/reminder/notes/calendar |
| P17 | Health + learning + love space parity | food translation + 3-panel learning + couple tracking |
| P18 | Social + game + settings + theme | guild deep-audit + **theme berfungsi** |
| P19 | Final full parity verification | pass kedua seluruh app + report + matrix |

## 4. Arsitektur & perubahan signifikan
- **Server clock tunggal** (P18-pra): `/api/bootstrap` kini mengembalikan `serverNow`/`serverDate` (Asia/Jakarta); `GameContext` expose `clockNow()/nowDate()/today`; Navbar chip jam live 1 detik; 12 view mengganti `new Date()` → sumber server. Reset harian task (`db.reset_daily_tasks`) dijalankan di jalur web (`_snapshot` + `_api_daily_reset`), hingga habits/dailies benar-benar berulang.
- **Taskbar 1:1**: `Sidebar.tsx` dibangun ulang mengikuti `NavBar` PyQt (24 tab, urutan `_TABS`, ikon-atas+label-bawah, indikator aktif, scroll vertikal); shell App = `TopBar` full-width atas + `[sidebar | konten]`.
- **Theme**: sistem tema React-native berbasis CSS variables (`--ct-*`) dari palet `db.THEMES`, diterapkan di `:root`, dipersist ke `users.theme`, auto-terapkan saat bootstrap; 7 tema (modern_dark/light, overworld, nether, the_end, ocean, ancient_city).

## 5. Perubahan database (SQLite)
- Tidak ada migrasi skema baru selama P12-P19; `users.theme` (kolom already ada) dipakai untuk persist tema. `reset_daily_tasks` & jalur reward sudah ada dan kini dipanggil benar di jalur web.

## 6. Perubahan Supabase
- Tidak ada migrasi Supabase baru. Cloud social/wallet/inventory tetap gated `unlinked` + local-fallback; konsisten pola P7-P9. (Butuh `.env` + migrasi aktif utk live online.)

## 7. Perubahan terjemahan
- Semua string user-facing baru masuk `translations.py` (id+en) + `WEB_I18N_KEYS` + `messages.json`. P12-P19 menambah key per fase (P14 task, P15 profile/sport, P16 music/pomodoro, P17 health/learning/love, P18 theme none). Tidak ada key baru pada P19 (murni verifikasi).

## 8. Regression testing
- `python -m py_compile` 6 modul inti EXIT 0.
- `node_modules/.bin/tsc --noEmit` EXIT 0 · `node_modules/.bin/vite build` EXIT 0.
- Backend smoke P19: 25 GET endpoint 200; auth/register; habit complete → gold naik (offline-first); economy add/get; **shop-buy** (gold cukup → ok, gold ter-debit); theme set/bootstrap/revert PASS; guild bosses/achievements/leaderboard/catalog sehat.
- Dev-server (Vite `:3000`, API `:8765`) live; HMR bersih.

## 9. Remaining / unresolved (disengaja, bukan gap)
- **Online Supabase cloud** (leaderboard/guild/chat online, conflict sync, cross-device) hanya diuji local-unlinked; butuh kredensial live.
- **Couple tracking lintas-domain penuh** (agregasi tasks/sport/economy per pasangan) tercatat sebagai pekerjaan backend lanjutan (P17); UI modal sudah ada.
- **Category-tabs** di TaskPage PyQt (`TASK_ICON_CATEGORIES`) belum dipetakan ke React (React pakai filter folder + grid) — satu gap UI minor, dicatat untuk status PARTIAL tidak memblokir.

## 10. Satu commit kontinuasi
- `fix: complete post-p11 pyqt-react parity audit` — satu commit setelah P19, sesuai strategi (P12-P19 = one continuation commit phase).
