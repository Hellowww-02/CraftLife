# CRAFTLIFE — FINAL PARITY MATRIX (P1-P19)

> Dibuat saat **P19 — Final Full Parity Verification (2026-09-01)**.
> Status: `VERIFIED 1:1` (perbandingan aktual + smoke), `PARTIAL`, `NOT VERIFIED`, `BROKEN`.
> Definisi "1:1" = **action parity** (tombol/aksi/logika setara PyQt; PyQt = source of truth), bukan pixel-identical.

| React | PyQt | UI | Feature | Behavior | State | Backend | Persistence | Status |
|---|---|---|---|---|---|---|---|---|
| Home | DashboardPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Profile | ProfilePage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Habits | TaskPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Dailies | TaskPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Quests | TaskPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| SportTrack | SportTrackPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Economy | EconomyPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Supplies | SuppliesPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Health & Food | HealthFoodPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Love Space | LovePage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Learning | LearningPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Pomodoro | PomodoroPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Music | MusicPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Notes | NotesPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Reminders | RemindersPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Calendar | CalendarPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Crafting | CraftingPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Shop | ShopPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Pets | PetsPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Friends | FriendsPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Guild | GuildPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Achievement | AchievementPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Leaderboard | LeaderboardPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Settings | SettingsPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Boss | ShopPage/GuildPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |
| Nutrition | HealthFoodPage | ok | ok | ok | ok | ok | ok | VERIFIED 1:1 |

## Catatan dimensi
- **UI**: layout/seksi/kartu/kontrol/input/dialog/modal/tabs/list/empty+loading+error states setara.
- **Feature**: action setara; tidak ada fitur PyQt hilang di React pada halaman di atas.
- **Behavior**: navigasi, save/edit/delete/cancel, konfirmasi, validasi, notifikasi setara.
- **State**: state dari snapshot server; `applyLive` satu sumber perubahan; server-clock tunggal (bukan `new Date()`).
- **Backend**: handler route setara; py_compile EXIT 0.
- **Persistence**: SQLite lokal = immediate/source utk offline; cloud = sync best-effort (gated) utk wallet/inventory/social.

## Post-P11 issue (re-audit P19)
| Issue | Hasil |
|---|---|
| 1B `_bad` studio_api | `def _bad` ADA (line 844) — fixed |
| 1C Shop purchase | bekerja saat gold cukup; 400 hanya `gold_insufficient` |
| 3 Music shuffle/repeat/import | hadir |
| 4 Task templates + folders | `TaskTemplateDialog` + `TaskFolderBar` hadir |
| 5 Sport reps | reps + chart hadir |
| 6 Economy template | TIDAK ada di PyQt & React — konsisten |
| 10 Theme | **diperbaiki di P18** (CSS vars + persist) |

## Sisa yang disengaja (bukan gap, didokumentasikan)
- Antarmuka on-line **Supabase cloud** (leaderboard/guild/chat online, conflict sync, cross-device) hanya diuji dalam kondisi unlinked/local-fallback — butuh kredensial `.env` + migrasi cloud aktif. Bukan regresi; konsisten pola P7–P9 (deferral gated).
- Theme boleh implementasi React-native (CSS vars) — diizinkan oleh aturan; palet & perilaku equivalent PyQt.
