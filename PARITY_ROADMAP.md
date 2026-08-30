# CraftLife — Rencana Parity 1:1 PyQt → React (Full Roadmap)

> Tujuan: menutup semua selisih antara UI PyQt legacy (`MainPyQt6.py`) dan UI React
> (`web/src`), sehingga **setiap fitur & perilaku di PyQt punya padanan setara di React**
> (action parity). Bukan pixel-identical, tapi **fitur & logika sama persis**.
>
> Skala kerja: PyQt ≈ **25.000 baris / ~90 class** utama → React 27 views.
> Karena itu pekerjaan dipecah menjadi fase bertahap P1 → ... dan dikerjakan satu per satu.

---

## 1. Metodologi parity

Kita definisikan "1:1" sebagai **action parity** (mengikuti aturan README):
- Setiap **tombol/aksi** yang ada di PyQt harus ada di React.
- Setiap **logika game** tetap di Python (`database.py` / `life_api.py` / `studio_api.py` / `cloud_api.py`).
- React hanya **memanggil API yang sama**, dengan state & UX yang menyamai PyQt.
- i18n string baru harus ditambah di (a) `translations.py`, (b) `WEB_I18N_KEYS` di `api_server.py`, (c) `web/src/i18n/messages.json`, untuk **id & en**.

**Klasifikasi gap:**
- **[MISSING]** = fitur PyQt tidak ada sama sekali di React (prioritas utama).
- **[PARTIAL]** = React punya versi, tapi tidak lengkap/dangkal dibanding PyQt.
- **[LOGIC-DRIFT]** = React mengubah/menyederhanakan logika yang seharusnya dari Python.
- **[UX-DIFF]** = hasil sama, perilaku/tampilan interaksi jauh berbeda dari PyQt.

---

## 2. GAP REPORT — temuan audit sekarang

Dibuat berdasarkan perbandingan class PyQt vs komponen React. (S = sebutan status.)

### 2.1 Grafis & visualisasi — **gap terbesar (seluruh area)**
| PyQt | React | Status |
|------|-------|--------|
| `EconomyTrendWidget` (grafik tren keuangan) | EconomyView hanya ikon `TrendingUp/Down`, **tanpa grafik** | **[MISSING]** |
| `SportRepsChartWidget` (grafik reps per set) | SportView **tidak ada** grafik reps | **[MISSING]** |
| `HealthChartWidget` (grafik health: tidur/berat/mood) | Health/Pomodoro **tanpa grafik** | **[MISSING]** |
| `ProgressRing` (cincin level/XP) | Dashboard menampilkan level, **tanpa ring** | **[PARTIAL]** |
| `HeatmapWidget` (28 hari) | Dashboard punya heatmap 28 hari ✅ | ✅ (~parity) |
| Menggunakan `QPainter`/`pg` untuk grafik | React **tidak punya library chart sama sekali** | **[MISSING]** |

> **Keputusan desain yang perlu diambil:** menambah library chart (mis. `recharts`) atau
> komponen SVG ringan buatan sendiri agar bundle tetap kecil. Untuk banyak grafik kecil,
> **SVG kustom** lebih cocok dengan estetika & ukuran bundle React saat ini.

### 2.2 Drag & drop (task & folder) — **prioritas tinggi**
| PyQt | React | Status |
|------|-------|--------|
| `DraggableCard` + drag-reorder antar folder/kategori | React **tidak ada** `onDrag/draggable/onDrop/reorder` sama sekali | **[MISSING]** |
| Reorder habit/daily/quest via drag | React reorder via... tidak ada | **[MISSING]** |

### 2.3 Dialog/langkah yang hilang
| PyQt | React | Status |
|------|-------|--------|
| `OnboardingWizard` | **tidak ada** | **[MISSING]** |
| `QuickAddDialog` | **tidak ada** (CommandPalette beda fungsi) | **[MISSING]** |
| `TalentTreeDialog` | ProfileView menampilkan talent parsial, **tanpa tree dialog** | **[PARTIAL]** |
| `YearWrappedDialog` (rekapan akhir tahun) | **tidak ada** | **[MISSING]** |
| `UndoToast` (undo setelah hapus/aksi) | Toast tanpa tombol *Undo* | **[PARTIAL]** |
| `DashboardWidgetDialog` (atur widget dashboard) | **tidak ada** | **[MISSING]** |
| `WeekdaySelector` (pilih hari berulang) | sebagian di Dailies | **[PARTIAL]** |
| `HabitTemplateDialog` | template ada di React ✅ | ✅ |
| `CustomBossDialog` | GuildView punya custom boss ✅ | ✅ |

### 2.4 Aplikasi spesifik
| PyQt | React | Status |
|------|-------|--------|
| `_LyricsFetcher` / `_MetadataWorker` (lirik & metadata musik) | MusicView **tidak ada** lirik | **[MISSING]** |
| `LogSportRepsDialog` (log reps/berat per set) | SportView hanya durasi/intensitas/catatan, **tidak ada rep log** | **[MISSING]** |
| `MathPreviewDialog` (preview LaTeX penuh via Python) | NotesView memakai math eval & latex preview **lokal** (sanitasi regex) | **[LOGIC-DRIFT]** |
| `_GalleryViewerDialog` / `_GalleryEditDialog` (foto love space) | LoveSpace punya gallery tapi **tanpa viewer/editor penuh** | **[PARTIAL]** |

---

## 3. RENCANA BERTAHAP (P1 → P…)

Setiap fase = satu paket kerja yang bisa dikerjakan & diverifikasi sendiri.
**Engine room utama adalah** `web/src/context/GameContext.tsx` + `web/src/components/views/*`.
Verifikasi: `npm run lint` (tsc) + `npm run build` + `python -m py_compile` modul terkait.

### 🎯 **P0 — Fondasi (basis seluruh pekerjaan)**
- Tambahkan modul **grafik ringan** `web/src/components/charts.tsx` (SVG: Line, Bar, Donut/Pie, Ring/ProgressRing, Heatmap) — bisa dipakai ulang semua view.
- Tambahkan hook **`useDragReorder`** untuk task & folder (drag & drop native HTML5).
- Tambahkan util **`undo`** (stack aksi reversible) untuk UndoToast.
- Siapkan pola **konvensi parity**: setiap aksi di React → cek API & i18n lengkap.
> Keluaran: fondasi grafis + drag + undo + pola. Belum menyentuh logika game.

### 🎯 **P1 — Task tracker: Habits / Dailies / Quests (reorder, folder, undo)**
- **Drag & drop** reorder task dalam satu folder & antar folder (menggantikan `DraggableCard`).
- **UndoToast** ter-hubung ke aksi hapus/selesaikan/freeze/fail.
- **QuickAddDialog** (cepat menambah habit/daily/quest, shortcut Ctrl+Q / "+" global).
- Cek **folder** (TaskFolderBar) lengkap vs `FolderDialog`: rename, hapus, template bawaan.
- **Templates** & duplicate lengkap (bandingkan `HabitTemplateDialog` & `morning_routine*`).
- `WeekdaySelector` untuk jadwal berulang dailies.
- Verifikasi **fail/freeze** behavior & reward persis `TaskPage`.

### 🎯 **P2 — Sport & Nutrition (grafik, rep log, makro, air)**
- Tambah **`LogSportReps`** (set/reps/berat) — aksi & dropdown set di SportView, sinkron dengan `sport_rep_logs`.
- **`SportRepsChartWidget`** (grafik reps per olahraga / waktu).
- **Health chart** (`HealthChartWidget`) untuk steps/tidur/berat/mood.
- Cek **calorie & macro goals** vs `SetGoalsDialog`/`HealthGoalsDialog`; **recipe manager** vs `RecipeManagerDialog`.
- **Water goal** UI lengkap vs PyQt.

### 🎯 **P3 — Ekonomi & Supplies (trend chart, debt saving investment subscription)**
- **`EconomyTrendWidget`** (grafik line/area pemasukan-pengeluaran, periode).
- **Debt & installment** (AddEditDebtDialog → sudah ada di React? audit), **debt notes**.
- **Saving add/withdraw**, **investment**, **subscription renew**, **IOU**.
- **Supplies stock** in/out/adjust (`_SupplyTxDialog`) parity.
- Periksa **currency / katagori** konsisten.

### 🎯 **P4 — RPG: Shop, Inventory, Craft, Enchant, Pets, Boss**
- Audit **reward & harga** Shop vs `ShopPage` (python `database.py` adalah otoritas).
- **Equip / sell / use** vs `inventory` & `user_pets` — pastikan React memanggil aksi sama.
- **Craft & enchant** vs `CraftingPage` (`/api/shop/craft`, `/api/shop/enchant`).
- **Boss** solo & guild (`BossView`, `GuildView`) vs `ShopPage`/`GuildPage` — cek `CustomBossDialog`, reward, skill.

### 🎯 **P5 — Karakter: Dashboard, Profile, Achievements, Leaderboard, Talent**
- **`ProgressRing`** di Dashboard (level/XP ring).
- **`TalentTreeDialog`** (tree talent lengkap, unlock/respec) vs ProfileView partisial.
- **`DashboardWidgetDialog`** — toggle & susun widget dashboard.
- **Achievements & redeem codes** vs `AchievementPage`.
- **`YearWrappedDialog`** (rekapan akhir tahun).

### 🎯 **P6 — Learning (Gemini/NotebookLM) & Notes**
- Audit **notebook/source** vs `learning_*`; **Gemini chat** (key di Python, bukan React) — pastikan React hanya memanggil API studio.
- **Quiz, flashcards, FAQ, timeline, summary, mind map, study guide** — pastikan semua ada & parity.
- **`MathPreviewDialog`** — alihkan ke **preview LaTeX via Python** (bukan sanitasi regex lokal) → perbaiki **[LOGIC-DRIFT]**.
- **Notes**: folders, archive, duplicate; drag reorder notes.

### 🎯 **P7 — Music**
- Tambah **lirik** (`_LyricsFetcher`) & tampilkan embed/metadata.
- Audit **playlist & history** (`playlists`, `music_play_history`) vs MusicPage.
- Pastikan **yt-dlp search/download** hanya untuk file lokal, tanpa upload.

### 🎯 **P8 — Calendar, Reminders, Notes, Heatmap**
- Calendar: **day notes, year jump, Indonesian holidays**, parity penuh.
- **Reminders** + sound; **`HolidayTemplate`**.
- **Heatmap** terhubung ke data nyata (dailies done) — sudah ada, tinggal audit.

### 🎯 **P9 — Social/Cloud 1:1**
- **Friends** request/accept/reject/remove/profile dialog (FriendsView) — cek local fallback vs Supabase.
- **Couple / Love Space** (`LoveSpaceView`) — gallery viewer/editor penuh, daily check-in, memories, bucket, weekly review, cycle, photo meta.
- **Chat** & **Guild chat** (`GuildChatDialog`, `CloudGuildChatDialog`) — attachments, reactions.
- **PvP** challenge/respond/claim.
- **Notification center** (navbar bell) parity.
- **Leaderboard**.
> Catatan: yang tidak ada di REPO cloud (migrasi belum di-apply di proyekmu) tetap *marked*,
> tidak diuji di environment lokal. RLS tests di `supabase/tests/*` jadi acuan.

### 🎯 **P10 — Auth, Settings, Profile, Syncing, Updater**
- **OnboardingWizard** (first-time) ditambah di React.
- **Cloud connect / sync / conflict / devices / migrate local** parity penuh di `SettingsView`.
- **Password, lock, security question, backup codes, stay-logged-in, switch local**, local login/register.
- **Export / import tracker** (SQLite `export_tracker_data` / import — bukan localStorage).
- **Check updates** → `updater.py`.
- i18n id/en lengkap.

### 🎯 **P11 — Polish & Health**
- `npm run build` (percepatan code-split, `manualChunks`, gzip size 807KB → turunkan).
- Aksesibilitas & theme (high contrast, font scale, currency) konsisten.
- Tidak mengubah logika Python untuk perbaikan UI kecuali benar-benar perlu.

---

## 4. Prioritas yang disarankan

1. **P0** (fondasi grafik+drag+undo) — membuka semua fase.

2. **P1 (Task tracker)** — paling sering dipakai, gap drag & quick-add paling terasa. *Mulai dari sini.*

3. **P2 & P3 (Sport/Nutrition, Ekonomi/Supplies)** — gap grafik besar & rep log hilang.

4. **P4 & P5 (RPG & Karakter)** — parity logika shop/pets/boss & ProgressRing/Talent.

5. **P6–P8 (Learning, Music, Calendar)** — fitur lanjutan.

6. **P9 & P10 (Social/Cloud, Auth/Settings)** — butuh Supabase + bergantung migrasi.

7. **P11 (Polish)** — terakhir.

---

## 5. Cara verifikasi tiap fase

```bash
cd web && npm run lint           # tsc type-check
cd web && npm run build          # hasilkan web/dist/index.html
python -m py_compile api_server.py life_api.py studio_api.py cloud_api.py database.py
python -c "import database as db; db.init_db(); c=db.get_conn(); print(c.execute('pragma integrity_check').fetchone()[0])"
```
- Setiap fitur baru di React harus **menghubungi endpoint API yang sudah ada** (coba tidak menambah endpoint baru tanpa perlu — kalau perlu, tambahkan di `do_GET`/`do_POST` + `WEB_I18N_KEYS`).
- Setiap string baru di **id & en**.

---

## 6. Catatan penting sebelum mulai

- **Jangan ubah logika RPG di TypeScript.** Semua aturan tetap di `database.py`.
- **Backup dulu.** Setiap fase mengubah `GameContext`/views; komit per fase.
- Untuk `Referention` (zip UI) **jangan di-merge untuk fitur**.
- Pastikan **`npm run build`** dijalankan setelah ubah frontend agar `web/dist` ter-update (user tidak butuh Node).
- Rekomendasi: kerjakan **P0 + P1** sebagai iterasi pertama yang terverifikasi, lalu evaluasi, baru lanjut P2.
