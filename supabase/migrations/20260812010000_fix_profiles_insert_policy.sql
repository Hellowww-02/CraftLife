-- Fix account linking when an Auth user exists but its public.profiles row is missing.

-- Backfill every existing Auth account idempotently.
insert into public.profiles(id,username,display_name)
select u.id,
  coalesce(nullif(u.raw_user_meta_data->>'username',''),'user_'||substr(u.id::text,1,8)),
  coalesce(nullif(u.raw_user_meta_data->>'display_name',''),split_part(coalesce(u.email,''),'@',1))
from auth.users u
on conflict(id) do nothing;

-- The desktop links only the currently authenticated user's own profile.
drop policy if exists profiles_owner_insert on public.profiles;
create policy profiles_owner_insert
on public.profiles for insert to authenticated
with check (id=auth.uid() and deleted_at is null);

grant insert on public.profiles to authenticated;

-- Ask PostgREST to refresh its schema/policy cache immediately.
notify pgrst, 'reload schema';
