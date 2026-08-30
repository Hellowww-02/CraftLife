
## P9 — Friends → Guild (issue #3, deepest audit) — progress sesi

### Audit temuan utama
1. `/api/guild/boss/attack` hardcode action="light" → PyQt 4 aksi (light/heavy/block/ultimate). FIXED (baca body.action, whitelist).
2. Rute start boss/team raid HILANG → identik issue #3 "raid team/attack MUST work". ADDED POST `/api/guild/boss/start` (bossId + teamIds, leader auto).
3. Rute skill class (`db.use_class_skill`)? — dicek: belum ada → ADDED POST `/api/guild/skill`.
4. Quick heal golden apple (`_quick_heal`) → ADDED POST `/api/guild/quick-heal`.
5. Unclaimed rewards (`_show_unclaimed_rewards` + `_claim_reward`) → ADDED GET `/api/guild/rewards` + POST `/api/guild/rewards/{id}/claim`.
6. `_guild_map` diperluas: bossAttack, bossParticipants, buffXp/Gold/Damage/critChance, member hp/maxHp/avatarEmoji.
7. FriendsPage: unread count → `_friends_map` memakai `get_unread_count_between`/`get_cloud_unread_count` (deskripsi tombol belum pakai badge — chat dialog basic sudah lewat GlobalChat; per-friend ChatDialog TBD P9 lanjutan).
8. FriendsPage batch: coupleStatus + presence fields → ADDED ke _friends_map (get_couple_status_between + get_cached_presence).
9. Register: avatarClass+bio (PyQt _register_tab combobox class) — api_server register route tidak meneruskan ke db.register_user → FIXED (dilanjutkan avatar_class & bio) + routed katalog `/api/catalog/avatar-classes` (baru) + `/api/catalog/class-skills` (baru). LoginView: combobox kelas+bio (parity).
10. Admin block Guild/Friends lokal (parity load()) → ditambahkan di GuildView & FriendsView (ui gates).

### Verifikasi
- DB direct: 4-role start solo/team, 4 aksi, non-participant ditolak ✓; rewards auto-post + claim ✓; use_class_skill ✓; golden_apple missing item ✓; transfer leadership ✓; couple full lifecycle (request → accept → status accepted → end → 'cancelled') ✓; unread/mark_read ✓; send/get messages ✓; PvP challenge→accept (status active, days_left=7)✓; friend request→accept→friends ✓.
- HTTP api_server: register avatarClass (mage ✓), /api/guild/boss/start ✓, attack heavy ✓, ultimate MP check ✓, skill ✓, quick-heal no-item ✓, rewards lifecycle ✓, catalog avatar-classes/class-skills ✓, friend chat send/read ✓ (chat "non-friend" = empty msg per db), couple/pvp endpoints via studio_api ✓.
- `cd web && npx tsc --noEmit` ✓ ; `npm run build` ✓ (setelah SocialGuildView dihapus, TS di App untuk attackGuildBoss(25) hilang).

### Catatan penting
- `SocialGuildView.tsx` DIHAPUS (file dead; tidak di-route). Pengganti: rewrite GuildView + FriendsView (parity FriendsPage/GuildPage untuk guild-lokal; online-guild cloud dianonimkan/dideferred per pola P7/P8 cloud-skip).
- i18n: tambahan kunci ke WEB_I18N_KEYS (P9 friends/guild batch, register_batch, chat batch) — lihat diff. `messages.json` di-sync dari translations.py (id dariTRANSLATIONS, en dariTRANSLATIONS).
- Struktur provider: `GameContext` kini exposes `activeBuffs: string[]` dari snapshot (`db.get_all_active_buffs`) utk Shop buff bar parity.
