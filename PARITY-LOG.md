
## P7 — Notes → Reminders → Calendar (2026-08-30)

### Notes (REWRITE NotesView, parity NotesPage)
- Server (life_api.py): +GET `POST /api/notes/math-chunks` (find_math_chunks→[{raw,converted}], skip_snap); +`POST /api/note-folders/{id}/update` (name→update_note_folder; icon-only→update_note_folder_icon); +`POST /api/note-folders/{id}/duplicate` (duplicate_note_folder).
- Web NotesView (~600 ln): header archive/show-archived, search, toolbar (folder/note/duplicate/to-learning/delete), tree rekursif (All=-1, NoFolder=0, expand/collapse-all, hover: subfolder/rename/edit-icon/duplicate/delete + emoji icon picker + rename modal), list filter (subtreeIds folder rekursif + search title/content + archived), ↑↓ reorder (folder>0 & tanpa search), editor: format toolbar (bold/italic/underline/strike/fontSize/colors), sup/sub, fraction (seleksi/modal), Σ dropdown, ∑ LaTeX (selection/all via previewMath, preview via mathChunks), zoom 50–200 display-only (TIDAK persist — parity `_on_zoom_changed`), SAVE MANUAL + dirty '*', send-to-learning → notebook picker.
- Key parity data: Tidak ada autosave di PyQt (hanya dirty flag); delete folder = 1 row (FK SET NULL); fraction HTML `<span style=...><sup>n</sup>/<sub>d</d></span> `.

### Reminders (REWRITE RemindersView + backend fix)
- **Backend bugs fixed**: map_reminder `isActive` salah (pakai `not triggered` → sekarang kolom `is_active`); repeat filter 'weekdays' (tidak ada di PyQt) → none/daily/weekly/custom; tambah description/datetime/repeatDays/triggered/soundFile; add route sekarang menerima reminderDatetime/soundType/soundFile/repeatDays penuh; `.toggle` lama men-flip `triggered` (SALAH) → sekarang flip `is_active` + reset triggered saat aktif (parity `_toggle_selected`); +`POST /api/reminders/{id}/update` (parity ReminderDialog._save, triggered=0); +`GET /api/reminders/due` (get_pending_reminders) + `POST /api/reminders/{id}/trigger` (get_next_reminder_datetime advance / mark triggered — logika jadwal tetap di Python).
- Web: dialog add/edit penuh (title, desc, date+time, repeat + custom day checkboxes Sen–Min, sound default/beep1/beep2/custom + **browse MP3 → apiUploadFile('reminder_sound')** — issue #4), konfirmasi waktu-lampau, validasi parity; list 🔔/🔕 + waktu + ✅; edit/delete(confirm)/toggle/test buttons; test dialog (suara loop/play → OK menghentikan, parity _test_selected).
- Scheduler GameContext ditulis ulang: poll /api/reminders/due tiap 10 detik → alarm loop global (beep tiap 2 detik / MP3 loop via /music/stream — parity `_play_reminder_*_loop`) + modal OK global di provider → POST /trigger per reminder (server reschedule). Modal Pomodoro alert dipertahankan (z-index alarm 95).
- sound.ts: beep1=600/200+800/200, beep2=400/300+600/300+800/300 (parity `_play_sound`), +startReminderLoop/stopReminderLoop.

### Calendar (REWRITE CalendarView)
- Server: `/api/holidays?year=` kini mengembalikan 3 tahun (y-1,y,y+1) — parity `_fetch_holidays`; `/api/calendar/note` kosong→delete (parity `_save_note`); +`POST /api/calendar/note/delete`.
- Web: tampilan SATU TAHUN 12 bulan grid 3 kolom (bukan month-nav — parity `months_grid`), aksi ◀ tahun ▶ + label + `food_today`; sel hari: today (primary+accent border), holiday (teks merah + tooltip 🏷️ nama), note (📝 + border accent); klik hari → dialog (info holiday, label, textarea, Save/Delete/Cancel — parity `_open_note_dialog`); deleteCalendarNote di context.

### i18n
+68 key reminders_*/day_* + msg/confirm/dialog ke messages.json & WEB_I18N_KEYS; +15 key month_01..12/btn_cancel/page_calendar_* (total messages.json sekarang ~810 key id+en).

### Verifikasi
tsc --noEmit ✓; vite build ✓ (dist diperbarui); smoke in-process ✓: math-chunks→[(raw,converted)]; folder update/duplicate ok; reminder add(past)→due→trigger(next=+1 hari)→toggle off(0)/on(reset triggered)→update(full field termasuk custom sound file); calendar save-strip / 372 holiday (2025–2027) / save-kosong=delete / delete route.

## P8 — Crafting → Shop → Pets (2026-08-30)

### Crafting (CraftView rewrite)
- PyQt CraftingPage langsung list `db.get_crafting_recipes()` — web SEBELUMNYA pakai katalog tanpa desc resep.
- Server: `_recipe_catalog` += `descId`/`descEn` (tuple `r["desc"]`) — parity lang-aware desc.
- View: desc per bahasa, buff (`output_buff`), materials dgn tag `[crafting_have_tag]/[crafting_missing_tag]` (light/#e05050), `crafting_gold_cost` (gold/#e05050) + `crafting_gold_short`, `crafting_owned` (max 1 per resep, tombol diganti label), tombol `crafting_btn` enabled iff can_craft.

### Shop (ShopView rewrite total)
- Web lama: tab shop/inventory (tidak ada di PyQt), tanpa pets tab, label jual "+40%" (SALAH — server 10%), tanpa buff bar, tanpa seasonal visibility filter, tanpa dialog qty.
- Server: `_shop_catalog` += `visible` (db.is_shop_item_visible — craft_only tersembunyi, seasonal hanya saat event window) + `seasonal`; +routes `GET /api/catalog/enchant` (maxLevel 5, baseXp 50) & `GET /api/buffs` (get_all_active_buffs).
- View parity: buff bar `⚡ Buff Aktif`; QTabWidget Items/Pets; items grid 4 kolom: icon/nama/`shop_seasonal_badge`/buff_desc/`shop_type_{type}`; owned → `shop_owned`; consumable → `shop_use({qty})` + `shop_buy_again` + Sell + `shop_sell_price` (max(1, cost*10%)); non-consumable → Sell + price + blok enchant (`enchant_level_tag`/`enchant_max_tag`/btn `enchant_btn`/`enchant_first_btn` dengan cost (lvl+1)*50 XP, precheck XP client parity `_enchant`); belum dimiliki → 💰 cost + `shop_buy`. Pets tab: `shop_active` + `shop_unequip`/`shop_equip`, atau 💰 cost + `shop_adopt`. Dialog jual parity `_sell_item` (qty slider 1..max + total live + konfirmasi akhir 2-langkah) → POST quantity (rpg.sellItem(itemId, qty)).

### Pets (PetsView rewrite)
- Drift diperbaiki: exp needed `level*100` (bukan 60), feed 30G (bukan 15), train `25+(lvl-1)*5` GOLD (bukan 15 MP — salah besar UI lama).
- Parity tambahan: info card `pets_active_info` (max 2 pet @ level ≥25, status `pets_max_1/2`), hunger bar amber `pets_hunger`, buff lines terskala `1+(lvl-1)*0.1` (`pets_buff_{xp,gold,dmg,reduc}_format` — format python `{val:.0f}` ditangani helper tr regex), `pets_empty`, grid 3 kolom, tombol equip/unequip + feed(train labels parity). Adoption market dipertahankan (parity ShopPage tab Pets bagian unowned).
- context: `unequipPet(petId?)` parity per-pet (fallback pet aktif); `sellItem(itemId, qty)`.

### i18n
+98 key (shop_*, enchant_*, crafting_*, pets_*, pet_*, db_enchant/db_pet/db_gold_insufficient, page_shop/pets/crafting_*) → messages.json + WEB_I18N_KEYS.

### Verifikasi
tsc ✓; build ✓; smoke db ✓: sell 2×=10%×2 gold; feed −30g hunger→100; train −25g(lvl1); equip/unequip; enchant −50 XP lvl1; can_craft+craft_item+duplikat ditolak ("already own"); katalog 59 item dgn visible/seasonal flags (seasonal=False di luar window — parity).
CATATAN: PyQt tidak punya UI equip ITEM (hanya pet) — kolom inventory.equipped hanya dipakai jalur cloud; web diserahkan sama (tanpa tombol equip item).
## P9 — Friends → Guild (audit terdalam) — 2026-08-30

- Server route baru: guild boss start (solo/team + teamIds filter), 4-aksi attack (action whitelist), guild skill, quick-heal, rewards list+claim, `/api/guild/bosses`, GET `/api/pvp`, friend chat GET/POST (mark-read, replyToId, editedAt/deletedAt/reactions), messages edit/delete/reaction, friends/{fid}/clear, catalog class-skills + avatar-classes. Fix: attack sebelumnya hardcode "light"; `import re` top-level di runtime route baru.
- `_guild_map` diperkaya: bossAttack/bossParticipants/buffXp/buffGold/buffDamage/critChance + member avatarEmoji/hp/maxHp; `_friends_map` +coupleStatus/presence/unreadCount; `_pvp_map` +winnerId; `_row_user` +hasSpyglass/bossDamageBonus/hpDamageReduction/mpBonus; register REST terima avatarClass+bio (sebelumnya paksa warrior).
- GuildView.tsx rewrite penuh (stats 6 kartu, member HP bar + 👑, 4-aksi boss + tooltips + quick heal saat HP 0, selector boss + tier filter + **dialog tim raid (filter level, maks 4+leader)**, custom boss dialog, skill bar, rewards popup, invites/join requests accept-reject, edit bio, chat, confirm leaves/transfer, admin gate, **spyglass info branch**).
- FriendsView.tsx rewrite penuh (admin gate, pending accept/reject, couple requests in/out accept/reject/cancel, status+p presence+unread per teman, End couple hanya accepted, chat dialog penuh: reply/edit/delete/react/clear/earlier/polling 3s, profile modal, PvP lengkap: none/pending_in accept+decline/pending_out/active score/finished win-lose-tie).
- SocialGuildView.tsx DIHAPUS (dead code, tipe break).
- LoginView: combobox kelas + bio (parity register PyQt).
- ShopView: perbaikan harga jual parity (max(1, int(10%))), sesi sebelumnya.
- i18n: ~330 key tersinkron (guild_*/friends_*/pvp_*/couple_*/raid_*/presence_*/chat_* + register_*) → messages.json + WEB_I18N_KEYS.
- Verifikasi: tsc ✓, build ✓, py_compile ✓. Smoke HTTP end-to-end: guild create→bosses(16)→start→4 aksi→kill→reward claim; raid team start+serang member; transfer leadership; couple request→accept→couple→end; pvp challenge→accept→active; chat send/reply ✓/edit ✓/react dua arah ✓/remove ✓/delete ✓/clear satu sisi ✓ (self 0, lawan tetap 3).
- Sisa terdokumentasi (bukan 100%): cloud guild chat (reaction/edit/delete jalur cloud Supabase) — konsisten dengan penundaan cloud P7–P8; UI cloud-online guild/GuildListDialog.


---

## P10 — Achievement → Leaderboard → Settings (2026-08-30)

### Sistem yang berubah
1. **Achievement**:
   - `_map_ach` (api_server) sekarang melokalisasi title/desc via `db.tr_achievement(ach, lang_user)` — parity AchievementPage PyQt yang SELALU pakai tr_achievement (bukan kolom DB). Field asli tetap ada (`rawName`/`rawDesc`).
   - `AchievementsView.tsx` di-rewrite penuh: search input (`achievement_search`), combo kategori (all + 15 kategori `achievement_category_*`), grid kartu 3 kolom (lg), progress bar + format `achievement_progress_format` `{progress} / {req} ({percent}%)`, reward `achievement_reward_format`, status: `achievement_locked` / `achievement_unlocked` + tombol `achievement_claim` (route POST `/api/achievements/{id}/claim` sudah ada) / `achievement_claimed`, empty `achievement_empty`.
2. **Leaderboard**:
   - Route `/api/leaderboard`: title key → nama terlokalisasi (helper `_leaderboard_title_loc` dari db.TITLES, lang user) + field `partner` dari `db.get_couple_partners_map()`.
   - `LeaderboardView.tsx` rewrite: combo mode urutan PyQt (cloud_productivity / cloud_guild / local, opsi `cloud_leaderboard_*`), tabel lokal 7 kolom dengan header `leaderboard_col_*`, sport `Lv.n` kuning + rebirth oranye (parity warna), 💞 pink couple dengan tooltip `leaderboard_partner_tip`/`leaderboard_single_tip`, medal 🥇🥈🥉; mode cloud di-render nyata (rank · user/guild · points/exp · events/members, header `leaderboard_rank/guild`, `cloud_leaderboard_points/events/exp/members`) — bukan placeholder; fallback lokal bila belum linked (persis PyQt).
   - Route baru `GET /api/cloud/leaderboard?mode=...` di cloud_api (guarded link + ensure_session): memanggil `get_online_guild_leaderboard(50)` / `get_global_productivity_leaderboard(30,50)`.
3. **Settings**:
   - Route baru: `GET /api/catalog/themes` (db.THEMES: key/label/primary/glow), `GET /api/catalog/avatar-classes` (db.AVATAR_CLASSES), `GET /api/version` (APP_VERSION updater + DB_PATH), `GET /api/update/check` (updater.check_for_update best-effort), `POST /api/settings/backup` (db.backup_database), `POST /api/admin/debug` (8 aksi, gated is_admin → 403 `not_admin`): add_xp/add_gold (db.gain_xp_gold), fill_hp_mp (db.update_user), max_level (Σ lvl×150 → 50), complete_tasks (habit/daily/todo), pet_level_up/add_exp/feed (db.admin_*).
   - `SettingsView.tsx` rewrite penuh sesuai urutan PyQt: Theme radios (preview dot glow, restart-prompt konfirmasi) → Sound (checkbox + hint) → Currency (hanya IDR/USD/EUR — buang SGD/JPY yang tidak ada di PyQt) → Language id/en + restart prompt → A11y (font scale kombo 80–140 step 10, high contrast, hint) → Admin panel (keys admin_*, warning) → Data management (export/import tracker JSON, import confirm `import_confirm_warning`, admin diblokir dengan `admin_export/import_blocked`, tombol Backup Sekarang) dengan warning reset → Reset Progress (password verify `reset_verify_password_*` → dialog ketik "RESET PROGRESS" `reset_confirm_*` → `reset_success_*` → reload) → Update group (versi + cek update) → DB group (path DB + backup). Kelas karakter select sekarang dari `/api/catalog/avatar-classes` (bug sebelumnya: paladin/ranger yang DOESN'T exist di db diganti; opsi fallback = 5 kelas asli db). Seksi cloud sync yang sudah ada dipertahankan penuh.

### Translate keys
- Disinkron ke translations→WEB_I18N_KEYS→messages.json: 166 key batch settings/reset/admin/a11y/update/import/export + 18 achievement_*(kategori/format) + 10 leaderboard/cloud_leaderboard + 8 key baru (web_hero_*, web_profile_saved/save, reload_now_confirm). Key BARU yang ditambah ke TRANSLATIONS: web_hero_custom/avatar/name/class/bio, web_profile_saved, web_profile_save, reload_now_confirm.
- Total messages.json id sekarang 1474 keys.

### Verifikasi
- `py_compile` api_server/cloud_api/translations OK; `tsc --noEmit` OK; `npm run build` OK (6.16s).
- Smoke HTTP sandbox port 8769: `/api/version` 1.4.0+dbPath ✓; themes 7 item + glow ✓; avatar-classes 5 ✓; achievements title/desc EN dari tr_achievement (desc "Defeat 1 boss" vs rawDesc ID) ✓; leaderboard partner field ✓; backup membuat file `backups/craftlife_backup_20260830_100037.db` ✓; admin/debug non-admin → 403 not_admin ✓; set is_admin=1 → fill_hp_mp/add_gold(+250)/pet_feed sukses + msg lokal ✓ (kemudian dikembalikan 0); update/check ✓; cloud/leaderboard unlinked → `{linked:false, rows:[]}` ✓.

### Belum / deferred
- Tema dipersist + preview dot & restart-prompt; skin CSS penuh 7 tema PyQt belum diterapkan ke Tailwind (data-level parity, visual theme = PARTIAL, dicatat untuk P11).
- Cloud leaderboard membutuhkan .env Supabase (latar historis fase ini: cloud opsional), route terbukti via guard unlinked.
- WEB env build node_modules tidak dipersist; npm install diulang tiap sesi (bekerja normal).


---

## P11 — FINAL RE-AUDIT & COMMIT (2026-08-30)

### Re-audit hasil
1. **Route coverage**: 268 path `/api/*` yang dipakai frontend diperiksa satu per satu — semua terpetakan ke backend (api_server / life_api / studio_api / cloud_api). 8 flag awal adalah false-positive (import path + template literal `api/ai/${kind}`, `couple/${id}`, `supplies${q}`) yang diverifikasi manual ada handler-nya.
2. **i18n re-audit**: ditemukan 41 key `t()` yang belum ada di messages.json → diselesaikan: 17 key baru (notes_*/pomodoro/web_backup_code/web_forgot_password) ditambah ke `translations.py` (id+en) sesuai fallback view; sisanya disinkron dari translations.py (key statis Login/Sport/Supplies + prefix dinamis food_*/health_*/sport_*/task_difficulty_*). WEB_I18N_KEYS +39, messages.json sekarang 1549 key · hasil scan ulang: **0 missing**.
3. **HTTP smoke GET final** (32 route aktual dari web/src/api): 31/32 OK; satu-satunya yang "gagal" adalah `/api/cloud/devices` → 400 `auth_required`, yang BENAR untuk akun belum ter-link cloud (frontend menangani kondisi ini).
4. **9 known issues**: semua terbukti di kode + smoke: currency util (currency.ts dipakai Economy+Supplies), gold reward pipeline, guild raid/attack+bosses, reminders MP3 upload '/api/upload/file', notes full parity (latex via server), music import/playback, pomodoro persisten+pomoAlarm, love gallery (albums/photo), healthfood reconstruct.
5. **Placeholder/TODO scan**: bersih (grep TODO/FIXME/mock/dummy/sample hanya menemukan kode fungsional).

### tsc / build
`tsc --noEmit` OK · `npm run build` OK (≈5–6s).

### Catatan jujur (tidak diklaim 100%)
- Fitur cloud-Supabase (leaderboard cloud, guild/friend chat cloud, sync): diuji hanya dalam kondisi unlinked/auth-guard; butuh .env kredensial live. Status = PARTIAL terdokumentasi juga di fase P7–P10.
- Skin visual 7 tema: data-persist + preview dot di Settings (PARTIAL visual; Tailwind tidak memetakan semua tema).
- Integrasi eksternal (AI Gemini, download music): guard 'unconfigured' ada; tidak diverifikasi dengan kredensial live di sandbox.

### Keputusan akhir
28 backend .py (api_server, life_api, studio_api, cloud_api, translations) + 30+ view React dimigrasikan bertahap P2–P11. Commit tunggal dilakukan SETELAH re-audit ini sesuai aturan: `feat: complete PyQt to React 1:1 parity migration`.
