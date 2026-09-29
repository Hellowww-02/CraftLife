# 🗺️ CraftLife Update Roadmap — Commit Phase **I** (I01 → I07) → **v1.7.2**

> Catatan versi: v1.7.1 dilewati dengan sengaja (keputusan user). Lompatan
> v1.7.0 → v1.7.2 sah untuk rilis ini.

## 📋 Permintaan user (verbatim, disingkat)

1. **Rekonstruksi 22 page** — frontend/UI/UX semua page + seluruh app:
   profesional, lebih interaktif, animatif, variatif; tiap page punya
   *signature* masing-masing. Kebebasan layout/design penuh.
   **HARD CONSTRAINT:** tidak boleh mengurangi fitur/sistem/logika/game —
   hanya menambah/memperbaiki/memodifikasi.
2. **Tema** — +5 tema baru (total 12), rekonstruksi 7 tema lama: palet warna
   profesional, animatif, variatif, interaktif.
3. **Markdown reader** — release notes di auto-updater & saved notes di
   Learning masih tampil sebagai teks markdown mentah → harus ter-render.
4. **Gemini API key tidak tersimpan** — pindah page / restart app → key
   hilang → chat & Studio error.
5. **Duplicate task salah folder** — duplikat kartu task harus masuk folder
   yang sedang dipilih user (bug: masuk Ungrouped). Berlaku TaskPage &
   SportTrack.
6. Ikuti 5 skill repo (taste-skill, vercel web-design-guidelines,
   awesome-design-md, image-to-code, playwright-cli).

## 🔍 Hasil audit (akar masalah)

| Item | Temuan |
|---|---|
| Gemini key | Backend persist OK (`users.gemini_api_key`, db commit). **Akar bug:** UI memakai `window.prompt()` — tidak didukung PyQt6 WebEngine & tidak andal di browser → save sering tidak terjadi; indikator key juga tidak dipulihkan saat mount. Fix: dialog input proper + GET status key + indikator persisten. |
| Duplicate folder | `db.duplicate_habit/daily/todo/sport_activity` TIDAK menyalin `folder_id` (semua tabel punya kolomnya). Fix: salin folder asli + terima folder target eksplisit dari frontend (folder aktif). |
| Markdown | `UpdateDialog.tsx:168` (`{info.notes}` mentah) & modal saved notes LearningView (`<pre>{body}</pre>`) → ganti ReactMarkdown (dependensi sudah ada). |
| Tema | 7 tema di `database.py THEMES` (single source of truth; R-prinsip). Web mengambil via `/api/catalog/themes`. Tambah 5 + poles 7. |
| 22 page | 24 view unik di `web/src/components/views/` (nutrition≡health, boss≡guild, social≡friends, lovespace≡love). Signature = identitas visual per halaman (header, aksen warna, motion, ornamen) tanpa mengubah logika. |

## 🗺️ Peta fase

| Fase | Isi | Gate bukti |
|---|---|---|
| **I01** | Bug batch: Gemini key (dialog+GET+indikator), duplicate→folder aktif (4 fungsi DB + API + frontend), Markdown ×2 | uji live :8899; tsc; build |
| **I02** | Tema: +5 baru, 7 lama dipoles palet & token; picker tema diperkaya (preview) | hitung THEMES=12; tsc; build |
| **I03** | Design system v2: toolkit signature (CSS animasi bersama `ct-sig-*`, PageSignature header, aksen per page, theme-aware) — fondasi I04–I06 | tsc; build |
| **I04** | Signature klaster A: dashboard, profile, habits, dailies, quests, sport, nutrition | visual + tsc; build |
| **I05** | Signature klaster B: shop, craft, pets, economy, supplies, notes, pomodoro | visual + tsc; build |
| **I06** | Signature klaster C: learning, music, love, friends, guild, reminders, calendar, achievements, leaderboard, settings | visual + tsc; build |
| **I07** | Finalisasi: updater 1.7.2, release notes, README, i18n sync, tag v1.7.2 | semua gate + 1 commit + tag |

## 🔒 Keputusan terkunci

- **K1** Versi = v1.7.2 (eksplisit user; v1.7.1 dilewati).
- **K2** Duplicate masuk **folder aktif**; bila tampilan "All" → salin folder asli task (fix dasar).
- **K3** Signature page = lapisan presentasi (header/aksen/motion/ornamen);
  handler, endpoint, dan state logika TIDAK dikurangi/diubah semantics-nya.
- **K4** Tema tetap bersumber tunggal di `database.py THEMES` (R6: satu sumber);
  web membaca katalog; key `theme_*` i18n untuk label baru.
- **K5** Markdown: ReactMarkdown (sudah dipakai di Learning studio) — tanpa dependensi baru.
- **K6** Tidak ada migrasi skema wajib; bila ada kolom tambahan → `_safe_alter` idempoten.
- **K7** Semua string baru bilingual id+en → translations.py.

## 📎 Perintah wajib tiap fase

```bash
python3 -m py_compile <modul tersentuh>
python3 scripts/export_i18n.py && cp web/src/i18n/messages.json web/public/i18n/messages.json
cd web && npx tsc --noEmit && npx vite build
CRAFTLIFE_API_PORT=8899 python3 api_server.py   # smoke endpoint tersentuh
```
