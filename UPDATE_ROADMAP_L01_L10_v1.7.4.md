# UPDATE ROADMAP — v1.7.4 (L01–L10) "Gacha & Glow"

> Versi: **v1.7.4** (v1.7.3 dilewati dengan sengaja — nomor mengikuti rencana
> update). Titik awal: tag `v1.7.2` (commit `c244b78`). Batas keras: hanya
> menambah/memodifikasi — tidak mengurangi fitur, logika game, sistem, atau
> fungsi yang sudah ada. Skill repo ke-6 ikut dipakai: **UI/UX Pro Max**
> (checklist pra-deliverinya masuk gate: kontras ≥4.5:1, focus-visible,
> prefers-reduced-motion, resilient text tanpa clipping, cursor-pointer).

## Hasil audit (fakta kode saat roadmap ditulis)

| Area | Temuan |
|---|---|
| Food DB | `food_data.py` → `DEFAULT_FOODS` tuple `(nama_id, nama_en, icon, kal, protein, karbo, lemak)`; **874 entri, 0 duplikat**; tabel `food_items` diseed otomatis |
| Pets | `PETS_DATA` = **25 pets** (cost/bonus/base_buff: xp_pct, gold_pct, hp_reduc, boss_dmg…); tabel `user_pets` (level/exp/hunger/happiness/is_active); adopt/feed/train ada; **belum ada rank/rarity, belum ada skill aktif, beli via shop** |
| Redeem | `redeem_codes` + `migrate_redeem_codes()`; **20 kode ada** (1 admin + 19 reward: xp/gold/item) |
| Achievements | `migrate_achievements()` + log server "Migrated 64 achievements" → **64 ada** |
| Notes bug | `expanded[id] !== false` → undefined dianggap TERBUKA; Expand-all pakai `tree` (hanya root) & Collapse-all `setExpanded({})` = dua-duanya **no-op/dead code** |
| Toast duplikat | `showToast` tanpa dedup (hanya `notifyApiErr` yang dedup 4s); `React.StrictMode` aktif di dev; audit call-site ganda diperlukan |
| Chart tooltip | `ct-chart-tip` transform `translate(-50%,-100%-10px)` → titik maksimum dekat tepi atas **terpotong** oleh overflow container |
| Kontras tema | belum ada token teks-di-atas-aksen; beberapa tombol/tema membuat teks "tenggelam" |
| Skill repo | 6 repo aktif: taste-skill, vercel web-design-guidelines, awesome-design, playwright-cli, (I03-grounding lama), **+ UI/UX Pro Max** |

## Keputusan terkunci (K)

| # | Keputusan |
|---|---|
| K1 | Versi **v1.7.4**; satu tag di akhir; commit per fase |
| K2 | **Pets via SPIN (gacha)** menggantikan pembelian langsung di shop. Pet yang sudah dimiliki tetap aman (tidak ada penghapusan). Spin memakai **Gold**; hasil duplikat dikonversi jadi **EXP latih** pet sejenis yang sudah dimiliki, atau refund Gold 50% bila belum dimiliki |
| K3 | Rank pets: **Common · Rare · Epic · Legendary · Mythic** + tipe khusus **SECRET** (dari redeem code & peluang spin terkecil). Semua 25 pet lama dipetakan ke rank; pet baru ditambahkan lintas rank (termasuk ≥2 Secret) |
| K4 | Peluang dasar spin (ditampilkan di UI): Common 34% · Rare 26% · Epic 18% · Legendary 12% · Mythic 8% · Secret 2%. **Pity**: tiap 10 spin tanpa Epic+ → jaminan Epic+; tiap 30 spin tanpa Legendary+ → jaminan Legendary+; counter reset saat dapat ≥ tier jaminan |
| K5 | **Skill aktif pet**: hanya Legendary/Mythic/Secret. Memakai **MP user**, cooldown per skill, kekuatan skill berskala **level pet**. Efek memakai kosakata buff yang sudah ada (xp_pct, gold_pct, boss_dmg, hp_reduc, mp_bonus…) |
| K6 | **Latih pet dirombak**: EXP latih = rentang acak berbasis rank (higher rank = rentang lebih besar), harga latih naikตาม level & rank; rumus hanya di `database.py` (single source of truth) |
| K7 | **LED strip**: komponen `LedStrip` + CSS `.ct-led-*`; varian signature per halaman (24 view) × adaptasi 12 tema via token (--ct-primary/accent/glow). Animasi: boot-sequence saat masuk halaman + pulse pada event (task selesai, naik level, spin), lalu **diam** — tanpa animasi paint idle (P42); hormati reduced-motion |
| K8 | **Kontras teks**: token baru aditif `on_primary` & `on_accent` di setiap entri THEMES (kontrak 13 kunci lama tetap utuh — PyQt abaikan kunci ekstra); audit semua tombol/badge di 12 tema |
| K9 | **Chart tooltip anti-potong**: tooltip flip ke bawah bila dekat tepi atas, clamp horizontal di dalam container (charts.tsx) |
| K10 | **Dedup pop-up**: jendela dedup 1.5s untuk title+message identik di `showToast` + audit akar-penyebab call-site ganda di semua view/dialog |
| K11 | **3 kode redeem baru**: 1 × pet SECRET, 1 × Gold besar, 1 × item langka; semua idempoten via pola `migrate_redeem_codes()` |
| K12 | **10 achievement baru** (kategori baru: spin/gacha, pet skill, kolektor rank, dsb.) + terjemahan ID/EN, tanpa duplikasi dengan 64 yang ada |
| K13 | **Notes**: collapse/expand diperbaiki dengan state eksplisit seluruh ID folder (walk rekursif); **checkpoint** posisi collapse/expand disimpan di localStorage (local-first, tanpa migrasi skema); **search folder** baru; baris folder diperbesar |
| K14 | **+100 makanan & +100 minuman** di `food_data.py` (tuple bilingual, makro per sajian sesuai fakta gizi), cek anti-duplikat terhadap 874 entri |
| K15 | Item **direbalance** + sistem **enchant** dapat sub-tab interaktif gaya "anvil" (murni menambah/memoles; jalur enchant lama tetap berfungsi) |

## Fase

| Fase | Isi |
|---|---|
| **L01** | Bug batch: (a) Notes collapse/expand + checkpoint + search folder + layout folder besar; (b) chart tooltip max-value clipping; (c) dedup toast + audit call-site ganda; (d) token `on_primary/on_accent` + audit kontras tombol 12 tema |
| **L02** | Food DB +200 (100 makanan + 100 minuman) bilingual, fakta gizi, tanpa duplikat |
| **L03** | 3 redeem code baru + 10 achievement baru + i18n ID/EN; list semua kode diberikan di chat |
| **L04** | LED strip system: komponen + CSS + 24 varian halaman + adaptasi 12 tema + integrasi PageSignature |
| **L05** | Backend Pet v2: rank semua pet, pet baru (incl. Secret), endpoint spin + peluang + pity, konversi duplikat, rombak latih (EXP acak + harga rank), skill aktif (MP/cooldown/level-scale), rebalance stats pet, endpoint pet-book |
| **L06** | Frontend Pet v2: UI spin animatif + tabel peluang + pity meter, buku pets, tombol skill, UI latih baru; halaman Pets direkonstruksi gaya arena Pokémon (referensi Boss Arena) |
| **L07** | Rebalance items + sub-tab enchant gaya anvil (fun, animatif, jelas) |
| **L08** | Interactivity pass: Guild (dashboard modern/pro), Leaderboard, Achievements, Friends — animasi, perilaku klik variatif, signature |
| **L09** | Audit i18n menyeluruh: toast/dialog/popup yang belum ID/EN disapu bersih |
| **L10** | Finalisasi: `updater.py` → 1.7.4, RELEASE_NOTES_v1.7.4.md (English), README, gate penuh, tag `v1.7.4` |

## Gate wajib (per fase)

`python3 -m py_compile` modul terkait · `cd web && ./node_modules/.bin/tsc --noEmit` (0 error) ·
`./node_modules/.bin/vite build` (catat hash+size) · `python3 scripts/export_i18n.py` + copy
`web/public/i18n/messages.json` bila ada kunci baru · live-test `:8899` · tree bersih.

**Checklist UI/UX Pro Max (pra-deliveri setiap fase UI):** kontras ≥4.5:1 per tema ·
focus-visible keyboard · prefers-reduced-motion · teks/chip/badge tidak clipping ·
cursor-pointer di elemen klik · timing animasi konsisten.
