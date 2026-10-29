# DESIGN.md — Kontrak Visual CraftLife

**Versi:** 1.7.4 · **Fase:** M06 · **Status:** aktif
**Sumber mesin:** `packages/craftlife-core/src/design/tokens.json`
**Generator:** `scripts/export_design_tokens.py` · **Tes:** `tests/test_m06_design_tokens.py` (19)

Dokumen ini adalah satu-satunya kontrak visual untuk **web dan Android**. Kalau
nilai di sini dan di `tokens.json` berbeda, `tokens.json` yang menang — dan
berarti dokumen ini yang harus diperbarui.

---

## 0. Batas fase M06

M06 **mengekstrak dan mendokumentasikan**, bukan mendesain ulang. Semua angka di
bawah adalah hasil pengukuran atas kode yang sudah ada, bukan target yang
diinginkan. Dua konsekuensinya:

- Tidak ada perubahan tampilan web. Acceptance criteria M06 justru menuntut itu
  (build hash stabil).
- Cacat visual yang ditemukan **dicatat, tidak diperbaiki**. Memperbaikinya
  berarti mengubah tampilan, dan itu butuh keputusan sadar di M07/M08.

Semuanya ada di [§11 Utang yang diketahui](#11-utang-yang-diketahui).

---

## 1. Arsitektur: tiga sumber, satu komposisi

Ini bagian yang paling sering disalahpahami, jadi ditulis lebih dulu.

```
database.THEMES  (Python)          12 palet x 16 field  <-- SUMBER KEBENARAN WARNA
        |
        |  applyTheme()  [web/src/utils/theme.ts:30]
        v  menyalin 15 field warna + --ct-theme, lalu set data-theme="<key>"
index.css  :root                   40 token             <-- DEFAULT + STRUKTURAL
index.css  @property (11)          initial-value        <-- bikin warna bisa dianimasikan
index.css  [data-theme="x"]        8 token unik         <-- ATMOSFER per tema
index.css  [data-theme="x"] .ct-amb                     <-- TUNING LED per tema
```

Yang penting dipahami:

1. **Warna tema tidak datang dari CSS.** `:root` hanya memuat salinan
   `modern_dark` sebagai nilai awal. Palet sebenarnya disuntikkan saat runtime
   oleh `applyTheme()`. Karena itu mengedit `:root` **tidak** mengubah tema apa
   pun — yang berubah cuma kilatan sebelum tema terpasang.
2. **`modern_dark` tidak punya blok `[data-theme]`.** Bukan cacat: `:root`
   *adalah* `modern_dark`. 11 tema lain punya blok.
3. **Blok tema ada dua bentuk** dan hanya mengambil yang pertama akan
   kehilangan sebagian besar token: `[data-theme="x"] { … }` untuk atmosfer,
   `[data-theme="x"] .ct-amb { … }` untuk LED.
4. **Android membaca `tokens.json`, bukan CSS.** File itu sudah memuat 12 palet
   lengkap dalam hex, jadi tidak perlu parsing CSS di build Gradle.

---

## 2. Token

| Kelompok | Jumlah | Sumber |
|---|---|---|
| Token di `:root` | **40** | `index.css` |
| Token unik di seluruh CSS | **55** | `index.css` |
| Registrasi `@property` | **11** | `index.css` |
| Tema | **12** × **16** field | `database.THEMES` |
| Token atmosfer unik per tema | **8** | blok `[data-theme]` |
| Class `.ct-*` | **275** dalam **92** kelompok | `index.css` |

Selisih 40 → 55 bukan duplikasi. 15 token tambahan hanya dideklarasikan di
scope-nya sendiri: `--ct-amb-*` (7), `--ct-nlm-*` (6), `--ct-sig-tone`,
`--ct-stem`. Itu sah — custom property memang boleh di-scope ke class.

### 2.1 Palet (16 field × 12 tema)

`primary` `light` `bg` `bg2` `bg3` `panel` `border` `accent` `accent2` `accent3`
`glow` `text` `muted` `on_primary` `on_accent` `label`

`label` adalah nama tampilan (mis. `🌸 Sakura`), **bukan** warna — karena itu
`applyTheme()` sengaja tidak menyalinnya ke CSS var.

12 tema: `ancient_city` `desert` `graphite` `modern_dark` `modern_light`
`nether` `ocean` `overworld` `royal` `sakura` `sunflower` `the_end`

`panel` dan `border` memakai `rgba()`, bukan hex — Android perlu
`Color.parseColor` dengan alpha, atau konversi ke `#AARRGGBB`.

### 2.2 Radius — skala 5 tingkat yang nyata

| Token | rem | **dp** |
|---|---|---|
| `--ct-r-sm` | 0.625 | **10** |
| `--ct-r-md` | 0.875 | **14** |
| `--ct-r-lg` | 1.125 | **18** |
| `--ct-r-xl` | 1.375 | **22** |
| `--ct-r-2xl` | 1.625 | **26** |

Langkahnya **+4 dp seragam** (10/14/18/22/26). Ini satu-satunya skala numerik di
sistem yang benar-benar konsisten — pertahankan.

### 2.3 Gerak

Kurva (3, masing-masing punya karakter):

| Token | Nilai | Pakai untuk |
|---|---|---|
| `--ct-ease` | `cubic-bezier(0.22, 1, 0.36, 1)` | keluar/masuk standar (out-quint) |
| `--ct-ease-spring` | `cubic-bezier(0.34, 1.56, 0.64, 1)` | overshoot: dialog pop, reward |
| `--ct-ease-inout` | `cubic-bezier(0.65, 0, 0.35, 1)` | transisi simetris (flip, geser) |

Durasi (4, sengaja berjarak — bukan satu angka):

| Token | Nilai |
|---|---|
| `--ct-t-fast` | 140ms |
| `--ct-t-med` | 240ms |
| `--ct-t-slow` | 420ms |
| `--ct-t-xslow` | 700ms |

**Android:** `cubic-bezier(0.22,1,0.36,1)` ≈ `FastOutSlowInInterpolator` tapi
tidak identik — pakai `PathInterpolator(0.22f, 1f, 0.36f, 1f)` supaya sama persis.

Semua animasi ambient sudah punya jalur `@media (prefers-reduced-motion: reduce)`
yang mematikannya (P9). Android harus menyamai lewat
`Settings.Global.ANIMATOR_DURATION_SCALE == 0`.

### 2.4 Elevasi

Tiga tingkat, masing-masing **tiga lapis** (bayangan dekat + jauh + inset
highlight 1px di atas). Inset itulah yang membuatnya terasa "terangkat", bukan
flat.

| Token | Komposisi |
|---|---|
| `--ct-elev-1` | `0 1px 2px` + `0 2px 6px` + inset `0 1px 0` 5% putih |
| `--ct-elev-2` | `0 2px 4px` + `0 6px 16px` + inset 6% |
| `--ct-elev-3` | `0 4px 10px` + `0 14px 36px` + inset 7% |
| `--ct-elev-glow` | halo `color-mix(accent 55%)` — untuk fokus/aktif |

**Android:** `elevation` Material tidak punya inset highlight. Jangan dipetakan
1:1 — tambahkan `foreground` berupa gradient 1px di tepi atas, atau hasilnya
terlihat lebih datar dari web.

### 2.5 Tipografi — **belum** menjadi skala

Diukur apa adanya, bukan dirapikan: **30 ukuran font berbeda**, satuan campur.

```
rem : 0.625  0.65  0.7  0.72  0.75  0.8125  0.95  1.28  1.35  1.625  2.6
px  : 8  9  9.5  10  10.5  11  11.5  12  13  13.5  15  19  22  26  34  44  56  64
```

Tidak ada rasio yang konsisten, dan ada nilai setengah piksel (9.5, 10.5, 13.5)
yang di Android akan menghasilkan pembulatan berbeda per kepadatan layar.

Berat hanya tiga: **700 / 800 / 900**. Tidak ada 400/500/600 — seluruh UI ini
memang berani dan tebal, itu bagian identitasnya.

Letter-spacing: `-0.018em` `-0.01em` `0.01em` … `0.06em` (negatif untuk judul
besar, positif untuk label kecil huruf kapital — pola yang benar, hanya belum
ditokenkan).

Font: system stack, **tanpa webfont** (offline-safe, P1):
`--ct-font-sans` (Segoe UI Variable Text → Inter → Roboto → system-ui) ·
`--ct-font-display` (Segoe UI Variable Display) · `--ct-font-mono` (Cascadia Code).

> **Usulan untuk M07/M08**, belum diterapkan: rapikan ke 7 tingkat
> 12/14/16/20/26/34/48 sp dengan rasio ~1.25, buang nilai setengah piksel.
> Jangan dilakukan di M06 — mengubah ukuran teks = mengubah tampilan.

### 2.6 Spacing — **belum** menjadi skala

Nilai yang terpakai: `0.25 0.35 0.375 0.5 0.55 0.6 0.8 1.1 2.2 2.5 rem`.
Tidak bertangga. Usulan M07/M08: skala 4dp (4/8/12/16/24/32/48).

---

## 3. Inventaris komponen (275 class → Android)

Pengelompokan otomatis ada di `tokens.json → classGroups`. Pemetaan ke komponen
native di bawah ini adalah keputusan desain, bukan hasil ekstraksi.

| Kelompok | Class | Komponen Android | Catatan |
|---|---|---|---|
| `sig` | 52 | `SignatureHeader` | **SignatureKit — lihat §4** |
| `nlm` | 19 | `NeumorphicCard` `RailButton` `ChatBubble` | gaya neumorphic, bukan Material |
| `amb` | 17 | `AmbientLedFrame` | LED perimeter; 3 mode × 12 tema × per halaman |
| `btn` | 13 | `CtButton` (varian: danger/ghost/glow/gold/icon) | |
| `craft` | 13 | `CraftingGrid` | |
| `arena` | 8 | `BattleArena` | termasuk `is-win` |
| `forge` | 7 | `ForgeStage` | animasi anvil/palu/percikan |
| `diff` | 6 | `DifficultyChip` (trivial→epic) | |
| `rank` | 6 | `RankBadge` | |
| `fin` | 5 | `FinanceTile` (income/expense/net) | |
| `flip` | 5 | `FlipCard` | butuh `cameraDistance` |
| `frame` | 5 | `RarityFrame` (common→mythic) | |
| `bar` | 4 | `StatBar` (HP/MP/XP) | `bar-low` untuk kondisi kritis |
| `nav` | 4 | `BottomNav` + `nav-pill` | **target sentuh, lihat §5** |
| `scene` | 4 | `SceneBackdrop` (aurora/grain/orbs) | lapisan atmosfer |
| `tab` | 4 | `SegmentedTab` | |
| `bubble` | 3 | `ChatBubble` | self/other |
| `card` | 3 | `CtCard` | `card-hover` tidak ada padanan sentuh → ganti ripple |
| `chart` | 3 | `ChartTooltip` | |
| `podium` | 3 | `LeaderboardPodium` | |
| `pomo` | 3 | `PomodoroDial` | |
| sisanya (71 kelompok × 1–2 class) | 98 | per-fitur | lihat `classGroups` |

`card-hover` dan `sheen` adalah efek **hover**, yang tidak ada di layar sentuh.
Jangan dipaksa — padanannya adalah ripple + state pressed.

---

## 4. SignatureKit: dipertahankan, bukan diratakan

SignatureKit adalah identitas per halaman dari v1.7.2 "Signature & Spectrum":
emblem, judul display, dan strip pola (`peaks` `grid` `circuit` `orbit` `dots`
`wave`). Dengan **52 class unik** ia kelompok terbesar di seluruh sistem —
lebih besar dari `btn` (13) atau `card` (3).

**Aturan M06: jangan diratakan ke Material default.** Menyeragamkannya akan
menghapus satu-satunya pembeda antar halaman, dan itu persis "generic AI UI"
yang ingin dihindari.

Catatan implementasi: `--ct-sig-seg` **tidak** dideklarasikan di CSS. Ia
di-set dari inline style di `SignatureKit.tsx:229`
(`['--ct-sig-seg']: segmented || 10`). Sah, tapi berarti token ini tidak akan
muncul di `tokens.json` sebagai nilai — Android harus menerimanya sebagai
parameter komponen, bukan token.

Tes `test_signaturekit_is_the_largest_group_and_stays_distinct` mengunci ini:
kalau kelompok `sig` menyusut di bawah 50 class, ada yang diam-diam diratakan.

---

## 5. Varian `is-*`

Konvensi `is-row` / `is-sm` (§8.5 roadmap) diukur, dan ternyata sudah berkembang
menjadi sistem modifier status yang lebih luas: **18 varian pada 10 class**.

| Class | Varian |
|---|---|
| `.ct-dmg-float` | `is-crit` `is-deal` `is-heal` `is-take` |
| `.ct-nlm-railbtn` | `is-active` `is-row` `is-sm` |
| `.ct-arena-msg` | `is-win` |
| `.ct-eq` | `is-playing` |
| `.ct-flip-scene` | `is-flipped` |
| 5 class lain | 1 varian masing-masing |

**Aturan:** `is-*` = status (Boolean, bisa beberapa sekaligus). Untuk varian
tunggal yang saling eksklusif, CSS ini memakai BEM `--` (mis.
`sig-badge--accent`, `frame-epic`). **Jangan campur keduanya.**

**Android:** `is-*` → `state` pada Compose (`Modifier.then(if (active) … else …)`);
`--` → enum varian pada parameter komponen.

---

## 6. Aksesibilitas

Ambang diwarisi dari gate v1.7.4: kontras ≥ 4,5:1 · `focus-visible` ·
`prefers-reduced-motion` · teks tanpa clipping · **target sentuh ≥ 48 dp**.

Semua angka kontras di bawah **dihitung** oleh `tests/test_m06_design_tokens.py`
dari nilai hex nyata, bukan diperkirakan.

### 6.1 Yang lolos

| Pasangan | Ambang | Hasil 12 tema |
|---|---|---|
| `text` / `bg` | 4,5:1 | **12/12 lolos** |
| `muted` / `bg` | 3:1 (teks besar) | **12/12 lolos** |
| `on_primary` / `primary` | 4,5:1 | **12/12 lolos** (utang M06 dibayar di M13, 2026-10-23) |

### 6.2 `focus-visible` dan reduced-motion

- `focus-visible`: dipakai, plus `--ct-elev-glow` sebagai cincin fokus.
- `prefers-reduced-motion`: ada dua jalur — blok `@media (prefers-reduced-motion:
  no-preference)` yang *mengaktifkan* transisi warna, dan `reduce` yang mematikan
  animasi ambient. Karena transisi warna hanya aktif di `no-preference`,
  pengguna yang meminta reduced-motion tidak mendapat animasi sama sekali. Itu
  benar, dan harus ditiru di Android.

### 6.3 Target sentuh ≥ 48 dp — **belum diverifikasi**

Ini ambang **baru** di M06 (tidak ada di web, karena web pakai kursor). Tidak ada
satu pun class `.ct-*` yang mendeklarasikan tinggi minimum 48px/dp, jadi
klaim "lulus" **tidak bisa dibuat sekarang**. Yang bisa dipastikan: `.ct-nav-item`
dan `.ct-btn-icon` adalah kandidat paling berisiko karena ukurannya rapat.

Verifikasi sesungguhnya baru mungkin di M07, saat komponen native benar-benar
ada dan bisa diukur. Dicatat sebagai pekerjaan terbuka, bukan diklaim lulus.

---

## 7. Cara memakai `tokens.json`

```jsonc
{
  "version": "1.7.4",
  "meta": { "rootTokens": 40, "themes": 12, "classes": 275, … },
  "themes": { "sakura": { "primary": "#ec4899", "on_primary": "#4c0519", … } },
  "structural": { "--ct-r-sm": "0.625rem", "--ct-ease": "cubic-bezier(…)", … },
  "property": { "--ct-primary": { "syntax": "<color>", "inherits": true, … } },
  "atmosphere": { "nether": { "--ct-grain-o": "0.05", … } },
  "classes": [ …275… ],
  "classGroups": { "sig": […52…], … },
  "variants": { "implemented": { ".ct-nlm-railbtn": ["is-active","is-row","is-sm"] } },
  "audit": { "problems": [], "warnings": [ …2… ] }
}
```

Nilai `structural` masih berupa string CSS (`0.625rem`). Konversi ke dp/sp ada
di sisi konsumen — tabel §2.2 adalah acuannya — supaya file ini tetap bebas dari
asumsi platform.

**Regenerasi:**

```bash
python3 scripts/export_design_tokens.py           # tulis tokens.json
python3 scripts/export_design_tokens.py --check   # exit 1 kalau drift
python3 scripts/export_design_tokens.py --report  # ringkasan + deviasi
```

Jalankan setelah mengubah `database.THEMES`, `index.css`, atau `theme.ts`.
`--check` juga dijalankan oleh `tests/test_m06_design_tokens.py`, jadi drift
tidak bisa lolos diam-diam.

---

## 8. Apa yang M06 buktikan

| Acceptance criteria | Bukti |
|---|---|
| `DESIGN.md` ada dan 12 tema terpetakan lengkap | dokumen ini; `test_twelve_themes_each_with_a_full_palette` memverifikasi 12 tema × 16 field, semua terisi |
| Token JSON dikonsumsi tanpa perubahan visual | `git status` menunjukkan `web/src/index.css` **tidak tersentuh**; M06 hanya menambah file baru |

Yang kedua perlu ditegaskan: M06 **tidak** menghasilkan perubahan visual karena
tidak mengedit CSS sama sekali. `tokens.json` adalah artefak turunan yang
dijaga sinkron oleh `--check`, bukan masukan yang di-generate ke CSS.

Keputusan ini sadar. Alternatifnya — membuat `index.css` di-generate dari JSON —
menyentuh file yang menentukan tampilan seluruh aplikasi demi keuntungan yang
belum dibutuhkan sampai M07. Kalau nanti Android benar-benar butuh CSS ikut
ter-generate, itu perubahan terpisah dengan risikonya sendiri.

---

## 9. Yang belum dikerjakan M06

- Type scale dan spacing belum ditokenkan (§2.5, §2.6) — butuh perubahan visual.
- Target sentuh ≥48 dp belum terverifikasi (§6.3) — butuh komponen native.
- Utang kontras 5 tema (§11) — butuh keputusan warna.
- Pemetaan komponen §3 masih tabel, belum komponen Android nyata (itu M07).

---

## 11. Utang yang diketahui

Ditemukan saat M06, **sengaja tidak diperbaiki**, semuanya dikunci oleh tes.
(§11.1 sudah LUNAS di M13 — lihat catatan di bawahnya.)

### 11.1 Lima tema di bawah kontras 4,5:1 (`on_primary` di atas `primary`) — ✅ LUNAS di M13 (2026-10-23)

Perbaikan: warna `primary`/`accent` digelapkan 6–12% (sakura: `on_primary`
digelapkan) sampai semua pasangan ≥ 4,5:1 — modern_dark `#8b5cf6→#8256e7`,
nether `#ef4444→#d23b3b`, the_end `#a855f7→#974cde`, ancient_city
`#0d9488→#0ea295` (diterangkan, teksnya gelap), modern_light accent
`#0891b2→#077f9c`, sakura on_primary `#4c0519→#440416`. Dikunci oleh
`tests/test_m06_design_tokens.py` (daftar utang sekarang kosong dan wajib
tetap kosong) + `CraftLife-Android/tests/a11y.test.ts`.

| Tema | Rasio | `on_primary` | `primary` |
|---|---|---|---|
| `nether` | **3,76** | `#ffffff` | `#ef4444` |
| `ancient_city` | **3,93** | `#032e2a` | `#0d9488` |
| `the_end` | **3,96** | `#ffffff` | `#a855f7` |
| `modern_dark` | **4,23** | `#ffffff` | `#8b5cf6` |
| `sakura` | **4,43** | `#4c0519` | `#ec4899` |

`modern_dark` adalah tema **default**, jadi ini yang paling sering terlihat.
Dikunci oleh `test_known_contrast_debt_is_pinned_and_documented` — kalau ada
warna yang diedit, tes akan menyebutnya, sehingga perbaikannya jadi keputusan
sadar dan bukan efek samping.

### 11.2 `--ct-t` dipakai 10 kali, tidak pernah dideklarasikan

`transition: var(--ct-t) var(--ct-ease)` muncul 10 kali di `index.css`, tapi
`--ct-t` tidak didefinisikan di mana pun — yang ada `--ct-t-fast/med/slow/xslow`.
Akibatnya deklarasi `transition` itu tidak berlaku dan elemen terkait **tidak
beranimasi**.

Memberi nilai pada `--ct-t` akan menghidupkan 10 animasi yang selama ini mati.
Itu perubahan tampilan, jadi di luar izin M06.

### 11.3 Paritas `:root` vs `db.THEMES['modern_dark']` melenceng di 5 nilai

| Token | CSS `:root` | `db.THEMES` |
|---|---|---|
| `--ct-bg` | `#0b0b16` | `#0a0a14` |
| `--ct-bg2` | `#14122c` | `#131129` |
| `--ct-bg3` | `#0c1a26` | `#0b1824` |
| `--ct-accent3` | `#22d3ee` | `#34d399` |
| `--ct-muted` | `#9b9fc4` | `#a0a4c8` |

Komentar di `index.css` mengklaim paritas, tapi sudah melenceng. Efeknya kecil:
`applyTheme()` menimpa semuanya saat runtime, jadi yang terlihat cuma kilatan
warna sesaat sebelum tema terpasang. `--ct-accent3` yang paling berbeda
(cyan vs hijau) dan layak dicek lebih dulu.

---

*Diperbarui saat M06. Angka di dokumen ini dihasilkan dari pengukuran; jalankan
`python3 scripts/export_design_tokens.py --report` untuk memverifikasi ulang.*
