"""CraftLife — auto-updater (Supabase atau GitHub Releases).

Alur operator (publish rilis):
  SUMBER = "supabase":
    1. Build versi baru (PyInstaller --onedir).
    2. Zip ISI folder dist/CraftLife -> craftlife-X.Y.Z.zip (tanpa .env & craftlife.db).
    3. Upload zip ke bucket 'app-updates' + insert ke public.app_releases.
  SUMBER = "github"  (REKOMENDASI — egress GRATIS, tidak masuk kuota Supabase):
    1. Build + zip seperti di atas.
    2. Buat GitHub Release dengan tag = versi (mis. v1.2.0), lampirkan zip.
    3. Selesai. App membaca https://api.github.com/repos/<repo>/releases/latest.

Alur client:
  check_for_update()  -> info bila versi lebih baru (dengan backoff anti-loop), else None.
  download_release()  -> zip terverifikasi sha256 (bila tersedia).
  apply_downloaded()  -> ekstrak staging + updater batch (Windows), app lalu keluar.

PENTING anti-loop (penghemat cached egress):
  - Versi yang sama TIDAK di-download berulang: ada backoff (default 24 jam) +
    catatan status di _update_state.json di folder aplikasi.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# v1.6.3 "Quality of Life" — commit phase A01–A14 (satu rilis):
#   A01–A03 lirik · A03.5 unduhan · A04–A08 Learning · A09–A12 Love Space · A13 Home · A14 rilis.
#   A08 (selesai 2026-09-15): sitasi sumber + grounding di jawaban AI, Audio Overview dua host
#   dengan suara mengikuti bahasa transkrip + pemutar MP3 interaktif (Range/seek), dan migrasi
#   dependency AI `google.generativeai` → `google.genai` (SDK lama end-of-support).
#   A09 (selesai 2026-09-16): Love Space → tab Plans — catatan acara yang dulu mustahil diisi,
#   edit acara, Special Day dengan pengulangan tahunan + pengingat H-n, hitung mundur, dan
#   hari istimewa otomatis dari profil. Migrasi SQLite otomatis (6 kolom relationship_events);
#   Supabase opsional lewat 20260916000000_phase_a09_love_special_days.sql.
#   A10 (selesai 2026-09-16): Love Space → tab Memories & Bucket List — kenangan kini bisa
#   diedit, diberi emoji pilihan, tag, bintang favorit, dan ditautkan ke foto galeri; bucket list
#   punya progres nyata, kategori, target tanggal (badge H-n/terlewat), catatan, prioritas, filter,
#   dan tombol "Simpan jadi kenangan" saat tercapai (idempoten). Migrasi SQLite otomatis (9 kolom
#   baru: 5 memories + 4 bucket_items, plus 2 indeks); Supabase opsional lewat
#   20260916010000_phase_a10_love_memories_bucket.sql.
#   A11 (selesai 2026-09-16): Love Space → tab connection/cycle/gallery diprofesionalkan.
#   Connection: riwayat jawaban (cari/filter kategori/favorit/jawab ulang), prompt favorit,
#   grafik tren mood 30/90 hari + skor koneksi, streak check-in. Cycle: riwayat siklus yang bisa
#   diedit + catatan + tombol "Jadikan pengingat" H-3/H-1 (idempoten), prediksi ovulasi/jendela
#   subur + badge keyakinan dari 3 siklus terakhir. Gallery: sampul album, jumlah & tanggal album,
#   aksi massal (pindah album/hapus/visibilitas) lewat satu endpoint, lightbox bernavigasi
#   keyboard (← → / Esc / zoom). Perbaikan bug: sync cloud penghapusan foto massal dulu no-op
#   karena `cloud_id` dibaca setelah baris dihapus. Migrasi SQLite otomatis (menstrual_cycles.updated_at,
#   love_albums.cover_photo_id + 2 indeks); Supabase opsional lewat
#   20260916020000_phase_a11_love_cycle_gallery_alignment.sql.
#   Paket baru yang WAJIB ada di mesin user: google-genai>=1.0.0, edge-tts>=6.1.0, gTTS>=2.5.0.
#   A12 (selesai 2026-09-16): Love Space → tab `overview` menjadi dashboard pasangan
#   (hero "bersama N hari / M tahun" dari tanggal jadian, kartu Hari istimewa berikutnya
#   + hitung mundur + tombol "Buat pengingat", cincin skor kedekatan + rincian check-in,
#   grid 6 statistik, aksi cepat) dan Special Day kini benar-benar berujung pada pengingat:
#   mesin `get_next_reminder_datetime` mengenal `repeat_type='yearly'` (29 Feb → 28 Feb),
#   ada endpoint idempoten `POST /api/love/events/<id>/create-reminder` (acara ATAU ulang
#   tahun/hari jadi dari profil), opsi **Tahunan** + input batas akhir di halaman Reminders
#   dengan badge "Tahunan · tiap {tanggal}", dan chip satu baris di Beranda. Migrasi SQLite
#   otomatis: `reminders.repeat_until` (kolom ini selama ini dirujuk kode tetapi belum pernah
#   ada), `reminders.source_ref` + indeks. Perbaikan bug dari uji A12: database BARU gagal
#   `init_db()` (indeks `love_albums` dibuat sebelum tabelnya — warisan A11), update reminder
#   yang tidak mengirim `repeat` menghapus pengulangan tahunan secara diam-diam, dan
#   `repeat_until`/`reminder_datetime` yang tidak valid membuat proses pengingat gagal.
#   A13 (selesai 2026-09-16): Home → Year Wrapped. Laporan ekonomi di dialog Wrapped tidak lagi
#   memakai "Rp" hardcoded: seluruh angka (pemasukan, pengeluaran, selisih bersih) lewat
#   `formatMoney(v, user.currency)` dari `web/src/utils/currency.ts` (satu-satunya formatter resmi),
#   ditambah chip mata uang aktif + catatan kurs kecil dari `/api/catalog/currency`. Seluruh teks
#   dialog kini i18n id+en (dulu hardcoded Indonesia). Polish laporan: kartu **Selisih bersih**
#   berwarna dinamis, **rasio tabungan**, rincian **per tipe** (habits/dailies/quests/sport dari
#   `by_type`), top habit dengan ikon + bar relatif, **pemilih tahun** (`GET /api/year-wrapped?year=`,
#   baru juga mengembalikan `years[]` dari `db.get_wrapped_years`), tombol **Salin ringkasan**
#   (clipboard) + **Unduh .txt**, confetti `canvas-confetti`, dan pemisahan **empty-state** dari
#   **error** (dulu keduanya tampil "belum ada aktivitas"). Di halaman Reminders, badge
#   **Tahunan · tiap {tanggal}** kini bisa diklik untuk langsung membuka dialog edit reminder itu.
#   Tidak ada migrasi (hanya membaca tabel yang sudah ada).
#   A15 (selesai 2026-09-16): perbaikan rail kiri halaman Learning. Ikon notebook kini benar-benar
#   tersimpan (`learning_notebooks.icon`/`description`/`updated_at`, ALTER otomatis di init_db),
#   `POST /api/learning/notebooks` meneruskan `icon`/`description`, dan `…/<id>/rename` menerima
#   `title`/`icon`/`description` secara parsial (mengganti ikon tidak mengosongkan judul). Rail kiri
#   menggambar satu avatar per notebook (emoji pilihan user, fallback inisial judul) dengan lebar
#   mengikuti token `--rail-w` (72/220 px), judul `truncate`, tombol **+ Notebook** ikut melebar, daftar
#   panjang bisa digulir. Dialog Ganti nama juga bisa mengganti emoji (pemilih `NB_EMOJI` dipakai bersama).
#   i18n: key baru `learning_icon_label` → total 4.325.
# v1.6.4 (dalam pengerjaan) — commit phase C01–C09:
#   C01 (selesai 2026-09-22): Learning shell baru ala NotebookLM — 3 panel sejajar
#   (Sumber ‖ Chat ‖ Studio) dengan divider seret + collapse (pengganti tombol preset
#   Sempit/Sedang/Lebar), preferensi v2 + migrasi otomatis, mobile tab tetap.
#   i18n: +5 key → total 4.330.
#   C02 (selesai 2026-09-22): multi-upload (input multiple + drag-and-drop + antrean
#   berurutan) 23 tipe berkas — dokumen terstruktur (xlsx/xls/pptx/csv/epub/rtf),
#   gambar via vision AI + audio via transkrip Gemini (butuh API key, else penanda);
#   berkas asli disimpan di learning_sources/<uid>/ + bisa diunduh/diekstrak-ulang;
#   migrasi SQLite otomatis (5 kolom + indeks); hapus sumber hanya menyentuh berkas
#   kelolaan app. i18n: +23 key → total 4.353.
#   C02-revisi (2026-09-22, hybrid): berkas asli pdf/gambar dilampirkan ke Gemini
#   saat chat/generate (maks 3, ≤20 MB); PDF scan lolos upload + warning; impor gagal
#   bersihkan yatim. i18n: +1 key → total 4.354.
#   C03 (selesai 2026-09-22): sumber URL di Web UI (website fetch+bersih, YouTube
#   transkrip API ganda + judul oEmbed, deteksi otomatis server-side); panduan 1–2
#   kalimat per sumber (AI backfill malas + kolom summary). i18n: +6 → total 4.360.
#   C04 (selesai 2026-09-22): saran chat kontekstual dari judul sumber + simpan
#   jawaban AI jadi catatan (lihat/salin/hapus per notebook). Field `savedNotes`.
#   i18n: +12 key → total 4.372.
#   C05 (selesai 2026-09-22): 4 output Studio baru (Briefing Doc, Data Table,
#   Infografik, Slide Deck) + ekspor CSV/HTML + warning AFC terminal dihilangkan
#   (disable eksplisit). i18n: +20 key → total 4.392.
#   Revisi C05 (2026-09-22): rumus LaTeX chat AI dirender KaTeX.
#   C06 (selesai 2026-09-22): database self-care — respons camelCase (ukuran tampil),
#   jadwal auto-clean mandiri, auto-clean perdana, rincian per tabel, checkpoint/
#   VACUUM manual + periodik. i18n: +10 key → total 4.402.
#   C07 (selesai 2026-09-23): auto-updater berfungsi — flatten staging multi-level
#   (dist/CraftLife/), abort bila exe absen + _update_apply.log, checksum digest
#   GitHub, check verbose (beda 'terbaru' vs 'gagal cek'), unduh latar untuk web.
#   i18n: +6 key → total 4.408.
#   C08 (selesai 2026-09-23): tanggal sinkron (today ticking, rollover ringan,
#   sync halaman) + streak habits benar (fail_streak nyata, mapping murni) +
#   indikator done. i18n: +1 key → total 4.409.
#   C09 (selesai 2026-09-23): finalisasi & rilis v1.6.4 — bump versi, sinkron
#   i18n 4 arah (4.409), README REVISI, RELEASE_NOTES, rekap fase, verifikasi
#   penuh + smoke hidup, satu commit + tag v1.6.4.
# v1.6.5 (selesai 2026-09-23): food database update — dedupe 850→774 (0
# duplikat), 9 koreksi gizi, 33 item baru (ciki/kerupuk/minuman), migrasi DB
# lama idempoten (sinkron kanonik + gabung duplikat semantik, log aman).
# v1.6.7 (selesai 2026-09-25): D01 code-split per view (JS awal -72%), D02
# ErrorBoundary dwibahasa, D03a tab Anggaran Economy, D03b favorit & terakhir
# Nutrition, D04 sapu Esc 47 dialog + CountUp + dialog pintasan + sapu emoji
# sub-header. Nol fitur dikurangi; migrasi aditif (economy_budgets,
# user_food_favorites) + export/impor ikut.
# v1.6.7 batch 2 (selesai 2026-09-25): E01 palet keyboard + aksi tugas, E02
# lonceng notifikasi, E03 timer tidur musik, E04 focus trap 13 dialog, F01 50
# makanan + F02 50 minuman baru (katalog 774->874, seed otomatis idempoten),
# F03 sortir grid nutrisi + preset porsi. i18n: +5 key -> total 4.447.
#
# M02 (2026-10-06): test suite + CI established before any refactor (roadmap
#   K20). No feature or schema change, so APP_VERSION is unchanged at 1.7.4.
#   Before this entry the repository had 0 Python tests and 0 frontend tests.
#   Added: tests/ (73 tests, stdlib unittest only — no new third-party test
#   dependency, per §8), packages/craftlife-core vitest suite (33 tests over
#   currency.ts and serverClock.ts), scripts/verify_gates.py implementing the
#   ten §7 gates plus the K22 version anchors and the §9 secrets rule, and
#   .github/workflows/ci.yml which runs that runner.
#   Product fix found by the new suite: settings_fx_title, settings_fx_ambient
#   and settings_fx_ambient_desc were used by the P9 ambient-LED toggle but
#   never registered, so English users fell back to Indonesian. i18n:
#   +3 keys -> total 4,616, still identical across id and en.
#   Bundle unchanged: entry index-CGxT26e0.js 462.61 kB / gzip 144.89 kB.
#
# M03 (2026-10-06): row-level sync prerequisites (G3 + G4). Purely additive
#   schema work, so APP_VERSION is unchanged at 1.7.4 and no Supabase migration
#   is added. All 41 tables that take part in personal sync (the 40
#   EXPORT_TABLES plus debt_notes) gain uuid, rev, updated_at and deleted_at,
#   a UNIQUE index on uuid, per-user (user_id, deleted_at) and
#   (user_id, updated_at) indexes, and an AFTER INSERT trigger that stamps uuid
#   and updated_at. SQLite auto-migration only: columns are added by
#   _safe_alter inside init_db(), so an existing database picks them up on next
#   launch and rows already present are backfilled once (WHERE uuid IS NULL),
#   which makes repeated launches a no-op. No integer primary key is altered,
#   and nothing reads the new columns yet.
#   Closes G3 (integer PKs are remapped on import, so entity identity was not
#   stable across devices) and G4 (no tombstone, so deletes could not
#   propagate). G10 stays open on purpose: adding debt_notes to EXPORT_TABLES
#   was measured to break cloud restore for every existing user, and the
#   obvious workaround would silently delete local debt notes instead.
#   Cost, recorded as a G5 risk: the four columns add ~111 bytes per row,
#   +44.8% on the test snapshot, which projects to +21.2 MB at the 200,000-row
#   ceiling against the 8 MB hard cap.
#
# M04 (2026-10-07 .. 2026-10-08): sync engine, channels A and B (closes G1 and
#   G4). Staged over four commits; APP_VERSION stays 1.7.4 because nothing here
#   is a user-visible release on its own — the sync engine is infrastructure
#   that M05+ builds on.
#   M04a: append-only channel for the 7 measured log tables (food_logs,
#     water_logs, health_logs, task_history, pomodoro_sessions, sport_rep_logs,
#     supplies_tx). The roadmap named 9; measurement of which tables are truly
#     append-only with no user-entity FK said 7, and the measurement won.
#     Supabase migration 20261007000000_phase_m04a_entity_channel_a.sql.
#   M04b: row-level 3-way merge for all 34 mutable tables. Applying a cloud
#     snapshot now MERGES per field instead of replacing the document, so a
#     habit edited on Desktop and a meal logged on Android both survive.
#     Deletes propagate through an AFTER DELETE trigger into sync_tombstones
#     rather than by rewriting 47 delete sites and ~361 queries to filter
#     deleted_at (measured cost of the roadmap's literal wording, and the
#     reason for that approved deviation). Supabase migration
#     20261008000000_phase_m04b_entity_channel_b.sql.
#   Foreign-key fix (same day): PRAGMA foreign_keys is a no-op inside a
#     transaction, so init_db()'s attempt to re-enable it was silently ignored
#     and the pooled connection ran with foreign keys OFF for the whole process
#     lifetime — no constraint enforcement and no ON DELETE CASCADE, which also
#     meant cascaded children were never tombstoned. The same in-transaction
#     pragma sat in six finally blocks. Fixed by committing before the pragma;
#     ForeignKeyEnforcementTest pins it (4 of 6 fail when the bug is restored).
#   M04c: sync status panel and a recoverable conflict surface. Also fixed
#     cloud_api._sync_out(), which called itself with no base case and raised
#     RecursionError on every call, making /api/cloud/sync-now,
#     /migrate-local and /conflict unable to return anything at all. That bug
#     predates M04 entirely (first commit). i18n: +21 keys -> 4,637, still
#     identical across id and en. Python suite 131 -> 180 tests.
# M05a (2026-10-11): identity layer untuk CraftLife Rules API. Tahap pertama
#   dari M05 yang dipecah jadi a-e (identity -> scoping -> rate limit/audit ->
#   store abstraction -> deployment). Tidak ada perubahan skema, tidak ada
#   migrasi Supabase, dan APP_VERSION tetap 1.7.4.
#   rules_auth.py memverifikasi Supabase JWT dengan pustaka standar saja (HS256;
#   §8 melarang dependensi baru, jadi kunci asimetris ditolak dengan kode
#   unsupported_alg, bukan diterima diam-diam). Identitas jadi per-request lewat
#   contextvars, karena _state["user_id"] bersifat global proses dan dua user
#   akan saling menimpa begitu layanan ini multi-tenant.
#   Penting untuk desktop: strict mode MATI secara default dan hanya aktif bila
#   CRAFTLIFE_JWT_SECRET di-set. Selama itu tidak di-set, tidak satu pun jalur
#   local-only yang berubah perilaku (P1/P4) — dan itu dipaku oleh tes, bukan
#   hanya diklaim.
#   Python 193 -> 240 tests.
# M05b (2026-10-11): tenant scoping untuk Rules API. Tahap kedua M05.
#   Menguji kriteria penerimaan "JWT user A -> tidak pernah membaca data user B"
#   secara empiris: setiap tabel ber-user_id diisi satu baris ber-sentinel milik
#   user B, lalu sebagai user A seluruh 301 route GET yang dipakai client web
#   dipanggil dan badan responsnya dipindai. Hasil: 0 kebocoran di 58 tabel.
#   Tidak ada perubahan kode produk di tahap ini - pengukurannya yang baru, dan
#   pengukurannya ternyata menunjukkan scoping yang ada sudah benar.
#   Satu peringatan yang tertanam di tes: food_items bersifat hibrida
#   (is_custom=0 adalah katalog bawaan 1.074 makanan yang memang dibagikan).
#   Probe versi pertama menandainya sebagai bocor; itu salah probe, bukan salah
#   produk, dan "memperbaiki" query-nya akan merusak katalog semua pengguna.
#   Python 240 -> 247 tests. Tidak ada perubahan skema, tidak ada migrasi.
# M05c (2026-10-11): rate limiting, audit logging, dan penutupan debug endpoint.
#   Tahap ketiga M05. Ketiga hal ini diukur TIDAK ADA sebelumnya, dan semuanya
#   jadi berbahaya begitu layanan internet-facing (R5).
#   rules_guard.py: token bucket per identitas (fallback ke IP) dengan ember
#   berukuran tetap dan kunci basi dibuang; batas dipasang SEBELUM auth supaya
#   banjaran tanpa identitas pun terkena. Audit log menulis method/path/status/
#   ip untuk operasi mutating dan kegagalan saja - isi request TIDAK PERNAH
#   disimpan karena body bisa berisi kata sandi dan data kesehatan, dan itu
#   dipaku oleh tes yang memeriksa skema, bukan hanya perilaku.
#   /api/admin/debug dinonaktifkan di Rules API (404): di layanan multi-tenant
#   tidak ada "admin" yang sah untuk memberi diri sendiri XP/gold lewat HTTP
#   (K9). Di desktop tetap ada - itu alat milik pengguna sendiri, dan
#   menghilangkannya akan jadi regresi P4.
#   /api/version tidak lagi membocorkan path absolut database di strict mode.
#   Skema SQLite: tabel baru rules_audit_log (auto-migrate di init_db, idempoten).
#   Tidak ada migrasi Supabase. Python 247 -> 287 tests.
#   Batasan yang dinyatakan jujur: rate limiter in-memory per-proses. Dengan
#   lebih dari satu replika batasnya jadi N x konfigurasi dan butuh store
#   bersama - itu keputusan deployment (M05e), bukan sesuatu yang dipalsukan.
# M05d (2026-10-11): lapisan penyimpanan, domain pertama = cloud.
#   cloud_api.py memanggil database.<fungsi> langsung di 25 tempat. Selama hanya
#   ada satu penyimpanan itu tidak salah - hanya menutup pintu: menukar SQLite
#   ke Postgres di sisi server berarti menyunting setiap pemanggilan sekaligus,
#   dalam satu perubahan yang tidak bisa diuji per bagian (R3 bertemu R5).
#   storage.py menaruh 16 operasi di satu antarmuka. SqliteCloudStorage murni
#   delegasi: tidak ada logika, tidak ada perubahan perilaku (P4). Domain kini
#   memanggil store.get_cloud_user_link(uid), bukan database.get_cloud_user_link(uid).
#   cloud_api.py tidak lagi mengimpor database sama sekali, dan itu dipaku oleh
#   tes AST - kalau ada yang menambahkannya lagi, build gagal.
#   Yang TIDAK diverifikasi: tidak ada adapter Postgres di sini. Kode produksi
#   tidak punya driver Postgres dan §8 melarang dependensi baru, jadi "bisa
#   ditukar" masih kemungkinan struktural, bukan sesuatu yang pernah dijalankan.
#   Adapter dan keputusan penyimpanannya milik M05e.
#   tests/harness.py: "storage" ditambahkan ke _DB_DEPENDENTS. Tanpa itu,
#   cloud_api yang diimpor ulang menarik storage LAMA yang masih menunjuk
#   DB_PATH yang sudah dihapus.
#   Tidak ada perubahan skema, tidak ada migrasi. Python 287 -> 306 tests.
# Audit Pemeliharaan Data (2026-10-11): fitur diaudit, tidak ada bug produk.
#   Semua 7 operasi diuji lewat HTTP sungguhan dan semuanya bekerja: status,
#   set retensi (5 nilai sah + 3 ditolak), set auto, set jadwal (3 sah + 1
#   ditolak), checkpoint (membebaskan 1,5 MB), VACUUM, dan purge.
#   Tiga janji yang tertulis di UI-nya sendiri diverifikasi sebagai janji:
#   file backup BENAR-BENAR ada di disk (1,8 MB), kelima tabel data master
#   utuh, dan riwayat yang masih dalam retensi selamat di 9 tabel.
#   Keterbatasan yang ditemukan dan DIPAKU sebagai batas yang diketahui, bukan
#   diperbaiki diam-diam: jadwal auto-purge hanya diperiksa saat configure(),
#   yaitu sekali per login desktop. Aplikasi yang dibiarkan menyala berminggu-
#   minggu tanpa login ulang tidak memeriksa ulang jadwalnya, jadi "Harian"
#   pada praktiknya berarti "tiap kali login". Untuk desktop yang dibuka-tutup
#   tiap hari itu setara.
#   Tidak ada perubahan kode produk. Python 306 -> 348 tests.
# Backup tracker ke cloud (2026-10-12): menutup lubang P6 di sisi cloud.
#   Paket gratis Supabase tidak punya backup otomatis. Backup lokal yang sudah
#   ada hanya menyelamatkan SQLite di satu perangkat; ia tidak menolong kalau
#   perangkat itu hilang atau database cloud-nya bermasalah.
#   Harian, otomatis, dipicu saat login (bersama auto-purge, thread terpisah
#   supaya kegagalan satu tidak membatalkan yang lain). Snapshot 40 tabel
#   dikompresi gzip lalu diunggah ke bucket privat `tracker-backups` di folder
#   milik pengguna. Rotasi menyimpan 14 terbaru.
#   Keamanan: policy storage owner-only di KEEMPAT operasi, termasuk SELECT.
#   Sengaja tidak meniru profile-photos yang membolehkan setiap pengguna
#   terautentikasi membaca objek siapa pun - isi satu backup adalah seluruh
#   data pribadi pengguna.
#   Admin: backup diizinkan (baca-saja, bukan vektor curang), restore tetap
#   ditolak (menulis). Ekspor biasa tidak berubah perilaku sama sekali.
#   Restore membuat backup LOKAL lebih dulu, dan menolak path di luar folder
#   pemanggil maupun path traversal.
#   Migrasi Supabase baru: 20261012000000_tracker_backups_bucket.sql (19 -> 20).
#   SQLite: 2 kolom baru di maintenance_state (last_backup_at, backup_auto).
#   Enam operasi baru lewat lapisan storage M05d, bukan panggilan database
#   langsung. Python 348 -> 484 tests.
#   Permukaan UI: panel "Backup Cloud" di Settings (status backup terakhir,
#   jumlah cadangan, toggle otomatis, tombol Backup Sekarang, daftar cadangan
#   dengan tombol Pulihkan). 15 key i18n dwibahasa baru (4637 -> 4652).
#   Key `settings_backup_now` sudah dipakai tombol backup database lokal, jadi
#   tombol cloud memakai `settings_backup_cloud_now` - menimpanya akan mengganti
#   label fitur lain.
# M09a (2026-10-22): pet gacha menjadi server-authoritative (roadmap M09
#   tahap 1, K13). Spin untuk pengguna cloud-linked tidak lagi diundi client:
#   migrasi Supabase 20261022000000_phase_m09a_pet_gacha_server.sql (21
#   migrasi) menambah katalog pets_server (39 pet, seed dari PETS_DATA),
#   cloud_user_pets, cloud_pet_spin_state, log idempoten cloud_pet_spins,
#   dan RPC spin_pet_cloud/fetch_cloud_pets dengan konstanta persis jalur
#   lokal (biaya 120, odds 34/26/18/12/8/2, pity 10/30, duplikat 60 EXP).
#   Gold dipotong lewat reward_ledger (spend_gold), baris state dikunci
#   FOR UPDATE agar dua device tidak bisa mengundi paralel, dan key yang
#   sama memutar ulang hasil pertama. Desktop: /api/pets/spin bercabang ke
#   cloud_api.pets_cloud_spin bila terhubung cloud; hasil server
#   dicerminkan ke user_pets/pet_spin_state lokal (nilai absolut, aman
#   diterapkan ulang) + cache cloud_pets_cache/cloud_pet_spin_state_cache.
#   Pengguna local-only tidak berubah sama sekali (spin lokal, P1).
#   APP_VERSION tetap 1.7.4 (rilis v2.0.0 milik M14). Python 484 -> 496 tes
#   (+12 M09a, termasuk pembaruan fake storage M05d). Yang BELUM
#   diverifikasi: migrasi belum diterapkan ke Supabase live dan RPC belum
#   dijalankan terhadap Postgres sungguhan - itu langkah operator.
# M09b (2026-10-22): talents, achievements, dan reward boss menjadi
#   server-authoritative + P10. Migrasi 20261022010000_phase_m09b_
#   talents_achievements_boss_server.sql (22 migrasi): constraint sumber
#   ledger diperluas ('pet_spin' dari M09a + 'boss_local'), katalog
#   talents_server (30) & bosses_server (16), cloud_user_talents +
#   unlock_talent_cloud (validasi class/level/poin/prasyarat persis
#   can_unlock_talent), cloud_user_achievements + claim achievement kini
#   mensyaratkan catatan unlock server, dan claim_boss_reward_cloud
#   (angka dari katalog dibagi member_count; satu key satu klaim).
#   Desktop: unlock_talent & claim_boss_reward mengantre perintah Kanal C
#   (talent_unlock/boss_reward, prioritas drain 70), handler sync_service
#   memanggil RPC-nya dan mencatat unlock sebelum klaim achievement;
#   boss_rewards menyimpan member_count (kolom baru, baris lama default 1);
#   GET /api/profile/talents menyegarkan talent dari cloud bila terhubung.
#   P10: jalur beli pet langsung dihapus dari UI (PyQt ShopPage + web
#   GameContext/rpg/ShopView) — pet hanya dari spin. db.adopt_pet dan
#   route /api/pets/adopt dipertahankan (bukan UI). Batas yang dicatat:
#   member_count guild LOKAL dilaporkan client (guild lokal tidak ada di
#   server); boss guild cloud sudah otoritatif sejak Phase 4C.
#   APP_VERSION tetap 1.7.4. Python 496 -> 512 tes (+16 M09b).
# M09c (2026-10-23): layar RPG Android — Pets (koleksi + spin), Shop
#   (katalog beli + inventaris pakai/equip/jual), Crafting (resep +
#   enchant), Achievements (progres + klaim). Tanpa endpoint baru: semua
#   memakai route yang sudah ada (GET /api/pets, /api/pets/odds,
#   /api/catalog/{shop,pets,recipes}, /api/inventory, /api/achievements;
#   POST /api/pets/spin, /api/shop/{buy,sell,use,equip,craft,enchant},
#   /api/achievements/{id}/claim). Perintah Kanal C tidak diantrekan
#   offline — server yang memutuskan; katalog pet digabung ke koleksi
#   karena _map_pet tidak membawa nama/ikon. 3 kunci i18n mobile baru
#   (4.700 -> 4.703). Android vitest 245 -> 252 (+7 model RPG).
# M10 (2026-10-23): Social di Android sekaligus — hub Social, Friends +
#   Chat (balas + reaksi + indikator mengetik), Guild lokal & online,
#   PvP, Leaderboard, Love Space 6 tab, Notifications. Mayoritas route
#   sosial SUDAH mengalir lewat api_server (life_api -> studio_api ->
#   cloud_api), jadi yang baru di server hanyalah jembatan cloud di
#   cloud_api: GET /api/cloud/guild-online + 15 aksi POST (role/transfer/
#   ban/kick/chat/boss), notifikasi sosial cloud, heartbeat presence, dan
#   registrasi token push. Push memakai Supabase sebagai "kantor pos":
#   migrasi device_push_tokens (23 migrasi) + RPC register_push_token
#   (auth.uid()) + Edge Function send-push yang memanggil FCM HTTP v1.
#   Token FCM hanya lahir dari google-services.json milik pemilik proyek
#   (Firebase Console) — tanpa file itu registrasi berhenti diam-diam dan
#   aplikasi tetap jalan. 14 kunci i18n mobile baru (4.703 -> 4.717).
#   Python 512 -> 520 tes (+8 M10), Android vitest 252 -> 259 (+7).
# M11 (2026-10-23): Offline & reliabilitas. (1) Plafon 8 MB snapshot
#   personal DIHAPUS (G5 tertutup): dokumen besar dipecah menjadi part
#   tracker_v1/part/NNN (<= 3 MB) yang digabung penerima hanya bila satu
#   generasi lengkap; migrasi 20261023010000 melonggarkan validasi
#   document_key RPC (24 migrasi). Dokumen kecil tidak berubah perilaku.
#   (2) Backoff desktop & Android kini ber-jitter deterministik +0..20%
#   agar job gagal bersamaan tidak menyerbu server saat jaringan pulih.
#   (3) Cache Android berpagar: maks 2.000 baris/jenis & 10.000 total,
#   yang terlama dibuang setelah sync (cache adalah salinan, bukan arsip).
#   (4) Recovery UI di Settings Android: job mati bisa diantrekan ulang,
#   konflik cloud diputuskan dari ponsel, sesi kedaluwarsa diarahkan ke
#   login. Tes: Python 520 -> 529 (+9), Android vitest 259 -> 266 (+7,
#   termasuk simulasi airplane/force-kill/reinstall). 5 kunci i18n baru
#   (4.717 -> 4.722). APP_VERSION tetap 1.7.4.
# v2.0.0 (2026-10-23): RILIS BESAR — CraftLife kini tiga platform.
#   Desktop (PyQt6 + web) tetap utuh; Android (Expo SDK 57) mencapai
#   parity fitur penuh lewat M07-M12; cloud Supabase menambah sync
#   antar-perangkat, RPG server-authoritative (pet gacha, talents,
#   achievements, boss), sosial online (teman, chat, guild, PvP,
#   leaderboard), snapshot personal terpecah-part (plafon 8 MB
#   dihapus), dan mode Rules API yang di-pentest (M13). 26 migrasi
#   Supabase. Catatan lengkap: RELEASE_NOTES_v2.0.0.md.
# M13 (2026-10-23): QA. Pentest Rules API (12 tes) menemukan & menutup
#   2 celah nyata: body request tanpa batas (kini plafon 16 MB -> 413)
#   dan Content-Length rusak yang membunuh handler (kini 400); method
#   liar kini 405 JSON. Audit RLS statis (5 tes) bersih. Utang kontras
#   M06 DIBAYAR: 6 tema digelapkan 6-12% sampai semua >= 4,5:1, Chip
#   Android 40dp -> 48dp (15 tes aksesibilitas). Performa server lokal:
#   bootstrap median 9,6 ms. Laporan QA_M13.md; bukti perangkat
#   (TalkBack, cold start) menunggu verifikasi pengguna setelah M14.
# M12 (2026-10-23): Verifikasi parity. VERIFIKASI_M12.md membandingkan
#   Desktop/Android/Cloud baris demi baris terhadap matriks roadmap
#   dengan bukti uji (Python 531, Android vitest 266 -> 273, core 42).
#   Tiga rute Android yang masih kerangka (Learning, Music, Cloud)
#   kini berisi layar nyata; pemutaran musik jujur ditandai belum
#   tersedia (berkas di desktop, tak ada endpoint streaming). Enam
#   bukti perangkat/live tersisa di tangan pengguna (daftarnya di
#   dokumen itu); sel terkait ditandai menunggu, bukan dicek paksa.
#   15 kunci i18n baru (4.722 -> 4.737). APP_VERSION tetap 1.7.4.
# Fix (2026-10-23): migrasi 20261023020000 mengganti 3 fungsi M09b
#   (unlock_talent_cloud, fetch_cloud_talents, claim_boss_reward_cloud)
#   yang memakai operator // khas Python di SQL Postgres; diganti div()
#   dengan semantik identik. Ketahuan dari supabase db lint --linked di
#   mesin pengguna; migrasi lama tidak disunting. +2 tes (529 -> 531).
APP_VERSION = "2.0.0"
CHANNEL = "stable"
USER_AGENT = "CraftLifeDesktop-Updater/1.0"

# "supabase" = download dari Storage Supabase (masuk kuota cached egress).
# "github"   = download dari GitHub Releases (egress gratis, TIDAK masuk kuota).
UPDATE_SOURCE = "github"
GITHUB_REPO = "Hellowww-02/CraftLife"

# Jangan tanya/unduh versi yang sama berulang dalam rentang ini (detik).
RETRY_BACKOFF_SECONDS = 24 * 3600


def parse_version(value: str):
    parts = re.findall(r"\d+", str(value or ""))
    if not parts:
        return (0,)
    return tuple(int(p) for p in parts[:4])


def is_newer(remote: str, local: str) -> bool:
    return parse_version(remote) > parse_version(local)


def _clean_tag(tag: str) -> str:
    """C07 §10: bersihkan tag rilis ('v1.6.4' -> '1.6.4'; toleran 'v.1.6.3')."""
    return re.sub(r"^[vV\s.]+", "", str(tag or "")).strip()


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


# ══════════════════════════════════════════════════════════════════════════════
#  STATUS LOKAL — anti-loop & hemat egress
# ══════════════════════════════════════════════════════════════════════════════
_STATE_FILE = app_root() / "_update_state.json"


def _load_state() -> dict:
    try:
        data = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _mark_attempt(version: str) -> None:
    state = _load_state()
    state.setdefault("attempts", {})[str(version)] = datetime.now(timezone.utc).isoformat()
    _save_state(state)


def _api_base():
    """(url, publishable_key) dari .env; None bila belum dikonfigurasi."""
    try:
        from cloud_config import load_cloud_config
        cfg = load_cloud_config()
        if cfg.url and cfg.publishable_key:
            return cfg.url.rstrip("/"), cfg.publishable_key
    except Exception:
        pass
    return None


def _rpc(name: str, payload: dict, timeout: int = 10):
    base = _api_base()
    if not base:
        raise RuntimeError("updater_not_configured")
    url, key = base
    import requests
    resp = requests.post(
        f"{url}/rest/v1/rpc/{name}",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        json=payload,
        timeout=timeout,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"updater http {resp.status_code}")
    return resp.json()


def _fetch_from_github(timeout: int = 10) -> dict | None:
    import requests
    resp = requests.get(
        f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
        headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"},
        timeout=timeout,
    )
    if resp.status_code != 200:
        return None
    rel = resp.json()
    version = _clean_tag(rel.get("tag_name"))
    if not version:
        return None
    assets = rel.get("assets") or []
    zip_asset = next((a for a in assets if (a.get("name") or "").lower().endswith(".zip")), None)
    # C07 §10: GitHub menyertakan digest "sha256:..." per aset — pakai untuk verifikasi.
    sha256 = ""
    digest = str((zip_asset or {}).get("digest") or "")
    if digest.lower().startswith("sha256:"):
        sha256 = digest.split(":", 1)[1].strip().lower()
    return {
        "version": version,
        "notes": (rel.get("body") or "")[:4000],
        "storage_path": zip_asset.get("name") if zip_asset else "",
        "download_url": zip_asset.get("browser_download_url") if zip_asset else None,
        "sha256": sha256,
        "size_bytes": zip_asset.get("size") if zip_asset else 0,
    }


def _fetch_from_supabase(timeout: int = 10) -> dict | None:
    data = _rpc("latest_app_release", {"p_channel": CHANNEL}, timeout)
    if isinstance(data, list):
        data = data[0] if data else {}
    if not isinstance(data, dict) or not data.get("version"):
        return None
    base = _api_base()
    if base:
        data["download_url"] = (
            f"{base[0]}/storage/v1/object/public/app-updates/{data.get('storage_path') or ''}"
        )
    return data


def _check_inner(timeout: int = 10):
    """Inti pemeriksaan update — melempar Exception agar pemanggil bisa
    membedakan 'tidak ada update' dari 'gagal memeriksa' (C07 §10)."""
    info = _fetch_from_github(timeout) if UPDATE_SOURCE == "github" else _fetch_from_supabase(timeout)
    if not info or not info.get("version"):
        return None
    version = str(info.get("version"))
    if not is_newer(version, APP_VERSION):
        return None
    # Anti-loop: versi yang sama jangan ditawarkan berulang dalam backoff.
    attempts = _load_state().get("attempts", {})
    last = attempts.get(version)
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            age = (datetime.now(timezone.utc) - last_dt).total_seconds()
            if age < RETRY_BACKOFF_SECONDS:
                return None
        except Exception:
            pass
    return info


def check_for_update(timeout: int = 10):
    """Return release dict bila ada versi lebih baru (dengan backoff anti-loop);
    selain itu None (diam saat offline / sudah dicoba baru-baru ini)."""
    try:
        return _check_inner(timeout)
    except Exception:
        return None


def check_update_status(timeout: int = 10) -> dict:
    """Varian verbose untuk Web UI: {"update": info|None, "error": str|None}.

    Error jaringan/timeout dikembalikan sebagai pesan jelas agar UI tidak
    mengklaim 'sudah terbaru' saat sebenarnya gagal memeriksa (C07).
    """
    try:
        return {"update": _check_inner(timeout), "error": None}
    except Exception as e:
        msg = str(e) or "update_check_failed"
        low = msg.lower()
        if "timed out" in low or "timeout" in low:
            msg = "timeout: %s" % msg
        elif ("urlopen" in low or "nodename nor servname" in low
                or "getaddrinfo" in low or "connection" in low
                or "max retries" in low or "name resolution" in low):
            msg = "network_unreachable: %s" % msg
        elif low == "updater_not_configured":
            msg = "network_unavailable: %s" % msg
        return {"update": None, "error": msg}


def download_release(info: dict, progress_cb=None) -> Path:
    """Unduh zip update ke temp & verifikasi sha256 (bila disediakan)."""
    import requests
    url = info.get("download_url")
    if not url:
        raise RuntimeError("updater_no_url")
    _mark_attempt(info.get("version", ""))
    dest = Path(tempfile.gettempdir()) / f"craftlife_update_{info.get('version', 'v')}.zip"
    expected = (info.get("sha256") or "").strip().lower()
    h = hashlib.sha256()
    done = 0
    with requests.get(url, stream=True, timeout=300, headers={"User-Agent": USER_AGENT}) as resp:
        resp.raise_for_status()
        total = int(resp.headers.get("content-length") or info.get("size_bytes") or 0)
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if not chunk:
                    continue
                fh.write(chunk)
                h.update(chunk)
                done += len(chunk)
                if progress_cb and total:
                    try:
                        progress_cb(done, total)
                    except Exception:
                        pass
    if expected:
        actual = h.hexdigest()
        if actual != expected:
            dest.unlink(missing_ok=True)
            raise RuntimeError("updater_checksum")
    return dest


def _flatten_staging(staging: Path) -> None:
    """C07 §10: naikkan isi paket berlapis (maks 4 level).

    Mengenali tata letak rilis resmi (isi dist/CraftLife di root zip, yang bisa
    ikut terzip sebagai folder 'dist/CraftLife/') + unwrap legacy satu-folder.
    Berhenti segera bila CraftLife.exe sudah di root staging.
    """
    for _ in range(4):
        try:
            entries = [p for p in staging.iterdir()
                       if p.name != "__MACOSX" and not p.name.startswith(".")]
        except OSError:
            return
        if any(p.is_file() and p.name.lower() == "craftlife.exe" for p in entries):
            return
        nested = staging / "dist" / "CraftLife"
        if nested.is_dir():
            for item in nested.iterdir():
                shutil.move(str(item), str(staging / item.name))
            shutil.rmtree(staging / "dist", ignore_errors=True)
            continue
        dirs = [p for p in entries if p.is_dir()]
        files = [p for p in entries if p.is_file()]
        if len(dirs) == 1 and not files:
            inner = dirs[0]
            for item in inner.iterdir():
                shutil.move(str(item), str(staging / item.name))
            try:
                inner.rmdir()
            except OSError:
                pass
            continue
        return


def _staging_dir() -> Path:
    return app_root() / "_update_staging"


def _apply_log_path() -> Path:
    return app_root() / "_update_apply.log"


def _apply_log(msg: str) -> None:
    """C07 §10: catat jejak apply agar kegagalan update bisa didiagnosis."""
    try:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        with open(_apply_log_path(), "a", encoding="utf-8") as fh:
            fh.write(f"[{ts} UTC] {msg}\n")
    except OSError:
        pass


def apply_downloaded(zip_path: Path, version: str) -> None:
    """Ekstrak paket baru, siapkan staging, lalu (Windows) jalankan updater batch.

    C07 §10: ABORT dengan error jelas bila CraftLife.exe tidak ada setelah
    staging di-flatten (tata letak zip salah) — JANGAN timpa instalasi.
    Seluruh langkah dicatat di _update_apply.log (folder aplikasi).
    """
    staging = _staging_dir()
    _apply_log(f"apply start version={version} zip={zip_path}")
    try:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        staging.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(staging)
        try:
            names = sorted(p.name for p in staging.iterdir())
        except OSError:
            names = []
        _apply_log(f"extracted entries: {names}")
        _flatten_staging(staging)
        exe = staging / "CraftLife.exe"
        if not exe.exists():
            try:
                names = sorted(p.name for p in staging.iterdir())
            except OSError:
                names = []
            _apply_log(f"ABORT updater_no_exe: CraftLife.exe tidak ada di staging {names}")
            shutil.rmtree(staging, ignore_errors=True)
            raise RuntimeError(
                "updater_no_exe: paket update tidak berisi CraftLife.exe "
                "(tata letak zip salah — harusnya isi dist/CraftLife di root)")
        _apply_log("exe check OK: CraftLife.exe ada di staging")
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass

        if os.name == "nt":
            bat = _write_updater_bat(staging, version)
            _apply_log(f"updater batch ditulis: {bat}")
            _launch_detached(f'cmd /c "{bat}"')
            _apply_log("updater batch diluncurkan (detached)")
        else:
            root = app_root()
            protected = {".env", "craftlife.db", "craftlife.db-wal", "craftlife.db-shm",
                         "_update_state.json", "_update_apply.log"}
            for item in staging.iterdir():
                dst = root / item.name
                if dst.name in protected:
                    continue
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)
            shutil.rmtree(staging, ignore_errors=True)
            _apply_log("apply selesai (posix copy)")
    except Exception as e:
        _apply_log(f"apply FAILED: {e}")
        raise


def _write_updater_bat(staging: Path, version: str = "") -> Path:
    root = app_root()
    bat = Path(tempfile.gettempdir()) / f"craftlife_update_{int(time.time())}.bat"
    if is_frozen():
        relaunch = f'start "" "{Path(sys.executable)}"'
    else:
        script = Path(sys.argv[0]).resolve() if (sys.argv and sys.argv[0]) else (root / "MainPyQt6.py")
        relaunch = f'start "" "{sys.executable}" "{script}"'
    pid = os.getpid()
    content = (
        "@echo off\r\n"
        "setlocal EnableDelayedExpansion\r\n"
        f"set PID={pid}\r\n"
        f"set SRC={staging}\r\n"
        f"set DST={root}\r\n"
        "set LOG=%DST%\\_update_apply.log\r\n"
        f"echo [%date% %time%] CraftLife updater start {version} >> \"%LOG%\" 2>&1\r\n"
        "set MAXWAIT=30\r\n"
        "set /a N=0\r\n"
        ":waitloop\r\n"
        "tasklist /FI \"PID eq %PID%\" /NH 2>nul | findstr /C:\"%PID%\" >nul\r\n"
        "if not errorlevel 1 (\r\n"
        "  ping 127.0.0.1 -n 2 >nul\r\n"
        "  set /a N+=1\r\n"
        "  if !N! LSS %MAXWAIT% goto waitloop\r\n"
        ")\r\n"
        "robocopy \"%SRC%\" \"%DST%\" /E /XF .env craftlife.db craftlife.db-wal craftlife.db-shm "
        "_update_state.json /XD backups logs learning_audio _update_staging /NFL /NDL /NJH /NJS /NP >> \"%LOG%\" 2>&1\r\n"
        "if errorlevel 8 exit /b 1\r\n"
        "echo [%date% %time%] robocopy exit=%errorlevel% >> \"%LOG%\" 2>&1\r\n"
        "rd /s /q \"%SRC%\"\r\n"
        f"cd /d \"%DST%\"\r\n"
        f"{relaunch}\r\n"
        "endlocal\r\n"
        "exit /b 0\r\n"
    )
    bat.write_text(content, encoding="ascii", errors="ignore")
    return bat


def _launch_detached(command: str) -> None:
    flags = 0
    if os.name == "nt":
        flags = (getattr(subprocess, "DETACHED_PROCESS", 0)
                 | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
    subprocess.Popen(command, shell=True, creationflags=flags, close_fds=True)


# ══════════════════════════════════════════════════════════════════════════════
#  UNDUH LATAR — untuk polling progres Web UI (C07)
# ══════════════════════════════════════════════════════════════════════════════
_dl_lock = threading.Lock()
_dl_state = {"state": "idle", "done": 0, "total": 0,
             "version": "", "zip": "", "error": ""}


def download_status() -> dict:
    """Salinan status unduh saat ini (aman-thread)."""
    with _dl_lock:
        return dict(_dl_state)


def reset_download() -> dict:
    """Kembalikan status ke idle (dipanggil setelah apply/dismiss)."""
    with _dl_lock:
        _dl_state.update({"state": "idle", "done": 0, "total": 0,
                          "version": "", "zip": "", "error": ""})
        return dict(_dl_state)


def _dl_progress(done: int, total: int) -> None:
    with _dl_lock:
        _dl_state["done"] = done
        _dl_state["total"] = total


def start_download(info: dict) -> dict:
    """Mulai unduh rilis di background thread; idempoten saat downloading.

    Mengembalikan status langsung — Web UI mem-poll download_status().
    """
    with _dl_lock:
        if _dl_state.get("state") == "downloading":
            return dict(_dl_state)
        _dl_state.update({"state": "downloading", "done": 0, "total": 0,
                          "version": str((info or {}).get("version") or ""),
                          "zip": "", "error": ""})

    def _run():
        try:
            zip_path = download_release(info, progress_cb=_dl_progress)
        except Exception as e:
            with _dl_lock:
                _dl_state.update({"state": "error", "error": str(e) or "download_failed"})
            return
        with _dl_lock:
            _dl_state.update({"state": "ready", "zip": str(zip_path),
                              "done": _dl_state.get("total") or _dl_state.get("done")})

    threading.Thread(target=_run, name="craftlife-update-dl", daemon=True).start()
    return download_status()
