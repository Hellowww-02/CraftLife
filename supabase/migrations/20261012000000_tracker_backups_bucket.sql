-- ---------------------------------------------------------------------------
-- Backup tracker ke Supabase Storage.
--
-- MENGAPA
-- Paket gratis Supabase tidak punya backup otomatis, dan aturan produk P6
-- berbunyi "jangan pernah kehilangan data". Backup lokal yang sudah ada di
-- halaman Pemeliharaan Data hanya menyelamatkan SQLite di satu perangkat; ia
-- tidak menolong kalau perangkat itu hilang atau database cloud-nya bermasalah.
--
-- BENTUK
-- Satu objek gzip per backup, di folder milik pengguna:
--     <auth.uid()>/craftlife_backup_<timestamp>.json.gz
-- Isinya snapshot 40 tabel tracker, dikompresi gzip (JSON murni terkompresi
-- sangat baik, dan paket gratis membatasi 50 MB per file).
--
-- KEAMANAN — ini bagian yang paling penting
-- Policy di sini sengaja TIDAK meniru `profile_storage_authenticated_read`,
-- yang mengizinkan setiap pengguna terautentikasi membaca foto profil siapa
-- pun. Itu masuk akal untuk foto profil. Untuk backup, isi satu objek adalah
-- SELURUH data pribadi pengguna: kesehatan, keuangan, catatan. Karena itu
-- keempat operasi dibatasi ketat ke pemilik folder, termasuk SELECT.
--
-- Tidak ada policy update: backup bersifat immutable. Mengubah backup yang
-- sudah ada tidak punya alasan yang sah.
-- ---------------------------------------------------------------------------

insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values ('tracker-backups', 'tracker-backups', false, 52428800,
        array['application/gzip', 'application/octet-stream'])
on conflict (id) do update
  set public = false,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- Baca: hanya pemilik. Tanpa klausa folder, pengguna lain bisa mengunduh
-- seluruh data pribadi seseorang hanya dengan menebak path.
drop policy if exists tracker_backup_owner_read on storage.objects;
create policy tracker_backup_owner_read on storage.objects for select to authenticated
using (bucket_id = 'tracker-backups'
       and (storage.foldername(name))[1] = auth.uid()::text);

-- Tulis: hanya ke folder sendiri.
drop policy if exists tracker_backup_owner_insert on storage.objects;
create policy tracker_backup_owner_insert on storage.objects for insert to authenticated
with check (bucket_id = 'tracker-backups'
            and (storage.foldername(name))[1] = auth.uid()::text);

-- Hapus: hanya miliknya sendiri — dipakai untuk rotasi backup lama.
drop policy if exists tracker_backup_owner_delete on storage.objects;
create policy tracker_backup_owner_delete on storage.objects for delete to authenticated
using (bucket_id = 'tracker-backups'
       and (storage.foldername(name))[1] = auth.uid()::text);
