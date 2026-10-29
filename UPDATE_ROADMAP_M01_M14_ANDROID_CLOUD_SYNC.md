# UPDATE ROADMAP — Android + Cloud Sync Migration (M01–M14)

> **Versi target:** `v2.0.0` (bump **MAJOR** — arsitektur berubah, bukan sekadar fitur; lihat `UPDATE_RULES.md` §5)
> **Titik awal:** tag `v1.7.4` (commit `a05bda3`), working tree bersih
> **Dokumen pendahulu:** `2026-10-06-PHASE0-ANDROID-MIGRATION-AUDIT.md` (laporan Phase 0, 25 seksi)
> **Bahasa:** Indonesia — diizinkan untuk `UPDATE_ROADMAP_*.md` oleh `UPDATE_RULES.md` §2 ("May remain Indonesian; translate on request"), mengikuti gaya `UPDATE_ROADMAP_L01_L10_v1.7.4.md` yang sudah ada.
>
> **Batas keras (berlaku di seluruh fase):**
> 1. **Tidak mengurangi** fitur, logika game, sistem, atau fungsi yang sudah ada (**P4**).
> 2. **Tidak membuat implementasi kedua** dari game rules / money formatter / i18n (**P2**).
> 3. Aplikasi tetap berfungsi **100% offline**; cloud tidak pernah jadi dependensi keras (**P1**).
> 4. Tidak ada data user yang hilang; migrasi idempoten & non-destruktif (**P6**).
> 5. Setiap klaim "selesai" harus disertai **bukti terukur** (**P5**).

---

## 1. Hasil audit (fakta kode saat roadmap ini ditulis)

Semua angka di bawah diukur langsung dari `a05bda3`, bukan diperkirakan.

### 1.1 Skala sistem

| Area | Fakta terukur |
|---|---|
| Git | 201 commit (2026-05-12 → 2026-10-04), 8 tag rilis (`v1.5.0` → `v1.7.4`) |
| Berkas terlacak | 212 · repo 11 MB |
| Python | `MainPyQt6.py` 25.218 LOC · `database.py` 17.186 · `studio_api.py` 4.620 · `api_server.py` 4.510 · `translations.py` 5.164 · `life_api.py` 1.811 · `cloud_service.py` 970 · `sync_service.py` 545 |
| Frontend | 37.178 LOC TS/TSX (87 `.tsx` + 37 `.ts`) · 30 view · `index.css` 2.185 LOC |
| API lokal | **234 route unik** (`api_server` 99 · `studio_api` 102 · `life_api` 67 · `cloud_api` 15 — referensi route) |
| DB lokal | **104 tabel nyata** (105 `CREATE TABLE`; `playlists_new` = scratch migrasi) · 90 index `idx_*` · 110 `FOREIGN KEY` · **138 `_safe_alter`** |
| Supabase | **16 migrasi · 53 tabel · 109 fungsi RPC · 67 policy RLS · 53 tabel RLS-enabled · 2 bucket privat · 1 Edge Function · 9 test SQL** |
| i18n | **4.613 key × id/en**, kedua `messages.json` identik (`git diff` kosong) |
| Desain | 12 tema · 275 class `.ct-*` · 40 token `--ct-*` |

### 1.2 Baseline gate §7 (semua HIJAU saat audit)

| Gate | Perintah | Hasil |
|---|---|---|
| Python syntax | `python -m py_compile api_server.py database.py studio_api.py life_api.py learning_helper.py music_downloader.py translations.py updater.py` | **exit 0** |
| Types | `npx tsc --noEmit` (di `web/`) | **0 error** |
| Build | `npx vite build` (di `web/`) | **clean**, `index-D6AxbvIC.js` 458,84 kB / gzip 143,84 kB |
| i18n | `python3 scripts/export_i18n.py` | **4.613 key**, diff kosong |
| DB baru | `init_db()` | **104 tabel** · `integrity_check=ok` · **0** FK violation · 1.074 food / 74 achievement / 23 redeem · 0,23 dtk |
| Idempotensi DB | `init_db()` 2× | tanpa error (0,23 dtk → 0,06 dtk) |
| Konsistensi RLS | policy vs `enable row level security` | **0** tabel ber-policy tanpa RLS; **0** RLS tanpa policy |
| Scan secret | `grep -rniE "service_role\|secret_key\|sk-…\|sb_secret"` | **tidak ada** kredensial live |

### 1.3 Aset yang SUDAH ada dan harus DIPAKAI ULANG

**Sync queue sudah menangani 15 entity type** (`sync_service.py:_process_queue`, baris 309–425):

```text
profile/upsert · profile_photo/upload · profile_photo/delete
direct_message/send · direct_message_attachment/send
productivity_event/record · achievement_claim/claim
shop_buy/buy · craft/craft · enchant/enchant
love_space_bundle/migrate · couple_end/end
personal_snapshot/upsert · gallery_photo/upload · gallery_photo/delete
```

> **Konsekuensi penting:** jalur "perintah server-authoritative" (Channel C di §3)
> **sudah berjalan** untuk `productivity_event`, `achievement_claim`, `shop_buy`,
> `craft`, `enchant`. Yang dikerjakan di roadmap ini adalah **memperluas** queue ini,
> bukan membangun sistem baru.

**Helper yang sudah ada dan dipakai ulang apa adanya:**

| Helper | Signature | Dipakai untuk |
|---|---|---|
| `_safe_alter` | `_safe_alter(cur, table, col, defn)` (`database.py:176`) | semua penambahan kolom di M03 — idempoten, aman untuk DB lama |
| `enqueue_sync` | `enqueue_sync(local_user_id, entity_type, entity_local_id, operation, payload=None)` (`database.py:15566`) | sudah **dedupe** pada `status IN ('pending','retry')` → aman dipanggil 2× (§8.2) |
| `get_pending_sync_jobs` / `get_all_sync_jobs` | `(local_user_id, limit)` | drain outbox |
| `reset_sync_backoff` | `(local_user_id)` | "Sync Sekarang" paksa retry |
| `cloud_personal_snapshot_hash` | canonical-JSON SHA-256 | hash semantik, tahan beda urutan row |
| `_sanitize_cloud_personal_snapshot` | whitelist tabel+kolom, cap 8 MB | validasi payload masuk |

**Backend yang sudah matang (jangan dibangun ulang):**

- `reward_ledger` — append-only, `unique(user_id, idempotency_key)`, `CHECK` whitelist `source`, `reversal_of`
- `spend_gold` — baca ulang saldo, raise `insufficient_balance`
- `record_productivity_event` — dedupe idempotency + jendela waktu (`>now()+5m` / `<now()-14d` → `invalid_event_time`) + **satu event per sumber per hari** untuk `habit|daily|sport` + keunikan `quest` + cap pomodoro harian
- `wallet_level_for_xp = greatest(1, floor(sqrt(xp/100))+1)` — level diturunkan server-side
- `upsert_personal_snapshot` — `SELECT … FOR UPDATE`, cek `base_revision`, idempoten pada `content_hash` sama, **wajib device terdaftar & belum di-revoke**

### 1.4 Celah yang harus ditutup

| # | Celah | Bukti |
|---|---|---|
| G1 | **Sync personal = whole-document LWW**; konflik diselesaikan biner (`keep_local`/`use_cloud`) → sisi kalah dibuang, hanya tersisa di `local_backup_payload` | `sync_service.py:_pull_personal`, `resolve_personal_conflict_*` |
| G2 | **33 tabel tanpa jalur cloud** — termasuk seluruh progresi RPG (`user_pets`, `pet_spin_state`, `user_talents`, `user_achievements`, `boss_battles`, `inventory`) + Learning (7 tabel) + Music (4 tabel) | set algebra `EXPORT_TABLES` vs `CREATE TABLE` |
| G3 | **PK integer lokal** di-remap saat import → identitas entitas tidak stabil lintas device | komentar di `apply_cloud_personal_snapshot` |
| G4 | **Tidak ada konvensi tombstone** di 40 tabel sync → delete tidak bisa merambat | 32 referensi `deleted_at`, terkonsentrasi di tabel cache cloud |
| G5 | **Cap 8 MB** pada snapshot (client + server) → user berat gagal sync total | `_sanitize_cloud_personal_snapshot` + `payload_too_large` |
| G6 | **Dual authority** progresi: `users` (lokal) vs `user_cloud_wallets` (server) | `database.py:15527 save_cloud_wallet` |
| G7 | **Nol automated test** (0 Python, 0 frontend; hanya 9 test SQL) | `find` |
| G8 | **`.env` ter-commit** (melanggar §9) — publishable key saja, bukan service-role | `git ls-files` |
| G9 | **Token via `?token=` URL query** → `sessionStorage` | `web/src/api/client.ts:9–24` |
| G10 | `debt_notes` tidak ikut sync padahal `debts` ikut | `EXPORT_TABLES` |
| G11 | README menulis "17 migrations", aktual **16** | `README.md:289` |

---

## 2. Keputusan terkunci (K)

Keputusan ini **tidak dibuka lagi** di tengah eksekusi. Kalau ada bukti baru yang
membantah, hentikan, laporkan, dan revisi dokumen ini — jangan menyimpang diam-diam (**P3**).

### Arsitektur

| # | Keputusan | Alasan |
|---|---|---|
| **K1** | **Game rules tetap SATU implementasi Python**, dijalankan server-side. Tidak boleh ada port ke Kotlin/Dart/TypeScript. | `database.py` = 17.186 LOC. Port = implementasi kedua → **pelanggaran P2 langsung** + drift XP/gold permanen |
| **K2** | **Backend tetap Supabase**, ditambah **CraftLife Rules API** (container Python) di depan domain tracker personal | 16 migrasi + 109 RPC + 67 policy sudah jadi. Pindah platform = buang 2 tahun kerja backend tanpa imbal hasil |
| **K3** | **Android = React Native + Expo (TypeScript)** | Satu-satunya opsi yang memenuhi P2: `types.ts`, `currency.ts`, kontrak API, 4.613×2 i18n jadi satu package bersama |
| **K4** | **Bukan WebView/Capacitor** untuk aplikasi produksi | Gagal brief §10/§24 ("jangan paksa UX desktop ke HP"). Boleh dipakai **hanya** sebagai spike de-risking |
| **K5** | Desktop **tetap** PyQt6 + React + SQLite in-process. Tidak di-rewrite, tidak diganti store | P4 zero regression; desktop adalah produk yang sedang dikirim |
| **K6** | `personal_snapshots` **tidak dihapus** — diturunkan jadi kanal backup/import/recovery | P4 (additive) + P6 (jangan hilang data). Sudah ada `personal_snapshot_versions` |

### Data & sinkronisasi

| # | Keputusan | Alasan |
|---|---|---|
| **K7** | **3 kanal sync**, bukan 1: (A) event log union-merge · (B) entity row-level 3-way merge · (C) perintah server-authoritative | Satu strategi untuk semua tipe data adalah penyebab G1 |
| **K8** | Setiap tabel syncable dapat **UUID client-generated + `rev` + `updated_at` + `deleted_at`** (additive via `_safe_alter`) | Menutup G3 + G4; prasyarat mutlak merge row-level |
| **K9** | **XP / gold / gems / level tidak pernah dihitung client.** Client mengirim perintah; server menulis `reward_ledger` | Sudah dibangun (K1.3). Brief §17 |
| **K10** | Tabel **append-only** (log makanan/air/sejarah/sesi/rep/transaksi) di-merge **union by UUID** — tidak pernah LWW | Commutative + idempotent → konflik mustahil terjadi. Ini mayoritas volume row |
| **K11** | Konflik field yang sama → **LWW by server timestamp, sisi kalah disimpan** sebagai revisi yang bisa dipulihkan, **bukan** dibuang diam-diam | P6. Mengganti perilaku biner G1 |
| **K12** | Preferensi **dipisah scope**: tema/font-scale/suara/LED/app-lock = **per device**; bahasa/notifikasi/mata uang = **per akun** | Sekarang tercampur di `users.*`; salah sync = device lain berubah sendiri |
| **K13** | **Pet gacha pindah server-side** di M09 (sekarang client-trusted + tidak sync) | Risiko eksploitasi + dua koleksi per user |
| **K14** | Kanal snapshot dipakai untuk: (1) migrasi device baru, (2) backup berkala, (3) disaster recovery | Memakai ulang aset yang sudah ada |

### Keamanan

| # | Keputusan | Alasan |
|---|---|---|
| **K15** | **Tidak ada** service-role key di client mana pun. Sudah benar sekarang — dijaga tetap benar | Terverifikasi saat audit |
| **K16** | Rules API memverifikasi **Supabase JWT di setiap route** dan men-scope semua query ke `auth.uid()` | API ini akan internet-facing (sekarang loopback) → risiko baru tertinggi |
| **K17** | Token Android di **Expo SecureStore (Android Keystore)**, access token hanya di memori, **tidak pernah** di URL/log | Menutup G9; WebView Android mencatat URL |
| **K18** | Setiap operasi ekonomi mutating **wajib** membawa idempotency key | Sudah pola yang ada |
| **K19** | Upload lewat **signed slot** + batas ukuran/MIME + re-encode (WebP ≤1600px q84) | Sudah pola yang ada |

### Proses

| # | Keputusan | Alasan |
|---|---|---|
| **K20** | **M02 (test suite) dikerjakan SEBELUM refactor apa pun** | G7 = risiko highest-likelihood. Refactor 17k LOC tanpa test = cara migrasi ini gagal |
| **K21** | Satu **commit phase per fase M**, satu tag di penutupan rilis; perbaikan susulan **memindahkan tag** | §5 |
| **K22** | `updater.py APP_VERSION` **dan** `web/package.json version` **dan** `mobile/package.json version` selalu identik | §5 (pelajaran rev-D: `web/package.json` sempat tertinggal di 1.7.2) |
| **K23** | **Five skills** dipakai sesuai fungsi, tidak ditumpuk: UI/UX Pro Max (struktur+a11y) → Taste (visual judgement) → Impeccable (**hanya** audit, tidak pernah generate) → Awesome Design MD (dokumentasi) → Playwright (**web saja**, tidak dipaksa ke native) | Brief §21–22. UI/UX Pro Max sudah jadi skill repo #6 sejak v1.7.4 |
| **K24** | **`DESIGN.md` ditulis sebelum UI Android skala besar** (M06) | Brief §23 |
| **K25** | **Change Impact Analysis (§33) wajib** sebelum tiap fase non-trivial | Brief §33 |
| **K26** | Learning & Music **tidak diestimasi** sebelum ada keputusan produk (lihat §9) | Tidak ada jalur cloud + hambatan platform nyata → estimasi apa pun akan bohong |
| **K27** | Android **tidak** memakai mekanisme auto-update `updater.py` | Kebijakan Play Store. Pakai Play + Expo OTA. `updater.py` tetap desktop-only |
| **K28** | Setiap efek ambient (LED, scene FX) **wajib** punya toggle di Settings + hormati `prefers-reduced-motion` / "Remove animations" Android | **P9** |

---

## 3. Model data & sinkronisasi (target)

### 3.1 Tiga kanal

| Kanal | Data | Strategi | Status |
|---|---|---|---|
| **A — Event log** | `food_logs`, `water_logs`, `health_logs`, `task_history`, `pomodoro_sessions`, `sport_activities`, `sport_rep_logs`, `supplies_tx`, `activity_log` | **Union merge** by UUID + idempotency key. Tidak pernah LWW | 🔨 baru |
| **B — Entity** | `habits`, `dailies`, `todos`, `notes`, `note_folders`, `task_folders`, `economy_items`, `economy_budgets`, `debts`, `debt_notes`, `savings`, `investments`, `subscriptions`, `recipes`, `recipe_items`, `reminders`, `calendar_notes`, `relationship_*`, `menstrual_*`, `food_items`(custom), `user_food_favorites`, `user_*_goals` | **Row-level 3-way merge**: client kirim `(uuid, base_rev, changed_fields)`; server merge per field | 🔨 baru, **memperluas `cloud_entity_map` yang sudah ada** |
| **C — Perintah** | XP, gold, gems, purchases, craft, enchant, gacha, achievement claim, boss, PvP | **Tidak di-sync** — dikirim sebagai RPC. Client hanya menampilkan hasil | ✅ **sudah jalan** untuk 5 entity type; diperluas di M09 |
| **D — Snapshot** (diturunkan) | seluruh 40 tabel | Backup berkala + migrasi device baru + recovery | ✅ sudah ada, **dipertahankan** (K6/K14) |

### 3.2 Alur tulis (Android maupun desktop)

```text
UI action
   │
   ▼
local store (SQLite) ── tulis segera, UI responsif ──► render optimis
   │
   ▼
outbox (sync_queue: status · retry_count · next_retry_at · last_error)
   │
   ├── kanal A/B ──► Rules API ──► merge server-side ──► Postgres
   │                                        │
   │                                        ▼
   │                              realtime postgres_changes
   │                                        │
   └── kanal C ──► Supabase RPC (security definer) ──► reward_ledger
                                            │
                                            ▼
                                   device lain menerima
```

### 3.3 Matriks strategi konflik

| Data | Strategi | Kenapa |
|---|---|---|
| XP / gold / gems / level | **Server-authoritative, event-sourced** | Skenario "Desktop 500 / Android 520" **tidak mungkin terjadi** — tidak ada device yang menyimpan nilai otoritatif |
| Pembelian / craft / enchant / gacha / klaim / reward | **Server-authoritative + idempotency key** | Sudah ada: `unique(user_id, idempotency_key)` di `reward_ledger` (phase5a:27) & `productivity_events` (social_realtime:76), plus `insufficient_balance` dan gate `admin_only` |
| Log append-only | **Union merge** | Dua device mencatat hal berbeda → dua-duanya selamat. Konflik mustahil |
| Entitas mutable, **field berbeda** | **Field-level 3-way merge** | Desktop rename habit, Android ubah XP-nya → dua-duanya applies |
| Entitas mutable, **field sama** | **LWW server timestamp + sisi kalah disimpan** | Bukan dibuang diam-diam (mengganti G1) |
| Delete vs edit | **Delete menang, edit jadi revisi terpulihkan** | Sesuai affordance `trash_bin` yang sudah ada |
| Counter yang tidak boleh dobel | **Uniqueness server-side** | Sudah: 1 event per sumber per hari, keunikan quest, cap pomodoro |
| Preferensi | **Split scope** (K12) | Per-device vs per-akun |
| Sosial / Love Space | **Server-authoritative + realtime** | Sudah jadi, tidak diubah |

**Anti-pattern yang ditolak tegas:** whole-document LWW diam-diam (perilaku sekarang).

---

## 4. Arsitektur target

```text
                        ┌──────────────── CRAFTLIFE CLOUD ────────────────┐
                        │                                                 │
                        │  Supabase Auth ── JWT ──┐                       │
                        │                         ▼                       │
                        │  ┌──────────────────────────────────────────┐   │
                        │  │ CraftLife Rules API  (container Python)  │   │
                        │  │ database.py engine · multi-tenant        │   │
                        │  │ kontrak 234 route · sole writer tracker  │   │
                        │  └───────────────┬──────────────────────────┘   │
                        │                  ▼                              │
                        │  PostgreSQL ── 53 tabel · 67 policy RLS         │
                        │  reward_ledger · personal_snapshots             │
                        │       │                    │                    │
                        │       ▼                    ▼                    │
                        │   Storage (2 bucket     Realtime                │
                        │   privat + attachment)  postgres_changes        │
                        └───────┬───────────────────────┬─────────────────┘
                                │                       │
              HTTPS + JWT       │                       │      HTTPS + JWT
                                ▼                       ▼
        ┌───────────────────────────┐   ┌───────────────────────────────┐
        │  DESKTOP (tidak berubah)  │   │  ANDROID (React Native/Expo)  │
        │  PyQt6 → React SPA        │   │  UI native: bottom nav,       │
        │  api_server.py in-process │   │  sheet, gesture, pull-refresh │
        │  SQLite craftlife.db      │   │  SQLite/WatermelonDB          │
        │  sync_service.py          │   │  outbox + backoff             │
        │  OS keyring               │   │  Expo SecureStore (Keystore)  │
        └─────────────┬─────────────┘   └───────────────┬───────────────┘
                      │                                 │
                      └────────►  packages/craftlife-core  ◄────────┘
                                  types.ts · currency.ts · serverClock.ts
                                  serverTime.ts · api/* · messages.json
                                  (P2 ditegakkan oleh compiler, bukan konvensi)
```

**Perubahan terhadap diagram brief §12:** hanya satu — penambahan tier **Rules API**.
Tier ini ada **semata-mata** untuk melindungi P2 dan brief §17.

---

## 5. Fase M01–M14

> **Sizing** memakai S/M/L/XL (relatif), bukan person-day — belum ada data velocity
> terukur untuk pekerjaan sebesar ini, dan angka palsu lebih buruk daripada tidak ada.

---

### M01 — Monorepo & `craftlife-core` · **S/M** · fondasi

**Tujuan:** menegakkan P2 lewat compiler, bukan konvensi.

**Pekerjaan**
- [ ] Setup npm workspaces di root (`package.json` sudah ada, tinggal tambah `workspaces`).
- [ ] Buat `packages/craftlife-core/` berisi:
  - `types.ts` (742 LOC — dipindah dari `web/src/types.ts`)
  - `utils/currency.ts` · `utils/serverClock.ts` · `utils/serverTime.ts`
  - `api/client.ts` (kontrak HTTP; `apiBase()` sudah relocatable)
  - `i18n/messages.json` (4.613 × 2)
- [ ] `web/` di-repoint ke package; **nol perubahan perilaku**.
- [ ] `tsconfig` base bersama; `web/tsconfig.json` extends.
- [ ] Tambah gate CI: package harus lolos `tsc --noEmit` sendiri.

**Acceptance criteria**
- `npx tsc --noEmit` di `web/` tetap **0 error**.
- `npx vite build` tetap clean; ukuran `index-*.js` tidak naik > 5% (tidak ada duplikasi kode).
- `grep -rn "from '\.\./types'" web/src` → **0** (semua lewat package).
- Tidak ada file `currency`/`serverClock`/`serverTime` duplikat di `web/src`.

**Gate:** `py_compile` · `tsc` · `vite build` · i18n sync · `git status --porcelain` bersih.
**Risiko:** R13 (schedule) — rendah di fase ini. **Tidak menyentuh** `database.py`.

---

### M02 — Test suite & CI · **L** · **WAJIB SEBELUM REFACTOR APA PUN (K20)**

**Tujuan:** menutup G7. Saat ini 0 test Python, 0 test frontend.

**Pekerjaan**
- [ ] **DB harness** (di-commit, bukan ad-hoc): fresh DB → `init_db()` → assert 104 tabel, `integrity_check=ok`, 0 FK violation; idempotensi (jalan 2×).
- [ ] **Legacy DB harness**: salinan DB lama → kolom baru muncul, row lama utuh, `init_db()` 2× tanpa error (§6 `UPDATE_RULES.md`).
- [ ] **API contract test** untuk 234 route: status code + bentuk respons + kode error i18n.
- [ ] **Sync engine test**: enqueue → dedupe → backoff → retry → drain.
- [ ] **Conflict test**: dua device simulasi, edit berbeda → dua-duanya selamat.
- [ ] **Frontend**: unit test `currency.ts`, `serverClock.ts` (rollover tengah malam), reducer `GameContext`.
- [ ] **i18n equality check** di CI: jumlah key identik di `translations.py`, `web/src/i18n`, `web/public/i18n`; **0** key terpakai yang hilang di `id` atau `en`.
- [ ] CI menjalankan seluruh gate §7 + test baru.

**Acceptance criteria**
- CI hijau dari commit bersih.
- Harness mereproduksi **tepat** angka baseline §1.2 (104 tabel · 4.613 key · 0 error).
- Test konflik **gagal** terhadap implementasi sync sekarang (bukti G1 nyata, bukan teori) — lalu hijau setelah M04.

**Gate:** semua gate §7 + suite baru.
**Risiko:** R2 — ini fase yang menurunkannya.

---

### M03 — Prasyarat skema row-level · **M** · additive, nol perubahan perilaku

**Tujuan:** menutup G3 + G4 + G10 tanpa menyentuh data.

**Pekerjaan**
- [ ] Via `_safe_alter(cur, table, col, defn)`, tambah ke **40 tabel `EXPORT_TABLES` + `debt_notes`**:
  - `uuid TEXT` (client-generated, `UNIQUE`)
  - `rev INTEGER DEFAULT 0`
  - `updated_at` (sudah ada di sebagian — lengkapi)
  - `deleted_at TEXT` (tombstone)
- [ ] Backfill UUID untuk row yang sudah ada (deterministik, idempoten).
- [ ] Index: `(uuid)`, `(user_id, deleted_at)`, `(user_id, updated_at)`.
- [ ] **Jangan** ubah PK integer yang ada — UUID adalah kolom pendamping (P4).
- [ ] Perbaiki G10: `debt_notes` masuk `EXPORT_TABLES`.

**Acceptance criteria**
- `init_db()` fresh **dan** legacy → kolom muncul, row lama utuh, 2× tanpa error.
- Jumlah UUID unik = jumlah row (0 duplikat, 0 NULL).
- `PRAGMA integrity_check=ok`, 0 FK violation.
- **Seluruh** test M02 tetap hijau (bukti nol regresi).

**Migrasi Supabase:** **tidak ada** di fase ini (murni SQLite). Dinyatakan eksplisit sesuai §3 poin 6.

---

### M04 — Sync engine: kanal A & B · **XL** · inti de-risking

**Tujuan:** menutup **G1** — risiko tertinggi di seluruh roadmap.

**Pekerjaan**
- [ ] **Kanal A (union merge)** untuk 9 tabel append-only: kirim `(uuid, idempotency_key, payload)`; server insert-if-absent; tidak pernah update.
- [ ] **Kanal B (row-level 3-way merge)** untuk ~25 tabel mutable:
  - client kirim batch `(uuid, base_rev, changed_fields, updated_at, deleted_at)`
  - server bandingkan `base_rev` per row → merge **per field** → bump `rev`
  - konflik field sama → LWW by server timestamp, **simpan sisi kalah** sebagai revisi
- [ ] **Tombstone propagation**: delete menulis `deleted_at`, bukan `DELETE`; garbage-collect setelah N hari.
- [ ] Perluas `enqueue_sync` dengan entity type baru (`entity_upsert`, `entity_delete`, `event_append`) — **memakai ulang** dedupe yang sudah ada.
- [ ] Perbaiki drain order: folder → task → history (dependensi FK).
- [ ] **Turunkan** kanal snapshot jadi backup/import/recovery (K6/K14) — **tidak dihapus**.
- [ ] UI status sync: pending count · failed count · last-synced · "Sync Sekarang" (paksa retry lewat `reset_sync_backoff`, sudah ada).
- [ ] Surface konflik: daftar "baru saja tertimpa" yang bisa dipulihkan — **bukan** dialog biner.

**Acceptance criteria**
- Test konflik M02 **hijau**: Desktop edit Habit A offline + Android catat 3 makanan offline → **dua-duanya selamat**.
- Delete di satu device merambat ke device lain.
- Replay outbox 2× → tidak ada duplikasi (idempoten).
- Kanal snapshot tetap berfungsi untuk device baru.
- **Nol regresi** desktop: seluruh test M02 hijau.

**Gate:** semua §7 + sync suite + cross-device suite.
**Risiko:** R1 (ditutup di sini), R8.

---

### M05 — CraftLife Rules API · **XL** · fondasi cloud

**Tujuan:** satu implementasi Python untuk dua client (K1).

**Pekerjaan**
- [ ] Containerisasi `api_server.py` + `database.py` sebagai layanan multi-tenant.
- [ ] **Verifikasi Supabase JWT di setiap route** (K16) + scope semua query ke `auth.uid()`.
- [ ] Ganti store SQLite → Postgres, **satu domain pada satu waktu** mengikuti pemisahan 4 modul yang sudah ada (`api_server` / `life_api` / `studio_api` / `cloud_api`).
- [ ] Rate limiting · audit logging · **tidak ada** debug endpoint.
- [ ] Health/version endpoint untuk smoke test.
- [ ] Desktop: jalur cloud-linked diarahkan ke Rules API; **local-only tetap 100% in-process** (P1).

**Acceptance criteria**
- Route tanpa JWT valid → 401. JWT user A → tidak pernah membaca data user B (test RLS + scoping).
- Desktop local-only: cabut jaringan → **semua** fitur lokal tetap jalan.
- Kontrak 234 route identik dengan yang dipakai `web/src/api/*` (contract test M02 hijau).

**Risiko:** R3 (monolit 17k LOC), R5 (jadi internet-facing). **Mitigasi:** angkat satu domain per PR, tidak big-bang.

---

### M06 — Design system & `DESIGN.md` · **M** · prasyarat UI (K24)

**Tujuan:** satu kontrak visual untuk web + Android.

**Pekerjaan**
- [ ] Ekstrak **40 token `--ct-*` × 12 tema** ke JSON bersama; `index.css` dan tema Android membaca dari sumber yang sama.
- [ ] Tulis **`DESIGN.md`** (skill: *Awesome Design MD*): token, type scale, spacing, radius (`0.625/0.875/1.125/1.375/1.625 rem` → 10/14/18/22/26 dp), elevation, motion (`cubic-bezier(0.22,1,0.36,1)`), inventaris komponen, **dan alasannya**.
- [ ] Petakan 275 class `.ct-*` → inventaris komponen native (card, button, input, nav, progress, XP bar, quest card, achievement card, avatar, badge, chart, empty/loading/error state, dialog, sheet, toast).
- [ ] Pertahankan **SignatureKit** (identitas per halaman) — jangan diratakan ke Material default (skill: *Taste*).
- [ ] Konvensi varian `is-row` / `is-sm` (§8.5) → component variants.
- [ ] Checklist a11y diwarisi dari gate v1.7.4: kontras ≥ 4,5:1 · `focus-visible` · `prefers-reduced-motion` · teks tanpa clipping · **+ target sentuh ≥ 48 dp**.

**Acceptance criteria**
- `DESIGN.md` ada dan 12 tema terpetakan lengkap.
- Token JSON dikonsumsi `index.css` **tanpa** perubahan visual di web (bukti: screenshot diff / build hash stabil).

---

### M07 — Fondasi Android · **L**

**Pekerjaan**
- [ ] Proyek Expo (TypeScript) di `mobile/`; `craftlife-core` dikonsumsi.
- [ ] Navigasi: **bottom navigation** (5–6 destinasi utama) + grouped "More" + deep link. 24 item sidebar **tidak** disalin 1:1.
- [ ] Tema dari token M06; 12 tema tersedia.
- [ ] Local SQLite (WatermelonDB/op-sqlite) + outbox yang **meniru bentuk `sync_queue`** (`status` · `retry_count` · `next_retry_at` · `last_error`).
- [ ] Auth: Supabase Auth + **Expo SecureStore/Keystore** (K17). Access token hanya di memori.
- [ ] Ganti 3 method `bridge.ts`: `pickFile` → SAF/media-library · `notify` → Expo Notifications · `openPath` → share/open intent.
- [ ] Sync status bar + WorkManager drain (battery-aware).
- [ ] Empty / loading / error state untuk setiap layar sejak awal (brief §10).

**Acceptance criteria**
- Login → data muncul dari cache → sync jalan.
- **Mode pesawat:** aplikasi tetap penuh fungsi lokal; perubahan masuk outbox; sinkron saat online.
- `mobile/package.json version` == `updater.py APP_VERSION` == `web/package.json version` (K22).

---

### M08 — Parity wave 1–3 · **XL**

**Wave 1 (inti):** Dashboard · Profile · Habits · Dailies · Quests · Settings
**Wave 2 (tracker):** SportTrack · Health & Food · Health logs/water · Economy
**Wave 3 (organisasi):** Supplies · Notes (+ attachment via Storage) · Reminders (+ notifikasi lokal) · Calendar · Pomodoro

**Aturan per layar (semua wave)**
- Struktur & a11y → *UI/UX Pro Max* · judgement visual → *Taste* · audit setelah milestone → *Impeccable*.
- **Bukan** salinan layout desktop: kartu mobile, bottom sheet, long-press, pull-to-refresh, gesture back.
- Money **wajib** lewat `formatMoney` dari `craftlife-core` (P2).
- Tanggal **wajib** lewat `serverClock`/`serverTime` (bukan clock browser/device) — kritis untuk streak.
- Semua string baru → `translations.py` (id + en) → `export_i18n.py` (**P7**).

**Acceptance criteria per layar:** UI jalan · state jalan · DB jalan · sync jalan · offline jalan · error handling · loading · empty · a11y · test lulus · **desktop tetap berfungsi**.

---

### M09 — RPG server-authoritative · **L**

**Pekerjaan**
- [x] **Pet gacha pindah server-side** (K13): tabel server + RPC spin (odds + pity) memakai pola `reward_ledger`. `user_pets` + `pet_spin_state` berhenti jadi client-trusted. *(M09a 2026-10-22: migrasi + jalur desktop selesai; UI Android menyusul di M09c.)*
- [x] `user_talents`, `user_achievements`, `boss_battles`, `boss_rewards`, `inventory` → server-authoritative (memakai `cloud_inventory` yang sudah ada). *(M09b 2026-10-22: talent/achievement/boss lokal selesai; inventory sudah otoritatif sejak Phase 5B; boss guild cloud sejak 4C.)*
- [x] Perluas kanal C: entity type gacha/talent/boss di `sync_queue`. *(gacha = RPC langsung M09a; talent_unlock + boss_reward mengantre per M09b.)*
- [x] Shop · Craft · Enchant · Achievements di Android — memakai jalur server yang ada (`shop_buy`, `craft`, `enchant`, `achievement_claim`). *(M09c 2026-10-23: 4 layar + model murni + 7 tes; perintah Kanal C tidak diantrekan offline.)*

**Acceptance criteria**
- Spin di dua device → satu koleksi, satu saldo gold, ledger konsisten.
- Client yang mengirim gold/XP sembarangan → ditolak server (test).
- **Tidak ada** jalur pembelian pet lama tersisa di UI (**P10**).

---

### M10 — Social · **L** · mayoritas sudah jadi di backend

**Pekerjaan**
- [x] Friends + chat (reply, reaction; lampiran tampil berpenanda, kirim lampiran menyusul) di Android — payload hybrid cloud/lokal dari server, polling 6 dtk. *(M10 2026-10-23)*
- [x] Guild lokal + online (chat, boss, role, transfer, ban via RPC) · PvP · Leaderboard · Love Space (6 tab). *(M10 2026-10-23)*
- [x] Notifications (sosial cloud + lokal) + **FCM push** via Supabase: tabel token + Edge Function send-push; aktivasi menunggu `google-services.json` pemilik proyek. *(M10 2026-10-23)*
- [x] Presence (heartbeat + status dari payload server) & typing (indikator dari payload chat cloud). *(M10 2026-10-23)*

**Acceptance criteria**
- Pesan realtime dua arah desktop ↔ Android.
- Love Space: dua partner melihat data yang sama; cycle/gallery/memories konsisten.
- Push sampai saat aplikasi ditutup (Android).

---

### M11 — Offline & reliabilitas · **M**

- [x] Backoff & retry tahan jaringan buruk; drain order benar. *(M11 2026-10-23: jitter deterministik desktop+Android; urutan drain prioritas sudah teruji.)*
- [x] Cache eviction + batas ukuran store lokal. *(M11: 2.000/jenis & 10.000 total, terlama dibuang.)*
- [x] **Hapus plafon 8 MB** dengan payload inkremental (menutup G5). *(M11: part tracker_v1/part/NNN <= 3 MB + migrasi RPC; dokumen kecil tidak berubah.)*
- [x] Recovery UI: konflik (putuskan dari ponsel), queue macet (antrekan ulang job mati), auth kedaluwarsa (ke login); device di-revoke sudah tertangani panel cloud M04c. *(M11 2026-10-23)*
- [x] Uji: airplane mode → online · force-kill saat sync · reinstall disimulasikan di lapisan outbox/sync (tes otomatis); ganti device & pemulihan akun tetap skenario perangkat asli M12. *(M11 2026-10-23)*

---

### M12 — Verifikasi parity penuh · **M**

- [x] Bandingkan **Desktop ↔ Android ↔ Cloud** terhadap matriks §7 baris demi baris, **dengan bukti**. (2026-10-23 — `VERIFIKASI_M12.md`: 34 baris diaudit ke kode nyata; ditemukan & ditutup 3 rute kosong: Learning, Music, Cloud.)
- [ ] Setiap sel ✓ harus punya test atau rekaman. **DITUNDA atas keputusan pengguna 2026-10-23: bukti perangkat diverifikasi sekaligus SETELAH M14 di HP Android fisik (bukan emulator). M12 dianggap BELUM SELESAI sampai perintah verifikasi lengkap diberikan.** (Uji otomatis lengkap: Python 531 + Android 273 + core 42. Sisa 6 bukti perangkat/live di tangan pengguna — daftarnya di `VERIFIKASI_M12.md` bagian akhir; sel terkait ditandai ⏳/◐, BUKAN ✓.)
- [x] Baris yang sengaja ⛔ didokumentasikan alasannya. (2026-10-23 — 5 baris ⛔ + alasannya di `VERIFIKASI_M12.md`.)

---

### M13 — QA · **M**

> **STATUS 2026-10-23: SELESAI dari sisi sandbox** — laporan `QA_M13.md`. Pentest menemukan & menutup 2 celah server nyata; utang kontras M06 lunas; Chip 40→48dp. Sisa jujur: bukti perangkat (TalkBack/cold start/baterai) menunggu verifikasi pengguna setelah M14, satu paket dengan daftar M12.

| Area | Yang diukur |
|---|---|
| Performa | cold start · memori · jumlah listener realtime · baterai · ukuran gambar |
| Keamanan | re-check S1–S6 · pentest ringan Rules API · audit RLS ulang |
| Aksesibilitas | kontras ≥ 4,5:1 · target ≥ 48 dp · TalkBack · "Remove animations" |
| Regresi | seluruh suite M02 + harness fase lama |
| Desain | **audit Impeccable** dijalankan di sini |
| Web | **Playwright CLI** untuk regresi UI desktop/web — **tidak** dipaksa ke native Android (K23) |

---

### M14 — Rilis · **S**

- [x] Build Play Store (AAB) · signing · data safety form. (2026-10-23 — signing release via `keystore.properties` tak-tercommit + `.example`; ikon/adaptive/splash baru; `PLAY_DATA_SAFETY_v2.0.0.md`. Build AAB aktual dijalankan operator di Windows per `OPERATOR_RELEASE_v2.0.0.md` §3 — sandbox tak punya SDK/JDK 17.)
- [x] `RELEASE_NOTES_v2.0.0.md` (Inggris) · `OPERATOR_RELEASE_v2.0.0.md` (§10.7). (2026-10-23)
- [x] **Version anchors** identik di **tiga** tempat (K22). (2026-10-23 — updater.py/web/core/mobile/app.json semua 2.0.0, versionCode 200; dijaga gate + version.test.ts.)
- [x] `updater.py` changelog + `README.md` diperbarui (§3 poin 8–9). (2026-10-23)
- [x] Satu commit phase, tag `v2.0.0`, working tree bersih (§5). (2026-10-23)
- [x] Laporan 10 poin + Format 1–7 di chat (§3/§4). (2026-10-23)

---

## 6. Dependency graph & critical path

```text
M01 (core package) ──┬──► M03 (skema) ──► M04 (sync A&B) ──┬──► M07 (Android fondasi) ──► M08 ──► M09 ──► M10
                     │                                     │                                      │
M02 (test suite) ────┴──► (mengawal semua fase di atas)     └──► M05 (Rules API) ──────────────────┘
                                                                                                  │
M06 (design system) ────────────────────────────────► M07                                          │
                                                                                                  ▼
                                                                          M11 ──► M12 ──► M13 ──► M14
```

**Critical path:** `M01 → M03 → M04 → M07 → M08 → M09 → M11 → M12 → M14`

**Boleh paralel:** M02 (segera, mengawal semua) · M05 (setelah M04) · M06 (kapan saja sebelum M07) · M10 (setelah M08).

**Gerbang keras:**
- **M02 harus selesai sebelum M03** (K20).
- **M04 harus selesai sebelum M07** — merilis Android di atas sync LWW = kehilangan data user yang terjamin (R1).
- **M06 harus selesai sebelum M07** (K24).

---

## 7. Matriks parity & urutan wave

✓ penuh · ◐ sebagian · ⛔ sengaja tidak · 🔨 perlu dibangun

| Fitur | Desktop | Android | Backend | Kanal | Realtime | Offline | Wave |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Dashboard | ✓ | 🔨 | ✓ derived | — | opsional | ✓ | 1 |
| Profile | ✓ | 🔨 | ✓ | C | opsional | ✓ | 1 |
| Habits | ✓ | 🔨 | ✓ | B | opsional | ✓ | 1 |
| Dailies | ✓ | 🔨 | ✓ | B | opsional | ✓ | 1 |
| Quests | ✓ | 🔨 | ✓ | B | opsional | ✓ | 1 |
| Settings (akun) | ✓ | 🔨 | ✓ | B | — | ✓ | 1 |
| Settings (device) | ✓ | 🔨 | — | ⛔ per-device | — | ✓ | 1 |
| SportTrack | ✓ | 🔨 | ✓ | A+B | opsional | ✓ | 2 |
| Health & Food | ✓ | 🔨 | ✓ | A+B | — | ✓ | 2 |
| Health logs / water | ✓ | 🔨 | ✓ | A | — | ✓ | 2 |
| Economy | ✓ | 🔨 | ✓ | B | — | ✓ | 2 |
| Supplies | ✓ | 🔨 | ✓ | A+B | — | ✓ | 3 |
| Notes | ✓ | 🔨 | ✓ | B | — | ✓ | 3 |
| Note attachments | ✓ | 🔨 | Storage | file | — | ◐ | 3 |
| Reminders | ✓ | 🔨 | ✓ | B | — | ✓ +notif lokal | 3 |
| Calendar | ✓ | 🔨 | statis | B | — | ✓ | 3 |
| Pomodoro | ✓ | 🔨 | ✓ | A | — | ✓ | 3 |
| Crafting | ✓ | 🔨 | ✓ | **C** | — | ◐ | 4 |
| Shop | ✓ | 🔨 | ✓ | **C** | — | ◐ | 4 |
| Enchant Forge | ✓ | 🔨 | ✓ | **C** | — | ◐ | 4 |
| Pets (gacha) | ✓ | 🔨 | **🔨 M09** | **C** | opsional | ◐ | 4 |
| Boss | ✓ | 🔨 | ✓ | **C** | ◐ | ◐ | 4 |
| Achievements | ✓ | 🔨 | ✓ | **C** | — | ◐ | 4 |
| Friends + chat | ✓ | 🔨 | ✓ | realtime | **✓** | ◐ | 5 |
| Guild | ✓ | 🔨 | ✓ | realtime | **✓** | ◐ | 5 |
| PvP | ✓ | 🔨 | ✓ | realtime | **✓** | ◐ | 5 |
| Leaderboard | ✓ | 🔨 | ✓ | realtime | **✓** | cached | 5 |
| Love Space | ✓ | 🔨 | ✓ | realtime | opsional | ◐ | 5 |
| Notifications | ✓ | 🔨 | ✓ | realtime | **✓** | ◐ | 5 |
| Command Palette | ✓ | ⛔ → search sheet | — | — | — | ✓ | — |
| Year Wrapped | ✓ | 🔨 | derived | — | — | ✓ | 5 |
| Learning | ✓ | **⏸ keputusan produk** | **tidak ada** | — | — | ✓ | — |
| Music | ✓ | **⏸ keputusan produk** | **tidak ada** | — | — | ✓ | — |
| Auto-update | ✓ | ⛔ Play/OTA (K27) | ✓ `app_releases` | — | — | — | — |
| Legacy Qt pages | ✓ fallback | ⛔ | — | — | — | — | — |

---

## 8. Gate wajib per fase

| Gate | Perintah | Kriteria lulus | Berlaku |
|---|---|---|---|
| Python syntax | `python -m py_compile api_server.py database.py studio_api.py life_api.py learning_helper.py music_downloader.py translations.py updater.py` | exit 0 semua modul | semua fase |
| Types (web) | `npx tsc --noEmit` di `web/` | **0 error** | semua fase |
| Types (core) | `npx tsc --noEmit` di `packages/craftlife-core/` | **0 error** | sejak M01 |
| Types (mobile) | `npx tsc --noEmit` di `mobile/` | **0 error** | sejak M07 |
| Build (web) | `npx vite build` | clean; catat hash + ukuran | semua fase |
| Build (Android) | `npx expo prebuild && ./gradlew assembleDebug` | clean | sejak M07 |
| i18n sync | `python3 scripts/export_i18n.py` + copy | jumlah key identik di semua sumber; **0** key terpakai hilang di `id`/`en` | semua fase ada string baru |
| DB baru | harness fresh | skema benar, idempoten | setiap perubahan skema |
| DB lama | harness legacy copy | kolom baru muncul, row lama utuh, 2× tanpa error | setiap perubahan skema |
| API | live test `:8899` payload nyata | bentuk respons benar, kode error i18n benar | setiap perubahan endpoint |
| Sync | cross-device suite | A→B dan B→A; offline→online dua arah; konflik; replay idempoten | sejak M04 |
| Frontend | unit + harness | hijau; **tidak ada** kebocoran `{placeholder}`; tidak ada komponen duplikat | semua fase UI |
| Regresi | jalankan ulang harness fase sebelumnya | sama atau membaik | semua fase |
| Smoke live | `/api/health`, `/api/version`, URL aset | 200; versi == `APP_VERSION` | setiap rilis |
| Cleanup | `PRAGMA integrity_check`, 0 row test, `users.currency` utuh | bersih | semua fase |
| Desain | checklist a11y (kontras ≥4,5:1 · focus-visible · reduced-motion · tanpa clipping · target ≥48 dp) | lulus | semua fase UI |
| Kebersihan tree | `git status --porcelain` | kosong | akhir tiap fase |

**Gate yang gagal diperbaiki SEBELUM dilaporkan** — bukan dilaporkan sebagai "known issue" tanpa persetujuan eksplisit maintainer (§7).

---

## 9. Yang TIDAK dikerjakan di roadmap ini (dan kenapa)

| Item | Alasan |
|---|---|
| **Learning di Android** | 7 tabel `learning_*` tanpa jalur cloud; Gemini + upload multi-file + audio. Butuh **keputusan produk**: tetap device-local (user kehilangan notebook saat ganti HP) atau bangun Storage + metadata. **Tidak diestimasi** sampai diputuskan (K26). |
| **Music di Android** | `playlists` menyimpan **path absolut**; `yt-dlp` tidak tersedia di Android; scoped storage membuat path tak bermakna lintas device. Butuh abstraksi MediaStore/content-URI, atau dikeluarkan dari v1 Android. **Tidak diestimasi** (K26). |
| **Rewrite PyQt6** | Desktop adalah produk yang sedang dikirim. P4. |
| **Ganti database** | SQLite lokal + Postgres cloud sudah tepat untuk P1. |
| **Port game rules ke bahasa lain** | **P2** (K1). |
| **Hapus `personal_snapshots`** | Masih dipakai untuk backup/import/recovery (K6). |
| **iOS** | Di luar lingkup; arsitektur K3 membuatnya murah nanti, tapi bukan pekerjaan roadmap ini. |
| **Linux/macOS packaging** | Sudah tercatat di roadmap README sebagai backlog terpisah. |
| **Perbaikan bug yang ditemukan di luar scope** | Dilaporkan, **tidak** diperbaiki tanpa persetujuan (**P3**). Termasuk G8, G9, G11 — diperbaiki hanya kalau Anda menyetujui. |

---

## 10. Risk register → pemetaan ke fase

| ID | Risiko | Sev | Ditutup di |
|---|---|:--:|---|
| **R1** | Sync LWW whole-document kehilangan data begitu ada device ke-2 | **High** | **M04** (prasyarat M03) |
| **R2** | Nol automated test → regresi tak terlihat | **High** | **M02** |
| **R3** | Monolit `database.py` 17.186 LOC sulit diekstrak aman | **High** | **M05** (satu domain per PR) |
| **R4** | Port rules ke TS/Kotlin → pelanggaran P2 | **High** | **K1** (keputusan, bukan pekerjaan) |
| **R5** | Rules API jadi internet-facing | **High** | **M05** + audit **M13** |
| **R6** | 33 tabel tanpa cloud muncul sebagai "fitur hilang" | Med | **M09** + matriks §7 sebagai checklist |
| **R7** | Dual authority `users` vs `user_cloud_wallets` | Med–High | **M05** |
| **R8** | Cap 8 MB menghentikan sync user berat | Med | **M11** |
| **R9** | `.env` ter-commit (G8) | Low–Med | **perlu persetujuan Anda** (§9) |
| **R10** | Token di URL query (G9) | Med | **perlu persetujuan Anda**; **wajib** sebelum M07 |
| **R11** | Learning device-local | Med | **keputusan produk** (§9) |
| **R12** | Music filesystem-bound | Med | **keputusan produk** (§9) |
| **R13** | 30 view ≈ 20k LOC UI dibangun ulang | Med | **M08** (wave) + `craftlife-core` (M01) |
| **R14** | Regresi desktop saat menambah cloud | Med | **M02** + gate regresi tiap fase |
| **R15** | i18n menyimpang antar 3 konsumen | Low–Med | **M02** (CI equality check) |
| **R16** | Desain Android jadi generik, identitas hilang | Med | **M06** + audit Taste/Impeccable |
| **R17** | Pet gacha client-trusted & tidak sync | Med | **M09** |
| **R18** | Kebijakan Play vs `updater.py` | Low | **K27** |

---

## 11. Definition of Done (per fitur)

Sebuah fitur **belum** selesai hanya karena compile, layar ada, tombol ada, atau API merespons.

Selesai = semua yang relevan berikut **terbukti**:

- [ ] UI berfungsi · state berfungsi · DB berfungsi
- [ ] Backend berfungsi · auth berfungsi · **authorization berfungsi**
- [ ] **Sync berfungsi** · **offline berfungsi**
- [ ] Error handling · loading state · **empty state**
- [ ] Aksesibilitas layak (kontras, target sentuh, screen reader, reduced motion)
- [ ] **Test lulus** (bukan "akan dites")
- [ ] **Desktop tetap berfungsi**
- [ ] Android berfungsi
- [ ] String baru ada di `translations.py` (id + en) dan terekspor
- [ ] Dokumentasi diperbarui (`README.md`, `DESIGN.md` bila visual berubah)
- [ ] Angka yang dilaporkan **nyata** (`tsc: 0 errors`, `4.613 keys`, `23/23 tests`, hash + ukuran build)

> "Kalau sesuatu **tidak** diverifikasi, katakan secara eksplisit. Optimisme diam-diam adalah defect." — `UPDATE_RULES.md` §4

---

## 12. Change Impact Analysis (template wajib, §33)

Diisi **sebelum** implementasi untuk setiap fase non-trivial:

```text
Fase            : M__ — <nama>
Tujuan          :
Bug/request     :

Menyentuh:
  [ ] Desktop (PyQt6 / React)      [ ] Android
  [ ] Backend (Rules API)          [ ] Supabase (RPC / RLS / Storage)
  [ ] Skema SQLite                 [ ] Skema Postgres
  [ ] Auth                         [ ] Sync engine
  [ ] Offline cache                [ ] UI / design system
  [ ] Test                         [ ] Dokumentasi

Regresi mungkin :
Rollback        :
Bukti lulus     :
```

---

## 13. Ringkasan urutan eksekusi

| Urut | Fase | Sizing | Gerbang |
|---:|---|:--:|---|
| 1 | **M01** Monorepo & `craftlife-core` | S/M | — |
| 2 | **M02** Test suite & CI | L | **wajib sebelum M03** (K20) |
| 3 | **M03** Prasyarat skema row-level | M | M02 hijau |
| 4 | **M04** Sync engine kanal A & B | **XL** | **wajib sebelum M07** |
| 5 | **M05** CraftLife Rules API | **XL** | setelah M04 |
| 6 | **M06** Design system & `DESIGN.md` | M | **wajib sebelum M07** (K24) |
| 7 | **M07** Fondasi Android | L | M04 + M06 |
| 8 | **M08** Parity wave 1–3 | **XL** | M07 |
| 9 | **M09** RPG server-authoritative | L | M08 |
| 10 | **M10** Social | L | M08 |
| 11 | **M11** Offline & reliabilitas | M | M09/M10 |
| 12 | **M12** Verifikasi parity penuh | M | M11 |
| 13 | **M13** QA | M | M12 |
| 14 | **M14** Rilis `v2.0.0` | S | M13 |

**Mulai dari M01.** Bukan dari proyek Android.

Alasannya satu kalimat: **semua pekerjaan Android di atas akan berdiri di atas model sync yang diketahui kehilangan data (R1), jadi model sync-nya yang harus dibenahi lebih dulu — dan itu butuh test suite (M02) serta kolom skema (M03) yang belum ada.**

---

## 14. Yang dibutuhkan dari maintainer sebelum M01 berjalan

| # | Pertanyaan | Kenapa menghambat |
|---|---|---|
| 1 | Setuju **`v2.0.0`** sebagai versi target (bump MAJOR)? | Menentukan narasi rilis & tag (§5) |
| 2 | **Learning**: device-local saja di Android, atau bangun cloud? | Tanpa ini M08 tidak bisa diestimasi jujur (K26) |
| 3 | **Music**: masuk v1 Android (butuh abstraksi MediaStore), atau tunda? | sama |
| 4 | Izin memperbaiki **G8** (`.env` ter-commit) + rotasi publishable key? | Melanggar §9; butuh keputusan Anda (P3) |
| 5 | Izin memperbaiki **G9** (token di URL)? | **Wajib** sebelum M07 |
| 6 | Infrastruktur untuk **Rules API**: hosting pilihan Anda? | M05 tidak bisa dimulai tanpa target deploy |
| 7 | Akun **Play Console** + signing key siapa yang pegang? | M14 |
| 8 | Ada **salinan DB legacy** yang boleh dipakai untuk harness M02? | Tanpa ini jalur migrasi legacy §6 tidak bisa diverifikasi |

---

*Dokumen ini adalah artefak perencanaan. Tidak ada kode yang diubah saat dokumen ini ditulis.*
*Bukti pengukuran ada di `2026-10-06-PHASE0-ANDROID-MIGRATION-AUDIT.md`, Appendix A.*
