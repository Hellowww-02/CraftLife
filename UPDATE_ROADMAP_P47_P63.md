# 🔧 CraftLife Update Roadmap — P47 → P63 ("Bugfix & Rich Content")

> **Satu commit phase** dari 17 item user (bug fatal → fitur baru) · Target versi: **v1.6.0**
> Basis: repo `main` pada v1.5.0 (`updater.py APP_VERSION = "1.5.0"`)
> Semua akar masalah di bawah sudah **diverifikasi langsung di kode** (bukan tebakan); yang bertanda 🔬
> sudah **direproduksi langsung** lewat smoke test API.

---

## 📜 Kontrak & Format (berlaku di SEMUA fase)

Aturan dari user — setiap sesi coding/update WAJIB menghasilkan:

1. **Translate key** di `translations.py` (wajib jika ada string baru; id + en serentak, lalu
   `scripts/export_i18n.py` → sinkron `messages.json`).
2. **File yang harus ditimpa** (daftar lengkap, untuk copy-paste/download ke laptop).
3. **File baru** (jika ada).
4. **Command baru** (jika ada — endpoint API / script / env).
5. **Kesimpulan** dari tiap sesi pengcodingan/update.
6. **Migrasi Supabase baru** (jika ada — di phase ini mayoritas migrasi hanya SQLite lokal
   via `database.py`, Supabase tidak tersentuh kecuali disebutkan).
7. **Kesimpulan akhir satu commit phase** — setelah fase terakhir (P63) selesai, dibuat rekap
   format 1–6 dari seluruh P47–P63.
8. **`updater.py` di-update** untuk satu commit phase ini → `APP_VERSION = "1.6.0"` (dikerjakan
   di P63 agar sekali bump untuk satu commit; `web/package.json` ikut disinkronkan).

Prinsip turunan (warisan kontrak lama, tetap berlaku):
- **Game rules hanya di `database.py`** — React tidak pernah menghitung ulang.
- **UI-only untuk perbaikan tampilan** — handler/state/API tidak berubah kecuali fase itu
  memang menyentuh backend (ditandai jelas per fase).
- **String baru selalu id+en.**
- Verifikasi wajib tiap fase: `py_compile` modul tersentuh · `tsc --noEmit` · `vite build` ·
  smoke test endpoint yang diubah (jalankan `python api_server.py` + curl).

---

## 🗺️ Peta Fase

| Fase | Item User | Judul | Lapisan | Risiko |
|---|---|---|---|---|
| P47 | #15 | Redeem code: seed order bug + admin code | Backend | 🔴 fatal — sudah direproduksi |
| P48 | #4 | Chat AI double-send | Frontend | 🔴 fatal |
| P49 | #11 | Input nominal: backspace jadi 0/default | Frontend sweep | 🟠 luas |
| P50 | #13 | Tema tidak tersimpan setelah restart | Frontend | 🟠 |
| P51 | #14 | Avatar color tidak tampil di mana pun | Frontend | 🟡 |
| P52 | #12 | Height trend 7 hari flat/tidak muncul | Backend + UI | 🟡 |
| P53 | #10 | Duplicate note salah lokasi + "(Copy)" | Backend + UI | 🟡 |
| P54 | #1 | Notes: attachment (import/paste) | Full-stack | 🟢 fitur besar |
| P55 | #2 | Notes: perluas LaTeX & simbol matematika | Backend + UI | 🟢 fitur |
| P56 | #3 | Edit & ganti icon folder (task + sporttrack) | Full-stack kecil | 🟢 fitur |
| P57 | #5 + #17 | Music engine global: tidak putus pindah page + berhenti saat logout | Frontend + PyQt shell | 🟠 |
| P58 | #6 | Lyrics: akurat, live per detik, import manual, bisa disimpan | Full-stack | 🟢 fitur besar |
| P59 | #7 | Icon playlist khusus (emoji + foto) | Full-stack kecil | 🟢 fitur |
| P60 | #8 | Layout Music page: scroll menyeluruh, fit page | UI-only | 🟡 |
| P61 | #9 | Love Space: couple account tidak terdeteksi | Backend (cloud sync) | 🟠 |
| P62 | #16 | Pembersihan database bulanan (history tracker) | Backend + UI | 🟠 butuh kehati-hatian |
| P63 | — | Finalisasi & rilis v1.6.0 (versi, changelog, verifikasi penuh, rekap commit phase) | Semua | — |

> Urutan disusun: bug fatal dulu (P47–P48), lalu bug berdampak luas (P49–P53), lalu fitur
> per domain (Notes → Task → Music → Social), ditutup finalisasi. Fase Music dijadikan berurutan
> (P57–P60) karena semuanya menyentuh `MusicView.tsx` — konflik merge minimal.

---

## P47 — Redeem Code: Seed Order Bug + Admin Code 🔬

**Item user #15.** *"Redeem code tidak mendapatkan apa-apa… 'invalid code or expired'… tidak bisa redeem jadi admin."*

**Akar masalah (TERBUKTI — direproduksi di DB baru):**
- `database.py init_db()` menjalankan `migrate_redeem_codes()` (15 kode `NEW_REDEEM_CODES`)
  **sebelum** blok "Insert default redeem codes" (±baris 1778). Blok default hanya jalan jika
  `SELECT COUNT(*) FROM redeem_codes == 0` — tapi tabel sudah berisi 15 kode hasil migrasi →
  **kondisi tidak pernah true** → 5 kode default **tidak pernah di-seed**:
  `ADMINADMINADMIN`, `WELCOME100`, `STARTGOLD`, `WOODSWORD`, `GOLDENAPPLE`.
- Akibatnya `redeem_code()` SELECT tidak ketemu → `"Invalid or expired code"` — termasuk untuk
  kode admin **meskipun password benar** (pemeriksaan password di handler lolos, tapi kode memang
  tidak ada di DB).
- Bug sekunder yang ikut diperbaiki:
  - Kode one-time **ditandai `used_by` SEBELUM hadiah diberikan** → jika pemberian hadiah gagal
    (mis. item tidak ada di `SHOP_ITEMS`), kode hangus tanpa hadiah.
  - `used_by` hanya menyimpan **satu** user → kode one-time yang dipakai user lain selamanya
    invalid untuk user ini (desktop multi-account). Butuh tabel pemakaian per-user.

**Rencana:**
- `database.py`:
  - Ganti blok seed default → `INSERT OR IGNORE` per kode (idempoten, urutan tidak penting).
  - `redeem_code()`: berikan hadiah dulu, tandai `used_by` **setelah** sukses (satu transaksi).
  - Tabel baru `redeem_code_redemptions(code_id, user_id, redeemed_at)` — one-time = sekali
    per user; cek keabsahan: `used_by IS NULL OR is_one_time = 0` diganti logika per-user.
  - Pastikan kode item default valid terhadap `SHOP_ITEMS` (cek `wooden_sword`, `golden_apple`).
- `api_server.py` `/api/profile/redeem`: deteksi kode admin tetap dari DB (sudah benar);
  pastikan pesan error membedakan `invalid` vs `already_redeemed` vs `already_admin`.
- `ProfileView.tsx`: prompt password jangan hardcode `^ADMINADMINADMIN$` — ikut flag
  `isAdminCode` dari respons katalog/endpooint (opsional kecil).

**File ditimpa:** `database.py`, `api_server.py`, (kecil) `web/src/components/views/ProfileView.tsx`
**File baru:** — · **Migrasi SQLite:** tabel `redeem_code_redemptions` + seed ulang idempoten
**Supabase:** tidak ada · **i18n:** `redeem_already_used_by_account` (id/en) + `redeem_code_recovered` (opsional)
**Verifikasi:** register user baru → redeem `WELCOME100` (sukses, XP +100), `ADMINADMINADMIN` + password (sukses, `isAdmin: true`), redeem ulang satu-time oleh user yang sama (ditolak `already_redeemed`), user kedua redeem kode yang sama (masih boleh — per-user).

---

## P48 — Chat AI Double-Send 🔬

**Item user #4.** *"Chat terkirim dua blok duplikat."*

**Akar masalah (TERBUKTI di kode):**
`LearningView.handleSendChat()` memanggil **DUA kali** request chat:
1. `addNotebookChat(id, userMsg, 'user')` → di `GameContext` (baris ±1454) implementasinya
   **bukan** menambah pesan lokal, melainkan **memanggil `studio.chat()`** (request #1);
2. kemudian `await studio.chat(activeNotebook.id, userMsg)` **lagi** di LearningView (request #2).

Tiap POST `/api/ai/chat` → `_chat_ai()` menjalankan `db.add_learning_chat(notebook_id, "user",
question)` + generate jawaban Gemini. Dua request = **2 blok user + 2 jawaban AI tersimpan** —
dan boros token Gemini 2×.

**Rencana (frontend-only):**
- `GameContext.addNotebookChat`: ubah jadi **murni append lokal** (user & ai) ke state notebook —
  tidak lagi memanggil `studio.chat`.
- `LearningView.handleSendChat`: tetap satu-satunya pemanggil `studio.chat()`; setelah jawaban
  masuk, append lokal (atau refresh via `applyLive` — pilih satu jalur saja, tidak keduanya).
- Pastikan `updateNotebook(id, {chatHistory: []})` (tombol bersihkan) juga menghapus history di
  server bila ada endpoint-nya (cek `/api/learning/*`).

**File ditimpa:** `web/src/context/GameContext.tsx`, `web/src/components/views/LearningView.tsx`
**File baru:** — · **Migrasi:** — · **i18n:** —
**Verifikasi:** kirim 1 chat → di UI tepat 1 blok user + 1 jawaban; refresh page → tetap 1 (DB tidak dobel); pantau network tab: hanya **1** POST `/api/ai/chat`.

---

## P49 — Input Nominal: Backspace Balik ke 0/Default

**Item user #11.** *"Backspace digit → balik ke 0/nilai default, harusnya kosong."*

**Akar masalah (dua pola):**
1. Pola `Number(e.target.value) || 0` / `|| <default>` di onChange banyak view — dikonfirmasi
   `HealthFoodView.tsx` (6 titik), `SportView.tsx` (1), dan pola serupa
   `parseFloat(...) || x` di dialog lain. Saat input dikosongkan → `''` → `0`/default → state
   berubah → input "nylonong" balik.
2. `MoneyInput.tsx`: `useEffect([value]) → setText(maskMoney(value))` memformat ulang pada
   setiap ketikan (cursor lompat), dan `onBlur` mengembalikan nilai lama saat kotak kosong —
   bukan membiarkan kosong lalu divalidasi saat save.

**Rencana (frontend-only, sweep menyeluruh):**
- Perbaiki `MoneyInput.tsx`: izinkan teks kosong selama fokus; panggil
  `onValueChange(0)` **atau** callback null-safe saat kosong (API kontrak baru
  `onValueChange?: (n: number | null)`); format ribuan hanya saat blur; jangan reformat saat
  user sedang mengetik (guard `isFocused`).
- Buat komponen `NumberInput.tsx` (baru) — input angka yang menyimpan string di state,
  `onChange` meneruskan `number | null`, coercing hanya onBlur. Ganti semua pola
  `Number(...) || 0` di: `HealthFoodView` (steps/sleep/HR/weight/height), `SportView`
  (weight/duration/calories), `EconomyView` + dialog economi, `SuppliesView`, `NutritionView`,
  `PomodoroView`, `QuickAddDialog`, `DashboardWidgetsDialog`, `OnboardingWizard`, `LoveSpaceView`
  (umur, dsb.), `PetsView` (feed/train), `SettingsView` (goals) — sweep via grep
  `Number(e.target.value) ||` dan `parseFloat(.* )|| `.
- Validasi akhir tetap di tombol Save (nilai kosong → pesan wajib isi, bukan diam-diam 0).

**File ditimpa:** `MoneyInput.tsx` + semua view yang memakai pola tersebut (daftar final di sesi kerja)
**File baru:** `web/src/components/NumberInput.tsx`
**Migrasi:** — · **i18n:** — (pakai key validasi yang ada; tambah `form_field_required` bila belum ada)
**Verifikasi:** ketik 5 digit → backspace semua → kotak kosong (bukan "0"/"170"); blur → tetap kosong; save dengan kosong → pesan validasi; ketik lagi nilai tersimpan benar.

---

## P50 — Tema Tidak Tersimpan Setelah Restart

**Item user #13.** *"Pilih theme nether → restart → balik default."*

**Akar masalah:**
- `GameContext` bootstrap (±baris 543): `if (uTheme && themePalettes[uTheme] && uTheme !==
  activeTheme)` — katalog tema (`/api/catalog/themes`) dimuat **asinkron** dan sering selesai
  **setelah** bootstrap → `themePalettes[uTheme]` masih kosong → tema user **tidak pernah
  diterapkan** → jatuh ke `modern_dark`.
- Simpanan `localStorage` juga tidak dapat diandalkan di QWebEngineView (bisa ter-reset antar
  sesi), sehingga satu-satunya sumber kebenaran adalah kolom `users.theme` (sudah ada:
  `set_user_theme` + bootstrap mengembalikan `theme`).

**Rencana (frontend-only):**
- GameContext: simpan `bootstrap.user.theme` ke state `userThemeFromServer`; efek terpisah yang
  menjalankan `setActiveThemeState(uTheme)` begitu `themePalettes` terisi (tidak lagi bergantung
  urutan race). `applyTheme` tetap lewat util tema.
- `setActiveTheme` tetap POST `/api/settings {theme}` (sudah benar).
- Pindahkan prioritas: `userThemeFromServer` > localStorage > default.
- Opsional: logging kecil untuk memudahkan diagnosa.

**File ditimpa:** `web/src/context/GameContext.tsx` (kecil)
**Migrasi:** — · **i18n:** —
**Verifikasi:** ganti tema → restart API + reload UI → tema sama; uji semua 7 tema + high-contrast.

---

## P51 — Avatar Color Tidak Menampilkan Warna

**Item user #14.** *"Avatar color tidak menampilkan color apapun di profile/navbar/friends."*

**Akar masalah:**
- Kolom `users.avatar_color` **ada**, tersimpan (`/api/settings {avatarColor}` →
  `update_user(avatar_color=…)`), dan dikirim bootstrap (`"avatarColor": …`). Tapi **tidak ada
  satu pun komponen yang merendernya** — `Navbar.tsx` (±baris 100) merender emoji avatar di
  container berwarna statis; `ProfileView` hanya pakai warna untuk state selected swatch;
  `FriendsView` dialog profil sama.

**Rencana (frontend-only, render):**
- Terapkan `style={{ backgroundColor: user.avatarColor }}` (dengan overlay/gradient konsisten
  design system `.ct-*`) di: `Navbar` avatar chip, `Sidebar` hero profile, `ProfileView` avatar
  besar + preview swatch, `FriendsView` see-profile dialog & daftar teman, `LoveSpaceView`
  (bila menampilkan avatar pasangan), `LeaderboardView` (baris user), chat bubbles pengirim.
- Fallback `#5a8a2e` bila kosong.

**File ditimpa:** `Navbar.tsx`, `Sidebar.tsx`, `ProfileView.tsx`, `FriendsView.tsx`,
`LeaderboardView.tsx` (final di sesi kerja) · **File baru:** — · **Migrasi:** — · **i18n:** —
**Verifikasi:** ganti warna di Profile → langsung berubah di navbar; restart → tetap.

---

## P52 — Height Trend 7 Hari Flat

**Item user #12.** *"Height chart tidak menampilkan progress padahal sudah input dari BMI/daily."*

**Akar masalah (TERBUKTI):**
`life_api.py` (±baris 517–528): `height_series` diisi dari **`hgoals.height_cm` (nilai statis
goal, default 170)** untuk semua 7 hari — **tidak pernah membaca `health_logs.height_cm`**.
Data logging tinggi sudah benar tersimpan (endpoint health log menerima `heightCm`), tapi seri
chart tidak memakainya → garis flat/tidak informatif.

**Rencana:**
- `life_api.py`: bangun `height_series` dari `by_date[d]["height_cm"]` dengan **carry-forward
  last-known** (tinggi jarang berubah — garis kontinu), fallback ke goal hanya bila belum pernah
  ada log sama sekali.
- `HealthFoodView.tsx`: pastikan chart tinggi memakai `heightSeries` dan skala Y tidak flat
  (min–max wajar, mis. ±5 cm dari median), tampilkan delta vs minggu lalu.

**File ditimpa:** `life_api.py`, `web/src/components/views/HealthFoodView.tsx`
**Migrasi:** — · **i18n:** — (opsional `health_height_trend`)
**Verifikasi:** input tinggi berbeda 2 hari berturut → chart naik; tanpa log → garis goal halus + label "belum ada data".

---

## P53 — Duplicate Note: Lokasi & "(Copy)"

**Item user #10.** *"Duplicate tidak di sebelah note asli, malah ke All Notes; jangan ada '(Copy)'."*

**Akar masalah (TERBUKTI):**
`database.py duplicate_note(uid, note_id, dest_folder_id=None)` → handler `/api/notes/duplicate`
meneruskan `dest_id` dari body (default **None** = root "All Notes"), judul ditambah
`" (Copy)"`, dan tidak mengatur `sort_order` ( jatuh ke akhir). SQLite lokal.

**Rencana:**
- `database.py duplicate_note`: default `dest_folder_id` = **folder note sumber**; judul **tanpa
  sufiks**; `sort_order` = setelah note sumber (geser urutan sisanya); kembalikan `folder_id`.
- `life_api.py`: handler terima `dest_id` opsional (tetap, untuk "duplicate to folder" bila ada).
- `NotesView.tsx`: panggil duplicate tanpa dest → muncul tepat di bawah note asal; state
  folder aktif tidak lompat.

**File ditimpa:** `database.py`, `life_api.py`, `web/src/components/views/NotesView.tsx`
**Migrasi:** — · **i18n:** —
**Verifikasi:** duplicate note di subfolder → duplikat ada di folder & posisi yang sama; nama tanpa "(Copy)"; urutan tetap.

---

## P54 — Notes: Attachment (Insert dari Laptop / Paste)

**Item user #1.** *Fitur baru.* Notes bisa dilampiri file: import dari laptop, atau paste dari
sumber mana pun (clipboard gambar/teks/file).

**Rencana (full-stack):**
- **SQLite** (`database.py`): tabel baru
  `note_attachments(id, note_id, user_id, file_name, mime, size, storage_path, kind, created_at)`
  — `kind`: image/file; `storage_path` menunjuk folder
  `<data>/craftlife_attachments/<user_id>/`.
- **API** (`api_server.py` + `life_api.py`):
  - `POST /api/notes/attachment` (multipart upload; reuse mekanisme `_handle_upload_file` +
    validasi ukuran/mime whitelist: png/jpg/webp/gif/pdf/txt/md/csv — **max 5 MB/file**, sesuai
    keputusan user 2026-09-08).
  - `GET /api/notes/attachment/image?id=` (serve aman, hanya pemilik).
  - `DELETE /api/notes/attachment` (hapus file + row).
  - Embed note: sisipkan token `[attachment:id]` di konten note → renderer NotesView menampilkan
    preview (gambar inline; file jadi chip unduh/buka via `bridge.openPath`).
- **UI** (`NotesView.tsx`): tombol 📎 di toolbar note; drag-and-drop ke editor; **paste**
  (event `onPaste`: clipboard file/gambar → upload otomatis, teks biasa tetap tempel teks);
  panel daftar attachment per note; hapus attachment.
- **PyQt bridge** (`web_shell.py`): pastikan `pickFile` menerima filter; `openPath` untuk buka
  file asli.

**File ditimpa:** `database.py`, `api_server.py`, `life_api.py`, `NotesView.tsx`, `web_shell.py`
**File baru:** `web/src/components/notes/NoteAttachments.tsx` (panel + chip)
**Migrasi SQLite:** tabel `note_attachments` · **Supabase:** — (lokal dulu; sinkronisasi cloud attachment menyusul sebagai phase terpisah bila diminta)
**i18n (baru):** `notes_attach_file`, `notes_attach_paste_hint`, `notes_attach_delete_confirm`,
`notes_attach_too_large`, `notes_attach_type_unsupported`, `notes_attach_open`, `notes_attach_download` (id+en)
**Verifikasi:** tempel screenshot dari clipboard → muncul inline; import PDF → chip; hapus → file hilang dari disk; ukuran maksimum ditolak dengan pesan.

---

## P55 — Notes: Perluas LaTeX & Teks Matematika

**Item user #2.** *"Tambahkan lebih banyak kalimat dan huruf matematika agar rich."*

**Kondisi kini:** `mathtools.py` sudah punya >200 simbol (Greek, arrows, operators AMS,
super/subskrip, `\mathbb` dll.) + endpoint `/api/notes/preview-math` & `math-chunks` +
toolbar konversi di NotesView.

**Rencana:**
- `mathtools.py`: tambah coverage — susunan/kalimat: `\frac{}{}` → bentuk berurut `a/b` +
  tanda kurung cerdas, `\binom`, `\sqrt[n]{}`, `\overline/\underline`, `\overset/\underset`,
  `\stackrel`, `\begin{cases}`/`matrix` (flat dengan │), `\substack`, `\xrightarrow{text}`;
  huruf: full Greek bold/italic (`\boldsymbol`, `\mathit`), double-struck tambahan
  (`\Bbbk` dst.), huruf math lain (`\aleph \beth \gimel \daleth \ell \hbar \imath \jmath`),
  operator tambahan (`\oiint \oiiint \varsubsetneqq \nleqslant` dsb.), simbol kimia/fisika
  umum, spasi `\quad \qquad \!` lebih lengkap, akcent (`\hat \bar \dot \ddot \vec` pada blok).
- **UI** (`NotesView.tsx`): palette simbol kategori (Greek, Operator, Panah, Relasi, Kalkulus,
  Huruf khusus, Template) — klik → sisip snippet LaTeX di kursor; tombol "Konversi" & pratinjau
  tetap via server (paritas维持).
- Uji regresi: string yang ada tetap konversi sama.

**File ditimpa:** `mathtools.py`, `web/src/components/views/NotesView.tsx`
**File baru:** `web/src/data/mathSymbols.ts` (katalog palette, id sama dengan server bila perlu)
**Migrasi:** — · **i18n:** `notes_math_palette_greek`, `notes_math_palette_operators`,
`notes_math_palette_arrows`, `notes_math_palette_relations`, `notes_math_palette_calculus`,
`notes_math_palette_letters`, `notes_math_palette_templates` (id+en)
**Verifikasi:** `\frac{a}{b}+\binom{n}{k}` → `a/b + (n k)`; `\boldsymbol{\alpha}` → 𝜶; palette klik menyisip dengan benar; `py_compile` + unit konversi cepat via python -c.

---

## P56 — Edit & Ganti Icon Folder (Task Page + SportTrack)

**Item user #3.** *"Belum ada fitur ganti/edit icon folder."*

**Kondisi kini:** kolom `task_folders.icon` **sudah ada** (default 📁) dan `TaskFolderBar`
merendernya; yang tidak ada adalah **UI editornya** (rename/edit folder tanpa pemilih icon).
SportTrack memakai `TaskFolderBar` yang sama.

**Rencana:**
- `life_api.py`: endpoint folder update harus menerima `icon` (cek handler
  `/api/task-folders` PUT/PATCH — lengkapi field icon bila belum).
- `TaskFolderBar.tsx`: dialog edit folder (rename + **grid pemilih icon** ±60 emoji kategori) —
  dipakai semua mode (habits/dailies/quests/sport/economy?); tombol edit muncul di chip folder
  (hover / menu ⋯).
- Ikon tersimpan per folder; tampil di chip bar & dialog.

**File ditimpa:** `life_api.py` (kecil), `web/src/components/TaskFolderBar.tsx`
**File baru:** `web/src/components/FolderIconPicker.tsx` (grid emoji, reuse lintas mode)
**Migrasi:** — (kolom sudah ada) · **Supabase:** —
**i18n:** `folder_edit_icon`, `folder_icon_picker_title`, `folder_icon_reset` (id+en)
**Verifikasi:** buat folder → edit icon → tersimpan setelah restart; ikut tampil di habits/dailies/quests/sport.

---

## P57 — Music Engine Global (Pindah Page Tetap Bunyi + Berhenti Saat Logout)

**Item user #5 & #17.**
- #5: *pindah page → musik berhenti* — **akar (TERBUKTI):** elemen `<audio>` hidup di dalam
  `MusicView.tsx`; `App.tsx` me-unmount view saat pindah halaman → audio ikut hancur.
- #17: *keluar aplikasi ke login/register → musik masih bunyi, baru berhenti saat login window
  ditutup* — **akar:** `WebMainWindow.closeEvent` hanya emit `logout_signal`; halaman web di dalam
  QWebEngineView tidak diberhentikan medianya sebelum window ditutup (audio Chromium masih
  berjalan sampai page benar-benar dibebaskan).

**Rencana:**
- **Frontend:** pindahkan kepemilikan audio ke **global** — `<audio>` tunggal dirender di
  `App.tsx` (di luar switch view), state player (currentTrack, isPlaying, progressMs, queue,
  shuffle/repeat, volume) di `GameContext` (`musicPlayer` slice). `MusicView` menjadi "remote
  control" yang mengontrol context (tidak lagi punya `<audio>` sendiri). Mini-player chip kecil
  di Navbar (judul + play/pause + next) supaya kontrol tetap terlihat di semua page.
- **PyQt:** di `web_shell.py closeEvent` (dan `MainPyQt6._logout` sebelum `main_win.close()`):
  `view.page().runJavaScript("window.craftlifeStopAllAudio && window.craftlifeStopAllAudio()")`
  + fallback `document.querySelectorAll('audio,video').forEach(e=>e.pause())`; setelah itu
  `view.setPage(None)`/stop sebelum window ditutup. Frontend menyediakan
  `window.craftlifeStopAllAudio` (pause + src reset) — dipanggil juga saat logout dari UI.
- Alarm pomodoro/reminder (Web Audio) ikut dihentikan oleh fungsi yang sama.

**File ditimpa:** `web/src/App.tsx`, `web/src/context/GameContext.tsx`,
`web/src/components/views/MusicView.tsx`, `web/src/components/Navbar.tsx`, `web_shell.py`,
`MainPyQt6.py` (hanya hook logout) · **File baru:** `web/src/components/MiniPlayer.tsx`
**Migrasi:** — · **i18n:** `music_miniplayer_now_playing`, `music_miniplayer_open` (id+en)
**Verifikasi:** putar lagu → pindah ke Dashboard → tetap bunyi + mini-player aktif; kembali ke Music → progress aman; logout → musik berhenti seketika sebelum login window tampil; close app → tidak ada audio tersisa.

---

## P58 — Lyrics: Akurat, Live Per-Detik, Import Manual, Bisa Disimpan

**Item user #6.** *"Lirik tidak selalu akurat… mau live per detik + isi sesuai lagu… bisa search
dari internet ATAU import manual dari komputer… dan bisa di-save (dari internet maupun user)."*

**Kondisi kini:** `get_lyrics()` (studio_api) sudah paralel LRCLIB get/search (varian query) +
lyrics.ovh + embedded tags; MusicView punya parser LRC + auto-scroll baris aktif.

**Rencana (full-stack):**
- **Akurasi pencarian** (`studio_api.py get_lyrics`):
  - Kirim **durasi track** ke LRCLIB (`duration` param pada `/api/get`, dan pilih hasil search
    dengan |durasi−durasi file| ≤ 3 dtk) → menghilangkan lirik versi live/remix yang salah.
  - Pembersihan metadata lebih agresif (feat., prod., "(Official Video)") + normalisasi
    huruf/ampersand; skor kandidat: kecocokan judul+artis+durasi.
  - Bila `syncedLyrics` tersedia → prioritaskan (live per detik); plain hanya fallback.
- **Import manual**: `POST /api/music/lyrics/import` (multipart .lrc/.txt via bridge.pickFile)
  → deteksi format LRC otomatis (timestamp `[mm:ss.xx]`) atau plain; simpan.
- **Penyimpanan per track**: tabel SQLite `song_lyrics(id, user_id, track_key, track_title,
  artist, source('web'|'user'|'embedded'), plain, synced, offset_ms, updated_at)` — `track_key`
  = path file / hash metadata. GET `/api/music/lyrics` → cek tersimpan dulu (source apapun),
  baru cari internet; tombol "Simpan lirik ini" & "Hapus lirik tersimpan" di drawer lyrics.
- **Offset live-sync**: tombol −0.5s / +0.5s di drawer (offset_ms per track, tersimpan) untuk
  koreksi lirik yang geser; auto-scroll tetap jalan.
- **UI**: drawer lyrics diberi header source badge (Web / File / Tersimpan / Disimpan-user),
  tombol refresh, import, save, hapus, offset.

**File ditimpa:** `studio_api.py`, `MusicView.tsx`, `web/src/api/studio.ts`, `database.py`
**File baru:** `web/src/components/music/LyricsDrawer.tsx` (refactor dari inline MusicView)
**Migrasi SQLite:** tabel `song_lyrics` · **Supabase:** —
**i18n:** `music_lyrics_saved_badge`, `music_lyrics_save`, `music_lyrics_saved_ok`,
`music_lyrics_delete_saved`, `music_lyrics_import`, `music_lyrics_import_ok`,
`music_lyrics_import_invalid`, `music_lyrics_offset`, `music_lyrics_offset_reset`,
`music_lyrics_match_duration` (id+en)
**Verifikasi:** lagu populer → synced per detik tepat (bandingkan dgn YT); lagu versi akustik (beda durasi) → tidak salah versi; import .lrc manual → live-sync jalan; save → restart → lirik langsung dari penyimpanan (offline); offset menggeser penyorotan.

---

## P59 — Icon Playlist Khusus (Emoji + Foto dari Komputer)

**Item user #7.** *"User bisa menambah icon playlist khusus, import foto dari komputer."*

**Rencana:**
- **SQLite**: `_safe_alter("playlists", "icon", "TEXT DEFAULT '🎵'")` — nilai berupa emoji ATAU
  penanda foto `photo:<id>` (tabel `user_profile_photos` pola serve bisa ditiru; buat tabel
  `playlist_icons(id, user_id, playlist_id, storage_path, mime)` atau simpan di folder
  attachments dengan reference — putuskan implementasi, rencana: tabel kecil khusus).
- **API**: `POST /api/music/playlist-icon` (multipart foto → resize max 512px, simpan, update
  `playlists.icon='photo:<id>'`), `GET /api/music/playlist-icon/image?id=` (serve, owner-only),
  reset ke emoji via `POST /api/music/playlist-rename` field `icon` (emoji).
- **UI** (`MusicView.tsx`): klik kanan / menu ⋯ playlist → "Ganti icon" → dialog dua tab
  (Emoji grid / Upload foto via bridge.pickFile); thumbnail bulat di daftar playlist & header.

**File ditimpa:** `database.py`, `studio_api.py`, `api_server.py` (serve), `MusicView.tsx`
**File baru:** `web/src/components/music/PlaylistIconDialog.tsx`
**Migrasi SQLite:** kolom `playlists.icon` + tabel `playlist_icons` · **Supabase:** —
**i18n:** `music_playlist_icon_change`, `music_playlist_icon_emoji`, `music_playlist_icon_photo`,
`music_playlist_icon_reset`, `music_playlist_icon_too_large` (id+en)
**Verifikasi:** ganti emoji → tampil; upload foto 4MB → di-resize & tampil; restart → tetap; playlist tanpa icon → default 🎵.

---

## P60 — Layout Music Page: Scroll Menyeluruh & Fit Page

**Item user #8.** *"Scroll area hanya di bagian playlist; isi lagu harus bagian dari scroll area; fix ukuran layout seluruhnya (fit page)."*

**Rencana (UI-only, kontrak R1/R10 berlaku):**
- Restrukturisasi `MusicView.tsx`: satu **scroll container utama** (library + daftar lagu +
  panel playlist) dengan `min-h-0`/flex yang benar; **player deck** (bawah) dan **drawer lyrics**
  tetap fixed/sticky; tidak ada scroll ganda nested yang saling berebut; tinggi konten mengikuti
  viewport (fit page) pada 1080×700 s.d. 1440p+.
- Sesuaikan setelah P57 (mini-player) dan P58 (drawer refactor) agar tidak konflik — urutan
  fase sudah menjamin ini dikerjakan setelahnya.
- Hormati R10: tanpa backdrop-filter di atas scene, tanpa animasi paint idle.

**File ditimpa:** `web/src/components/views/MusicView.tsx`, (bila perlu) `web/src/index.css`
**File baru:** — · **Migrasi:** — · **i18n:** —
**Verifikasi:** daftar 100+ lagu discroll mulus; deck tidak menutupi lagu terakhir (padding bawah); lyrics drawer membuka tanpa merusak layout; 1080×700 tidak ada overflow horizontal.

---

## P61 — Love Space: Couple Account Tidak Terdeteksi

**Item user #9.** *"Sudah menjalin couple + login cloud Supabase, tapi tidak bisa track couple account di Love Space."*

**Dugaan akar (diverifikasi sebagian, perlu diagnosa live saat implementasi):**
- `studio_api` menandai `coupleActive = get_couple_context(uid).active` yang membaca tabel
  **LOKAL** `couple_relationships`. Alur couple di cloud (`send/respond_couple_request` RPC)
  ada di `cloud_service.py`, tapi **tidak ada jalur yang menuliskan hasilnya ke tabel lokal**
  saat kedua pihak sudah cloud-linked → `coupleActive` selalu `false` lokal → fitur couple
  (couple profile shared, tracking pasangan) tidak muncul, meski relasi ada di Supabase.
- `love_profile_cloud` hanya aktif `if is_cloud_linked(uid)` — jika relasi couple hanya ada di
  cloud sedangkan mirror lokal kosong, scope "shared" ditolak (`couple_active` false).

**Rencana:**
- Diagnosa: bandingkan isi `couple_relationships` lokal vs `couple_relationships` cloud untuk
  akun ter-link (fungsi cloud sudah punya akses tabel tsb — lihat `cloud_service` sinkronisasi).
- Fix backend: saat sync/refresh (`sync_service` atau `studio_api love()`), **mirror** status
  couple cloud → lokal (active/ended, partner mapping via `cloud_entity_map`), sehingga
  `get_couple_context` benar; idempoten dan aman untuk mode offline (relasi lokal murni tetap
  didukung).
- UI Love Space: badge status couple (aktif / menunggu / tidak terhubung) + tampilan akun
  pasangan (nama, avatar) bila aktif.

**File ditimpa:** `studio_api.py`, `cloud_service.py`/`sync_service.py`, `database.py` (fungsi mirror), `LoveSpaceView.tsx`
**File baru:** — · **Migrasi SQLite:** kemungkinan kolom `couple_relationships.cloud_status` sudah ada — cukup pakai · **Supabase:** TIDAK ada migrasi baru (skema 4f sudah mencakup)
**i18n:** `love_couple_status_active`, `love_couple_status_pending`, `love_couple_status_none`,
`love_couple_partner_card` (id+en)
**Verifikasi:** dua akun cloud link + couple accept → Love Space kedua pihak menampilkan couple aktif & couple profile shared; putus cloud → fitur lokal tetap jalan; tanpa cloud → tidak ada regresi.

---

## P62 — Pembersihan Database Bulanan (History Tracker)

**Item user #16.** *"Belum ada fitur pembersihan database; 3 bulan main → 1 GB. Yang dibersihkan hanya history tracker sebelum hari ini."*

**Rencana (fitur backend + UI, hati-hati):**
- **Definisi "history tracker"** (yang dibersihkan; data master tidak disentuh):
  `task_history`, `activity_log`, `pomodoro_sessions`, `sport_rep_logs`, `music_play_history`,
  `boss_battles`/`boss_rewards` (riwayat), `notifications` lama, cache chat cloud
  (`cloud_messages`, `chat_attachments_cache` dsb. — hanya cache), `trash_bin` kedaluwarsa.
  `health_logs`/`food_logs`/`water_logs`/`economy_items` **TIDAK** ikut default (data kesehatan
  & keuangan user) — tetap disediakan opsi lanjutan.
- **Retensi** (konfigurasi di Settings, **default: 30 hari terakhir** — keputusan user
  2026-09-08; pilihan: 1 hari / 7 hari / 30 hari / 90 hari / nonaktif).
- **Mekanisme** (`database.py` + `api_server.py`):
  - `purge_tracker_history(user_id, before_date)` → hitung baris+byte yang akan dihapus
    (dry-run), jalankan DELETE per tabel, `PRAGMA wal_checkpoint(TRUNCATE)` + `VACUUM`,
    kembalikan laporan ukuran sebelum/sesudah.
  - **Backup otomatis dulu** (`backup_database`) sebelum purge pertama kali.
  - Auto: saat boot, jika `last_purge_at` ≥ 30 hari → jalankan purge sesuai retensi (bisa
    dimatikan). Tabel kecil `maintenance_state(user_id, last_purge_at, retention_days, auto)`.
  - Endpoint: `GET /api/settings/cleanup` (status+estimasi), `POST /api/settings/cleanup`
    (jalankan / ubah retensi / toggle auto).
- **UI** (`SettingsView.tsx`): seksi "Pemeliharaan Data" — ukuran DB, estimasi hemat, pilihan
  retensi, tombol Bersihkan Sekarang (dengan konfirmasi + ringkasan hasil), toggle otomatis
  bulanan.
- **Catatan dampak (ditampilkan ke user di UI):** heatmap/achievements yang menghitung dari
  `task_history` akan kehilangan hitungan lama (progress achievement yang sudah diklaim aman);
  streak tersimpan di `users` — tidak terpengaruh.

**File ditimpa:** `database.py`, `api_server.py`, `SettingsView.tsx`
**File baru:** — (UI inline di Settings) · **Migrasi SQLite:** tabel `maintenance_state`
**Supabase:** — (murni lokal) · **i18n:** `settings_maintenance_title`, `settings_db_size`,
`settings_cleanup_now`, `settings_cleanup_confirm`, `settings_cleanup_done`,
`settings_cleanup_retention`, `settings_cleanup_retention_1d/7d/30d/90d/off`,
`settings_cleanup_auto`, `settings_cleanup_estimate`, `settings_cleanup_warning` (id+en)
**Verifikasi:** DB uji berisi ribuan baris history → dry-run akurat → purge → ukuran file mengecil (VACUUM) → app jalan normal; backup dibuat; auto-purge terjadwal benar.

---

## P63 — Finalisasi & Rilis v1.6.0 (Penutup Commit Phase)

**Rencana:**
- `updater.py`: `APP_VERSION = "1.6.0"` · `web/package.json` version `1.6.0` (sinkron).
- README: badge release → v1.6.0, seksi "What's New in v1.6.0" (tabel 17 item), update tabel
  status.
- **Rekap satu commit phase** (format 1–6 dari seluruh P47–P62) — dokumen
  `UPDATES/2026-09-08-P47-P63-PHASE-SUMMARY.md` (folder `UPDATES/` dibuat mengikuti konvensi
  README).
- Verifikasi penuh: `py_compile` semua modul · `tsc --noEmit` · `vite build` · smoke test API
  (register → bootstrap → redeem → notes duplicate → music lyrics) · konsistensi i18n
  (`translations.py` ↔ `WEB_I18N_KEYS` ↔ `messages.json`, via `scripts/export_i18n.py`).
- Siapkan artefak rilis: `scripts/build.ps1` → zip tanpa `.env` & `craftlife.db` → GitHub
  Release `v1.6.0` (langkah operator di laptop user).

**File ditimpa:** `updater.py`, `web/package.json`, `README.md`
**File baru:** `UPDATES/2026-09-08-P47-P63-PHASE-SUMMARY.md` (+ opsional log per fase `UPDATES/…-P4x-….md` sesuai format 1–7)

---

## 📦 Rekap Migrasi & Rilis

| Jenis | Isi |
|---|---|
| **SQLite (database.py)** | `redeem_code_redemptions` (P47) · `note_attachments` (P54) · `song_lyrics` (P58) · `playlists.icon` + `playlist_icons` (P59) · `maintenance_state` (P62) |
| **Supabase** | **TIDAK ADA** migrasi baru di commit phase ini (semua perbaikan lokal; couple memakai skema 4f yang sudah ada) |
| **Endpoint baru** | `/api/notes/attachment*` (P54) · `/api/music/lyrics/import` + `song_lyrics` CRUD (P58) · `/api/music/playlist-icon*` (P59) · `/api/settings/cleanup` (P62) · minor: folder icon (P56) |
| **Versi** | 1.5.0 → **1.6.0** (P63) |

## ✅ Keputusan Terkunci (2026-09-08)

| Hal | Keputusan |
|---|---|
| Eksekusi | Roadmap **direview user dulu** — eksekusi menunggu sinyal mulai (bisa semua berurutan P47→P63 atau per fase) |
| P62 retensi default | **30 hari terakhir** (heatmap & progress achievement 30 hari terakhir aman; opsi lain tetap tersedia) |
| P54 attachment | **Max 5 MB/file**, whitelist tetap: png/jpg/webp/gif/pdf/txt/md/csv |
| P59 foto playlist | (belum dikonfirmasi) — rencana: disimpan lokal dulu, tidak sync cloud |
