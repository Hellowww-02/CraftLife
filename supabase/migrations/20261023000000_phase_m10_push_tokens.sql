-- Phase M10 — Token push per perangkat untuk notifikasi sosial.
--
-- Supabase adalah "kantor pos"-nya: token FCM tiap perangkat dicatat di
-- sini, dan Edge Function `send-push` (supabase/functions/send-push)
-- membacanya untuk memanggil FCM HTTP v1 — satu-satunya jalur yang boleh
-- membangunkan aplikasi Android yang sedang tertutup. File
-- `google-services.json` tetap diterbitkan dari Firebase Console oleh
-- pemilik proyek; migrasi ini hanya menyiapkan tempat mencatat tokennya.
--
-- Token bersifat rahasia per perangkat: RLS hanya mengizinkan pemilik
-- membaca/menulis barisnya sendiri, dan fungsi registrasi memakai
-- auth.uid() — client tidak bisa mendaftarkan token atas nama orang lain.

create table if not exists public.device_push_tokens (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  platform text not null default 'android' check (platform in ('android', 'ios', 'desktop')),
  token text not null,
  device_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, token)
);

create index if not exists device_push_tokens_user_idx
  on public.device_push_tokens (user_id);

alter table public.device_push_tokens enable row level security;

drop policy if exists device_push_tokens_owner_select on public.device_push_tokens;
create policy device_push_tokens_owner_select on public.device_push_tokens
  for select to authenticated using (user_id = auth.uid());

drop policy if exists device_push_tokens_owner_insert on public.device_push_tokens;
create policy device_push_tokens_owner_insert on public.device_push_tokens
  for insert to authenticated with check (user_id = auth.uid());

drop policy if exists device_push_tokens_owner_update on public.device_push_tokens;
create policy device_push_tokens_owner_update on public.device_push_tokens
  for update to authenticated using (user_id = auth.uid())
  with check (user_id = auth.uid());

drop policy if exists device_push_tokens_owner_delete on public.device_push_tokens;
create policy device_push_tokens_owner_delete on public.device_push_tokens
  for delete to authenticated using (user_id = auth.uid());

create or replace function public.register_push_token(
  p_token text, p_platform text default 'android', p_device_name text default ''
) returns public.device_push_tokens
language plpgsql security definer set search_path = public as $$
declare
  row_out public.device_push_tokens;
begin
  if auth.uid() is null then
    raise exception 'auth_required';
  end if;
  if coalesce(trim(p_token), '') = '' then
    raise exception 'token_required';
  end if;
  insert into public.device_push_tokens (user_id, platform, token, device_name)
  values (auth.uid(),
          case when p_platform in ('android', 'ios', 'desktop') then p_platform else 'android' end,
          trim(p_token), coalesce(p_device_name, ''))
  on conflict (user_id, token) do update
    set platform = excluded.platform,
        device_name = excluded.device_name,
        updated_at = now()
  returning * into row_out;
  return row_out;
end;
$$;

revoke execute on function public.register_push_token(text, text, text) from public, anon;
grant execute on function public.register_push_token(text, text, text) to authenticated;
