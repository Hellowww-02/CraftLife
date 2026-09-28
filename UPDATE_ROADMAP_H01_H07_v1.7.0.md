# 🗺️ CraftLife Update Roadmap — Commit Phase **H** (H01 → H07) → **v1.7.0**

> **Satu commit phase** dari 4 area permintaan user (Learning Studio · Guild/Boss Arena · Shop · Cloud & Sync) → **Release v1.7.0**
> Basis: repo `main` pada **v1.6.7** (tag `v1.6.7`, batch D01–G04) · 6 fase kerja + 1 fase finalisasi
> Nama fase **H** karena A–G sudah terpakai (A=v1.6.3, B=backlog, C=v1.6.4, D/E/F/G=batch v1.6.7).
> Prosedur induk: `UPDATE_RULES.md` (10-point report, Format 1–6 di chat tiap fase, verification gates §7).
> **Status: DRAFT PLANNING — menunggu konfirmasi keputusan §🔒 sebelum implementasi.**

---

## 📜 Kontrak & Format (berlaku di SEMUA fase H)

1. **Translate key** di `translations.py` (**id + en serentak**), lalu
   `python3 scripts/export_i18n.py` + salin ke `web/public/i18n/messages.json`.
2. **File yang harus ditimpa** (daftar lengkap untuk copy-paste ke laptop).
3. **File baru** (jika ada).
4. **Command/endpoint baru** (jika ada) + perintah verifikasi.
5. **Kesimpulan** tiap sesi pengodingan.
6. **Migrasi** SQLite (auto-apply, idempoten) + Supabase (opsional, atau "tidak ada").
7. **Kesimpulan akhir satu commit phase** (format 1–7) — dibuat di **H07**.
8. **`updater.py`** di-update (changelog tiap fase; `APP_VERSION = "1.7.0"` di H07).
9. **`README.md`** direvisi di H07 (narasi v1.7.0 + perbaikan footer salah kutip, lihat H07).
10. **Release Notes v1.7.0** — dibuat di H07 (file + isi lengkap di chat untuk GitHub Release).

**Prinsip turunan:** game logic hanya di `database.py` · string baru selalu id+en ·
verifikasi wajib tiap fase (`py_compile` · `tsc --noEmit` · `vite build` · smoke API `:8899`) ·
UI legacy PyQt (`CRAFTLIFE_WEB_UI=0`) tetap jalan tanpa crash, tidak wajib dapat fitur baru ·
**R1–R10 UIUX** (token `--ct-*`, `.ct-btn` standard, anti-flicker R10, a11y gate) berlaku penuh.

**Aturan skill frontend (sesuai arahan maintainer, 2026-09-28):**
setiap pekerjaan UI/UX fase ini memakai skill — *Taste Skill* (Design Read satu baris sebelum
ngoding; motion harus termotivasi; pre-flight check), *Vercel web-design-guidelines* (audit
`file:line`: aria-label, focus-visible, transisi properti eksplisit, empty states),
*awesome-design-md* (kosakata visual), *image-to-code* (bila ada pekerjaan visual besar),
*playwright-cli* (uji klik nyata bila memungkinkan).

---

## 🔒 Keputusan yang Perlu Dikonfirmasi User (planning)

| # | Topik | Usulan default (jalan bila tidak diubah) |
|---|-------|-------------------------------------------|
| K1 | **Versi rilis** | `v1.7.0` sesuai permintaan explisit maintainer (catatan: UPDATE_RULES §5 menyatakan fase multi-area lazimnya bump MINOR → `1.7.0`; keputusan maintainer menang, dicatat di laporan). |
| K2 | **Dropdown artefak Studio** | List vertikal A06 diganti **satu dropdown combobox ringkas** (grup per tipe + cari + urutan) + baris aksi untuk item terpilih; area pratinjau interaktif mengambil **seluruh tinggi panel** (hapus `max-h-[360px]`). Semua aksi lama (Buka/Rename/Ekspor md·txt·csv·html/Duplikat/Hapus) tetap ada. |
| K3 | **Kualitas output Studio** | Prompt 12 generator di-rewrite lebih kaya & profesional di `learning_helper.py` (tetap satu endpoint per tipe; parameter baru **opsional**; skema JSON output kompatibel-lama sehingga artefak lama tetap terender). Tanpa parameter baru → hasil lebih bagus dari prompt baru (bukan "identik lama"), sesuai permintaan "lebih powerful". |
| K4 | **Animasi Boss Arena** | Animasi **event-driven** (serangan → shake + damage float + HP tween; menang/kalah → sequence) bukan loop idle, sesuai R10 anti-flicker; tanpa `backdrop-filter` di atas stage; hormat `prefers-reduced-motion`. Handler/API/logika damage **0% berubah**. |
| K5 | **Kategori Shop** | Sub-tab kategori murni **frontend** (grup by `type`: weapon/armor/tool/consumable/special/legendary + Semua), tanpa perubahan backend/katalog. |
| K6 | **Cloud dialog** | Seksi Cloud di Settings menjadi **kartu status ringkas + tombol "Buka Cloud Center"**; seluruh konfigurasi pindah ke **`CloudAccountDialog`** profesional (status · register/sign-in · sync center · konflik · perangkat · troubleshooting). Endpoint lama tetap dipakai (tidak ada endpoint baru wajib). |
| K7 | **Fix "HTTP 400"** | Backend cloud memetakan exception Supabase → **kode error terstruktur** (`auth_invalid_credentials`, `auth_email_not_confirmed`, `migration_not_applied`, dll) + `detail`; UI menerjemahkan kode → panduan bilingual. Tidak ada lagi teks mentah "HTTP 400". |
| K8 | **Migrasi** | SQLite: hanya jika H03/H06 butuh kolom (default: **tidak ada**). Supabase: **none** (perbaikan cloud hanya sisi klien/error mapping). |

---

## 🗺️ Peta Fase

| Fase | Area | Judul | Lapisan | Risiko |
|---|---|---|---|---|
| **H01** | 📚 Learning | Output Studio lebih powerful: rewrite prompt 12 generator + parameter opsional baru (audience/tone/notes slide dll) | Backend (`learning_helper.py`, `studio_api.py` kecil) | 🟠 (menyangkut kualitas AI; skema harus backward-compat) |
| **H02** | 📚 Learning | **Dropdown artefak** menggantikan list vertikal + pratinjau full-height + toolbar aksi item terpilih | Frontend | 🟢 |
| **H03** | 📚 Learning | Pratinjau interaktif premium (quiz progress+nav, flashcard flip 3D+shuffle+keyboard, slide deck viewer navigasi, timeline/infografik/tabel visual) + dialog per-tipe lebih lengkap | Frontend | 🟡 |
| **H04** | ⚔️ Guild | **Boss Arena** interaktif & animatif + rekonstruksi GuildView (war-room), fungsi 0% berkurang | Frontend (UI-only) | 🟡 |
| **H05** | 🛒 Shop | Item per **kategori** (sub-tab) + makeover "game shop" (rarity frame, gold plate, hover glow, sort) | Frontend (UI-only) | 🟢 |
| **H06** | ☁️ Cloud | **CloudAccountDialog** profesional + error code terstruktur + fix pesan "HTTP 400" + sync center | Full-stack (API kecil + FE) | 🟠 |
| **H07** | 📦 Release | Finalisasi & rilis **v1.7.0** (i18n sync, versi, README, Release Notes, verifikasi penuh) | Semua | 🟢 |

**Urutan:** klaster Learning berurutan (H01 backend dulu → H02 layout → H03 preview/dialog,
meminimalkan konflik file `LearningView.tsx`) → Guild (H04) → Shop (H05) → Cloud (H06) → finalisasi (H07).

---

# 🔵 KLASTER 1 — LEARNING STUDIO (H01–H03)

## H01 — Output Studio lebih powerful (prompt & opsi) 🔬

**Akar masalah (diverifikasi di kode):**
- Prompt 12 tipe ada di `learning_helper.generate_studio_content` (`learning_helper.py:877`);
  instruksi output saat ini minimal (mis. slide deck hanya `title + bullets`, `:1211-1212`),
  tidak ada arahan kualitas (contoh, penjelasan, sitasi sumber, struktur profesional).
- `system` prompt generik satu kalimat (`learning_helper.py:1225`).
- Dialog opsi sudah kaya (`studioOptions.ts`, 12 skema) tetapi beberapa tipe minim
  (briefing-doc hanya length+language+focus; data-table hanya rows; infographic hanya points).

**Pekerjaan:**
1. Rewrite prompt 12 generator: persona ahli per tipe, struktur output lebih kaya per tipe —
   - **Quiz**: soal berjenjang (ingatan→penerapan→analisis), `explanation` wajib per soal PG,
     tips menjawab di esai, distribusi topik dari sources.
   - **Flashcards**: depan/belakang + contoh pemakaian + mnemonic bila bermanfaat.
   - **Slide Deck**: `title`, `bullets`, **`notes`** (speaker notes) per slide + pembuka/penutup kuat.
   - **Timeline**: era/fase + signifikansi tiap peristiwa.
   - **Infographic**: `stats` bernilai nyata dari sumber + poin berdampak.
   - **Summary/Study Guide/FAQ/Briefing/Mind Map**: struktur + kedalaman + rujukan bagian sumber.
2. Parameter **opsional** baru (semua backward-compat; tidak dikirim = default):
   `audience` (beginner/intermediate/advanced), `tone` (academic/friendly/exam-prep),
   `include_examples` (bool) — dikirim dialog H03, divalidasi server (clamp/whitelist).
3. `studio_api._studio_generate` meneruskan parameter baru (tanpa mengubah endpoint/payload lama).

**Acceptance:** artefak LAMA tetap terender (skema kompatibel) · tanpa parameter baru endpoint
menghasilkan output skema sama (isi lebih kaya) · `py_compile` + smoke `POST /api/ai/summary`
(mock tanpa key Gemini boleh — jalur `[MOCK]` sudah ada).

## H02 — Dropdown artefak + pratinjau full-height 🔬

**Akar masalah (diverifikasi di kode):**
- `LearningView.tsx:1462-1464`: pratinjau interaktif dibatasi `max-h-[360px]` dan di bawahnya
  `StudioArtifactList` (`StudioArtifactList.tsx`, list `max-h-[420px]`) → preview kecil/tertutup.

**Pekerjaan (frontend, data & handler tetap):**
1. Komponen baru `StudioArtifactSelect` (atau rewrite `StudioArtifactList`): **dropdown combobox**
   — trigger menampilkan artefak aktif (ikon tipe · judul · waktu relatif); panel dropdown:
   cari judul, grup per tipe dengan badge jumlah, urutan Terbaru/Terlama/Tipe, klik = pilih.
2. Baris **aksi item terpilih** di bawah dropdown: Buka · ⋮ menu (Rename, Ekspor .md/.txt/.csv/.html
   sesuai tipe, Duplikat, Hapus) — semua handler lama (`onRename/onDuplicate/onDelete/onExport`).
3. Pratinjau interaktif menjadi isi utama panel: hapus `max-h-[360px]` (ganti grow + scroll internal
   bila perlu), header "Pratinjau interaktif" + nama artefak terpilih.
4. a11y: `role=combobox/listbox`, navigasi keyboard ↑↓ Enter Esc (pakai `useFocusTrap`/`useEscapeClose`),
   `aria-label` semua tombol ikon.

**Acceptance:** semua fungsi list lama ada (cari/urut/filter via grup/rename/ekspor/duplikat/hapus/buka) ·
preview jauh lebih lega · Esc menutup dropdown · 0 perubahan handler/state notebook.

## H03 — Pratinjau interaktif premium + dialog lebih lengkap 🔬

**Akar masalah (diverifikasi di kode):**
- Flashcards tanpa animasi flip/keyboard (`LearningView.renderFlashcards`, `:700-727`).
- Quiz tanpa progress indicator/navigasi soal (`renderQuiz`, `:729-870`).
- Slide deck viewer tanpa keyboard/layar penuh (`StudioNewViews.tsx:175-203`).
- Dialog briefing-doc/data-table/infographic miskin opsi (`studioOptions.ts:299-340`).

**Pekerjaan (frontend + skema opsi):**
1. **Quiz**: progress bar + lompat soal (chip nomor), status terjawab, ringkasan skor lebih visual
   (bar PG/Esai), tombol Evaluate tetap di akhir. Draft localStorage TETAP bekerja (kunci `q.id`).
2. **Flashcards**: flip 3D CSS (transform), tombol shuffle, keyboard ←/→/Space, progress "n/N",
   mode "acak urutan" tersimpan per sesi.
3. **Slide deck**: viewer dengan thumbnail strip, navigasi ←/→ + klik thumbnail, counter, tombol
   "Presentasikan" (mode fokus dalam panel), hormat reduced-motion.
4. **Timeline**: garis vertikal dengan titik era + kartu peristiwa (bukan markdown polos).
5. **Infographic**: statistik hero tiles + poin bernomor (versi besar dari preview list).
6. **Data table**: kolom sortable + zebra + sticky header.
7. **Dialog per tipe diperkaya** (UI + `studioOptions.ts` + payload → H01): `audience`, `tone`,
   `include_examples` (semua tipe relevan); slide-deck: +`audience`; briefing-doc: +`tone`;
   quiz: +`tone exam-prep default`.
8. i18n: semua label/hint baru id+en (Format 1).

**Acceptance:** keyboard penuh di quiz/flashcards/deck · draft jawaban tidak hilang ·
reduced-motion → flip instan · dialog tetap tersimpan per notebook (`loadStudioConfig`).

---

# 🟣 KLASTER 2 — GUILD & BOSS ARENA (H04)

## H04 — Boss Arena interaktif & animatif + rekonstruksi GuildView 🔬

**Akar masalah (diverifikasi di kode):**
- Arena boss guild hanya panel kecil `ct-war-panel` (`GuildView.tsx:419-477`): judul teks +
  HP bar statis + 4 tombol; hasil serangan tampil sebagai **modal teks** (`attackModal`, `:92`).
- Tidak ada panggung boss, feedback hit, damage number, atau suasana "battle".
- `BossView.tsx` (264 baris) adalah **kode mati** — tidak diimpor di mana pun
  (`App.tsx` case `'boss'` → `GuildView`); disentuh = out of scope, dicatat backlog.

**Kontrak keras dari maintainer:** *fungsi/fitur/sistem/logika game 0% berkurang, hanya boleh
menambah; layout bebas; full rekonstruksi.* → semua handler (`startSolo/openTeamDialog/attack/
guildSkill/quickHeal/chat/invite/kick/transfer/rewards/desc`) **tidak diubah**; hanya JSX/CSS.

**Pekerjaan (UI-only + kit CSS baru):**
1. **Boss Arena stage** (bagian atas seksi boss):
   - Panggung bertingkat warna tier (`TIER_COLORS` sudah ada, `GuildView.tsx:21`) + vignette statis.
   - Sprite boss besar (emoji katalog `guild.bossIcon`) + plate nama + badge tier + ATK info.
   - HP bar besar segmented (`ct-bar-track`) dengan **tween lebar** + kilat damage saat berkurang.
   - **Damage number float-up** dihitung murni visual dari delta `guild.bossHp` sebelum/sesudah
     response `attack()` (tanpa mengubah logika; angka dari teks hasil tetap di combat log).
   - **Combat log** kecil (3–5 baris terakhir dari hasil serangan — teks yang tadinya modal
     `attackModal`), modal hasil tetap tersedia via ikon ⓘ (tidak ada fitur hilang).
   - Tombol aksi 2×2 hotbar style (`ct-btn` + ikon Lucide), tekan = `ct-press` + glow singkat;
     tombol Ultimate menonjol dengan nama skill kelas (`boss_ultimate_name_*` ada).
   - Quick-heal saat HP 0 (jalur `myHpZero` ada, `:443`) tampil sebagai state "tumbang" visual.
2. **Victory/defeat moment**: boss HP habis → glow + banner singkat (state berasal dari data
   guild yang sudah ada; tanpa polling/logika baru).
3. **Guild shell war-room**: header dengan emblem + XP bar bergaya guild hall; stat cards
   (6 kartu ada, `:366-381`) jadi tile dengan ikon Lucide; member cards diberi rank frame;
   chat/invite/rewards tetap pada fungsinya.
4. Kit CSS baru di `index.css` (tanpa `@layer`, R2/R8/R10): `.ct-arena`, `.ct-arena-stage`,
   `.ct-boss-sprite` (transform-only motion, event-driven), `.ct-dmg-float`, `.ct-hp-flash`,
   `.ct-log-line`, dll; `prefers-reduced-motion` menonaktifkan float/flash.
5. Semua string baru → key i18n id+en (judul seksi, label log, tooltip).

**Acceptance:** semua aksi lama berfungsi identik (start solo/team, 4 serangan, skill, heal,
chat, invite, kick, transfer, claim reward, edit desc) · tidak ada animasi idle per-frame (R10) ·
kontras ≥4.5:1 · reduced-motion tetap fungsional · `tsc` 0 + build clean.

---

# 🟡 KLASTER 3 — SHOP (H05)

## H05 — Item per kategori + makeover "game shop" 🔬

**Akar masalah (diverifikasi di kode):**
- Tab Items menampilkan **semua 59 item dalam satu grid rata**
  (`ShopView.tsx:96-190`, `visibleItems.map`), tanpa pengelompokan kategori.
- Katalog backend `database.py SHOP_ITEMS` (`:4423`, 59 item) punya field `type`:
  weapon 11 · armor 15 · tool 9 · consumable 18 · special 1 · legendary 5 —
  i18n `shop_type_*` keenam tipe **sudah ada** (`translations.py:712-717`).
- Kartu item polos (`ct-task-card`) — tidak terasa "toko game".

**Pekerjaan (frontend-only, handler buy/sell/use/equip/enchant/adopt tidak berubah):**
1. **Sub-tab kategori** di dalam tab Items: Semua · ⚔️ Weapon · 🛡️ Armor · ⛏️ Tool ·
   🍎 Consumable · ✨ Special · 🌟 Legendary, masing-masing badge jumlah item;
   kategori dihitung dari `type` item (tanpa backend).
2. **Sortir** (nama A–Z · harga ↑ · harga ↓ · kepemilikan) + badge "baru dimiliki"? (default: kategori).
3. **Makeover kartu shop** (R8: `.ct-btn` tetap; frame rarity baru):
   - Kartu item = socket besar + nama + buff desc + plate harga gold (`💰 n G` dalam chip).
   - Rarity frame by tipe: weapon/armor → `ct-frame-rare`, tool → common, legendary →
     `ct-frame-legendary` (kelas sudah ada di `index.css`), consumable → common+.
   - State jelas: **OWNED** ribbon, **EQUIPPED** ribbon, **×qty** consumable, disabled beli
     saat gold kurang (tetap terlihat jelas alasannya — tooltip harga).
   - Hover: lift + sheen (`ct-card` ada); ikon item pop ringan (transform).
4. Tab Pets & Inventory dipertahankan (0 perubahan fungsi); buff bar tetap.
5. i18n baru: label sub-tab kategori, sortir, ribbon (id+en).

**Acceptance:** item terkelompok rapi per kategori · semua aksi beli/jual/pakai/equip/enchant
identik · slot equip 10 tetap sinkron (`slotUsedCount`) · kontras & focus-visible lolos.

---

# 🟢 KLASTER 4 — CLOUD & SYNC (H06)

## H06 — CloudAccountDialog + fix "HTTP 400" 🔬

**Akar masalah (diverifikasi di kode):**
1. **Pesan "HTTP 400"**: `api_server.py:4276` mengirim `code = 200 if extra.get("ok", True) else 400`
   untuk semua hasil cloud; client `apiPost` (`web/src/api/client.ts:52`) melempar
   `new Error(data.error || data.msg || 'HTTP ${res.status}')`. Bila body 400 tidak membawa
   `error` yang ramah (mis. exception Supabase mentah via `fail()` di `api_server.py:3878`
   → `str(e)`), toast menampilkan teks mentah Inggris atau literal **"HTTP 400"**.
2. Exception Supabase tidak dipetakan: `cloud_service.sign_in/sign_up` (`cloud_service.py:139-157`)
   melempar `AuthApiError` mentah (400 = kredensial salah / email belum dikonfirmasi);
   RPC `upsert_personal_snapshot`/`register_cloud_device` gagal → string mentah PostgREST.
3. **Tidak ada dialog khusus**: seluruh cloud = input + 7 tombol inline di Settings
   (`SettingsView.tsx:515-600`); status queue/personal/konflik (`public_status`,
   `cloud_api.py:50-94`) hampir tak terlihat user; tidak ada panduan error → user buntu
   ("tidak bisa melakukan action lainnya").

**Pekerjaan:**
1. **Backend — error code terstruktur** (`cloud_api.py` + `cloud_service.py`, aditif):
   - Wrapper `_cloud_err(exc)` memetakan: `AuthApiError`/teks → `auth_invalid_credentials`,
     `auth_email_not_confirmed`, `auth_email_exists`, `auth_weak_password`, `auth_rate_limited`;
     `PGRST202/205`/"Could not find the function" → `cloud_migration_not_applied`;
     RuntimeError konfigurasi → `cloud_not_configured` / `cloud_sdk_missing`;
     timeout/connection → `cloud_network_error`; lainnya → `cloud_error` + `detail` terpotong.
   - Semua handler `/api/cloud/*` mengembalikan `{ok:false, error:<code>, detail?, hint?}`
     konsisten → body 400 **selalu** punya `error` (client tak pernah fallback "HTTP 400").
   - `/api/cloud/register`: tangani `verification_required` + pesan "cek email" eksplisit.
2. **Frontend — `CloudAccountDialog`** (file baru `web/src/components/CloudAccountDialog.tsx`):
   - Step/status machine dari `/api/cloud/status`: **Belum dikonfigurasi** (checklist `.env` +
     SDK + migrasi) → **Siap, belum linked** (form register/sign-in + validasi inline + password
     show/hide) → **Menunggu verifikasi email** (hint cek inbox) → **Linked** (Sync Center).
   - **Sync Center**: tombol Sync Sekarang (progress + hasil pushed/pulled/personal),
     status antrian (pending/retry/failed + contoh error ramah), Migrasikan Data Lokal,
     resolusi konflik (panel kuning yang sekarang, dipindah ke dialog), Kelola Perangkat
     (list + revoke + rename), Sign Out.
   - **Error banner** dalam dialog: kode → teks id/en + langkah perbaikan (mis.
     `cloud_migration_not_applied` → "jalankan migrasi Supabase di dashboard, lalu Coba Lagi").
   - Buka dari Settings: seksi Cloud diringkas jadi kartu status (configured/linked/queue/last
     sync) + tombol **"Buka Cloud Center"**; `runCloud` lama dipakai ulang untuk aksi di dialog.
   - a11y: focus trap, Esc tutup, label semua input.
3. i18n: ±25–35 key baru (`cloud_center_*`, `cloud_err_*`, `cloud_fix_*`) id+en.
4. Endpoint baru: **tidak ada** (semua memakai `/api/cloud/*` yang sudah ada).

**Acceptance:** kredensial salah → pesan ramah bilingual (bukan "HTTP 400") · email belum
diverifikasi → langkah jelas · sync gagal karena migrasi → petunjuk + tombol retry ·
tanpa `.env` → checklist konfigurasi · status/queue/konflik/perangkat semua terlihat & bisa
diatasi dari satu dialog · tanpa `.env`/cloud pun app lokal 100% normal (P1).

---

# 🏁 FINALISASI — H07

## H07 — Finalisasi & rilis v1.7.0

1. Sinkron i18n penuh: `translations.py` ↔ `WEB_I18N_KEYS` ↔ 2× `messages.json` (0 key hilang).
2. `updater.py`: entri changelog H01–H06 + `APP_VERSION = "1.7.0"`; `web/package.json` → `1.7.0`.
3. `README.md`: What's New v1.7.0, badge, angka i18n, release history; **perbaikan temuan audit:**
   footer salah kutip *"v1.6.7 — Study & Stability"* → *"Performance & Polish"*.
4. `RELEASE_NOTES_v1.7.0.md` (isi lengkap juga ditempel di chat).
5. Verifikasi penuh (gate §7 UPDATE_RULES): `py_compile` 8 modul · `tsc` 0 · `vite build`
   (hash+ukuran) · harness DB fresh+legacy bila ada migrasi · smoke API `:8899`
   (`/api/health`, `/api/version`, 1 endpoint cloud, 1 endpoint ai) · regresi harness lama · cleanup.
6. Satu commit phase + tag annotated `v1.7.0`; instruksi operator (push, build exe, zip isi
   `dist/CraftLife/`, sha256, GitHub Release).

---

## 📎 LAMPIRAN A — Master File List (direncanakan)

### A.1 File yang akan ditimpa (±14)
| File | Fase | Alasan |
|---|---|---|
| `learning_helper.py` | H01 | Rewrite prompt 12 generator + parameter opsional |
| `studio_api.py` | H01 | Teruskan parameter baru di `_studio_generate` |
| `web/src/components/learning/studioOptions.ts` | H01/H03 | Opsi baru (audience/tone/examples) + payload |
| `web/src/components/views/LearningView.tsx` | H02/H03 | Dropdown artefak, preview full-height, renderer premium |
| `web/src/components/learning/StudioArtifactList.tsx` | H02 | Rewrite → dropdown (atau file baru menggantikan) |
| `web/src/components/learning/StudioNewViews.tsx` | H03 | Slide deck viewer + timeline/infografik/tabel premium |
| `web/src/components/learning/StudioGenerateDialog.tsx` | H03 | Render opsi baru (minor) |
| `web/src/components/views/GuildView.tsx` | H04 | Rekonstruksi arena + war-room (UI-only) |
| `web/src/components/views/ShopView.tsx` | H05 | Sub-tab kategori + makeover kartu |
| `web/src/index.css` | H04/H05 | Kit arena/dmg-float + frame kartu shop |
| `cloud_api.py` | H06 | Error code mapping semua handler cloud |
| `cloud_service.py` | H06 | Klasifikasi exception Supabase (helper) |
| `web/src/components/views/SettingsView.tsx` | H06 | Seksi cloud → kartu status + tombol Cloud Center |
| `translations.py` + 2× `messages.json` | semua | Key baru id+en |
| `updater.py` · `README.md` · `web/package.json` | H07 | Versi & rilis |

### A.2 File baru (±2)
| File | Fase | Isi |
|---|---|---|
| `web/src/components/CloudAccountDialog.tsx` | H06 | Cloud Center profesional |
| `RELEASE_NOTES_v1.7.0.md` | H07 | Catatan rilis GitHub |

### A.3 Migrasi
- **SQLite:** tidak direncanakan (semua perubahan UI/prompt/error-mapping). Bila H03/H06
  ternyata butuh kolom → `_safe_alter` idempoten + uji fresh/legacy.
- **Supabase:** none.

## 📎 LAMPIRAN B — Perintah wajib tiap fase

```bash
python3 -m py_compile api_server.py database.py studio_api.py life_api.py learning_helper.py music_downloader.py translations.py updater.py
python3 scripts/export_i18n.py && cp web/src/i18n/messages.json web/public/i18n/messages.json
cd web && npx tsc --noEmit && npx vite build
CRAFTLIFE_API_PORT=8899 python3 api_server.py   # smoke: /api/health /api/version + endpoint tersentuh
```

## 📎 LAMPIRAN C — Risiko & Mitigasi

| Risiko | Mitigasi |
|---|---|
| Prompt baru mengubah skema output → artefak lama rusak | Semua parser (`parseDataTable/Infographic/SlideDeck`, quiz/flashcard) membaca kunci lama; field baru **tambahan**; uji artefak lama tetap render |
| Animasi arena → flicker (R10) | Event-driven transform/opacity only; tanpa backdrop-filter di stage; cek reduced-motion |
| Error mapping cloud salah tebak → pesan generik | `detail` mentah tetap disertakan (terpotong 200 char) + kode fallback `cloud_error` |
| Regresi draft quiz / podcast audio | State & localStorage key tidak diubah; uji manual alur A04/A08 di laporan |
| Gemini key tidak tersedia di sandbox | Jalur `[MOCK]` sudah ada; verifikasi struktur prompt via unit string, kualitas AI diverifikasi maintainer |

## 📎 LAMPIRAN D — Backlog (BUKAN bagian commit phase ini)

- `BossView.tsx` mati (solo arena) — hidupkan/hapus, tunggu keputusan.
- Temuan audit repo: `.env` ter-commit (hapus + rotate), `RELEASE_NOTES_v1.6.4/v1.6.5/v1.6.7.md`
  & summary C01-C09 yang dirujuk README tetapi tidak ada di repo.
- U12-style QA pass lanjutan (contrast semua tema catalog).

---

# ✅ STATUS AKHIR — v1.7.0 (ditutup 28 Sep 2026)

| Fase | Hasil |
|---|---|
| H01 prompt & opsi Studio | ✅ 12 tipe + audience/tone/examples; field baru `topic`/`hint`/`example`/`notes` terpersist |
| H02 dropdown artefak | ✅ combobox cari/urut/grup + preview full-height |
| H03 pratinjau premium | ✅ flip 3D, progres+chip+ring kuis, slide notes |
| H04 Boss Arena | ✅ panggung event-driven + log; logika nol perubahan |
| H05 Shop kategori | ✅ 6 sub-tab + badge jumlah |
| H06 Cloud dialog + fix 400 | ✅ 4 tab dialog; 11 kode error bilingual |
| H07 finalisasi | ✅ tag v1.7.0, 1 commit phase, tree bersih |
| **H08 (tambahan penutup)** | ✅ hasil serangan pindah ke **kotak pesan dalam arena** ala duel Pokémon — popup modal dihapus; pesan kemenangan bertahan, bersih otomatis saat boss baru |

**Revisi dokumentasi penutup:** README (badge, What's New v1.7.0, tabel docs,
changelog), RELEASE_NOTES_v1.7.0.md (bagian Guild + angka verifikasi), roadmap
ini — semua diperbarui ke status final dalam commit yang sama (tetap 1 commit
phase, tag tetap v1.7.0).

**Bukti akhir:** `tsc --noEmit` 0 error · `vite build` 7,41 s
(index-1J3SVAtF.js 454,27 kB · GuildView-_U7Ewczo.js 32,30 kB) ·
i18n 4.528 kunci (+74), 0 missing · py_compile 8 modul OK.

**Backlog selesai di rilis ini:** `.env` dilepas dari tracking git
(rotasi kunci tetap disarankan).
