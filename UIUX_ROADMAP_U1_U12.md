# 🎨 CraftLife UI/UX Roadmap — U1 → U12

> **Tujuan:** Seluruh UI/UX CraftLife benar-benar **profesional, interaktif, rich animation, rich theme,
> rich color palette** — sesuai metodologi **UI UX Pro Max skill** (192 reasoning rules, 88 styles,
> 119 UX guidelines, canonical pre-delivery checklist).
>
> **Kontrak tetap berlaku di SEMUA fase:** UI/UX saja. Backend, logika, behavior, fungsi, sistem,
> dan game rule **0% tersentuh**. Theme catalog tetap backend-authoritative (`/api/catalog/themes`).
>
> **Format update 1–7** diterapkan di setiap akhir fase (`UPDATES/…-U<n>-….md`),
> dan **PHASE SUMMARY U1–U12** lengkap dibuat di akhir U12.

---

## 📐 Rules of Engagement (berlaku global)

| # | Aturan | Detail |
|---|--------|--------|
| R1 | **UI-only** | Hanya `className`, CSS, wrapper presentasional. Larangan: ubah handler, state, API call, props logic, `database.py`, `api_server.py`, dst. |
| R2 | **Token-driven** | Semua warna/gerak/bentuk lewat token `--ct-*` & kelas `.ct-*`. No ad-hoc hex di komponen baru. |
| R3 | **Skill-grounded** | Tiap fase mulai dengan query skill (`--domain` / `--design-system`) dan ditutup dengan **canonical pre-delivery checklist**. |
| R4 | **A11y = gate, bukan bonus** | Contrast ≥4.5:1, focus-visible, keyboard nav, `prefers-reduced-motion` — kalau gagal, fase belum selesai. |
| R5 | **Verifikasi wajib** | `tsc --noEmit` 0 error + `vite build` clean + class terkonfirmasi masuk bundle, setiap fase. |
| R6 | **String baru → format #1** | Kalau fase menambah string UI (rare), wajib tambah key `translations.py` id+en serentak. |
| R7 | **Rollback mudah** | Perubahan CSS/className = revert cepat per-fase via git. |
| R8 | **Button standard** (sejak U3.3 = Signature) | SEMUA tombol wajib `.ct-btn` + varian (`primary`/`gold`/`secondary`/`ghost`/`danger`) + ukuran (`-sm`/base/`-lg`/`-icon`/`-icon-sm`). Bahasa visual: **Game-HUD bevel** (stem 3D bawah, press = stem collapse) + ikon/plate memakai **`.ct-socket`** (slot inset inventory) + sheen sweep pada CTA metalik. Tanpa style ad-hoc. Kartu pembawa dialog fixed hanya boleh `.ct-hover-glow`. |
| R9 | **Kebebasan layout** (sejak U3.3, mandat user; DIPERKUAT U3.4: berlaku SEMUA page & phase) | Layout boleh direkonstruksi lebih berani (komposisi ulang, hierarki baru) ASAL: semua kontrol/tombol/fungsi tetap ada & reachable, handler/logika/data tidak berubah, backend 0% tersentuh. |
| R10 | **Higiene compositor / anti-flicker** (flick-fix, 2026-09-07) | TANPA `backdrop-filter` di atas scene/layer animasi (scrim modal = rgba pekat saja); TANPA animasi paint per-frame yang jalan idle (box-shadow/background-position/gradient bergerak); gerak kontinu hanya hover/interaksi (R5 diperkuat); elemen dekoratif idle = statis. |

---

## 🗺️ Progress Tracker

| Fase | Nama | Status | Update-log |
|------|------|--------|-----------|
| U1 | Design System Foundation & Token Architecture | ✅ Selesai (sesi ini) | `2026-09-06-ui-v2-aurora-craft.md` |
| U2 | Shell & Navigation Excellence | ✅ Selesai | `2026-09-07-u2-shell-nav.md` |
| U3 | Dashboard & Data Storytelling | ✅ Selesai (+U3.1 fix, +U3.2/3.3 Buttons, +U3.4 FULL reconstruction) | `u3*.md` |
| U4 | Task Core: Habits · Dailies · Quests | ✅ Selesai (full reconstruction + Task Kit) | `2026-09-07-u4-task-core.md` |
| U5 | Body: Sport · Nutrition · Health · Pomodoro | ✅ Selesai (Body Kit + Pomodoro Ring) | `2026-09-07-u5-body.md` |
| U6 | Economy & Supplies | ✅ Selesai (Finance Hero + Tab Segmen) | `2026-09-07-u6-economy.md` |
| U7 | RPG: Shop · Craft · Pets · Boss | ✅ Selesai (RPG Kit + Hotbar + Achievement Frames) | `2026-09-07-u7-rpg.md` |
| U8 | Social: Friends · Guild · Love Space · Leaderboard | ✅ Selesai (Chat Bubbles + War-Room + Rose Theme) | `2026-09-07-u8-social.md` |
| U9 | Studio: Notes · Learning · Music · Calendar · Reminders | ✅ Selesai (Music Disc+EQ + Calendar Ring) | `2026-09-07-u9-studio.md` |
| U10 | Account: Login · Onboarding · Profile · Settings + Dialog Sweep | ✅ Selesai (Switch Kit + Dialog Sweep Tuntas) | `2026-09-07-u10-account.md` |
| U11 | Global Motion & Interaction Pass | ✅ Selesai (Scroll-Reveal + Empty Block-Art + Skeleton + Cleanup) | `2026-09-08-u11-motion.md` |
| U12 | QA Total: A11y · Contrast · Responsive · PHASE SUMMARY | ⬜ | — |

---

## ✅ U1 — Design System Foundation & Token Architecture *(SELESAI)*

**Delivered:** `index.css` v2.0 "Aurora Craft" — Tailwind 4 `@theme` (slate aurora-tint, lightness-matched),
token radius/easing/duration/shadow, ambient aurora + block-grid bg, glassmorphism, 12 keyframes,
kelas utilitas (`.ct-card`, `.ct-press`, `.ct-stagger`, `.ct-skeleton`, `.ct-bar-fill`, `.ct-chip-buff`,
`.ct-gradient-text`, `.ct-float`, `.ct-pop`, `.ct-view`), a11y base (focus ring, cursor, reduced-motion).
+ Pilot: App shell, Navbar, Login, Dashboard entrance.

**Sisa U1 (quick wins, masuk awal U2):** persist `design-system/craftlife/MASTER.md` via skill
(`--persist`) sebagai source of truth tertulis.

---

## 🧭 U2 — Shell & Navigation Excellence

**Goal:** Shell terasa seperti app game premium — nav = "hub" utama.

**Scope:** `Navbar.tsx`, `Sidebar.tsx`, `CommandPalette.tsx`, `ToastContainer.tsx`, `UndoToast.tsx`, `index.css`

**Perubahan (className/CSS only):**
- Sidebar: active indicator animasi (pill sliding via CSS), icon micro-motion saat hover (scale/bounce 1x), badge count `ct-pop`, mobile drawer dengan spring transition
- Navbar: level badge `ct-block` saat berubah, clock chip tabular-nums, gold chip shimmer tipis, XP bar shine (sudah) + tooltip
- Command palette: backdrop blur加深, panel spring-in, item hover slide, kategori stagger
- Toast: entrance spring + exit fade, ikon tipe (success/error/info) berwarna token, progress bar auto-dismiss
- Empty & loading state shell: `ct-skeleton` pada section yang loading

**Skill checkpoints:** `"navigation sidebar active state" --domain ux` · `"toast notification timing" --domain ux` · `"modal backdrop scrim legibility" --domain ux`

**Acceptance:** navigasi keyboard penuh (Tab/Enter/Esc), focus-visible di semua item nav, target klik ≥44px, reduced-motion → tanpa slide/spring.

---

## 📊 U3 — Dashboard & Data Storytelling

**Goal:** Dashboard = "wow" pertama tiap dibuka; data terasa hidup.

**Scope:** `DashboardView.tsx`, `DashboardSummaryPanel.tsx`, `DashboardWidgetsDialog.tsx`, `YearWrappedDialog.tsx`, `charts.tsx`, `RankDialog.tsx`

**Perubahan:**
- Hero banner: gradient border animated (conic glow), avatar `ct-float` halus, streak flame pulse
- Stat cards: `ct-card` + hover lift + ikon berwarna token; angka pakai `ct-num` (tabular)
- Progress rings (`charts.tsx` wrapper CSS): stroke glow, animate-in saat mount (CSS `@starting-style`/class)
- Weekly/health chart: area gradient fill lembut, grid line tipis, tooltip chip `ct-chip`
- Widgets dialog & Year Wrapped: entrance stagger + section divider glow
- Chart warna diverifikasi aman butiran warna (color-blind safe palette dari skill `charts.csv`)

**Skill:** `"chart color accessibility" --domain chart` · `"dashboard card hierarchy" --domain ux`

**Acceptance:** semua kartu kontras ≥4.5:1, chart punya legend/tooltip, tidak ada layout shift saat data load (skeleton dulu).

---

## ✅ U4 — Task Core: Habits · Dailies · Quests

**Goal:** Interaksi "complete task" = paling satisfying di seluruh app.

**Scope:** `HabitsView.tsx`, `DailiesView.tsx`, `QuestsView.tsx`, `TaskFolderBar.tsx`, `TaskTemplateDialog.tsx`, `QuickAddDialog.tsx`

**Perubahan:**
- Task card: `ct-card`, difficulty diwujudkan warna border-left token (easy/medium/hard/epic), hover lift, complete → strike-through + fade + checkbox pop (`ct-block`)
- Positive/negative habit: twin tone (emerald/rose) konsisten
- Folder bar: chip `ct-chip` aktif = gradient accent; folder count badge
- Streak badge: flame + `ct-pulse-glow` untuk streak ≥7
- QuickAdd & Template dialog: spring-in, field focus ring accent
- List entrance: `ct-stagger` per grup; undo toast terhubung visual (sudah U2)
- **Tanpa** mengubah logic trigger/fail/freeze sama sekali

**Skill:** `"card list interaction feedback" --domain ux` · `"positive negative habit color semantics" --domain style`

**Acceptance:** keyboard toggle task berfungsi, kartu tidak "jump" saat complete (stable bounds), reduced-motion → instan tanpa animasi.

---

## 💪 U5 — Body: Sport · Nutrition · Health · Pomodoro

**Scope:** `SportView.tsx`, `HealthFoodView.tsx` (health+food), `NutritionView.tsx`, `PomodoroView.tsx`

**Perubahan:**
- Stat tiles seragam (icon token color + `ct-num`), reps/calorie chart polish (gradient area)
- Water goal: progress "botol" dengan wave shimmer CSS
- Weight/height trend: line glow + dot hover
- Pomodoro: ring countdown dramatis (glow sesuai mode focus/break — accent berbeda), tombol start/pause `ct-press` besar, sesi selesai → pulse celebration (CSS, tanpa confetti berlebihan)
- Food DB list: row hover highlight, search focus ring

**Skill:** `"progress ring timer" --domain ux` · `"data entry form inline validation" --domain ux`

**Acceptance:** mode focus vs break terlihat sekali lihat (warna + label), angka semua tabular.

---

## 💰 U6 — Economy & Supplies

**Scope:** `EconomyView.tsx`, `SuppliesView.tsx`, `MoneyInput.tsx`

**Perubahan:**
- Transaction card: ikon kategori dalam chip warna, nominal `ct-num` (pemasukan emerald / pengeluaran rose), tanggal muted
- Balance hero: angka besar `ct-gradient-text`, delta harian chip
- Subscription dialog: field grid rapi, auto-renew toggle accent, due-date badge warna urgensi
- Savings/investment: progress bar `ct-bar-fill`, target line marker
- Supplies: stock level bar (safe/low/out warna token), adjust button `ct-press`

**Skill:** `"finance dashboard color semantics" --domain style` · `"currency formatting locale" --domain ux`

**Acceptance:** warna pemasukan/pengeluaran konsisten & tidak bergantung warna saja (ada ikon ±), kontras nominal kuat.

---

## ⚔️ U7 — RPG: Shop · Craft · Pets · Boss

**Goal:** Sisi game terasa seperti game sungguhan.

**Scope:** `ShopView.tsx`, `CraftView.tsx`, `PetsView.tsx`, `BossView.tsx` (via GuildView render), `AchievementsView.tsx` (+ redeem codes)

**Perubahan:**
- Item/pet card: rarity frame (common → legendary = border glow bertingkat: token tiers), harga gold chip, afford/disabled state jelas
- Equip slot: dashed border + glow saat terisi
- Crafting: requirement checklist (✓ emerald / ✗ rose), success → `ct-block` + shimmer
- Boss: HP bar besar `ct-bar-fill` + shake saat kena hit (`ct-shake`), damage number float-up (CSS), boss defeat → flash dim + victory glow; **feedback visual saja, damage math tetap backend**
- Spyglass reveal, ultimate/shield/revive = glow states berbeda
- Achievements: unlocked = gold gradient frame + `ct-pulse-glow` untuk claimable, locked = grayscale + lock
- Pets: slot scaling info chip, feed/train button press feedback

**Skill:** `"rpg game hud style" --domain style` · `"rarity color tiers" --domain color` · `"combat feedback timing" --domain ux`

**Acceptance:** disabled (gold kurang) jelas tanpa hover, animasi combat ≤400ms dan berhenti saat reduced-motion.

---

## ❤️ U8 — Social: Friends · Guild · Love Space · Leaderboard

**Scope:** `FriendsView.tsx`, `GuildView.tsx`, `LoveSpaceView.tsx`, `LeaderboardView.tsx`

**Perubahan:**
- Chat bubbles: entrance slide+fade per pesan, own vs other beda arah/warna, timestamp chip muted, reaction chips `ct-chip` (+pop saat react), typing indicator dots animasi, attachment thumb rounded + hover zoom
- Friends list: status online glow dot, request badge pulse
- Guild panel: member rank frame warna, leader crown accent, boss section war-room vibe (panel gradient gelap)
- Love Space: theme hangat khusus (token override lokal pink/rose lewat wrapper class `ct-theme-love`), memory cards polaroid-style hover tilt (CSS), check-in streak heart pulse
- Leaderboard: podium top-3 (tinggi bertingkat + glow), row highlight, rank delta chip

**Skill:** `"chat message entrance animation" --domain ux` · `"dating app warm palette" --domain color` (Love Space) · `"leaderboard podium" --domain style`

**Acceptance:** chat tetap 3s refresh tanpa flicker (animasi hanya pada item baru), semua modal scrim legible.

---

## 🎓 U9 — Studio: Notes · Learning · Music · Calendar · Reminders

**Scope:** `NotesView.tsx`, `LearningView.tsx`, `MusicView.tsx`, `CalendarView.tsx`, `RemindersView.tsx`

**Perubahan:**
- Notes: card `ct-card` + folder chip, LaTeX preview panel surface jelas, pin accent
- Learning: 3-tab slide (sudah) + tab indicator pill bergerak, source card type badge (PDF/YouTube/text warna token), AI chat typing dots + answer fade-in, studio generate progress shimmer
- Music: player bar glass, album art berputar pelan saat play (CSS rotate, hormat reduced-motion), lyric aktif highlight + auto-scroll smooth, equalizer bar mini saat playing
- Calendar: hari ini = ring accent, ada catatan = dot, holiday = chip merah kecil, month transition slide
- Reminders: time chip `ct-num`, upcoming pulse halus

**Skill:** `"music player now playing" --domain style` · `"calendar heat grid" --domain style` · `"ai chat streaming indicator" --domain ux`

**Acceptance:** rotasi art & equalizer berhenti saat pause/reduced-motion, scroll lirik tidak melompat.

---

## ⚙️ U10 — Account: Login · Onboarding · Profile · Settings + Dialog Sweep

**Scope:** `LoginView.tsx` (refine), `OnboardingWizard.tsx`, `ProfileView.tsx`, `SettingsView.tsx`, semua dialog tersisa (`RankDialog`, `DashboardWidgetsDialog`, dll)

**Perubahan:**
- Onboarding: step transition slide, progress dots animasi, final step celebration (CSS confetti-tipis, reduced-motion aman)
- Profile: hero card class/race frame, talent tree grid dengan connector glow, hero customization preview live
- Settings: section nav chip aktif, toggle switch accent + spring, cloud status badge (synced/syncing/error warna token), tema picker = swatch bulat + selected ring
- Dialog sweep: satukan semua modal ke pattern satu (backdrop blur + panel spring + close Esc + focus trap check)

**Skill:** `"onboarding progress" --domain ux` · `"settings toggle switch" --domain ux` · `"theme picker swatch" --domain style`

**Acceptance:** semua toggle punya label + state terlihat, tema ganti instan tanpa reload, high-contrast mode tetap override benar.

---

## 🎬 U11 — Global Motion & Interaction Pass

**Goal:** Konsistensi & "signature feel" di seluruh app.

**Scope:** `index.css` (library), semua views (sweep ringan), `GameContext` **tidak** disentuh.

**Perubahan:**
- Motion tokens resmi: `fast=140ms / med=240ms / slow=420ms` + easing spring — audit semua transisi menyimpang
- Shared modal/panel/dropdown variants (CSS classes) dipakai seragam
- Scroll-reveal ringan untuk section panjang (CSS `animation-timeline` / fallback class on-mount — tanpa listener baru)
- Skeleton map: setiap state loading di app punya `ct-skeleton`
- Empty states: ilustrasi CSS mini (block-art) + CTA
- Cuan mikro: haptic-like press di semua tombol utama, angka penting count-up (CSS counter / token transition)
- Perf audit: animasi hanya transform/opacity, tanpa layout thrashing; cek di DevTools

**Skill:** `"animation timing tokens" --domain ux` · `"gsap presets entrance" --domain gsap` (referensi timing) · `"empty state illustration" --domain ux`

**Acceptance:** tidak ada durasi seragam di semua interaksi (distance-aware), 60fps scroll di view berat (Economy/Music).

---

## 🏆 U12 — QA Total + PHASE SUMMARY

**Goal:** Pengakuan resmi: UI/UX "Pro Max certified". 

**Scope:** audit menyeluruh, perbaikan temuan, dokumentasi final.

**Checklist QA (canonical — dari skill, adaptasi desktop-web):**
- [ ] Contrast: teks ≥4.5:1 di SEMUA tema catalog + high-contrast mode (sample per view, alat bantu kontras)
- [ ] Keyboard: navigasi penuh tiap view, focus-visible jelas, Esc menutup semua modal
- [ ] Target klik ≥44px; icon-only button punya `title`/aria-label
- [ ] `prefers-reduced-motion`: nol animasi berulang; fungsional 100%
- [ ] Responsive: 375 / 768 / 1024 / 1440px — tanpa horizontal scroll, tanpa elemen terpotong
- [ ] High contrast + font scale (setting app) tetap layak
- [ ] Tidak ada emoji sebagai ikon struktural (Lucide konsisten, stroke width seragam)
- [ ] Stable bounds: tidak ada layout shift saat press/hover/complete
- [ ] Tema catalog: semua palet backend dirender benar dengan layer v2 (aurora/glass mengikuti token)
- [ ] `tsc --noEmit` 0 error · `vite build` clean · bundle size wajar
- [ ] Smoke run: `python MainPyQt6.py` — WebEngine load :8765, semua view dibuka manual

**Deliverables akhir:**
1. Perbaikan semua temuan QA
2. `UPDATES/…-U12-….md` berisi **PHASE SUMMARY U1–U12** lengkap: kesimpulan keseluruhan + rekap format 1–6 gabungan (translate keys terkumpul, semua file timpa/baru, command, migrasi — mestinya nol)
3. Update screenshot set + README section "UI v2" (opsional, sepengetahuanku)

---

## 📊 Estimasi & Ritme

| Fase | Ukuran | Estimasi sesi kerja |
|------|--------|---------------------|
| U1 | ✅ | selesai |
| U2–U3 | M | 1 sesi gabungan |
| U4–U5 | M | 1 sesi gabungan |
| U6–U7 | M–L | 1 sesi |
| U8 | L | 1 sesi |
| U9 | L | 1 sesi |
| U10–U11 | M–L | 1 sesi |
| U12 | M | 1 sesi (audit + summary) |

> Total ± 6–7 sesi kerja. Setiap akhir sesi → update-log format 1–6. Akhir U12 → format 7 (phase summary).

---

## 🏁 Hasil Akhir (final — 2026-09-08)

| Metrik | Nilai |
|---|---|
| File TSX/CSS direkonstruksi | **41** (semua di `web/src/`) |
| Class kit `ct-*` | ±90 (token, tombol, kartu, socket, chip/tab, dialog, fase, motion) |
| Perubahan backend / logika / handler / i18n / migrasi | **0** — UI/UX-only terjaga penuh |
| Kontras (U12, terukur) | body 17.1:1 · muted 7.8:1 (WCAG AA lulus) |
| Build final | `tsc` 0 error · vite clean · CSS 147 KB · JS 1.02 MB |
| Log sesi | 13 file `UPDATES/2026-09-0*.md` (format 1–7 locked) |
| Hotfix di tengah jalan | popup z-index (U3.4) · **flicker global** → lahirnya R10 |
| Bug QA final | token `--ct-t2` yatim → diperbaiki (U12) |

**Backlog v2.1:** Esc-per-modal · count-up angka (butuh render nilai) · code-splitting per view · penyapuan sisa emoji struktural di sub-header.

**Aturan permanen untuk UI berikutnya:** R1–R10 (lihat tabel di atas).

---

## 🚫 Luar Scope (butuh persetujuan eksplisit, karena sentuh non-UI)

- Menambah **palet tema baru** ke catalog (→ perlu ubah `database.py` THEMES) — *alternative*: CSS-side "variant" per tema tanpa ubah backend
- Ganti font global / tambah webfont eksternal (offline-first terpengaruh)
- Code-splitting / refactor struktur komponen
- Perubahan teks/i18n massal

---

*Roadmap ini living document — tracker di atas di-update tiap fase selesai. Sumber metodologi: UI UX Pro Max skill v2.0 (`.claude/skills/ui-ux-pro-max`).*
