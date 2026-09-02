# 🗺️ PARITY ROADMAP — P30 → P46 (Phase 4)

> **Lanjutan dari roadmap parity yang ada** (melanjutkan `PARITY_ROADMAP.md` yang sempat dihapus).
> Sejarah fase: **P1–P11** migrasi PyQt→React per halaman → **P12–P19** deep-audit → **P20–P21** → **P22–P29** Phase 3 (i18n sweep).
> **Phase 4 ini (P30–P46)** memperbaiki issue + bug yang dilaporkan pasca Phase 2/3 (P12–P21) dan menambah fitur baru.

---

## 0. Direktif Global (wajib dipegang semua fase)

1. **Tujuan akhir: semua page React 100% 1:1 dengan PyQt.** PyQt = **sumber kebenaran perilaku/fitur** (bukan referensi pixel-identik; UI front-nya di-convert ke React dengan kebebasan desain, tapi *action parity* harus sama).
2. **Jangan jadikan `MainPyQt6.py` sebagai referensi UI front React** — tapi **convert** perilakunya ke React. Boleh rewrite komponen React dari nol bila perlu ("abaikan design React yang sekarang").
3. **Semua string user-facing wajib ber-key translations** — `translations.py` (id+en) + `WEB_I18N_KEYS` di `api_server.py` + `web/src/i18n/messages.json`. Tidak boleh ada hardcode / ternary `lang === 'id' ? …`.
4. **Game rules hanya di `database.py`** — jangan diduplikasi di TypeScript.
5. **Satu commit phase** diperbolehkan. Di akhir setiap commit-phase, keluarkan **laporan update format 1–7** (lihat §6).
6. Verifikasi tiap fase: `py_compile` backend EXIT 0, `tsc --noEmit` EXIT 0, `vite build` EXIT 0.

---

## 1. P30 — Fondasi Global (lintas halaman) ✅ DONE (2026-09-02)

**Cakupan:** fix chart stretch, helper input currency, buff navbar, baseline i18n.

| Sub | Issue | Aksi |
|-----|-------|------|
| a | Chart `LineChart`/`DualLineChart`/`BarChart`/`Sparkline` di `web/src/components/charts.tsx` pakai `width`/`height` **fixed** (default 320/120) → chart mentok kiri, tidak stretch kanan-kiri | Ubah semua chart jadi **responsif** (`viewBox` + `preserveAspectRatio="none"`/`width="100%"`, atau ukur container via `ResizeObserver`). Terapkan ke Home (sleep↔productivity), Health&Food (weight/height trend), Economy, Sport. |
| g | Input nominal economy masih format IDR walau currency aktif ≠ IDR | Buat helper `currency.ts`: `parseMoneyInput(value, currency)` + `moneyInputMask(...)`; terapkan ke SEMUA dialog economy (transaksi, debt, saving, invest, subs, IOU). |
| 2 | Navbar hanya tampil 2 buff (boss_dmg, crit_chance) | Tampilkan **seluruh buff aktif** dari `db.get_all_active_buffs(user_id)` (sudah ada di `database.py:10846`), expose via `/api/bootstrap`/`/api/me`, render badge lengkap di Navbar/Sidebar (ikon + label per buff, tooltip). |

**File:** `web/src/components/charts.tsx`, `web/src/utils/currency.ts`, `web/src/components/Navbar.tsx`, `web/src/components/Sidebar.tsx`, `api_server.py`, `web/src/i18n/messages.json`, `translations.py` (+`WEB_I18N_KEYS`).

**DoD:** semua chart mengisi lebar container; navbar menampilkan semua buff; tidak ada input currency yang salah format.

---

## 2. P31 — Profile + Settings: Hero Customization & Class ✅ DONE (2026-09-02)

| Sub | Issue | Aksi |
|-----|-------|------|
| b | Tab **Hero Customization** masih di Settings; harus **pindah ke Profile** menggantikan tab lama (screenshot 3) | Pindahkan blok Hero Customization & Class dari `SettingsView.tsx` → `ProfileView.tsx` (struktur tab Profile mengikuti PyQt `ProfilePage`: hero/avatar, bio, class). |
| b | Class **hanya boleh ganti seminggu sekali**, bukan setiap hari | Ubah `database.py: change_class()` → cooldown **7 hari (7×24 jam)** dari `last_class_change` (✅ dikonfirmasi user). Kunci tetap `db_class_change_cooldown`. |
| x | Settings setelah pemindahan tetap rapi & tidak ada sisa tab hero | Bersihkan Settings; pastikan sisa toggles tetap 1:1 PyQt. |

**File:** `web/src/components/views/ProfileView.tsx`, `web/src/components/views/SettingsView.tsx`, `database.py`, `api_server.py`, i18n.

**DoD:** Hero Customization ada di Profile; ganti class ter-blok 7 hari (pesan cooldown tampil); Settings tanpa tab hero.

---

## 3. P32 — Tasks: Habits / Dailies / Quests (cleanup shortcut template) ✅ DONE (2026-09-02)

| Sub | Issue | Aksi |
|-----|-------|------|
| c/d/e | Tombol shortcut template (`morning_routine`, `healthy_life`, `work_productivity`, `project_prep`, `event_planning`, dll.) masih tampil sebagai tombol cepat di **`TaskFolderBar.tsx`** (bar folder, tepat di sebelah tombol "Ungrouped") | **Dihapus** blok render `templates.slice(0,4)` + state/effect `listTemplates` + `applyTaskTemplate` + `TEMPLATE_MODES`. Tombol **📋 Templates** + `TaskTemplateDialog` tetap dipertahankan (1:1 PyQt). SportView punya tombol "Template PyQt" sendiri (di luar scope P32). |
| c/d/e | String belum semua ber-key | Key seluruh string hardcoded di `HabitsView`/`DailiesView`/`QuestsView` **dan** `TaskFolderBar` (badge/filter/opsi difficulty, Good/Bad, Positive/Negative, Freeze, Frozen, tooltip edit/delete/folder, placeholder, Ungrouped, prompt rename). |

**File:** `web/src/components/TaskFolderBar.tsx`, `web/src/components/views/HabitsView.tsx`, `DailiesView.tsx`, `QuestsView.tsx`, `translations.py`, `api_server.py` (`WEB_I18N_KEYS`), `web/src/i18n/messages.json`, `web/public/i18n/messages.json`.

**DoD:** tidak ada tombol template langsung selain tombol Templates ✅; grid tetap rapi ✅; string ber-key semua (termasuk TaskFolderBar) ✅.

---

## 4. P33 — SportTrack: Reps Chart + Folder System

| Sub | Issue | Aksi |
|-----|-------|------|
| f | Reps chart **tidak muncul** padahal sudah log reps per hari | Debug `SportView.tsx` (aggregasi `repSeriesByDate` + komponen `BarChart`). Pastikan `life.sportRepsSummary()` dikonsumsi benar dan chart render zero-fill 7 hari (parity `SportRepsChartWidget` PyQt). |
| f | Tambah **system folder** seperti habits/dailies/quests | Pakai `task_folders` (mode `sport` atau reuse mekanisme folder task) + endpoint di `life_api.py`/`api_server.py` + UI folder bar di SportView. |
| f | i18n | Key semua string baru. |

**File:** `web/src/components/views/SportView.tsx`, `database.py`, `life_api.py`, `api_server.py`, i18n.

**DoD:** chart reps 7 hari tampil setelah log; sport punya folder (buat/pindah/rename/hapus) 1:1 task.

---

## 5. P34 — Economy: Nominal Input Sesuai Currency

| Sub | Issue | Aksi |
|-----|-------|------|
| g | Savings harus bisa **input nominal bebas** (bukan tombol +50k/−50k) | Ganti tombol fixed → input nominal + tombol Tambah/Tarik (`db.add_to_saving` / withdraw sudah ada). |
| g | Invest harus **masukkan total nilai invest** sesuai input user | Form invest: input nominal total (amount), simpan via `db.add_investment`. |
| g | Semua dialog economy masih format IDR | Terapkan helper currency (dari P30) ke semua input nominal + tampilan. |
| g | Sisa string `lang === 'id' ?` di EconomyView (tab labels, placeholder, dst.) | Key-kan semua (tabungan/savings, investasi/invest, tarik/withdraw, nominal labels…). |

**File:** `web/src/components/views/EconomyView.tsx`, `web/src/utils/currency.ts`, i18n.

**DoD:** saving add/withdraw nominal bebas; invest menyimpan total nilai; input menampilkan simbol/format currency aktif; 0 ternary hardcoded.

---

## 6. P35 — Supplies / Achievements / Leaderboard (audit ringan)

| Sub | Issue | Aksi |
|-----|-------|------|
| h/v/w | Diklaim sudah 1:1 | Verifikasi cepat vs PyQt (`SuppliesPage`, `AchievementPage`, `LeaderboardPage`) + i18n audit. Hanya perbaiki bila ditemukan gap. |

**File:** `SuppliesView.tsx`, `AchievementsView.tsx`, `LeaderboardView.tsx`, i18n (bila perlu).

---

## 7. P36 — Health & Food: Terjemahan Makanan + Chart

| Sub | Issue | Aksi |
|-----|-------|------|
| i | Database makanan di React belum pakai **terjemahan id/en** (PyQt sudah) | Expose `nameId`/`nameEn` dari `food_data.py` lewat API; `HealthFoodView.tsx` + dialog makanan render nama sesuai bahasa aktif (pola data-mapping, bukan ternary UI). |
| i | Chart **weight trend 7d** & **height trend 7d** mentok kiri | Perbaikan dari P30 (stretch) — verifikasi di halaman ini. |

**File:** `web/src/components/views/HealthFoodView.tsx`, `life_api.py`, `food_data.py`, i18n.

**DoD:** setiap makanan/minuman tampil nama id/en sesuai bahasa; chart weight/height stretch penuh.

---

## 8. P37 — Love Space: Couple Profile & Couple Account 1:1

| Sub | Issue | Aksi |
|-----|-------|------|
| j | Couple profile & couple account tidak 1:1 PyQt `LovePage` | Re-audit PyQt `LovePage` (profile pasangan, check-in, memories, bucket, events, weekly review, cycle, photo) → samakan struktur/data/aksi di `LoveSpaceView.tsx`. |
| j | i18n | Key semua string baru. |

**File:** `web/src/components/views/LoveSpaceView.tsx`, `studio_api.py`, i18n.

**DoD:** couple profile & account section match PyQt (field, aksi, tampilan data).

---

## 9. P38 — Learning: 3-Tab Slide + Layout Stretch

| Sub | Issue | Aksi |
|-----|-------|------|
| k | **Slide antar 3 tab** (Sources / Chat AI / Studio Generate) belum ada (PyQt pakai slide antar tab) | Implement transisi slide (CSS `transform`/`motion`) antar 3 tab sesuai PyQt. |
| k | Layout kurang rapi & **tidak stretch** saat salah satu tab ditutup | Perbaiki layout: panel yang tersisa melebar penuh (flex-1) ketika tab lain ditutup. |

**File:** `web/src/components/views/LearningView.tsx`, i18n.

**DoD:** 3 tab bisa di-slide; menutup tab → panel tersisa stretch penuh.

---

## 10. P39 — Music: Lyrics Live Search (Pomodoro audit)

| Sub | Issue | Aksi |
|-----|-------|------|
| l | Pomodoro sudah 1:1 | Audit saja. |
| m | Lyrics search **kurang cepat** & cakupan sempit; lyrics harus **live sync menit/detik** | Percepat + perluas pencarian lirik (`studio_api.get_lyrics` + `_clean_lyrics_query`), tambah fallback provider/query variance, dan render **time-synced lyrics** (highlight baris sesuai posisi pemutaran). |

**File:** `web/src/components/views/MusicView.tsx`, `studio_api.py`, i18n.

**DoD:** pencarian lirik lebih cepat & lebih luas; lirik berjalan sinkron dengan waktu musik.

---

## 11. P40 — Notes / Reminders / Calendar (audit)

| Sub | Issue | Aksi |
|-----|-------|------|
| n/o/p | Diklaim sudah 1:1 | Verifikasi vs PyQt + i18n audit. Perbaiki bila ada gap kecil. |

**File:** `NotesView.tsx`, `RemindersView.tsx`, `CalendarView.tsx` (bila perlu).

---

## 12. P41 — Crafting: Consumable qty 0 memblokir craft

| Sub | Issue | Aksi |
|-----|-------|------|
| q | Bila resep butuh item **consumable** dan qty-nya 0, craft tetap bisa | Cek di backend (`db` craft path) + `CraftView.tsx`: sebelum craft, validasi semua bahan termasuk consumable — bila qty 0 → blokir + toast "bahan tidak cukup". |

**File:** `web/src/components/views/CraftView.tsx`, `database.py`, `api_server.py`, i18n.

**DoD:** resep dengan consumable qty 0 tidak bisa di-craft (pesan jelas).

---

## 13. P42 — Shop: Keterangan Buff + Consumable 0

| Sub | Issue | Aksi |
|-----|-------|------|
| r | Keterangan **buff item** tidak tampil di subtab Bag/Inventory | Tampilkan deskripsi buff tiap item (dari katalog shop `db`) di baris inventory. |
| r | Consumable qty 0: tampilkan **0** di shop & bag; beli lagi → qty **bertambah sesuai jumlah dibeli** (bukan reset) | Perbaiki tampilan qty & logika beli (`db.buy_item`/inventory) supaya akumulatif; qty 0 tetap terlihat. |

**File:** `web/src/components/views/ShopView.tsx`, `database.py`, `api_server.py`, i18n.

**DoD:** buff item menjelaskan efeknya; consumable 0 tampil 0; beli menambah qty.

---

## 14. P43 — Pets: Slot Equip Bertingkat + Recalc Buff

| Sub | Issue | Aksi |
|-----|-------|------|
| s | Fitur baru: **level >25 dan kelipatan 5 di atasnya** bisa equip +1 pet lagi | Ubah `database.py: equip_pet()` — `max_pets = 1` (level<25), lalu `2 + floor((level-25)/5)` untuk level ≥ 25 (25→2, 30→3, 35→4, dst.). |
| s | Jangan lupa **recalculate buff** | Panggil `recalculate_all_buffs()` setelah equip/unequip (sudah ada). |

**File:** `database.py`, `api_server.py`, i18n (bila ada string baru).

**DoD:** jumlah pet aktif mengikuti level; buff ter-recalc otomatis.

---

## 15. P44 — Friends: Chat 1:1 PyQt

| Sub | Issue | Aksi |
|-----|-------|------|
| t | Pesan chat tidak **real-time** dengan waktu/tanggal user saat ini | Pakai server clock (`clockNow()`) untuk timestamp; auto-refresh percakapan (parity `QTimer 3s` PyQt). |
| t | Chat pertemanan **tidak selengkap PyQt** (ada attachment, reply, edit, delete, reactions, load-earlier, clear) | Samakan dengan PyQt `ChatDialog`: **reply, edit, delete, reactions (👍❤️😂🎉😮😢), load earlier (50/page), clear chat, download attachment** — plus timestamps. (Attachment: ikuti PyQt — cloud-mode download; konfirmasi scope di pertanyaan.) |

**File:** `web/src/components/views/FriendsView.tsx`, `studio_api.py`/`api_server.py`, `cloud_service.py` (bila attachment), i18n.

**DoD:** chat teman real-time + fitur lengkap 1:1 PyQt.

---

## 16. P45 — Guild: Chat, Spyglass, Info Serangan Boss

| Sub | Issue | Aksi |
|-----|-------|------|
| u | Guild chat **kadang tidak terkirim** + belum lengkap | Perbaiki alur kirim (await + konfirmasi sukses/gagal + refresh); samakan fitur chat guild dengan PyQt (reactions, hapus, dsb.). |
| u | **Spyglass** tidak terimplementasi (equip/unequip tak ada efek) | Implementasi: equip spyglass → `users.has_spyglass=1` & reveal **stat boss penuh (HP/damage)**; unequip → bersihkan flag & sembunyikan detail (parity `_update_boss_info`). |
| u | Tidak ada keterangan **damage & HP yang diblok** + info serangan saat menyerang boss | Tampilkan info hasil serangan per aksi (light/heavy/block/ultimate/skill): damage diberikan, damage diblok, HP boss sisa, kritikal — samakan log PyQt `attack_boss`. |

**File:** `web/src/components/views/GuildView.tsx`, `database.py` (spyglass + attack info), `api_server.py`, i18n.

**DoD:** chat guild reliable & lengkap; spyglass punya efek nyata; tiap serangan menampilkan info damage/blok/HP.

---

## 17. P46 — Verifikasi Final + Commit + Laporan (format 1–7)

1. Full regression: `py_compile` semua modul inti; `tsc --noEmit`; `vite build`.
2. Smoke test backend (endpoint GET/POST inti) + cek i18n konsisten (key id+en).
3. **Satu commit** phase P30–P46.
4. Buat **laporan update format 1–7** (lihat §6) sebagai kesimpulan keseluruhan commit phase.

---

## 5. Catatan Teknis Lintas-Fase

- **Chart stretch**: ubah `charts.tsx` agar `svg` pakai `viewBox` + `width="100%"` (dengan `preserveAspectRatio` sesuai jenis chart) — satu fix menyelesaikan Home, Health&Food, Economy, Sport.
- **Currency**: satu helper `formatMoney` sudah ada (`web/src/utils/currency.ts`) — tambah `parseMoneyInput` + mask per currency (IDR, USD, EUR, SGD, JPY, dst.) dan pakai konsisten.
- **Buff navbar**: `db.get_all_active_buffs` + `db.get_skill_buffs` sudah ada → tinggal expose + render.
- **Backend yang harus disentuh**: `change_class` (cooldown 7 hari), `equip_pet` (slot bertingkat), spyglass (equip/unequip + reveal), craft consumable check, `add_investment` (nominal total), endpoint sport folder & chat.
- **i18n workflow**: string baru → `translations.py` (id+en) → tambah ke `WEB_I18N_KEYS` di `api_server.py` → tambah ke `web/src/i18n/messages.json` (id+en).
- **Tidak ada migrasi Supabase baru** yang diprediksi wajib (attachment chat sudah ada di migrasi `20260813220000_phase4b2_b3_chat_attachments.sql`). Bila P44 memutuskan upload attachment baru, akan ditandai di §6.

---

## 6. Format Laporan Akhir Tiap Commit-Phase (1–7)

**Protokol eksekusi (dikonfirmasi user):** aku **tidak** coding sampai kamu kirim perintah `MULAI Pxx` / `LANJUT Pxx`. Setiap selesai coding/update, aku lampirkan **6 format** di akhir chat:

1. **Translate key di `translations.py`** (daftar key baru id+en, bila ada)
2. **File yang harus ditimpa** (daftar file yang diubah)
3. **File yang baru** (daftar file baru)
4. **Command baru** (bila ada — mis. build/verifikasi)
5. **Kesimpulan tiap bagian coding/update**
6. **Migrasi Supabase baru** (bila ada)

Lalu di akhir **satu commit phase** (setelah fase terakhir), tambah:
7. **Kesimpulan keseluruhan commit phase** (mis. P30–P46).

---

## 7. Pertanyaan / Konfirmasi sebelum eksekusi

Lihat pertanyaan di chat (ask_user):
1. Cara eksekusi (langsung semua vs bertahap).
2. Formula slot pet.
3. Scope attachment chat Friends.
4. Jenis cooldown class (7 hari vs per minggu kalender).
