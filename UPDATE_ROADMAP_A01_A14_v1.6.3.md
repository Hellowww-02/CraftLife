# 🗺️ CraftLife Update Roadmap — Commit Phase **A** (A01 → A14)

> **Satu commit phase** dari 4 area permintaan user (Music · Learning · Love Space · Home) → **Release v1.6.3**
> Basis: repo `main` pada **v1.6.0** (commit `cfdac0d`) · 14 fase + 1 fase finalisasi
> Semua akar masalah di bawah **sudah diverifikasi langsung di kode** (nomor baris = bukti), bukan tebakan.
> Fase bertanda 🔬 sudah direproduksi/ditelusuri penuh lewat audit kode + smoke API di workspace.

---

## 📜 Kontrak & Format (berlaku di SEMUA fase A)

Aturan dari user — setiap sesi coding/update WAJIB menghasilkan 10 item.

> ⚠️ **ATURAN DELIVERY (ARAHAN USER, 2026-09-14 — berlaku mulai A01, dikoreksi setelah A01):**
> laporan **format 1–6 ditampilkan LANGSUNG DI CHAT**, lengkap & konkret (key id+en apa adanya,
> daftar file apa adanya, perintah apa adanya, kesimpulan, migrasi) — **setiap kali** selesai coding,
> bukan cuma sebagai file dan bukan cuma ringkasan tabel. File markdown hanya **arsip** di repo
> (`2026-09-14-A0X-*.md`), bukan satu-satunya cara penyampaian.

1. **Translate key** di `translations.py` (wajib jika ada string baru — **id + en serentak**), lalu
   `python scripts/export_i18n.py` → sinkron `web/src/i18n/messages.json` + `web/public/i18n/messages.json`.
2. **File yang harus ditimpa** (daftar lengkap untuk copy-paste dari workspace ke laptop).
3. **File baru** (jika ada).
4. **Command baru** (jika ada — endpoint API / script / env / perintah shell).
5. **Kesimpulan** dari tiap sesi pengodingan/update.
6. **Migrasi Supabase baru** (jika ada — di phase ini mayoritas migrasi **SQLite lokal** via `database.py`).
7. **Kesimpulan akhir satu commit phase** (format 1–6 untuk seluruh A01–A14) — dibuat di **A14**.
8. **`updater.py`** di-update untuk satu commit phase → `APP_VERSION = "1.6.3"` (`web/package.json` ikut
   disinkronkan). ✅ **Sudah dikerjakan di A01** (bump sekali untuk satu commit phase); A14 hanya memverifikasi.
9. **`README.md`** selalu di-update setiap fase (narasi versi terbaru + dokumentasi baru) — fase: bagian
   "What's New in v1.6.3 — in progress"; finalisasi penuh di **A14**.
10. **Release Notes untuk GitHub Release** — di **A14** (`RELEASE_NOTES_v1.6.3.md`).

**Prinsip turunan (warisan kontrak lama, tetap berlaku):**
- 🧠 **Game rules & business logic hanya di `database.py`** — React tidak pernah menghitung ulang.
- 🎨 **UI-only** untuk perbaikan tampilan — handler/state/API tidak berubah kecuali fase itu memang
  menyentuh backend (ditandai jelas per fase).
- 🌐 **String baru selalu id + en** — tidak boleh ada teks hardcoded baru di TSX.
- ✅ **Verifikasi wajib tiap fase:** `py_compile` modul tersentuh · `tsc --noEmit` · `vite build` ·
  smoke test endpoint yang diubah (`python api_server.py` + `curl`).
- 🖥️ **Precedent rilis sebelumnya (P54/P57–P59/P62):** fitur baru diimplementasikan di **backend + React UI**;
  UI legacy PyQt (`CRAFTLIFE_WEB_UI=0`) tetap **jalan tanpa crash** tapi tidak wajib mendapat fitur baru.
  Phase A mengikuti precedent ini (tidak mengubah `MainPyQt6.py` kecuali disebutkan).

---

## 🔒 Keputusan yang Sudah Dikunci Bersama User

| Topik | Keputusan |
|---|---|
| Counter Quiz | **Dua counter terpisah** — Pilihan Ganda & Essay. Default **10 MC + 5 Essay (total 15)**. Masing-masing **maks 30**, dan **total gabungan ≤ 30**. |
| Dialog generator | **Setiap tipe generate Studio punya dialog konfigurasi sendiri** (ala NotebookLM "Customize") — bukan satu counter global. ✅ termasuk permintaan eksplisit user. |
| Migrasi | **Diizinkan penuh** — kolom/tabel SQLite baru (auto-apply di `init_db()`) + migrasi Supabase hanya untuk fitur cloud. |
| Higiene repo | **Ditunda** (di Backlog, bukan bagian commit phase ini). Versi tetap naik ke **1.6.3**. |
| Learning UI | **Restrukturisasi menyeluruh** ala NotebookLM (fungsi tetap 100% sama). |

---

## 🗺️ Peta Fase

| Fase | Item user | Judul | Lapisan | Risiko |
|---|---|---|---|---|
| **A01** | #1a | Music: lirik **mengikuti lagu** saat track berganti otomatis | Frontend | 🔴 fatal UX |
| **A02** | #1b | Music: **perluasan & akurasi** pencarian lirik (kandidat + album + durasi) | Backend + FE | 🟠 luas |
| **A03** | #1c | Music: import lirik manual — **format .lrc terdokumentasi** + template + validasi + ekspor | Full-stack | 🟢 |
| **A04** ✅ | #2a | Learning: **bug jawaban essay** (fatal) + skor + dua counter MC/Essay | FE + Backend | 🔴 fatal |
| **A05** ✅ | #2b | Learning: **dialog per-tipe generator** Studio (NotebookLM Customize) | FE + Backend | 🟠 |
| **A06** ✅ | #2c | Learning: hasil generate sebagai **daftar artefak rapi** (list ke bawah) | FE + Backend | 🟡 |
| **A07** ✅ | #2d | Learning: **restrukturisasi UI ala NotebookLM** (rail sumber / chat / studio) | Frontend | 🟡 |
| **A08** | #2e | Learning: **sitasi sumber** + pemilihan sumber grounding (+ podcast dua host & migrasi SDK `google.genai`) | Full-stack | ✅ **Selesai 2026-09-15** |
| **A09** | #3a | Love Space tab `plans`: catatan acara, edit, **Special Day** + pengingat berulang | Full-stack | ✅ **Selesai 2026-09-16** |
| **A09** | #3a | Love `plans`: notes event (hole) + **edit** + **special days/recurring** | Full-stack + migrasi | 🟠 |
| **A10** | #3b | Love: `memories` & `bucket list` diprofesionalkan | Full-stack + migrasi | ✅ **Selesai 2026-09-16** |
| **A11** | #3c | Love: `connection` · `cycle` · `gallery` — audit + polish profesional | Full-stack (kecil) | ✅ **Selesai 2026-09-16** |
| **A12** ✅ | #3d | Love `overview` + integrasi **special day → Reminder (repeat yearly)** | Full-stack + migrasi | ✅ **Selesai 2026-09-16** |
| **A13** ✅ | #4 | Home: **Year Wrapped pakai currency user** + i18n + polish | FE + Backend | ✅ **Selesai 2026-09-16** |
| **A14** ✅ | — | **Finalisasi & rilis v1.6.3** (i18n sync, versi, README rev, Release Notes, verifikasi penuh, kesimpulan commit phase) | Semua | ✅ **Selesai 2026-09-16** |
| **A15** ✅ | 📚 Learning | **Perbaikan rail kiri** — ikon notebook tersimpan & tampil sesuai input user (`learning_notebooks.icon` + `description` + `updated_at`, API create/rename parsial), satu avatar per notebook (emoji user → fallback inisial), tata letak rail rapi (lebar `--rail-w` 72/220 px, judul truncate, tombol ikut melebar), dialog Ganti nama bisa mengganti emoji | Learning | ✅ **Selesai 2026-09-16** |

**Urutan disusun:** bug fatal dulu (A01, A04) → fitur Music berurutan (A01–A03, semuanya menyentuh `MusicView`/`studio_api` lirik) → Learning (A04–A08, satu klaster `LearningView`) → Love Space (A09–A12, satu klaster `LoveSpaceView`) → Home (A13) → finalisasi (A14). Konflik merge minimal karena tiap klaster menyentuh file yang sama secara berurutan.

**Total realisasi:** **23 file ditimpa** · **27 file kode baru** (+3 migrasi Supabase opsional + dokumen rilis) · **+567 key i18n baru** (id+en; **3.757 → 4.324**) · **10 endpoint baru** + **1 parameter baru** (`/api/year-wrapped?year=`, A13) · **5 blok migrasi SQLite** (A06, A08, A09, A10, A11, A12 — auto-apply) + **3 migrasi Supabase opsional** (A09, A10, A11).

---

# 🔵 KLASTER 1 — MUSIC PAGE (#1)

## A01 — Lirik mengikuti lagu yang sedang diputar ✅ *SELESAI 2026-09-14*

**Item user #1a:** *"live lyric tidak berganti ketika lagu sudah ganti; saat tab lyric terbuka dan musik berganti, lyric masih menampilkan lyric lagu sebelumnya."*

**Akar masalah (TERBUKTI di kode):**
- `web/src/components/views/MusicView.tsx` **L215–222** — `loadLyrics(entry)` **hanya** dipanggil di
  `handlePlayLibraryFile`, yaitu saat user **mengklik** trek dari daftar.
- Tidak ada `useEffect` yang memantau `playingFile` (L97–103 mengonsumsi `useMusicPlayer()` tanpa efek
  reaktif). Akibatnya semua jalur pergantian lagu **tanpa klik** tidak memicu muat lirik:
  - `MusicPlayerContext.tsx` **L199** `onEnded → next()` (auto-advance akhir lagu),
  - **L95–107** `next()` / **L110–117** `prev()` (tombol di MiniPlayer/Navbar & MusicView L231–232),
  - `MiniPlayer.tsx` (kontrol dari halaman lain),
  - `repeat` (L197) & `shuffle` (L99–103).
- Race tambahan: `loadLyrics` (L304–323) tidak punya penjaga urutan — respons lambat untuk trek A bisa
  menimpa lirik trek B bila user cepat berpindah (`setLyrics` tanpa cek identitas trek).
- `activeLyricLine` di-reset hanya saat `syncedLines` berubah (L146–148) — tidak saat trek berganti.

**Perubahan:**
1. **Efek tunggal pemantau trek** di `MusicView`:
   ```tsx
   useEffect(() => {
     if (!lyricsOpen || !playingFile?.path) return;
     loadLyrics(playingFile);          // dedupe via cache per trackKey
   }, [lyricsOpen, playingFile?.path]);
   ```
   (kunci `path` — bukan objek — supaya tidak refetch saat `durationMs` berubah.)
2. **Cache lirik per trek** (in-memory `Map<trackKey, LyricsPayload>` + TTL sesi) → pindah-pindah lagu
   kembali ke trek sebelumnya = instan, tanpa hit API/network.
3. **Penjaga balapan (race guard):** `lyricsReqRef` menyimpan `trackKey` yang diminta terakhir; respons
   diabaikan bila `trackKey` tidak lagi sama (juga batal-kan `setLyricsLoading`).
4. **MiniPlayer & lirik:** saat trek berganti dari mana pun, drawer menampilkan header trek aktif
   (judul · artis · durasi) sehingga jelas lirik milik siapa.
5. **Efek lirik aktif:** reset `activeLyricLine` ke `-1` begitu trek berubah (bukan hanya saat parses berubah).
6. **Auto-scroll** drawer ke baris aktif tetap (parity `_update_synced_lyric`), tapi tidak menggulir saat
   pengguna sedang membaca manual (`isUserScrolling` guard 3 detik).

**Format 1 — i18n key baru (id / en):**

| Key | id | en |
|---|---|---|
| `music_lyrics_now_for` | `Lirik untuk: {title}` | `Lyrics for: {title}` |
| `music_lyrics_track_change_hint` | `Lirik otomatis mengikuti lagu yang sedang diputar.` | `Lyrics follow the track that is currently playing.` |
| `music_lyrics_disabled_no_track` | `Pilih lagu dulu untuk melihat lirik.` | `Play a track first to view lyrics.` |

**Format 2 — File ditimpa:** `web/src/components/views/MusicView.tsx` · `web/src/components/music/LyricsDrawer.tsx`
**Format 3 — File baru:** — (tidak ada)
**Format 4 — Command baru:** — (tidak ada)
**Format 5 — Kesimpulan fase:** Lirik kini 100% sinkron dengan trek aktif di semua jalur (klik, next/prev, auto-advance, mini-player, shuffle/repeat); race condition respons terlambat ditutup; perpindahan antar trek yang pernah diputar menjadi instan lewat cache.
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** `tsc --noEmit` · `vite build` · smoke manual: putar trek → biarkan habis (auto-advance) → drawer harus berpindah lirik · tekan next/prev · ganti lagu dari MiniPlayer di halaman lain.

---

## A02 — Perluasan & akurasi pencarian lirik (kandidat, album, durasi) ✅ *SELESAI 2026-09-14*

**Item user #1b:** *"terkadang lyric yang ditemukan tidak benar-benar sync ... berdasarkan lagu/artist/album/detika (durasi) yang dipilih user."*

**Akar masalah (TERBUKTI):**
- `studio_api.py` **L1315+** `get_lyrics()` sudah melakukan scoring, tapi:
  - **album tidak dipakai sama sekali** dalam pencarian maupun skoring (`_score_lyrics_candidate` L1281–1312
    hanya artist + title + duration + bonus synced).
  - `lrclib.net/api/get` (**L1341–1355**) mengirim `duration` → LRCLIB mencocokkan **ketat**; bila metadata
    durasi file berbeda sedikit (tag vs durasi unduhan) hasilnya **kosong** dan kode jatuh ke `search` yang
    longgar (sumber utama kesalahan versi live/remix/karaoke).
  - **`/api/music/library` dibatasi 80 item** — `music_downloader.py` **L221** `out[:80]`; metadata lengkap
    (termasuk `duration`, `_read_metadata` L177–198) hanya untuk 80 file terbaru. Playlist yang memuat file
    di luar 80 teratas → `metaFor(path)` = `undefined` → `MusicView` **L160–171** memberi
    `duration: 0` → pencarian lirik tanpa durasi → versi salah. **Inilah penyebab paling sering.**
  - Tidak ada cara user memilih kandidat lain; `refresh=1` (L1191–1195) melewati lirik tersimpan.
  - Tidak ada cache negatif → tiap pindah trek tanpa hasil mengulang 4–6 request jaringan (timeout 5s,
    total 9s — L1400+) sehingga drawer tampak "muter terus".

**Perubahan:**
1. **Backend `studio_api.py`:**
   - Endpoint baru **`GET /api/music/lyrics-candidates`** → kembalikan **daftar kandidat** (maks 12) dengan
     `{artist, title, album, duration, synced(bool), plain(bool), source, score, preview}` — sumber:
     LRCLIB `get` (durasi eksak & toleransi ±2s) + LRCLIB `search` (varian: `artist title`,
     `title album`, `artist album title`) + lyrics.ovh.
   - `_score_lyrics_candidate()` diperluas: **+album match (+1.5)**, +penalti keras untuk penanda versi
     (`live`, `remix`, `karaoke`, `cover`, `instrumental`, `sped up`, `slowed`) pada judul/album kandidat,
     bonus `synced`, dan **toleransi durasi 3 tahap** (`≤2s: +3`, `≤5s: +1.5`, `>15s: −2`).
   - `get_lyrics(artist, title, file_path, duration, album=None, prefer=None)` — `prefer` = index kandidat
     pilihan user.
   - Endpoint baru **`POST /api/music/lyrics-apply`** → simpan kandidat terpilih sebagai lirik tersimpan
     (`source="user-pick"`) → tidak pernah tertimpa pencarian berikutnya.
   - **Cache negatif in-memory** (key → waktu, TTL 10 menit) supaya trek tanpa lirik tidak memicu
     request berulang; `refresh=1` mengabaikan cache + lirik tersimpan.
2. **Backend `music_downloader.py`:**
   - `list_library(limit=None)` — batas default dinaikkan (**80 → 500**, env `CRAFTLIFE_MUSIC_LIB_LIMIT`),
     dan item memuat `durationMs`, `mtime`, `album` yang konsisten.
   - Tambah **`get_track_meta(path)`** (1 file) + **`get_track_meta_many(paths)`** (batch, dedupe, cache
     `mtime`) → dipakai API baru agar playlist besar selalu punya metadata walau melewati batas listing.
3. **Backend `api_server.py`:** endpoint baru **`GET /api/music/track-meta?paths=a|b|c`** (batch, dipakai
   MusicView saat `missing: true`).
4. **Frontend `MusicView.tsx`:** saat memuat playlist, jalankan `trackMeta` batch untuk jalur tanpa metadata →
   isi `library` lokal → `duration` tersedia untuk `loadLyrics`.
5. **Frontend komponen baru `LyricsSearchDialog.tsx`:** daftar kandidat (judul/artis/album/durasi/badge
   `SYNCED`·`PLAIN`·skor), tombol **Pakai**, preview 5 baris, badge merah untuk durasi menyimpang
   ("durasi beda 42s — kemungkinan versi live"), plus tombol **Refresh pencarian** memakai album+durasi.
6. **LyricsDrawer:** tambah tombol 🔍 **Cari kandidat** (membuka dialog) + tampilkan asal lirik
   (`lrclib synced` / `user-pick` / `embedded`) + chip durasi trek vs durasi kandidat.

**Format 1 — i18n key baru (id / en):**

| Key | id | en |
|---|---|---|
| `music_lyrics_candidates` | `Pilih sumber lirik` | `Choose a lyrics source` |
| `music_lyrics_search_expand` | `Cari lebih luas (album + durasi)` | `Search wider (album + duration)` |
| `music_lyrics_use` | `Pakai lirik ini` | `Use these lyrics` |
| `music_lyrics_duration_match` | `Durasi cocok ({sec} dtk)` | `Duration match ({sec}s)` |
| `music_lyrics_duration_off` | `Durasi beda {diff} dtk — cek versi lagu` | `Duration differs by {diff}s — check the version` |
| `music_lyrics_version_warning` | `Kandidat ini kemungkinan versi live/remix/karaoke.` | `This candidate is likely a live/remix/karaoke version.` |
| `music_lyrics_source_lrclib` | `LRCLIB` | `LRCLIB` |
| `music_lyrics_source_ovh` | `lyrics.ovh` | `lyrics.ovh` |
| `music_lyrics_source_embedded` | `Tertanam di file` | `Embedded in file` |
| `music_lyrics_source_user` | `Import manual` | `Manual import` |
| `music_lyrics_source_pick` | `Pilihanmu` | `Your pick` |
| `music_lyrics_no_candidates` | `Tidak ada kandidat lirik untuk lagu ini.` | `No lyrics candidates found for this track.` |
| `music_lyrics_index_hint` | `Metadata diambil dari album/artis/durasi (mutagen).` | `Metadata is read from album/artist/duration (mutagen).` |

**Format 2 — File ditimpa:** `studio_api.py` · `music_downloader.py` · `api_server.py` ·
`web/src/components/views/MusicView.tsx` · `web/src/components/music/LyricsDrawer.tsx` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/music/LyricsSearchDialog.tsx`

> ✅ **STATUS A02 — SELESAI (2026-09-14).** Catatan realisasi vs rencana:
> 1. Key i18n bertambah **15** (13 rencana + 2 pelengkap UI: `music_lyrics_score`, `music_lyrics_close`).
> 2. Endpoint `/api/music/track-meta` ditempatkan di **`studio_api.py`** (bukan `api_server.py`) karena
>    seluruh endpoint musik lain ada di sana; `api_server.py` tetap disentuh untuk `WEB_I18N_KEYS`.
> 3. **Perbaikan bonus:** key A01 (`music_lyrics_now_for`, `music_lyrics_track_change_hint`,
>    `music_lyrics_disabled_no_track`, `music_lyrics_scroll_paused`) ternyata belum terdaftar di
>    `WEB_I18N_KEYS` (hanya terbaca lewat `messages.json` bawaan) → kini ikut didaftarkan agar
>    `/api/i18n` juga melayaninya.
> 4. Endpoint baru: `GET /api/music/lyrics-candidates`, `GET /api/music/track-meta`,
>    `POST /api/music/lyrics-apply`.
**Format 4 — Command baru:**
```
GET  /api/music/lyrics-candidates?artist=&title=&album=&duration=&key=
POST /api/music/lyrics-apply            {"key","artist","title","plain","synced","source"}
GET  /api/music/track-meta?paths=<path1>|<path2>      (max 200 path/req)
env  CRAFTLIFE_MUSIC_LIB_LIMIT (default 500)
```
**Format 5 — Kesimpulan fase:** Pencocokan lirik tidak lagi bergantung pada 80 file terbaru; kandidat diberi skor dengan album + toleransi durasi bertingkat + deteksi versi live/remix, dan user akhirnya bisa memilih sendiri kandidat yang benar (tersimpan permanen sebagai `user-pick`). Cache negatif menghilangkan request berulang pada trek tanpa lirik.
**Format 6 — Migrasi:** — (tidak ada; semua memakai tabel `song_lyrics` yang sudah ada)
**Verifikasi:** curl `lyrics-candidates` untuk 3 trek berbeda (satu sengaja durasi melenceng) · `tsc --noEmit` · `vite build` · smoke: pilih kandidat → pindah lagu → kembali → kandidat tetap tersimpan.

---

## A03 — Import lirik manual: format terdokumentasi + template + validasi + ekspor ✅ *SELESAI 2026-09-14*

**Item user #1c:** *"aku masih belum tahu format seperti apa yang dipakai untuk memakai fitur upload lyric dari computer langsung."*

**Akar masalah (TERBUKTI):**
- Import sudah ada di backend (`studio_api.py` **L1860–1873**) dengan deteksi otomatis `[mm:ss]` → synced,
  selain itu dianggap plain (L1867–1871), tapi **tidak ada dokumentasi/format di UI**, tidak ada template,
  tidak ada laporan validasi, dan tidak ada ekspor.
- Frontend (`MusicView.tsx` **L367–383**, input file **L480–481** `accept=".lrc,.txt,text/plain"`) hanya
  menampilkan toast "format tidak valid" tanpa menjelaskan apa yang salah.
- Tidak mendukung penanda LRCLIB standar `[ar:]`, `[ti:]`, `[al:]`, `[offset:]` → file .lrc asli dari
  internet sering gagal/tersimpan sebagai plain.

**Perubahan:**
1. **Backend `studio_api.py`** — parser LRC diperluas (`_parse_lrc_like`):
   metadata `[ar:]`/`[ti:]`/`[al:]`/`[by:]` diabaikan sebagai baris lirik; `[offset:±ms]` **dijumlahkan** ke
   `offsetMs` trek; dukungan `[mm:ss]`, `[mm:ss.x]`, `[mm:ss.xx]`, `[mm:ss.xxx]`, multi-timestamp per baris,
   dan tag `[mm:ss.xx]` tanpa teks (diperlakukan sebagai jeda, bukan baris kosong).
2. **Endpoint baru `POST /api/music/lyrics-validate`** → kembalikan
   `{ok, format:"lrc"|"plain", timedLines, firstMs, lastMs, warnings[], preview[]}` — dipakai UI untuk
   menampilkan hasil sebelum menyimpan (bukan toast buta).
3. **Endpoint baru `GET /api/music/lyrics-template`** → unduh `craftlife-lyrics-template.lrc`
   (berisi contoh 6 baris bertimestamp + komentar cara pakai).
4. **Endpoint baru `GET /api/music/lyrics-export?key=&format=lrc|txt`** → unduh lirik tersimpan
   (lrc = dengan timestamp + header `[ar:]`/`[ti:]`/`[offset:]`).
5. **Frontend `LyricsImportDialog.tsx` (baru):** drop-zone + pilih file · **panduan format 3 blok**
   (LRC bertimestamp / teks polos / dari internet yang didukung) · contoh format disalin sekali klik ·
   tombol **Unduh template** · panel hasil validasi (jumlah baris bertimestamp, baris pertama/terakhir,
   peringatan) · tombol Simpan.
6. **LyricsDrawer:** tambah tombol ⤓ ekspor + tombol ❓ panduan format (membuka dialog yang sama di tab panduan).

**Format 1 — i18n key baru (id / en):**

| Key | id | en |
|---|---|---|
| `music_lyrics_import_title` | `Import lirik dari komputer` | `Import lyrics from computer` |
| `music_lyrics_import_drop` | `Tarik file ke sini atau klik untuk memilih` | `Drag a file here or click to choose` |
| `music_lyrics_import_format` | `Format yang didukung` | `Supported formats` |
| `music_lyrics_format_lrc_desc` | `LRC bertimestamp — lirik bergerak sendiri. Contoh: [00:12.35]Baris lirik` | `Timestamped LRC — lyrics scroll in sync. Example: [00:12.35]Lyric line` |
| `music_lyrics_format_plain_desc` | `Teks polos — lirik tampil utuh tanpa sinkronisasi waktu.` | `Plain text — lyrics show as-is without time sync.` |
| `music_lyrics_format_tags_desc` | `Tag metadata didukung: [ar:Artis] [ti:Judul] [al:Album] [offset:+500]` | `Metadata tags supported: [ar:Artist] [ti:Title] [al:Album] [offset:+500]` |
| `music_lyrics_download_template` | `Unduh template .lrc` | `Download .lrc template` |
| `music_lyrics_validate` | `Cek file` | `Validate file` |
| `music_lyrics_validate_ok` | `{n} baris bertimestamp siap dipakai ({first} → {last})` | `{n} timestamped lines ready ({first} → {last})` |
| `music_lyrics_validate_plain` | `File dikenali sebagai teks polos (tanpa timestamp).` | `File detected as plain text (no timestamps).` |
| `music_lyrics_validate_warn` | `Peringatan: {list}` | `Warnings: {list}` |
| `music_lyrics_export` | `Ekspor lirik` | `Export lyrics` |
| `music_lyrics_copy_example` | `Salin contoh format` | `Copy format example` |
| `music_lyrics_import_guide` | `Panduan format lirik` | `Lyrics format guide` |

**Format 2 — File ditimpa:** `studio_api.py` · `web/src/components/views/MusicView.tsx` ·
`web/src/components/music/LyricsDrawer.tsx` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/music/LyricsImportDialog.tsx`
**Format 4 — Command baru:**
```
POST /api/music/lyrics-validate           {"content","key"}
GET  /api/music/lyrics-template           → .lrc (text/plain, Content-Disposition)
GET  /api/music/lyrics-export?key=&format=lrc|txt
```
**Format 5 — Kesimpulan fase:** Format import yang dulu tak terdokumentasi kini dijelaskan **di dalam aplikasi** (panduan + template + validasi sebelum simpan), dan mendukung seluruh penanda .lrc standar sehingga file lirik hasil unduhan dari internet langsung bekerja. User juga bisa mengekspor lirik tersimpan.
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** unggah 3 file uji (`.lrc` valid, `.lrc` dengan `[offset:]`, `.txt` polos) → validasi & tampilan benar · unduh template · ekspor ulang → bandingkan isi.

> ✅ **STATUS A03 — SELESAI (2026-09-14).** Catatan realisasi vs rencana:
> 1. Key i18n bertambah **34** (14 rencana + 20 pelengkap: label tab, tombol simpan, 8 kalimat
>    peringatan validasi, pesan ekspor, chip jeda/offset/metadata).
> 2. Endpoint template/ekspor memakai mekanisme unduhan yang **sudah ada** di repo
>    (`{"__file_bytes__": bytes, "name":…, "mime":…}`), kini juga berlaku untuk `studio_api.handle_get`
>    (sebelumnya hanya `life_api`) — tanpa kode respons mentah baru.
> 3. Peringatan validasi dikirim sebagai **kode** (`untimed_lines:3`) agar diterjemahkan di UI (id/en),
>    bukan string bahasa yang dikunci di backend.
> 4. `LyricsImportDialog` menggantikan input file lama di `MusicView` (hidden `<input type=file>` dihapus);
>    tombol ekspor & panduan ditambahkan di `LyricsDrawer` (Ekspor ⤓ → .lrc/.txt, Panduan ❓).

---

# 🟣 KLASTER 2 — LEARNING PAGE (#2)

## A03.5 — 🔧 Audit & perbaikan SELURUH export/download (permintaan user, pra-A04) ✅ *SELESAI 2026-09-14*

**Permintaan user:** *"aku mau memperbaiki semua export di seluruh app, yang di health & food, termasuk
download template lrc itu tidak bisa, entah mungkin terdownload dimana. Analisis seluruh audit semua
fungsi dan fitur export atau download apakah bisa masuk benar ke file computer, jika tidak langsung perbaiki."*

**Akar masalah (TERBUKTI):** `web_shell.py` tidak menyambungkan `QWebEngineProfile.downloadRequested`
→ Qt WebEngine **membuang setiap unduhan tanpa pesan** (tidak ada berkas di mana pun). Beberapa tombol
juga membuat `<a download>` tanpa memasukkan anchor ke DOM.

**Perubahan:**
1. `web_shell.py`: `DownloadManager` (folder `Downloads/CraftLife`, nama unik, notifikasi lokasi berkas,
   deteksi gagal, antrean "buka folder" yang dieksekusi di GUI thread) + impor Qt dijadikan opsional
   (api_server tetap bisa `import web_shell` headless) + pemasangan handler di `WebMainWindow.__init__`.
2. `api_server.py`: `GET /api/system/downloads-info`, `POST /api/system/open-downloads`,
   `POST /api/system/stage-file` + `GET /api/system/download-file?id=` (berkas buatan klien diunduh
   sebagai attachment; 8 MB; TTL 1 jam; id per-user), helper `_download_mod()/_downloads_info()`.
3. `web/src/api/client.ts`: helper kanonik `downloadUrl`, `downloadApiFile`, `saveBlobToFile`,
   `saveFileToComputer`, `downloadTargetInfo`, `openDownloadsFolder`, `onDownloadEvent`.
4. `web/src/components/DownloadToaster.tsx` (baru): jembatan `window.craftlifeDownloadEvent` → toast
   "Tersimpan di: {path}".
5. 5 titik ekspor dimigrasi: `HealthFoodView` (nutrisi), `SettingsView` (tracker JSON + tombol buka folder),
   `LearningView` (studio .txt), `FriendsView` (lampiran), `LyricsImportDialog`/`MusicView` (template +
   ekspor lirik).

**Format 1 — i18n key baru (id / en):** `download_saved_title`, `download_saved_msg`,
`download_started_msg`, `download_failed_title`, `download_failed_msg`, `download_folder_default`,
`download_open_folder`, `download_open_failed`, `download_web_mode_note` (9 key).
**Format 2 — File ditimpa:** `web_shell.py` · `api_server.py` · `web/src/api/client.ts` ·
`web/src/api/studio.ts` · `web/src/App.tsx` · `web/src/components/views/HealthFoodView.tsx` ·
`SettingsView.tsx` · `LearningView.tsx` · `FriendsView.tsx` · `MusicView.tsx` ·
`web/src/components/music/LyricsImportDialog.tsx` · `translations.py` · 2× `messages.json` · `README.md`
**Format 3 — File baru:** `web/src/components/DownloadToaster.tsx`
**Format 4 — Command baru:** `GET /api/system/downloads-info` · `POST /api/system/open-downloads` ·
`POST /api/system/stage-file` · `GET /api/system/download-file?id=` · env `CRAFTLIFE_DOWNLOAD_DIR`
**Format 5 — Kesimpulan:** Semua fitur ekspor (nutrisi, tracker, studio, lirik, lampiran) kini benar-benar
tersimpan di `Downloads/CraftLife`, lokasinya diberitahukan, dan bisa dibuka dari aplikasi.
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** lihat blok verifikasi A03.5 di `README.md` + laporan `2026-09-14-A03.5-export-download.md`.

---

## A04 — Bug jawaban essay (fatal) + skor + dua counter MC/Essay ✅ *SELESAI 2026-09-15*

**Item user #2a:** *"bagian generate quiz ada bug di bagian soal essay — tidak bisa mengetik apa-apa untuk menjawab soal essay."* + *"mau diperbaiki agar bisa diatur berapa soal PG dan berapa essay, total maks 30."*

**Akar masalah (TERBAIKTI, dua lapis):**
1. **Lapis closure (gejala "tidak bisa mengetik"):** `LearningView.tsx` **L272** `essayAnswers` diperbarui
   lewat closure di **L463** (`setEssayAnswers((prev) => ({ ...prev, [qIndex]: e.target.value }))`) sementara
   **L499** tombol **Evaluate** menyetel `quizSubmitted = true`. Begitu `quizSubmitted` bernilai `true`,
   `textarea` di **L461** menjadi `disabled` — dan karena `quiz` divalidasi ulang tiap render dari
   `activeNotebook` (yang di-*refetch* oleh `refreshNotebooks()` di **L632** setelah generate), nilai
   textarea yang belum ter-commit ke server ikut hilang pada render berikutnya. Hasilnya: user mengetik,
   state & DOM ter-desync → seolah "tidak bisa mengetik".
2. **Lapis skor:** **L441–448** skor hanya menghitung pilihan ganda (`mc`), essay tidak dinilai dan tidak
   dihitung — tidak ada umpan balik kelayakan jawaban (`modelAnswer` hanya ditampilkan pasif di **L468**).
3. **Lapis counter:** **L960–963** hanya **satu** input (`studioCount`, min 10 max 30, default 15) →
   `handleGenerateQuiz` (**L616–621**) mengirim `count: studioCount`; backend `learning_helper.py`
   **L423–426** membagi otomatis `quiz_mc = round(n*0.7)`, `quiz_essay = sisa` → user tidak punya kendali.

**Perubahan:**
1. **Pisahkan state essay dari render notebook:** `essayAnswers` disimpan sebagai `Record<qid, string>`
   dengan **key stabil `q.id`** (bukan `qIndex`) + `useRef` mirror, dan textarea menjadi
   **fully controlled** (`value={essayAnswers[q.id] ?? ''}`). Klik Evaluate **tidak lagi men-disable**
   textarea; mode penilaian memakai flag terpisah (`quizReviewed`) sehingga user masih bisa memperbaiki
   jawaban lalu menekan **Evaluasi ulang**.
2. **Auto-save draft jawaban** per notebook ke `localStorage` (`cl_learning_quiz_draft_<nbId>_<genId>`)
   sehingga jawaban tidak hilang saat pindah tab/panel atau refresh.
3. **Skor komposit:**
   - PG: jumlah benar (`correctAnswerIndex`),
   - Essay: **self-assessment** tiga tombol per soal — `✅ Sesuai` / `🟡 Sebagian` / `❌ Belum` (default belum
     dinilai), bobot 1 / 0.5 / 0,
   - Ringkasan: `Nilai: 18.5/25 (74%)` + rincian PG vs Essay + tombol **Lihat jawaban contoh** untuk semua
     essay sekaligus (mode latihan).
4. **Dua counter (keputusan user):** komponen baru `components/learning/QuizCountFields.tsx`:
   - `Pilihan Ganda` (0–30, default **10**), `Essay` (0–30, default **5**),
   - indikator live **Total: 15/30** (merah + tombol generate ter-disable bila `> 30` atau keduanya 0),
   - tombol preset cepat: `10/5 (default)` · `20/10` · `30/0` · `0/10`.
5. **Backend:** `learning_helper.generate_studio_content(..., count=None, mc_count=None, essay_count=None)`
   — bila `mc_count`/`essay_count` dikirim, prompt memakai keduanya apa adanya (total ≤ 30 dijaga di
   server juga, bukan hanya UI); `count` lama tetap dihormati (backward compatible).
   `studio_api._studio_generate` (**L1548–1560**) membaca key baru `mcCount`/`essayCount` dari body.
6. Prompt quiz (**learning_helper.py L478–490**) diperkuat: instruksi eksplisit mencetak **tepat** N soal
   `"type":"mc"` dan M soal `"type":"essay"` + `model_answer` wajib untuk essay.

**Format 1 — i18n key baru (id / en):**

| Key | id | en |
|---|---|---|
| `learning_quiz_mc_count` | `Jumlah soal pilihan ganda` | `Multiple-choice questions` |
| `learning_quiz_essay_count` | `Jumlah soal essay` | `Essay questions` |
| `learning_quiz_total_count` | `Total: {total}/30` | `Total: {total}/30` |
| `learning_quiz_total_over` | `Total melebihi 30 soal — kurangi salah satu.` | `Total exceeds 30 questions — reduce one side.` |
| `learning_quiz_total_zero` | `Isi minimal satu jenis soal.` | `Set at least one question type.` |
| `learning_quiz_preset_default` | `10 PG + 5 Essay (default)` | `10 MC + 5 Essay (default)` |
| `learning_quiz_answer_hint` | `Jawabanmu otomatis tersimpan sebagai draft.` | `Your answers are auto-saved as a draft.` |
| `learning_quiz_essay_self_mark` | `Nilai mandiri` | `Self-assess` |
| `learning_quiz_essay_done` | `Sesuai` | `Matches` |
| `learning_quiz_essay_partial` | `Sebagian` | `Partial` |
| `learning_quiz_essay_missing` | `Belum` | `Missing` |
| `learning_quiz_score_detail` | `PG {mcCorrect}/{mcTotal} · Essay {essayPoints}/{essayTotal}` | `MC {mcCorrect}/{mcTotal} · Essay {essayPoints}/{essayTotal}` |
| `learning_quiz_review_again` | `Evaluasi ulang` | `Re-evaluate` |
| `learning_quiz_show_model_answers` | `Lihat semua jawaban contoh` | `Show all model answers` |

**Format 2 — File ditimpa:** `web/src/components/views/LearningView.tsx` · `learning_helper.py` ·
`studio_api.py` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/learning/QuizCountFields.tsx`
**Format 4 — Command baru:** payload `/api/ai/quiz` (dan `/api/learning/generate`) menerima
`mcCount`, `essayCount` (selain `count` lama).
**Format 5 — Kesimpulan fase:** Jawaban essay kini benar-benar bisa diketik (controlled, tidak lagi ter-disable oleh flag penilaian, plus draft auto-save), punya penilaian mandiri dengan skor komposit PG+Essay, dan jumlah soal PG/Essay bisa diatur user dengan pengaman total ≤ 30 (default 10 PG + 5 Essay).
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** generate quiz 10 PG + 5 Essay → ketik semua essay → pindah panel → kembali (jawaban utuh) → Evaluasi → skor tampil dengan rincian · uji guard: 20 + 20 → tombol generate ter-disable.

### 📌 REALISASI A04 (2026-09-15) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| `essayAnswers` key stabil `q.id` | ✅ `Record<string, string>` + normalisasi `items[]` (`key = String(q.id ?? i)`) | id dari server = `g<genId>_<i>`; fallback indeks untuk data lama |
| `useRef` mirror | ✅ diganti **satu sumber kebenaran**: tidak perlu mirror karena textarea *controlled* penuh + draft `localStorage` (lebih sederhana, tidak ada state ganda) | teks tetap utuh saat refetch |
| `quizReviewed` (bukan `disabled` saat submit) | ✅ diimplementasikan; `textarea` **tanpa** `disabled` sama sekali | juga untuk opsi PG: hanya PG yang dikunci saat mode nilai |
| Skor komposit | ✅ `PG mcCorrect/mcTotal · Essay poin/total` + persen + hint bobot | |
| Bobot ✅ 1 · 🟡 0,5 · ❌ 0 | ✅ `essayMarks: Record<string, number>` + tombol nilai mandiri | ditambah label nilai `x / 1` per soal |
| "Evaluasi ulang" + "Lihat semua jawaban contoh" | ✅ kedua tombol hadir; **Retake** tetap ada (sekarang juga menghapus draft) | jawaban **tidak** dihapus oleh "Evaluasi ulang" |
| Draft `cl_learning_quiz_draft_<nbId>_<genId>` | ✅ + auto-save debounce 400 ms + load saat ganti notebook + hapus draft setelah generate baru | |
| i18n 14 key (tabel di atas) | ✅ 14 key dikirim, **id disesuaikan**: `10 PG + 5 **Esai** (default)` | + 11 key tambahan (lihat bawah) |
| `QuizCountFields.tsx` (baru) | ✅ dipakai di panel Studio; ekspor `QUIZ_TOTAL_MAX/QUIZ_DEFAULT_MC/QUIZ_DEFAULT_ESSAY/QUIZ_PRESETS` | butuh helper `tr(key, vars, fallback)` — `tr` bawaan hanya 2 argumen → dibuat `trv`/`trq` lokal |
| Backend `mc_count`/`essay_count` | ✅ `learning_helper.generate_studio_content(..., count, mc_count, essay_count)` + `_clamp_cnt` + `count_note`; `studio_api._studio_generate` menerima alias `mcCount/mc_count/mcQuestions` & `essayCount/essay_count/essayQuestions` | |
| Persist quiz ternormalisasi | ✅ `json.dumps({"title":…, "questions": payload["quiz"]})` + `_nb_map` **mempertahankan** `type` & `modelAnswer` (+ deteksi esai untuk data lama) | akar bug "essay jadi PG tanpa opsi" setelah refetch |
| Counter flashcard tetap sendiri | ✅ label baru `learning_flashcard_count_label` (10–30), tombol Generate mati bila total kuis > 30 / 0 | |

**Key i18n tambahan di luar tabel rencana (11):** `learning_quiz_count_title`, `learning_quiz_preset_full`,
`learning_quiz_preset_mc_only`, `learning_quiz_preset_essay_only`, `learning_quiz_hide_model_answers`,
`learning_quiz_score_hint`, `learning_quiz_no_model_answer`, `learning_quiz_ready_title`,
`learning_quiz_ready_msg`, `learning_quiz_generating`, `learning_flashcard_count_label`.

**Hasil uji:** matriks counter 10 baris ✅ · smoke HTTP `mcCount/essayCount` → kwargs ✅ · `_nb_map`
`mc/essay/essay` (soal lama ikut terbaca) ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean ✅ ·
i18n **3.819 → 3.844** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-14-A04-jawaban-essay-counter-kuis.md`](2026-09-14-A04-jawaban-essay-counter-kuis.md).

---

## A05 — Dialog konfigurasi per tipe generator Studio (ala NotebookLM "Customize") ✅ *SELESAI 2026-09-15*

**Item user #2b:** *"setiap generate studio masing-masing tipe generate ada dialog masing-masing — jadi lebih terlihat NotebookLM banget dan profesional."*

**Kondisi sekarang (TERBUKTI):** `LearningView.tsx` **L944–952** — klik kartu tipe langsung memanggil
generator (`handleGenerateQuiz`/`handleGenerateFlashcards`/`handleGenerateStudio`/`handleGeneratePodcast`)
tanpa konfigurasi apa pun; satu-satunya kontrol adalah `studioCount` global (**L960–963**) + `studioTopic`
(**L943**) + ukuran font.

**Perubahan:**
1. **Komponen baru `components/learning/StudioGenerateDialog.tsx`** — dialog seragam `.ct-backdrop`/`.ct-dialog`
   (design system v2), dengan struktur: header (ikon + nama tipe) · **"Konfigurasi"** (kontrol spesifik tipe) ·
   **"Sumber"** (ringkas: `3 sumber dipilih · 12.400 kata` + tombol buka rail sumber — terhubung ke A08) ·
   footer (`Batal` / `Generate`).
2. **Opsi per tipe (8 dialog):**

| Tipe | Kontrol di dialog |
|---|---|
| **Quiz** | Jumlah PG (0–30, def 10) · Jumlah Essay (0–30, def 5) · indikator total ≤ 30 · Tingkat kesulitan (Mudah/Campuran/Sulit) · Bahasa output (Otomatis/id/en) · Fokus topik (opsional, teks) |
| **Flashcards** | Jumlah kartu (5–30, def 15) · Gaya kartu (Istilah→Definisi / Tanya→Jawab / Rumus→Arti) · Tingkat kesulitan · Fokus topik |
| **Audio Overview** | Gaya pembawa acara (Santai/Formal/Debat) · Panjang (Singkat ±6 giliran / Standar 14–24 / Mendalam) · Bahasa · Instruksi tambahan (prompt bebas ala NotebookLM "customize") |
| **Mind Map** | Kedalaman cabang (1–3) · Maks cabang (3–8) · Maks sub per cabang |
| **Study Guide** | Bagian yang disertakan (Ringkasan/Konsep/Contoh/Latihan/Kesimpulan — multi-check) · Jumlah soal latihan (3–10) |
| **FAQ** | Jumlah Q&A (5–15, def 8) · Gaya jawaban (Singkat/Detail) |
| **Timeline** | Granularitas (Hari/Minggu/Bulan/Tahun) · Sertakan tanggal absolut (toggle) |
| **Summary** | Panjang (Ringkas ≤150 kata / Standar ≤400 / Mendalam ≤800) · Gaya (Poin-poin / Naratif) |

3. **Ingat pengaturan terakhir** per notebook (`localStorage` key `cl_learning_studio_cfg_<nbId>_<type>`),
   plus tombol **Reset ke default** — user tidak mengatur ulang tiap kali.
4. **Backend `learning_helper.py`:** parameter baru diteruskan ke prompt masing-masing tipe
   (`difficulty`, `language`, `style`, `length`, `depth`, `branches`, `sections`, `faqCount`, `granularity`,
   `absoluteDates`, `focus`) — semuanya opsional; **tanpa parameter = perilaku lama** (zero-regression).
5. **Backend `studio_api._studio_generate`:** whitelist parameter baru + validasi rentang di server
   (mencegah prompt injection di luar rentang).
6. **Kartu grid Studio** (L944–952) sekarang **membuka dialog**, bukan langsung generate; tombol
   **Cepat** (⚡) di tiap kartu tetap ada untuk generate dengan pengaturan terakhir (power user).

**Format 1 — i18n key baru (id / en) — ±34 key:**

| Key | id | en |
|---|---|---|
| `learning_dialog_title` | `Konfigurasi {type}` | `Configure {type}` |
| `learning_dialog_sources_summary` | `{sources} sumber · {words} kata` | `{sources} sources · {words} words` |
| `learning_dialog_advanced` | `Pengaturan lanjutan` | `Advanced settings` |
| `learning_dialog_remember` | `Ingat pengaturan ini untuk notebook ini` | `Remember these settings for this notebook` |
| `learning_dialog_reset_default` | `Reset ke default` | `Reset to default` |
| `learning_dialog_quick_add` | `Tambahkan ke Studio` | `Add to Studio` |
| `learning_dialog_generate_now` | `Generate sekarang` | `Generate now` |
| `learning_opt_difficulty` | `Tingkat kesulitan` | `Difficulty` |
| `learning_opt_difficulty_easy` | `Mudah` | `Easy` |
| `learning_opt_difficulty_mixed` | `Campuran` | `Mixed` |
| `learning_opt_difficulty_hard` | `Sulit` | `Hard` |
| `learning_opt_language` | `Bahasa hasil` | `Output language` |
| `learning_opt_language_auto` | `Ikuti sumbernya` | `Follow the sources` |
| `learning_opt_focus` | `Fokus topik (opsional)` | `Focus topic (optional)` |
| `learning_opt_card_style` | `Gaya kartu` | `Card style` |
| `learning_opt_card_style_term` | `Istilah → Definisi` | `Term → Definition` |
| `learning_opt_card_style_qa` | `Pertanyaan → Jawaban` | `Question → Answer` |
| `learning_opt_card_style_formula` | `Rumus → Arti` | `Formula → Meaning` |
| `learning_opt_host_style` | `Gaya pembawa acara` | `Host style` |
| `learning_opt_host_casual` | `Santai & akrab` | `Casual & friendly` |
| `learning_opt_host_formal` | `Formal & edukatif` | `Formal & educational` |
| `learning_opt_host_debate` | `Diskusi kritis` | `Critical discussion` |
| `learning_opt_length` | `Panjang` | `Length` |
| `learning_opt_length_short` | `Singkat` | `Short` |
| `learning_opt_length_standard` | `Standar` | `Standard` |
| `learning_opt_length_deep` | `Mendalam` | `In-depth` |
| `learning_opt_depth` | `Kedalaman cabang` | `Branch depth` |
| `learning_opt_branches` | `Jumlah cabang utama` | `Main branches` |
| `learning_opt_sections` | `Bagian yang disertakan` | `Sections to include` |
| `learning_opt_exercises` | `Jumlah soal latihan` | `Practice questions` |
| `learning_opt_faq_count` | `Jumlah Q&A` | `Number of Q&A` |
| `learning_opt_answer_style` | `Gaya jawaban` | `Answer style` |
| `learning_opt_answer_brief` | `Singkat` | `Brief` |
| `learning_opt_answer_detail` | `Detail` | `Detailed` |
| `learning_opt_granularity` | `Granularitas waktu` | `Time granularity` |
| `learning_opt_absolute_dates` | `Sertakan tanggal absolut` | `Include absolute dates` |
| `learning_opt_summary_style` | `Gaya ringkasan` | `Summary style` |
| `learning_opt_summary_bullets` | `Poin-poin` | `Bullet points` |
| `learning_opt_summary_narrative` | `Naratif` | `Narrative` |
| `learning_opt_custom_instructions` | `Instruksi tambahan` | `Extra instructions` |

**Format 2 — File ditimpa:** `learning_helper.py` · `studio_api.py` · `web/src/api/studio.ts` ·
`web/src/components/views/LearningView.tsx`
**Format 3 — File baru:** `web/src/components/learning/StudioGenerateDialog.tsx` ·
`web/src/components/learning/studioOptions.ts` (skema opsi per tipe + serialisasi payload)
**Format 4 — Command baru:** payload baru pada `/api/learning/generate` & `/api/ai/{kind}`
(`difficulty`, `language`, `style`, `length`, `depth`, `branches`, `sections`, `faqCount`, `granularity`,
`absoluteDates`, `focus`, `instructions`, `mcCount`, `essayCount`).
**Format 5 — Kesimpulan fase:** Setiap tipe Studio kini punya dialog konfigurasi sendiri (mirip "Customize" NotebookLM) — pengaturan tersimpan per notebook, divalidasi di server, dan perilaku lama tetap identik bila user memakai tombol Cepat (⚡).
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** buka tiap 8 dialog → generate 1× per tipe → cek hasil sesuai opsi (mis. FAQ 5 vs 15, summary ringkas vs mendalam) · tutup & buka ulang dialog → opsi terakhir masih tersimpan.

### 📌 REALISASI A05 (2026-09-15) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| `components/learning/StudioGenerateDialog.tsx` (baru) | ✅ dibuat; header ikon + nama tipe + 1 baris penjelasan, blok **Sumber**, blok **Konfigurasi**, **Pengaturan lanjutan** (collapse), footer *Ingat…* / *Reset ke default* / *Batal* / *Generate sekarang* | tombol Esc menutup dialog; tombol Generate mati + pesan bila validasi gagal |
| `components/learning/studioOptions.ts` (baru) | ✅ dibuat — skema opsi 8 tipe + default + `loadStudioConfig/saveStudioConfig/resetStudioConfig` + `buildStudioPayload` + `summarizeStudioConfig` + `STUDIO_META` | satu sumber kebenaran untuk dialog **dan** tombol ⚡ |
| 8 dialog dengan opsi per tipe | ✅ semua; **counter PG/Essay (A04) dipindah ke dalam dialog Quiz** (memakai komponen `QuizCountFields` yang sama) + `instructions`/`focus` masuk "Pengaturan lanjutan" | panel Studio kini hanya menampilkan **ringkasan pengaturan terakhir** + tombol *Ubah pengaturan* → tidak ada dua tempat mengatur hal sama |
| Ingat pengaturan `cl_learning_studio_cfg_<nbId>_<type>` | ✅ + checkbox *Ingat pengaturan ini untuk notebook ini* (default aktif) + *Reset ke default*; nilai kunci asing/JSON rusak diabaikan → default | |
| Backend `learning_helper.py` parameter baru | ✅ `difficulty, language, style, length, depth, branches, subs, sections, exercises, faq_count, granularity, absolute_dates, focus, instructions` (semua opsional → **zero-regression**) | `subs` ditambahkan (rencana menyebut "maks sub per cabang" tanpa nama param) |
| Backend `studio_api._studio_generate` whitelist + validasi | ✅ helper baru `_studio_opts()` — whitelist pilihan, clamp angka, potong teks (200/600), filter `sections` ke 5 nilai sah, alias camelCase (`cardStyle/hostStyle/answerStyle/summaryStyle/faqCount/absoluteDates`) | validasi UI **dan** server (dua lapis) |
| Kartu grid → dialog; tombol ⚡ tetap ada | ✅ klik kartu = buka dialog; **⚡** = generate cepat dengan pengaturan terakhir | `activeStudioType` ikut di-set saat kartu/dialog dibuka |
| Kartu `studioCount` (10–30) untuk flashcard | ✅ dipindah ke dialog Flashcards dengan rentang **5–30** (default 15) sesuai rencana; server juga menerima 5–30 | |
| i18n ±34 key | ✅ **84 key** dikirim (tambahan: 8 baris `learning_dialog_blurb_*`, toggle on/off, `learning_opt_subs`, 4 granularitas, 5 nama bagian study guide, `learning_opt_lang_id/_en`, 10 key toast proses, `ai_thinking`) | id disesuaikan (mis. "Campuran", "Diskusi kritis") |

**Hasil uji:** uji prompt 25 kasus (termasuk zero-regression + matriks kuis A04 tetap utuh) ✅ · validasi server 12 kasus ✅ ·
integrasi 8 endpoint via `handle_post` ✅ · uji skema frontend 29 kasus (esbuild → node) ✅ · `tsc --noEmit` 0 error ✅ ·
`vite build` clean ✅ · i18n **3.844 → 3.928** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-15-A05-dialog-generate-studio.md`](2026-09-15-A05-dialog-generate-studio.md).

---

## A06 — Hasil generate sebagai daftar artefak rapi (list ke bawah) ✅ *SELESAI 2026-09-15*

**Item user #2c:** *"setiap generate studio berbentuk list ke bawah — ada di dalam list rapi."*

**Kondisi sekarang (TERBUKTI):** output Studio = **satu** area `max-h-[360px]` (**L966–969**) yang menampilkan
tipe aktif saja, plus **daftar riwayat kecil** `max-h-40` di bawahnya (**L977–995**) yang hanya chip
`gtype + topic + tanggal`. Tidak ada nama artefak, aksi, filter, atau preview — hasil generate terasa
"hilang" begitu tipe lain dipilih.

**Perubahan:**
1. **Komponen baru `components/learning/StudioArtifactList.tsx`** — daftar vertikal (list ke bawah) sebagai
   **isi utama panel Studio**:
   - **Kartu artefak:** ikon tipe · judul (`title`/topik) · badge tipe · waktu relatif ("3 menit lalu") ·
     jumlah item ("15 soal", "20 kartu", "18 giliran") · ukuran · sumber yang dipakai (jumlah) ·
     aksi: **Buka**, **Ganti nama**, **Ekspor (.md)**, **Duplikat**, **Hapus**;
   - **Filter chips** per tipe (Semua/Quiz/Flashcards/…), **pencarian** judul, **urutan** (Terbaru/Terlama/Tipe);
   - **Empty state** yang mengarahkan ke dialog generator;
   - **Klik kartu → detail artefak** dirender tepat di bawah kartu (akordeon) atau di area detail
     (menyesuaikan mode panel), sehingga tetap "satu scroll list" sesuai permintaan user.
2. **Backend `database.py`:** fungsi baru `rename_learning_generation(gen_id, notebook_id, title)` +
   `db.get_learning_generation(gen_id, notebook_id)`; `_nb_map` (`studio_api.py` **L113–135**) menambah
   `itemCount`, `sizeBytes`, `title` yang sudah ada → dipakai UI untuk metadata kartu.
3. **Backend `studio_api.py`:** endpoint baru **`POST /api/learning/generations/rename`** dan
   **`GET /api/learning/generations/export?generationId=&notebookId=&format=md|txt`**.
4. **Riwayat lama digantikan** oleh daftar artefak ini (tidak ada lagi dua daftar yang membingungkan);
   tombol hapus tetap memakai `delete_learning_generation` yang ada.

**Format 1 — i18n key baru (id / en):**

| Key | id | en |
|---|---|---|
| `learning_artifacts` | `Hasil Studio` | `Studio outputs` |
| `learning_artifacts_count` | `{n} hasil` | `{n} outputs` |
| `learning_artifact_open` | `Buka` | `Open` |
| `learning_artifact_rename` | `Ganti nama` | `Rename` |
| `learning_artifact_export_md` | `Ekspor .md` | `Export .md` |
| `learning_artifact_duplicate` | `Duplikat` | `Duplicate` |
| `learning_artifact_delete` | `Hapus` | `Delete` |
| `learning_artifact_items_quiz` | `{n} soal` | `{n} questions` |
| `learning_artifact_items_cards` | `{n} kartu` | `{n} cards` |
| `learning_artifact_items_turns` | `{n} giliran` | `{n} turns` |
| `learning_artifact_empty_title` | `Belum ada hasil Studio` | `No Studio outputs yet` |
| `learning_artifact_empty_hint` | `Pilih salah satu tipe di atas untuk membuat materi baru.` | `Pick a type above to create new material.` |
| `learning_artifact_filter_all` | `Semua` | `All` |
| `learning_artifact_sort_newest` | `Terbaru` | `Newest` |
| `learning_artifact_sort_oldest` | `Terlama` | `Oldest` |
| `learning_artifact_sort_type` | `Tipe` | `Type` |
| `learning_artifact_renamed` | `Nama hasil diperbarui` | `Output renamed` |
| `learning_artifact_now` | `baru saja` | `just now` |

**Format 2 — File ditimpa:** `database.py` · `studio_api.py` · `web/src/components/views/LearningView.tsx` ·
`web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/learning/StudioArtifactList.tsx`
**Format 4 — Command baru:**
```
POST /api/learning/generations/rename     {"generationId","notebookId","title"}
GET  /api/learning/generations/export?generationId=&notebookId=&format=md|txt
```
**Format 5 — Kesimpulan fase:** Semua hasil generate kini tampil sebagai satu daftar artefak vertikal yang rapi (filter, pencarian, urutan, rename, ekspor, duplikat, hapus) — menggantikan riwayat chip kecil yang mudah hilang; user bisa membuka detail tanpa kehilangan yang lain.
**Format 6 — Migrasi:** Kolom baru `learning_generations.updated_at` (SQLite, via `_safe_alter` di `init_db()`); `title` sudah ada.
**Verifikasi:** generate 4 tipe berbeda → daftar memuat 4 kartu · rename & ekspor satu kartu · hapus satu kartu → daftar & notebook tersinkron.

### 📌 REALISASI A06 (2026-09-15) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| `components/learning/StudioArtifactList.tsx` (baru) | ✅ dibuat — kartu artefak + filter chips dinamis + pencarian + urutan + pratinjau akordeon + dialog ganti nama. **Pratinjau (`ArtifactPreview`) ikut di berkas yang sama** agar tetap 1 file baru seperti rencana | pratinjau membaca `content` milik kartu itu sendiri (read-only), jadi artefak lama tetap bisa dibaca |
| Detail artefak "di bawah kartu (akordeon) atau area detail" | ✅ akordeon di dalam daftar (satu scroll). Area interaktif (kuis dikerjakan / kartu dibalik / podcast diputar) **tetap dipertahankan** di atas daftar dan kini bisa **dilipat** — supaya alur A04 (menjawab esai) tidak berubah | bila artefak yang dibuka bukan yang terbaru, muncul toast jujur: area interaktif memakai hasil terbaru tipe itu (`learning_artifact_not_latest`) |
| Aksi: Buka · Ganti nama · Ekspor (.md) · Duplikat · Hapus | ✅ kelima aksi ada + **Ekspor .txt** (karena endpoint memang mendukung `md|txt`) | ikon `lucide` konsisten dengan panel lain |
| Backend `database.py`: `rename_learning_generation` + `get_learning_generation` | ✅ keduanya + **`duplicate_learning_generation`** (untuk aksi Duplikat) | judul dipangkas 120 karakter & wajib tidak kosong |
| `_nb_map` menambah `itemCount`/`sizeBytes`/`title` | ✅ plus `words` dan `updatedAt`; perhitungan lewat helper `_artifact_meta()` (tahan isi rusak / bukan JSON) | tipe teks dihitung per **kata** ("340 kata") |
| Endpoint `rename` + `export` | ✅ keduanya + **`duplicate`**; `export` mengembalikan berkas *staged* (`{id,name,size,format,gtype,itemCount}`) lalu diunduh via `/api/system/download-file` (jalur A03.5 yang sudah terbukti) | format tak dikenal dinormalkan ke `md` |
| Riwayat lama digantikan | ✅ blok riwayat chip + tombol hapus lama **dihapus** dari `LearningView` | tombol hapus per kartu memakai `delete_learning_generation` yang sama |
| Migrasi `learning_generations.updated_at` | ✅ `_safe_alter` di `init_db()` (idempoten, DB lama otomatis dapat kolom baru) | |
| — (tambahan tak terencana) | ✅ **`Content-Type` per ekstensi** untuk semua berkas unduhan (`_dl_mime_for`) — sebelumnya semuanya `application/octet-stream`, sehingga `.md/.csv/.lrc` tidak dikenali browser | memperbaiki seluruh ekspor A03.5 juga |

**Hasil uji:** metadata artefak 6 kasus ✅ · markdown/teks 9 kasus ✅ · live end-to-end (rename + updatedAt, duplikat, hapus,
ekspor .md 262 byte & .txt 84 byte dengan nama berkas + Content-Type benar, kasus gagal `title_required`/`learning_not_found`) ✅ ·
`tsc --noEmit` 0 error ✅ · `vite build` clean ✅ · i18n **3.928 → 3.968** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-15-A06-daftar-artefak-studio.md`](2026-09-15-A06-daftar-artefak-studio.md).

---

## A07 — Restrukturisasi UI Learning Page ala NotebookLM ✅ *SELESAI 2026-09-15*

**Item user #2d:** *"tampilan UI dan GUI learning page aku mau samakan dengan NotebookLM tapi sedikit identik, punya ciri khas sendiri untuk CraftLife, secara fungsional 100% sama."*

**Kondisi sekarang (TERBUKTI):** satu baris panel dengan 3 kolom yang bisa di-*drag-resize*
(`LearningView.tsx` **L297–345** logika resize + localStorage), toggle 3 tombol (**L769–790**),
panel `Sumber` (**L822–860**), `Chat` (**L870–912**), `Studio` (**L914–995**). Semua berbagi latar
`slate-900/70` + aksen violet; ikon `lucide`; judul panel berupa label uppercase kecil.

**Perubahan (fungsi 100% dipertahankan, lapisan tampilan diganti):**
1. **Shell ala NotebookLM:**
   - **Rail kiri sempit (72px)** — berpindah antar-notebook (avatar inisial), tombol **+ Notebook**,
     **Sumber**, **Chat**, **Studio**, dan pemilih bahasa; pada layar besar rail bisa melebar (220px)
     menampilkan daftar notebook + judul.
   - **Kolom tengah (Sumber ⇄ Chat bertukar konteks):** default NotebookLM = daftar **Sumber** sebagai
     view utama dengan kartu sumber (ikon tipe, judul, jumlah kata, tanggal, chip "dipakai"),
     lalu tombol mengalihkan ke **Chat** yang menampilkan riwayat dengan balon pengguna/AI.
   - **Kolom kanan = Studio (daftar artefak dari A06)** dengan grid peluncur 8 tipe di bagian atas.
   - **Topbar:** judul notebook **inline-editable** (rename langsung, endpoint rename sudah ada),
     chip jumlah sumber, tombol panel (Sumber/Chat/Studio), tombol ekspor & pengaturan.
2. **Design language ala NotebookLM + identitas CraftLife:**
   - Latar netral gelap berlapis (`#141318` → `#1c1b21`), permukaan kartu `rgba(255,255,255,.03)`,
     border 1px halus, radius 14–18px, **tanpa glow berlebih** (tetap patuh aturan anti-flicker R10);
   - Aksen utama **tetap emerald/violet CraftLife** (bukan biru Google) → "sedikit identik, punya ciri khas";
   - Tipografi campuran: `Plus Jakarta Sans` untuk UI + **`JetBrains Mono`** untuk badge/angka (sudah dimuat);
   - Sorotan sumber pada jawaban chat memakai chip ringan (disiapkan di A08);
   - Ikon tetap `lucide` (tidak menambah dependency).
3. **Interaksi:** panel kanan bisa **collapse** (bukan drag bebas) dengan 3 preset lebar
   (Sempit 320px / Sedang 420px / Lebar 560px) — menyederhanakan resize manual yang rawan di WebEngine;
   `localStorage` menyimpan preset + status panel per notebook (kompatibel dengan key lama
   `cl_learning_panel_widths` → dimigrasi otomatis).
4. **Responsif:** < 1024px → rail jadi bottom-bar, panel jadi tab penuh (Sumber/Chat/Studio), tanpa scroll ganda.
5. **Semua fungsi lama tetap:** buat/hapus/rename notebook, unggah sumber (file/URL/teks), lihat isi sumber,
   chat AI, 8 generator (kini lewat dialog A05), ekspor, hapus hasil, ubah ukuran font hasil, TTS podcast.

**Format 1 — i18n key baru (id / en) — ±22 key:**

| Key | id | en |
|---|---|---|
| `learning_nb_switcher` | `Notebook` | `Notebook` |
| `learning_topbar_sources` | `{n} sumber` | `{n} sources` |
| `learning_topbar_ready` | `Siap dijawab AI` | `Ready for AI answers` |
| `learning_view_sources` | `Sumber` | `Sources` |
| `learning_view_chat` | `Chat` | `Chat` |
| `learning_view_studio` | `Studio` | `Studio` |
| `learning_add_source_hint` | `Tambahkan sumber untuk memulai — PDF, dokumen, teks, atau tautan.` | `Add a source to begin — PDF, document, text, or link.` |
| `learning_source_used` | `Dipakai` | `Used` |
| `learning_source_unused` | `Tidak dipakai` | `Not used` |
| `learning_source_type_pdf` | `PDF` | `PDF` |
| `learning_source_type_doc` | `Dokumen` | `Document` |
| `learning_source_type_text` | `Teks` | `Text` |
| `learning_source_type_url` | `Tautan` | `Link` |
| `learning_source_type_youtube` | `YouTube` | `YouTube` |
| `learning_panel_narrow` | `Sempit` | `Narrow` |
| `learning_panel_medium` | `Sedang` | `Medium` |
| `learning_panel_wide` | `Lebar` | `Wide` |
| `learning_panel_collapse` | `Sembunyikan panel` | `Hide panel` |
| `learning_rename_notebook` | `Ganti nama notebook` | `Rename notebook` |
| `learning_suggestion_q1` | `Jelaskan konsep utama dari sumber ini` | `Explain the key concepts in this source` |
| `learning_suggestion_q2` | `Buat rangkuman singkat untuk belajar cepat` | `Create a quick study summary` |
| `learning_suggestion_q3` | `Apa yang sering ditanyakan dari materi ini?` | `What is commonly asked about this material?` |
| `learning_suggestion_q4` | `Buatkan kuis dari materi ini` | `Create a quiz from this material` |

**Format 2 — File ditimpa:** `web/src/components/views/LearningView.tsx` (rombak) · `web/src/index.css`
(token `--ct-nlm-*` + kelas kartu/permukaan baru)
**Format 3 — File baru:** `web/src/components/learning/LearningShell.tsx` ·
`web/src/components/learning/SourcesRail.tsx` · `web/src/components/learning/ChatPanel.tsx` ·
`web/src/components/learning/NotebookRail.tsx` · `web/src/components/learning/SourceCard.tsx`
**Format 4 — Command baru:** — (memakai endpoint yang sudah ada; rename notebook via endpoint yang sama
dengan rename/duplikat yang ada)
**Format 5 — Kesimpulan fase:** Learning Page kini bertata letak NotebookLM (rail notebook → Sumber ⇄ Chat → Studio) dengan identitas visual CraftLife: warna, tipografi, dan ornamennya sendiri — seluruh 22 fungsi lama tetap utuh, dan resize manual yang rawan digantikan preset panel + collapse.
**Format 6 — Migrasi:** — (tidak ada; preferensi panel di localStorage dengan migrasi otomatis)
**Verifikasi:** `tsc --noEmit` · `vite build` · uji headless WebEngine/Chromium: 29 halaman tetap jalan · uji 22 fungsi Learning satu per satu · uji breakpoint 768/1024/1440px.

---

### 📌 REALISASI A07 (2026-09-15) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| `components/learning/{LearningShell,SourcesRail,ChatPanel,NotebookRail,SourceCard}.tsx` (baru) | ✅ **kelimanya dibuat persis seperti rencana** (tidak dikonsolidasi) — `SourceCard` dipisah karena juga dipakai `SourcesRail` untuk kartu jenis sumber & akan dipakai A08 untuk chip sitasi | `LearningShell` memegang state tata letak + migrasi key lama; `NotebookRail` memegang rail & bottom-bar |
| Rail 72 px → 220 px (avatar + judul) | ✅ `--rail-w` diset dari state shell; tombol melebar/menyempit ada di kepala rail | di layar <1024 px rail menjadi **bottom-bar**; tombol Sumber/Chat/Studio hanya di desktop karena tab mobile menangani hal sama (menghindari kontrol kembar) |
| Topbar: judul **inline-rename** + chip sumber + tombol panel | ✅ judul `<input>` memakai endpoint `rename` yang sudah ada; `Enter` simpan · `Esc` batal · tidak berubah = tanpa panggilan API | chip: `{n} sumber` · `{m} kata` · status “Siap dijawab AI” |
| Panel Sumber: kartu (ikon tipe · judul · jumlah kata · tanggal · chip `used/unused`) | ✅ + **pencarian** (aktif bila >3 sumber), **Upload** & **Tambah**, empty state, footer `n sumber · grounding` | chip Dipakai/Tidak dipakai **sudah interaktif** (state lokal, tersinkron dengan daftar sumber) → tinggal disambungkan ke API di A08 |
| Panel Chat: bubble + kartu saran + composer | ✅ balon tetap memakai **ReactMarkdown + prose** (format jawaban AI tidak berubah), 4 kartu saran langsung mengirim pertanyaan, saran hanya tampil saat chat kosong | `handleSendChat` menerima teks eksplisit — aman untuk `onClick` biasa (argumen non-string diabaikan) |
| Studio kanan = daftar artefak A06 + grid peluncur 8 tipe | ✅ keduanya utuh & berurutan (grid A05 → ringkasan pengaturan → area interaktif bisa dilipat → daftar artefak A06) | kontrol font hasil + topik + Ekspor tetap di tempatnya |
| **Preset 320/420/560 + collapse**, migrasi `cl_learning_panel_widths` | ✅ tombol preset berputar Sempit→Sedang→Lebar, tombol panel untuk sembunyikan/tampilkan; key baru **`cl_learning_layout`** | lebar efektif dibatasi `total − rail − 360 px` agar kolom tengah tidak pernah terjepit; drag-resize (`renderPanelDivider`, `panelSizes`, `resizing`, `rowRef`, `touchX`, `panelIdx`, `compactPanel`) **dihapus** |
| <1024 px: rail → bottom-bar + tab panel | ✅ rail `hidden lg:flex` + bottom-bar mobile, tab Sumber/Chat/Studio, kolom tengah/Dstudio bergantian via state `view` | breakpoint Tailwind `lg` = 64rem (1024 px) terverifikasi di CSS hasil build |
| 22 fungsi Learning tetap 100 % | ✅ **24/24 smoke live** mencakup semua endpoint yang dipakai 22 fungsi itu (notebook CRUD, sumber, chat, 8 generator, artefak, ekspor, bahasa) | tidak ada endpoint baru — Format 4 memang kosong |
| — (tambahan tak terencana) | ✅ **CSS section “7b. LEARNING SHELL”** (+140 baris) dengan token `--ct-nlm-*`; ✅ **pemilih bahasa di rail**; ✅ **kartu saran chat**; ✅ **chip grounding interaktif** (fondasi A08); ✅ pembersihan 9 impor ikon yang tak lagi dipakai | semua bebas `backdrop-filter` (R10) |

**Hasil uji:** logika tata letak **11/11** ✅ · render komponen **10/10** ✅ · live API **24/24** ✅ · `tsc --noEmit` 0 error ✅ ·
`vite build` clean ✅ · i18n **3.968 → 3.998** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-15-A07-shell-learning-notebooklm.md`](2026-09-15-A07-shell-learning-notebooklm.md).

---

## A08 — Sitasi sumber + pemilihan sumber grounding ✅ *(selesai 2026-09-15; diperluas dengan permintaan user: podcast dua host + migrasi SDK)*

**Item user #2e (turunan "fungsional 100% seperti NotebookLM"):** jawaban AI menunjuk sumbernya, dan hanya sumber terpilih yang dipakai.

**Kondisi sekarang (TERBUKTI):** `studio_api._chat_ai` (**L1438+**) mengirim jawaban sebagai teks polos;
`add_learning_chat` menyimpan `(role, content)` saja (tabel `learning_chats`); sumber digabung buta
(`_nb_map` L134–140 membatasi tiap sumber 4.000 karakter) tanpa penanda `[1]`, `[2]`.

**Perubahan:**
1. **Backend `learning_helper.py`:** prompt chat diberi daftar sumber bernomor (`[S1] Judul: …`) dan
   diwajibkan mencantumkan sitasi `[S1]`/`[S2]` pada klaim; `_chat_ai` mengembalikan
   `{answer, citations:[{index, sourceId, title, snippet}]}` dengan pemetaan nomor → baris sumber.
2. **Pemilihan sumber:** `_chat_ai` & `_studio_generate` menerima `sourceIds: []` → hanya sumber itu yang
   dijadikan konteks (default: semua). Ditampilkan di UI sebagai checkbox di `SourcesRail` (A07) dengan
   indikator "3 dari 5 sumber dipakai" (i18n `learning_source_used` sudah disiapkan).
3. **Frontend `ChatPanel`:** chip sitasi `[1]` di dalam balon jawaban → hover/klik menampilkan popover
   (judul sumber + potongan kalimat) → klik membuka sumber penuh (endpoint `source-content` yang ada).
4. **Fallback aman:** bila model tidak memberi sitasi, jawaban tetap ditampilkan tanpa chip (tidak error) —
   ditandai `citations: []`.

**Format 1 — i18n key baru (id / en) — ±8 key:** `learning_citations` (`Sitasi` / `Citations`) ·
`learning_citation_source_n` (`Sumber {n}` / `Source {n}`) · `learning_cite_from_sources` (`Jawab
hanya dari sumber terpilih` / `Answer only from selected sources`) · `learning_sources_selected_count`
(`{n} dari {total} sumber dipakai` / `{n} of {total} sources used`) · `learning_citation_unavailable`
(`Model tidak memberi sitasi untuk jawaban ini.` / `The model gave no citations for this answer.`) ·
`learning_open_source` (`Buka sumber` / `Open source`) · `learning_filter_sources` (`Pilih sumber` /
`Select sources`) · `learning_grounding_on` (`Grounding aktif` / `Grounding on`)

**Format 2 — File ditimpa:** `learning_helper.py` · `studio_api.py` · `database.py` (simpan `citations` JSON
di `learning_chats` — kolom baru via `_safe_alter`) · `web/src/components/learning/ChatPanel.tsx` ·
`web/src/components/learning/SourcesRail.tsx` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/learning/CitationChip.tsx`
**Format 4 — Command baru:** payload `sourceIds` untuk `/api/ai/chat` & `/api/learning/generate`;
respons chat menambah `citations[]`.
**Format 5 — Kesimpulan fase:** Jawaban AI kini dapat dilacak ke sumber aslinya (chip sitasi → potongan → isi penuh) dan generate/chat bisa dibatasi ke sumber tertentu — dua ciri paling khas NotebookLM.
**Format 6 — Migrasi:** kolom baru `learning_chats.citations` (TEXT/JSON, SQLite).
**Verifikasi:** chat dengan 3 sumber → sitasi muncul & mengarah ke sumber benar · nonaktifkan 2 sumber → jawaban hanya mengutip yang aktif · model tanpa sitasi → tidak error.
**Catatan risiko:** fase ini bergantung pada kepatuhan model Gemini terhadap format sitasi; bila hasilnya tidak konsisten saat uji, fase ini **ditunda ke commit phase berikutnya** tanpa menahan A09–A14 (dependensinya satu arah).

### 📌 REALISASI A10 (2026-09-16) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| Migrasi `relationship_memories` +5 kolom & `relationship_bucket_items` +5 kolom | ✅ **9 kolom baru** (`memories`: `emoji`, `tags`, `is_favorite`, `photo_id`, `updated_at`; `bucket_items`: `notes`, `priority`, `updated_at`, `promoted_memory_id`) — `category` & `target_date` ternyata **sudah ada** sejak skema awal, jadi hanya dipastikan via `_safe_alter` | **plus 2 indeks** (`idx_relationship_memories_user_fav`, `idx_relationship_bucket_items_user_due`); migrasi idempoten (diuji `init_db()` dua kali) |
| Fungsi DB baru: `update_relationship_memory` · `toggle_memory_favorite` · `update_relationship_bucket_item` · `get_relationship_bucket_stats` | ✅ semua ada, **plus** `get_relationship_memory` · `get_relationship_bucket_item` (satu baris) · `promote_relationship_bucket_item` (item → kenangan, idempoten) · helper `_love_tags_norm` / `love_memory_tags` | `add_relationship_memory` & `add_relationship_bucket_item` diperluas dengan argumen opsional (pemanggil lama tetap jalan) |
| API `memories/<id>/update` · `memories/<id>/favorite` · `bucket/<id>/update` · `bucket/<id>/promote-to-memory` | ✅ keempatnya hidup + validasi nyata (`love_memory_title_required`, `love_memory_date_required`, `love_bucket_title_required`, `no_fields`, `learning_not_found`) | `POST /api/love/memories` & `POST /api/love/bucket` kini menerima payload lengkap; snapshot `loveSpace` menambah `memoryYears`, `memoryTags`, `memoryStats`, `bucketStats` |
| UI `memories`: toolbar (cari/tahun/tag/favorit/urutan), kartu timeline, emoji bisa dipilih, badge tag, bintang, thumbnail foto, edit, hapus | ✅ semua terpasang; dulu emoji **selalu** `"💖"` dari `_love_map` — kini kolom asli + pemilih 12 emoji & emoji bebas | **plus** 4 kartu statistik (total · favorit · bertag · berfoto), chip tag yang bisa diklik untuk memfilter, jejak “diubah {tanggal}”, dan pratinjau chip tag di dialog |
| UI Bucket List: progres bar, kategori berikon, target tanggal + badge `⏰ terlewat`/`H-30`, catatan, prioritas ⭐, filter (Semua/Belum/Selesai/Terlewat), dialog edit, tombol “Simpan jadi kenangan” | ✅ semua terpasang; **plus** pencarian item, chip statistik (total/selesai/belum/lewat target), tambah cepat (Enter) yang mempertahankan perilaku lama, dan penanda “Sudah jadi kenangan” | promote membawa **tanggal pencapaian** + catatan item + tag `bucket, <kategori>`; item ditandai `promoted_memory_id` sehingga **tidak bisa diduplikasi** |
| Format 1 (i18n ± 24 key) | ✅ **90 key** (naik 4.076 → 4.166) | perlu tambahan untuk toolbar, statistik, filter berhitungan, label kategori bucket, dan pesan validasi |
| Format 3 (`LoveMemoryDialog.tsx` · `LoveBucketDialog.tsx`) | ✅ keduanya dibuat, **plus 1 file tak terencana: `components/love/memoryUtils.ts`** (logika murni tanggal/tag/filter/statistik supaya bisa diuji tanpa DOM, pola sama seperti `eventUtils.ts` A09) | `studio.ts` +4 method; `GameContext` +4 action (`updateLoveMemory`, `loveMemoryFavorite`, `updateLoveBucket`, `promoteLoveBucket`) & `addLoveMemory` kini ber-payload objek |
| Format 6 (SQLite 9 kolom + Supabase opsional “perluas migrasi A09”) | ✅ SQLite otomatis; Supabase dibuat sebagai **berkas tersendiri** `20260916010000_phase_a10_love_memories_bucket.sql` (lebih aman: migrasi A09 sudah tersebar, jadi tidak ditimpa) | kolom `photo_id` (kenangan) & `promoted_memory_id` (bucket) **sengaja tidak dikirim ke cloud** — keduanya menunjuk data lokal; `cloud_service.migrate_love_space_from_local` diperluas agar emoji/tag/favorit/catatan/prioritas ikut bermigrasi |
| — (temuan tambahan saat uji) | ✅ `mirror_cloud_love_record` (memory & bucket) diperluas supaya kolom baru tidak hilang saat sinkronisasi · ✅ `love_gallery_privacy_hint` yang selama ini **belum ada** di i18n ikut ditambahkan | keduanya ketemu dari audit kode, bukan dari laporan user |

**Hasil uji:** DB **65/65** ✅ · logika+render FE **77/77** ✅ · render tab memories+bucket **37/37** ✅ ·
live API **45/45** ✅ · regresi A07+A08+A09+Love **38/38** ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean ✅ ·
i18n **4.076 → 4.166** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-16-A10-love-memories-bucket-list.md`](2026-09-16-A10-love-memories-bucket-list.md).

### 📌 REALISASI A09 (2026-09-16) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| Migrasi 6 kolom `relationship_events` | ✅ `icon`, `location`, `is_special`, `recurring`, `remind_days_before`, `updated_at` via `_safe_alter` (idempoten; diuji dengan `init_db()` dua kali) | kolom `notes` memang sudah ada — **hole-nya murni UI**, persis dugaan user |
| `add_relationship_event` diperluas · `update_…` · `get_relationship_events(include_past)` · `upcoming_relationship_events` | ✅ semua ada; nama fungsi mengikuti gaya file (`get_relationship_event` untuk satu baris, `update_relationship_event`, `upcoming_relationship_events`) | **plus** helper baru `_love_recurring_norm`, `_love_remind_norm`, `_love_next_occurrence`, `_love_days_until`, `_love_date_add_days` |
| API `POST /api/love/events/<id>/update` + `GET /api/love/events/upcoming` | ✅ keduanya hidup; `_love_map` menambah `upcomingEvents` + `specialDays` ke snapshot `loveSpace` (aman offline) | **plus** validasi `love_event_title_required` / `love_event_date_required` dan normalisasi nilai liar |
| Komponen baru `components/love/LoveEventDialog.tsx` | ✅ dipakai untuk **Tambah & Edit**; berisi judul · tanggal · 6 kategori berikon · pemilih ikon (12 preset + kustom) · lokasi · **catatan** · toggle Special Day → tahunan + pengingat H-n · **pratinjau hitung mundur** · validasi | **plus file tak terencana `components/love/eventUtils.ts`** — logika tanggal/pengelompokan murni supaya bisa diuji tanpa DOM dan dipakai bersama kartu & dialog |
| Kartu tab `plans` dirombak (Akan datang / Sudah lewat, pencarian, filter kategori, ikon ⭐, notes 2 baris, Edit + Hapus) | ✅ semua terpasang + **filter “hanya hari istimewa”**, **badge `H-12`/`Hari ini!`**, **chip 🔔 H-n**, **kartu “Hari istimewa terdekat”** yang otomatis memuat **ulang tahun & hari jadi dari profil** | kolom Bucket List **dipertahankan apa adanya** (dipoles di A10 sesuai rencana) |
| Sinkronisasi cloud aman | ✅ payload acara dikirim lengkap; jalur cloud memakai `love_upsert_cloud` dengan `record_id` cloud yang ada (bukan bikin baris baru) | server lama mengabaikan kunci tak dikenal → tidak ada regresi |
| — (temuan tambahan saat uji) | ✅ **daftar langsung diperbarui** setelah simpan (dulu `applyLive` tidak membawa `loveSpace`, jadi acara baru tidak muncul sampai reload) · ✅ **deep-link sub-tab** `?loveTab=plans` (pola `?login=1`) · ✅ 2 kategori baru (**Anniversary**, **Liburan**) + i18n-nya | |

**Hasil uji:** DB **37/37** ✅ · logika+render FE **51/51** ✅ · render tab plans **17/17** ✅ · live API **19/19** ✅ ·
regresi A07+A08+Love **23/23** ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean ✅ · i18n **4.030 → 4.076** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-16-A09-love-plans-special-days.md`](2026-09-16-A09-love-plans-special-days.md).

### 📌 REALISASI A08 (2026-09-15) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| Prompt sumber bernomor `[S1]` + wajib sitasi | ✅ `chat_with_citations()` baru di `learning_helper.py` (prompt: daftar `[S1] Judul: …`, aturan “setiap klaim wajib penanda”, sapaan/pertanyaan balik tanpa sitasi, `temperature 0.4`) | regex `_CITE_RE` menangkap `[S1]`–`[S9]`, dedupe nomor, potongan kalimat `_citation_snippet` ≤ 200 karakter pada batas kata |
| `_chat_ai` → `{answer, citations[], grounded, sourcesUsed}` | ✅ `studio_api._chat_ai` mengembalikan **dict** + `_parse_citations/_normalize_ids`; fallback aman ke potongan teks lama bila model gagal | 2 rute chat (notebook & `/api/ai/chat`) mengirim `answer` + `citations` + `grounded` + `sourcesUsed` |
| Pemilihan sumber: `sourceIds: []` untuk chat **dan** generate | ✅ diterima di `POST …/chat` (array/string) dan `_studio_generate` via `_selected_sources` | kosong = semua sumber (perilaku lama tidak berubah) |
| Chip sitasi di balon + popover + buka sumber | ✅ `CitationChip.tsx` (baru): `[S1]` → chip nomor → popover judul + snippet + **Buka sumber** (endpoint `source-content`); di bawah balon ada baris ringkasan sitasi | sitasi **tahan reload** karena ikut disimpan di `learning_chats.citations` dan dikirim `_nb_map` sebagai `chatHistory[].citations` |
| Fallback model tanpa sitasi | ✅ `citations: []` → jawaban tampil apa adanya, **tanpa error** | diuji pada smoke (mock mengembalikan `[S1]`; jalur “tanpa penanda” diuji di unit) |
| — (permintaan user 2026-09-15) Podcast interaktif & berbahasa Indonesia | ✅ **`PodcastPlayer.tsx` (baru, 340+ baris)** + `build_podcast_audio()` (edge-tts per giliran, `id-ID-ArdiNeural`/`GadisNeural`, fallback gTTS) + endpoint `POST/GET /api/learning/podcast/audio` + tabel `learning_audio` | akar keluhan `speakLine` (SpeechSynthesisUtterance tanpa `lang`) **dihapus total**; pemutar: klik giliran = seek, sorotan aktif + auto-scroll, ±15 dtk, kecepatan, loop, unduh, buat ulang; HTTP Range/206 untuk seek |
| — (keluhan terminal user) `google.generativeai` end of support | ✅ migrasi ke **`google.genai`** (`genai.Client` + `client.models.generate_content`) dengan multi-model & retry; `google.generativeai` hanya jaring pengaman | `requirements.txt`: `google-genai>=1.0.0` (wajib), `google-generativeai` dibuang, `gTTS>=2.5.0` ditambah |
| Format 1 (i18n ± 8 key) | ✅ **32 key** (30 A08 + `play`/`pause`) | perlu tambahan untuk kontrol pemutar (seek, ±15 dtk, kecepatan, loop, ikuti, unduh, mesin suara, host, dll) |
| Format 3 (`CitationChip.tsx`) | ✅ dibuat, **plus 1 file tak terencana: `PodcastPlayer.tsx`** | `studio.ts` menambah `chat(sourceIds)`, `podcastAudio()`, `podcastAudioUrl()`; `GameContext.addNotebookChat` menerima `citations` |
| Format 6 (`learning_chats.citations`) | ✅ **plus tabel baru `learning_audio`** (kolom: notebook_id, generation_id, path, language, engine, voice_a, voice_b, duration_sec, size_bytes, turns_json, created_at) | semua via `_safe_alter`/`CREATE TABLE IF NOT EXISTS` → idempoten, SQLite-only |

**Hasil uji:** unit helper AI **23/23** ✅ · render komponen FE **20/20** ✅ · live API **25/25** ✅ ·
regresi A07 **24/24** ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean ✅ · i18n **3.998 → 4.030** ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-15-A08-citasi-grounding-podcast-sdk.md`](2026-09-15-A08-citasi-grounding-podcast-sdk.md).

---

# 🌸 KLASTER 3 — LOVE SPACE (#3)

> **Audit lengkap 6 sub-tab** (bukan hanya `plans`) sudah dilakukan; ringkasan temuan hole → fase:
> `plans` (**A09**, **A10**) · `memories`/`bucket` (**A10**) · `connection`/`cycle`/`gallery` (**A11**) ·
> `overview` (**A12**). Aturan pekerjaan: **tidak menghapus fungsi yang ada**, hanya melengkapi dan
> memprofesionalkan (UX + data + integrasi).

## A09 — Tab `plans`: notes event (hole), edit, dan Special Days/recurring ✅ *(selesai 2026-09-16)*

**Item user #3a:** *"di bagian subtab plans, untuk penambahan events & special days tidak ada penambahan notes — itu jelas kurang (holes feature) dan kurang profesional."*

**Akar masalah (TERBUKTI — persis seperti dugaan user):**
- `LoveSpaceView.tsx` **L276** mendeklarasikan `const [evNotes, setEvNotes] = useState('')` dan
  **L1032** mengirimnya ke `loveEvent({ ..., notes: evNotes })` — **tetapi tidak ada satu pun input yang
  mengikat `setEvNotes`** (grep: hanya `setEvNotes('')` saat reset). → **field notes mustahil diisi**.
- **L1048** hanya ada tombol hapus; **tidak ada edit** event (API hanya menyediakan
  `/api/love/events/${id}/delete` — `web/src/api/studio.ts`).
- DB sudah punya kolom `notes` (`database.py` **L1396–1405** `relationship_events`) → hole-nya murni UI,
  tapi **special day / recurring tidak ada sama sekali** (tidak ada kolom, tidak ada logika).
- Tidak ada pengelompokan akan datang vs lampau, tidak ada hitung mundur, tidak ada lokasi/pengingat,
  dan kategori hanya 4 (`date`, `gift`, `milestone`, `dream`) tanpa ikon.

**Perubahan:**
1. **Migrasi SQLite (`database.py` `init_db()` via `_safe_alter`) — tabel `relationship_events`:**

| Kolom baru | Tipe | Fungsi |
|---|---|---|
| `icon` | TEXT DEFAULT '' | Emoji/ikon acara (🎂 🎉 💍 …) |
| `location` | TEXT DEFAULT '' | Tempat acara |
| `notes` | *(sudah ada)* | Catatan panjang (kini benar-benar bisa diisi) |
| `is_special` | INTEGER DEFAULT 0 | Tandai sebagai **Special Day** |
| `recurring` | TEXT DEFAULT 'none' | `none` / `yearly` (ulang tiap tahun) |
| `remind_days_before` | INTEGER DEFAULT 0 | 0 = tanpa pengingat; 1/3/7/14/30 hari sebelumnya |
| `updated_at` | TEXT DEFAULT '' | Jejak audit |

2. **Fungsi DB baru:** `add_relationship_event(...)` diperluas (kolom baru) ·
   **`update_relationship_event(event_id, user_id, **fields)`** · **`get_relationship_events(user_id, include_past=True)`** ·
   **`upcoming_relationship_events(user_id, days=90)`** (menghitung tanggal tahun berjalan untuk `recurring='yearly'`,
   termasuk ulang tahun & anniversary dari `relationship_profiles.start_date`).
3. **API baru:** `POST /api/love/events/<id>/update` · `GET /api/love/events/upcoming?days=90`
   (dipanggil `_love_map` agar ikut snapshot `loveSpace`, aman offline).
4. **UI — komponen baru `components/love/LoveEventDialog.tsx`** (dipakai untuk Tambah & Edit):
   judul · tanggal · kategori (dengan ikon) · **lokasi** · **catatan (textarea 4 baris)**
   · toggle **Special Day** → muncul opsi **Ulangi setiap tahun** + **Ingatkan H hari sebelumnya**
   · validasi (judul & tanggal wajib) · pratinjau hitung mundur ("dalam 12 hari").
5. **UI — kartu tab `plans` dirombak:** daftar **Events** dikelompokkan **Akan datang** (urut naik, dengan
   badge `H-12`) dan **Sudah lewat** (kolaps default), pencarian, filter kategori, tombol
   `✏️ Edit` + `🗑 Hapus`, ikon special day ⭐, tampilan notes maks 2 baris (klik untuk buka dialog).
   **Bucket List** ikut memakai pola kartu yang sama (isi lengkap di A10).
6. **Sinkronisasi cloud:** payload event dikirim lengkap; **field baru diabaikan server lama** (RPC whitelist
   — lihat Format 6), jadi tidak ada error; bila migrasi Supabase diterapkan, special days ikut tersinkron.

**Format 1 — i18n key baru (id / en) — ±18 key:**

| Key | id | en |
|---|---|---|
| `love_event_add_title` | `Tambah acara` | `Add event` |
| `love_event_edit_title` | `Edit acara` | `Edit event` |
| `love_event_notes` | `Catatan` | `Notes` |
| `love_event_notes_ph` | `Detail acara, rencana, hadiah, atau hal yang perlu disiapkan…` | `Event details, plans, gifts, or what to prepare…` |
| `love_event_location` | `Lokasi` | `Location` |
| `love_event_icon` | `Ikon` | `Icon` |
| `love_event_special` | `Special Day` | `Special Day` |
| `love_event_special_hint` | `Tandai sebagai hari istimewa (ulang tahun, anniversary).` | `Mark as a special day (birthday, anniversary).` |
| `love_event_recurring` | `Ulangi setiap tahun` | `Repeat every year` |
| `love_event_remind_before` | `Ingatkan sebelumnya` | `Remind me` |
| `love_event_remind_none` | `Tanpa pengingat` | `No reminder` |
| `love_event_remind_days` | `{n} hari sebelum` | `{n} days before` |
| `love_event_upcoming` | `Akan datang` | `Upcoming` |
| `love_event_past` | `Sudah lewat` | `Past` |
| `love_event_in_days` | `{n} hari lagi` | `in {n} days` |
| `love_event_today` | `Hari ini!` | `Today!` |
| `love_event_years_ago` | `{n} tahun lalu` | `{n} years ago` |
| `love_event_updated` | `Acara diperbarui` | `Event updated` |

**Format 2 — File ditimpa:** `database.py` · `studio_api.py` · `web/src/components/views/LoveSpaceView.tsx` ·
`web/src/context/GameContext.tsx` (tambah `updateLoveEvent`) · `web/src/api/studio.ts` ·
`supabase/migrations/…` (opsional, lihat Format 6)
**Format 3 — File baru:** `web/src/components/love/LoveEventDialog.tsx`
**Format 4 — Command baru:**
```
POST /api/love/events/<id>/update        {"title","date","category","icon","location","notes",
                                          "isSpecial","recurring","remindDaysBefore"}
GET  /api/love/events/upcoming?days=90
```
**Format 5 — Kesimpulan fase:** Hole paling jelas di Love Space ditutup: field catatan event yang selama ini mustahil diisi kini berfungsi, event bisa diedit (bukan hanya dihapus), dan lahir konsep **Special Day** dengan pengulangan tahunan + hitung mundur + pengaturan pengingat — membuat tab `plans` terasa seperti fitur matang, bukan formulir setengah jadi.
**Format 6 — Migrasi:**
- **SQLite (wajib, otomatis):** 6 kolom baru `relationship_events` via `_safe_alter` di `init_db()` — ✅ **terpasang & diuji** (37/37, idempoten).
- **Supabase (opsional, hanya untuk user cloud):** migrasi baru
  `supabase/migrations/2026xxxxxxxxxx_phase_a_love_special_days.sql` — `ALTER TABLE public.love_space_events
  ADD COLUMN icon/location/is_special/recurring/remind_days_before/updated_at` + `CREATE OR REPLACE FUNCTION
  public.upsert_love_space_record(...)` yang memasukkan field baru. **Tanpa migrasi ini aplikasi tetap
  normal** (field baru hanya lokal, payload cloud lama tetap valid) — tidak ada regresi.
**Verifikasi:** tambah event + notes → buka ulang (notes tersimpan) · edit judul/tanggal · jadikan Special Day
ulang tahun tanggal yang sudah lewat → muncul di "Akan datang" tahun ini · hapus · `py_compile` ·
`tsc --noEmit`.

---

## A10 — Memories & Bucket List: dari daftar sederhana menjadi fitur matang ✅ *(selesai 2026-09-16)*

**Item user #3b:** *"audit semua fitur sub-tab, lakukan perubahan untuk lebih memprofesionalkan fungsinya."*

**Akar masalah (TERBUKTI):**
- **Memories** (`LoveSpaceView.tsx` **L835–858**): hanya daftar + modal tambah (judul/tanggal/deskripsi)
  + hapus; **tidak ada edit**, tidak ada pencarian/filter, tidak ada tanda favorit, tidak bisa
  menautkan foto (padahal album & galeri sudah ada), emoji selalu hardcoded `'💖'` (**L1112**).
- **Bucket List** (**L1063–1090**): hanya judul + checkbox + hapus; **tidak ada target tanggal, kategori,
  catatan, maupun progres**; tidak ada jalur dari item selesai → kenangan (padahal alurnya natural).
- Tabel `relationship_memories` & `relationship_bucket_items` sudah ada tetapi miskin kolom
  (`database.py` **L1406+**).

**Perubahan:**
1. **Migrasi SQLite:**
   - `relationship_memories`: `+emoji TEXT DEFAULT ''`, `+tags TEXT DEFAULT ''`,
     `+is_favorite INTEGER DEFAULT 0`, `+photo_id INTEGER`, `+updated_at TEXT DEFAULT ''`.
   - `relationship_bucket_items`: `+target_date TEXT DEFAULT ''`, `+category TEXT DEFAULT 'dream'`,
     `+notes TEXT DEFAULT ''`, `+priority INTEGER DEFAULT 0`, `+updated_at TEXT DEFAULT ''`.
2. **Fungsi DB baru:** `update_relationship_memory(...)` · `toggle_memory_favorite(...)` ·
   `update_relationship_bucket_item(...)` · `get_relationship_bucket_stats(user_id)`
   (jumlah total/selesai/terlambat target).
3. **API baru:** `POST /api/love/memories/<id>/update` · `POST /api/love/memories/<id>/favorite` ·
   `POST /api/love/bucket/<id>/update` · `POST /api/love/bucket/<id>/promote-to-memory` (item selesai →
   kenangan otomatis dengan tanggal pencapaian + catatan).
4. **UI — sub-tab `memories`:** toolbar (pencarian, filter tahun, filter tag, toggle "hanya favorit",
   urutan Terbaru/Terlama), kartu kenangan bergaya timeline dengan **emoji bisa dipilih**, badge tag,
   bintang favorit, thumbnail foto (bila `photo_id`), aksi **Edit** (dialog baru
   `components/love/LoveMemoryDialog.tsx`), tautkan foto dari galeri, hapus.
5. **UI — Bucket List:** kartu dengan **progres bar** (total vs selesai %), kategori berikon, target tanggal
   (+badge `⏰ terlewat` / `H-30`), catatan, prioritas (⭐), filter (Semua/Belum/Selesai/Terlewat),
   aksi edit (dialog `components/love/LoveBucketDialog.tsx`), dan tombol **Simpan jadi kenangan** saat
   item ditandai selesai (opsional, satu klik).

**Format 1 — i18n key baru (id / en) — ±24 key:**

| Key | id | en |
|---|---|---|
| `love_memory_edit_title` | `Edit kenangan` | `Edit memory` |
| `love_memory_emoji` | `Emoji kenangan` | `Memory emoji` |
| `love_memory_tags` | `Tag` | `Tags` |
| `love_memory_tags_ph` | `mis. liburan, pertama kali, keluarga` | `e.g. vacation, first time, family` |
| `love_memory_favorite` | `Tandai favorit` | `Mark as favorite` |
| `love_memory_only_fav` | `Hanya favorit` | `Favorites only` |
| `love_memory_link_photo` | `Tautkan foto` | `Link a photo` |
| `love_memory_filter_year` | `Tahun` | `Year` |
| `love_memory_updated` | `Kenangan diperbarui` | `Memory updated` |
| `love_bucket_progress` | `{done} dari {total} tercapai` | `{done} of {total} achieved` |
| `love_bucket_target_date` | `Target tanggal` | `Target date` |
| `love_bucket_category` | `Kategori` | `Category` |
| `love_bucket_notes` | `Catatan` | `Notes` |
| `love_bucket_priority` | `Prioritas` | `Priority` |
| `love_bucket_overdue` | `Lewat target` | `Overdue` |
| `love_bucket_filter_all` | `Semua` | `All` |
| `love_bucket_filter_open` | `Belum` | `Open` |
| `love_bucket_filter_done` | `Selesai` | `Done` |
| `love_bucket_filter_late` | `Terlewat` | `Overdue` |
| `love_bucket_promote` | `Simpan jadi kenangan` | `Save as memory` |
| `love_bucket_promoted` | `Ditambahkan ke kenangan` | `Added to memories` |
| `love_bucket_edit_title` | `Edit item bucket list` | `Edit bucket list item` |
| `love_category_travel` | `Perjalanan` | `Travel` |
| `love_category_gift` | `Hadiah` | `Gift` |

**Format 2 — File ditimpa:** `database.py` · `studio_api.py` · `web/src/components/views/LoveSpaceView.tsx` ·
`web/src/context/GameContext.tsx` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/love/LoveMemoryDialog.tsx` ·
`web/src/components/love/LoveBucketDialog.tsx`
**Format 4 — Command baru:**
```
POST /api/love/memories/<id>/update          POST /api/love/memories/<id>/favorite
POST /api/love/bucket/<id>/update            POST /api/love/bucket/<id>/promote-to-memory
```
**Format 5 — Kesimpulan fase:** `memories` dan `bucket list` naik kelas: keduanya bisa diedit, diberi tag/emosi/kategori/target, difilter & dicari, serta saling terhubung (item bucket selesai → kenangan). Bucket list punya indikator progres nyata sehingga terasa seperti rencana bersama, bukan daftar centang.
**Format 6 — Migrasi:** SQLite: 9 kolom baru (2 tabel) + 2 indeks — auto-apply. Supabase opsional: **berkas
sendiri** `supabase/migrations/20260916010000_phase_a10_love_memories_bucket.sql` (kolom
`love_space_memories(emoji,tags,is_favorite,updated_at)` & `love_space_bucket_items(notes,priority,updated_at)`, check prioritas 0–3, 2 indeks, + `upsert_love_space_record` yang memetakan field baru; tanpa ini field baru
tetap tersimpan lokal tanpa error). `photo_id` & `promoted_memory_id` sengaja tidak dikirim ke cloud.
**Verifikasi:** tambah 3 kenangan → tagi, favoritkan, tautkan foto, filter tahun → hasil benar · tambah bucket
dengan target tanggal lewat → badge terlewat · selesaikan item → "Simpan jadi kenangan" berfungsi.

---

## A11 — `connection` · `cycle` · `gallery`: audit & polish profesional

**Akar masalah (TERBUKTI, hasil audit sub-tab):**
- **Connection** (**L635–758**): prompt muncul acak tanpa riwayat/filter/kategori yang bisa ditelusuri;
  favorit tersimpan (`promptFavorites`) tapi tidak ada tampilan khusus; check-in mood tersimpan
  (`love_space_checkins`) **tanpa visualisasi tren**; tidak ada streak/momen konsistensi.
- **Cycle** (**L760–833**): pengaturan + prediksi ada, tapi riwayat siklus hanya bisa dihapus,
  **tidak bisa diedit**, tidak ada catatan per siklus, dan tidak ada garis waktu siklus sebelumnya.
- **Gallery** (**L860–1013**): album bisa dibuat/diubah/dihapus, tapi tidak ada **cover album**, tidak ada
  jumlah foto per album, tidak ada aksi massal (pilih beberapa → pindah album), lightbox tanpa navigasi
  keyboard, metadata hanya bisa diubah satu per satu lewat blur.

**Perubahan:**
1. **Connection:**
   - Panel **Riwayat jawaban** (dari `promptResponses`) dengan filter kategori + pencarian + tandai favorit;
   - Panel **Favorit** (daftar prompt yang mudah diulang kapan saja) dengan tombol "Tanya pasangan";
   - **Grafik tren mood** (pakai `web/src/components/charts.tsx` yang sudah ada) — mood kamu vs pasangan
     30/90 hari + `connectionScore` mingguan;
   - **Streak check-in** ("7 hari berturut-turut") + badge konsistensi; empty state yang mengarahkan.
2. **Cycle:**
   - Tabel **riwayat siklus** (mulai, akhir, panjang hari, catatan) dengan **edit** + hapus + tambah manual;
   - Kolom **notes** per siklus; prediksi menampilkan "siklus berikutnya · perkiraan ovulasi · jendela subur"
     dengan rentang tanggal + toleransi keyakinan (berdasarkan 3 siklus terakhir);
   - Tombol **Jadikan pengingat** (membuat reminder H-3 dari prediksi — memanfaatkan integrasi A12).
3. **Gallery:**
   - **Cover album** (foto pertama / dipilih user), jumlah foto, dan tanggal album;
   - **Aksi massal:** mode pilih → pindah/hapus/atur visibilitas beberapa foto sekaligus;
   - Lightbox: navigasi ← →, `Esc`, zoom 1×/2×, tombol simpan ke album saat melihat;
   - Metadata (caption/tanggal/visibilitas) bisa disimpan eksplisit dengan tombol **Simpan** (bukan hanya blur).

**Format 1 — i18n key baru (id / en) — ±22 key:**

| Key | id | en |
|---|---|---|
| `love_conn_history` | `Riwayat jawaban` | `Answer history` |
| `love_conn_favorites` | `Prompt favorit` | `Favorite prompts` |
| `love_conn_search_ph` | `Cari prompt…` | `Search prompts…` |
| `love_conn_ask_partner` | `Tanya pasangan` | `Ask your partner` |
| `love_conn_mood_trend` | `Tren mood 30 hari` | `30-day mood trend` |
| `love_conn_streak` | `{n} hari berturut-turut` | `{n}-day streak` |
| `love_conn_my_mood` | `Mood kamu` | `Your mood` |
| `love_conn_partner_mood` | `Mood pasangan` | `Partner's mood` |
| `love_conn_empty_history` | `Belum ada jawaban tersimpan. Mulai dari satu prompt.` | `No saved answers yet. Start with one prompt.` |
| `love_cycle_history` | `Riwayat siklus` | `Cycle history` |
| `love_cycle_edit_title` | `Edit siklus` | `Edit cycle` |
| `love_cycle_notes` | `Catatan siklus` | `Cycle notes` |
| `love_cycle_next` | `Perkiraan siklus berikutnya` | `Next cycle estimate` |
| `love_cycle_fertile` | `Jendela subur` | `Fertile window` |
| `love_cycle_confidence` | `Keyakinan prediksi: {level}` | `Prediction confidence: {level}` |
| `love_cycle_add_reminder` | `Jadikan pengingat` | `Create reminder` |
| `love_gallery_album_cover` | `Jadikan cover album` | `Set as album cover` |
| `love_gallery_album_count` | `{n} foto` | `{n} photos` |
| `love_gallery_select_mode` | `Pilih beberapa` | `Select multiple` |
| `love_gallery_bulk_move` | `Pindahkan ke album` | `Move to album` |
| `love_gallery_bulk_delete` | `Hapus terpilih` | `Delete selected` |
| `love_gallery_save_meta` | `Simpan keterangan` | `Save details` |
| `love_conn_avg_*` · `love_cycle_*` · `love_gallery_*` (lanjutan) | lihat lampiran D | — |

**Format 2 — File ditimpa:** `database.py` · `studio_api.py` · `web/src/components/views/LoveSpaceView.tsx`
(dipecah ke `components/love/*`) · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/love/LoveConnectionPanel.tsx` ·
`web/src/components/love/LoveCyclePanel.tsx` · `web/src/components/love/LoveGalleryPanel.tsx`
**Format 4 — Command baru:** `POST /api/love/cycles/<id>/update` · `POST /api/love/albums/<id>/cover` ·
`POST /api/love/photos/bulk` (`{action:"move"|"delete"|"visibility", ids[], albumId?, visibility?}`)
**Format 5 — Kesimpulan fase:** Tiga sub-tab yang sebelumnya "ada tapi datar" kini punya kedalaman fungsional: connection punya riwayat/favorit/tren/streak, cycle punya riwayat yang bisa diedit + prediksi ber-keyakinan + jalur ke pengingat, gallery punya cover, aksi massal, dan lightbox bernavigasi keyboard.
**Format 6 — Migrasi:** SQLite: `relationship_cycles.notes`/`updated_at`; `love_albums.cover_photo_id`.
Supabase opsional: kolom yang sama pada `love_space_cycles` + RPC `upsert_love_space_record` (record_type `cycle`).
**Verifikasi:** 4 sub-tab diuji satu per satu dengan data nyata · tren mood render tanpa data (empty state) · aksi massal galeri hanya memengaruhi foto milik user (`myPhotosOwn` yang ada).

### 📌 REALISASI A11 (2026-09-16) — apa yang benar-benar dikirim

| Rencana di atas | Realisasi | Catatan |
|---|---|---|
| Panel **Riwayat jawaban** + filter kategori + pencarian + favorit | ✅ `LoveConnectionPanel.tsx` — pencarian teks (jawaban sendiri, jawaban pasangan, teks prompt), dropdown kategori **berhitungan**, tombol **Hanya favorit**, ⭐ per baris, **Jawab ulang** (isi ulang prompt ke form), 🗑️ hapus, hitungan “n dari m” | tabel `relationship_prompt_responses` lama dipakai apa adanya; `filterResponses`/`historyCategories` di `connectionUtils.ts` diuji unit |
| Panel **Favorit** + tombol “Tanya pasangan” | ✅ chip prompt favorit (klik = langsung dipakai) + tombol **“Pakai prompt ini”**/**Tanya pasangan** yang menyalin prompt ke clipboard dengan toast | `promptByKey`, `favoritePrompts`; bank prompt 20 butir/5 kategori dipindah ke `connectionUtils.ts` (dulu di dalam view) |
| **Grafik tren mood** 30/90 hari + skor koneksi | ✅ `DualLineChart` (mood kamu vs pasangan) + `LineChart` (skor koneksi 1–5) dari `web/src/components/charts.tsx` yang sudah ada; pemilih rentang **30/90 hari**; **empty state** jelas bila belum ada check-in | data dari `love_space_checkins`; `buildMoodSeries` hanya memakai hari yang benar-benar ada check-in (garis tidak “drop ke nol” palsu) |
| **Streak check-in** + badge konsistensi | ✅ kartu statistik: streak `🔥 {n} hari` (tetap dihitung bila check-in terakhir kemarin), total check-in, rata-rata mood kamu, mood pasangan, skor koneksi | `checkinStats` |
| Riwayat siklus + **edit** + hapus + tambah manual + catatan | ✅ tabel `Mulai · Selesai · Panjang · Catatan · Aksi` dengan **form edit inline** dan **form tambah manual** (`data-testid="love-cycle-add-form"`), panjang hari inklusif, siklus berjalan tampil **“Berjalan”** | `update_menstrual_cycle` (baru) + `POST /api/love/cycles/<id>/update`; `delete` & `add` lama tetap dipakai |
| Prediksi + ovulasi + jendela subur + keyakinan | ✅ kartu prediksi: rentang tanggal, hari ke-, **perkiraan ovulasi**, **jendela subur** (rentang), **badge keyakinan** (Rendah < 2 siklus / Sedang 2–3 dengan sebaran ≤ 7 / Tinggi ≥ 3 dengan sebaran ≤ 3) + baris **dasar prediksi** (`n siklus · sebaran m hari`) | server **tidak** diperluas: `get_menstrual_prediction` tetap seperti semula; ovulasi & jendela subur dihitung di klien (`cycleUtils.ts`) supaya tidak ada dua sumber kebenaran |
| Tombol **“Jadikan pengingat”** | ✅ dua tombol **H-3** dan **H-1**; endpoint baru `POST /api/love/cycles/create-reminder` (daysBefore di-clamp 0–30, jam **09:00**, `repeat_type="none"`, **idempoten** judul+tanggal) | memakai jalur reminder yang sudah ada (`db.add_reminder`) sehingga muncul di menu Reminder; `reminderId` diperbaiki (`reminder_id` vs `id`) |
| **Cover album** + jumlah foto + tanggal | ✅ kolom `love_albums.cover_photo_id` + endpoint `POST /api/love/albums/<id>/cover` (foto otomatis dimasukkan ke album bila belum anggota, `added` dikembalikan) + tombol ⭐ di lightbox; chip album menampilkan **nama · n foto · tanggal · ⭐** | sampul menunjuk foto terhapus otomatis dikosongkan di dua lapis (server & `albumSummary`) |
| **Aksi massal** pindah album/hapus/visibilitas | ✅ mode pilih (hanya **foto milik sendiri** yang bisa dicentang), tombol **Pindahkan ke album** (pilih album → `move`), hapus, dan visibilitas; semua lewat **satu** endpoint `POST /api/love/photos/bulk` | `myPhotosOwn` dipertahankan sebagai nama lama, kini berbasis `isOwnPhoto` di `galleryUtils.ts` |
| Lightbox: ← → · `Esc` · zoom · simpan ke album | ✅ tombol ‹ › + navigasi **keyboard** (← → / ↑ ↓ / spasi), `Esc` menutup, `+`/`-` zoom 1×↔2× (juga tombol di UI), tombol **Simpan ke album** + **Jadikan cover** saat melihat | `galleryParts.tsx` (`ZoomableViewer` menerima `zoomSignal`) — helper ini dulu tinggal di dalam view dan dipakai bersama dialog profil/unggah |
| Metadata dengan tombol **Simpan** | ✅ panel keterangan di lightbox punya tombol **Simpan keterangan** (bukan hanya `blur`) + tanggal & visibilitas | `love-gallery-save-meta` |
| — (temuan tambahan saat uji) | ✅ **bug sync cloud penghapusan massal**: `cloud_id` dibaca **sebelum** baris dihapus (dulu setelah hapus → `get_love_space_photo_raw` mengembalikan `None`, antrean sync tidak pernah terisi; foto tetap tertinggal di Supabase + storage). Kini hanya foto milik user yang di-enqueue | diuji eksplisit: 2 foto → 2 enqueue dengan `cloud_photo_id` benar; foto pasangan → `failed` & tanpa enqueue; tanpa cloud link → tanpa enqueue |
| — (temuan tambahan saat uji) | ✅ **`reminderId` selalu kosong** pada respons create-reminder (fungsi DB mengembalikan key `reminder_id`) | kini `reminder_id` → fallback `id` |
| — (temuan tambahan saat uji) | ✅ **badge keyakinan muncul tanpa prediksi** (menampilkan “Rendah · 0 siklus”) | badge kini hanya dirender bila ada prediksi |
| — (temuan tambahan saat uji) | ✅ nilai id `love_weekly_review` masih berbahasa Inggris di locale Indonesia | diubah menjadi **“Review Mingguan Hubungan”** |
| Format 1 (i18n ± 22 key) | ✅ **78 key baru** — blok A11 di `translations.py` memuat **82 entri** (`love_conn_*` · `love_cycle_*` · `love_gallery_*` · `love_album_*` · `love_actions`); 4 entri memakai key yang sudah ada (`love_cycle_history`, `love_album_copy_to`, `love_album_move_to`, `love_album_remove`) | total i18n **4.166 → 4.244** (+78) |
| Format 2 (file ditimpa) | ✅ `database.py` · `studio_api.py` · `translations.py` · `api_server.py` (`WEB_I18N_KEYS`) · `web/src/api/studio.ts` · `web/src/context/GameContext.tsx` · `web/src/components/views/LoveSpaceView.tsx` · `web/src/i18n/messages.json` + `web/public/i18n/messages.json` | `LoveSpaceView.tsx` **2.200 → 1.635 baris** |
| Format 3 (file baru) | ✅ 7 berkas: `connectionUtils.ts` · `cycleUtils.ts` · `galleryUtils.ts` · `galleryParts.tsx` · `LoveConnectionPanel.tsx` · `LoveCyclePanel.tsx` · `LoveGalleryPanel.tsx` | semua util murni (tanpa DOM) supaya bisa diuji tanpa browser |
| Format 4 (command baru) | ✅ `POST /api/love/cycles/<id>/update` · `POST /api/love/cycles/create-reminder` · `POST /api/love/albums/<id>/cover` · `POST /api/love/photos/bulk` | bulk adalah **satu** panggilan untuk tiga aksi (dulu klien memanggil per foto → rawan setengah jalan) |
| Format 6 (migrasi) — **KOREKSI** | ✅ SQLite: **`menstrual_cycles.updated_at`** (bukan `relationship_cycles` seperti tertulis di rencana — tabel siklus nyata bernama `menstrual_cycles`, kolom `notes` sudah ada) + `love_albums.cover_photo_id` + indeks `idx_menstrual_cycles_user_start` / `idx_love_albums_user_cover`. Supabase: **tidak ada perubahan skema yang diperlukan** (`love_space_cycles` sudah punya `updated_at`+trigger+indeks, RPC `upsert_love_space_record` cabang `cycle` sudah ada sejak A10; album memang lokal) — disediakan `20260916020000_phase_a11_love_cycle_gallery_alignment.sql` yang **idempoten** sebagai jaring pengaman + dokumentasi pemetaan | lihat berkas migrasi untuk catatan “sengaja tidak di cloud” |

**Hasil uji:** DB **49/49** ✅ · API in-process **44/44** ✅ · regresi API **35/35** ✅ ·
FE unit **93/93** ✅ · FE SSR tab **59/59** ✅ · FE view **18/18** ✅ · `tsc --noEmit` 0 error ✅ ·
`vite build` clean ✅ · i18n **4.166 → 4.244** ✅ · server `:8899` hidup dengan aset baru ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-16-A11-love-connection-cycle-gallery.md`](2026-09-16-A11-love-connection-cycle-gallery.md).


---

## A12 — `overview` diprofesionalkan + Special Day → Reminder (repeat **yearly**) ✅ *SELESAI 2026-09-16*

**Akar masalah (TERBUKTI):**
- `overview` (**L566–633**) hanya menampilkan ringkasan ringan; `connectionScore`, `startDate`, dan
  `cyclePrediction` sudah tersedia di payload `loveSpace` (**studio_api `_love_map` L141+**) tapi
  **belum divisualisasikan**; tidak ada kartu "hari ke-N bersama", tidak ada hitung mundur hari istimewa
  (karena special day belum ada — lihat A09).
- **Reminder engine tidak punya opsi tahunan:** `database.py` **L11092** `get_next_reminder_datetime`
  hanya mendukung `none/daily/weekly/custom`, dan `RemindersView.tsx` **L289–294** menyediakan 4 opsi itu
  saja → **tidak mungkin** membuat pengingat ulang tahun/anniversary tahunan.

**Perubahan:**
1. **Reminder engine (`database.py`):**
   - Tambah `repeat_type='yearly'` pada `get_next_reminder_datetime` (menambah 1 tahun, menangani 29 Feb)
     dan pada validasi `update_reminder`; kolom `repeat_until` yang sudah ada tetap dihormati.
   - Fungsi baru `create_reminder_from_special_day(user_id, event_id, days_before)` → membuat reminder
     pada tanggal `event − H` dengan `repeat_type='yearly'`.
2. **API:** `POST /api/love/events/<id>/create-reminder` (dipakai dari A09/A12) — idempoten: bila reminder
   untuk event itu sudah ada, perbarui bukan duplikasi.
3. **UI Reminders:** opsi **`Tahunan`** pada dropdown repeat (`RemindersView.tsx`) + label i18n; daftar
   reminder menampilkan badge "Tahunan · tiap {tanggal}".
4. **UI `overview` dirombak** menjadi dashboard pasangan yang informatif:
   - **Hero couple card:** nama kamu & pasangan, tipe hubungan, **"bersama selama N hari / M tahun"**
     (dari `startDate`), avatar/inisial, badge status couple (data sudah ada: `coupleActive`, `couplePartner`);
   - **Kartu hari istimewa berikutnya** (dari `upcoming_relationship_events`) dengan hitung mundur & tombol
     **Buat pengingat**;
   - **Connection score** sebagai cincin progres + rincian komponen (check-in terakhir, streak, mood rata-rata);
   - **Statistik grid:** total kenangan, bucket tercapai, foto, prompt terjawab, check-in bulan ini;
   - **Aksi cepat:** check-in hari ini, tambah kenangan, tambah acara, buka pengingat;
   - **Empty state** ramah untuk pasangan yang baru mulai (mengarahkan isi tanggal jadian).
5. **Dashboard (Home) opsional-ringan:** chip "Hari istimewa terdekat" memakai data yang sama — cukup satu
   baris, tidak mengubah tata letak Home.

**Format 1 — i18n key baru (id / en) — ±20 key:**

| Key | id | en |
|---|---|---|
| `love_together_days` | `Bersama selama {days} hari` | `Together for {days} days` |
| `love_together_years` | `{years} tahun {days} hari` | `{years} years {days} days` |
| `love_next_special` | `Hari istimewa berikutnya` | `Next special day` |
| `love_create_reminder` | `Buat pengingat` | `Create reminder` |
| `love_reminder_created` | `Pengingat dibuat` | `Reminder created` |
| `love_reminder_exists` | `Pengingat untuk acara ini sudah ada` | `A reminder for this event already exists` |
| `love_conn_score` | `Skor kedekatan` | `Connection score` |
| `love_stat_memories` | `Kenangan` | `Memories` |
| `love_stat_bucket_done` | `Bucket tercapai` | `Bucket achieved` |
| `love_stat_photos` | `Foto` | `Photos` |
| `love_stat_prompts` | `Prompt terjawab` | `Prompts answered` |
| `love_stat_checkins_month` | `Check-in bulan ini` | `Check-ins this month` |
| `love_quick_checkin` | `Check-in hari ini` | `Check in today` |
| `love_quick_memory` | `Tambah kenangan` | `Add memory` |
| `love_quick_event` | `Tambah acara` | `Add event` |
| `love_empty_cta` | `Isi tanggal jadian untuk membuka hitungan hari bersama.` | `Set your anniversary date to unlock the days-together counter.` |
| `reminders_repeat_yearly` | `Tahunan` | `Yearly` |
| `reminders_badge_yearly` | `Tahunan · tiap {date}` | `Yearly · every {date}` |
| `dash_next_special` | `Hari istimewa: {title} ({days} hari lagi)` | `Special day: {title} (in {days} days)` |
| `love_cycle_reminder_created` | `Pengingat siklus dibuat` | `Cycle reminder created` |

**Format 2 — File ditimpa:** `database.py` · `studio_api.py` · `web/src/components/views/LoveSpaceView.tsx` ·
`web/src/components/views/RemindersView.tsx` · `web/src/components/views/DashboardView.tsx` ·
`web/src/context/GameContext.tsx` · `web/src/api/studio.ts`
**Format 3 — File baru:** `web/src/components/love/LoveOverviewPanel.tsx` ·
`web/src/components/love/ConnectionScoreRing.tsx`
**Format 4 — Command baru:** `POST /api/love/events/<id>/create-reminder` ·
repeat type `yearly` pada `/api/reminders` (payload `{repeat:'yearly'}`).
**Format 5 — Kesimpulan fase:** `overview` berubah dari ringkasan datar menjadi dashboard pasangan (hitungan hari bersama, hari istimewa terdekat, skor kedekatan, statistik, aksi cepat), dan Love Space akhirnya bisa **mengirim pengingat tahunan** untuk hari istimewa lewat sistem Reminder yang sudah ada — fitur yang sebelumnya mustahil dibuat karena engine-nya belum mengenal pengulangan tahunan.
**Format 6 — Migrasi:** SQLite: perluasan dukungan `repeat_type` + kolom **`reminders.repeat_until`**
(**KOREKSI 2026-09-16:** rencana awal menyebut kolom ini "sudah tersedia lewat `_safe_alter`" — **salah**;
kolomnya belum pernah dibuat sehingga setiap penulisan `repeat_until` selama ini gagal `no such column`.
A12 membuatnya + `reminders.source_ref` + indeks; lihat Realisasi di bawah). Supabase: — (tidak ada;
pengingat disimpan lokal, termasuk dalam cakupan migrasi opsional A09).
**Verifikasi:** buat special day (ulang tahun pasangan) → buat pengingat → cek muncul di Reminders dengan
badge Tahunan + tanggal H-{n} yang benar · uji 29 Februari · cek overview menghitung "bersama N hari" dengan
`startDate` yang ada.

---

### 📌 REALISASI A12 (2026-09-16) — apa yang benar-benar dikirim

**Format 1 — Key i18n baru: 64** (blok A12 di `translations.py`, ikut `WEB_I18N_KEYS`; total **4.244 → 4.308**)

| Grup | Jumlah | Key |
|---|---|---|
| Hero pasangan | 9 | `love_together_days` · `love_together_years` · `love_hero_title` · `love_hero_since` · `love_hero_no_date` · `love_empty_cta` · `love_rel_dating` · `love_rel_engaged` · `love_rel_married` |
| Hari istimewa | 18 | `love_overview_sub` · `love_next_special` · `love_special_none` · `love_special_today` · `love_special_tomorrow` · `love_in_days` · `love_years_count` · `love_create_reminder` · `love_reminder_created` · `love_reminder_created_detail` · `love_reminder_exists` · `love_reminder_no_date` · `love_reminder_bad_event` · `love_reminder_from_love` · `love_reminder_anniversary` · `love_reminder_birthday` · `love_reminder_repeat_yearly` · `love_reminder_repeat_once` |
| Kartu & aksi | 6 | `love_reminder_hint` · `love_special_remind_days` · `love_special_days_list` · `love_special_source_profile` · `love_open_reminders` · `love_me` |
| Skor & statistik | 16 | `love_score_ring` · `love_score_breakdown` · `love_score_last_checkin` · `love_score_no_checkin` · `love_score_avg_my` · `love_score_avg_partner` · `love_score_short` · `love_stat_title` · `love_stat_memories` · `love_stat_bucket_done` · `love_stat_bucket_of` · `love_stat_photos` · `love_stat_albums` · `love_stat_prompts` · `love_stat_checkins_month` · `love_checkin_today_short` · `love_days_ago` |
| Aksi cepat | 7 | `love_quick_title` · `love_quick_checkin` · `love_quick_checkin_done` · `love_quick_memory` · `love_quick_event` · `love_quick_bucket` · `love_quick_reminders` |
| Reminder tahunan | 5 | `reminders_repeat_yearly` · `reminders_repeat_yearly_hint` · `reminders_badge_yearly` · `reminders_repeat_until_hint` · `reminders_source_love` |
| Beranda | 2 | `dash_next_special` · `dash_next_special_today` |

**Format 2 — File yang ditimpa (12)**

| # | File | Perubahan A12 |
|---|---|---|
| 1 | `database.py` | migrasi `reminders.repeat_until` + `source_ref` + indeks (`_safe_alter`) · **perbaikan urutan indeks `love_albums`** (database baru tidak bisa `init_db()` — warisan A11) · `get_next_reminder_datetime`: cabang **`yearly`** (29 Feb → 28 Feb), `repeat_until` tahan `'YYYY-MM-DD HH:MM:SS'`/nilai rusak, `current_dt_str` tidak valid → `None` (dulu `ValueError`) · fungsi baru `create_reminder_from_special_day` |
| 2 | `studio_api.py` | endpoint `POST /api/love/events/<id>/create-reminder` (idempoten, id acara **atau** kunci profil) |
| 3 | `life_api.py` | `map_reminder`: **`yearly`** di whitelist + kirim `repeatUntil` & `sourceRef` · `POST /api/reminders` menerima `repeatUntil` · `update` **tidak lagi memaksa** `repeat_type='none'`/`repeat_days=''` saat body tidak mengirimnya (temuan regresi: menghapus pengulangan tahunan diam-diam) · `trigger` meneruskan `repeat_until` ke mesin |
| 4 | `translations.py` | 64 key baru (id + en) |
| 5 | `api_server.py` | `WEB_I18N_KEYS` +64 |
| 6 | `web/src/components/views/LoveSpaceView.tsx` | tab `overview` → `LoveOverviewPanel`; loader `events/upcoming?days=365`; handler `createSpecialReminder` + `quickOverviewAction`; prop `onNavigate`; `miniStat` & 5 state check-in lama dihapus; 1.635 → 1.631 baris |
| 7 | `web/src/components/views/RemindersView.tsx` | opsi **Tahunan** + hint, input **batas akhir pengulangan**, badge pengulangan & penanda 💞 di daftar, `repeatLabel`/`isLoveReminder` (diekspor untuk uji) |
| 8 | `web/src/components/views/DashboardView.tsx` | chip satu baris `dash_next_special` (data `loveSpace`, tanpa API baru) |
| 9 | `web/src/App.tsx` · `web/src/context/GameContext.tsx` · `web/src/api/studio.ts` · `web/src/types.ts` | `onNavigate` untuk Love Space · aksi `loveEventReminder` + tipe payload `yearly`/`repeatUntil` · `studio.loveEventReminder` · `ReminderItem.repeat` memuat `'yearly'` + `repeatUntil`/`sourceRef` |

**Format 3 — File baru (3 kode)**

| File | Isi |
|---|---|
| `web/src/components/love/overviewUtils.ts` | Logika murni (bisa diuji tanpa DOM): `daysTogether`, `durationParts/durationText`, `countdownBadge`, `specialIcon`, `nextSpecialDay`, `nextSpecialFromProfile` (+urusan 29 Feb), `overviewStats`, `scoreBreakdown`, `lastCheckinText`, `nextAgenda`, `quickActions`, `relationshipLabel`, `isProfileSpecial` |
| `web/src/components/love/ConnectionScoreRing.tsx` | Cincin skor (memakai `ProgressRing` dari `charts.tsx`) + 4 baris rincian (check-in terakhir · streak · rata mood kamu · rata mood pasangan) |
| `web/src/components/love/LoveOverviewPanel.tsx` | Seluruh tab `overview`: hero hari bersama, kartu hari istimewa + tombol **Buat pengingat**, agenda terdekat, cincin skor, grid 6 statistik, 5 aksi cepat, form & riwayat check-in (parity lama) |

**Format 4 — Perintah / endpoint baru:** `POST /api/love/events/<id>/create-reminder` (body opsional `{daysBefore, time}`; balasan `{ok, already, updated, reminder_id, reminder_date, days_before, repeat_type, title, category, next_date, source_ref}`) · payload `{repeat:"yearly", repeatUntil:"YYYY-MM-DD"}` pada `POST /api/reminders` & `/api/reminders/<id>/update`.

**Format 6 — Migrasi (auto, SQLite):** `reminders.repeat_until` (TEXT) · `reminders.source_ref` (TEXT DEFAULT '') · indeks `idx_reminders_source_ref` · perbaikan urutan pembuatan indeks `idx_love_albums_user_cover`. **Supabase: tidak ada perubahan skema** — pengingat pada cloud memakai `public.reminders` yang sudah memuat `repeat_type`; kolom `repeat_until`/`source_ref` murni lokal (pengingat pengguna cloud tetap dibuat lokal, sama seperti perilaku A09–A11).

**Hasil uji:** DB **47/47** ✅ · smoke API **35/35** ✅ · regresi A09–A12 **50/50** ✅ (3× berturut) ·
FE unit **65/65** ✅ · FE render/SSR **71/71** ✅ · `tsc --noEmit` 0 error ✅ · `vite build` clean
(**`index-N3fi8Iak.js`** 1.282,39 kB) ✅ · i18n **4.244 → 4.308** ✅ · server `:8899` hidup dengan aset baru ✅ ·
DB lokal bersih (`integrity_check` ok) ✅.
**Format 1–6 dikirim di chat** sesuai ⚠️ ATURAN DELIVERY — laporan berkas:
[`2026-09-16-A12-love-overview-yearly-reminder.md`](2026-09-16-A12-love-overview-yearly-reminder.md).

**Bug yang ikut tertutup (ditemukan oleh uji A12 — semuanya sebelum rilis):**
1. **Database baru gagal `init_db()`** — indeks `idx_love_albums_user_cover` (A11) dijalankan **sebelum** tabel `love_albums` dibuat, dan `_safe_alter` `cover_photo_id` ikut hilang karena tabelnya belum ada → pemasangan baru crash (`no such table: main.love_albums` / `no such column: cover_photo_id`). Kini indeks & kolom dipastikan **setelah** `CREATE TABLE`.
2. **Update reminder menghapus pengulangan** — `POST /api/reminders/<id>/update` selalu menulis `repeat_type='none'` + `repeat_days=''` bila body tidak mengirim `repeat`, sehingga pengingat tahunan berubah menjadi sekali jalan tanpa peringatan. Kini keduanya opsional.
3. **`repeat_until` tak terbaca = pengingat gagal** — `datetime.strptime(repeat_until, "%Y-%m-%d")` melempar `ValueError` untuk nilai `'YYYY-MM-DD HH:MM:SS'` maupun nilai rusak; `reminder_datetime` yang tidak valid juga membuat `get_next_reminder_datetime` crash. Keduanya kini aman (batas diabaikan / baris dilewati).
4. **Kolom `repeat_until` tidak pernah ada** — dirujuk `update_reminder` & `get_next_reminder_datetime` sejak lama, tetapi tabelnya belum punya kolom itu (koreksi roadmap: klaim "sudah tersedia" **salah**; kini dibuat lewat `_safe_alter`).
5. **`nextSpecialFromProfile` memakai tahun tanggal asli** — hari jadi 2020 dihitung di tahun 2021 (chip Beranda bisa menampilkan tanggal lampau). Kini tahun berjalan diambil dari `now`.

---

# 🟡 KLASTER 4 — HOME PAGE (#4)


## A13 — Year Wrapped memakai currency user + i18n + polish

**Item user #4:** *"di fungsi dialog year wrapped, bagian laporan economy (pengeluaran dan pemasukan) masih menggunakan currency IDR secara default, yang harusnya menggunakan currency yang sedang digunakan user."*

**Akar masalah (TERBUKTI):**
- `web/src/components/YearWrappedDialog.tsx` **L31**:
  `const money = (v: number) => \`Rp ${Math.round(Number(v || 0)).toLocaleString()}\`;` → **hardcoded "Rp"**,
  lalu dipakai di **L79** (pemasukan) & **L83** (pengeluaran).
- Ini **melanggar aturan modul** `web/src/utils/currency.ts` yang menuliskan eksplisit:
  *"DB SELALU menyimpan IDR … Semua formatter uang di Web UI WAJIB lewat modul ini — tidak ada lagi 'Rp' hardcoded."*
  (`formatMoney(amountIdr, currency)` menghitung `amountIdr / rate` lalu menambahkan simbol mata uang user.)
- Server mengirim angka mentah IDR (`db.get_year_wrapped` → `income`/`expense`), dan `ensureCurrencyRates()`
  sudah dijalankan di `GameContext` (**L547**) → **tinggal dipakai**.
- Bonus temuan: seluruh teks dialog masih hardcoded bahasa Indonesia (`Belum ada aktivitas…`, `Pemasukan total`,
  `Pengeluaran total`, `tugas diselesaikan`, `hari aktif`, `Hari terbaik`, `sesi fokus`, `Kebiasaan teratas`,
  `streak terpanjang`, `Tutup`) → user `en` tetap melihat teks Indonesia.

**Perubahan:**
1. **Currency:** ganti `money()` → `formatMoney(value, user.currency)` dari `utils/currency.ts`
   (dipanggil dengan `user.currency` dari `useGame()`), tampilkan **chip mata uang aktif** (`IDR` / `USD` / …)
   + catatan kurs kecil ("kurs 1 USD = Rp 17.800") agar transparan.
2. **i18n penuh:** semua string dialog dipindahkan ke `translations.py` (id+en).
3. **Polish isi laporan:**
   - kartu ekonomi ditambah **Selisih bersih** (net = income − expense) dengan warna dinamis + persentase
     tabungan (`(income-expense)/income`);
   - rincian **per tipe tugas** (habits/dailies/quests) memakai `by_type` yang sudah dikirim server;
   - top habits memakai ikon + bar relatif;
   - **pemilih tahun** (`/api/year-wrapped?year=`) — server `api_server.py` meneruskan `year` ke
     `db.get_year_wrapped(user_id, year)`;
   - tombol **Salin ringkasan** (clipboard, teks rapi) + **Unduh .txt**; confetti `canvas-confetti` (sudah
     jadi dependency) saat dibuka — sesuai tema "Wrapped".
4. **Empty-state & error:** bila `!w.total_done && !w.focus_sessions` tetap ada, kini dengan i18n +
   ajakan mengisi tracker; bila API gagal → pesan singkat, bukan dialog kosong.

**Format 1 — i18n key baru (id / en) — ±18 key:**

| Key | id | en |
|---|---|---|
| `wrapped_title` | `CraftLife Wrapped {year}` | `CraftLife Wrapped {year}` |
| `wrapped_tasks_done` | `tugas diselesaikan` | `tasks completed` |
| `wrapped_active_days` | `{n} hari aktif` | `{n} active days` |
| `wrapped_best_day` | `Hari terbaik: {date} ({n} tugas)` | `Best day: {date} ({n} tasks)` |
| `wrapped_focus` | `{sessions} sesi fokus · {minutes} mnt` | `{sessions} focus sessions · {minutes} min` |
| `wrapped_level` | `Lv {level}` | `Lv {level}` |
| `wrapped_streak` | `streak terpanjang {n}` | `longest streak {n}` |
| `wrapped_top_habits` | `Kebiasaan teratas` | `Top habits` |
| `wrapped_income` | `Pemasukan total` | `Total income` |
| `wrapped_expense` | `Pengeluaran total` | `Total expenses` |
| `wrapped_net` | `Selisih bersih` | `Net balance` |
| `wrapped_saving_rate` | `Rasio tabungan {pct}%` | `Saving rate {pct}%` |
| `wrapped_by_type` | `Rincian per tipe` | `Breakdown by type` |
| `wrapped_currency_note` | `Ditampilkan dalam {currency} (kurs 1 {currency} = {rate})` | `Shown in {currency} (rate 1 {currency} = {rate})` |
| `wrapped_pick_year` | `Pilih tahun` | `Pick a year` |
| `wrapped_copy` | `Salin ringkasan` | `Copy summary` |
| `wrapped_download` | `Unduh .txt` | `Download .txt` |
| `wrapped_empty` | `Belum ada aktivitas di tahun ini. Mulai catat task-mu!` | `No activity this year yet. Start tracking your tasks!` |
| `wrapped_copied` | `Ringkasan disalin` | `Summary copied` |

**Format 2 — File ditimpa:** `web/src/components/YearWrappedDialog.tsx` · `web/src/api/rpg.ts` ·
`api_server.py` (teruskan `?year=`) · `web/src/context/GameContext.tsx` (bila perlu expose `currency`)
**Format 3 — File baru:** — (tidak ada)
**Format 4 — Command baru:** `GET /api/year-wrapped?year=2025` (opsional, kompatibel tanpa parameter)
**Format 5 — Kesimpulan fase:** Laporan ekonomi di Year Wrapped kini mengikuti mata uang aktif user (melalui satu-satunya formatter resmi `formatMoney`), seluruh teks dialog tersedia id+en, dan laporan diperkaya (selisih bersih, rasio tabungan, rincian per tipe, pemilih tahun, salin/unduh).
**Format 6 — Migrasi:** — (tidak ada)
**Verifikasi:** ganti currency user ke USD → buka Wrapped → angka & simbol berubah (`$ 1,234`) + catatan kurs · ganti bahasa ke en → seluruh teks Inggris · pilih tahun sebelumnya → data tahun itu tampil.

> **KOREKSI (2026-09-16, saat pelaksanaan):** tabel key di atas adalah **rencana**. Realisasinya:
> **16 key baru** (bukan 19) karena **19 key `wrapped_*` sudah ada** sejak fase P5 (`wrapped_title`,
> `wrapped_hero`, `wrapped_total`, `wrapped_active_days`, `wrapped_best`, `wrapped_focus`, `wrapped_level`,
> `wrapped_streak`, `wrapped_income`, `wrapped_expense`, `wrapped_top_habits`, `wrapped_habits_top`,
> `wrapped_empty`, `wrapped_open`, `wrapped_close`, dst.) → dipakai ulang, tidak diduplikasi.
> Nama `wrapped_best_day` yang direncanakan **tidak dibuat**: key nyatanya `wrapped_best`
> (`"Hari terbaik: {date} ({n} tugas)"`). `wrapped_saving_rate` akhirnya **tanpa placeholder**
> (`"Rasio tabungan"` / `"Saving rate"`) karena dipakai sebagai label kartu, sedangkan nilai persen
> dirender terpisah. Tambahan di luar rencana: `wrapped_currency_note_idr`, `wrapped_error`,
> `wrapped_type_habit/daily/todo/sport/other`. Lihat Realisasi di bawah.

### 📌 REALISASI A13 (2026-09-16) — apa yang benar-benar dikirim

**Format 1 — Key i18n baru: 16** (blok A13 di `translations.py`, ikut `WEB_I18N_KEYS`; total **4.308 → 4.324**)

| Grup | Jumlah | Key |
|---|---|---|
| Laporan ekonomi | 6 | `wrapped_net` · `wrapped_saving_rate` · `wrapped_by_type` · `wrapped_currency_note` (bervariabel `{currency}`/`{rate}`) · `wrapped_currency_note_idr` · `wrapped_tasks_done` |
| Aksi & pemilih tahun | 4 | `wrapped_pick_year` · `wrapped_copy` · `wrapped_download` · `wrapped_copied` |
| Status | 1 | `wrapped_error` |
| Label tipe task | 5 | `wrapped_type_habit` · `wrapped_type_daily` · `wrapped_type_todo` · `wrapped_type_sport` · `wrapped_type_other` |

**Dipakai ulang (19 key lama fase P5, tidak diduplikasi):** `wrapped_title` · `wrapped_open` ·
`wrapped_hero` · `wrapped_total` · `wrapped_active_days` · `wrapped_best` · `wrapped_focus` ·
`wrapped_level` · `wrapped_streak` · `wrapped_income` · `wrapped_expense` · `wrapped_top_habits` ·
`wrapped_habits_top` · `wrapped_empty` · `wrapped_close` · `btn_close` · `web_retry` · `loading` · `msg_error`

**Format 2 — File yang ditimpa (8)**

| # | File | Perubahan A13 |
|---|---|---|
| 1 | `web/src/components/YearWrappedDialog.tsx` | Tulis ulang penuh: `formatMoney(v, user.currency)` (dulu `money()` `Rp` hardcoded di L31), chip mata uang + catatan kurs, i18n seluruh teks, **selisih bersih** (warna & tanda dinamis), **rasio tabungan**, **rincian per tipe**, top habit ikon + bar, **pemilih tahun**, **Salin ringkasan** + **Unduh .txt** (`saveBlobToFile`), confetti, **empty vs error** + tombol Coba lagi, tutup via `Esc`/klik latar |
| 2 | `web/src/api/rpg.ts` | `yearWrapped(year?: number)` → `GET /api/year-wrapped[?year=]` |
| 3 | `api_server.py` | Route `/api/year-wrapped` naik dari lambda jadi handler eksplisit: `?year=` (validasi 1970–2999, fallback tahun berjalan) + `years[]` + `try/except` → `{ok:false,msg}`; `WEB_I18N_KEYS` **+16** |
| 4 | `database.py` | Fungsi baru **`get_wrapped_years(user_id)`** (tahun dari `task_history` + `pomodoro_sessions` + `economy_items`, menurun, selalu memuat tahun berjalan) — `get_year_wrapped` sendiri **tidak diubah** |
| 5 | `translations.py` | Blok A13 (16 key id+en) |
| 6 | `web/src/components/views/RemindersView.tsx` | Badge **Tahunan** kini tombol (buka dialog edit reminder tahunan itu) — `openEdit` dipecah jadi `openEditOf(r)` + wrapper; badge harian/mingguan tetap label pasif |
| 7 | `web/src/i18n/messages.json` | Hasil `scripts/export_i18n.py` (4.324 key) |
| 8 | `web/public/i18n/messages.json` | Salinan identik (sha256 sama) |

**Format 3 — File baru (1):** `web/src/components/wrapped/wrappedUtils.ts` — logika murni
(`wrappedHasData`, `wrappedNet`, `wrappedSavingRate`, `wrappedTypeLabel`, `wrappedTypeRows`,
`wrappedHabitRows`, `wrappedYearOptions`, `wrappedFileName`, `wrappedCurrencyNote`,
`wrappedSummaryText`); formatter uang **disuntikkan sebagai parameter** supaya tetap murni & bisa diuji.
Harness uji (tidak ikut rilis): `/home/user/a13_harness/{a13_db_api_test.py, a13_regress.py, build.cjs, src/*, fe/*}`.

**Format 4 — Command baru:** `GET /api/year-wrapped?year=2025` (opsional; tanpa parameter tetap kompatibel
seperti sebelumnya) → respons kini `{ok, wrapped, years[]}`. Perintah uji:
`python3 /home/user/a13_harness/a13_db_api_test.py` · `python3 /home/user/a13_harness/a13_regress.py` ·
`NODE_PATH=web/node_modules node /home/user/a13_harness/build.cjs` lalu
`NODE_PATH=web/node_modules A13_WEB=web node /home/user/a13_harness/fe/a13_unit.cjs` (dan `…/a13_view.cjs`).

**Format 5 — Kesimpulan fase:** Item #4 user tertutup: laporan ekonomi Year Wrapped **mengikuti mata uang
aktif** (satu-satunya formatter resmi, plus chip & catatan kurs), seluruh dialog ber-i18n **id+en**, dan
laporan naik kelas (selisih bersih, rasio tabungan, rincian per tipe, bar, pemilih tahun, salin/unduh,
confetti) dengan **empty-state terpisah dari error**. Server tetap satu sumber kebenaran: angka dikirim
IDR mentah, konversi hanya di klien.

**Format 6 — Migrasi:** — (**tidak ada**). A13 hanya **membaca** tabel yang sudah ada
(`task_history`, `pomodoro_sessions`, `economy_items`, `habits`, `users`) dan tidak menambah
kolom/tabel → SQLite auto-apply apa adanya, **Supabase: tidak ada** migrasi cloud.

**Hasil uji:** DB/API **33/33** ✅ · FE **103/103** (unit 59 + DOM 44) ✅ · regresi A09–A13 **33/33** ✅
(3× berturut) · `tsc --noEmit` **0 error** · `py_compile` **6/6 OK** · build **`index-C18HtkK7.js`**
(1.295,08 kB) + **`index-BtP_pgWk.css`** (178,50 kB) · live `:8899`: health 200, aset baru 200,
`/api/i18n` dua bahasa memuat key A13, `/api/year-wrapped` normal.

**Catatan jujur (self-caught sebelum kirim):**
1. Rencana `wrapped_saving_rate` memakai placeholder `{pct}%`, tetapi di UI key itu dipakai sebagai
   **label kartu** → placeholder akan bocor tampil mentah. Diperbaiki jadi label tanpa placeholder
   (nilai persen dirender terpisah); ringkasan teks menyusun `"Rasio tabungan 60%"`.
2. `wrapped_best_day` pada rencana tidak ada di berkas i18n — key nyata **`wrapped_best`**; dipakai apa adanya.
3. Catatan kurs memakai `formatMoney` (pemisah ribuan gaya modul: `Rp 17,800`), **bukan** `Rp 17.800`
   seperti di roadmap — sengaja demi konsistensi dengan seluruh modul currency.

---

# 🏁 FINALISASI — A14

## A14 — Finalisasi & rilis **v1.6.3** (penutup commit phase A)

**Langkah:**
1. **i18n sinkron penuh:**
   ```bash
   python scripts/export_i18n.py
   cp web/src/i18n/messages.json web/public/i18n/messages.json
   ```
   lalu verifikasi 4 arah: `translations.py` ↔ `WEB_I18N_KEYS` (bila ada key baru yang perlu disajikan API) ↔
   `messages.json` ↔ `public/i18n/messages.json` — jumlah key **harus identik** (laporan angka di kesimpulan).
2. **Versi:** `updater.py` → `APP_VERSION = "1.6.3"` + komentar riwayat versi;
   `web/package.json` → `"version": "1.6.3"`; cek juga label versi di `SettingsView` (bila membaca dari API → otomatis).
3. **README.md (REVISI):** badge Release → `v1.6.3 "…"`, badge i18n → jumlah key final, tambah seksi
   **"✨ What's New in v1.6.3"** (tabel perbaikan per area: Music / Learning / Love Space / Home + item fatal
   ditandai), segarkan **Feature Tour** (Music: lirik per-trek + pencarian kandidat + import terdokumentasi;
   Learning: dialog per tipe + daftar artefak + UI NotebookLM-style; Love Space: special days + reminder tahunan
   + dashboard pasangan; Home: Wrapped multi-currency), tambah baris roadmap
   `✅ Commit Phase A (A01–A14) — v1.6.3`, dan **perbaiki 3 link `UPDATES/…` yang rusak** (temuan analisis §11.2)
   sebagai bonus dokumentasi — *tanpa* menyentuh kode.
4. **`RELEASE_NOTES_v1.6.3.md`** untuk GitHub Release (file baru, draf ada di workspace).
5. **`2026-09-14-A01-A14-PHASE-SUMMARY.md`** — rekap satu commit phase format 1–6 (mengikuti pola
   `2026-09-08-P47-P63-PHASE-SUMMARY.md`) berisi: daftar file ditimpa, file baru, key i18n baru, endpoint baru,
   migrasi (SQLite + Supabase opsional), kesimpulan per fase, langkah operator rilis.
6. **Verifikasi penuh rilis:**

| Uji | Target |
|---|---|
| `python -m py_compile` modul tersentuh (`api_server`, `database`, `studio_api`, `life_api`, `learning_helper`, `music_downloader`, `translations`, `updater`) | EXIT 0 |
| `npx tsc --noEmit` | 0 error |
| `npx vite build` | clean (catat ukuran CSS/JS baru) |
| **Smoke S1–S10** (API hidup + curl) | lihat Lampiran C |
| Uji UI headless (WebEngine/Chromium) | Music · Learning · Love · Home terbuka tanpa error konsol |
| Konsistensi i18n 4 arah | jumlah key identik |
| Workspace bersih dari artefak uji (`craftlife.db*`, `backups/`, lampiran uji) | tidak ada file sampah ikut ter-commit |

7. **Kesimpulan commit phase A (format 1–7)** — dibuat sebagai dokumen terpisah + dirangkum di jawaban akhir.

**Format 1 — i18n key baru:** gabungan seluruh fase (lihat Lampiran B) — **±145 key** baru untuk id & en.
**Format 2 — File ditimpa (final):** `README.md` · `updater.py` · `web/package.json` ·
`web/src/i18n/messages.json` · `web/public/i18n/messages.json` + seluruh file fase A01–A13.
**Format 3 — File baru (final):** `RELEASE_NOTES_v1.6.3.md` · `2026-09-14-A01-A14-PHASE-SUMMARY.md` (+ 12 file kode baru dari fase sebelumnya).
**Format 4 — Command baru (final):** 9 endpoint + 1 env var (lihat Lampiran B/C).
**Format 5 — Kesimpulan fase:** Commit phase A ditutup pada v1.6.3 dengan 4 area permintaan user terpenuhi, semua bug fatal tertutup, dokumentasi rilis (README + Release Notes + rekap fase) lengkap, dan verifikasi berjenjang lolos.
**Format 6 — Migrasi:** SQLite: 5 blok migrasi (A06 `learning_generations.updated_at`; A08 `learning_chats.citations` **+ tabel `learning_audio`**; A09 6 kolom `relationship_events`; A10 9 kolom 2 tabel + A11 `menstrual_cycles.updated_at` & `love_albums.cover_photo_id` + 2 indeks + A12 `reminders.repeat_until` & `reminders.source_ref` + indeks `idx_reminders_source_ref`) — semua auto-apply. Supabase: **3 migrasi opsional** — `20260916000000_phase_a09_love_special_days.sql`, `20260916010000_phase_a10_love_memories_bucket.sql`, dan `20260916020000_phase_a11_love_cycle_gallery_alignment.sql` (hanya untuk user cloud; ketiganya berdiri sendiri sehingga aman dijalankan berurutan).

### 📌 REALISASI A14 (2026-09-16) — penutup commit phase

**Format 1 — i18n:** sinkron 4 arah **4.324 = 4.324 = 4.324** (`translations.py` ↔ `src/i18n/messages.json` ↔ `public/i18n/messages.json`), 0 nilai menyimpang, `WEB_I18N_KEYS` **4.253** lengkap di id+en; commit phase **+567 key** (3.757 → 4.324).

**Format 2 — file final ditimpa:** README (badge rilis → v1.6.3 “Quality of Life+”, badge i18n → 4.324, What’s New final + ringkasan per area, Feature Tour Music/Learning/Love Space, roadmap commit phase, **3 link `UPDATES/…` rusak diperbaiki**) · `updater.py` · `web/package.json` (1.6.3) · `web/src/i18n/messages.json` + `web/public/i18n/messages.json` · `.gitignore` (craftlife.db-shm/-wal, logs/) + seluruh file fase A01–A13.

**Format 3 — file baru:** `RELEASE_NOTES_v1.6.3.md` (final) · `2026-09-14-A01-A14-PHASE-SUMMARY.md` (rekap Format 1–7) + 14 laporan per fase + 27 file kode baru (A02–A13) + 3 migrasi Supabase opsional.

**Format 4 — command:** tidak ada endpoint baru di A14; yang dijalankan adalah **Smoke S1–S10** (`python3 /home/user/a14_harness/smoke_a14.py` → **55/55**) + perintah wajib tiap fase (`py_compile` 8 modul · `tsc --noEmit` · `vite build` · `export_i18n.py` + salin).

**Format 5 — kesimpulan:** rilis v1.6.3 ditutup sebagai **satu commit phase**: 4 area permintaan user terkirim, 3 bug fatal tertutup, dokumentasi rilis lengkap (README + Release Notes + rekap fase), verifikasi berjenjang lolos, workspace bersih dari artefak uji.

**Format 6 — migrasi:** tidak ada migrasi baru di A14 (SQLite auto-apply & 3 Supabase opsional sudah terdokumentasi di Format 6 fase A06/A08–A12).

**Bukti verifikasi A14:** `py_compile` **8/8 EXIT 0** · `tsc` **0 error** · build **`index-C18HtkK7.js`** (1.295,08 kB) + **`index-BtP_pgWk.css`** (178,50 kB) · Smoke **S1–S10 55/55** · harness FE A11 170/171 (1 snapshot key lama) · A12 136/136 · A13 103/103 · regresi A13 33/33 (3×) + DB/API 33/33 · DB bersih (0 baris semua tabel uji, integrity ok, currency IDR) · `/api/version` **1.6.3**.

---

### 📌 REALISASI A15 (2026-09-16) — perbaikan rail kiri Learning (lanjutan A14)

**Permintaan user:** *satu perbaikan kecil* di **sidebar kiri** halaman Learning — ikon notebook harus
tampil sesuai emoji yang diinput user saat membuat notebook, dan tata letaknya dirapikan.
**Batasan yang dipegang:** hanya rail kiri (`NotebookRail.tsx`); panel tengah (Sumber) & kanan (Chat/Studio)
tidak disentuh.

**Format 1 — i18n:** **+1 key** `learning_icon_label` = ("Ikon (emoji)", "Icon (emoji)") → `translations.py` &
`messages.json` (`web/src` + `web/public`, identik) **4.325**; pindai 107 berkas `web/src` → 1.799 key literal
dipakai, **0 hilang** di id & en (8 prefiks dinamis).

**Format 2 — file ditimpa:** `database.py` (migrasi 3 kolom + `create_learning_notebook(user, title, icon, description)`
+ `update_learning_notebook` parsial + helper `_notebook_icon`) · `studio_api.py` (create membaca `icon`/`description`;
`rename` parsial + kode error `learning_no_fields`) · `web/src/components/learning/NotebookRail.tsx` (satu avatar,
`notebookGlyph()`, tata letak) · `web/src/components/views/LearningView.tsx` (pemilih emoji bersama `NB_EMOJI` +
`NotebookIconPicker`, `openRenameDialog`, ikon ikut tersimpan & direset) · `web/src/api/studio.ts`
(`renameNotebook(id, title, icon?)`) · `web/src/index.css` (modifier rail `.is-row`/`.is-sm`/`:focus-visible` +
aturan bottom-bar `<1024 px`) · `translations.py` · `web/src/i18n/messages.json` + `web/public/i18n/messages.json` ·
README · RELEASE_NOTES · `updater.py`.

**Format 3 — file baru:** tidak ada berkas kode baru (perbaikan memakai berkas yang sudah ada);
harness `a15_harness/{build.cjs, src/rail.tsx, i18n_scan.py, a15_db_test.py, a15_api_test.py, patch_a15_*.py}`.

**Format 4 — command:** tidak ada endpoint baru; endpoint lama diperluas (`POST /api/learning/notebooks`
menerima `icon`/`description`; `POST /api/learning/notebooks/<id>/rename` menerima `icon`). Perintah uji:
`python3 /home/user/a15_harness/i18n_scan.py` · `python3 /home/user/a15_harness/a15_db_test.py` ·
`python3 /home/user/a15_harness/a15_api_test.py` · `node /home/user/a15_harness/fe/a15_rail.cjs`.

**Format 5 — kesimpulan:** ikon notebook kini benar-benar tersimpan dan tampil sesuai pilihan user, rail kiri
rapi (lebar 72/220 px, judul terpotong aman, aksi jelas), dan notebook lama pun bisa diganti ikonnya.
Verifikasi: DB **23/23** · API **17/17** · harness rail **46/46** · regresi A11 **170/170** · A12 **136/136** ·
A13 **103/103** · `py_compile` **8/8** · `tsc` **0 error** · build bersih.

**Format 6 — migrasi:** SQLite auto-apply **blok ke-7**: `learning_notebooks.icon` (TEXT DEFAULT '📚'),
`.description` (TEXT DEFAULT ''), `.updated_at` (TEXT DEFAULT '') — dijalankan di `init_db()` (setelah blok A06)
sehingga database **baru** maupun **lama** sama-sama mendapat kolomnya. **Tidak ada migrasi Supabase**
(notebook hanya tersimpan lokal).

---

# 📎 LAMPIRAN A — Master File List (untuk copy-paste dari workspace ke laptop)

### A.1 File yang harus ditimpa (23)

**Backend / Python (7)**
1. `database.py` — A06, A08, A09, A10, A11, A12, **A13** (`get_wrapped_years`) (migrasi kolom + fungsi baru)
2. `studio_api.py` — A02, A03, A06, A09, A10, A11, A12 (endpoint & mapping)
3. `learning_helper.py` — A04, A05, A08 (prompt + parameter baru)
4. `music_downloader.py` — A02 (batas library + `get_track_meta`)
5. `api_server.py` — A02, A12, **A13 ✅** (route `track-meta`, `WEB_I18N_KEYS`, handler `year-wrapped` + `?year=`)
5b. `life_api.py` — A12 (whitelist `repeat: yearly` di `map_reminder`, `repeatUntil` di create/update, `repeat_until` pada `trigger`, update parsial tidak menghapus pengulangan)
6. `translations.py` — semua fase (key id+en baru) — termasuk blok **A13** (16 key `wrapped_*`)
7. `updater.py` — A14 (`APP_VERSION = "1.6.3"`)

**Frontend (11)**
8. `web/src/components/views/MusicView.tsx` — A01, A02, A03
9. `web/src/components/music/LyricsDrawer.tsx` — A01, A02, A03
10. `web/src/components/views/LearningView.tsx` — A04, A05, A06, A07
11. `web/src/components/views/LoveSpaceView.tsx` — A09, A10, A11, A12
12. `web/src/components/views/RemindersView.tsx` — A12 (opsi repeat tahunan, badge **klik→edit** di A13)
13. `web/src/components/views/DashboardView.tsx` — A12 (chip hari istimewa, opsional)
14. `web/src/components/YearWrappedDialog.tsx` — **A13 ✅** (tulis ulang: currency user + i18n + polish)
15. `web/src/context/GameContext.tsx` — A09, A10, A12 (action baru)
16. `web/src/api/studio.ts` · 17. `web/src/api/rpg.ts` — endpoint baru (**A13**: `yearWrapped(year?)`)
18. `web/src/index.css` — A07 (token & kelas baru design language Learning)
19. `web/package.json` — A14 (versi)
20. `web/src/App.tsx` — A12 (`onNavigate` untuk aksi cepat Love Space)
21. `web/src/types.ts` — A12 (`ReminderItem.repeat` memuat `'yearly'`, `repeatUntil`, `sourceRef`)
22. `web/src/i18n/messages.json` + 23. `web/public/i18n/messages.json` — semua fase (hasil `export_i18n.py`)

**Dokumen (1)**
- `README.md` — A14 (REVISI)

### A.2 File baru (27 file kode + 3 migrasi Supabase opsional + dokumen)

| File | Fase |
|---|---|
| `web/src/components/music/LyricsSearchDialog.tsx` | A02 |
| `web/src/components/music/LyricsImportDialog.tsx` | A03 |
| `web/src/components/learning/QuizCountFields.tsx` | A04 |
| `web/src/components/learning/StudioGenerateDialog.tsx` | A05 |
| `web/src/components/learning/studioOptions.ts` | A05 |
| `web/src/components/learning/StudioArtifactList.tsx` | A06 |
| `web/src/components/learning/LearningShell.tsx` | A07 |
| `web/src/components/learning/SourcesRail.tsx` · `ChatPanel.tsx` · `NotebookRail.tsx` · `SourceCard.tsx` | A07 |
| `web/src/components/learning/CitationChip.tsx` | A08 |
| `web/src/components/love/LoveEventDialog.tsx` | A09 |
| `web/src/components/love/LoveMemoryDialog.tsx` · `LoveBucketDialog.tsx` · `memoryUtils.ts` | A10 |
| `web/src/components/love/LoveConnectionPanel.tsx` · `LoveCyclePanel.tsx` · `LoveGalleryPanel.tsx` | A11 |
| `web/src/components/love/connectionUtils.ts` · `cycleUtils.ts` · `galleryUtils.ts` · `galleryParts.tsx` | A11 |
| `supabase/migrations/20260916020000_phase_a11_love_cycle_gallery_alignment.sql` *(opsional)* | A11 |
| `web/src/components/love/LoveOverviewPanel.tsx` · `ConnectionScoreRing.tsx` · `overviewUtils.ts` | A12 |
| `web/src/components/wrapped/wrappedUtils.ts` | **A13** |
| `RELEASE_NOTES_v1.6.3.md` · `2026-09-14-A01-A14-PHASE-SUMMARY.md` | A14 |
| `supabase/migrations/2026xxxxxxxxxx_phase_a_love_special_days.sql` *(opsional)* | A09 |
| `supabase/migrations/20260916010000_phase_a10_love_memories_bucket.sql` *(opsional)* | A10 |

---

# 📎 LAMPIRAN B — Master Command & i18n Baru

### B.1 Endpoint baru (10)

```
GET  /api/music/lyrics-candidates?artist=&title=&album=&duration=&key=
POST /api/music/lyrics-apply
GET  /api/music/lyrics-validate  (POST)          POST /api/music/lyrics-validate
GET  /api/music/lyrics-template
GET  /api/music/lyrics-export?key=&format=lrc|txt
GET  /api/music/track-meta?paths=a|b|c
POST /api/learning/generations/rename
GET  /api/learning/generations/export?generationId=&notebookId=&format=md|txt
POST /api/love/events/<id>/update
GET  /api/love/events/upcoming?days=90
POST /api/love/events/<id>/create-reminder
POST /api/love/memories/<id>/update · /api/love/memories/<id>/favorite
POST /api/love/bucket/<id>/update · /api/love/bucket/<id>/promote-to-memory
POST /api/love/cycles/<id>/update · /api/love/albums/<id>/cover · /api/love/photos/bulk
GET  /api/year-wrapped?year=            (A13 ✅ — + `years[]` di respons)
```
*(total ±18 rute; 9 di antaranya benar-benar modul baru, sisanya sub-rute aksi pada entitas yang sudah ada)*

### B.2 Env baru

```
CRAFTLIFE_MUSIC_LIB_LIMIT=500      # batas item listing pustaka musik (default 500, sebelumnya hardcode 80)
```

### B.3 Perintah wajib tiap fase

```bash
python -m py_compile api_server.py database.py studio_api.py life_api.py learning_helper.py music_downloader.py translations.py updater.py
cd web && npx tsc --noEmit && npx vite build
python scripts/export_i18n.py && cp web/src/i18n/messages.json web/public/i18n/messages.json
python api_server.py            # smoke endpoint yang berubah
```

### B.4 Key i18n baru per fase (untuk `translations.py`)

| Fase | Namespace / jumlah | Contoh key |
|---|---|---|
| A01 | `music_lyrics_*` (3) | `music_lyrics_now_for`, `music_lyrics_track_change_hint` |
| A02 | `music_lyrics_*` (13) | `music_lyrics_candidates`, `music_lyrics_duration_off`, `music_lyrics_source_pick` |
| A03 | `music_lyrics_*` (14) | `music_lyrics_import_title`, `music_lyrics_format_lrc_desc`, `music_lyrics_download_template` |
| A04 | `learning_quiz_*` (14) | `learning_quiz_mc_count`, `learning_quiz_total_over`, `learning_quiz_essay_self_mark` |
| A05 | `learning_opt_*` / `learning_dialog_*` (34) | `learning_opt_difficulty_hard`, `learning_opt_host_debate`, `learning_opt_granularity` |
| A06 | `learning_artifact*` (18) | `learning_artifacts`, `learning_artifact_export_md`, `learning_artifact_sort_type` |
| A07 | `learning_*` (30) | `learning_view_sources`, `learning_suggestion_q1`, `learning_panel_wide` |
| A08 | `learning_citation*` + `learning_podcast_*` + `play`/`pause` (**32**) | `learning_citations`, `learning_citation_source_n`, `learning_open_source`, `learning_grounding_on`, `learning_sources_selected_count`, `learning_filter_sources`, `learning_podcast_title`, `learning_podcast_hosts_voices`, `learning_podcast_seek`, `learning_podcast_back15`, `learning_podcast_fwd15`, `learning_podcast_speed`, `learning_podcast_loop`, `learning_podcast_loop_short`, `learning_podcast_follow`, `learning_podcast_follow_short`, `learning_podcast_download`, `learning_podcast_download_short`, `learning_podcast_regenerate`, `learning_podcast_regenerate_short`, `learning_podcast_generating_hint`, `learning_podcast_generate_hint`, `learning_podcast_engine`, `learning_podcast_host`, `learning_podcast_now`, `learning_podcast_no_turns`, `learning_podcast_audio_failed`, `learning_podcast_audio_ready`, `learning_podcast_audio_ready_detail`, `learning_no_podcast`, `learning_citations_found`, `play`, `pause` |
| A09 | `love_event_*` (18) | `love_event_notes`, `love_event_special`, `love_event_in_days` |
| A10 | `love_memory_*` / `love_bucket_*` (**90**) | `love_memory_edit_title`, `love_memory_emoji`, `love_memory_only_fav`, `love_memory_link_photo`, `love_bucket_progress`, `love_bucket_promote`, `love_bucket_target_date`, `love_bucket_priority`, `love_bucket_filter_late`, `love_memory_tags` |
| A11 | `love_conn_*` / `love_cycle_*` / `love_gallery_*` / `love_album_*` (**78 baru** dari 82 entri blok A11) | `love_conn_mood_trend`, `love_conn_streak`, `love_cycle_next`, `love_cycle_add_reminder`, `love_gallery_select_mode`, `love_gallery_bulk_move`, `love_gallery_save_meta` |
| A12 | `love_*` / `reminders_*` / `dash_*` (**64 baru** — 4.244 → 4.308) | `love_together_days`, `love_next_special`, `love_create_reminder`, `love_reminder_birthday`, `love_stat_bucket_of`, `love_quick_checkin`, `reminders_badge_yearly`, `dash_next_special` |
| A13 ✅ | `wrapped_*` (**16 baru** — 4.308 → **4.324**; **19 key lama dipakai ulang** (15 `wrapped_*` + `btn_close`, `web_retry`, `loading`, `msg_error`)) | `wrapped_net`, `wrapped_saving_rate`, `wrapped_currency_note`, `wrapped_currency_note_idr`, `wrapped_pick_year`, `wrapped_copy`, `wrapped_download`, `wrapped_copied`, `wrapped_error`, `wrapped_tasks_done`, `wrapped_type_habit/daily/todo/sport/other` |
| **Total** | **+567 key baru** (id + en; **3.757 → 4.324**) | seluruhnya dijaga konsisten oleh `scripts/export_i18n.py` |

---

# 📎 LAMPIRAN C — Checklist Smoke Test v1.6.3 ✅ *DIJALANKAN 2026-09-16 (A14) — 55/55 LOLOS*

> Skrip: `python3 /home/user/a14_harness/smoke_a14.py` (server hidup `:8899`). Hasil rinci per skenario: blok **✅ A14 verification** di `README.md`.

| # | Skenario | Perintah / langkah | Harapan |
|---|---|---|---|
| S1 | API hidup & versi | `curl /api/health`, `/api/version` | `ok:true`, `version: 1.6.3` |
| S2 | Music — lirik ikut lagu | putar trek → next → auto-advance | lirik berganti tiap trek |
| S3 | Music — kandidat lirik | `curl "/api/music/lyrics-candidates?artist=Tulus&title=Monokrom&duration=...`" | ≥1 kandidat + skor |
| S4 | Music — import & template | unduh `lyrics-template`, impor kembali, validasi | format terdeteksi `lrc`, n baris bertimestamp |
| S5 | Learning — essay | generate quiz (10 PG + 5 Essay) → ketik 5 essay → evaluasi | teks tersimpan, skor komposit tampil |
| S6 | Learning — dialog per tipe | FAQ jumlah 5 vs 15 | hasil sesuai opsi |
| S7 | Learning — artefak | generate 3 tipe → daftar artefak | 3 kartu, filter/rename/ekspor jalan |
| S8 | Love — event notes & special day | tambah event + notes → edit → special day tahunan | notes tersimpan; muncul di "Akan datang" |
| S9 | Love — reminder tahunan | buat pengingat dari special day | reminder `repeat_type=yearly` + tanggal H-n |
| S10 | Home — Wrapped currency | set currency USD → buka Wrapped | angka & simbol USD + catatan kurs; bahasa en → teks Inggris |

---

# 📎 LAMPIRAN D — Risiko & Mitigasi

| Risiko | Fase | Mitigasi |
|---|---|---|
| Model Gemini tidak konsisten mencantumkan sitasi | A08 | Fallback tanpa chip; fase dapat ditunda tanpa menahan fase lain |
| Perubahan prompt menyentuh 8 tipe → regresi hasil | A05 | Parameter opsional (tanpa parameter = prompt lama), uji 1 generate per tipe |
| Rombakan UI Learning menurunkan performa WebEngine | A07 | Pertahankan aturan R10 anti-flicker; uji headless di WebEngine; hindari `backdrop-filter` & animasi idle |
| Kolom baru Love tidak tersinkron ke cloud | A09–A11 | Migrasi Supabase opsional disediakan; tanpa itu field baru tetap lokal (tidak ada error — RPC whitelist) |
| Race condition lirik saat user berpindah cepat | A01 | Race guard `trackKey` + cache per trek |
| `tsc` gagal karena `types.ts` perlu tipe baru | A04, A06, A09–A12 | Tipe `LearningGeneration`, `LoveEvent`, `LoveMemory`, `LoveBucketItem` diperbarui di fase terkait (bagian dari file ditimpa) |

---

# 📎 LAMPIRAN E — Backlog (BUKAN bagian commit phase ini)

Hasil analisis repo v1.6.0 (§11 dokumen `CraftLife-ANALISIS-v1.6.0.md`) yang **sengaja ditunda** oleh user:

| # | Item | Dampak |
|---|---|---|
| B01 | `.env` dikeluarkan dari git + `.env.example` + rotasi kunci | 🔴 keamanan |
| B02 | Perbaikan 3 link `UPDATES/…` di README *(sebagian dikerjakan di A14 sebagai bonus dokumentasi)* | 🟠 dokumentasi |
| B03 | Hapus 8 file mati (`BossView`, `NutritionView`, `HealthPomodoroView`, 4 `data/*`, `useUndo`) | 🟠 kebersihan |
| B04 | Hapus duplikat route `/api/catalog/avatar-classes` | 🟠 kebersihan |
| B05 | Code-splitting bundle (JS 1,08 MB → target <600 KB) | 🟠 performa |
| B06 | Pytest untuk `database.py` + `scripts/smoke.py` gate rilis otomatis | 🟠 kualitas |
| B07 | Pecah `GameContext` (222 member) & `MainPyQt6.py` (25k baris) | 🟡 pemeliharaan |
| B08 | Pemisahan definisi tema PyQt ↔ CSS token (anti-drift) | 🟡 konsistensi |

---

*Roadmap ini disusun dari pembacaan kode langsung pada commit `cfdac0d` (v1.6.0). Setiap fase menyebutkan file + nomor baris bukti, sehingga implementasi bisa diverifikasi ulang satu per satu.*
