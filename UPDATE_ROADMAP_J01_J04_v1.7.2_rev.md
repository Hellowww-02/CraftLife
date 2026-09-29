# UPDATE ROADMAP — v1.7.2 REVISI (J01–J04) "Signature & Spectrum +"

> Revisi masuk ke rilis **v1.7.2 yang sudah ada** (pola H08/v1.7.0): versi TETAP 1.7.2,
> commit baru + **tag v1.7.2 dipindahkan** ke commit terakhir (aturan UPDATE_RULES §5),
> dokumentasi direvisi di file yang sudah ada (tanpa file release-notes baru).
> Batas keras: hanya menambah/memoles presentasi — tidak mengurangi fitur/logika/game (K3).

## Temuan audit

| Item | Fakta |
|---|---|
| Health & Food hidup | `HealthFoodView.tsx` (route `nutrition` & `health`) — **belum** punya signature; patch I04 kemarin mengenai `NutritionView.tsx` yang dead-code |
| Charts | `components/charts.tsx`: ProgressRing, Sparkline, LineChart, DualLineChart, BarChart, DonutChart, Heatmap, GroupBar — **tanpa** tooltip/hover |
| Konsumen chart | DashboardSummaryPanel, DashboardView, EconomyView, HealthFoodView, SportView, PomodoroView, Love panels |
| Tombol | `.ct-btn` sudah punya hover/active transform; belum ada sheen |
| Dialog | 35 file pakai `.ct-backdrop` + `.ct-dialog` — bisa dianimasikan satu titik CSS |
| Task card | `.ct-task-card` (index.css:880) + drag state `drag.isDragging/isOver` sudah ada di Habits/Dailies/Quests |

## Fase

| Fase | Isi |
|---|---|
| **J01** | Signature HealthFoodView: PageSignature `dots` + aksen teal, navigasi tanggal ke slot kanan (kunci `page_health_title/subtitle` sudah ada) |
| **J02** | Lapisan interaktivitas global (CSS): sheen `.ct-btn-primary/gold/glow`; entrance `.ct-backdrop` fade + `.ct-dialog` pop; `.ct-task-card` entrance-stagger + drag affordance (tilt+grip); drop indicator `.ct-drop-line`; shine bar gamifikasi `.ct-bar-shine` |
| **J03** | Chart interaktif di `charts.tsx`: hover tooltip (pointer-nearest point) + guide line + highlight dot untuk LineChart/DualLineChart/BarChart; hover segmen DonutChart (pusat berubah), Heatmap (sel), GroupBar (segmen); CSS `.ct-chart-tip` |
| **J04** | Revisi docs (RELEASE_NOTES_v1.7.2.md + README) — direvisi in-place; commit; tag v1.7.2 dipindah; laporan Format 1–7 |

## Gate wajib

`python3 -m py_compile` modul terkait · `cd web && ./node_modules/.bin/tsc --noEmit` ·
`./node_modules/.bin/vite build` (catat hash+size) · i18n export bila ada kunci baru ·
live `:8899` sanity · tree bersih.
