-- CraftLife: registry rilis untuk auto-update desktop.
-- App klien (anon) membaca rilis terbaru via RPC latest_app_release(),
-- lalu mengunduh zip dari bucket publik 'app-updates'.
-- Hanya operator (service_role / dashboard) yang menulis tabel ini.

create table if not exists public.app_releases (
  id uuid primary key default gen_random_uuid(),
  version text not null unique check(char_length(version) between 1 and 32),
  channel text not null default 'stable' check(channel in('stable','beta')),
  notes text not null default '' check(char_length(notes)<=4000),
  storage_path text not null check(char_length(storage_path) between 1 and 512),
  sha256 text not null default '' check(char_length(sha256)<=64),
  size_bytes bigint not null default 0,
  released_at timestamptz not null default now(),
  created_at timestamptz not null default now()
);

create index if not exists app_releases_channel_time on public.app_releases(channel, released_at desc);

alter table public.app_releases enable row level security;

create policy app_releases_public_read on public.app_releases
  for select using (true);

-- RPC: rilis terbaru per channel (bisa dipanggil pakai anon key, tanpa login).
create or replace function public.latest_app_release(p_channel text default 'stable')
returns jsonb language sql stable security definer set search_path=public as $$
  select to_jsonb(r)
  from (
    select version, channel, notes, storage_path, sha256, size_bytes, released_at
    from public.app_releases
    where channel = coalesce(p_channel, 'stable')
    order by released_at desc, created_at desc
    limit 1
  ) r;
$$;

revoke execute on function public.latest_app_release(text) from public, anon;
grant execute on function public.latest_app_release(text) to public, anon, authenticated;

-- Bucket publik tempat operator mengunggah paket zip rilis.
insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values
  ('app-updates', 'app-updates', true, 1073741824, array['application/zip', 'application/octet-stream'])
on conflict(id) do update set
  public = true,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

create policy app_updates_public_read on storage.objects for select to public
  using (bucket_id = 'app-updates');
