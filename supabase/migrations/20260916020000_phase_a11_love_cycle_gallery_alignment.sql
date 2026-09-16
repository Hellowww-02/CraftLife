-- CraftLife v1.6.3 · fase A11 — Love Space: penyelarasan cloud (tab connection · cycle · gallery)
--
-- OPSIONAL & IDEMPOTEN. Fase A11 hampir seluruhnya bekerja di sisi lokal dan
-- memakai tabel/RPC cloud yang SUDAH ada; migrasi ini hanya jaring pengaman bila
-- ada instalasi yang tertinggal, plus dokumentasi pemetaan A11 → cloud.
-- Tanpa menjalankannya pun aplikasi tetap normal.
--
-- PEMETAAN A11 → CLOUD (semuanya sudah tersedia sejak fase 4a/A10):
--   • Tab CYCLE — edit riwayat siklus (`start_date`, `end_date`, `notes`) memakai
--     RPC public.upsert_love_space_record(...) cabang 'cycle'. Tabel
--     public.love_space_cycles sudah punya `updated_at` + trigger `love_cycles_updated`
--     + indeks `love_cycles_space_start`, jadi tidak ada perubahan skema yang
--     dibutuhkan. (Di SQLite lokal A11 menambahkan `menstrual_cycles.updated_at`.)
--   • Tab CONNECTION — tren mood & riwayat jawaban membaca data yang sudah
--     tersinkron: love_space_checkins (indeks `love_checkins_space_date`) dan
--     love_space_prompt_responses (indeks `love_prompts_space_date`).
--   • Tab GALLERY — hapus massal foto memakai jalur yang sama dengan hapus satu
--     foto: client meng-enqueue sinkron `gallery_photo` delete dan cloud
--     menghapus baris love_space_photos (policy `love_photos_owner_delete`) +
--     objek di storage. PERBAIKAN A11: `cloud_id` dibaca SEBELUM baris lokal
--     dihapus, sehingga penghapusan massal benar-benar ikut ke cloud.
--   • SENGAJA TIDAK di cloud: album galeri (`love_albums` / `love_album_items`)
--     dan kolom sampul `cover_photo_id`. Album adalah pengelompokan pribadi di
--     perangkat dan menunjuk id foto lokal, jadi tidak bisa dipetakan ke cloud
--     tanpa tabel album + id foto cloud. Fitur A11 tetap utuh secara lokal.

-- ── 1) Jaring pengaman siklus (no-op pada instalasi yang sudah lengkap) ───────
alter table public.love_space_cycles
  add column if not exists updated_at timestamptz not null default now();

create index if not exists love_cycles_space_start
  on public.love_space_cycles(love_space_id, start_date desc, id);

do $$
begin
  if not exists (select 1 from pg_trigger where tgname = 'love_cycles_updated') then
    create trigger love_cycles_updated before update on public.love_space_cycles
      for each row execute function public.set_updated_at();
  end if;
end $$;

-- ── 2) Verifikasi (jalankan manual bila perlu) ────────────────────────────────
-- select column_name, data_type from information_schema.columns
--   where table_schema='public' and table_name='love_space_cycles' order by ordinal_position;
-- select indexname from pg_indexes
--   where schemaname='public' and tablename in
--     ('love_space_cycles','love_space_checkins','love_space_prompt_responses','love_space_photos');
