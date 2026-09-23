# 🗺️ CraftLife Update Roadmap — Commit Phase **C** (C01 → C09) → **v1.6.4**

> **Satu commit phase** dari 3 area permintaan user (Learning · Database & Updater · Date Utilities) → **Release v1.6.4**
> Basis: repo `main` pada **v1.6.3** (commit phase A01–A15) · 8 fase kerja + 1 fase finalisasi
> Nama fase **C** karena kode-B sudah dipakai item backlog B01–B08 di `UPDATE_ROADMAP_A01_A14_v1.6.3.md` Lampiran E.
> Prosedur: `UPDATE_RULES.md` (10-point report, Format 1–6 di chat tiap fase, verification gates).

---

## 📜 Kontrak & Format (berlaku di SEMUA fase C)

1. **Translate key** di `translations.py` (**id + en serentak**), lalu
   `python scripts/export_i18n.py` + salin ke `web/public/i18n/messages.json`.
2. **File yang harus ditimpa** (daftar lengkap untuk copy-paste ke laptop).
3. **File baru** (jika ada).
4. **Command/endpoint baru** (jika ada) + perintah verifikasi.
5. **Kesimpulan** tiap sesi pengodingan.
6. **Migrasi** SQLite (auto-apply, idempoten) + Supabase (opsional, atau "tidak ada").
7. **Kesimpulan akhir satu commit phase** (format 1–7) — dibuat di **C09**.
8. **`updater.py`** di-update (changelog tiap fase; `APP_VERSION = "1.6.4"` di C09).
9. **`README.md`** direvisi di C09 (narasi v1.6.4).
10. **Release Notes v1.6.4** — dibuat di C09 (file + isi lengkap di chat untuk ditempel ke GitHub Release).

**Prinsip turunan:** game logic hanya di `database.py` · string baru selalu id+en ·
verifikasi wajib tiap fase (`py_compile` · `tsc --noEmit` · `vite build` · smoke API) ·
UI legacy PyQt (`CRAFTLIFE_WEB_UI=0`) tetap jalan tanpa crash, tidak wajib dapat fitur baru.

---

## 🔒 Keputusan yang Sudah Dikunci Bersama User (2026-09-22)

| Topik | Keputusan |
|---|---|
| Studio outputs (C05) | **FULL** — 4 output baru: Briefing Doc, Data Table, Infografik (SVG), Slide Deck (HTML + ekspor) |
| Video Overview | **DITUNDA** (backlog — butuh render video/ffmpeg, berat & berisiko) |
| Tipe sumber (C02) | **Dokumen + gambar + audio** — pdf/docx/xlsx/pptx/csv/txt/md/epub + gambar (vision AI) + audio (transkrip via Gemini, butuh API key) |
| Perilaku updater (C07) | **Dialog + hitung mundur** — cek otomatis saat start, dialog berisi catatan rilis + Download + countdown, diperbaiki & hadir di Web UI |
| Tag rilis | `vX.Y.Z` tanpa titik nyasar (tag live `v.1.6.3` salah menurut UPDATE_RULES §10) |

---

## 🗺️ Peta Fase

| Fase | Area | Judul | Lapisan | Status |
|---|---|---|---|---|
| **C01** | 📚 Learning | Shell baru: 3 panel + **drag splitter + collapse** ala NotebookLM | Frontend | ✅ Selesai 2026-09-22 |
| **C02** | 📚 Learning | Multi-upload + semua tipe dokumen + file asli disimpan + ekstraksi terstruktur | Full-stack + migrasi | ✅ Selesai 2026-09-22 |
| **C03** | 📚 Learning | Sumber dari web (URL + YouTube) di Web UI + panduan ringkas per sumber | Full-stack | ✅ Selesai 2026-09-22 |
| **C04** | 📚 Learning | Chat: saran pertanyaan + simpan jawaban jadi catatan | Full-stack (kecil) | ✅ Selesai 2026-09-22 |
| **C05** | 📚 Learning | 4 output Studio baru (Briefing Doc, Data Table, Infografik, Slide Deck) | Full-stack | ✅ Selesai 2026-09-22 |
| **C06** | 🗄️ Database | Self-care: betulkan 0-byte + auto-clean terjadwal + rincian ukuran + WAL/VACUUM robust | Full-stack + migrasi | ✅ Selesai 2026-09-22 |
| **C07** | 🔄 Updater | Updater berfungsi: hardening + endpoint + dialog Web UI + auto-check + langkah operator | Full-stack | ✅ Selesai 2026-09-23 |
| **C08** | 🕐 Date | Tanggal live + rollover tengah malam + sinkron semua halaman | Frontend (+kecil backend) | ✅ Selesai 2026-09-23 |
| **C09** | 📦 Release | Finalisasi & rilis **v1.6.4** | Semua | ✅ Selesai 2026-09-23 |

**Urutan:** klaster Learning berurutan (C01–C05, satu area `LearningView`/Studio) → Database (C06)
→ Updater (C07) → Date (C08) → finalisasi (C09).

---

# 🔵 KLASTER 1 — LEARNING PAGE (C01–C05)

## C01 — Shell Learning baru: 3 panel + drag splitter + collapse ⬜

**Akar masalah (terverifikasi):** `LearningShell.tsx` memakai preset Sempit/Sedang/Lebar
(320/420/560px) + komentar eksplisit "drag digantikan preset karena rawan di WebEngine";
kolom tengah menukar Sumber⇄Chat lewat tab, bukan 3 panel sejajar seperti NotebookLM.

**Target (perilaku NotebookLM):**
- Desktop (≥1024px): `[rail notebook] [panel Sumber] ‖ [panel Chat] ‖ [panel Studio]`.
- Divider antar panel **bisa diseret** (pointer events, clamp min/max, aman WebEngine:
  tanpa `backdrop-filter`, tanpa animasi idle).
- Tiap panel samping bisa **di-collapse** (tombol di tepi panel) + strip ramping untuk
  membuka kembali; preferensi tersimpan (`cl_learning_layout` format v2 + migrasi
  otomatis dari format preset v1 dan key legacy `cl_learning_panel_widths`).
- Tombol preset Sempit/Sedang/Lebar **dihapus** (permintaan eksplisit user).
- Mobile (<1024px): tab penuh Sumber/Chat/Studio tetap dipertahankan.

**File:** `web/src/components/learning/LearningShell.tsx` (tulis ulang, interface props
tetap) · `web/src/index.css` (kelas `.ct-nlm-splitter` dkk, tanpa `@layer`) ·
`translations.py` + 2× `messages.json` (key collapse/expand/hint).

**Verifikasi:** `tsc` · `vite build` · harness unit (migrasi state + clamp) + SSR render
(desktop 3 panel, collapse, mobile tabs) · i18n 0 hilang.

### 📌 REALISASI C01 (2026-09-22) — shell 3 panel + drag + collapse ✅

**Format 1 — i18n:** +5 key → **4.330** (`learning_src_hide/show`,
`learning_studio_hide/show`, `learning_drag_hint`), id+en, 3 sumber identik.
**Format 2 — ditimpa:** `LearningShell.tsx` (tulis ulang) · `NotebookRail.tsx`
(nav view dihapus) · `LearningView.tsx` (props rail) · `index.css` (splitter/strip) ·
`translations.py` + 2× `messages.json` · `updater.py` (changelog) · roadmap ini.
**Format 3 — baru:** `web/src/components/learning/shellState.ts` (state v2 + migrasi +
clamp, pure/testable).
**Format 4 — command:** tanpa endpoint baru; uji: `npx tsc --noEmit` **0 error** ·
`vite build` bersih (`index-DdYJCrrN.js` 1.298,33 kB/gzip 344,62 kB · CSS 181,58 kB) ·
harness `c01_harness` unit **22/22** + SSR **22/22** · `py_compile` translations OK.
**Format 5 — kesimpulan:** Learning kini 3 panel sejajar dengan divider seret +
collapse + preferensi tersimpan; tombol Sempit/Sedang/Lebar dihapus; mobile tab tetap.
**Format 6 — migrasi:** tidak ada (SQLite maupun Supabase).

## C02 — Multi-upload + semua tipe dokumen + file asli disimpan ✅

**Akar masalah:** input file single (`files?.[0]`, `SourcesRail.tsx:84-92`), whitelist
`.txt/.md/.pdf/.docx` (`api_server.py:2720-2733`), file asli dihapus setelah ekstrak
(`studio_api.py:2772-2780`), ekstraktor hanya pdf/docx/txt
(`studio_api.py:2690-2715`, `learning_helper.py:66-95`).

**Target:**
- Upload **banyak file sekaligus**: input `multiple` + drag-and-drop + antrean dengan
  progres per file + ringkasan berhasil/gagal.
- Tipe: `pdf docx xlsx xls pptx csv tsv txt md markdown rtf epub` + gambar
  (`png jpg jpeg webp gif` → dianalisis vision AI) + audio (`mp3 wav m4a ogg opus flac`
  → ditranskrip via Gemini, butuh API key). Batas ukuran per file 25 MB (audio) /
  20 MB (dokumen), bisa dilewati sebagian dengan pesan jelas.
- **File asli disimpan** di `learning_sources/<uid>/` dan tidak dihapus; DB menyimpan
  metadata berkas (nama, mime, ukuran, path) + teks hasil ekstraksi.
- Ekstraksi **terstruktur**: xlsx → tabel Markdown per sheet; pptx → outline per slide;
  pdf → penanda halaman; docx → heading; epub → bab.
- Penampil sumber: info berkas asli (unduh/buka) + teks terekstrak + tombol ekstrak ulang;
  hapus sumber ikut menghapus berkas.

**Migrasi SQLite (auto):** kolom baru `learning_sources.file_name/mime_type/file_size/
file_path/extracted_at` (+ indeks). **Supabase: tidak ada** (sumber lokal saja).

**Dependensi baru (wajib):** `openpyxl` (sudah ada di requirements) · `python-pptx` ·
`EbookLib` atau `ebooklib` (epub) — ditambah ke `requirements.txt`.

### 📌 REALISASI C02 (2026-09-22) — multi-upload + 23 tipe berkas + file asli ✅

**Format 1 — i18n:** +23 key → **4.353** (6 `learning_source_type_*`: sheet/slides/
csv/image/audio/book · 16 antrean/berkas/ekstrak-ulang · 1 `learning_supported_types`),
id+en, 3 sumber identik.
**Format 2 — ditimpa:** `learning_helper.py` (ekstraktor xlsx/xls/pptx/csv/epub/rtf +
dispatcher `extract_source_file` + vision/transkrip Gemini) · `database.py` (migrasi 5
kolom + indeks + CRUD aman) · `api_server.py` (whitelist 23 ekstensi + dir per-user +
rute unduh berkas) · `studio_api.py` (impor preservasi + rute re-extract + `_nb_map`) ·
`SourcesRail.tsx` (tulis ulang: antrean drain + drag-drop) · `LearningView.tsx` (viewer
berkas + re-extract) · `SourceCard.tsx` (6 tipe + chip berkas) · `studio.ts` ·
`index.css` (overlay drop) · `requirements.txt` (pptx/EbookLib/xlrd/striprtf) ·
`translations.py` + 2× `messages.json` · `updater.py` (changelog) · roadmap ini.
**Format 3 — baru:** harness `c02_harness` (extract/dblife/apilife/unit/ssr).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-DiC3kT_p.js` 1.307,52 kB/gzip 347,03 kB · CSS 182,41 kB) · harness extract
**19/19** + dblife **18/18** + apilife **13/13** + FE unit **7/7** + SSR **7/7** (64 cek) ·
`py_compile` semua modul OK.
**Format 5 — kesimpulan:** unggah banyak berkas sekaligus (23 tipe) dengan antrean
berurutan + progres; berkas asli tersimpan di `learning_sources/<uid>/` dan bisa
diunduh/diekstrak-ulang dari penampil; gambar/audio tanpa API key tetap tersimpan
dengan penanda + peringatan; hapus sumber menghapus hanya berkas kelolaan app.
**Format 6 — migrasi:** SQLite otomatis (5 kolom `file_*`/`extracted_at` +
indeks `notebook_id,user_id`); Supabase: tidak ada. **Deviasi tercatat:** batas ukuran
diseragamkan **20 MB** (bukan 25 MB audio) karena batas inline API Gemini 20 MB;
jumlah tipe final **23** (tsv/markdown/ogg/opus/flac ikut terdaftar).
**Revisi C02-hybrid (2026-09-22):** AI kini menerima berkas asli pdf/gambar sebagai
lampiran multimodal saat chat + generate Studio (maks 3 berkas, ≤20 MB/berkas, hanya
path kelolaan); teks ekstraksi tetap jadi grounding utama (sitasi/jumlah kata/Office).
PDF scan (tanpa teks) tidak lagi ditolak saat upload — tersimpan + warning
`learning_pdf_no_text`, AI membaca PDF aslinya. Impor gagal membersihkan file yatim.
i18n +1 → **4.354**. Harness `direct.py` **16/16**; regresi C02 tetap hijau (64/64).

## C03 — Sumber dari web (URL + YouTube) di Web UI + panduan sumber ✅

**Akar masalah:** `fetch_website_text`/`fetch_youtube_transcript` hanya dipanggil PyQt
legacy (`MainPyQt6.py:18582-18585`); dialog Web UI hanya menyimpan teks tempel
(`LearningView.tsx:1416`).

**Target:** dialog "Tambah sumber" Web UI mendukung tempel teks, URL website (fetch +
bersihkan), URL YouTube (transkrip); tiap sumber punya ringkasan panduan otomatis
(1–2 kalimat via Gemini saat ada key, else potongan teks); chip jumlah kata; toggle
grounding per sumber tetap.

### 📌 REALISASI C03 (2026-09-22) — sumber URL + panduan per sumber ✅

**Format 1 — i18n:** +6 key → **4.360** (`learning_add_text/website/youtube`,
`learning_url_ph`, `learning_fetch_save`, `learning_url_invalid`), id+en, 3 sumber identik.
**Format 2 — ditimpa:** `learning_helper.py` (`fetch_website`/`fetch_youtube` + judul,
API transkrip ganda, oEmbed, `source_snippet`/`make_source_guide`) · `database.py`
(kolom `summary` + setter) · `studio_api.py` (rute `sources` tangani `url` +
`_map_sources` backfill malas) · `LearningView.tsx` (dialog 3 mode + simpan async) ·
`SourceCard.tsx` (baris panduan) · `studio.ts` (`addSourceFromUrl`) · `index.css`
(`.ct-guide-clamp`) · `translations.py` + 2× `messages.json` · `updater.py` · roadmap.
**Format 3 — baru:** harness `c03_harness` (web/yt/guide/api/fe_ssr).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-tsvqzOy-.js` 1.310,00 kB/gzip 347,69 kB · CSS 182,51 kB) · harness C03 **60/60**
(web 7 + yt 20 + guide 13 + api 17 + FE 3) + regresi C01–C02 **80/80** · `py_compile` OK.
**Format 5 — kesimpulan:** dialog Tambah mendukung teks tempel, URL website (fetch +
bersih + judul otomatis), URL YouTube (7 bentuk URL, transkrip id/en→any, judul oEmbed);
server otoritatif soal deteksi tipe; tiap sumber tampilkan panduan 1–2 kalimat (AI
saat ada key, disimpan malas ≤2/panggil; else potongan); chip kata + grounding tetap.
**Format 6 — migrasi:** SQLite otomatis (kolom `summary`); Supabase: tidak ada.
Tanpa endpoint baru (ekstensi kontrak `POST .../sources` dengan field `url`).

## C04 — Chat: saran pertanyaan + simpan jawaban jadi catatan ✅

**Target (perilaku NotebookLM):** kartu saran pertanyaan saat chat kosong (kontekstual
dari judul sumber); tombol "Simpan jadi catatan" pada tiap jawaban AI; daftar catatan
tersimpan per notebook (lihat/hapus/salin); riwayat chat + sitasi tetap (A08).

**Migrasi SQLite (auto):** tabel `learning_notes(id, notebook_id, user_id, title,
content, created_at)`. **Supabase: tidak ada.**

### 📌 REALISASI C04 (2026-09-22) — saran kontekstual + catatan ✅

**Format 1 — i18n:** +12 key → **4.372** (4 `learning_suggest_*`, `learning_save_note`,
`learning_note_saved/empty/copy/copied/delete_confirm`, `learning_notes_title/empty`),
id+en, 3 sumber identik.
**Format 2 — ditimpa:** `database.py` (tabel `learning_notes` + CRUD) · `studio_api.py`
(rute notes + field `savedNotes` di `_nb_map`) · `ChatPanel.tsx` (saran kontekstual +
tombol simpan + tombol catatan) · `LearningView.tsx` (modal catatan + handler) ·
`studio.ts` (`addNote`/`deleteNote`) · `translations.py` + 2× `messages.json` ·
`updater.py` (changelog) · roadmap ini.
**Format 3 — baru:** harness `c04_harness` (notes/fe_unit/fe_ssr).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-BLS8MtUr.js` 1.314,93 kB/gzip 348,76 kB · CSS 182,51 kB) · harness C04 **29/29**
(notes 13 + FE unit 8 + SSR 8) + regresi C01–C03 **184/184** · `py_compile` OK.
**Format 5 — kesimpulan:** chat kosong menampilkan saran kontekstual dari judul sumber
(konsep/ringkasan/kuis + banding bila ≥2 sumber; generik bila tanpa sumber); tiap
jawaban AI punya tombol Simpan jadi catatan (judul otomatis); modal Catatan tersimpan
mendukung lihat (expand), salin, hapus; riwayat chat + sitasi tidak berubah.
**Format 6 — migrasi:** SQLite otomatis (tabel `learning_notes` + indeks);
Supabase: tidak ada. Field API `savedNotes` (bukan `notes` — nama itu sudah dipakai
kolom teks notebook).

## C05 — 4 output Studio baru ✅

**Target:** tipe generator baru memakai pola `_studio_generate` + dialog konfigurasi
(A05) + daftar artefak (A06): **Briefing Doc** (laporan terstruktur + sitasi),
**Data Table** (tabel perbandingan dari sumber + ekspor CSV), **Infografik** (SVG
terstruktur dari poin kunci), **Slide Deck** (tayangan HTML + ekspor file tunggal).
Tanpa dependensi render video (Video Overview resmi backlog).

**Temuan user 2026-09-22 (warning AFC di terminal) → diperbaiki dalam C05:**
sebelum chat AI muncul `logger.warning` SDK: *"Direct use of automatic function
calling (AFC) in Models.generate_content is not recommended…"*.
**Akar masalah (hasil audit):** SDK `google-genai` (terverifikasi di v2.24.0)
mengaktifkan AFC secara *default* untuk SEMUA panggilan `Models.generate_content`
— tidak ada early-return untuk config tanpa tools (`models.py: generate_content` →
`should_disable_afc` = False bila tak disebut → warning sekali per proses via flag
`_logged_afc_warning`). Repo tidak memakai tools/function-calling sama sekali
(config hanya `temperature`), jadi ini murni noise terminal + overhead kecil
(deep-copy config), bukan error fungsional.
**Target perbaikan (C05-0, dikerjakan saat C05 dimulai):**
- `learning_helper.py`: helper `_gen_config(temperature)` →
  `GenerateContentConfig(temperature, automatic_function_calling =
  AutomaticFunctionCallingConfig(disable=True))` dengan fallback
  `model_fields` untuk SDK lama; dipakai di `_generate_once` + `_multimodal_once`
  (mencakup chat, Studio, guide, vision, transkrip — semua jalur Gemini).
- Alternatif yang ditolak: migrasi ke `Chat.send_message` (overkill — repo tak
  pakai tools; Chat API butuh manajemen history); filter logging (sembunyikan
  gejala, bukan perbaikan).
- Harness: mock `GenerateContentConfig` menangkap kwargs → assert
  `disable is True` (tanpa network/key).
**Status: ✅ selesai 2026-09-22 (lihat REALISASI C05 di bawah).**

### 📌 REALISASI C05 (2026-09-22) — 4 output Studio + AFC fix ✅

**Format 1 — i18n:** +20 key → **4.392** (4 label `learning_studio_*`, 4 blurb
dialog, 4 opsi `learning_opt_*`, `learning_artifact_items_rows/slides/points`,
`learning_artifact_export_csv/html`, 3 `learning_slide_*`), id+en, 3 sumber identik.
**Format 2 — ditimpa:** `learning_helper.py` (`_gen_config` + 4 prompt + param) ·
`studio_api.py` (rute + payload + slot `_nb_map` + parser + ekspor csv/html) ·
`studioOptions.ts` (registry 12 tipe) · `LearningView.tsx` (grid + render) ·
`StudioArtifactList.tsx` (pratinjau + tombol csv/html) · `studio.ts` (format) ·
`types.ts` (union gtype) · `translations.py` + 2× `messages.json` · `updater.py` ·
roadmap ini.
**Format 3 — baru:** `web/src/components/learning/StudioNewViews.tsx`
(DataTableView/InfographicView/SlideDeckView + parser) · harness `c05_harness/`
(afc/prompts/studio/export/fe_unit/fe_ssr).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-p4gTJ2yJ.js` 1.326,96 kB/gzip 351,58 kB · CSS 182,54 kB) · harness C05
**85/85** (afc 8 + prompts 16 + studio 16 + export 13 + FE unit 20 + SSR 12) +
regresi C01–C04 **213/213** · `py_compile` OK.
**Format 5 — kesimpulan:** 12 generator (Briefing Doc markdown + 3 JSON ketat
dengan parser server defensif + fallback mentah); tabel interaktif, infografik
SVG, slide bernavigasi; ekspor CSV (`;`+BOM utk Excel ID, gate data_table) dan
HTML mandiri (gate slide_deck, tombol+keyboard+print); warning terminal AFC
hilang (`disable=True` terverifikasi ke logika SDK asli; fallback SDK lama).
**Format 6 — migrasi:** tanpa migrasi DB (tipe = baris `learning_generations`);
Supabase: tidak ada. Desktop tidak tersentuh (8 tipe lama nol-perubahan).

### 📌 REVISI C05 (2026-09-22) — rumus LaTeX chat AI ✅

**Temuan user:** jawaban chat AI menampilkan `$\text{pH}$`, `$H^+$`, dll mentah.
**Akar:** `ChatPanel.tsx` memakai `ReactMarkdown` polos tanpa plugin math.
**Perbaikan:** `remark-math` + `rehype-katex` (katex 0.16.47) di ChatPanel;
CSS KaTeX via `@import` di `index.css` (bukan impor-JS, agar SSR esbuild aman).
Inline `$…$`, display `$$…$$` (multiline = blok, sebaris = inline), `$5` tunggal
tetap utuh; `&amp;` di paste user = artefak copy (render benar, dibuktikan harness).
**Bukti:** `tsc` 0 · build bersih (`index-CuQ40_Cl.js`, CSS 211,02 kB + font KaTeX)
· harness `c05rev_harness/math_ssr.tsx` **8/8** + regresi FE C01–C05 hijau.
Scope: ChatPanel saja; markdown Studio/artefak/catatan tidak berubah; i18n tetap 4.392.

---

# 🟡 KLASTER 2 — DATABASE & UPDATER (C06–C07)

## C06 — Database self-care ✅

**Akar masalah:** (1) key snake vs camel → tampil 0 B (`studio_api.py:1363-1371` vs
`SettingsView.tsx:67-72,99-101`); (2) auto-clean pertama tidak pernah jalan
(`database.py:6663-6672`); (3) tanpa jadwal harian/mingguan (interval = retensi);
(4) `wal_autocheckpoint=0` tanpa checkpoint berkala + VACUUM bisu
(`database.py:145-160,6630-6640`).

**Target:**
- Betulkan mapping key (respons camelCase konsisten) → ukuran tampil benar.
- Auto-clean berjalan sejak awal + **jadwal mandiri** (harian/mingguan/bulanan, terpisah
  dari retensi 1/7/30/90 hari).
- Rincian ukuran per tabel + total + tombol checkpoint/VACUUM manual dengan laporan
  sebelum/sesudah + error yang terlihat (tidak bisu).
- Checkpoint WAL berkala (tiap N menit saat idle + saat purge) sehingga `-wal` tidak
  membengkak; VACUUM di koneksi khusus non-pooled.

**Migrasi SQLite (auto):** `maintenance_state.schedule` (+ default `monthly`).
**Supabase: tidak ada.**

### 📌 REALISASI C06 (2026-09-22) — database self-care ✅

**Format 1 — i18n:** +10 key → **4.402** (`settings_cleanup_schedule`, 3
`settings_schedule_*`, `settings_cleanup_tables/total`, `settings_checkpoint_now`,
`settings_vacuum_now`, `settings_maintenance_done/failed`) + nilai
`settings_cleanup_auto` digenerikkan; id+en, 3 sumber identik.
**Format 2 — ditimpa:** `database.py` (migrasi `schedule`, jadwal mandiri,
auto-clean perdana, `db_table_sizes`, `run_checkpoint`, `run_vacuum`, timer
hormati interval) · `studio_api.py` (respons camelCase, aksi checkpoint/vacuum)
· `api_server.py` (timer saat jadi server) · `SettingsView.tsx` (jadwal + tabel
ukuran + tombol manual) · `studio.ts` · `translations.py` + 2× `messages.json` ·
`updater.py` · roadmap ini.
**Format 3 — baru:** harness `c06_harness/` (schema/purge/keys/ops).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-DCueK2Yg.js` 1.606,01 kB/gzip 436,61 kB · CSS 211,63 kB) · harness C06
**42/42** (schema 8 + purge 9 + keys 14 + ops 11) + regresi C01–C05rev
**306/306** · `py_compile` OK.
**Format 5 — kesimpulan:** ukuran DB tampil benar (camelCase); auto-clean jalan
sejak login pertama; jadwal harian/mingguan/bulanan mandiri dari retensi;
rincian per tabel (dbstat + fallback) + total; checkpoint/VACUUM manual dengan
laporan sebelum→sesudah + error terlihat; VACUUM di koneksi khusus; checkpoint
periodik 5 menit juga saat mode server (desktop tetap 10 dtk, tanpa diubah).
**Format 6 — migrasi:** SQLite otomatis (kolom `schedule` + backfill, diuji di DB
lama tanpa kolom); Supabase: tidak ada; desktop tidak tersentuh.

## C07 — Auto-updater yang benar-benar bekerja ✅

**Akar masalah:** auto-check hanya di PyQt legacy (`MainPyQt6.py:24500`); Web UI cuma
toast (`SettingsView.tsx:311-322`); worker tanpa try/except (hang 0%);
`_flatten_staging` 1 level + tanpa cek exe + tanpa log apply (UPDATE_RULES §10).

**Target:**
- `updater.py`: flatten multi-level (kenali `dist/CraftLife/`), **abort bila
  `CraftLife.exe` tidak ada**, tulis `_update_apply.log`, pakai checksum aset GitHub
  (`digest`) bila tersedia, tangani error jaringan/timeout dengan pesan jelas.
- Endpoint: `GET /api/update/check` (tetap) + `POST /api/update/download` (progres via
  polling `GET /api/update/status`) + `POST /api/update/apply` (staging + restart).
- **Dialog update Web UI** di Settings: versi tersedia + catatan rilis + tombol
  Download + progress bar + countdown auto-lanjut (keputusan user) + tombol Nanti.
- Auto-check saat start di mode web (flag di bootstrap + pemicu React sekali per sesi).
- Perbaiki `_UpdateWorker` PyQt (try/except → sinyal `failed`).
- **Langkah operator konkret** publikasi rilis (build → zip isi `dist/CraftLife/` →
  tag `v1.6.4` → lampirkan zip + sha256 → publish → user lama auto-update) —
  diantar sebagai dokumen + di chat.

### 📌 REALISASI C07 (2026-09-23) — auto-updater berfungsi ✅

**Format 1 — i18n:** +6 key → **4.408** (`update_download/downloaded`,
`update_check_failed`, `update_reopen_note`, `update_size`, `update_applying`;
`update_failed/checking/countdown/later/apply` + `btn_close` dipakai ulang) —
id+en, `translations.py` = 2× `messages.json` = `WEB_I18N_KEYS`.
**Format 2 — ditimpa:** `updater.py` (flatten multi-level, abort tanpa-exe,
`_update_apply.log`, digest sha256, `_clean_tag`, `check_update_status`, unduh
latar) · `api_server.py` (check verbose, `update/status/download/apply`, flag
`updateCheck` + cache 6 jam, whitelist) · `MainPyQt6.py` (try/except
`_UpdateWorker` → `failed`, CRLF utuh) · `GameContext.tsx` (pendingUpdate +
auto-check sekali/sesi) · `SettingsView.tsx` (cek → dialog) · `App.tsx` ·
`studio.ts` · `translations.py` + 2× `messages.json` · roadmap ini.
**Format 3 — baru:** `UpdateDialog.tsx` + `UpdateDialogHost.tsx` ·
`OPERATOR_RELEASE_v1.6.4.md` · harness `c07_harness/` (7 file).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-BmM4ZscF.js` 1.612,53 kB/gzip 438,47 kB · CSS 211,63 kB) · harness C07
**39/39** (flatten 6 + applylog 5 + check 6 + manager 5 + static 6 + cache 3 +
fkeys 8) + regresi C01–C06 **348/348** · `py_compile` OK.
**Format 5 — kesimpulan:** zip `dist/CraftLife/` dikenali; paket tanpa exe
diabort sebelum menimpa + tercatat di log; checksum GitHub diverifikasi; error
jaringan/timeout tampil jelas (bukan "terbaru" palsu); unduh latar bisa dipoll;
dialog Web (tawar → unduh → countdown 15 dtk → apply → restart) + auto-check
sekali per sesi; worker PyQt teruskan error ke dialog.
**Format 6 — migrasi:** tidak ada (SQLite/Supabase tak tersentuh; desktop hanya
fix worker + tanpa perubahan perilaku lain).

---

# 🟢 KLASTER 3 — DATE UTILITIES (C08)

## C08 — Tanggal selalu sinkron ✅

**Akar masalah:** `today` dibekukan saat bootstrap (`GameContext.tsx:460`) sementara jam
ticking (`Navbar.tsx:44-58`); `useState(today)` tidak ikut update
(`HealthFoodView.tsx:40`, `EconomyView.tsx:38,56,64`, `LoveSpaceView.tsx:216`);
heartbeat menandai tanggal sebelum bootstrap sukses (`GameContext.tsx:652-665`).

**Target:** `today` menjadi state ticking (diperbarui tiap menit dari jam server +
rollover tengah malam **tanpa** bootstrap penuh); halaman-halaman menyinkronkan
state tanggalnya saat `today` berubah; heartbeat hanya menandai setelah bootstrap
sukses + retry saat gagal; fallback UTC dihapus dari jalur utama.
+ Tambahan user (gabung C08): (H1) indikator habit sudah dikerjakan di Habits
  page; (H2) audit + betulkan streak/fail-streak habits (akar: mapping fallback
  lifetime + kolom fail_streak tak ada).

### 📌 REALISASI C08 (2026-09-23) — tanggal sinkron + streak habits benar ✅

**Format 1 — i18n:** +1 key → **4.409** (`habit_done_today`) — id+en,
`translations.py` = 2× `messages.json` = `WEB_I18N_KEYS`.
**Format 2 — ditimpa:** `database.py` (kolom `habits.fail_streak` + migrasi,
`complete_habit` up/down, skip parity) · `api_server.py` (`_map_habit` murni
tanpa fallback, `/api/clock`, `/api/tasks/rollover`, whitelist) ·
`GameContext.tsx` (today state ticking, heartbeat rollover ringan + ping clock)
· `HabitsView.tsx` (badge done + kunci tombol) · `EconomyView.tsx` ·
`HealthFoodView.tsx` · `LoveSpaceView.tsx` (sync prev-today) · `types.ts` ·
`translations.py` + 2× `messages.json` · `updater.py` · roadmap ini.
**Format 3 — baru:** `utils/serverClock.ts` · migrasi Supabase
`20260923000000_phase_c08_habits_fail_streak.sql` · harness `c08_harness/`
(6 file).
**Format 4 — command:** `tsc` **0 error** · `vite build` bersih
(`index-O0lT_OOa.js` 1.614,08 kB/gzip 439,08 kB · CSS 211,63 kB) · harness C08
**29/29** (migrate 3 + streak 7 + mapfix 4 + rollover 3 + clockdate 6 +
festatic 6) + regresi C01–C07 **416/416** · `py_compile` OK.
**Format 5 — kesimpulan:** bug "streak 29 bangkit" sembuh (mapping tanpa
fallback lifetime + `fail_streak` nyata: up reset, down +1, terlewat +1, luar
jadwal dipertahankan); kartu habit tampil badge done + tombol dikunci;
`today` ticking dari jam server (fallback UTC dibuang); rollover tengah malam
via refresh ringan (tandai hanya saat sukses + retry); 3 halaman ikut today
baru tanpa ganggu user yang melihat tanggal lain; desktop ikut sembuh (label
fail otomatis).
**Format 6 — migrasi:** SQLite otomatis (kolom `fail_streak` + backfill 0,
diuji di DB lama); Supabase opsional (1 file SQL); desktop: perilaku streak
membaik tanpa ubah kode UI.

---

# 🏁 FINALISASI — C09

## C09 — Finalisasi & rilis **v1.6.4** ✅

1. i18n sinkron 4 arah + angka final. 2. `updater.py` `APP_VERSION = "1.6.4"` +
   changelog fase C. 3. `README.md` revisi v1.6.4. 4. `RELEASE_NOTES_v1.6.4.md` +
   isi lengkap di chat. 5. Verifikasi penuh (gates §7) + smoke C1–C8. 6. Kesimpulan
   commit phase Format 1–7. 7. Satu commit + tag `v1.6.4` + tree bersih + instruksi upload.

### 📌 REALISASI C09 (2026-09-23) — finalisasi & rilis v1.6.4 ✅

**Format 1 — i18n:** sinkron 4 arah **4.409 = 4.409 = 4.409**
(`translations.py` ↔ 2× `messages.json`, nilai identik non-kosong),
`WEB_I18N_KEYS` **4.260** lengkap, 1.788 key terpakai dipindai — **0 hilang**;
commit phase **+85 key** (4.324 → 4.409).
**Format 2 — file final ditimpa:** README REVISI (badge v1.6.4, What's New,
Feature Tour, docs +4 baris, changelog, roadmap ✅, footer "Study & Stability")
· `updater.py` (1.6.4 + changelog C) · `web/package.json` + lock (1.6.4) ·
`.gitignore` (db-shm/-wal, logs/) + seluruh file fase C01–C08.
**Format 3 — file baru:** `RELEASE_NOTES_v1.6.4.md` ·
`2026-09-23-C01-C09-PHASE-SUMMARY.md` + 8 file C01–C08.
**Format 4 — command:** tanpa endpoint baru; smoke hidup `smoke_c09.py`
**31/31** + audit i18n **4/4** + `py_compile` 8 modul + `tsc` 0 + `vite build`
bersih (index-O0lT_OOa.js 1.614,08/gzip 439,08 · CSS 211,63) + regresi
**416/416** (ketat: bump versi sempat mematahkan 1 uji ekspektasi-remote C07 —
diperbaiki, hijau ulang).
**Format 5 — kesimpulan:** v1.6.4 "Study & Stability" — 3 area terpenuhi, 4 bug
fatal tertutup, semua gerbang §7 hijau, satu commit + tag `v1.6.4`, tree bersih.
**Format 6 — migrasi:** SQLite otomatis (blok fase C, teruji DB baru+lama);
Supabase 1 opsional (C08 `habits.fail_streak`).
**Format 7 — penutup:** commit phase C selesai; operator ikut runbook; upload:
push commit + tag, publish Release (zip + sha256).

---

# 📎 LAMPIRAN A — Master File List (diisi berjalan per fase)

## A.1 File yang ditimpa
- C01: `LearningShell.tsx` · `NotebookRail.tsx` · `LearningView.tsx` · `index.css` ·
  `translations.py` + 2× `messages.json` · `updater.py`
- C02: `learning_helper.py` · `database.py` · `api_server.py` · `studio_api.py` ·
  `SourcesRail.tsx` · `LearningView.tsx` · `SourceCard.tsx` · `studio.ts` · `index.css` ·
  `requirements.txt` · `translations.py` + 2× `messages.json` · `updater.py`
- C03: `learning_helper.py` · `database.py` · `studio_api.py` · `LearningView.tsx` ·
  `SourceCard.tsx` · `studio.ts` · `index.css` · `translations.py` + 2× `messages.json` ·
  `updater.py`
- C04: `database.py` · `studio_api.py` · `ChatPanel.tsx` · `LearningView.tsx` ·
  `studio.ts` · `translations.py` + 2× `messages.json` · `updater.py`
- C05: `learning_helper.py` · `studio_api.py` · `studioOptions.ts` ·
  `LearningView.tsx` · `StudioArtifactList.tsx` · `StudioNewViews.tsx` (baru) ·
  `studio.ts` · `types.ts` · `translations.py` + 2× `messages.json` · `updater.py`
- C06: `database.py` · `studio_api.py` · `api_server.py` · `SettingsView.tsx` ·
  `studio.ts` · `translations.py` + 2× `messages.json` · `updater.py`

## A.2 File baru
- C01: `web/src/components/learning/shellState.ts`
- C02: (hanya harness di luar repo: `c02_harness/`)
- C03: (hanya harness di luar repo: `c03_harness/`)
- C04: (hanya harness di luar repo: `c04_harness/`)
- C05: `web/src/components/learning/StudioNewViews.tsx` + harness `c05_harness/`
- C06: (hanya harness di luar repo: `c06_harness/`)

---

# 📎 LAMPIRAN B — Endpoint, Env & i18n Baru (diisi berjalan)

## B.1 Endpoint baru
- C02: `POST /api/learning/notebooks/<nid>/sources/<sid>/re-extract` ·
  `GET /api/learning/sources/<sid>/file` (unduh berkas asli, owner-only)
- C04: `POST /api/learning/notebooks/<nid>/notes` (simpan) ·
  `POST /api/learning/notebooks/<nid>/notes/<id>/delete` (hapus; daftar via `_nb_map`)
- C05: `POST /api/ai/briefing-doc` · `POST /api/ai/data-table` ·
  `POST /api/ai/infographic` · `POST /api/ai/slide-deck` (+ alias snake_case) ·
  `GET /api/learning/generations/export?format=csv|html` (gate per tipe)
- C06: `POST /api/settings/cleanup` aksi `checkpoint`/`vacuum` (+ `set` terima
  `schedule`; GET camelCase + `tableSizes`)
_(`POST .../sources` + field `url` dipakai C03 — bukan endpoint baru._
_(C04: notes CRUD · C05: 4 tipe generate · C07: update download/status/apply)_

## B.2 Env baru
_(bila ada)_

## B.3 Key i18n baru per fase
_(basis v1.6.3 = 4.325 key)_
- C01: +5 → **4.330** (`learning_src_hide`, `learning_src_show`, `learning_studio_hide`,
  `learning_studio_show`, `learning_drag_hint`)
- C02: +23 → **4.353** (6 `learning_source_type_*` + 16 antrean/berkas/re-extract +
  `learning_supported_types`; daftar lengkap di REALISASI C02)
- C02-revisi: +1 → **4.354** (`learning_pdf_no_text`)
- C03: +6 → **4.360** (`learning_add_text`, `learning_add_website`,
  `learning_add_youtube`, `learning_url_ph`, `learning_fetch_save`,
  `learning_url_invalid`)
- C04: +12 → **4.372** (4 `learning_suggest_*`, `learning_save_note`,
  `learning_note_saved`, `learning_note_empty`, `learning_notes_title`,
  `learning_notes_empty`, `learning_note_copy`, `learning_note_copied`,
  `learning_note_delete_confirm`)
- C05: +20 → **4.392** (4 `learning_studio_*`, 4 `learning_dialog_blurb_*`,
  4 `learning_opt_*`, `learning_artifact_items_rows`,
  `learning_artifact_items_slides`, `learning_artifact_items_points`,
  `learning_artifact_export_csv`, `learning_artifact_export_html`,
  3 `learning_slide_*`)
- C06: +10 → **4.402** (`settings_cleanup_schedule`, 3 `settings_schedule_*`,
  `settings_cleanup_tables`, `settings_cleanup_total`, `settings_checkpoint_now`,
  `settings_vacuum_now`, `settings_maintenance_done`, `settings_maintenance_failed`)

---

# 📎 LAMPIRAN C — Checklist Smoke Test v1.6.4 (dijalankan di C09)

| # | Skenario | Harapan |
|---|---|---|
| S1 | API hidup & versi | `/api/health` ok, `/api/version` = 1.6.4 |
| S2 | Learning drag | Seret divider Sumber/Studio → lebar berubah + tersimpan |
| S3 | Learning upload | Upload 5 file campuran (pdf+xlsx+png+mp3+md) → semua jadi sumber |
| S4 | Learning web | Tempel URL + YouTube → jadi sumber terekstrak |
| S5 | Studio baru | Generate Briefing/Data Table/Infografik/Slide Deck → artefak + ekspor |
| S6 | DB ukuran | Settings tampil ukuran > 0 + rincian tabel |
| S7 | DB jadwal | Set harian → due → auto purge + laporan |
| S8 | Updater | Dialog update + progres + apply (simulasi/staging) |
| S9 | Tanggal | Rollover tengah malam → semua halaman ikut tanpa reload |
| S10 | Regresi | Harness A11/A12/A13/A15 tetap hijau |

---

# 📎 LAMPIRAN D — Backlog (BUKAN bagian commit phase ini)

| # | Item | Alasan tunda |
|---|---|---|
| D01 | Video Overview (render ffmpeg) | Berat & berisiko — keputusan user |
| D02 | Deep Research agent + kolaborasi notebook | Butuh infrastruktur cloud + biaya |
| D03 | Integrasi Google Drive/Docs/Slides | Butuh OAuth + API Google |
| D04 | Backlog lama B01–B08 (env hygiene, file mati, duplikat route, code-splitting, pytest, pecah GameContext/MainPyQt, tema anti-drift) | Di luar scope C; B04/B03 kecil boleh diselipkan bila menyentuh file yang sama |

---

*Roadmap disusun dari audit kode langsung pada v1.6.3 (2026-09-22). Setiap fase menyebut
file + nomor baris bukti.*
