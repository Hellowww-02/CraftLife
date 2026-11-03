# M15 — Cloud-first: HP ↔ Supabase langsung (tanpa PC)

Status: **selesai dari sisi sandbox (2026-11-02), bukti live menunggu `db push`
+ uji perangkat pengguna.** Satu commit fase; rincian tahap ada di roadmap.

## Apa yang berubah

### M15a — Aturan main di Postgres (RPC)
`supabase/migrations/20261102000000_phase_m15a_cloud_first_rules.sql`:
17 fungsi (`m15_*`) memindahkan aturan `database.py` apa adanya —
`gain_xp_gold` (mesin XP/gold/level + buff skill + admin ×5), `lose_hp`
(termasuk totem revive), `penalize_gold`/`penalize_xp`, `complete_habit`,
`complete_daily`, `fail_daily` (freeze → HP → gold → XP), `add_freeze_to_daily`
(ice_block), `complete_todo`, `complete_sport_activity` (+ kurva sport
level×100), `complete_pomodoro` (1 XP/menit, gold menit//5), dan
`apply_late_debt_penalty` (clamp 10..100).

**Utang S4 dibayar:** kurva level dompet (`wallet_level_for_xp`) diganti dari
placeholder `sqrt(xp/100)` menjadi kurva desktop (threshold kumulatif
`150·L·(L-1)/2`) — satu kebenaran untuk desktop & cloud.

### M15b — Mode cloud di Android
- `src/cloud/supabase.ts` — klien PostgREST/GoTrue (fetch murni, tanpa
  dependensi baru). Kredensial: `EXPO_PUBLIC_SUPABASE_URL` +
  `EXPO_PUBLIC_SUPABASE_ANON_KEY` (publik by-design; RLS yang menjaga).
- `src/cloud/backend.ts` — router `cloud://api` yang mempertahankan bentuk
  respons `api_server.py` (mapper `_map_habit/_map_daily/_map_todo` disalin
  dari sumber) + shim global fetch.
- `src/cloud/mode.ts` + Settings → **Sumber Data (Cloud / Desktop)** + login
  email/kata sandi Supabase dari aplikasi.

### Yang JALAN di mode cloud hari ini
Identitas (`/api/me`), jam server, daftar **Habits / Dailies / Todos**
(bentuk respons sama dengan desktop), dan SEMUA aksi aturan: complete/fail
habit, complete/fail/freeze daily, complete todo, complete sport,
pomodoro, plus hadiah XP/gold/level/HP/MP penuh.

### Yang sementara mode Desktop (jujur, `cloud_pending`)
Sosial (teman/chat/guild/PvP/leaderboard), Love, Music, Learning, Calendar,
Supplies/Economy/Notes/Reminders CRUD, Health/Food — endpoint-nya ada, tapi
mapper bentuk responsnya belum dipindah; layar menampilkan error jujur
`cloud_pending:<path>` di mode cloud, bukan data palsu. Pekerjaan
inkremental — pola router sudah siap tinggal menambah rute.

## Cara pakai (operator)
1. `npx supabase db push` (migrasi M15a) → `npx supabase db lint --linked` → `[]`.
2. Di `.env` Android: isi `EXPO_PUBLIC_SUPABASE_URL` + `EXPO_PUBLIC_SUPABASE_ANON_KEY`
   (dari dashboard Supabase), lalu `npx expo start -c` + rebuild APK.
3. Di aplikasi: Settings → Sumber Data → **Cloud** → daftar/masuk akun.
4. Bukti live aturan: `python3 scripts/m15_parity_live.py` (lihat header file).

## Bukti & batas verifikasi
- `tests/test_m15_rules_parity.py` (11 test): kurva level dieksekusi di dua
  sisi untuk total 0..5000 (0 selisih), rumus penalti dibandingkan, konstanta
  pomodoro dipantek ke `database.py`, semua fungsi terkunci `security definer`
  + `search_path` + `auth.uid()`, tanpa grant anon.
- `CraftLife-Android/tests/cloudBackend.test.ts` (8 test): mapper vs kontrak
  `_map_*`, routing RPC, fallback `cloud_pending` yang jujur.
- **Batas jujur:** sandbox tanpa Postgres — eksekusi RPC nyata diverifikasi
  lewat `scripts/m15_parity_live.py` + uji perangkat oleh pengguna.
