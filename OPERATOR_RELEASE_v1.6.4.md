# Operator: publikasi rilis CraftLife v1.6.4 (C07)

Dokumen ini langkah konkret menerbitkan rilis agar **user lama auto-update**
(desktop PyQt + Web UI). Prasyarat: fase **C09 sudah selesai** (versi 1.6.4
dibump di `updater.py` + `web/package.json`). JANGAN publish dari branch kerja
C07 — `APP_VERSION` masih `1.6.3` sampai C09.

## 0. Syarat sebelum mulai

- [ ] C09 selesai (bump versi + smoke test).
- [ ] Repo bersih: semua harness hijau, `tsc` 0 error, `vite build` bersih.
- [ ] Akses publish ke repo `Hellowww-02/CraftLife` (GitHub Releases).

## 1. Build Windows (`--onedir`)

```powershell
# dari root repo, di mesin build Windows:
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

Hasil wajib: folder `dist/CraftLife/` berisi **`CraftLife.exe`** + pustaka.
(Catatan: updater C07 mengenali zip yang memuat folder `dist/CraftLife/`,
tetapi tata letak RESMI tetap: **isi** `dist/CraftLife/` di **root zip**.)

## 2. Zip ISI folder (bukan foldernya)

Masuk ke `dist/CraftLife/`, pilih **semua isi**, kompres menjadi:

```text
craftlife-1.6.4.zip
```

**JANGAN sertakan:** `.env`, `craftlife.db*` (`-wal`/`-shm`), `_update_state.json`,
`_update_apply.log`, folder `backups/`, `logs/`, `_update_staging/`.

Verifikasi cepat (WAJIB — updater abort bila exe absen):

```powershell
# root zip harus langsung memuat CraftLife.exe:
tar -tf craftlife-1.6.4.zip | Select-String -Pattern "^CraftLife.exe$|^dist/CraftLife/CraftLife.exe$"
```

Salah satu baris di atas HARUS muncul. Bila tidak ada → zip salah, ulangi.

## 3. Catat sha256 (verifikasi manual)

```powershell
(Get-FileHash craftlife-1.6.4.zip -Algorithm SHA256).Hash.ToLower()
```

GitHub otomatis menyediakan `digest` per aset (dipakai updater untuk verifikasi);
hash lokal ini untuk pemeriksaan manual bila ada laporan `updater_checksum`.

## 4. Buat GitHub Release

1. Repo → **Releases** → **Draft a new release**.
2. **Tag:** `v1.6.4` — TEPAT seperti ini. LARANGAN: `v.1.6.4` (titik nyasar,
   pernah terjadi di 1.6.3), spasi, atau tanpa huruf `v`.
3. **Title:** `CraftLife v1.6.4`.
4. **Notes:** ringkasan user-facing (ID + EN singkat disarankan).
5. **Attach:** `craftlife-1.6.4.zip` (tepat satu zip).
6. **Publish release** (sebagai **latest** — bukan pre-release).

## 5. Verifikasi end-to-end (mesin uji di v1.6.3)

- [ ] Desktop: dialog update muncul (otomatis/manual) → Download → progres
      0→100% → countdown → restart → versi terbaca **1.6.4**.
- [ ] Web UI: badge/dialog update muncul setelah start → alur sama → server
      restart → versi **1.6.4**.
- [ ] `_update_apply.log` di folder aplikasi memuat `exe check OK` + `selesai`.
- [ ] Data user utuh: `.env`, `craftlife.db`, `backups/` tidak tersentuh
      (updater memproteksinya).

## 6. Bila rilis rusak (rollback)

1. Di GitHub Release v1.6.4 → **Edit** → centang **pre-release** + **Save**.
   `releases/latest` tidak lagi menawarkannya (updater membaca endpoint itu).
2. Perbaiki → ulangi langkah 1–5 dengan tag patch (`v1.6.5`), JANGAN
   menimpa/menghapus tag `v1.6.4` yang sudah terlanjur diambil sebagian user.
3. User yang sudah terlanjur rusak: arahkan unduh manual zip rilis sehat,
   ekstrak menimpa instalasi (`.env` + `craftlife.db` aman tidak ikut di zip).

## 7. Larangan (ringkas)

| # | Jangan | Kenapa |
|---|--------|--------|
| 1 | Tag `v.1.6.4` / tanpa `v` | Komparasi versi & display rusak |
| 2 | Zip berisi folder `dist/` | Updater abort `updater_no_exe` |
| 3 | Sertakan `.env` / `craftlife.db` | Menimpa data user |
| 4 | Publish sebagai pre-release | Tidak terdeteksi `latest` |
| 5 | Publish sebelum C09 | Versi masih 1.6.3 = loop update |

*Rujukan teknis: `updater.py` (docstring C07), UPDATE_RULES §10, roadmap C07.*
