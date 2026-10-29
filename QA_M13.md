# Laporan QA M13 — 23 Oktober 2026

Metode sama seperti M12: klaim lama tidak dipercaya begitu saja; setiap area
diukur ulang. Yang tidak bisa dibuktikan dari sandbox dinyatakan terus
terang sebagai **MENUNGGU BUKTI PENGGUNA** (satu paket dengan daftar M12,
sesuai keputusan pengguna 2026-10-23: verifikasi perangkat sekaligus
setelah M14 di HP fisik).

## 1. Keamanan

### Pentest ringan Rules API (BARU: `tests/test_m13_pentest.py`, 12 test)
Kasus: tanpa token, payload JWT dirusak, secret salah, token kedaluwarsa,
`alg=none`, token sah milik sub tak-tertaut (tidak bocor data orang lain),
JSON rusak, string injeksi SQL (`' OR '1'='1`), method liar (DELETE),
path traversal (`..%2f`), body raksasa 20 MB, Content-Length rusak.

**Dua celah NYATA ditemukan dan diperbaiki di `api_server.py`:**
1. Body dibaca sebesar `Content-Length` **tanpa batas** → DoS memori untuk
   server yang menghadap internet. Sekarang: plafon 16 MB → `413`
   (unggahan sah terbesar ~6,8 MB).
2. `Content-Length` non-numerik membunuh handler (`ValueError` tak
   tertangani). Sekarang: `400 bad_content_length`.
3. Bonus: method selain GET/POST dulu dijawab halaman HTML `501` bawaan;
   sekarang `405 method_not_allowed` ber-JSON.

### Audit RLS ulang (BARU: `tests/test_m13_rls_audit.py`, 5 test)
Semua tabel `public.*` mengaktifkan RLS; setiap fungsi `security definer`
mengunci `search_path`; tidak ada grant tabel ke `anon`. `using (true)`
hanya lolos untuk SELECT pada katalog bersama (item toko, resep, katalog
pet/talent/boss, definisi achievement, daftar rilis) dan direktori sosial
baca-saja (`user_presence`, `online_guilds`, `online_guild_members`) —
semuanya tercatat dengan alasan di test. Audit ini statis; eksekusi live
tetap dibuktikan `supabase db lint` pengguna.

### Re-check S1–S6 (dari audit Phase 0)
| ID | Isu | Status M13 |
|---|---|---|
| S1 | `.env` ter-commit | ✅ Tertutup — gate `no-secrets` hijau |
| S2 | Token di URL `?token=` | ✅ Tidak ditemukan di web/Android (grep bersih); Android tidak pernah menerima pola ini |
| S3 | Nol test otomatis | ✅ Tertutup — Python 525 lulus (26 skip live/Postgres) · Android 288 · core 42 |
| S4 | Otoritas ganda progresi | ✅ Rules API penulis tunggal (suite M05) |
| S5 | Rules API menghadap internet | ✅ JWT tiap rute + scoping + rate limit + audit log (M05c) + pentest M13 |
| S6 | Plafon snapshot 8 MB | ✅ Tertutup di M11 (payload part) |

## 2. Aksesibilitas (BARU: `tests/a11y.test.ts`, 15 test)

- **Utang kontras M06 DIBAYAR.** 6 pasangan warna di bawah 4,5:1 diperbaiki
  di sumbernya (`database.THEMES`): primary/accent digelapkan 6–12%
  (modern_dark, nether, the_end, ancient_city, modern_light) dan
  `on_primary` sakura digelapkan. Semua 12 tema kini ≥ 4,5:1 untuk teks
  body maupun teks tombol; daftar utang di test M06 dikosongkan dan dijaga
  tetap kosong. `DESIGN.md` §11.1 ditandai lunas.
- **Target sentuh:** konstanta 48dp ditegakkan; **Chip ditemukan 40dp →
  diperbaiki ke 48dp** (test membaca sumber primitif, bukan klaim).
- **Animasi:** tidak ada animasi dekoratif kustom di Android (nol pemakaian
  `Animated`), jadi "Remove animations" sistem tidak dilawan oleh aplikasi.
- **MENUNGGU BUKTI PENGGUNA:** sesi TalkBack di HP fisik (setelah M14).

## 3. Performa (BARU: `tests/test_m13_performance.py`, 2 test)

Median lokal (DB uji, 5 sampel): `/api/bootstrap` **9,6 ms** ·
`/api/habits` 3,8 ms · `/api/cloud/status` 3,4 ms · `/api/leaderboard`
3,3 ms. Payload bootstrap dijaga < 2 MB. Jumlah langganan realtime
persisten di Android: **0** (sinkronisasi model tarik + outbox; tidak ada
saluran Supabase yang menggantung → tidak ada beban baterai dari listener).
Cold start / memori / baterai di HP: **MENUNGGU BUKTI PENGGUNA**.

## 4. Regresi

Gate §7 penuh: **17 lulus / 0 gagal / 1 skip**. Seluruh suite: Python 525 lulus · Android 288 lulus (17 file) · core 42 · TypeScript 0 error.
Playwright CLI untuk regresi UI web **tidak tersedia di sandbox** (tanpa
browser) — regresi web dibuktikan oleh gate types/build + test kontrak
API; sesi Playwright dicatat sebagai item lingkungan desktop pengguna,
sesuai K23 (tidak dipaksa ke native Android).

## 5. Audit desain (Impeccable, audit-only)

Sesuai batasan skill (audit saja, tanpa redesign): temuan yang diperbaiki
di M13 adalah Chip 40dp dan kontras 6 tema. Tidak ditemukan pola yang
dilarang pedoman Android proyek (teks raksasa, gradien berlebihan,
glassmorphism) pada primitif bersama; audit layar-per-layar mendalam
menunggu sesi perangkat (screenshot HP fisik).

## Temuan untuk M14
- `app.json` belum menunjuk ikon/splash khusus (masih bawaan Expo) — aset
  rilis dikerjakan di M14.
- Version anchors: `app.json` masih `1.7.4`/`versionCode 174` — bump ke
  2.0.0 memang tugas M14 (K22), bukan sekarang.
