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

## 4. P33 — SportTrack: Reps Chart + Folder System ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| f | Reps chart **tidak muncul** padahal sudah log reps per hari | Root cause: `/api/sport/reps` mengembalikan `activities` tanpa field `series`, sedangkan SportView membangun chart dari `a.series` per-aktivitas → selalu kosong. Fix: endpoint kini mengembalikan `series` global (7 hari zero-fill via `db.get_sport_rep_series(uid)`, parity `SportRepsChartWidget`); SportView merender `BarChart` dari `series` tersebut (zero-fill, tampil bila ada data). |
| f | Tambah **system folder** seperti habits/dailies/quests | `map_sport` kini menyertakan `folderId`; `db.reorder_tasks` mendukung mode `sport` (→ `sport_activities`); `GameContext` menambah cabang `sport` di `moveTaskAcrossFolders` + `reorderSportLogs`; `SportView` memakai `TaskFolderBar mode="sport"` (create/rename/duplicate/delete + filter + drag-drop antar folder) + chip folder per kartu + drop-zone "keluar dari folder" (parity `drop_here_to_remove_folder`). |
| f | i18n | Key baru `task_edit_title`, `task_duplicate_title`, `sport_notes_ph`; bersihkan 7 ternary `lang === 'id' ?` + tooltip/placeholder hardcoded di SportView. |

**File:** `web/src/components/views/SportView.tsx`, `web/src/context/GameContext.tsx`, `web/src/api/rpg.ts`, `web/src/types.ts`, `life_api.py`, `database.py`, `translations.py`, `api_server.py` (`WEB_I18N_KEYS`), `web/src/i18n/messages.json`, `web/public/i18n/messages.json`.

**DoD:** chart reps 7 hari tampil setelah log ✅ (smoke: series 7 hari zero-fill, log 50 reps → hari ini 50); sport punya folder (buat/pindah/rename/hapus) 1:1 task ✅ (smoke: reorder sport move/remove folder OK).

---

## 5. P34 — Economy: Nominal Input Sesuai Currency ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| g | Savings harus bisa **input nominal bebas** (bukan tombol +50k/−50k) | Tombol fixed `+50k`/`-50k` diganti **MoneyInput per kartu + tombol ＋ (Tambah) / − (Tarik)**; memakai `db.add_to_saving`/`withdraw_from_saving` yang sudah ada. (smoke: USD 50k add → 50k; withdraw 20k → 30k.) |
| g | Invest harus **masukkan total nilai invest** sesuai input user | Form invest sudah pakai `MoneyInput` → `db.add_investment` (input nominal total tersimpan; validasi max 10% saldo = parity `investment_max_10_percent`). (smoke: invest 500 USD tersimpan; collect 5% → 525 USD.) |
| g | Semua dialog economy masih format IDR | Verifikasi: semua nominal pakai `MoneyInput`/`formatMoney` dengan `currency` aktif (konversi IDR↔currency di `currency.ts` + `_to_idr` server). Sisa format "IDR" (tombol `+50k`/`-50k`) hilang bersama fix savings. |
| g | Sisa string `lang === 'id' ?` di EconomyView (tab labels, placeholder, dst.) | **0 ternary tersisa.** Ditambah 47 key economy baru (tab labels, banner, debt row, placeholder, hint, dll.). |
| g+ | **Tambahan (konfirmasi user):** (1) kartu transaksi menampilkan **nama** (bukan kategori) — parity `_make_card` PyQt; kategori jadi sub-line bila berbeda. (2) Invest punya **dialog lengkap** `AddInvestmentDialog` (nama + ikon 📈🏦💰🏠🚀 + nominal + catatan) + **Collect Return input nominal manual** (parity `_collect_return` → `db.add_investment_return`, bukan +5% fix) + tombol hapus invest + tanggal investasi di kartu. (3) Subs punya **dialog lengkap** `AddSubscriptionDialog` (nama + ikon 📺🎵🤖📚🏋️📅 + biaya + jatuh tempo + periode monthly/yearly/one-time + auto-renew checkbox + catatan), edit via dialog sama, kartu tampil `{amount} per {period}` + jatuh tempo merah bila lewat + catatan + tombol Renew hanya saat overdue. |

**File:** `web/src/components/views/EconomyView.tsx`, `web/src/context/GameContext.tsx`, `web/src/api/life.ts`, `web/src/types.ts`, `life_api.py` (endpoint `investments/{id}/add-return` + `delete`, `subscriptions/{id}/update`; snapshot `investedDate`/`isRecurring`), `translations.py`, `api_server.py` (`WEB_I18N_KEYS`), `web/src/i18n/messages.json`, `web/public/i18n/messages.json`.

**DoD:** saving add/withdraw nominal bebas ✅; invest menyimpan total nilai ✅; input menampilkan simbol/format currency aktif ✅; 0 ternary hardcoded ✅.

---

## 6. P35 — Supplies / Achievements / Leaderboard (audit ringan) ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| h/v/w | Diklaim sudah 1:1 | Verifikasi vs PyQt (`SuppliesPage`, `AchievementPage`, `LeaderboardPage`): struktur 3 view sudah dekat parity (supplies: stock card/history/restock/notes; achievements: grid + claim reward + search; leaderboard: local vs cloud + XP/Gold/level ranks). Tidak ada gap fungsional yang perlu diubah. |
| h/v/w | i18n audit | **0 ternary `lang === 'id' ?` tersisa** di ketiga view. `SuppliesView` (semua label header/subtitle/aksi/modal/transaksi/history), `AchievementsView` (toast claim + subtitle), `LeaderboardView` (hint lokal, fallback cloud, empty lokal/cloud) diganti `t(...)`. Reuse key lama: `low_stock`, `web_supply_adjust`, `supplies_stock_now`. +9 key baru P35. |

**File:** `SuppliesView.tsx`, `AchievementsView.tsx`, `LeaderboardView.tsx`, `translations.py`, `api_server.py` (`WEB_I18N_KEYS`), `web/src/i18n/messages.json`, `web/public/i18n/messages.json`.

**DoD:** 3 view 1:1 vs PyQt ✅; 0 ternary hardcoded ✅; py_compile + tsc --noEmit + vite build EXIT 0 ✅.

---

## 7. P36 — Health & Food: Terjemahan Makanan + Chart ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| i | Database makanan di React belum pakai **terjemahan id/en** (PyQt sudah) | `life_api.py` `/api/food/items` kini mengembalikan `nameId` + `nameEn` per item (default → `get_food_name(name, "en")` dari `FOOD_NAMES_MAP`; custom → nameId==nameEn). `HealthFoodView` merender nama lewat helper data-mapping `foodNameOf(f, lang)` (bukan ternary UI), pencarian mencakup kedua bahasa, `logFood` mengirim `foodId` + `foodName` (nameId) agar lookup default-food akurat di kedua bahasa. Dialog resep (`NewRecipeModal`) + modal makanan custom ikut memakai nameId/nameEn. |
| i | Chart **weight trend 7d** & **height trend 7d** mentok kiri | Verified: `LineChart` sudah responsif sejak P30 (`useMeasuredWidth` + `w-full`), `width={460}` hanya fallback pra-pengukuran → chart weight/height kini stretch penuh. |
| i | i18n sisa | 0 ternary `lang === 'id' ?` UI tersisa. Bersihkan placeholder custom food (`food_custom_ph`), label `Target air` (`food_water_goal`), label makro modal custom (`food_calories/protein/carbs/fat_label`), opsi ekspor (`export_xlsx_option`, `export_docx_option`), hint 30 hari (`food_export_days_hint`). +3 key baru. |

**File:** `web/src/components/views/HealthFoodView.tsx`, `life_api.py`, `translations.py`, `api_server.py` (`WEB_I18N_KEYS`), `web/src/i18n/messages.json`, `web/public/i18n/messages.json`.

**DoD:** nama makanan/minuman tampil id/en sesuai bahasa ✅; chart weight/height stretch penuh ✅; py_compile + tsc --noEmit + vite build EXIT 0 ✅.

---

## 8. P37 — Love Space: Couple Profile & Couple Account 1:1 ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| j | **Couple profile** (dialog edit profil) tidak 1:1 `_LoveProfileDialog` PyQt (hanya 3 field: nama pasangan/nama sendiri/tanggal) | Dialog profil React kini 1:1: hint `love_profile_both_hint`; kartu **Profil Kamu** (nama, gender male/female, umur, tanggal lahir); kartu **Profil Pasangan** (nama wajib, gender, umur, tanggal lahir); kartu **Relasi** (status hubungan dating/engaged/married/long_distance + mulai bersama); validasi nama pasangan wajib (`love_partner_required`). Backend `_love_map` expose `myGender/myAge/myBirthdate/partnerGender/partnerAge/partnerBirthdate`; `/api/love/profile` menerima + menyimpan field baru (my_gender/my_age/my_birthdate/partner_birthdate) via `db.save_relationship_profile`. |
| j | **Couple account** (modal Tracking Couple) tidak 1:1 `CoupleTrackingDialog` PyQt (hanya ringkasan stat Love) | Endpoint baru `GET /api/love/couple-tracking` (studio_api) membangun summary **11 sub-tab per orang** (Tasks/Sport/Economy/Supplies/Health/Love/Learning/Pomodoro/Music/Reminders/Achievements) untuk saya + pasangan, line di-render server-side via `db.tr_db(lang=…)` (parity `CoupleTrackingDialog._tab_*`; achievement memakai `db.tr_achievement`). Modal React kini render sub-tab bar + 2 kartu per pasangan; fallback `ct_no_couple`. |
| j | Hero banner tidak 1:1 `LovePage.load()` | Hero kini menampilkan `love_couple_format` (nama pasangan + hari bersama), status link (`love_couple_linked`/`love_couple_not_linked` + `love_cloud_realtime`), dan health sync (`love_health_sync` gender+usia dari BMI). `_love_map` expose `linkedPartnerUsername`, `cloudLoveActive`, `healthProfile`. `GameContext.updateLoveSpace` kini me-refresh snapshot loveSpace setelah save (parity `LovePage.load()`). |
| j | i18n | 0 ternary `lang === 'id' ?` tersisa di LoveSpaceView (title/subtitle/badge diganti `t(...)`); semua string baru memakai key existing (`love_profile_*`, `love_type_*`, `ct_*`, `love_health_sync`, dll.) — tanpa key baru. |

**File:** `web/src/components/views/LoveSpaceView.tsx`, `web/src/context/GameContext.tsx`, `web/src/types.ts`, `web/src/api/studio.ts`, `studio_api.py`.

**DoD:** couple profile & account section match PyQt (field, aksi, tampilan data) ✅; py_compile + tsc --noEmit + vite build EXIT 0 ✅; smoke `_couple_tracking_map(0)`→`no_couple`, `_love_map(0)` field lengkap ✅.

---

## 9. P38 — Learning: 3-Tab Slide + Layout Stretch ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| k | **Slide antar 3 tab** (Sources / Chat AI / Studio Generate) belum ada (PyQt pakai slide antar tab) | Implement transisi slide (CSS `transform`/`motion`) antar 3 tab sesuai PyQt. |
| k | Layout kurang rapi & **tidak stretch** saat salah satu tab ditutup | Perbaiki layout: panel yang tersisa melebar penuh (flex-1) ketika tab lain ditutup. |

**File:** `web/src/components/views/LearningView.tsx`, `web/src/index.css`, `translations.py`, `api_server.py`, `web/src/i18n/messages.json`.

**DoD:** 3 tab bisa di-slide; menutup tab → panel tersisa stretch penuh. ✅
- 3 panel selalu di-render (parity `_splitter`); container `flex flex-col lg:flex-row items-stretch`.
- Sources (`lg:w-[280px]`) & Studio (`lg:w-[330px]`) collapse → `lg:w-0 p-0 border-0 opacity-0 invisible` saat ditutup; Chat `flex-1 min-w-0` melebar penuh.
- Slide arah (`ct-slide-in-r` / `ct-slide-in-l`) via `switchPanel` + `PANEL_ORDER`; compact nav mobile memanggil `switchPanel`.
- i18n: 0 sisa `lang === 'id' ?`; +9 key baru; perbaiki nilai `ai_answers_grounded_in_this_notebook_s_sources`; `messages.json` diregenerasi (3440→3681 key).

---

## 10. P39 — Music: Lyrics Live Search (Pomodoro audit) ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| l | Pomodoro sudah 1:1 | Audit saja. ✅ 20 key i18n terpakai, semua ada di `translations.py` + `messages.json`; 0 `lang === 'id' ?`. |
| m | Lyrics search **kurang cepat** & cakupan sempit; lyrics harus **live sync menit/detik** | Percepat + perluas pencarian lirik (`studio_api.get_lyrics` + `_clean_lyrics_query`), tambah fallback provider/query variance, dan render **time-synced lyrics** (highlight baris sesuai posisi pemutaran). ✅ |

**File:** `web/src/components/views/MusicView.tsx`, `web/src/api/studio.ts`, `studio_api.py`.

**DoD:** pencarian lirik lebih cepat & lebih luas; lirik berjalan sinkron dengan waktu musik. ✅
- Backend: `_clean_lyrics_query` diperluas (live/remaster/radio-edit/bracket/ft.); `get_lyrics(artist, title, path)` kini paralel LRCLIB get + LRCLIB search **multi-varian** (artis+judul → judul saja → artis saja) + lyrics.ovh; timeout 6s→5s; fallback **lirik tertanam file** (mutagen, path divalidasi di dalam music dir).
- Endpoint `/api/music/lyrics` menerima `path` (validasi sama dengan `/music/stream`).
- Frontend: drawer lirik diperlebar (`w-72`→`w-80`); tiap baris tampil **timestamp min:sec** (mono); baris aktif putih-bold (parity `_style_lyric_block`), header hijau sumber (web/file); **auto-scroll** garis aktif ke tengah (parity `ensureCursorVisible`).

---

## 11. P40 — Notes / Reminders / Calendar (audit) ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| n/o/p | Diklaim sudah 1:1 | Verifikasi vs PyQt + i18n audit. Perbaiki bila ada gap kecil. ✅ |

**File:** `NotesView.tsx`, `RemindersView.tsx`, `CalendarView.tsx`, `translations.py`, `api_server.py`, `web/src/i18n/messages.json`.

**DoD audit:** ketiga halaman diverifikasi 1:1 vs PyQt (feature/behavior) + i18n dibersihkan.
- `CalendarView` ↔ `CalendarPage` ✅ (12 bulan grid 3 kolom, nav tahun + Hari Ini, header Senin–Minggu, today/holiday/note marker, dialog catatan Save/Delete/Cancel, empty→hapus, holiday tooltip). Sisa `lang === 'id' ? h.nameId : h.nameEn` = **lookup data nameId/nameEn** (diizinkan).
- `RemindersView` ↔ `RemindersPage` ✅ (list 🔔/🔕 + ✅ triggered, add/refresh, edit/delete/toggle/test, dialog lengkap repeat+custom days+sound+browse, validasi title/datetime/past/custom-file/custom-days). Fix: hapus ternary `lang === 'id' ? 'Batal' : 'Cancel'` → `tr('dialog_cancel')`; drop `lang` tak terpakai.
- `NotesView` ↔ `NotesPage` ✅ (folder tree + subfolder + icon + duplikat, search, arsip, count, editor rich text: font size/color/B/I/U/strike/highlight, simbol, superscript/subscript/pecahan/LaTeX, zoom). Fix: 7 tooltip toolbar hardcoded EN → key baru.

---

## 12. P41 — Crafting: Consumable qty 0 memblokir craft ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| q | Bila resep butuh item **consumable** dan qty-nya 0, craft tetap bisa | Cek di backend (`db` craft path) + `CraftView.tsx`: sebelum craft, validasi semua bahan termasuk consumable — bila qty 0 → blokir + toast "bahan tidak cukup". ✅ |

**File:** `api_server.py`, `web/src/context/GameContext.tsx`.

**DoD:** resep dengan consumable qty 0 tidak bisa di-craft (pesan jelas). ✅
- **Root cause:** `api_server._map_inv` memetakan `quantity` dengan `int(row.get("quantity") or 1)` → consumable qty **0** dikirim ke web sebagai **1**, sehingga CraftView menampilkan tag "✅ punya" dan meng-enable tombol craft. Backend `db.can_craft`/`db.craft_item` sendiri sudah benar (membaca qty mentah `inv.get(iid, 0) < 1` → menolak) — jadi klik craft gagal dengan error yang membingungkan.
- **Fix:** `_map_inv` kini `int(qty) if qty is not None else 1` (qty 0 tetap 0; NULL legacy → 1). Berdampak pada snapshot & `/api/inventory`.
- **Fix UX:** `GameContext.craftItem` catch → `notifyApiErr` (toast "damage" dengan pesan server `db_craft_missing` = "Bahan atau gold belum cukup untuk crafting!") menggantikan toast info samar.
- `CraftView.tsx` sudah benar (`invIds` filter `quantity >= 1`; tag material merah `crafting_missing_tag`; tombol `disabled={!ok}`) — kini efektif setelah data qty benar.
- Smoke test: `can_craft` → `{ok:False, missing:['greater_health_potion']}`; `craft_item` → `{ok:False, msg:'Missing materials or gold for crafting!'}`; `_map_inv(qty=0)` → `0`; kontrol resep berkecukupan → `ok:True`.

---

## 13. P42 — Shop: Keterangan Buff + Consumable 0 ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| r | Keterangan **buff item** tidak tampil di subtab Bag/Inventory | Tampilkan deskripsi buff tiap item (dari katalog shop `db`) di baris inventory. ✅ |
| r | Consumable qty 0: tampilkan **0** di shop & bag; beli lagi → qty **bertambah sesuai jumlah dibeli** (bukan reset) | Perbaiki tampilan qty & logika beli (`db.buy_item`/inventory) supaya akumulatif; qty 0 tetap terlihat. ✅ |

**File:** `web/src/components/views/ShopView.tsx`.

**DoD:** buff item menjelaskan efeknya; consumable 0 tampil 0; beli menambah qty. ✅
- **Bag subtab**: baris inventory kini menampilkan `buffDesc`/`buff_desc` item (parity kartu shop `item["buff_desc"]`).
- **Shop items tab**: consumable menampilkan badge `× {qty}` di samping nama (abu jika 0, biru jika >0) — qty 0 terlihat di shop. Bag sudah menampilkan `× 0` (parity P41 `_map_inv`).
- **Beli akumulatif**: `db.buy_item` sudah benar (`quantity=quantity+1` utk consumable; INSERT default 1 saat baris baru; equipment unik ditolak `db_item_already_owned`). Diverifikasi smoke test: 3× beli → qty 3; pakai habis → 0; beli lagi → 1 (bukan reset).
- Guard UX: tombol Sell di Bag di-disable saat `qty < 1` (backend `sell_item` menolak `db_item_insufficient_quantity`).
- i18n: buff bar ShopView hardcoded → `buff_bar_title` + `buff_bar_empty` (key sudah ada).

---

## 14. P43 — Pets: Slot Equip Bertingkat + Recalc Buff ✅ DONE (2026-09-03)

| Sub | Issue | Aksi |
|-----|-------|------|
| s | Fitur baru: **level >25 dan kelipatan 5 di atasnya** bisa equip +1 pet lagi | Ubah `database.py: equip_pet()` — `max_pets = 1` (level<25), lalu `2 + floor((level-25)/5)` untuk level ≥ 25 (25→2, 30→3, 35→4, dst.). ✅ |
| s | Jangan lupa **recalculate buff** | Panggil `recalculate_all_buffs()` setelah equip/unequip (sudah ada). ✅ |

**File:** `database.py`, `api_server.py`, `MainPyQt6.py`, `web/src/context/GameContext.tsx`, `web/src/components/views/PetsView.tsx`, `translations.py`, `web/src/i18n/messages.json`.

**DoD:** jumlah pet aktif mengikuti level; buff ter-recalc otomatis. ✅
- `database.py`: helper baru `max_active_pets(level)` (1 di bawah 25; `2 + (level-25)//5` utk ≥25) dipakai `equip_pet` (menggantikan `2 if >=25 else 1`). `recalculate_all_buffs()` sudah dipanggil equip/unequip.
- `api_server.py`: snapshot mengekspos `maxActivePets` (dihitung backend) — TS tidak menduplikasi rule.
- `MainPyQt6.py` PetsPage: display `max_pets` → `db.max_active_pets(user_level)` + status `pets_max_n`.
- React: `GameContext` state `maxActivePets` (snapshot + applyLive); `PetsView` memakai nilai backend + status `pets_max_n` (`{n}`), hapus hardcode `lang==='id'` judul adopsi → `adoption_sanctuary`.
- i18n: +1 key `pets_max_n` ("✅ bisa {n} pet").
- Smoke: formula 1/24→1, 25/29→2, 30/34→3, 35→4, 40→5, 55→8; level 30 equip 4 pet → 3 aktif (tertua diganti); level 24 → 1 aktif.

---

## 15. P44 — Friends: Chat 1:1 PyQt  ✅ DONE (2026-09-04)

| Sub | Issue | Aksi | Status |
|-----|-------|------|--------|
| t | Pesan chat tidak **real-time** dengan waktu/tanggal user saat ini | Server clock `clockNow()` (optimistic) + timestamp server (`created_at`); auto-refresh `setInterval 3s` (parity `QTimer 3s` PyQt). | ✅ |
| t | Chat pertemanan **tidak selengkap PyQt** | Full `ChatDialog` parity: reply, edit, delete, reactions (👍❤️😂🎉😮😢) + remove, load earlier **50/page**, clear chat (lokal; cloud diblokir), download attachment, attachment upload (≤5), typing indicator (cloud), placeholder input. | ✅ |
| t | Attachment upload **di-wire ke Supabase storage** (keputusan user) | **Hybrid** seperti PyQt: cloud-linked + friend punya `cloud_user_id` → `get_or_create_direct_conversation` + `send_direct_message_with_attachments` (upload Supabase storage, fallback pending+enqueue sync); else local BLOB `prepare_chat_attachment` + `link_local_chat_attachments`. Download: cache lokal → fallback `download_chat_attachment` dari Supabase storage. | ✅ |

**File:** `studio_api.py` (helpers `_cloud_chat_context`/`_cloud_service_for_user`/`_refresh_cloud_chat`/`_load_chat_payload`/serializer + endpoint hybrid send/clear/edit/delete/react/typing/attachment/discard), `api_server.py` (route download binary `/api/friends/attachments/{id}/download` + owner-check), `web/src/api/client.ts` (`apiGetBlob`), `web/src/api/studio.ts`, `web/src/components/views/FriendsView.tsx`.

**DoD:** chat teman real-time + fitur lengkap 1:1 PyQt (hybrid cloud/local). ✅

- Backend chat GET (`/api/friends/{id}/chat`) kini hybrid: `cloudMode` bila linked (refresh 50 + reactions + attachments + mark-read + typing), else `db.get_messages` (limit default 50, cap 2000).
- Edit/delete/react/clear menerima flag `cloud`; key `pending:` diblokir (`chat_pending_action_blocked`).
- Attachment prepare memakai ulang `cloud_service.prepare_chat_attachment` (validasi mime/ukuran + image→WEBP + thumbnail) — aturan tidak diduplikasi di TS.
- React: `chatCloudMode` + `friendTyping` + `pendingAttachments` state; hardcode `lang==='id'` (load-earlier + claim PvP) diganti `tr()`; placeholder `chat_input_placeholder`; auto-scroll.
- i18n: **0 key baru** (semua key `chat_*`/`cloud_chat_typing`/`chat_pending`/`claim` sudah ada).
- Smoke (local): send/reply/edit/react/delete/clear/typing OK; attachment PNG → `pixel.webp` (image/webp) + thumbnail, send-only-attachment → teks `📎 Attachment`, linked `local_message_id`, discard menghapus BLOB; download owner-check OK. Cloud path belum teruji end-to-end (Supabase tidak terkonfigurasi di sandbox) — code menyalin panggilan PyQt `ChatDialog` persis.


---

## 16. P45 — Guild: Chat, Spyglass, Info Serangan Boss  ✅ DONE (2026-09-04)

| Sub | Issue | Aksi | Status |
|-----|-------|------|--------|
| u | Guild chat **kadang tidak terkirim** + belum lengkap | Akar bug: `POST /api/guild/messages` mengirim ke guild ONLINE (cloud) padahal halaman React menampilkan guild LOKAL → pesan tampak hilang. Diubah jadi **lokal-only** (parity `GuildChatDialog._send_message`). Chat guild jadi dialog penuh parity `GuildChatDialog` lokal: send + clear-all (leader) + poll 3s + format `[HH:MM] name: msg` + admin-block. | ✅ |
| u | **Spyglass** tidak terimplementasi (equip/unequip tak ada efek) | Info boss di selector kini **di-gate `hasSpyglass`** (parity `_update_boss_info`): dengan spyglass → `guild_boss_info_format` penuh (HP/ATK/XP/Gold/Min Level) + `🔭 guild_spyglass_detail`; tanpa spyglass → hanya ikon+nama+[tier] + `Min Level: X ✅/🔒` + hint `guild_spyglass_buy_hint`. (Flag `has_spyglass` sudah direcalc backend oleh equipment, lihat buff recalculation.) | ✅ |
| u | Tidak ada keterangan **damage & HP yang diblok** + info serangan saat menyerang boss | Modal hasil serangan penuh parity `_perform_action`: victory (`victory_title` + `extra_effect`), block (`boss_block_title`/`boss_block_result`), spyglass (`boss_attack_spyglass` + boss HP sisa + counter-damage + critical), no-spyglass (`boss_attack_no_spyglass` + `actual_damage`), + `boss_block_active_info` / `boss_reduction_info` / `boss_shield_used` / `attack_totem_revive` / effect ultimate. | ✅ |
| u | Tombol mulai boss | Parity `_boss_selector`: start boss **leader-only** (`guild_start_boss`; non-leader disabled `guild_only_leader`); judul boss aktif pakai `boss_title_format` (ikon+nama+[tier]) dengan warna tier; filter tier + `cboss_custom_tag`; dialog custom boss memakai key `cboss_*`. | ✅ |
| issue#1 | Chat friends (dan guild) **tidak realtime** dgn jam user (skew 7 jam) | Helper `fmtChatTime` di `web/src/utils/serverTime.ts`; **fix final pasca-P46**: backend mengirim `epoch` (unix detik absolut) per pesan (local/cloud/guild) via `_ts_epoch()` di `studio_api.py`, frontend merender `epoch` di zona browser user — chat & jam app selalu sinkron di zona LOKASI USER berapa pun zona server. | ✅ |

**File:** `web/src/components/views/GuildView.tsx` (rewrite boss section + chat dialog + i18n cleanup), `web/src/utils/serverTime.ts` (`fmtChatTime`), `web/src/components/views/FriendsView.tsx` (timestamp via `fmtChatTime`), `web/src/api/studio.ts` (`guildChat` GET), `web/src/types.ts` (`bossIcon`/`bossTier`), `studio_api.py` (GET `/api/guild/messages` + POST lokal-only + `_guild_map` bossIcon/bossTier), `api_server.py` (WEB_I18N_KEYS +5), `translations.py` (+5 key), `web/src/i18n/messages.json` + `web/public/i18n/messages.json` (regenerated 3694 keys).

**DoD:** chat guild reliable (lokal, tampil seketika) + lengkap (dialog + clear + poll); spyglass mengubah tampilan info boss; tiap serangan menampilkan info damage/blok/HP lengkap; timestamp chat WIB realtime. ✅

- Smoke: `POST /api/guild/messages` → `{ok:True}` + `skip_snap`; `GET /api/guild/messages` → messages + `isLeader`; `_guild_map` → `bossIcon`/`bossTier`.
- Verifikasi: `py_compile` OK (translations/api_server/studio_api/cloud_service/cloud_api/database); `tsc --noEmit` OK; `vite build` OK.
- i18n: **+5 key** (`guild_spyglass_buy_hint`, `guild_boss_min_level`, `guild_no_boss`, `guild_chat_send_fail`, `guild_chat_send_ok`).

---

## 17. P46 — Verifikasi Final + Commit + Laporan (format 1–7)  ✅ DONE (2026-09-04)

1. Full regression: `py_compile` semua modul inti; `tsc --noEmit`; `vite build`. ✅
2. Smoke test backend (endpoint GET/POST inti) + cek i18n konsisten (key id+en). ✅
3. **Satu commit** phase P30–P46. ✅ (`0d3b301`)
4. Buat **laporan update format 1–7** (lihat §6) sebagai kesimpulan keseluruhan commit phase. ✅ (di chat)

**Fix tambahan (dibundle user sebelum P46) — jam app timezone mengikuti lokasi user:**
- Akar bug: `serverNow.tzOffsetMin` bergantung zona proses server (Asia/Jakarta via `time.tzset()`, yang **no-op di Windows** → tzOffsetMin=0 → jam tampil UTC, mis. 06:00 padahal 13:18 WIB).
- Fix: `Navbar.tsx` merender jam dari **zona browser (lokasi user)** — `clockNow()` tetap instan UTC sinkron server, field `.getHours()` dst. dibaca di zona browser. `serverTime.fmtChatTime()` kini default pakai **offset zona browser** (param `tzMin` jadi opsional); `FriendsView`/`GuildView` memanggil `fmtChatTime(m.createdAt)`.
- Verifikasi simulasi (TZ=Asia/Jakarta): jam 13:18:00, chat zoned `06:18+00:00`→`13:18`, naive `13:18`→`13:18`.

**Fix lanjutan (pasca-P46, laporan user) — chat friends/guild kembali sinkron dgn jam user:**
- Akar bug: timestamp pesan **lokal** disimpan sebagai string naif zona server (`datetime.now().isoformat()`), sehingga setelah jam app pindah ke zona browser, slice mentah `[11:16]` menampilkan jam server (bukan jam user) bila zona server ≠ zona browser.
- Fix: `studio_api.py` menambah helper `_ts_epoch()` + field `epoch` (unix detik absolut) di `_local_message_payload`, `_cloud_message_payload`, dan GET `/api/guild/messages`. `fmtChatTime(iso, epochSec)` memprioritaskan `epoch` → render `HH:MM` di zona browser user (sama persis dgn jam app); fallback ISO ber-zona/naif tetap ada.
- Verifikasi: round-trip naive↔epoch konsisten di server UTC maupun WIB (epoch sama utk instan sama); node render `epoch → 13:57 WIB` benar; smoke API: guild & friends chat GET mengembalikan `epoch` benar.

**Hasil verifikasi P46:**
- `py_compile *.py` — OK (18 modul).
- `tsc --noEmit` — OK (exit 0). `vite build` — OK (2441 modul).
- i18n: 3694 key `translations.py` ↔ `messages.json` (id=en set identik, 0 missing); `WEB_I18N_KEYS` (3585) semua ada di translations.
- Smoke HTTP: `/api/health` OK; register→login→`/api/bootstrap` (serverNow + user) OK; create guild OK; POST+GET `/api/guild/messages` OK (isLeader + pesan tampil); `/api/guild` (bossIcon/bossTier/members) OK; `/api/guild/bosses` (16 boss) OK. DB smoke dibersihkan setelahnya.

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
